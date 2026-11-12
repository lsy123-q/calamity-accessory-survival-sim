import csv,random,statistics
from pathlib import Path
from absorber_sim import simulate
ROOT=Path(__file__).parent
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
        v=simulate('absorber',events,0,300,base_hp=725,debuff_rolls=rolls,base_defense=defense,contacts=contacts,projectile_types=types,defense_damage_rolls=dd)
        details.append(dict(hits=n,seed=seed,defense=defense,kind='absorber',**v))
    print(n,sum(v['alive'] for v in details if v['hits']==n),flush=True)
with (ROOT/'absorber_trials.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=details[0]);w.writeheader();w.writerows(details)
summary=list(csv.DictReader((ROOT/'raw400_600_survival.csv').open(encoding='utf-8-sig')))
p=statistics.mean(v['alive'] for v in details)*100
p0=float(summary[0]['baseline_pct'])
summary.append(dict(kind='absorber',survival_pct=p,baseline_pct=p0,uplift_pp=p-p0,mean_time=statistics.mean(v['time'] for v in details)))
summary.sort(key=lambda v:-float(v['survival_pct']))
with (ROOT/'survival_with_absorber.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=summary[0]);w.writeheader();w.writerows(summary)
for v in summary:print(v)
