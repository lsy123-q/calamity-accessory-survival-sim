import csv,json,statistics
from pathlib import Path
ROOT=Path(__file__).parent
cfg=json.loads((ROOT/'sigmoid_plateau_weights.json').read_text(encoding='utf-8'))
weights={int(n):w for n,w in cfg['hit_count_weights'].items()}
assert abs(sum(weights.values())-1)<1e-10
original=[r for r in csv.DictReader((ROOT/'two_sets_trials.csv').open(encoding='utf-8-sig')) if int(r['hits'])<=15 and r['kind'] not in ['evolution','lumen']]
evo=[]
for name in ['evolution_types_trials.csv','evolution_types_7_8_trials.csv']:
    evo.extend(csv.DictReader((ROOT/name).open(encoding='utf-8-sig')))
groups={}
for r in original:groups.setdefault(r['kind'],[]).append(r)
for r in evo:groups.setdefault('evolution_'+r['types'],[]).append(r)
def weighted(vs):
    assert len(vs)==3000,len(vs)
    rates={}
    for n in weights:
        chosen=[v for v in vs if int(v['hits'])==n]
        assert len(chosen)==200
        assert len({(r['dataset'],r['seed']) for r in chosen})==200
        rates[n]=statistics.mean(v['alive']=='True' for v in chosen)
    return 100*sum(weights[n]*p for n,p in rates.items())
p0=weighted(groups['baseline'])
summary=[dict(kind=k,survival_pct=weighted(vs),baseline_pct=p0,uplift_pp=weighted(vs)-p0,trials=len(vs)) for k,vs in groups.items() if k!='baseline']
summary.sort(key=lambda r:-r['survival_pct'])
for i,r in enumerate(summary,1):r['rank']=i
with (ROOT/'sigmoid_types2_8_ranking.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=summary[0]);w.writeheader();w.writerows(summary)
print('BASELINE',p0)
for r in summary:print(r)
metadata=dict(weights=weights,projectile_type_counts=list(range(2,9)),evolution_scenarios='ranked separately, not averaged',lumen_excluded=True,baseline_pct=p0,trials_per_configuration=3000)
(ROOT/'sigmoid_types2_8_metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
