import csv,json,statistics
from pathlib import Path
import settings
from run_simulation import build_trial,weights
from nebulous_engine import simulate
ROOT=Path(__file__).resolve().parent
c={k:v for k,v in vars(settings).items() if k.isupper()}
# Current DLL: 300 HP revival, ready initially, 90-second cooldown.
# Direct fatal Hurt clamps HP to zero before PreKill; no extra immunity/cleanse.
# DOT fatalities cost at most one HP here; reset to300 approximates that within1HP.
rows=[]
for n in range(1,16):
 for ds in ('fixed','random'):
  for seed in range(100):
   duration,defense,events,rolls,dd,contacts,u=build_trial(c,ds,n,seed)
   v=simulate(['nebulous'],events,rolls,dd,contacts,{t:int(x*4) for t,x in u.items()},defense,duration,config=c)
   rows.append(dict(dataset=ds,hits=n,seed=seed,**v))
 print(n,flush=True)
w=weights(c)
rate=sum(w[n]*statistics.mean(r['alive'] for r in rows if r['hits']==n) for n in w)*100
with (ROOT/'nebulous_trials.csv').open('w',newline='',encoding='utf-8-sig') as f:
 writer=csv.DictWriter(f,fieldnames=rows[0]);writer.writeheader();writer.writerows(rows)
old=list(csv.DictReader((ROOT/'sigmoid_types2_8_ranking.csv').open(encoding='utf-8-sig')))
print('OLD_FIELDS',old[0],flush=True)
result={'survival_pct':rate,'trials':len(rows),'mean_revives':statistics.mean(r['revives'] for r in rows),'per_hit':{n:statistics.mean(r['alive'] for r in rows if r['hits']==n)*100 for n in w},'settings':c}
(ROOT/'nebulous_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False),flush=True)
