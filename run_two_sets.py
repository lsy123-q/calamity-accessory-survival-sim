import csv,random,statistics,subprocess,sys,time,pickle
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
from two_sets_sim import simulate
ROOT=Path(__file__).parent
KINDS=['baseline','sponge','chalice','lumen','rampart','radiance','core','heart_heal','heart_parry','evolution','absorber']

def batch(dataset,n):
    results=[]
    for seed in range(100):
        duration=16200 if dataset=='fixed270' else random.Random(1010000+n*1000+seed).randint(10800,16200)
        r=random.Random((810000 if dataset=='fixed270' else 1810000)+n*1000+seed)
        times=[v+40*i for i,v in enumerate(sorted(r.randrange(duration-40*(n-1)) for _ in range(n)))]
        rolls={t:r.random()<.5 for t in times}
        extra=random.Random((910000 if dataset=='fixed270' else 1910000)+n*1000+seed)
        defense=extra.randint(118,154)
        contacts={t:extra.random()<.25 for t in times}
        types={t:extra.randrange(4) for t in times}
        events={t:extra.randint(400,600) for t in times}
        dd={t:extra.random()<.5 for t in times}
        for k in KINDS:
            v=simulate(k,events,0,300,base_hp=725,debuff_rolls=rolls,base_defense=defense,contacts=contacts,projectile_types=types,defense_damage_rolls=dd,duration_ticks=duration)
            results.append(dict(dataset=dataset,hits=n,seed=seed,duration=duration/60,defense=defense,kind=k,**v))
    return results

def old_data():
    out=[]
    for name in ['raw400_600_trials.csv','absorber_trials.csv']:
        for r in csv.DictReader((ROOT/name).open(encoding='utf-8-sig')):
            r={k:(v if k=='kind' else v=='True' if k=='alive' else int(v) if k in ['hits','seed','defense'] else float(v)) for k,v in r.items()}
            out.append(dict(dataset='fixed270',duration=270,**r))
    return out

def main():
    details=old_data()
    tasks=[('random180_270',n) for n in range(1,21)]+[('fixed270',n) for n in range(16,21)]
    jobs=ROOT/'two_sets_jobs'
    jobs.mkdir(exist_ok=True)
    waiting=list(tasks)
    active=[]
    while waiting or active:
        while waiting and len(active)<4:
            dataset,n=waiting.pop(0)
            out=jobs/f'{dataset}_{n}.pkl'
            log=(jobs/f'{dataset}_{n}.log').open('w')
            proc=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--worker',dataset,str(n)],stdout=log,stderr=log)
            active.append((proc,dataset,n,out,log))
        for job in active[:]:
            proc,dataset,n,out,log=job
            code=proc.poll()
            if code is not None:
                log.close()
                if code:raise RuntimeError(f'{dataset} {n} failed: {out.with_suffix(".log").read_text()}')
                values=pickle.loads(out.read_bytes())
                details.extend(values)
                print(dataset,n,{k:sum(v['alive'] for v in values if v['kind']==k) for k in KINDS},flush=True)
                active.remove(job)
        time.sleep(.25)
    assert len(details)==44000,len(details)
    with (ROOT/'two_sets_trials.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=details[0]);w.writeheader();w.writerows(details)
    summary=[]
    for dataset in ['fixed270','random180_270','combined']:
        selected=details if dataset=='combined' else [v for v in details if v['dataset']==dataset]
        p0=statistics.mean(v['alive'] for v in selected if v['kind']=='baseline')*100
        for k in KINDS[1:]:
            vs=[v for v in selected if v['kind']==k]
            p=statistics.mean(v['alive'] for v in vs)*100
            summary.append(dict(dataset=dataset,kind=k,trials=len(vs),survival_pct=p,baseline_pct=p0,uplift_pp=p-p0))
    summary.sort(key=lambda v:(v['dataset'],-v['survival_pct']))
    with (ROOT/'two_sets_survival.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=summary[0]);w.writeheader();w.writerows(summary)
    for v in summary:print(v)
if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--worker':
        dataset,n=sys.argv[2],int(sys.argv[3])
        result=batch(dataset,n)
        (ROOT/'two_sets_jobs'/f'{dataset}_{n}.pkl').write_bytes(pickle.dumps(result))
    else:main()
