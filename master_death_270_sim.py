from bisect import bisect_right
"""Calamity original accessory comparison; stdlib only, seeded paired hit schedules.
Incoming damage is AFTER shared defenses, BEFORE accessory-specific effects.
Flat background regeneration substitutes for the game's dynamic regeneration.
Not a full Terraria combat simulator. See assumptions.json.
"""
import random, math, csv, json, statistics
from pathlib import Path

ROOT = Path(__file__).parent
FPS = 60
DURATION = 270
RUNS = 80

def schedule(damage, interval, seed):
    r = random.Random(seed)
    events = {}
    t = 1.0
    while t < DURATION:
        events[round(t*FPS)] = round(damage*r.uniform(.85,1.15))
        t += max(.8, interval*r.uniform(.75,1.25))
    return events

def simulate(kind, events, regen, potion, base_hp=1000, shared_stone=False, natural_share=0, fixed_iframes=False, debuff_rolls=None, moving=True, base_defense=100, contacts=None, projectile_types=None):
    maximum = base_hp+(150 if kind=='chalice' else 0)
    hp = maximum
    shield, recharge_delay, recharge_fraction = 120, 0, 0.0
    bleed, bleed_fraction = 0.0, 0.0
    potion_ready, potions, absorbed, erased = 0, 0, 0, 0.0
    minimum = hp
    healed = 0.0
    lumen_shield=0.0
    lumen_end=-1
    lumen_ready=0
    lumen_cd_end=0
    rampart_ready=0
    regen_time=3600
    regen_count=0
    debuff_end=-1
    reference_debuff_end=-1
    had_debuff=False
    dot_prevented=0.0
    heart=kind in ('heart_heal','heart_parry')
    nano_charge=0
    nano_active=False
    nano_active_remaining=0
    nano_pause=0
    nano_uses=0
    dd_total=0
    dd_remaining=0
    dd_duration=60
    dd_delay=0
    core_pool=0
    core_immune_end=0
    evo_ready=0
    evo_immune_end=0
    evo_type=-1
    last_attack=max(events,default=-1)
    cooldown = (45 if kind=='chalice' or shared_stone else 60)*FPS
    for tick in range(DURATION*FPS):
        if heart:
            if not nano_active and nano_charge>=1800:
                activate=(maximum-hp>=180) if kind=='heart_heal' else (tick+1 in events or (tick>last_attack and maximum-hp>=180))
                if activate:
                    nano_active=True
                    nano_active_remaining=120
                    nano_charge=0
                    nano_uses+=1
            if nano_active and tick%2==1:
                recovery=min(maximum-hp,3)
                hp+=recovery
                healed+=recovery
            if nano_pause>0:
                nano_pause-=1
            elif nano_active:
                nano_active_remaining-=1
                if nano_active_remaining<=0:
                    nano_active=False
            else:
                nano_charge=min(1800,nano_charge+1)
        if kind=='core' and dd_total:
            if tick>=core_immune_end:
                if dd_delay>0:dd_delay-=1
                else:dd_remaining=max(0,dd_remaining-1)
                if dd_remaining==0:dd_total=0
        if kind=='core' and core_pool>0 and tick%6==0:
            recovery=min(maximum-hp,1)
            hp+=recovery
            healed+=recovery
            core_pool-=1
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
        if kind=='lumen' and lumen_end>=0 and tick>=lumen_end:
            lumen_cd_end=tick+int(max(15,(1-lumen_shield/500)*75)*60)
            lumen_ready=lumen_cd_end
            lumen_shield=0
            lumen_end=-1
        if events.get(tick,0) and debuff_rolls and debuff_rolls.get(tick,False):
            reference_debuff_end=tick+180
        before_hit=hp
        unmitigated=events.get(tick,0)
        damage=int(unmitigated*.9)
        if damage:
            if kind=='sponge':
                damage=max(1,int(unmitigated*(.8 if shield else .9)))
                blocked=min(shield,damage)
                absorbed+=blocked+int(unmitigated*.9)-damage
                shield-=blocked
                hp-=damage-blocked
                recharge_delay=480
            elif kind=='lumen':
                if lumen_end>=0 or tick>=lumen_ready:
                    if lumen_end<0:
                        lumen_shield=500
                        lumen_end=tick+181
                    cost=math.ceil(damage*.9)
                    lumen_shield-=cost
                    actual=0 if lumen_shield>=0 else math.ceil(-lumen_shield/.9)
                    absorbed+=damage-actual
                    hp-=actual
                    if lumen_shield<=0:
                        lumen_shield=0
                        lumen_end=-1
                        lumen_cd_end=tick+4500
                        lumen_ready=lumen_cd_end
                else:
                    hp-=damage
            elif kind=='rampart':
                if tick<rampart_ready:
                    absorbed+=damage
                else:
                    actual=int((unmitigated-8)*(.65 if hp<=maximum*.5 else .9))
                    absorbed+=damage-actual
                    hp-=actual
                    bonus=int(min(1,max(0,(1-hp/maximum)/.75))*30)
                    rampart_ready=tick+(40 if fixed_iframes else 80+bonus+(30 if actual>200 else 0))
            elif heart:
                actual=((unmitigated+base_defense)*(.5 if nano_active else 1)-(base_defense+20))*.9
                if contacts and contacts.get(tick,False):actual*=.85
                actual=max(1,int(actual))
                absorbed+=damage-actual
                hp-=actual
                nano_pause=60
            elif kind=='core':
                current_dd=int(dd_total*dd_remaining/dd_duration) if dd_duration else 0
                actual=int((unmitigated+min(base_defense,current_dd))*(1-.1*(1-min(base_defense,current_dd)/base_defense)))
                absorbed+=damage-actual
                hp-=actual
                current_def=max(0,base_defense-current_dd)
                shatter=int(current_def/2)
                standard=(unmitigated+base_defense-actual)*.3333
                if standard<current_def/2:
                    core_pool=max(core_pool,shatter)
                else:
                    shatter=max(24,round(standard))
                dd_total=min(base_defense,current_dd+shatter)
                dd_duration=min(900,dd_remaining+60)
                dd_remaining=dd_duration
                dd_delay=10
                core_immune_end=tick+40
            elif kind=='evolution':
                contact=contacts.get(tick,False) if contacts else False
                this_type=projectile_types.get(tick,0) if projectile_types else 0
                if tick<evo_immune_end:
                    absorbed+=damage
                elif not contact and tick>=evo_ready:
                    absorbed+=damage
                    evo_type=this_type
                    scalar=min(1,max(0,(damage-maximum*.05)/(maximum*.45)))
                    evo_ready=tick+int(5400*(.33+.67*scalar))
                    evo_immune_end=tick+80
                    regen_time=0
                else:
                    actual=round(damage*.75) if not contact and tick<evo_ready and this_type==evo_type else damage
                    absorbed+=damage-actual
                    hp-=actual
            elif kind=='radiance':
                hp-=damage
            elif damage>5:
                hp-=5
                bleed+=damage-5
            else:
                hp-=damage
        if damage and hp<before_hit:
            regen_time=0
            if debuff_rolls and debuff_rolls.get(tick,False):
                debuff_end=tick+180
        if hp<=0:
            return dict(alive=False,time=tick/FPS,hp=0,debt=bleed,potions=potions,absorbed=absorbed,erased=erased,healed=healed,dot_prevented=dot_prevented,nano_uses=nano_uses)
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
        # Vanilla natural regeneration, current Calamity item bonuses.
        # Equipment bonuses occur before UpdateBadLifeRegen.
        flat=4 if kind=='chalice' else 0
        natural_multiplier=1.0
        timer_bonus=0
        if kind=='radiance':
            flat+=round(8-6*hp/maximum)
            timer_bonus=1
            natural_multiplier=1.75
        if kind=='lumen' and tick<lumen_cd_end:
            flat+=round(6-4*hp/maximum)
            timer_bonus=1
            natural_multiplier=1.75
            if lumen_shield<=0 and hp<=maximum*.5:
                flat+=1
        regen_time+=timer_bonus
        afflicted=tick<debuff_end
        if afflicted:
            # Generic damaging debuff clears positive regen and natural timer.
            flat=-50
            regen_time=0
            if kind=='radiance':
                flat+=24

        elif had_debuff and kind=='radiance':
            regen_time+=900
        dot_prevented+=((25 if tick<reference_debuff_end else 0)-(13 if kind=='radiance' else 25 if afflicted else 0))/60 if afflicted else (25/60 if tick<reference_debuff_end else 0)
        had_debuff=afflicted
        regen_time+=1
        stages=bisect_right((300,600,900,1200,1500,1800,2400,3000,3600),regen_time)
        regen_time=min(regen_time,3600)
        natural=stages*(.5 if moving else 1.25)*natural_multiplier*(maximum/400*.85+.15)
        life_regen=flat+round(natural)
        regen_count+=life_regen
        if regen_count>=120:
            recovery=min(maximum-hp,regen_count//120)
            hp+=recovery
            healed+=recovery
            regen_count%=120
        elif regen_count<=-120:
            paid=(-regen_count)//120
            hp-=paid
            regen_count+=paid*120
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
            return dict(alive=False,time=tick/FPS,hp=0,debt=bleed,potions=potions,absorbed=absorbed,erased=erased,healed=healed,dot_prevented=dot_prevented,nano_uses=nano_uses)
    return dict(alive=True,time=DURATION,hp=hp,debt=bleed+bleed_fraction,potions=potions,absorbed=absorbed,erased=erased,healed=healed,dot_prevented=dot_prevented,nano_uses=nano_uses)

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
