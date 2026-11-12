import random,csv,statistics
from pathlib import Path
from lumen_sim import simulate
ROOT=Path(__file__).parent
rows=[]
for n in range(1,31):
    result={k:[] for k in ['sponge','chalice','lumen','lumen_natural']}
    wins={k:0 for k in ['sponge','chalice','lumen']}
    for seed in range(100):
        r=random.Random(810000+n*1000+seed)
        times=[v+40*i for i,v in enumerate(sorted(r.randrange(10800-40*(n-1)) for _ in range(n)))]
        events={t:300 for t in times}
        current={}
        for k in result:
            v=simulate('lumen' if k.startswith('lumen') else k,events,5,300,base_hp=800,natural_share=5 if k=='lumen_natural' else 0)
            result[k].append(v)
            if k!='lumen_natural':
                # Survival first, sustain when alive, survival time when dead.
                current[k]=(1,v['absorbed']+v['erased']+v['healed']) if v['alive'] else (0,v['time'])
        best=max(current.values())
        winners=[k for k,v in current.items() if v[0]==best[0] and abs(v[1]-best[1])<1e-6]
        for k in winners:wins[k]+=1/len(winners)
    row={'hits':n}
    for k,vs in result.items():
        row[k+'_survival']=sum(v['alive'] for v in vs)
        row[k+'_time']=round(statistics.mean(v['time'] for v in vs),2)
        if k in wins:row[k+'_wins']=round(wins[k],2)
    rows.append(row)
    print(row,flush=True)
with (ROOT/'lumen_800_results.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
