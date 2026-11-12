"""Calamity original accessory comparison; stdlib only, seeded paired hit schedules.
Incoming damage is AFTER shared defenses, BEFORE accessory-specific effects.
Flat background regeneration substitutes for the game's dynamic regeneration.
Not a full Terraria combat simulator. See assumptions.json.
"""
import random, math, csv, json, statistics
from pathlib import Path

ROOT = Path(__file__).parent
FPS = 60
DURATION = 180
RUNS = 80

def schedule(damage, interval, seed):
    r = random.Random(seed)
    events = {}
    t = 1.0
    while t < DURATION:
        events[round(t*FPS)] = round(damage*r.uniform(.85,1.15))
        t += max(.8, interval*r.uniform(.75,1.25))
    return events

def simulate(kind, events, regen, potion, base_hp=1000, shared_stone=False):
    maximum = base_hp*(1.25 if kind=='chalice' else 1)
    hp = maximum
    shield, recharge_delay, recharge_fraction = 120, 0, 0.0
    bleed, bleed_fraction = 0.0, 0.0
    potion_ready, potions, absorbed, erased = 0, 0, 0, 0.0
    minimum = hp
    healed = 0.0
    cooldown = (45 if kind=='chalice' or shared_stone else 60)*FPS
    for tick in range(DURATION*FPS):
        if kind=='sponge':
            if recharge_delay:
                recharge_delay -= 1
                if recharge_delay==0 and shield==0:
                    shield=1
            elif shield<120:
                recharge_fraction += .2
                pip = int(recharge_fraction+1e-9)
                shield=min(120,shield+pip)
                recharge_fraction -= pip
        damage=events.get(tick,0)
        if damage:
            if kind=='sponge':
                damage=max(1,int(damage*(.9 if shield else 1)))
                blocked=min(shield,damage)
                absorbed+=blocked+events[tick]-damage
                shield-=blocked
                hp-=damage-blocked
                recharge_delay=480
            elif damage>5:
                hp-=5
                bleed+=damage-5
            else:
                hp-=damage
        if hp<=0:
            return dict(alive=False,time=tick/FPS,hp=0,debt=bleed,potions=potions,absorbed=absorbed,erased=erased,healed=healed)
        if potion and tick>=potion_ready and hp<=maximum*.5:
            recovery=min(maximum-hp,potion)
            healed+=recovery
            hp+=recovery
            potions+=1
            potion_ready=tick+cooldown
            if kind=='chalice':
                clear=min(bleed,potion*.5)
                erased+=clear
                bleed-=clear
        recovery=min(maximum-hp,(regen+(2 if kind=='chalice' else 0))/FPS)
        healed+=recovery
        hp+=recovery
        if kind=='chalice':
            if bleed>5:
                loss=bleed/120
                bleed_fraction+=loss
                paid=int(bleed_fraction)
                hp-=paid
                bleed_fraction-=paid
                bleed-=loss
            elif bleed>0:
                hp-=int(bleed)+1
                bleed=bleed_fraction=0
        minimum=min(minimum,hp)
        if hp<=0:
            return dict(alive=False,time=tick/FPS,hp=0,debt=bleed,potions=potions,absorbed=absorbed,erased=erased,healed=healed)
    return dict(alive=True,time=DURATION,hp=hp,debt=bleed+bleed_fraction,potions=potions,absorbed=absorbed,erased=erased,healed=healed)

def main():
    rows=[]
    for regen in [0,5]:
        for potion in [0,300]:
            for damage,interval in [(100,20),(200,20),(200,10),(200,5),(400,5),(600,10)]:
                results={k:[] for k in ['sponge','chalice']}
                for seed in range(RUNS):
                    events=schedule(damage,interval,seed)
                    for k in results:
                        results[k].append(simulate(k,events,regen,potion))
                for k,values in results.items():
                    survivors=[v for v in values if v['alive']]
                    rows.append(dict(regen=regen,potion=potion,hit=damage,interval=interval,accessory=k,
                        survival_pct=100*len(survivors)/RUNS,
                        mean_survival_seconds=round(statistics.mean(v['time'] for v in values),2),
                        survivor_mean_hp=round(statistics.mean(v['hp'] for v in survivors),1) if survivors else '',
                        survivor_mean_bleed=round(statistics.mean(v['debt'] for v in survivors),1) if survivors else '',
                        mean_potions=round(statistics.mean(v['potions'] for v in values),2)))
    with (ROOT/'results.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    assumptions=dict(version='Installed Calamity 2.2.4 original DLL; no CAmod/asd patches',
        base_hp=1000,chalice_hp=1250,duration_seconds=DURATION,runs_per_scenario=RUNS,
        hits='Same seeded schedule per pair. Damage uniform +/-15%; interval uniform +/-25%; minimum 0.8 sec. Successful hits only.',
        defense='Hit values after common defense, before accessory-specific reduction. No common endurance. Sponge adds 10% reduction while shield positive.',
        regeneration='Constant HP/sec common regen 0 or 5, plus Chalice 2. Dynamic natural regen, defense damage, debuffs, knockback and adrenaline excluded.',
        potions='None or hypothetical 300 HP. Drink at <=50% HP if ready, initially ready. 60 sec cooldown Sponge;45 sec Chalice. No other philosopher stone. No other healing.',
        bleed='Per-frame exponential k=1/120; integral damage accumulator; flush when <=5; potion erases up to half nominal heal. Remaining bleed reported, never counted as prevented damage.',
        initial_state='Full HP, full Sponge shield120; recharge delay8 sec, recharge12/sec after first pip.',
        limitations='Approximate per-frame update order, regen float HP, rounding of reduced hits; not an in-game survival prediction. Equal scenario weights are not a universal win rate.')
    (ROOT/'assumptions.json').write_text(json.dumps(assumptions,ensure_ascii=False,indent=2),encoding='utf-8')
    print('regen potion hit interval | Sponge survival/time | Chalice survival/time')
    for i in range(0,len(rows),2):
        a,b=rows[i:i+2]
        print(f"{a['regen']:>5} {a['potion']:>6} {a['hit']:>3} {a['interval']:>8} | {a['survival_pct']:>5.1f}%/{a['mean_survival_seconds']:>6} | {b['survival_pct']:>5.1f}%/{b['mean_survival_seconds']:>6}")
if __name__=='__main__': main()
