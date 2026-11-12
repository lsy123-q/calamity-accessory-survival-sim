import csv,random,pickle,subprocess,sys,time,statistics,itertools,json
from pathlib import Path
from combo_sim import simulate
ROOT=Path(__file__).parent
ITEMS=['sponge','chalice','rampart','radiance','core','heart','evolution','absorber']
CONFIGS=[(a+'+'+b+(':'+policy if 'heart' in (a,b) else ''),(a,b),policy)
         for a,b in itertools.combinations(ITEMS,2)
         for policy in (['heal','parry'] if 'heart' in (a,b) else ['heal'])]

def worker(dataset,n,chunk):
    configs=CONFIGS[chunk*7:(chunk+1)*7]
    out=[]
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
        for name,items,policy in configs:
            v=simulate(items,events,rolls,dd,contacts,types,defense,duration,policy)
            out.append(dict(dataset=dataset,hits=n,seed=seed,config=name,**v))
    return out

def main():
    assert len(CONFIGS)==35
    jobs=ROOT/'combo_jobs';jobs.mkdir(exist_ok=True)
    waiting=[(dataset,n,chunk) for n in range(1,16) for dataset in ['fixed270','random180_270'] for chunk in range(5)]
    active=[];details=[];done=0
    while waiting or active:
        while waiting and len(active)<4:
            dataset,n,chunk=waiting.pop(0);out=jobs/f'{dataset}_{n}_{chunk}.pkl'
            log=out.with_suffix('.log').open('w')
            proc=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--worker',dataset,str(n),str(chunk)],stdout=log,stderr=log)
            active.append((proc,out,log))
        for job in active[:]:
            proc,out,log=job;code=proc.poll()
            if code is not None:
                log.close()
                if code:raise RuntimeError(out.with_suffix('.log').read_text())
                details.extend(pickle.loads(out.read_bytes()));active.remove(job);done+=1
                if done%10==0:print('Completed',done,'/150 batches',flush=True)
        time.sleep(.2)
    assert len(details)==105000,len(details)
    with (ROOT/'combo_trials.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=details[0]);w.writeheader();w.writerows(details)
    weights={n:(.25 if n<=3 else 1)/12.75 for n in range(1,16)}
    baseline_rows=[r for r in csv.DictReader((ROOT/'two_sets_trials.csv').open(encoding='utf-8-sig')) if r['kind']=='baseline' and int(r['hits'])<=15]
    p0=sum(weights[n]*statistics.mean(r['alive']=='True' for r in baseline_rows if int(r['hits'])==n) for n in weights)*100
    summary=[]
    for name,items,policy in CONFIGS:
        vs=[v for v in details if v['config']==name]
        assert len(vs)==3000
        p=sum(weights[n]*statistics.mean(v['alive'] for v in vs if v['hits']==n) for n in weights)*100
        summary.append(dict(config=name,survival_pct=p,baseline_pct=p0,uplift_pp=p-p0,trials=len(vs)))
    summary.sort(key=lambda v:-v['survival_pct'])
    with (ROOT/'combo_survival.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=summary[0]);w.writeheader();w.writerows(summary)
    print('BASELINE',p0)
    for v in summary:print(v)
if __name__=='__main__':
    if len(sys.argv)>1:
        dataset,n,chunk=sys.argv[2],int(sys.argv[3]),int(sys.argv[4])
        values=worker(dataset,n,chunk)
        (ROOT/'combo_jobs'/f'{dataset}_{n}_{chunk}.pkl').write_bytes(pickle.dumps(values))
    else:main()
