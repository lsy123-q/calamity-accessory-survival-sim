import csv,random,statistics,json
from pathlib import Path
from master_death_sim import simulate
ROOT=Path(__file__).parent
KINDS=['sponge','chalice','lumen','rampart','radiance','core','heart_heal','heart_parry','evolution']
rows=[]
details=[]
for n in range(1,16):
    ranks={k:[] for k in KINDS}
    for seed in range(100):
        r=random.Random(810000+n*1000+seed)
        times=[v+40*i for i,v in enumerate(sorted(r.randrange(10800-40*(n-1)) for _ in range(n)))]
        rolls={t:r.random()<.5 for t in times}
        extra_rng=random.Random(910000+n*1000+seed)
        defense=extra_rng.randint(80,120)
        contacts={t:extra_rng.random()<.25 for t in times}
        types={t:extra_rng.randrange(4) for t in times}
        events={t:extra_rng.randint(500,600) for t in times}
        current={}
        for k in KINDS:
            v=simulate(k,events,0,300,base_hp=725,debuff_rolls=rolls,base_defense=defense,contacts=contacts,projectile_types=types)
            current[k]=(1,v['absorbed']+v['erased']+v['healed']+v['dot_prevented']) if v['alive'] else (0,v['time'])
            details.append(dict(hits=n,seed=seed,defense=defense,kind=k,**v))
        for k,v in current.items():
            better=sum(w[0]>v[0] or (w[0]==v[0] and w[1]>v[1]+1e-6) for w in current.values())
            tied=sum(w[0]==v[0] and abs(w[1]-v[1])<=1e-6 for w in current.values())
            ranks[k].append(1+better+(tied-1)/2)
    row=dict(hits=n,**{k:round(statistics.mean(v),3) for k,v in ranks.items()})
    rows.append(row)
    print(row,flush=True)
for filename,values in [('rank_master_death.csv',rows),('master_death_trials.csv',details)]:
    with (ROOT/filename).open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=values[0]);w.writeheader();w.writerows(values)
print('OVERALL', {k:round(statistics.mean(x[k] for x in rows),3) for k in KINDS})
