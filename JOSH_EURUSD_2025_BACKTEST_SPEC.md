# Josh Models — EURUSD 2025 Backtest Spec
## Reverse-engineering playbook for Claude Code

**Version:** 1.0  
**Date:** 2026-08-26  
**Pair:** EURUSD (spot or 6E futures equivalent; use spot EURUSD unless specified)  
**Period:** 2025-01-01 → 2025-12-31 (inclusive)  
**Purpose:** Identify, each trading day, which of Josh’s session models is valid, simulate entries on **H1 open**, and produce a structured backtest + daily model calendar.

This document is the single source of truth. Do not invent extra ICT concepts unless they are required to implement a rule already written here.

---

## 0. Goal

Given EURUSD OHLC data and a daily news calendar, for every trading day in 2025:

1. Classify the **session narrative** (Asia / London / New York).
2. Decide which **model(s)** are eligible.
3. Apply Josh’s **execution rules** (H1 open, SL, invalidation, news protocol, TGIF/OSOK filters).
4. Simulate trades.
5. Output:
   - A **daily model calendar**
   - A **trade blotter**
   - Performance stats
   - Conflict log (days where 2+ models compete)

This is reverse-engineering of how Josh operates, not a generic ICT scanner.

---

## 1. Timezone, sessions, and candle convention

### 1.1 Timezone (critical)

All hours in this spec are **New York local time** (America/New_York), DST-aware.

ICT killzones in the source notes map to NY time:

| Label in notes | NY time window | Meaning |
|---|---|---|
| Asia | 20:00–00:00 (prev evening) | Asia range / AH / AL |
| 1:00 | 01:00 NY | Early London |
| 2:00 | 02:00 NY | London open proxy |
| 3:00 | 03:00 NY | Core London / PO3 |
| 4:00 | 04:00 NY | Late London |
| 5:00–7:00 | 05:00–07:00 NY | Pre-NY |
| 8:00 | 08:00 NY | NY AM |
| 9:00 | 09:00 NY | NY continuation / reversal |
| 10:00 | 10:00 NY | Late NY |

If data is stored in UTC, convert every timestamp to `America/New_York` before classifying candles.

### 1.2 Candle definition

- **H1 candle of hour X** = bar whose **open time** is `X:00` NY.
- Josh **enters on the open of the H1 candle** specified by the model.
- Exception only when the model explicitly says: wait for retracement / limit after large displacement, or wait first M15 of the next hour.

### 1.3 Reference highs / lows

| Token | Definition |
|---|---|
| **AH / AL** | Asia High / Asia Low = high/low of the Asia session range (20:00–00:00 NY previous evening, inclusive of those H1 bars unless you document a tighter range). |
| **LDNH / LDNL** | London High / London Low so far that day before NY (from 00:00 or 02:00 NY through 07:59 NY). Document the exact window used. Default: 02:00–07:59 NY. |
| **PDH / PDL** | Previous day’s high / low (00:00–23:59 NY previous calendar day). |
| **LRLR** | London Retracement / London Range Retracement: after a London directional move, price retraces that move **outside NY killzone** (before 08:00 NY) and later continues the London direction in NY. Treat as: swing created in London, pullback before 08:00, then NY continuation. |
| **PO3** | Power of 3: accumulation → manipulation → distribution around a key H1 candle (often 03:00 or 04:00). |
| **KZ** | Killzone. London KZ ≈ 02:00–05:00 NY. NY KZ ≈ 07:00–10:00 NY. “Outside KZ” = not inside those windows. |
| **OB** | Order block: last opposite-color H1 candle before displacement. |
| **Displacement** | Impulsive H1 close beyond a swing, leaving imbalance / fair value gap on M15. |
| **SMT** | Smart Money Technique vs DXY (or GBPUSD if used). Optional filter, not required for the base backtest unless DXY data is available. |
| **OSOK** | Weekly narrative / profile bias (see §5). |
| **TGIF** | Friday fade of Mon–Thu directional candles (see §5). |

If DXY is not available, skip SMT as a hard filter and log it as `smt_unavailable`.

---

## 2. Execution DNA (always on)

These override vague wording.

1. **Default entry = H1 open** of the model’s entry hour.
2. If manipulation prints on the **:45 M15** of the prior hour, enter immediately on next H1 open (do not wait for a pullback). Source tip: “Si manipula a las :45, entramos justo en la apertura”.
3. If there is **large displacement** into the entry hour, do **not** chase the H1 open. Wait for an M15 retrace into the OB / FVG and use a limit. If no fill by the model’s latest allowed time, skip.
4. Typical hold / target style in Josh posts: **+2R** or “full TP”. For the backtest use a **ruleset of targets** (see §7). Do not discretionary-exit.
5. One model can produce at most **one primary trade** unless NY Continuation .2 is explicitly unlocked.
6. Risk per primary trade: **1.0R** (normalize results in R).  
   NY Continuation .2 uses **0.5R** only.

### Operating windows (from source)

Allowed trade windows (NY):

- 03:00 → 09:00
- 04:00 → 10:00
- 08:00 → 14:00
- 09:00 → 15:00
- 10:00 → 16:00

If a trade is still open at the window end, flatten at the close of that hour’s H1 (or at 16:00 NY Friday). Document the choice; default = flatten at window end.

---

## 3. Model catalog (source of truth)

Implement each model as a boolean detector + execution template.

### 3.1 ASIA

#### Asia Model.1
**Detect**
- Asia session sweeps or builds a range (AH/AL).
- H1 02:00 **confirms** that manipulation (close in the intended trade direction, away from the swept side).

**Execute**
- Direction: opposite the swept Asia extreme (if Asia high swept and 02:00 confirms down → short).
- Entry: **03:00 H1 open**
- SL: high/low of the **02:00 H1** (for shorts: SL above 02:00 high; longs: SL below 02:00 low)

**Notes**
- Often runs to end of London, then can reverse in NY. Do not auto-flip into NY Reversal unless NY Reversal rules independently fire.

#### Asia Model.2
**Detect**
- **OSOK bias confirmed** (see §5). Hard requirement.
- H1 02:00 does **not** confirm. That is allowed.

**Execute**
- Entry: **03:00 H1 open**
- SL: **Asia high** (shorts) or **Asia low** (longs) — wider than Model.1
- Direction = OSOK daily/weekly bias

---

### 3.2 LONDON

#### London Reversal.1  (highest-frequency named model in Josh posts)
**Detect**
- H1 **02:00 or 03:00** takes AH or AL.
- Confirmation = **OB + displacement** after the raid.
- Soft filter: the two prior H4 candles preferably print **against** the reversal direction (not mandatory; log if missing).

**Execute**
- If 02:00 takes AH/AL → entry **03:00 H1 open**
- If 03:00 takes AH/AL → entry **04:00 H1 open**
- SL: the AH or AL that was taken
- Partials: at opposite AH/AL
- Time-based exit option: when H1 **07:00** takes the low/high of H1 **06:00**, flatten remaining
- If displacement is huge into the entry open → wait M15 retrace to OB, limit order. No fill → skip
- Exception path: 03:00 takes AH/AL but **no confirmation**. Then wait first M15 of 04:00 and enter on that retrace to the marked OB. SL = 04:00 H1 open.

**Follow-on**
- This model often unlocks **NY Continuation .1** the same day.

#### London Reversal 2.1
**Detect**
- H1 **01:00** takes the relevant high/low (AH/AL or prior swing).
- H1 **02:00 MUST confirm** 01:00. If 02:00 does not confirm → **no trade**. Confirmation at 03:00 is invalid for this variant.

**Execute**
- Entry: **03:00 H1 open**
- SL: the raided extreme (AH/AL or 01:00 wick extreme)

#### London Reversal 2.2
**Detect**
- H1 **04:00** takes AH/AL.

**Execute**
- Entry between **04:50–04:55** NY (use 04:45 or 04:50 M15 open as proxy if only M15 data exists; if only H1, skip this model or enter 05:00 open and tag `approximation`).
- Expect expansion **outside killzone**.
- Do **not** arm NY Continuation after this model the same day (source: NY tends to consolidate).

---

### 3.3 NEW YORK

#### NY Continuation .1
**Detect (all required)**
- A **London Reversal** already occurred the same day, preferably London Reversal.1, with the London extreme at **03:00 or 04:00**.
- **LRLR exists**: pullback of the London move occurred before 08:00 NY (“outside KZ”), then NY looks to resume London direction.

**Execute**
- Direction = same as the completed London Reversal
- Entry: **08:00 or 09:00 H1 open**
  - Preferred: 08:00 open through / beyond the highs or lows made outside KZ (e.g. above 07:00 high for longs)
- SL: London extreme (LDNH/LDNL) or a clear M15 invalidation swing
- Management: when price **takes the LRLR** (takes the outside-KZ pullback extreme), move SL to **breakeven**

#### NY Continuation .2
**Detect (all required)**
- Same day already has **London Reversal.1** AND **NY Continuation .1**
- This is the **third trade of the day only**
- If there is news: use News Protocol instead of a naked 09:00 entry
- If no news: entry **09:00 H1 open** (notes also allow 09:00/10:00)

**Execute**
- Risk = **0.5R**
- Exit minimum around 10:00 (flatten at 10:00 or 11:00 H1 open if not stopped)

#### NY Reversal .1
**Detect**
- H1 **08:00 or 09:00** takes **LDNH or LDNL** and closes back inside / shows rejection context.
- Source short form: “Se toma el LDNH/LDNL con la vela de las 8:00/9:00 y entramos a las 9:00/10:00 respectivamente.”

**Execute**
- If 08:00 takes London extreme → entry **09:00 H1 open**
- If 09:00 takes London extreme → entry **10:00 H1 open**
- Direction = opposite the raid (raid of LDNH → short; raid of LDNL → long)
- SL: above/below the 08:00 or 09:00 H1 wick that did the raid (or the London extreme if tighter logic is needed — pick one and keep it consistent)
- Friday + opposite weekly candles → tag **TGIF** as confluence, not a separate model

#### NY Reversal .2
**Detect**
- The day’s high or low forms at **05:00 / 06:00 / 07:00**
- An **H1 order block** exists before 08:00
- Then **displacement**
- Example pattern: 05:00 high takes LDNH, then displacement down

**Execute**
- Entry: **08:00 H1 open**
- SL: beyond the **07:00 H1** (shorts: above 07:00 high)
- If price has already expanded a lot before 08:00 → do not chase; wait M15 retrace/raid into OB. No fill by 09:00 → skip

---

### 3.4 NEWS PROTOCOL (not a session model; a modifier)

Applies only to **08:30 NY and 10:00 NY** high-impact USD/EUR events (CPI, FOMC, NFP, PPI, PMI, GDP, Unemployment, Retail Sales, etc.).

**Rules**
1. Focus on the **last M15 candle before the news**.
2. Place a limit at that M15’s **high** (for longs) or **low** (for shorts) according to the armed model direction.
3. If price takes the **opposite side** of that M15 before the news → cancel / flatten.
4. If the limit is **not filled before the news release** → **do not enter**. Chasing the spike is invalid.
5. Source example uses “8:15 high / 8:15 low” as the pre-08:30 reference candle. Generalize: last complete M15 before the event.

On news days, News Protocol **wraps** NY Continuation .2 and any NY entry that would otherwise fire through the event.

---

## 4. Narrative filters (OSOK + TGIF)

These are filters / confluence, not standalone entries (except Asia Model.2 requires OSOK).

### 4.1 OSOK (weekly profile)
Implementation (deterministic approximation):

- Mon–Tue: allow session models both ways; tag `osok=session_only`.
- Wed–Fri: compute Daily bias:
  - If D1 is making higher highs / holding above prior day mid / expanding away from Monday range in one direction → `osok_dir = that direction`.
  - Prefer models aligned with `osok_dir` from Wednesday onward.
- Log alignment: `with_osok` / `against_osok`.
- Asia Model.2 **cannot fire** unless `osok_dir` is set.

Do not overfit. A simple rule is enough:

```
osok_dir = sign( D1 close[Wed] - weekly open )
```

Update Thursday/Friday with the latest D1 close vs weekly open. Allow override if price takes the opposite weekly extreme and displaces.

### 4.2 TGIF
- Look at Mon–Thu daily candles.
- If Mon–Thu are majority bearish (or all bearish) and Thursday interacts with a PD array (PDH/PDL/weekly level) → Friday search **longs**.
- Opposite for bullish Mon–Thu → Friday search **shorts**.
- TGIF most often expresses as **NY Reversal .1** on Friday (Josh example 2026-08-21).

Tag Friday trades `tgif=true` when this condition holds.

---

## 5. Daily model identification algorithm

Run once per day after 16:00 NY (or sequentially hour by hour for a realistic sim).

### 5.1 Priority (when multiple models qualify)

Use this order. First armed model that also has a valid fill wins the **primary** slot. Later models only fire if explicitly allowed as follow-ons.

1. News Protocol lockout / modification (if 08:30 or 10:00 event)
2. London Reversal 2.1 (01:00+02:00 confirm)  
3. London Reversal.1 (02:00/03:00 raid)  
4. Asia Model.1 (02:00 confirm → 03:00)  
5. Asia Model.2 (only if OSOK and 02:00 did not confirm)
6. London Reversal 2.2 (04:00 raid → 04:50 entry)
7. NY Reversal .2 (05:00–07:00 extreme + H1 OB)
8. NY Continuation .1 (requires prior London Reversal + LRLR)
9. NY Reversal .1 (08:00/09:00 takes London extreme)
10. NY Continuation .2 (requires LR.1 + NY Cont.1)

**Conflict principle**
- A day can have a **sequence** (London Reversal.1 → NY Continuation.1 → optional NY Cont.2).
- A day should **not** take both NY Continuation.1 and NY Reversal.1 in the same direction-conflict. If London reversal was short and NY raids LDNL for a long reversal, NY Reversal.1 **cancels** an unfilled NY Cont.1. If NY Cont.1 is already in profit and LRLR taken, BE rule protects; do not add the opposite reversal unless SL is hit first.

### 5.2 Hour-by-hour state machine

Maintain daily state:

```
asia_high, asia_low
london_high, london_low
took_ah, took_al
london_reversal_variant = None | LR1 | LR21 | LR22
lrlr = False
primary_trade = None
ny_cont1_done = False
news_today = {0830, 1000, none}
osok_dir, tgif
```

Update after each H1 close, then evaluate entries at the next H1 open.

---

## 6. Backtest mechanics

### 6.1 Data required

Minimum:
- EURUSD M15 and H1 OHLC, 2024-12-01 → 2025-12-31 (need December 2024 for PDH/weekly open / Asia of Jan 2)
- Daily OHLC
- Optional H4 for the “two previous H4 opposite” filter
- Economic calendar with timezone (08:30 / 10:00 NY events only for protocol)
- Optional DXY H1 for SMT tags

Spread / costs:
- Use 0.8–1.2 pips round-turn as default EURUSD cost, plus 0.1 pip slippage on H1-open market entries.
- Limit entries: fill only if M15 trades through the limit; no slippage beyond spread.

### 6.2 Target / stop framework (must be deterministic)

Default **Target Set A** (use this first):

- SL as defined by the model
- TP1 = 1R (close 50%)
- TP2 = 2R (close remainder)
- If model defines a time exit, it can flatten remainder earlier
- NY Cont.1 BE rule still applies when LRLR is taken

Also run **Target Set B** as a robustness check:
- No partials, full size to 2R or time stop

### 6.3 Validity filters

Skip a candidate if:
- SL < 5 pips (too tight / noise) or SL > 40 pips (unless Asia Model.2)
- Entry would occur inside a scheduled 08:30/10:00 print without News Protocol compliance
- Friday after 12:00 NY if spread regime is abnormal (optional)
- Holiday / no London-NY overlap session (Christmas week, etc.) — still log the day as `no_session`

### 6.4 What “model applicable that day” means

Even if no fill occurs, still record the **detected model**.  
A day can be:
- `detected_and_traded`
- `detected_not_filled`
- `no_model`
- `conflict`

This calendar is as important as PnL.

---

## 7. Required outputs

### 7.1 `daily_calendar.csv`

One row per calendar day in 2025 (weekdays only, or include weekends as `closed`).

Columns:
- date
- weekday
- osok_dir
- tgif (bool)
- news_0830 (bool)
- news_1000 (bool)
- asia_model (`none|1|2`)
- london_model (`none|LR1|LR21|LR22`)
- ny_model (`none|NYC1|NYC2|NYR1|NYR2`)
- sequence (e.g. `LR1>NYC1`)
- primary_model
- secondary_model
- status (`traded|detected_no_fill|no_model|conflict`)
- notes

### 7.2 `trades.csv`

One row per simulated order.

Columns:
- trade_id
- date
- model
- direction (`long|short`)
- entry_time
- entry_price
- sl_price
- tp1_price
- tp2_price
- exit_time
- exit_price
- exit_reason (`sl|tp1|tp2|be|time|news_cancel|eod`)
- r_multiple
- risk_fraction (`1.0|0.5`)
- with_osok
- tgif
- news_wrapped
- sl_pips
- comments

### 7.3 `performance.md`

Include:
- Net R, win rate, avg R, profit factor, max DD in R
- Breakdown by model
- Breakdown by weekday
- Breakdown TGIF vs non-TGIF Fridays
- Breakdown news days vs quiet days
- Sequence stats: P(NYC1 | LR1), P(NYR1 | Friday), etc.

### 7.4 `assumptions.md`

List every implementation choice that the source left ambiguous (Asia range exact hours, LDN window, fill rules, etc.).

---

## 8. Worked examples (from Josh’s public posts, Aug 2026)

Use these only as classification sanity checks, not as 2025 labels.

| Date | Pair | Josh label | Spec mapping | Entry style |
|---|---|---|---|---|
| 2026-08-21 Fri | EURUSD | `ny reversal.1` + TGIF + SMT PDH | NY Reversal .1 + TGIF | Short, H1 open after NY raid of highs |
| 2026-08-19 Wed | EURUSD | `3/3 this week` + BUY ticket | NY Continuation .1 (probable) | Long, H1/M5 execution shown |
| 2026-08-17 Mon | EURUSD | M15 Market Maker Sell Model | Treat as London distribution / LR-family, not a separate model | Short |
| 2026-08-12 Wed | EURUSD | SMT + 9:30 expansion, CPI | NY Continuation + News Protocol | NY expansion |
| 2026-08-07 Fri | GBPUSD | `lnd reversal.1` + 3AM | London Reversal .1 | Short on 03:00 open family |
| 2026-08-04 Tue | EURUSD | Asia range + PO3 3AM | Asia Model .1 | 03:00 family |

If a Josh post uses “Market Maker Sell/Buy Model”, map it to the session model that actually produced the MM structure (usually London Reversal or NY Reversal), do **not** create a new model.

---

## 9. Implementation plan for Claude Code

Build in this order. Do not skip validation.

1. Load data, convert to America/New_York, resample H1/M15/H4/D1.
2. Build session levels: AH/AL, LDNH/LDNL, PDH/PDL, weekly open.
3. Ingest news calendar; flag 08:30 and 10:00 NY.
4. Implement detectors one model at a time with unit tests on synthetic candles.
5. Implement the daily state machine + priority list.
6. Simulate Target Set A, then B.
7. Emit the four artifacts in §7.
8. Print a sample week (any week in March 2025 and any week in August 2025) for manual audit.

### Suggested stack
- Python 3.11+
- pandas + numpy
- pytz or zoneinfo
- pytest for detector tests

Do not require a paid data vendor in the spec. Accept CSV paths:

```
data/eurusd_m15.csv
data/eurusd_h1.csv
data/eurusd_d1.csv
data/calendar.csv
```

Expected columns: `datetime, open, high, low, close, volume`  
`calendar.csv`: `datetime, currency, event, impact`

---

## 10. Acceptance tests

The job is not done until:

- [ ] Every weekday in 2025 has a calendar row
- [ ] No trade enters off a mid-H1 price unless the model is LR2.2 or a documented retrace-limit
- [ ] NY Cont.2 never appears unless LR1 and NYC1 already exist that day
- [ ] LR2.1 never fires if 02:00 did not confirm 01:00
- [ ] Asia Model.2 never fires without OSOK
- [ ] News days do not market-enter through 08:30/10:00 without protocol
- [ ] Results are reported in R, not account currency
- [ ] `assumptions.md` exists and is honest

---

## 11. What this backtest will NOT do

- It will not copy Josh’s discretionary chart markup perfectly.
- It will not use “feel” or SMT unless DXY is provided.
- It will not claim that a detected model is what Josh actually took in 2025 (those posts are 2026 samples). It claims: **if these rules describe his playbook, this is how they would have fired on EURUSD in 2025.**

That is the reverse-engineering product.
