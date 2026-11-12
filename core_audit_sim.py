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

def simulate(kind, events, regen, potion, base_hp=1000, shared_stone=False, natural_share=0, fixed_iframes=False, debuff_rolls=None, moving=True, base_defense=100, contacts=None, projectile_types=None, defense_damage_rolls=None, duration_ticks=16200, core_mode='actual'):
    if core_mode=='ideal_defense':kind='ideal_defense'
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
    metrics=dict(hits=0,core_heal=0,overheal=0,granted=0,not_stacked=0,dd_extra=0,short2=0,short7=0,eligible=0,not_eligible=0)
    previous_core_hit=-999999
    core_immune_end=0
    evo_ready=0
    evo_immune_end=0
    evo_type=-1
    last_attack=max(events,default=-1)
    total_defense=base_defense+(int(base_defense*.5) if kind=='ideal_defense' else 20 if heart else 8 if kind=='rampart' else 6 if kind=='absorber' else 0)
    immune_end=0
    absorber_buff_end=-1
    cooldown = (45 if kind=='chalice' or shared_stone else 60)*FPS
    for tick in range(duration_ticks):
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
        if dd_total:
            if tick>=immune_end:
                if dd_delay>0:dd_delay-=1
                else:dd_remaining=max(0,dd_remaining-1)
                if dd_remaining==0:dd_total=0
        if kind=='core' and core_pool>0 and tick%6==0:
            recovery=min(maximum-hp,1)
            hp+=recovery
            healed+=recovery
            core_pool-=1
            metrics['core_heal']+=recovery
            metrics['overheal']+=1-recovery
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
        source=events.get(tick,0)
        damage=0
        if source and tick>=immune_end:
            current_dd=int(dd_total*dd_remaining/dd_duration) if dd_duration else 0
            current_dd=min(total_defense,current_dd)
            current_def=max(0,total_defense-current_dd)
            endurance=.1
            if kind=='absorber' and tick<absorber_buff_end:endurance+=.05
            if kind=='sponge' and shield>0:endurance+=.1
            if kind=='rampart' and hp<=maximum*.5:endurance+=.25
            endurance*=max(0,1-current_dd/total_defense)
            incoming=source*(.5 if heart and nano_active else 1)
            damage=max(1,int(max(1,incoming-current_def)*(1-endurance)))
            if heart and contacts and contacts.get(tick,False):damage=max(1,int(damage*.85))
            contact=contacts.get(tick,False) if contacts else False
            this_type=projectile_types.get(tick,0) if projectile_types else 0
            cancelled=False
            if kind=='evolution' and not contact and tick>=evo_ready:
                baseline=max(1,int((source-base_defense)*.9))
                absorbed+=baseline
                evo_type=this_type
                scalar=min(1,max(0,(damage-maximum*.05)/(maximum*.45)))
                evo_ready=tick+int(5400*(.33+.67*scalar))
                immune_end=tick+80
                regen_time=0
                cancelled=True
            if not cancelled:
                if kind=='evolution' and not contact and tick<evo_ready and this_type==evo_type:
                    damage=max(1,int(damage*.75))
                actual=damage
                if kind=='core':
                    metrics['hits']+=1
                    metrics['dd_extra']+=actual-max(1,int((source-total_defense)*.9))
                    if previous_core_hit>=0:
                        metrics['short2']+=tick-previous_core_hit<120
                        metrics['short7']+=tick-previous_core_hit<420
                    previous_core_hit=tick
                if kind=='sponge':
                    blocked=min(shield,actual)
                    shield-=blocked
                    actual-=blocked
                    recharge_delay=480
                elif kind=='lumen' and (lumen_end>=0 or tick>=lumen_ready):
                    if lumen_end<0:
                        lumen_shield=500
                        lumen_end=tick+181
                    lumen_shield-=math.ceil(actual*.9)
                    actual=0 if lumen_shield>=0 else math.ceil(-lumen_shield/.9)
                    if lumen_shield<=0:
                        lumen_shield=0
                        lumen_end=-1
                        lumen_cd_end=tick+4500
                        lumen_ready=lumen_cd_end
                baseline=max(1,int((source-base_defense)*.9))
                absorbed+=baseline-actual
                if kind=='chalice' and actual>5:
                    bleed+=actual-5
                    hp-=5
                else:
                    hp-=actual
                if actual>0:
                    iframe=40
                    if kind=='rampart':
                        bonus=int(min(1,max(0,(1-hp/maximum)/.75))*30)
                        iframe=80+bonus+(30 if actual>200 else 0)
                    immune_end=tick+iframe
                    if kind=='absorber' and hp>0:
                        recovery=min(maximum-hp,int(actual*.05))
                        hp+=recovery
                        healed+=recovery
                    if heart:nano_pause=60
                    if kind=='core' or (defense_damage_rolls and defense_damage_rolls.get(tick,False)):
                        standard=max(0,source-actual)*.3333
                        if kind=='core' and standard<current_def/2:
                            shatter=int(current_def/2)
                            metrics['eligible']+=1
                            metrics['granted']+=shatter
                            metrics['not_stacked']+=min(core_pool,shatter)
                            if core_mode=='stack':core_pool+=shatter
                            elif core_mode=='instant':
                                recovery=min(maximum-hp,shatter) if hp>0 else 0
                                hp+=recovery
                                healed+=recovery
                                metrics['core_heal']+=recovery
                                metrics['overheal']+=shatter-recovery
                            else:core_pool=max(core_pool,shatter)
                        else:
                            if kind=='core':metrics['not_eligible']+=1
                            shatter=max(24,round(standard))
                        if core_mode=='no_forced_dd' and not (defense_damage_rolls and defense_damage_rolls.get(tick,False)):shatter=0
                        dd_total=min(total_defense,current_dd+shatter)
                        dd_duration=min(900,dd_remaining+60)
                        dd_remaining=dd_duration
                        dd_delay=10
        elif source:
            # Dodge/extended iframes also avoid the attack and its debuff.
            absorbed+=max(1,int((source-base_defense)*.9))
        if damage and hp<before_hit:
            regen_time=0
            if debuff_rolls and debuff_rolls.get(tick,False):
                debuff_end=tick+180
        if hp<=0:
            return dict(alive=False,time=tick/FPS,hp=0,debt=bleed,potions=potions,absorbed=absorbed,erased=erased,healed=healed,dot_prevented=dot_prevented,nano_uses=nano_uses,core_left=core_pool,metrics=metrics)
        if potion and tick>=potion_ready and hp<=maximum*.5:
            recovery=min(maximum-hp,potion)
            healed+=recovery
            hp+=recovery
            potions+=1
            potion_ready=tick+cooldown
            if kind=='absorber':
                absorber_buff_end=tick+2400
                debuff_end=-1
            if kind=='chalice':
                clear=min(bleed,potion*.5)
                erased+=clear
                bleed-=clear
        # Vanilla natural regeneration, current Calamity item bonuses.
        # Equipment bonuses occur before UpdateBadLifeRegen.
        flat=4 if kind=='chalice' else 0
        if kind=='absorber' and tick<absorber_buff_end:flat+=4
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
            return dict(alive=False,time=tick/FPS,hp=0,debt=bleed,potions=potions,absorbed=absorbed,erased=erased,healed=healed,dot_prevented=dot_prevented,nano_uses=nano_uses,core_left=core_pool,metrics=metrics)
    return dict(alive=True,time=duration_ticks/60,hp=hp,debt=bleed+bleed_fraction,potions=potions,absorbed=absorbed,erased=erased,healed=healed,dot_prevented=dot_prevented,nano_uses=nano_uses,core_left=core_pool,metrics=metrics)

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
