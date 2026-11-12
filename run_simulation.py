"""현재 실험 실행기: settings.py 수정 → python run_simulation.py.

--dry-run: 설정 검증/실행 규모만 표시. --smoke: 작은 샘플로 실행 경로 점검.
과거 결과 캐시는 사용하지 않으며, 각 실행 폴더에 설정 스냅샷을 보존한다.
"""
import argparse,csv,hashlib,itertools,json,math,pickle,random,statistics,subprocess,sys,time
from datetime import datetime
from pathlib import Path
from current_engine import simulate
import settings

ROOT=Path(__file__).resolve().parent
VALID_ITEMS={'sponge','chalice','rampart','radiance','core','heart','evolution','absorber','nebulous'}

def validate(c):
    if c['FPS']!=60:raise ValueError('FPS는 게임 상수이므로60을 유지하세요.')
    for key in ['BASE_DR','PROJECTILE_PROBABILITY','DEBUFF_PROBABILITY','DEFENSE_DAMAGE_PROBABILITY']:
        if not 0<=c[key]<=1:raise ValueError(key+'는0~1이어야 합니다.')
    for low,high in [('DEFENSE_MIN','DEFENSE_MAX'),('RAW_DAMAGE_MIN','RAW_DAMAGE_MAX'),('HIT_COUNT_MIN','HIT_COUNT_MAX'),('RANDOM_DURATION_MIN_SECONDS','RANDOM_DURATION_MAX_SECONDS')]:
        if c[low]>c[high]:raise ValueError(low+'가 '+high+'보다 큽니다.')
    if c['PLAYER_MAX_HP']<=0 or c['MAX_LIFE1']<=0 or c['DEFENSE_MIN']<=0:raise ValueError('HP/MAXLIFE1/방어력은 양수여야 합니다.')
    if not 0<c['START_HP_FRACTION']<=1:raise ValueError('START_HP_FRACTION은0초과1이하입니다.')
    if c['HIT_COUNT_MIN']<1 or c['RAW_DAMAGE_MIN']<1:raise ValueError('공격 수/원본 피해는1이상입니다.')
    if c['MIN_ATTACK_GAP_TICKS']<0:raise ValueError('최소 공격 간격은0이상입니다.')
    if c['SAMPLES_PER_HIT_COUNT']<1 or c['WORKERS']<1:raise ValueError('표본/프로세스 수는1이상입니다.')
    if not c['DATASETS'] or len(set(c['DATASETS']))!=len(c['DATASETS']) or set(c['DATASETS'])-{'fixed','random'}:raise ValueError('DATASETS에는fixed/random을 중복 없이 지정하세요.')
    if not c['ACCESSORIES'] or len(set(c['ACCESSORIES']))!=len(c['ACCESSORIES']) or set(c['ACCESSORIES'])-VALID_ITEMS:raise ValueError('ACCESSORIES의 아이템 ID가 잘못됐습니다.')
    if not c['HEART_POLICIES'] or set(c['HEART_POLICIES'])-{'heal','parry'}:raise ValueError('심장 정책은heal/parry입니다.')
    for key in ['PROJECTILE_TYPE_COUNTS','COMBO_PROJECTILE_TYPE_COUNTS']:
        if not c[key] or len(set(c[key]))!=len(c[key]) or any(not isinstance(v,int) or v<1 for v in c[key]):raise ValueError(key+'에는 서로 다른1이상 정수를 넣으세요.')
    if c['MODE'] not in ['single','combos']:raise ValueError('MODE는single/combos입니다.')
    if c['WEIGHT_MODE'] not in ['uniform','sigmoid_plateau']:raise ValueError('WEIGHT_MODE를 확인하세요.')
    if c['SIGMOID_STEEPNESS']<=0:raise ValueError('시그모이드 기울기는 양수입니다.')
    for key in ['POTION_TRIGGER_MISSING_HP','DEBUFF_DPS','DEBUFF_DURATION_SECONDS','POTION_HEAL','DEFENSE_EFFECTIVENESS','DEFENSE_DAMAGE_RATIO','DEFENSE_DAMAGE_FLOOR']:
        if c[key]<0:raise ValueError(key+'는0이상입니다.')
    if c['DD_RECOVERY_BASE_TICKS']<=0 or c['DD_RECOVERY_MAX_TICKS']<c['DD_RECOVERY_BASE_TICKS']:raise ValueError('방어력 손상 회복기간을 확인하세요.')
    if c['POTION_COOLDOWN_SECONDS']<=0 or not 0<=c['ABSORBER_AURA_STAY_SECONDS']<=30:raise ValueError('물약 쿨다운/장판 체류시간을 확인하세요.')
    durations=[]
    if 'fixed' in c['DATASETS']:durations.append(c['FIXED_DURATION_SECONDS'])
    if 'random' in c['DATASETS']:durations.append(c['RANDOM_DURATION_MIN_SECONDS'])
    if min(durations)*60-c['MIN_ATTACK_GAP_TICKS']*(c['HIT_COUNT_MAX']-1)<=0:raise ValueError('전투시간 안에 해당 공격 수와 최소 간격을 배치할 수 없습니다.')
    output=(ROOT/c['OUTPUT_DIRECTORY']).resolve()
    if not output.is_relative_to(ROOT) or output==ROOT:raise ValueError('결과 폴더는 이 작업 폴더 아래의 하위 폴더로 지정하세요.')

def configurations(c):
    out=[dict(name='baseline',items=[],policy='heal',types=4)]
    if c['MODE']=='single':
        for item in c['ACCESSORIES']:
            policies=c['HEART_POLICIES'] if item=='heart' else ['heal']
            counts=c['PROJECTILE_TYPE_COUNTS'] if item=='evolution' else [4]
            for policy in policies:
                for count in counts:
                    name='heart_'+policy if item=='heart' else 'evolution_'+str(count) if item=='evolution' else item
                    out.append(dict(name=name,items=[item],policy=policy,types=count))
    else:
        for items in itertools.combinations(c['ACCESSORIES'],2):
            for policy in (c['HEART_POLICIES'] if 'heart' in items else ['heal']):
                for count in (c['COMBO_PROJECTILE_TYPE_COUNTS'] if 'evolution' in items else [4]):
                    name='+'.join(items)+(':'+policy if 'heart' in items else '')+(':types'+str(count) if 'evolution' in items else '')
                    out.append(dict(name=name,items=list(items),policy=policy,types=count))
    return out

def weights(c):
    def sigmoid(x):return 1/(1+math.exp(-max(-700,min(700,x))))
    plateau=c['SIGMOID_PLATEAU_START'];mid=c['SIGMOID_MIDPOINT'];slope=c['SIGMOID_STEEPNESS']
    values={n:1. if c['WEIGHT_MODE']=='uniform' or n>=plateau else sigmoid(slope*(n-mid))/sigmoid(slope*(plateau-mid)) for n in range(c['HIT_COUNT_MIN'],c['HIT_COUNT_MAX']+1)}
    total=sum(values.values())
    return {n:v/total for n,v in values.items()}

def build_trial(c,dataset,n,seed):
    fixed=dataset=='fixed';fps=c['FPS']
    duration=round(c['FIXED_DURATION_SECONDS']*fps) if fixed else random.Random(c['RANDOM_DURATION_SEED']+n*1000+seed).randint(round(c['RANDOM_DURATION_MIN_SECONDS']*fps),round(c['RANDOM_DURATION_MAX_SECONDS']*fps))
    r=random.Random(c['FIXED_EVENT_SEED' if fixed else 'RANDOM_EVENT_SEED']+n*1000+seed)
    gap=c['MIN_ATTACK_GAP_TICKS']
    times=[v+gap*i for i,v in enumerate(sorted(r.randrange(duration-gap*(n-1)) for _ in range(n)))]
    roll_values=[r.random()<c['DEBUFF_PROBABILITY'] for _ in times]
    extra=random.Random(c['FIXED_EXTRA_SEED' if fixed else 'RANDOM_EXTRA_SEED']+n*1000+seed)
    defense=extra.randint(c['DEFENSE_MIN'],c['DEFENSE_MAX'])
    contact_values=[extra.random()<1-c['PROJECTILE_PROBABILITY'] for _ in times]
    original_types=[extra.randrange(4) for _ in times]
    damage_values=[extra.randint(c['RAW_DAMAGE_MIN'],c['RAW_DAMAGE_MAX']) for _ in times]
    dd_values=[extra.random()<c['DEFENSE_DAMAGE_PROBABILITY'] for _ in times]
    fractions=random.Random(c['FIXED_TYPE_FRACTION_SEED' if fixed else 'RANDOM_TYPE_FRACTION_SEED']+n*1000+seed)
    uniforms=[(t+fractions.random())/4 for t in original_types]
    events={};rolls={};contacts={};dd={};u={}
    for i,tick in enumerate(times):
        # 같은 틱 후속 공격은 첫 공격이 주는 무적에 막히므로 최초 공격만 엔진에 전달.
        if tick in events:continue
        events[tick]=damage_values[i];rolls[tick]=roll_values[i]
        contacts[tick]=contact_values[i];dd[tick]=dd_values[i];u[tick]=uniforms[i]
    return duration,defense,events,rolls,dd,contacts,u

def worker(run_dir,dataset,n):
    manifest=json.loads((run_dir/'manifest.json').read_text(encoding='utf-8'))
    c=manifest['settings'];configs=manifest['configurations'];out=[]
    for seed in range(c['SAMPLES_PER_HIT_COUNT']):
        duration,defense,events,rolls,dd,contacts,u=build_trial(c,dataset,n,seed)
        for setup in configs:
            types={t:int(v*setup['types']) for t,v in u.items()}
            v=simulate(setup['items'],events,rolls,dd,contacts,types,defense,duration,setup['policy'],config=c)
            out.append(dict(dataset=dataset,hits=n,seed=seed,duration=duration/60,defense=defense,config=setup['name'],**v))
    return out

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run',action='store_true');parser.add_argument('--smoke',action='store_true')
    args=parser.parse_args()
    c={k:v for k,v in vars(settings).items() if k.isupper()}
    if args.smoke:
        c.update(HIT_COUNT_MIN=1,HIT_COUNT_MAX=3,SAMPLES_PER_HIT_COUNT=2,FIXED_DURATION_SECONDS=10,RANDOM_DURATION_MIN_SECONDS=8,RANDOM_DURATION_MAX_SECONDS=10,WORKERS=2)
    validate(c);configs=configurations(c);wgt=weights(c)
    tasks=[(ds,n) for n in wgt for ds in c['DATASETS']]
    records=len(tasks)*c['SAMPLES_PER_HIT_COUNT']
    print(f'Mode={c["MODE"]}, configurations={len(configs)-1}, trials/config={records}, total outcomes={records*len(configs)}',flush=True)
    print('Hit weights (%):', {n:round(v*100,4) for n,v in wgt.items()},flush=True)
    if args.dry_run:return
    digest=hashlib.sha256(json.dumps(c,sort_keys=True).encode()).hexdigest()[:8]
    run_dir=(ROOT/c['OUTPUT_DIRECTORY'])/(('smoke_' if args.smoke else '')+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'_'+digest)
    run_dir.mkdir(parents=True)
    manifest=dict(settings=c,configurations=configs,weights=wgt,smoke=args.smoke)
    (run_dir/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    (run_dir/'settings_snapshot.py').write_text((ROOT/'settings.py').read_text(encoding='utf-8'),encoding='utf-8')
    print('Output:',run_dir,flush=True)
    active=[];details=[];waiting=list(tasks);done=0
    while waiting or active:
        while waiting and len(active)<c['WORKERS']:
            ds,n=waiting.pop(0);path=run_dir/f'{ds}_{n}.pkl';log=path.with_suffix('.log').open('w',encoding='utf-8')
            proc=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--worker',str(run_dir),ds,str(n)],stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            active.append((proc,path,log))
        for task in active[:]:
            proc,path,log=task;code=proc.poll()
            if code is not None:
                log.close()
                if code:raise RuntimeError(path.with_suffix('.log').read_text(encoding='utf-8',errors='replace'))
                details.extend(pickle.loads(path.read_bytes()));active.remove(task);done+=1
                print(f'Completed {done}/{len(tasks)}',flush=True)
        time.sleep(.2)
    assert len(details)==records*len(configs)
    with (run_dir/'trials.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=details[0]);writer.writeheader();writer.writerows(details)
    rates={}
    for setup in configs:
        values=[r for r in details if r['config']==setup['name']]
        rates[setup['name']]=100*sum(wgt[n]*statistics.mean(r['alive'] for r in values if r['hits']==n) for n in wgt)
    baseline=rates.pop('baseline')
    summary=[dict(config=name,survival_pct=p,baseline_pct=baseline,uplift_pp=p-baseline,trials=records) for name,p in rates.items()]
    summary.sort(key=lambda r:-r['survival_pct'])
    with (run_dir/'ranking.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=summary[0]);writer.writeheader();writer.writerows(summary)
    for i,r in enumerate(summary,1):print(i,r,flush=True)
    print('Finished:',run_dir/'ranking.csv',flush=True)

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--worker':
        run_dir=Path(sys.argv[2]);ds=sys.argv[3];n=int(sys.argv[4])
        (run_dir/f'{ds}_{n}.pkl').write_bytes(pickle.dumps(worker(run_dir,ds,n)))
    else:main()
