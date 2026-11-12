# 칼라미티 장신구 생존 시뮬레이션

## 지금부터 수정하고 실행할 파일

1. **`settings.py`**: 플레이어·전투·회복 정책·집계 가중치. 한국어 주석 포함.
2. **`run_simulation.py`**: 위 설정을 읽는 통합 실행기.
3. **`current_engine.py`**: 효과 계산 엔진. 장신구 고유 계수를 바꾸려는 경우에만 수정.

Python3.10이상, 추가 패키지 설치 없이 실행합니다. 이 폴더에서 터미널을 열고:

```powershell
python run_simulation.py --dry-run
python run_simulation.py
```

첫 명령은 설정과 실행 규모만 확인합니다. 둘째 명령이 실제 실험입니다.
아주 작은 표본으로 작동을 확인하려면 `python run_simulation.py --smoke`를 사용하세요.
smoke는 실행 중에만 표본·전투시간을 줄이며 settings.py 자체를 바꾸지 않습니다.

## 자주 수정할 값

```python
PLAYER_MAX_HP = 725       # 장신구 제외 최종 최대HP
MAX_LIFE1 = 600           # 성배의+25% 기준; 현재150HP추가
DEFENSE_MIN = 118
DEFENSE_MAX = 154         # 전투마다 기본 방어력 난수
BASE_DR = 0.10            # 10%
RAW_DAMAGE_MIN = 400
RAW_DAMAGE_MAX = 600      # 방어력·DR 적용 전
FIXED_DURATION_SECONDS = 270
RANDOM_DURATION_MIN_SECONDS = 180
RANDOM_DURATION_MAX_SECONDS = 270
SAMPLES_PER_HIT_COUNT = 100
```

`MODE="single"`이 최신 단독 비교입니다. `MODE="combos"`로 바꾸면2개 조합을 실행합니다.
단독 에볼루션은 `PROJECTILE_TYPE_COUNTS`, 조합의 에볼루션은 `COMBO_PROJECTILE_TYPE_COUNTS`를 사용합니다.
심장은 `HEART_POLICIES`의 회복형/패링형을 따로 비교합니다.

`MAX_MANA`는 루멘 제외 모델에서는 기록용입니다. 값을 바꿔도 생존 결과가 달라지지 않습니다.
`DIFFICULTY_LABEL` 역시 이름이므로, 난이도를 바꾸려면 방어력 효율과 방어력 손상 최소치 등도 직접 지정해야 합니다.
모든 시간은 초 또는 주석에 적힌 틱 단위입니다. FPS는 게임 기준60으로 고정합니다.

## 결과와 재현성

- 매 실행마다 `results_current/날짜_설정해시/`를 새로 만듭니다.
- `manifest.json`: 실제 사용한 모든 설정, 구성, 가중치. **smoke의 실제 설정도 여기에 기록됩니다.**
- `settings_snapshot.py`: 편집한 원본 설정 파일의 사본.
- `ranking.csv`: 생존율·미착용 대비퍼센트포인트 증가량.
- `trials.csv`: 전투별 생존 여부,HP,물약 수 등.
- 로그와 작업별pickle은 중간 산출물입니다. 다른 사람에게 받은pickle은 불러오지 마세요.
- 설정을 바꾸면 **전체 입력과 기준선을 새로 계산**하며 과거CSV/캐시는 재사용하지 않습니다.
- 과거 실험CSV는 그대로 남습니다. 설정 파일만 편집해서 기존CSV가 갱신되지는 않습니다.

기본 설정은 최신 단독 실험과 같습니다: 루멘 제외,에볼루션2~8종 별도,1~15회,
시그모이드1~7회 상승/7~15회 동일 비중,두 전투시간 세트 각100회입니다.
미착용 포함17구성×3000전투=51,000개 결과를 새로 계산하므로 몇 분 걸릴 수 있습니다.
PC가 버벅이면 WORKERS를1~2로 낮추세요.

## 공개 저장소 구성

최신 실행 파일은 `settings.py`, `current_engine.py`, `run_simulation.py`입니다.
`verify_current.py`는 과거 모델 대비 회귀 검사와 물약 경계값·꿀 효과 검사를 수행합니다.

그 외 Python 파일은 이전 실험 코드입니다. 일부는 과거 CSV가 필요하며 settings.py를 사용하지 않습니다.
모드 DLL, 디컴파일 코드, 작업 캐시와 대용량 원시 결과는 공개 저장소에 포함하지 않습니다.

최신 순위는 `results/latest/ranking.csv`, 해당 실행 조건은 `results/latest/manifest.json`에 있습니다.
이 결과에는 성벽의 피격 후5초 꿀 효과와 손실HP300 물약 정책이 반영되어 있습니다.
모델의 가정·생략 사항은 `FINAL_ASSUMPTIONS_KO.md`를 참고하세요. 실제 게임 엔진을 실행한 검증이 아닙니다.

물약 조건은 `POTION_TRIGGER_MISSING_HP = 300`입니다.
성운의 코어 ID는 `nebulous`이며 단독·조합 실행에 포함할 수 있습니다.
