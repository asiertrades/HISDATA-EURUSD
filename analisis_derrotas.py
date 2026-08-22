import sys, csv, bisect, collections, statistics as st
from datetime import date, timedelta
sys.path.insert(0,'/home/user/HISDATA-EURUSD')
import cisd_forever_backtest as bt, cisd_m1_sim as m1sim
HERE='/home/user/HISDATA-EURUSD'; PIP=0.0001
bars=bt.load_h4_cached([2024,2025],HERE); idx={b.t:i for i,b in enumerate(bars)}
sigs=[s for s in bt.run_engine(bars, bt.Params()) if s.entry_time.year==2025]
ts,mo,mh,ml,mc=m1sim.load_m1(2025,HERE)
cal={}
with open(HERE+'/calendario_trades_2025.csv') as f:
    for r in csv.DictReader(f):
        y,m,d=map(int,r['fecha'].split('-'))
        cal[(date(y,m,d),int(r['hora_entrada']),r['dir'])]=(r['resultado'], r['evento'])
DIAS=['Lun','Mar','Mié','Jue','Vie','Sáb','Dom']

# orden dentro de la sesión
ses_de=lambda t: (t-timedelta(hours=17)).date()
orden={}
g=collections.defaultdict(list)
for s in sorted(sigs,key=lambda x:x.entry_time): g[ses_de(s.entry_time)].append(s)
for v in g.values():
    for k,s in enumerate(v): orden[id(s)]=k

filas=[]
for s in sigs:
    k=(s.entry_time.date(), s.entry_time.hour, s.direction)
    if k not in cal: continue
    res,ev=cal[k]
    if res not in ('win','loss'): continue
    i=idx[s.sig_time]; b=bars[i]; j=i
    while bars[j].hour!=17: j-=1
    ref=bars[j]; sesb=bars[j:i+1]
    rng=max(b.h-b.l,1e-5); body=abs(b.c-b.o); long=s.direction=='long'
    upw=(b.h-b.c) if b.c>b.o else (b.h-b.o); dnw=(b.o-b.l) if b.c>b.o else (b.c-b.l)
    q=bisect.bisect_left(ts,s.entry_time); end=bisect.bisect_left(ts,s.entry_time+timedelta(hours=24))
    if q>=end: continue
    e=mo[q]; mfe=mae=0.0
    for z in range(q,end):
        mfe=max(mfe,(mh[z]-e) if long else (e-ml[z])); mae=max(mae,(e-ml[z]) if long else (mh[z]-e))
    filas.append(dict(
        s=s, win=res=='win', ev=ev or '', fecha=s.entry_time.date(), dia=DIAS[s.entry_time.weekday()],
        hora=s.entry_time.hour, dir=s.direction, tier=s.tier,
        cuerpo=body/PIP, ratio=body/rng, atr=s.atr6/PIP,
        mecha=(upw if long else dnw)/max(body,1e-9),
        exc=((ref.l-min(x.l for x in sesb)) if long else (max(x.h for x in sesb)-ref.h))/PIP,
        rango_ses=(max(x.h for x in sesb)-min(x.l for x in sesb))/PIP,
        dist17=abs(b.c-ref.o)/PIP,
        cierre_pos=(b.c-b.l)/rng if long else (b.h-b.c)/rng,
        segunda=orden[id(s)]>0, mfe=mfe/PIP, mae=mae/PIP,
        rel_atr=body/max(s.atr6,1e-9)))

per=[f for f in filas if not f['win']]
print(f"LAS {len(per)} DERROTAS DE 2025\n")
print(f"{'fecha':11} {'día':4} {'h':3} {'dir':6} {'tier':5} {'evento':8} {'cuerpo':>7} {'ratio':>6} "
      f"{'exceso':>7} {'rango':>7} {'a favor':>8} {'contra':>8}")
print('─'*104)
for f in sorted(per, key=lambda x:x['fecha']):
    print(f"{str(f['fecha']):11} {f['dia']:4} {f['hora']:02d}h {f['dir']:6} {f['tier']:5} {f['ev'] or '—':8} "
          f"{f['cuerpo']:6.1f}p {f['ratio']:6.2f} {f['exc']:6.1f}p {f['rango_ses']:6.1f}p "
          f"{f['mfe']:7.1f}p {f['mae']:7.1f}p")

print(f"\n\n¿HAY ALGO ANTES DE ENTRAR QUE ANTICIPE LA EXCURSIÓN EN CONTRA?\n")
gan=[f for f in filas if f['win']]
print(f"{'variable':28} {'media ✓':>10} {'media ✕':>10} {'dif':>8}")
for var,etq in (('cuerpo','cuerpo (pips)'),('ratio','cuerpo/rango'),('exc','exceso barrido'),
                ('rango_ses','rango sesión'),('dist17','dist. al open 17:00'),('atr','ATR6 H4'),
                ('mecha','mecha contra/cuerpo'),('cierre_pos','cierre en la vela'),('rel_atr','cuerpo/ATR6')):
    a=st.mean(f[var] for f in gan); b_=st.mean(f[var] for f in per)
    print(f"{etq:28} {a:10.2f} {b_:10.2f} {b_-a:+8.2f}")
print()
# correlación de cada variable con la excursión en contra
import math
def corr(xs,ys):
    n=len(xs); mx=st.mean(xs); my=st.mean(ys)
    num=sum((x-mx)*(y-my) for x,y in zip(xs,ys))
    den=math.sqrt(sum((x-mx)**2 for x in xs)*sum((y-my)**2 for y in ys))
    return num/den if den else 0
print("Correlación con la excursión EN CONTRA (todas las señales):")
for var in ('cuerpo','ratio','exc','rango_ses','dist17','atr','mecha','cierre_pos','rel_atr'):
    print(f"   {var:14} {corr([f[var] for f in filas],[f['mae'] for f in filas]):+.3f}")
print(f"\n   (para comparar, correlación del ATR6 con la excursión A FAVOR: "
      f"{corr([f['atr'] for f in filas],[f['mfe'] for f in filas]):+.3f})")
