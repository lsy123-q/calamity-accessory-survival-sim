import sys,subprocess,time,pickle,csv,statistics
from pathlib import Path
from functools import partial
import run_two_sets
from core_audit_sim import simulate
ROOT=Path(__file__).parent
MODES=['actual','instant','stack','no_forced_dd']
def worker(mode,n):
    run_two_sets.KINDS=['core']
    run_two_sets.simulate=partial(simulate,core_mode=mode)
    return [dict(mode=mode,**v) for dataset in ['fixed270','random180_270'] for v in run_two_sets.batch(dataset,n)]
def main():
    jobs=ROOT/'core_audit_jobs';jobs.mkdir(exist_ok=True)
    waiting=[(mode,n) for n in range(1,21) for mode in MODES]
    active=[];details=[];done=0
    while waiting or active:
        while waiting and len(active)<4:
            mode,n=waiting.pop(0)
            out=jobs/f'{mode}_{n}.pkl';log=out.with_suffix('.log').open('w')
            proc=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--worker',mode,str(n)],stdout=log,stderr=log)
            active.append((proc,out,log))
        for job in active[:]:
            proc,out,log=job
            code=proc.poll()
            if code is not None:
                log.close()
                if code:raise RuntimeError(out.with_suffix('.log').read_text())
                details.extend(pickle.loads(out.read_bytes()));active.remove(job)
                done+=1
                if done%8==0:print('batches',done,'/80',flush=True)
        time.sleep(.2)
    with (ROOT/'core_audit.pkl').open('wb') as f:pickle.dump(details,f)
    for mode in MODES:
        vs=[v for v in details if v['mode']==mode]
        totals={k:sum(v['metrics'][k] for v in vs) for k in vs[0]['metrics']}
        print(mode,'survival',statistics.mean(v['alive'] for v in vs)*100,'totals',totals,'coreleft_dead',statistics.mean(v['core_left'] for v in vs if not v['alive']),flush=True)
if __name__=='__main__':
    if len(sys.argv)>1:
        mode,n=sys.argv[2],int(sys.argv[3]);values=worker(mode,n)
        (ROOT/'core_audit_jobs'/f'{mode}_{n}.pkl').write_bytes(pickle.dumps(values))
    else:main()
