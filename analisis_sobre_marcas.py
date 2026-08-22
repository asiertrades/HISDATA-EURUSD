import sys, bisect, csv, collections, statistics as st
from datetime import timedelta, date
sys.path.insert(0,'/home/user/HISDATA-EURUSD')
import cisd_forever_backtest as bt, cisd_m1_sim as m1sim, ltf_bars, ob_entry
import combo_cisd_unicorn as cu
HERE='/home/user/HISDATA-EURUSD'; PIP=0.0001; COSTE=1.0
bars=bt.load_h4_cached([2024,2025],HERE)
sigs=[s for s in bt.run_engine(bars, bt.Params()) if s.entry_time.year==2025]
b15=ltf_bars.load(15,[2024,2025],HERE); idx15={b.t:i for i,b in enumerate(b15)}
m1=m1sim.load_m1(2025,HERE)
obs=ob_entry.find_obs(b15, min_body_p=1.0)
byd={True:[o for o in obs if o.is_bull], False:[o for o in obs if not o.is_bull]}
arr={k:[o.activation_t for o in v] for k,v in byd.items()}
cal={}
with open(HERE+'/calendario_trades_2025.csv') as f:
    for r in csv.DictReader(f):
        y,m,d=map(int,r['fecha'].split('-'))
        if r['resultado'] in ('win','loss'):
            cal[(date(y,m,d),int(r['hora_entrada']),r['dir'])]=r['resultado']

def entrada_ob(sig, modo, r_target, minr=4.0):
    long=sig.direction=="long"
    ini=sig.entry_time-timedelta(hours=4); fin=sig.entry_time+timedelta(hours=4)
    lst=byd[long]; k=bisect.bisect_left(arr[long], ini)
    while k<len(lst) and lst[k].activation_t<fin:
        o=lst[k]; j=idx15.get(o.activation_t)
        if j is not None:
            niv,sl=o.entrada(modo),o.stop(1.0); risk=abs(niv-sl)
            if risk>=minr*PIP:
                for jj in range(j+1,len(b15)):
                    if b15[jj].t>=fin: break
                    if b15[jj].t<sig.entry_time: continue
                    if (b15[jj].l<=niv) if o.is_bull else (b15[jj].h>=niv):
                        tp=niv+r_target*risk if o.is_bull else niv-r_target*risk
                        res,rr,_=cu.simular(m1, b15[jj].t, niv, sl, tp, 24.0)
                        if res in ("sin datos","sin llenar"): return None
                        return dict(r=rr, neto=rr-COSTE*PIP/risk, risk=risk/PIP, hora=b15[jj].t.hour, fill=b15[jj].t)
                    
        k+=1
    return None

def entrada_mercado(sig, r_target, sl_pips=None):
    """A mercado en la apertura de la vela de entrada; SL en el extremo de la vela CISD."""
    long=sig.direction=="long"
    ts,mo,mh,ml,mc=m1
    i=bisect.bisect_left(ts, sig.entry_time)
    if i>=len(ts): return None
    e=mo[i]
    sl=(sig.lo-PIP) if long else (sig.hi+PIP)
    if sl_pips: sl=(e-sl_pips*PIP) if long else (e+sl_pips*PIP)
    risk=abs(e-sl)
    if risk<=0: return None
    tp=e+r_target*risk if long else e-r_target*risk
    res,rr,_=cu.simular(m1, sig.entry_time, e, sl, tp, 24.0)
    if res in ("sin datos","sin llenar"): return None
    return dict(r=rr, neto=rr-COSTE*PIP/risk, risk=risk/PIP, hora=sig.entry_time.hour)

marcadas=[]
for s in sigs:
    k=(s.entry_time.date(), s.entry_time.hour, s.direction)
    if k in cal: marcadas.append((s, cal[k]=='win'))
print(f"Señales de 2025 con marca en tu calendario: {len(marcadas)}  "
      f"(✓ {sum(1 for _,w in marcadas if w)} · ✕ {sum(1 for _,w in marcadas if not w)})\n")

metodos=[("OB open · TP 3R",  lambda s: entrada_ob(s,"open",3.0)),
         ("OB open · TP 2R",  lambda s: entrada_ob(s,"open",2.0)),
         ("OB mitad · TP 3R", lambda s: entrada_ob(s,"mitad",3.0)),
         ("mercado · SL extremo CISD · TP 2R", lambda s: entrada_mercado(s,2.0)),
         ("mercado · SL 20 pips · TP 3R", lambda s: entrada_mercado(s,3.0,20.0))]

print(f"{'método':36} {'grupo':8} {'señales':>8} {'entra':>7} {'WR':>7} {'R/op neto':>11} {'R total':>9}")
res_cache={}
for nom,fn in metodos:
    for etq,filtro in (("✓", True), ("✕", False)):
        sub=[s for s,w in marcadas if w==filtro]
        rr=[]
        for s in sub:
            key=(nom,s.sig_time,s.direction)
            if key not in res_cache: res_cache[key]=fn(s)
            o=res_cache[key]
            if o: rr.append(o)
        if not rr: continue
        print(f"{nom:36} {etq:8} {len(sub):8} {len(rr):7} "
              f"{sum(1 for o in rr if o['r']>0)/len(rr)*100:6.1f}% "
              f"{sum(o['neto'] for o in rr)/len(rr):+11.3f} {sum(o['neto'] for o in rr):+9.1f}")

# dentro de los ✓, por hora del llenado con OB
print("\n■ Dentro de tus ✓: resultado del OB open TP 3R por hora del llenado")
g=collections.defaultdict(list)
for s,w in marcadas:
    if not w: continue
    o=res_cache[("OB open · TP 3R",s.sig_time,s.direction)]
    if o: g[o['hora']].append(o)
print(f"   {'hora':>6} {'ops':>5} {'WR':>7} {'R/op':>9}")
for h in sorted(g):
    v=g[h]
    if len(v)>=5:
        print(f"   {h:5}h {len(v):5} {sum(1 for o in v if o['r']>0)/len(v)*100:6.1f}% {sum(o['neto'] for o in v)/len(v):+9.3f}")

# combinación final: filtro de calidad + franja horaria + entrada OB
q={(x.sig_time,x.direction,x.tier) for x in bt.run_engine(bars, bt.Params(qOn=True)) if x.quality_ok}
print("\n■ Aplicando filtros sobre tus 138 marcas (entrada OB open, TP 3R)")
print(f"   {'filtro':34} {'señales':>8} {'✓':>4} {'✕':>4} {'% ✓':>6} {'ops':>5} {'R total':>9}")
def evalua(nombre, cond):
    sel=[(s,w) for s,w in marcadas if cond(s,w)]
    if not sel: return
    rr=[]
    for s,w in sel:
        o=res_cache[("OB open · TP 3R",s.sig_time,s.direction)]
        if o and cond(s,w,o): rr.append(o)
    v=sum(1 for _,w in sel if w)
    print(f"   {nombre:34} {len(sel):8} {v:4} {len(sel)-v:4} {v/len(sel)*100:5.0f}% {len(rr):5} "
          f"{sum(o['neto'] for o in rr):+9.1f}")
def c(cond):
    return lambda s,w,o=None: cond(s,o) if o is not None else cond(s,None)
evalua("todas", c(lambda s,o: True))
evalua("+ calidad CISD", c(lambda s,o: (s.sig_time,s.direction,s.tier) in q))
evalua("+ franja 05-07 y 09-10 NY", c(lambda s,o: o is None or o['hora'] in (5,6,7,9,10)))
evalua("+ calidad y franja", c(lambda s,o: (s.sig_time,s.direction,s.tier) in q and (o is None or o['hora'] in (5,6,7,9,10))))

# ¿cuántos ✓ se pierden por no encontrar entrada?
sin=[s for s,w in marcadas if w and not res_cache[("OB open · TP 3R",s.sig_time,s.direction)]]
print(f"\n   ✓ sin entrada con el OB: {len(sin)} de {sum(1 for _,w in marcadas if w)}")
