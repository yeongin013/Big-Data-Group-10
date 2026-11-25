# 담당자별 수정 요청 (2026-11-14)

근거: [`merge_review.md`](merge_review.md) (브랜치 병합 검토, 11/11)와 [`draft1_review.md`](draft1_review.md) (1차 리뷰)에서 아직 열려 있는 항목. 11/14 기준으로 `Hyeonseop`(f874e91)과 `goeun`(db57a5f)에는 11/11 이후 새 커밋이 없다. `yuchan-final`에는 11/14에 `dcd8756`이 올라왔다 (유찬 절 끝의 "11/14 커밋 `dcd8756` 검토" 참고).

진행 방법:

1. 각자 자기 브랜치에서 아래 항목을 고치고 푸시한다.
2. 고친 항목은 이 파일의 체크박스를 채우거나 PR 설명에 번호로 적는다.
3. 최영인이 `Hyeonseop` → `goeun` → `yuchan-final` 순서로 병합한다.
4. 병합 뒤 기준 수치(빈발 상품 713, 빈발 쌍 585, 규칙 189, Y2 유지 134/189, PCY 후보 1,238)가 그대로인지 확인한다.

## 11/17 점검 결과

세 브랜치에 수정 커밋이 올라왔다 (`Hyeonseop` f3c8216, `goeun` 38be000, `yuchan-final` 428a39e). 각 브랜치를 임시 worktree에서 읽고 테스트와 T2, T4, T5를 실행해 확인했다.

| 브랜치 | 판정 | 남은 것 |
|---|---|---|
| `Hyeonseop` | 병합 가능 | 4는 일부 반영(PR 설명에 시간 기록 없음), 6은 일부 반영(MMDS Example 6.1 대조 없음) |
| `goeun` | 병합 가능 | 5는 일부 반영(T6은 아직 구현 전), low 라우터 confidence·support 혼동 일부 남음 |
| `yuchan-final` | 보류 | 3(H3 파일 5개) 미반영, 6의 CPU 이름 미반영 |

- 세 브랜치 모두 테스트가 통과한다. `main`과도, 브랜치끼리도 충돌이 없다.
- 기준 수치가 유지된다: 빈발 상품 713, 빈발 쌍 62 / 585 / 4,364 / 26,111, 규칙 189, PCY 후보 1,238, 3개 조합 103. `h2.csv`는 `main`과 바이트 단위로 같다.
- `Hyeonseop`: 두 알고리즘을 같은 numpy 방식으로 맞추자 모든 support 수준에서 A-Priori가 PCY보다 2~4배 빨라졌다(1%에서 0.13초 대 0.42초). `main`의 `results/`는 PCY가 빠르다고 나온다. 병합 뒤 기준 PC에서 T2를 다시 잰다.
- `yuchan-final`: `t5_sensitivity.csv`는 브랜치 코드로 다시 만들어진다. `min_ci_cust_lo` 변화는 bootstrap을 100회에서 1,000회로 올린 결과다. `null_check.csv`의 20회는 1회 10초가 넘으면 seed를 줄이는 규칙(`null_model.py:77-78`) 때문이다. 기준 PC에서 다시 돌리면 100회가 된다. 그래서 요청 2와 10은 병합 뒤 재실행으로 갈음한다.
- 세 브랜치가 모두 `src/run_all.py`를 고친다. 병합한 뒤 `run_all` 전체를 한 번 돌린다.

결정 (11/17, 최영인): `season_filter("Christmas 2010")`이 성수기 표(2009-12와 2010-11을 합친 표, 규칙 315개)를 돌려주는 것을 인정한다. 2010년 크리스마스만의 표는 아니다. "december 2010"은 0개를 돌려준다. 이 차이는 보고서의 Solar 에이전트 절에 한계로 적는다.

## 11/20 점검 결과

`Hyeonseop`(f3c8216)에는 11/17 이후 새 커밋이 없다. PR #1은 열려 있다. `goeun`에는 29e3d29(11/17) 한 건이 올라왔다. `yuchan-final`에는 11/18~19에 네 건이 올라왔다: 48858c8(H3 질문 SHA-256), 981f87e(정답지 확정, `season_filter`, 라우터 기준선·채점 재생성), b2fc9ad(11/17 `season_filter` 결정 반영), 6b860e0(옛 정답지 초안, CPU 이름). 이번 점검은 git만으로 했고, 테스트는 실행하지 않았다.

| 브랜치 | 판정 | 남은 것 |
|---|---|---|
| `Hyeonseop` | 병합 가능 (11/17과 같음) | 없음 |
| `goeun` | 병합 가능 (11/17과 같음) | 없음 |
| `yuchan-final` | 보류 | 3, 11, 13 (H3 파일), 12 (`src/agent.py` 충돌) |

- 반영 확인: 요청 5(`tests/test_evaluate.py`에 테스트 10개), 6(T3 상품 support 최댓값 a435e68, CPU 이름 6b860e0), 8(질문 SHA 48858c8).
- **H3 문제와 정답지가 공개 브랜치에 있다.** `tests/h3_questions.csv`의 SHA-256(`090ed183…ed68`)과 `tests/h3_answer_key.csv`의 SHA-256(`d4a96315…81f3`)이 레포 밖 비공개 파일과 같다. 최종 문제와 정답지가 그대로 GitHub에 올라가 있고, 정고은도 볼 수 있다. `results/h3_grading.csv`와 `results/h3_router_runs.jsonl`에도 문제별 기대 도구, 호출 인자, 답이 들어 있어 정답지와 같은 정보다. 11/14 요청 3의 "히스토리는 그대로 둔다"는 옛 초안 기준이었다.
- `goeun`의 비결과 파일(코드, 테스트, README, 웹 화면)을 새 질문과 비교했다. 질문의 상품명 20개는 하나도 없다. 겹치는 네 단어 표현 9개는 모두 공개 전에 들어간 일반 표현이다(`tests/sample_questions.csv` 11/05, README·`web/index.html` 11/17). `goeun`의 마지막 커밋은 11/17 14:26이고, 질문이 올라간 981f87e는 11/18 16:10이다.
- `src/agent.py` 충돌: `Hyeonseop` → `goeun` → `yuchan-final` 순서로 메모리에서 시험 병합하면 `src/agent.py`의 `season_filter` 부분에서 충돌이 난다. `src/pcy.py`, `src/run_all.py`는 자동으로 합쳐진다. 유찬 쪽 `season_filter`의 동작은 11/17 결정과 같다("Christmas 2010" → 315개, "december 2010" → 0개).
- `results/timings.csv`를 유찬의 Intel Windows 기기에서 다시 만들었다. 11/17 결정대로 병합 뒤 기준 PC에서 다시 잰다.

결정 (11/20, 최영인): 지금 질문 세트와 정답지를 그대로 쓴다. 대신 아래를 지킨다.

1. H3 파일 4개(`tests/h3_questions.csv`, `tests/h3_answer_key.csv`, `results/h3_grading.csv`, `results/h3_router_runs.jsonl`)는 `agent-v1` 태그 전까지 어떤 브랜치에도 두지 않는다 (유찬 요청 11).
2. `scripts/grade_h3.py`는 레포 밖 경로를 읽고, 채점 결과도 레포 밖에 쓴다 (유찬 요청 13).
3. `main`의 `.gitignore`에 `tests/h3_questions.csv`, `tests/h3_answer_key.csv`, `results/h3_*`를 넣는다 (최영인).
4. 정고은은 새로 clone한 레포로 작업한다. 자기 기기에서 아래 명령을 실행해 결과를 알려 준다. 첫 줄은 AI 도구 대화 기록에 H3 파일 이름이 있는지, 둘째 줄은 로컬에 해당 커밋이 있는지 본다.

   ```bash
   grep -rl -e "h3_questions" -e "h3_answer_key" ~/.claude/projects/ ~/.codex/sessions/ 2>/dev/null
   git log --all --oneline -- tests/h3_questions.csv
   ```

5. `agent-v1` 태그는 질문이 올라가기 전 커밋인 `goeun` 29e3d29(11/17 14:26)에 단다. H3는 이 커밋의 에이전트로 채점한다. 이후 에이전트 변경(수정안의 Solar 실행 선택, 유찬의 `season_filter` 수정)은 H3와 따로 평가한다. 정답지의 기간 함정 문제는 29e3d29의 `season_filter` 동작으로 다시 확인한다.
6. AI 도구 규칙: `CLAUDE.md`와 `AGENTS.md`에 "`tests/h3_*`, `results/h3_*`와 레포 밖 H3 폴더는 읽지 않는다"를 적는다.
7. 보고서 한계 절에 질문이 공개 브랜치에 있던 기간, 채점한 에이전트 커밋, 평가자가 질문을 알고 `season_filter`를 고쳤다는 점을 적는다.

## 11/23 점검 결과

새 커밋: `yuchan-final`은 a2a4125(11/22)까지 다섯 건(465fff8, 2a64e44, d09e78c, 6811d53, a2a4125), `Hyeonseop`은 f33392e(11/22) 한 건이다. `goeun`(29e3d29)과 `main`은 그대로다. `agent-v1` 태그는 아직 없다.

| 브랜치 | 판정 | 남은 것 |
|---|---|---|
| `Hyeonseop` | 병합 가능 | 없음 |
| `goeun` | 병합 가능 | 없음 |
| `yuchan-final` | 병합 가능 | 2, 10 (병합 뒤 기준 PC에서 재실행) |

- `yuchan-final`: 요청 11, 12, 13을 반영했다. 최신 커밋에 H3 질문·정답지·채점 결과 파일이 없다. `.gitignore`에 `tests/h3_questions.csv`, `tests/h3_answer_key*.csv`, `results/h3_*.jsonl`, `results/h3_grading.csv`가 들어갔다. `scripts/grade_h3.py`는 인자 > 환경변수 > 레포 밖 기본 폴더 순서로 경로를 정하고, 결과도 레포 밖에 쓴다. `main`과 `goeun`을 자기 브랜치에 합쳐 `src/agent.py` 충돌을 풀었다. 새 `tests/test_agent_tools.py`에는 H3 질문과 겹치는 표현이 없다.
- `yuchan-final` 6811d53이 `season_filter`의 비수기 단어에 "winter", "겨울"을 더했다. 질문이 공개된 뒤 평가자가 바꾼 것이다. H3는 `agent-v1`(`goeun` 29e3d29)로 채점하므로 점수에는 영향이 없다. 보고서 한계 절(11/20 결정 7)에 같이 적는다.
- `Hyeonseop` f33392e("Solar 실행 선택용 집계 함수 추가"): 수정안의 알고리즘 담당 첫 산출물이다. `src/mining_job.py`의 `MiningJob`에 `profile()`(1차 통계와 설정별 메모리 추정), `pilot()`(표본 시험 집계), `validate_setting()`(예산 검사), `run()`(전체 집계)이 있다. `src/pcy.py`의 1차 패스를 `_encode_baskets`, `_count_buckets`로 나눴고, 결과는 그대로다. 설명은 `plan/solar_mining_tools.md`, 테스트는 `tests/test_mining_job.py`다.
- 시험 병합: 임시 worktree에서 `main`에 `Hyeonseop` → `goeun` → `yuchan-final`을 합쳤다. 충돌이 없다. 테스트 모듈 9개(`test_textbook`, `test_pcy_hash`, `test_evaluate`, `test_answer_key`, `test_answer_check`, `test_api`, `test_agent_tools`, `test_role2_integration`, `test_mining_job`)가 모두 통과한다.
- 병합본 `season_filter`: "Christmas 2010" 315개, "christmas season" 315개, "december 2010" 0개, "winter 2010" 0개, "summer 2011" 0개. 11/17 결정과 같다.
- 병합본 `MiningJob`으로 Y1, support 1%를 돌렸다. 빈발 상품 713, 세 설정 모두 빈발 쌍 585, 관측 후보 Apriori 252,748, PCY 작은 버킷 243,918, PCY 큰 버킷 1,238. 기준 수치가 유지된다.

수정안 보완점과 이어지는 관찰 (기준 PC, 1회 측정):

- `profile()`이 0.39초 걸린다. 1년 차 전체 집계와 비슷한 크기라, 지금 규모에서는 통계를 만드는 비용만으로 선택의 이득을 넘을 수 있다 (보완점 B).
- 예산 64 MiB에서는 세 설정이 모두 통과하고, 모델 메모리는 Apriori가 가장 작다(1,015,312 B, PCY 작은 버킷 3,054,127 B, PCY 큰 버킷 4,194,292 B). 이 입력에서는 메모리 기준 규칙 기반 선택이 늘 Apriori를 고른다. f33392e의 PCY 메모리 추정은 후보 수 상한을 써서, 지지도를 낮춰도 PCY가 Apriori보다 크게 나왔다. 그래서 어떤 예산에서도 선택이 갈리지 않았다 (보완점 A). 35ee06b에서 고쳤다 (11/24 점검 결과).
- `pilot()` 기본값(장바구니 1,000개, 기준 10건)은 0.02초에 끝나지만, 빈발 쌍이 1,060개로 전체의 585개와 크게 다르다. 표본 결과는 시간 추정용으로만 쓰고, 개수는 Solar에 "표본 기준"으로 표시해 보낸다.

## 11/24 점검 결과

새 커밋과 브랜치:

- `main`: PR #1로 `Hyeonseop`이 병합됐다(4ed6518, 11/23). 이현섭이 병합했고, 그대로 둔다.
- `Hyeonseop`: 35ee06b(11/23) "PCY 메모리 추정에 실제 후보 쌍 반영".
- `goeun-solar-selection`: 정고은의 새 브랜치다. `Hyeonseop` f33392e에서 갈라졌다. ff79472(11/23)에 H4 Solar 선택 모듈과 작업 이력 화면이 들어 있다.
- `yuchan-final`: bfa7739, 6fbc532, ae0106e(11/23)에 세 방식 비교표 틀(`plan/selection_compare.md`)이 들어 있다.
- `goeun`: 29e3d29 그대로다. `agent-v1` 태그는 아직 없다.

| 브랜치 | 판정 | 남은 것 |
|---|---|---|
| `Hyeonseop` | 병합됨 | 6의 MMDS Example 6.1 대조 (선택) |
| `goeun` | 병합 가능 (`agent-v1` 기준) | 5, low 라우터 |
| `goeun-solar-selection` | 검토 중 | `goeun` 대신 병합할지 최영인이 정한다 |
| `yuchan-final` | 병합 가능 | 2, 10 (병합 뒤 기준 PC에서 재실행) |

- **H3:** 어느 브랜치 끝에도 H3 질문·정답지·채점 파일이 없다. 11/20 이후 H3 파일을 건드린 커밋은 11/20 결정 1을 따른 것뿐이다. `yuchan-final`의 `reviews/h3_questions_sha256.txt`는 해시만 담는다.
- **시험 병합:** 임시 worktree에서 `main`(4ed6518)에 `goeun-solar-selection`, `yuchan-final`을 차례로 합쳤다. 충돌이 없다. 테스트 모듈 10개가 모두 통과한다. 11/23의 9개에 `test_mining_selection`이 더해졌다.
- **35ee06b:** `profile()`이 중복을 뺀 관측 후보 쌍을 세어 PCY 메모리를 추정한다. 기준 PC에서 `main`으로 Y1(장바구니 19,743개)을 확인했다.
  - 지지도 1%, 예산 6 MiB에서는 세 설정이 모두 통과한다.
  - 지지도 0.25%, 예산 6 MiB에서는 PCY 큰 버킷만 통과한다. 모델 메모리는 PCY 큰 버킷 4,194,292 B, Apriori 8,229,624 B다(`plan/solar_mining_tools.md`).
  - 메모리 기준 선택이 갈리는 조건이 생겼다 (보완점 A의 근거).
- **`goeun-solar-selection`:** `src/mining_selection.py`의 `MiningSelector`에 세 전략이 있다.
  - `rules`: 예산 안에서 Apriori, PCY 작은 버킷, PCY 큰 버킷 순으로 고른다. 보완점 A가 정해질 때까지 쓰는 임시 규칙이다.
  - `solar_once`: Solar에 한 번만 묻는다.
  - `solar_pilot`: Solar가 시험 집계를 한 번 요청할 수 있고, 실패하면 한 번 다시 고른다.
  - Solar 오류나 시간 초과가 나면 규칙 기반으로 넘어간다. 기존 H3 에이전트(`src/agent.py`)는 바꾸지 않는다. SQLite 작업 서버와 `/api/jobs` 엔드포인트는 아직 없다 (최영인 담당).
- **정고은 확인 명령 결과** (`goeun-solar-selection`의 `reviews/goeun_h3_check.md`):
  - AI 대화 기록에서는 Codex 기록 1개(11/11 세션)에 파일 이름이 나왔다. 질문이 올라간 11/18보다 앞선 세션이다. Claude 기록에서는 나오지 않았다.
  - 새 clone에서는 질문 파일 커밋이 없다. 기존 체크아웃에는 해당 커밋이 받아져 있다. 정고은은 파일 내용을 열지 않았다고 적었다.
  - `agent-v1`인 29e3d29는 11/17 커밋이므로 채점 기준은 그대로다.
- **`yuchan-final` 비교표 틀:** 35ee06b 기준 PCY 작은 버킷의 지지도 1% 모델 메모리(2,935,207 B)로 예산 경계를 다시 잡았다. 0.25%, 6 MiB 조건(B0.25)도 더했다.

### 점검 뒤에 바뀐 것 (11/24 오후 ~ 11/25)

위 내용은 11/24 오전 점검 시점의 기록이다. 그 뒤에 아래가 바뀌었다. 자세한 기록은 `reviews/integration_1124.md`와 `reviews/h4_progress.md`에 있다.

- **`agent-v1` 태그:** `goeun` 29e3d29에 달고 푸시했다 (11/24).
- **병합:** `goeun`, `yuchan-final`, `Hyeonseop`을 `main`에 병합하고 기준 PC에서 `run_all`을 다시 돌려 `results/`를 커밋했다 (11/24). `goeun-solar-selection`은 통합 브랜치 `h4-integration`을 거쳐 `main`에 병합했다 (11/25, 6a88a44). 위 표의 "검토 중"과 "병합 가능"은 모두 "병합됨"이 됐다.
- **보완점 A:** 결정했다 (11/24). 규칙 기반 선택은 예산을 통과한 설정 중 Apriori, PCY 작은 버킷, PCY 큰 버킷 순으로 첫 번째를 고른다. "임시 규칙"이 아니다.
- **작업 서버:** SQLite 작업 서버(`src/jobs.py`)와 `/api/jobs` 경로를 만들었다 (11/24).
- **이제 `main`에서 작업한다.** `h4-integration`은 `main`과 같은 커밋이다.

## 수정안 검토 (11/20)

대상: `Basket Insight Agent 프로젝트 수정안.docx` (레포 밖).

요약: Solar가 1차 패스 통계(빈발 상품 수, 장바구니 크기, 상품 쌍 수, 버킷 통과율)와 메모리 예산을 보고 Apriori, PCY 버킷 65,521개, PCY 버킷 1,048,573개 중 하나를 고른다. 근거가 부족하면 표본 시험 집계를 한 번 요청하고, 실패하면 한 번 다시 고른다. 서버는 SQLite 대기열, 작업 스레드, 별도 집계 프로세스로 돌고, API는 `POST /api/jobs`, `GET /api/jobs/{id}`, `GET /api/jobs/{id}/results` 세 개다. 규칙 기반 선택, Solar 1회 선택, Solar 시험 집계·재선택의 세 방식을 정확성, 실행 비용, 선택 결과, 서버 운영으로 비교한다. 첫 목표는 Solar가 설정을 골라 작업 한 건을 끝내는 것이다.

수치 확인: 후보 감소 99.5%(252,748 → 1,238)는 맞다. Apriori 0.193초와 PCY 0.635초는 PR #1의 Windows(Ryzen 7 9800X3D) 측정값이다.

보완할 점:

- [ ] A. 비교 기준인 "규칙 기반 선택"을 정의한다. 예: 삼각 배열 예상 메모리가 예산 이하면 Apriori, 아니면 PCY 큰 버킷.
- [ ] B. 큰 입력을 만드는 방법을 정한다(표본 추출, 장바구니 복제, 2년치 전체). 1년 차 집계는 1.5초 안에 끝나서, 지금 규모에서는 Solar 호출 시간이 집계 절감보다 클 가능성이 크다.
- [ ] C. 시간 전제는 기준 PC 값으로 쓴다. 지지도 1%에서 Windows(PR #1)는 Apriori가 빨랐다. `Hyeonseop` 브랜치의 Mac `results/timings.csv`는 PCY 큰 버킷이 빨랐다(0.288초 대 0.561초). 11/17 측정은 다시 Apriori가 빨랐다.
- [ ] D. "실제 최대 메모리" 측정 방법을 정한다. `tracemalloc`은 프로세스 전체 메모리가 아니다. `resource`는 Windows에 없으므로, 팀원 Windows 기기에서 재려면 `psutil`이 필요하다. 강제 한도는 OS마다 방법이 달라 문서대로 나중에 따로 검증한다.
- [ ] E. 범위: 동결된 `plan_v0.6`에 없는 새 연구 질문이다. H1–H3는 그대로 두고, 이 질문은 확장(H4 또는 부록)으로 분리한다. H3 채점에 쓰는 기존 규칙 조회 도구는 남긴다. 12/8까지 약 18일이므로 첫 목표(작업 한 건 끝내기)부터 한다.

담당별 할 일 (수정안의 분담 기준):

| 담당 | 할 일 |
|---|---|
| 공통 | A, B 결정 |
| 이현섭 | 1차 통계와 시험 집계 도구, 설정·메모리 추정 검증, 고정 방식과 결과 일치 확인 |
| 유찬 | 세 방식 비교표(시간, 메모리, 실패 원인), 요청 11, 12, 13 |
| 최영인 | 평가 데이터와 재현 명령, SQLite 대기열·작업 스레드·집계 프로세스 연결, C, D |
| 정고은 | Solar 선택·시험 요청·재선택 도구 호출, 실패·시간 초과 시 규칙 기반으로 넘어가기, 작업 이력 화면 |

## 이현섭 (A-Priori·PCY, `Hyeonseop`)

판정: 수정 후 병합.

- [x] 1. A-Priori 2차 패스를 `Counter`에서 삼각 배열로 되돌린다 (계획 §3.1, 11/11 결정).
- [x] 2. 구현을 `src/` 한 곳에 둔다. `role2_algorithms/`의 핵심을 옮기고 io, CLI, examples, docs는 지운다.
- [x] 3. PCY `n_candidates_all`을 `main` 정의로 되돌리고 `possible_frequent_item_pairs` 열을 지운다. `apriori.run()`의 `n_candidates`는 실제로 나타난 후보 수(1%에서 252,748)로 맞춘다.
- [x] 4. 두 알고리즘을 같은 방식(numpy)으로 맞춘 뒤 실데이터로 `python -m src.run_all --only T2`를 돌리고, 시간 결과를 PR 설명에 적는다. 지금 브랜치는 T2가 645초 걸리고 "PCY가 빠르다"는 결론이 뒤집힌다. (PR #1 설명에 Windows 5회 중앙값 기록, 11/24 확인)
- [x] 5. T2 출력에 support 1%의 빈발 3개 조합 수(103개)를 한 줄 넣는다 (11/11 결정).
- [x] 6. `tests/test_textbook.py`에 confidence 필터로 걸러지는 규칙이 생기는 예제를 넣는다. MMDS Example 6.1과 대조하는 테스트가 있으면 더 좋다 (1차 리뷰 #6). (confidence 필터 테스트는 PR #1에 반영, MMDS 대조는 없음)

## 정고은 (Solar 에이전트·API, `goeun`)

판정: 수정 후 병합.

- [x] 1. `season_filter`가 기간을 파싱하게 한다.
  - 315개를 반환하는 입력: 성수기 표현("christmas season", "peak season", "크리스마스 성수기" 등), "2009-12", "2010-11", "december 2009", "november 2010"
  - 0개를 반환하는 입력: 그 밖의 연도나 계절
  - 도구 설명에 허용 값을 적고, 라우터도 같은 파서를 쓴다
  - 테스트에 7개 경우를 넣는다: "christmas 2011", "summer season", "november 2010", "christmas season", "peak season", "크리스마스 성수기", "Christmas 2010"
- [x] 2. 시스템 프롬프트에 "A → B means baskets with A also contain B; there is no order"를 넣는다. 접속 테스트에서 모델이 전건을 "먼저 산 상품"으로 설명했다.
- [x] 3. `top_rules` 도구 안에서 limit을 1~500으로 제한한다. 지금은 API에서만 막아서, Solar가 도구를 직접 부르면 막히지 않는다.
- [x] 4. `--eval`은 `--key`를 필수로 받는다. 질문 파일 SHA, 실행 ID, HTTP 재시도를 기록한다 (1차 리뷰 #9).
- [ ] 5. `--ping` 도움말과 docstring을 실제 동작(`agent_runs.jsonl`, `tool_choice: "auto"`)에 맞춘다. T6과 채점에서는 `method == "ping"`인 행을 건너뛴다.
- [x] 6. `plan/upstage_terms_check.md`에 11/11 ping 결과를 적고 `reviews/`로 옮긴다. 지금 문서의 "실제 API 접속은 아직 수행하지 않았다"는 같은 브랜치의 ping 기록과 모순된다. (29e3d29: `reviews/upstage_terms_check.md`에 11/11 접속 시험 기록)
- [x] 7. `src/api.py`
  - POST는 `application/json`만 받는다
  - Host가 127.0.0.1이나 localhost가 아니면 403을 낸다
  - `Content-Length`가 잘못되면 500이 아니라 400을 낸다
- [x] 8. 데모 예시 문장 "What should we bundle for the Christmas season?"을 다른 문장으로 바꾸고 README의 해당 문장도 고친다. 노출된 옛 H3 질문과 글자까지 같다.
- [x] low. `rules_y1.csv`, `rules_season.csv`를 `run_all`이 만들게 한다 (1차 리뷰 #11).
- [ ] low. 라우터가 support 숫자를 confidence로 넣는 문제를 고친다. 끝에 공백이 있는 상품명 22개도 매칭되게 한다.
- [x] low. 기록하는 모델 ID를 상수가 아니라 응답 값으로 남긴다.

H3 질문과 정답지는 `agent-v1` 태그 전까지 에이전트 담당에게 공개하지 않는다 (계획 §3.4). 위 항목은 1차 리뷰와 병합 검토에서 나온 것이고, 새 질문 세트와는 관계없다.

## 유찬 (규칙 검증·기준선·측정, `yuchan-final`)

판정: 일부만 수정 후 병합.

- [x] 1. `src/evaluate.py:197-198`의 `seed=` 인자를 지워 bootstrap seed를 0으로 되돌린다 (계획 §3.2).
- [ ] 2. `results/`의 `null_check.csv`, `t5_sensitivity.csv`, `timings.csv`를 `main` 버전으로 되돌린다. 다시 재는 것은 알고리즘 브랜치를 병합한 뒤 기준 PC(최영인의 Mac)에서 한다.
- [x] 3. H3 파일 5개를 PR에서 뺀다: `tests/h3_questions.csv`, `tests/h3_answer_key.csv`, `results/h3_grading.csv`, `results/h3_router_runs_v2.jsonl`, `scripts/grade_h3.py`. 히스토리는 그대로 둔다. (11/20 요청 11로 대체, 11/23 반영 확인)
- [x] 4. T5 bootstrap을 100회에서 1,000회로 바꾼다 (계획 §6, 1차 리뷰 #8).
- [x] 5. `tests/test_evaluate.py`에 `_split` off-by-one, `_ci`, `top5_filter`, `drop_top1pct`, `merge_same_day`, changed 플래그 테스트를 넣는다 (1차 리뷰 #7).
- [x] 6. T3에 상품 support 최댓값(0.162)을 넣는다. `timings.csv`의 CPU를 "arm" 대신 실제 모델명으로 적는다.
- [x] 7. `run_all.py` T6: `agent_runs.jsonl`과 `h3_grades.csv`가 둘 다 있으면 `NotImplementedError`로 멈추지 말고 경고만 낸다.
- [x] 8. 새 H3 질문 초안을 검토한다. 파일은 레포 밖에 있고, 최영인이 따로 공유한다. 11/17에 질문 파일 SHA-256을 커밋한다.
- [x] 선택. 새 입력 검사를 확인하는 테스트를 1~2개 넣는다. (a2a4125 `tests/test_agent_tools.py`)

### 11/14 커밋 `dcd8756` 검토 ("Submit weekly T3 and T5 results")

이 커밋은 `results/`의 CSV 3개(`null_check.csv`, `t5_sensitivity.csv`, `timings.csv`)만 바꿨다. 위 요청은 모두 그대로 열려 있다.

- 요청 2와 반대다. 세 CSV를 `main` 버전으로 되돌리지 않고, 다른 기기에서 다시 만들어 덮어썼다.
- `null_check.csv`의 `support_0.25`, `b1` 행이 100회에서 20회로 줄었다. 11/11 결정은 100회 유지다. 1회 시간도 `main`보다 2~5배 길다(`b1` 25.9초 대 5.5초).
- CSV를 브랜치 코드로 다시 만들 수 없다. `null_check.csv`에 `max_product_support` 열이 생기고 `seconds` 열이 없어졌다. 그런데 브랜치의 `src/`에는 `max_product_support`를 만드는 코드가 없고, `null_model.py:132`는 아직 `seconds`를 쓴다. 커밋하지 않은 코드로 만들었거나 손으로 고친 파일이다.
- `t5_sensitivity.csv`의 `min_ci_cust_lo`가 바뀌었다(기준 줄 0.04336 → 0.04360). 요청 1(seed)을 반영하지 않았기 때문이다. 판정(H1 No, H2 Yes, changed 모두 False)은 같다.
- T5 bootstrap은 여전히 100회다 (`run_all.py:108`, 요청 4).
- H3 파일 5개가 그대로 있다 (요청 3).

추가 요청:

- [x] 9. `max_product_support`를 만드는 코드를 커밋한다 (요청 6의 일부). 결과 CSV는 코드와 함께만 바꾼다.
- [ ] 10. `dcd8756`의 CSV 3개를 `main` 버전으로 되돌린다. 결과는 병합 뒤 기준 PC에서 `run_all`로 다시 만든다.

11/20 추가 요청:

- [x] 11. H3 파일 4개(`tests/h3_questions.csv`, `tests/h3_answer_key.csv`, `results/h3_grading.csv`, `results/h3_router_runs.jsonl`)를 `agent-v1` 태그 전까지 브랜치에 두지 않는다. 방법은 최영인과 따로 정한다.
- [x] 12. `goeun`을 합친 상태에서 `src/agent.py` 충돌을 풀 수 있게, `main`과 `goeun`을 받아 `season_filter` 변경을 다시 맞춘다.
- [x] 13. `scripts/grade_h3.py`가 질문·정답지 경로를 인자나 환경변수로 받게 하고, 기본값을 레포 밖 폴더로 둔다. 채점 결과도 레포 밖에 쓴다.

## 최영인 (데이터·재현)

- [x] 재현 1차 리허설 (T1, T2, 11/14). clean clone 결과가 커밋된 CSV와 같다. 다른 것은 기기마다 다른 `timings.csv`뿐이다.
- [x] `scripts/download_data.py`가 certifi 인증서 묶음을 쓴다. 리허설에서 python.org Python이 `CERTIFICATE_VERIFY_FAILED`로 멈춘 문제를 고쳤다.
- [x] H3 질문 30개 초안 (레포 밖)
- [x] 위 수정 요청을 각 담당자에게 전달한다.
- [x] 유찬 검토 뒤 질문 파일 SHA-256을 커밋한다 (11/17). 유찬이 48858c8에서 커밋했다.
- [x] H3 공개 처리 방식을 정한다 (11/20 점검 결과의 결정).
- [x] `.gitignore`에 H3 파일 규칙을 넣고, `CLAUDE.md`·`AGENTS.md`에 H3 파일 읽기 금지 규칙을 적는다. (11/24)
- [x] 정고은의 확인 명령 결과를 받는다. (11/24 점검 결과)
- [x] `goeun` 29e3d29에 `agent-v1` 태그를 단다. (11/24, 푸시함)
- [x] 수정이 들어오면 세 브랜치를 순서대로 병합하고, 기준 PC에서 `run_all` 전체를 다시 돌려 `results/`를 커밋한다. (11/24, `reviews/integration_1124.md`)
- [x] 문서에 12주차 리포트를 쓴다 (11/24).
- [ ] low. 보고서에 계획 수치 정정 주석을 단다: 상품 4,877 → 4,707, 최대 장바구니 1,108 → 1,106. 캐시 이름(`lines_`, 계획은 `baskets_`) 차이도 적는다. 수치 두 개는 `reviews/report_draft.md` 초안에 넣었다. 캐시 이름은 아직이다.
