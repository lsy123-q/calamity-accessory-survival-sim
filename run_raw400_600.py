import csv,random,statistics
from pathlib import Path
from raw400_600_sim import simulate
ROOT=Path(__file__).parent
KINDS=['baseline','sponge','chalice','lumen','rampart','radiance','core','heart_heal','heart_parry','evolution']
details=[]
for n in range(1,16):
    for seed in range(100):
        rng=random.Random(810000+n*1000+seed)
        times=[v+40*i for i,v in enumerate(sorted(rng.randrange(16200-40*(n-1)) for _ in range(n)))]
        rolls={t:rng.random()<.5 for t in times}
        extra=random.Random(910000+n*1000+seed)
        defense=extra.randint(118,154)
        contacts={t:extra.random()<.25 for t in times}
        types={t:extra.randrange(4) for t in times}
        events={t:extra.randint(400,600) for t in times}
        dd={t:extra.random()<.5 for t in times}
        for k in KINDS:
            v=simulate(k,events,0,300,base_hp=725,debuff_rolls=rolls,base_defense=defense,contacts=contacts,projectile_types=types,defense_damage_rolls=dd)
            details.append(dict(hits=n,seed=seed,defense=defense,kind=k,**v))
    print(n,{k:sum(v['alive'] for v in details if v['hits']==n and v['kind']==k) for k in KINDS},flush=True)
with (ROOT/'raw400_600_trials.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=details[0]);w.writeheader();w.writerows(details)
p0=statistics.mean(v['alive'] for v in details if v['kind']=='baseline')
summary=[]
for k in KINDS[1:]:
    vs=[v for v in details if v['kind']==k]
    p=statistics.mean(v['alive'] for v in vs)
    summary.append(dict(kind=k,survival_pct=p*100,baseline_pct=p0*100,uplift_pp=(p-p0)*100,mean_time=statistics.mean(v['time'] for v in vs)))
summary.sort(key=lambda v:-v['survival_pct'])
with (ROOT/'raw400_600_survival.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=summary[0]);w.writeheader();w.writerows(summary)
print('BASELINE',p0*100)
for v in summary:print(v)
