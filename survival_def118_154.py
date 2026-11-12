import random,csv,statistics,math
from pathlib import Path
from survival_baseline_sim import simulate
ROOT=Path(__file__).parent
baseline={}
for n in range(1,16):
    for seed in range(100):
        r=random.Random(810000+n*1000+seed)
        times=[v+40*i for i,v in enumerate(sorted(r.randrange(16200-40*(n-1)) for _ in range(n)))]
        rolls={t:r.random()<.5 for t in times}
        rng=random.Random(910000+n*1000+seed)
        defense=rng.randint(118,154)
        contacts={t:rng.random()<.25 for t in times}
        types={t:rng.randrange(4) for t in times}
        events={t:rng.randint(500,600) for t in times}
        v=simulate('baseline',events,0,300,base_hp=725,debuff_rolls=rolls,base_defense=defense,contacts=contacts,projectile_types=types)
        baseline[n,seed]=int(v['alive'])
p0=statistics.mean(baseline.values())
values={}
for r in csv.DictReader((ROOT/'def118_154_trials.csv').open(encoding='utf-8-sig')):
    values.setdefault(r['kind'],[]).append((int(r['hits']),int(r['seed']),int(r['alive']=='True')))
summary=[]
for k,vs in values.items():
    p=statistics.mean(v[2] for v in vs)
    diffs=[v-baseline[n,seed] for n,seed,v in vs]
    # Stratified SE: hit counts have fixed equal weights, seeds random within each.
    variance=sum(statistics.variance([v-baseline[n,s] for nn,s,v in vs if nn==n])/100 for n in range(1,16))/225
    summary.append(dict(kind=k,trials=len(vs),survival_pct=p*100,baseline_pct=p0*100,uplift_pp=(p-p0)*100,relative_uplift_pct=(p/p0-1)*100,paired_margin95_pp=1.96*math.sqrt(variance)*100))
summary.sort(key=lambda r:-r['survival_pct'])
with (ROOT/'survival_uplift_def118_154.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=summary[0]);w.writeheader();w.writerows(summary)
print('BASELINE',sum(baseline.values()),'/',len(baseline),p0*100)
for r in summary:print(r)
