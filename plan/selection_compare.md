# 선택 방식 비교표 틀

수정안의 세 선택 방식을 같은 조건에서 비교하는 표의 틀이다. 수치는 아직 없다. 실험을
돌린 뒤 `results/selection_compare.csv`에 채운다. 이 비교는 동결된 `plan_v0.6`의 H1~H3
판정에 들어가지 않고 확장(H4 또는 부록)으로 보고한다(`reviews/change_requests.md`의
수정안 검토 E).

방식의 정의는 `reviews/change_requests.md`의 수정안 검토와 11/23 점검,
`plan/solar_mining_tools.md`(`main` 4ed6518에 병합됨),
`plan/solar_selection_integration.md`(`goeun-solar-selection` ff79472)를 따랐다.
세 문서와 코드는 모두 `main`에 있다(11/25 병합). 수정안 원문과 다른 부분이
있으면 고친다.

## 1. 비교 대상

| `strategy` | 방식 | 선택 방법 | Solar 요청 | 전체 실행이 실패하면 |
|---|---|---|---|---|
| `rules` | 규칙 기반 선택 | 예산을 통과한 설정 중 Apriori, `pcy_small`, `pcy_large` 순으로 첫 번째를 고른다(결정 A, `mining_selection.baseline`) | 0회 | 재선택 없음 |
| `solar_once` | Solar 1회 선택 | `profile()`과 예산을 보고 Solar가 한 번 고른다 | 1회 | 재선택 없음 |
| `solar_pilot` | Solar 시험 집계·재선택 | Solar가 `pilot()`을 한 번까지 요청하고 `choose`로 고른다 | 최대 4회 | 한 번 다시 고른다 |

- 세 방식 모두 `src/mining_job.py`의 `MiningJob`을 쓴다. 설정은 `apriori`,
  `pcy_small`(65,521 버킷), `pcy_large`(1,048,573 버킷)이다.
- Solar 오류, 시간 초과, 잘못된 선택이 이어지면 규칙 기반 설정으로 넘어간다
  (`selected` 이벤트의 `source`가 `rules_fallback`). 예산 안에 드는 설정이 없으면 실패한다.

## 2. 조건 (행)

행 하나는 `strategy` × 조건 × 반복 하나다.

| 조건 | 쓸 값 |
|---|---|
| `dataset` (입력) | I0: 1년 차 전체(`y1`, 19,743건). I1: 2년치 전체(`all`, 38,700건)(결정 B) |
| `support` | 0.01. 조건 B0.25, B0.25-all에서는 0.0025(0.25%) |
| `memory_budget_bytes` (예산) | 아래 조건 표 |
| `repeat` | 5회. `scripts/run_selection_compare.py`의 기본값이다 |

지지도 1%에서 I0의 모델 메모리 추정치는 Apriori 1,015,312 B, `pcy_small` 2,935,207 B,
`pcy_large` 4,194,292 B다(`main` 4ed6518 코드로 계산, 후보 수는 `exact`). 예산은 이 세
값 사이에서 정한다.

| 지지도 | 예산 | 범위 | 후보 설정 | 보려는 것 |
|---|---|---|---|---|
| 1% | B0 | 4,194,292 B 이상(11/23 측정은 64 MiB) | 셋 | 세 설정 중에서 고르는 차이 |
| 1% | B1 | 2,935,207 B 이상 4,194,292 B 미만 | 둘(`apriori`, `pcy_small`) | 예산이 `pcy_large`를 가려낼 때의 차이 |
| 0.25% | B0.25 | 6 MiB(6,291,456 B) | 하나(`pcy_large`) | PCY가 메모리 모델에서 유리해지는 경우(이슈 #5). 입력은 I0이다 |
| 0.25% | B0.25-all | 6 MiB(6,291,456 B) | 하나(`pcy_large`) | B0.25와 같고 입력만 I1이다 |

후보가 하나뿐인 예산(지지도 1%에서 1,015,312 B 이상 2,935,207 B 미만)에서는 세 방식이
같은 설정을 고르므로 시간 차이만 남는다.

B0.25의 추정치는 I0가 Apriori 8,229,624 B, `pcy_small` 21,344,227 B, `pcy_large`
4,194,292 B다. I1은 Apriori 10,039,680 B, `pcy_small` 27,411,247 B, `pcy_large`
4,194,292 B다. 둘 다 `pcy_large`만 예산 안에 들어간다. 조건 이름 B0.25와 B0.25-all은
`scripts/run_selection_compare.py`를 따른다.

## 3. 열

| 열 | 뜻 | 가져오는 곳 |
|---|---|---|
| `selected` | 고른 설정 | `selected` 이벤트의 `setting` |
| `source` | 누가 골랐는가 | `selected` 이벤트의 `source`(`rules`, `solar`, `rules_fallback`) |
| `pairs_ok` | 빈발 쌍이 기준 결과와 같은가 | `run(selected)`의 빈발 쌍과 빈도가 세 설정 공통 결과와 같은지 |
| `best_ok` | 최선 선택인가 | 예산을 통과한 설정 중 집계 시간이 가장 짧은 것을 골랐는지. 설정별 시간은 같은 실행에서 설정을 고정해 돌린 행(`fixed:<설정>`)의 집계 시간 중앙값이다 |
| `t_profile_s` | 통계 시간 | `profile()` |
| `t_pilot_s` | 표본 집계 시간 | `pilot` 이벤트 `result`의 `elapsed_s`. 없으면 0 |
| `t_select_s` | 선택 시간 | 작업 `stats`의 `select_seconds`. `profile()`이 끝난 뒤부터 설정을 확정할 때까지다. Solar 요청과 표본 집계 시간을 포함하고, `t_profile_s`는 포함하지 않는다 |
| `t_mining_s` | 전체 집계 시간 | `run(selected)` |
| `t_pcy_pass1_s` | PCY 1차 패스 | 상품 빈도 집계, 상품 ID 변환, 해시 버킷 집계 |
| `t_pcy_pass2_s` | PCY 2차 패스 | 후보 쌍 필터링과 빈도 집계, 빈발 쌍 결과 생성 |
| `t_total_s` | 작업 총 시간 | 접수부터 결과까지. `profile()`을 포함한다 |
| `mem_model_bytes` | 모델 메모리 | `profile()`의 `settings[selected]["modeled_memory_bytes"]`. `n_candidates_estimate`를 근사한 경우(`candidate_count_method`가 `exact`가 아님)에는 예산 판정에 쓴 `modeled_memory_upper_bound_bytes`를 함께 적는다 |
| `mem_peak_bytes` | 실제 최대 메모리 | 집계 프로세스의 최대 상주 메모리로, 작업 `stats`의 `peak_rss_bytes`다. 기준 PC에서만 잰다(결정 D). Windows에서는 비어 있다 |
| `n_solar_calls` | Solar 요청 수 | `chat()` 호출 수 |
| `n_pilots` | 표본 집계 수 | `pilot` 이벤트 수 |
| `failures` | 실패 원인 | 4절 분류. 없으면 비워 둔다 |
| `job_id` | 작업 번호 | 실험용 작업 저장소(`data/jobs/selection_compare/jobs.sqlite`)의 번호다. 화면이 쓰는 저장소와 다르다 |
| `run_at`, `commit`, `solar_model`, `python`, `machine` | 실행 정보 | 실행 시각, 코드 커밋(커밋하지 않은 변경이 있으면 `-dirty`), 요청한 Solar 모델, Python 버전, 운영체제와 CPU 종류. 한 번의 실행에서 모든 행이 같다 |

- 반복마다 세 방식을 차례로 돌리고, 시작하는 방식을 반복마다 바꾼다. Solar 응답 시간이
  실행 도중에 변해도 한 방식에 몰리지 않는다.
- Solar를 쓰는 방식이 있는데 `UPSTAGE_API_KEY`가 없으면 스크립트는 시작할 때 멈춘다.
- 시간은 기준 PC에서 잰다(C). 반복의 중앙값을 쓰고 범위를 괄호에 적는다(`timings.csv`와
  같다).
- PCY 패스별 시간은 전체 집계 시간에 포함되며, 비트맵 준비와 후보 공간 진단은
  전체 집계 시간에만 들어간다. Apriori 행은 두 열을 비워 둔다.
- `t_total_s`는 `t_profile_s + t_select_s + t_mining_s`에 서버 오버헤드(대기열 대기,
  프로세스 시작)를 더한 것이다. `t_select_s`에 `t_pilot_s`가 들어 있으니 따로 더하지 않는다.

## 4. 실패 원인

| 값 | 뜻 | 보이는 곳 |
|---|---|---|
| `no_feasible` | 예산 안에 드는 설정이 없다 | `failed` |
| `invalid_call` | Solar가 없는 설정, 예산을 넘는 설정, 쓸 수 없는 `pilot`을 요청했다 | `invalid_tool_call` |
| `no_selection` | Solar가 선택을 돌려주지 않았다. 4턴 안에 유효한 선택이 없었다 | `fallback` |
| `solar_error` | Solar 요청이 HTTP 오류로 끝났다 | `fallback` |
| `solar_unreachable` | Solar에 닿지 못했거나 시간이 초과됐다(요청당 120초, 최대 3회 시도) | `fallback` |
| `deadline` | 작업 `deadline`을 넘겼다 | 서버 |
| `run_failed` | 전체 집계 프로세스가 실패했다 | `reselection` |

- `failures`에는 한 행에서 생긴 값을 모두 적는다(예: `invalid_call,run_failed`).
- `solar_error`, `solar_unreachable`, `deadline`은 평소에는 나오지 않으므로 따로 흉내 내어
  돌린다(`MiningSelector`의 `chat`에 실패하는 함수를 넣거나 잘못된 키, 짧은 `deadline`을
  쓴다). 그 행에는 조건에 `injected`를 적어 구분한다.
- 11/25 기준으로 `scripts/run_selection_compare.py`는 흉내 실패 행을 만들지 않는다. 서버는
  `deadline`을 저장만 하고 적용하지 않아서 `deadline` 값은 나오지 않는다. 이 둘을 실험에서
  뺄지는 팀이 정한다.

## 5. 빈 표

요약표는 입력 × 예산마다 한 장씩이다. 아래는 I0 × B0의 틀이고, 칸은 실험 뒤 채운다.

| 행 | `selected`(반복별) | `source` | `pairs_ok` | `best_ok` | `failures` |
|---|---|---|---|---|---|
| `rules` | | | | | |
| `solar_once` | | | | | |
| `solar_pilot` | | | | | |

| 행 | `t_profile_s` | `t_pilot_s` | `t_select_s` | `t_mining_s` | `t_total_s` | `mem_model_bytes` | `mem_peak_bytes` | `n_solar_calls` | `n_pilots` |
|---|---|---|---|---|---|---|---|---|---|
| `rules` | | | | | | | | | |
| `solar_once` | | | | | | | | | |
| `solar_pilot` | | | | | | | | | |

## 6. 결정과 남은 것

결정 내용은 `reviews/h4_progress.md`의 결정 표에 있다.

| 항목 | 바뀐 곳 | 내용 |
|---|---|---|
| A 규칙 기반 선택 정의 | 1절 `rules` 행 | 결정(11/24). 예산을 통과한 설정 중 Apriori, `pcy_small`, `pcy_large` 순으로 첫 번째를 고른다(`mining_selection.baseline`) |
| B 큰 입력 | 2절 `dataset` 행 | 결정(11/24). 2년치 전체 38,700건을 쓴다. 서버 데이터셋 이름은 `all`이다. 11/23 측정에서 `profile()`이 0.39초라, I0에서는 선택 비용이 집계 절감보다 클 수 있다 |
| C 시간의 기준 PC | 3절 시간 열 | 결정(11/20). 기준 PC 값으로 쓴다 |
| D 실제 최대 메모리 측정법 | 3절 `mem_peak_bytes` 행 | 결정(11/24). 기준 PC에서만 잰다. 집계 프로세스가 표준 라이브러리 `resource`로 자기 최대 상주 메모리를 기록한다. Windows에서는 값이 비어 있다 |
| 반복 수 | 2절 `repeat` 행 | 5회. `scripts/run_selection_compare.py`의 기본값이다 |

채우기 전에 필요했던 것은 11/24에 갖춰졌다.

- Solar 요청 수: 작업 `stats`의 `n_solar_calls`, `n_pilots`로 기록된다.
- 서버: `src/jobs.py`에 작업 서버가 있고 `/api/jobs` 경로로 접수한다. `t_total_s`는 서버를 통한 실행에서 잰다.
- `deadline` 정할 때 쓸 값: `chat()` 한 번은 최악의 경우 363초 걸린다(120초 × 3회 시도 +
  대기 3초). `solar_pilot`은 요청이 여러 번이다.
