import random, statistics, csv, json
from pathlib import Path
from simulate import simulate

ROOT=Path(__file__).parent
RUNS=100
rows=[]
detail=[]
for pattern in ['exact_hits']:
    for n in range(1,31):
        values={'sponge':[],'chalice':[]}
        counts=[]
        for seed in range(RUNS):
            r=random.Random(810000+n*1000+seed)
            if pattern=='uniform':
                times=sorted(r.randrange(10800) for _ in range(n))
            elif pattern=='clustered':
                centers=[r.randrange(10800) for _ in range(r.randint(1,min(6,n)))]
                times=sorted(max(0,min(10799,round(r.choice(centers)+r.gauss(0,120)))) for _ in range(n))
            else:
                # Exactly n landed hits: uniform order statistics with 40-tick spacing.
                times=[v+40*i for i,v in enumerate(sorted(r.randrange(10800-40*(n-1)) for _ in range(n)))]
            events={}
            ready=0
            for t in times:
                if t>=ready:
                    events[t]=300
                    ready=t+40
            counts.append(len(events))
            for kind in values:
                values[kind].append(simulate(kind,events,5,300))
        a,b=values['sponge'],values['chalice']
        wins={'sponge':0,'chalice':0,'tie':0}
        both=[]
        for va,vb in zip(a,b):
            if va['alive'] and vb['alive']:
                sa,sb=va['absorbed'],vb['erased']
                both.append((sa,sb))
            elif va['alive'] != vb['alive']:
                sa,sb=int(va['alive']),int(vb['alive'])
            else:
                sa,sb=va['time'],vb['time']
            wins['sponge' if sa>sb+1e-6 else 'chalice' if sb>sa+1e-6 else 'tie']+=1
        print(n,wins,'bothalive',len(both),'prevented',tuple(round(statistics.mean(v[i] for v in both),1) for i in [0,1]) if both else '-')
        detail.append(dict(hits=n,**wins,both_alive=len(both),sponge_prevented=round(statistics.mean(v[0] for v in both),2) if both else '',chalice_prevented=round(statistics.mean(v[1] for v in both),2) if both else ''))
        for kind,results in values.items():
            rows.append(dict(pattern=pattern,attacks=n,accessory=kind,mean_landed=round(statistics.mean(counts),3),
                survival_pct=sum(x['alive'] for x in results)*100/RUNS,
                mean_survival=round(statistics.mean(x['time'] for x in results),3)))
with (ROOT/'random_180_absorption.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
for p in ['exact_hits']:
    print(p)
    for k in ['sponge','chalice']:
        selected=[x for x in rows if x['pattern']==p and x['accessory']==k]
        print(k,'survival',round(statistics.mean(x['survival_pct'] for x in selected),2),'time',round(statistics.mean(x['mean_survival'] for x in selected),2),'hits',round(statistics.mean(x['mean_landed'] for x in selected),2))
    for low,high in [(1,5),(6,10),(11,15),(16,20),(21,25),(26,30)]:
        print(low,high,[(k,round(statistics.mean(x['survival_pct'] for x in rows if x['pattern']==p and x['accessory']==k and low<=x['attacks']<=high),1)) for k in ['sponge','chalice']])

with (ROOT/'absorption_wins.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=detail[0]);w.writeheader();w.writerows(detail)
