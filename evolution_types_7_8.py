import csv,random,math,statistics,pickle,subprocess,sys,time
from pathlib import Path
from combo_sim import simulate
ROOT=Path(__file__).parent

def worker(dataset,n):
    out=[]
    for seed in range(100):
        duration=16200 if dataset=='fixed270' else random.Random(1010000+n*1000+seed).randint(10800,16200)
        r=random.Random((810000 if dataset=='fixed270' else 1810000)+n*1000+seed)
        times=[v+40*i for i,v in enumerate(sorted(r.randrange(duration-40*(n-1)) for _ in range(n)))]
        rolls={t:r.random()<.5 for t in times}
        extra=random.Random((910000 if dataset=='fixed270' else 1910000)+n*1000+seed)
        defense=extra.randint(118,154)
        contacts={t:extra.random()<.25 for t in times}
        original_types={t:extra.randrange(4) for t in times}
        events={t:extra.randint(400,600) for t in times}
        dd={t:extra.random()<.5 for t in times}
        fractions=random.Random((2910000 if dataset=='fixed270' else 3910000)+n*1000+seed)
        # Uniform U with floor(4U)==the exact original four-type assignment.
        uniforms={t:(original_types[t]+fractions.random())/4 for t in times}
        for count in range(7,9):
            types={t:int(uniforms[t]*count) for t in times}
            v=simulate(['evolution'],events,rolls,dd,contacts,types,defense,duration)
            out.append(dict(dataset=dataset,hits=n,seed=seed,types=count,**v))
    return out

def main():
    jobs=ROOT/'evolution_types_7_8_jobs';jobs.mkdir(exist_ok=True)
    waiting=[(dataset,n) for n in range(1,16) for dataset in ['fixed270','random180_270']]
    active=[];details=[];done=0
    while waiting or active:
        while waiting and len(active)<4:
            dataset,n=waiting.pop(0);out=jobs/f'{dataset}_{n}.pkl';log=out.with_suffix('.log').open('w')
            proc=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--worker',dataset,str(n)],stdout=log,stderr=log)
            active.append((proc,out,log))
        for job in active[:]:
            proc,out,log=job;code=proc.poll()
            if code is not None:
                log.close()
                if code:raise RuntimeError(out.with_suffix('.log').read_text())
                details.extend(pickle.loads(out.read_bytes()));active.remove(job);done+=1
                if done%5==0:print('Completed',done,'/30',flush=True)
        time.sleep(.2)
    assert len(details)==6000
    with (ROOT/'evolution_types_7_8_trials.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=details[0]);w.writeheader();w.writerows(details)
    print('7/8 type extra trials saved',len(details))
if __name__=='__main__':
    if len(sys.argv)>1:
        dataset,n=sys.argv[2],int(sys.argv[3]);values=worker(dataset,n)
        (ROOT/'evolution_types_7_8_jobs'/f'{dataset}_{n}.pkl').write_bytes(pickle.dumps(values))
    else:main()
