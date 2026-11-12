"""여기를 수정한 뒤 `python run_simulation.py` 실행.

이 파일은 새 통합 실행기 전용입니다. 과거 실험 스크립트/CSV는 당시 기록으로 보존합니다.
설정 변경은 기존 결과 파일을 바꾸지 않습니다. 실행마다 새 결과 폴더를 만듭니다.
기존 모델의 근사/생략 사항은 FINAL_ASSUMPTIONS_KO.md를 참고하세요.
"""

# ── 플레이어 기본값 ──────────────────────────────────────────────
PLAYER_MAX_HP = 725              # 비교 장신구 착용 전의 최종 최대 HP(statLifeMax2).
MAX_LIFE1 = 600                  # statLifeMax. 성배는 이 값의 25%를 추가(현재 +150).
MAX_MANA = 380                  # 기록용. 루멘 제외 상태에서는 마나 연동 효과가 없어 결과에 영향 없음.
START_HP_FRACTION = 1.0          # 시작 HP 비율. 1.0=풀피, 0.5=반피.
DEFENSE_MIN = 118                # 전투마다 추첨할 기본 방어력의 최솟값(양끝 포함).
DEFENSE_MAX = 154                # 장신구의 추가 방어력은 엔진에서 별도로 더함.
BASE_DR = 0.10                   # 기본 DR. 0.10=10%. 장신구 DR은 더한 뒤 방어력 손상 반영.
DEFENSE_EFFECTIVENESS = 1.0      # 방어력 1당 원본 피해 감소량. 현재 요청한 100%=1.0.
MOVING = True                    # True=이동 중 자연 체젠, False=수평 정지 계수.
FOOD_REGEN_PENALTY = False       # True=음식 부족 체젠 페널티 50%. 음식의 다른 능력치는 모델에 없음.
INITIAL_REGEN_TIME_TICKS = 3600   # 자연 체젠 타이머 초기값. 이후 피격/디버프로 초기화됨.
SPONGE_START_FULL = True         # True=보호막 완충 시작, False=8초 충전 대기부터 시작.
HEART_START_FULL = False         # 심장 게이지. 기본은 보스전 시작 시 빈 게이지.

# ── 난이도·피해·공격 빈도 ───────────────────────────────────────
DIFFICULTY_LABEL = "Master Death" # 결과에 적는 이름. 이것만 바꿔도 수치가 자동 변경되지는 않음.
RAW_DAMAGE_MIN = 400             # 방어력/DR 적용 전 원본 피해의 최솟값.
RAW_DAMAGE_MAX = 600             # 매 공격 정수 균등 난수. 난이도 피해 배율을 다시 곱하지 않음.
PROJECTILE_PROBABILITY = 0.75     # 투사체 확률. 나머지 25%는 접촉 공격.
HIT_COUNT_MIN = 1                # 전투 전체의 공격 기회 수. 실제 피격 횟수와 다를 수 있음.
HIT_COUNT_MAX = 15
MIN_ATTACK_GAP_TICKS = 40         # 최소 공격 간격. 0이면 동시/초근접 공격도 가능(아래 주의).
# 0으로 설정하면 같은 틱에 여러 공격이 올 수 있습니다. 입력은 리스트로 유지하고,
# 기본 무적40틱/장신구 무적에 의해 같은 틱의 후속 공격은 무시하도록 처리합니다.

# ── 전투시간과 표본 ─────────────────────────────────────────────
FIXED_DURATION_SECONDS = 270     # 고정 시간 세트: 4분30초.
RANDOM_DURATION_MIN_SECONDS = 180 # 랜덤 시간 세트: 3분~4분30초, 틱 단위 균등 추첨.
RANDOM_DURATION_MAX_SECONDS = 270
SAMPLES_PER_HIT_COUNT = 100      # 시간 세트 하나당/공격 횟수 하나당 표본. 기본 구성당 3000회.
DATASETS = ("fixed", "random")   # 둘 다 쓰면 각각 같은 비중. 하나만 남겨도 됨.

# ── 디버프와 방어력 손상 ────────────────────────────────────────
DEBUFF_PROBABILITY = 0.50        # HP 피격마다 가상 디버프를 부여할 확률.
DEBUFF_DPS = 25                  # 디버프의 최종 HP/초. 방어력/DR/데스 추가 배율을 곱하지 않음.
DEBUFF_DURATION_SECONDS = 3      # 재적용 시 시간만 갱신. 중첩하지 않음.
DEFENSE_DAMAGE_PROBABILITY = 0.50 # 공격의 방어력 손상 가능 확률. 코어의 자체 강제 효과는 별도.
DEFENSE_DAMAGE_RATIO = 0.3333    # 원본-실제 피해 중 방어력 손상으로 넘기는 비율.
DEFENSE_DAMAGE_FLOOR = 24        # 현재 마스터 데스/문로드 이후의 표준 방어력 손상 최소치.
DD_RECOVERY_BASE_TICKS = 60      # 손상마다 더하는 회복기간. 60틱=1초.
DD_RECOVERY_MAX_TICKS = 900      # 누적 회복기간 상한. 900틱=15초.
DD_DELAY_AFTER_IMMUNITY_TICKS = 10 # 무적이 끝나고 복구 시작까지 기다리는 시간.

# ── 회복 정책 ───────────────────────────────────────────────────
POTION_HEAL = 300                # 0이면 물약 사용 안 함. HP 회복량. 성배의 출혈 제거량도 이 값의 50%로 연동.
POTION_TRIGGER_MISSING_HP = 300 # 잃은 체력이 이 값 이상이고 쿨다운이 끝났으면 즉시 마심.
POTION_COOLDOWN_SECONDS = 60     # 일반 물약 쿨다운. 성배는 이 값의75%.
POTION_START_READY = True
HEART_HEAL_TRIGGER_MISSING_HP = 180 # 심장 회복형을 쓸 최소 잃은 HP. 나노머신 충전도 필요.
ABSORBER_AURA_STAY_SECONDS = 30  # 장판 안 체류시간 0~30초. 버프는 체류시간+10초로 근사.

# ── 비교 대상 ───────────────────────────────────────────────────
MODE = "single"                # "single"=최신 단독 비교, "combos"=칼라 장신구2개 조합.
ACCESSORIES = (                 # 루멘은 포함하지 않음. 아래 영문 ID는 바꾸지 말고 항목 삭제/복원.
    "sponge", "chalice", "rampart", "radiance", "core", "heart", "evolution", "absorber", "nebulous",
)
HEART_POLICIES = ("heal", "parry") # 회복형/공격1틱 전 완벽한 예측 패링형을 별도 비교.
PROJECTILE_TYPE_COUNTS = (2, 3, 4, 5, 6, 7, 8) # 단독 에볼루션: 종류별 별도 순위, 각 종류 균등 출현.
COMBO_PROJECTILE_TYPE_COUNTS = (4,) # 조합 실험 기본은4종. 늘리면 에볼루션 포함 조합 수도 증가.

# ── 집계 가중치 ─────────────────────────────────────────────────
WEIGHT_MODE = "sigmoid_plateau" # "uniform"으로 바꾸면 모든 공격 횟수 동일 비중.
SIGMOID_MIDPOINT = 4.0           # S자 곡선 중심. 4회에서 상대 가중치가 절반 부근.
SIGMOID_STEEPNESS = 1.0          # 클수록 가파르게 증가. 0보다 커야 함.
SIGMOID_PLATEAU_START = 7        # 이 횟수부터 동일한 최대 상대 가중치.

# ── 실행·재현성 ─────────────────────────────────────────────────
WORKERS = 4                     # 동시에 실행할 Python 프로세스 수. PC가 버벅이면1~2로 낮추기.
OUTPUT_DIRECTORY = "results_current" # 실행할 때마다 이 폴더 아래에 새 하위 폴더 생성.
FIXED_EVENT_SEED = 810000        # 아래 시드는 바꾸지 않으면 같은 입력을 재현.
RANDOM_EVENT_SEED = 1810000
FIXED_EXTRA_SEED = 910000
RANDOM_EXTRA_SEED = 1910000
RANDOM_DURATION_SEED = 1010000
FIXED_TYPE_FRACTION_SEED = 2910000
RANDOM_TYPE_FRACTION_SEED = 3910000
FPS = 60                        # 게임 기준 상수. 실행기는60만 허용합니다.

RAMPART_HONEY_ENABLED = True # 성벽 피격 후300틱 꿀: 체젠+1HP/s, 음수체젠 완화, 자연체젠 타이머+2/틱.
