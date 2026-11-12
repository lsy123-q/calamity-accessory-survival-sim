import random, statistics, csv, json
from pathlib import Path
from simulate import simulate

ROOT=Path(__file__).parent
RUNS=100
rows=[]
for pattern in ['uniform','clustered','exact_hits']:
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
        for kind,results in values.items():
            rows.append(dict(pattern=pattern,attacks=n,accessory=kind,mean_landed=round(statistics.mean(counts),3),
                survival_pct=sum(x['alive'] for x in results)*100/RUNS,
                mean_survival=round(statistics.mean(x['time'] for x in results),3)))
with (ROOT/'random_180.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
for p in ['uniform','clustered','exact_hits']:
    print(p)
    for k in ['sponge','chalice']:
        selected=[x for x in rows if x['pattern']==p and x['accessory']==k]
        print(k,'survival',round(statistics.mean(x['survival_pct'] for x in selected),2),'time',round(statistics.mean(x['mean_survival'] for x in selected),2),'hits',round(statistics.mean(x['mean_landed'] for x in selected),2))
    for low,high in [(1,5),(6,10),(11,15),(16,20),(21,25),(26,30)]:
        print(low,high,[(k,round(statistics.mean(x['survival_pct'] for x in rows if x['pattern']==p and x['accessory']==k and low<=x['attacks']<=high),1)) for k in ['sponge','chalice']])
