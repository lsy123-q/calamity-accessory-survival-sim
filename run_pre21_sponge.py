import random,csv,statistics
from pathlib import Path
from pre21_sponge_sim import simulate
ROOT=Path(__file__).parent
details=[]
for dataset in ['fixed270','random180_270']:
    for n in range(1,16):
        for seed in range(100):
            duration=16200 if dataset=='fixed270' else random.Random(1010000+n*1000+seed).randint(10800,16200)
            r=random.Random((810000 if dataset=='fixed270' else 1810000)+n*1000+seed)
            times=[v+40*i for i,v in enumerate(sorted(r.randrange(duration-40*(n-1)) for _ in range(n)))]
            rolls={t:r.random()<.5 for t in times}
            extra=random.Random((910000 if dataset=='fixed270' else 1910000)+n*1000+seed)
            defense=extra.randint(118,154)
            contacts={t:extra.random()<.25 for t in times};types={t:extra.randrange(4) for t in times}
            events={t:extra.randint(400,600) for t in times};dd={t:extra.random()<.5 for t in times}
            v=simulate(['sponge'],events,rolls,dd,contacts,types,defense,duration)
            details.append(dict(dataset=dataset,hits=n,seed=seed,**v))
weights={n:(.25 if n<=3 else 1)/12.75 for n in range(1,16)}
p=sum(weights[n]*statistics.mean(v['alive'] for v in details if v['hits']==n) for n in weights)*100
old=list(csv.DictReader((ROOT/'weighted_lowhit_reduced.csv').open(encoding='utf-8-sig')))
base=float(old[0]['baseline_pct'])
summary=[dict(kind=r['kind'],survival_pct=float(r['survival_pct'])) for r in old if r['kind'] not in ['lumen','sponge']]
summary.append(dict(kind='sponge_pre21',survival_pct=p));summary.sort(key=lambda v:-v['survival_pct'])
with (ROOT/'pre21_sponge_ranking.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=summary[0]);w.writeheader();w.writerows(summary)
with (ROOT/'pre21_sponge_trials.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=details[0]);w.writeheader();w.writerows(details)
print('PRE21',p,'UPLIFT',p-base)
for i,r in enumerate(summary,1):print(i,r)
