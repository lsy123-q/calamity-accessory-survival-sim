import csv,random,statistics
from pathlib import Path
from natural_dot_sim import simulate
rows=[]
for n in range(1,16):
    ranks={k:[] for k in ['sponge','chalice','lumen','rampart','radiance']}
    for seed in range(100):
        r=random.Random(810000+n*1000+seed)
        times=[v+40*i for i,v in enumerate(sorted(r.randrange(10800-40*(n-1)) for _ in range(n)))]
        rolls={t:r.random()<.5 for t in times}
        current={}
        for k in ranks:
            v=simulate(k,{t:300 for t in times},5,300,base_hp=800,debuff_rolls=rolls)
            current[k]=(1,v['absorbed']+v['erased']+v['healed']+v['dot_prevented']) if v['alive'] else (0,v['time'])
        for k,v in current.items():
            better=sum(w[0]>v[0] or (w[0]==v[0] and w[1]>v[1]+1e-6) for w in current.values())
            tied=sum(w[0]==v[0] and abs(w[1]-v[1])<=1e-6 for w in current.values())
            ranks[k].append(1+better+(tied-1)/2)
    row=dict(hits=n,**{k:round(statistics.mean(v),3) for k,v in ranks.items()})
    rows.append(row)
    print(row,flush=True)
with (Path(__file__).parent/'rank_natural_dot.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
print('OVERALL', {k:round(statistics.mean(x[k] for x in rows),3) for k in ranks})
