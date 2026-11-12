"""통합 실행기의 회귀·설정 반영 확인. 실행: python verify_current.py"""
from combo_sim import simulate as historical
from current_engine import simulate
from run_simulation import build_trial,configurations,validate,weights
import settings

def main():
    c={k:v for k,v in vars(settings).items() if k.isupper()}
    validate(c)
    # Defaults must reproduce the prior simulation engine for exactly the same input.
    checked=0
    for n,seed in [(1,3),(3,6),(5,14),(8,25),(12,48),(15,90)]:
        duration,defense,events,rolls,dd,contacts,u=build_trial(c,'fixed',n,seed)
        for setup in configurations(c):
            types={t:int(v*setup['types']) for t,v in u.items()}
            if 'nebulous' in setup['items']:continue
            a=historical(setup['items'],events,rolls,dd,contacts,types,defense,duration,setup['policy'])
            legacy=dict(c,RAMPART_HONEY_ENABLED=False,POTION_TRIGGER_MISSING_HP=(c['PLAYER_MAX_HP']+(int(c['MAX_LIFE1']*.25) if 'chalice' in setup['items'] else 0))*.5)
            b=simulate(setup['items'],events,rolls,dd,contacts,types,defense,duration,setup['policy'],config=legacy)
            b.pop('revives')
            assert a==b,(setup['name'],n,seed,a,b)
            checked+=1
    # New potion boundary: 299 missing does not trigger; 300 does, for any max HP.
    for maximum in (725,875):
        for missing in (299,300):
            test=dict(c,PLAYER_MAX_HP=maximum,START_HP_FRACTION=(maximum-missing)/maximum,INITIAL_REGEN_TIME_TICKS=0)
            result=simulate([], {},{},{},{},{},130,1,config=test)
            assert result['potions']==int(missing>=300),result
    # Honey after one hit: 1HP/s flat and faster natural regen, or 3HP/s less DOT.
    test=dict(c,POTION_HEAL=0,INITIAL_REGEN_TIME_TICKS=0)
    for dot in (False,True):
        args=(['rampart'],{0:400},{0:dot},{0:False},{0:False},{0:0},130,180)
        enabled=simulate(*args,config=dict(test,RAMPART_HONEY_ENABLED=True))
        disabled=simulate(*args,config=dict(test,RAMPART_HONEY_ENABLED=False))
        assert enabled['hp']>disabled['hp'],(enabled,disabled)
    # Editing core player values must affect the calculation, not merely metadata.
    changed=dict(c,PLAYER_MAX_HP=1000,MAX_LIFE1=800,BASE_DR=.2,POTION_HEAL=0)
    v=simulate([], {0:500},{0:False},{0:False},{0:False},{0:0},100,1,config=changed)
    assert v['hp']==680,v
    v=simulate(['chalice'], {},{},{},{},{},100,1,config=changed)
    assert v['hp']==1200,v
    changed['DEFENSE_EFFECTIVENESS']=.5
    v=simulate([], {0:500},{0:False},{0:False},{0:False},{0:0},100,1,config=changed)
    assert v['hp']==640,v
    # Same-frame input generation must not silently use the last attack instead of first.
    dense=dict(c,MIN_ATTACK_GAP_TICKS=0,FIXED_DURATION_SECONDS=1,HIT_COUNT_MAX=1000)
    validate(dense)
    duration,defense,events,rolls,dd,contacts,u=build_trial(dense,'fixed',1000,0)
    assert len(events)<=60 and set(events)==set(rolls)==set(dd)==set(contacts)==set(u)
    assert abs(sum(weights(c).values())-1)<1e-12
    assert len(configurations(dict(c,MODE='combos')))==45
    print(f'PASS: {checked} default regression cases; HP/MAXLIFE1/DR/defense settings; dense attacks; weights; combos.')

if __name__=='__main__':main()
