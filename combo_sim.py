"""Paired Calamity accessory model. No Lumen/CAmod accessories.
All item coefficients and common experimental assumptions carried from prior model.
Shield absorption precedes Chalice. OnHurt effects use Chalice's immediate5damage.
"""
from bisect import bisect_right

def simulate(items,events,rolls,dd_rolls,contacts,types,defense,duration,policy='heal'):
    sp='sponge' in items; ch='chalice' in items; ra='rampart' in items
    pu='radiance' in items; co='core' in items; he='heart' in items
    ev='evolution' in items; ab='absorber' in items
    maximum=725+(150 if ch else 0); hp=maximum
    total_defense=defense+20*he+8*ra+6*ab
    shield=120 if sp else 0; shield_delay=0; shield_partial=0.
    bleed=0.; bleed_partial=0.; regen_time=3600; regen_count=0
    debuff_end=-1; had_debuff=False; potion_ready=0; potions=0; aura_end=-1
    dd_total=0; dd_remaining=0; dd_duration=60; dd_delay=0; immune_end=0
    core_pool=0; core_healed=0; core_procs=0
    nano_charge=0; nano_active=False; nano_remaining=0; nano_pause=0; nano_uses=0
    evo_ready=0; evo_type=-1; last_attack=max(events,default=-1)
    end_time=duration/60
    for tick in range(duration):
        if he:
            if not nano_active and nano_charge>=1800:
                activate=(maximum-hp>=180) if policy=='heal' else (tick+1 in events or (tick>last_attack and maximum-hp>=180))
                if activate:
                    nano_active=True; nano_remaining=120; nano_charge=0; nano_uses+=1
            if nano_active and tick%2==1:hp=min(maximum,hp+3)
            if nano_pause>0:nano_pause-=1
            elif nano_active:
                nano_remaining-=1
                if nano_remaining<=0:nano_active=False
            else:nano_charge=min(1800,nano_charge+1)
        if dd_total and tick>=immune_end:
            if dd_delay>0:dd_delay-=1
            else:dd_remaining=max(0,dd_remaining-1)
            if dd_remaining==0:dd_total=0
        if co and core_pool>0 and tick%6==0:
            core_healed+=min(maximum-hp,1)
            hp=min(maximum,hp+1); core_pool-=1
        if sp:
            if shield_delay:
                shield_delay-=1
                if shield_delay==0 and shield==0:shield=1
            elif shield<120:
                shield_partial+=.2
                pip=int(shield_partial+1e-9)
                shield=min(120,shield+pip);shield_partial-=pip
        source=events.get(tick,0)
        if source and tick>=immune_end:
            current_dd=min(total_defense,int(dd_total*dd_remaining/dd_duration))
            current_def=max(0,total_defense-current_dd)
            endurance=.1+(.1 if sp and shield>0 else 0)+(.25 if ra and hp<=maximum*.5 else 0)+(.05 if ab and tick<aura_end else 0)
            endurance*=max(0,1-current_dd/total_defense)
            incoming=source*(.5 if he and nano_active and shield<=0 else 1)
            damage=max(1,int(max(1,incoming-current_def)*(1-endurance)))
            if he and contacts[tick]:damage=max(1,int(damage*.85))
            dodge=ev and not contacts[tick] and tick>=evo_ready
            if dodge:
                evo_type=types[tick]
                scalar=min(1,max(0,(damage-maximum*.05)/(maximum*.45)))
                evo_ready=tick+int(5400*(.33+.67*scalar))
                immune_end=tick+(120 if ra else 80);regen_time=0
            else:
                if ev and not contacts[tick] and tick<evo_ready and types[tick]==evo_type:
                    damage=max(1,int(damage*.75))
                actual=damage
                if sp:
                    blocked=min(shield,actual);shield-=blocked;actual-=blocked
                    shield_delay=480
                if actual<=0:
                    immune_end=tick+(85 if ra else 40)
                    if he:nano_pause=30
                else:
                    immediate=min(5,actual) if ch else actual
                    if ch:bleed+=actual-immediate
                    hp-=immediate;regen_time=0
                    if rolls[tick]:debuff_end=tick+180
                    iframe=40
                    if ra:
                        bonus=int(min(1,max(0,(1-hp/maximum)/.75))*30)
                        iframe=80+bonus+(30 if immediate>200 else 0)
                    immune_end=tick+iframe
                    if ab and hp>0:hp=min(maximum,hp+int(immediate*.05))
                    if he:nano_pause=60
                    if co or dd_rolls[tick]:
                        # Core's special minimum gate sees immediate HurtInfo damage;
                        # standard Chalice DD branch compensates for pending bleed.
                        gate_standard=max(0,source-immediate)*.3333
                        if co and gate_standard<current_def/2:
                            shatter=int(current_def/2)
                            core_pool=max(core_pool,shatter);core_procs+=1
                        else:
                            shatter=max(24,round(max(0,source-actual)*.3333))
                        dd_total=min(total_defense,current_dd+shatter)
                        dd_duration=min(900,dd_remaining+60);dd_remaining=dd_duration;dd_delay=10
        if hp<=0:
            return dict(alive=False,time=tick/60,hp=0,potions=potions,nano_uses=nano_uses,core_healed=core_healed,core_procs=core_procs)
        if tick>=potion_ready and hp<=maximum*.5:
            hp=min(maximum,hp+300);potions+=1;potion_ready=tick+(2700 if ch else 3600)
            if ab:aura_end=tick+2400;debuff_end=-1
            if ch:bleed=max(0,bleed-150)
        flat=4*ch+(round(8-6*hp/maximum) if pu else 0)+(4 if ab and tick<aura_end else 0)
        if pu:regen_time+=1
        afflicted=tick<debuff_end
        if afflicted:flat=-50+(24 if pu else 0);regen_time=0
        elif had_debuff and pu:regen_time+=900
        had_debuff=afflicted;regen_time+=1
        stages=bisect_right((300,600,900,1200,1500,1800,2400,3000,3600),regen_time)
        regen_time=min(regen_time,3600)
        regen_count+=flat+round(stages*.5*(1.75 if pu else 1)*(maximum/400*.85+.15))
        if regen_count>=120:hp=min(maximum,hp+regen_count//120);regen_count%=120
        elif regen_count<=-120:
            paid=(-regen_count)//120;hp-=paid;regen_count+=paid*120
        if ch:
            if bleed>5:
                loss=bleed/120;bleed_partial+=loss;paid=int(bleed_partial)
                hp-=paid;bleed_partial-=paid;bleed-=loss
            elif bleed>0:hp-=int(bleed)+1;bleed=bleed_partial=0
        if hp<=0:
            return dict(alive=False,time=tick/60,hp=0,potions=potions,nano_uses=nano_uses,core_healed=core_healed,core_procs=core_procs)
    return dict(alive=True,time=end_time,hp=hp,potions=potions,nano_uses=nano_uses,core_healed=core_healed,core_procs=core_procs)
