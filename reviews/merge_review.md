# 브랜치 병합 검토 (2026-11-11)

대상: `origin/Hyeonseop` (f874e91, 알고리즘), `origin/yuchan-final` (f125da7, 평가). 기준은 `main` (923757a)과 그 `results/`다. 검토는 읽기 전용으로 했고, 브랜치와 `main`은 바꾸지 않았다.

## 요약

| 브랜치 | 판정 | 이유 |
|---|---|---|
| `Hyeonseop` | 수정 후 병합 | 결정적 결과는 `main`과 같다. 하지만 계획 §3.1(삼각 배열)과 어긋나고, T2의 의미(후보 수 열, 시간 결론)가 바뀌었다 |
| `yuchan-final` | 일부만 수정 후 병합 | 견고성 수정은 결과를 바꾸지 않는다. bootstrap seed 변경과 H3 파일은 계획 §3.2, §3.4와 어긋난다 |

두 브랜치를 함께 시험 병합하면 충돌이 없고, 테스트 5종이 모두 통과한다.

## 기준 수치

| 항목 | main | Hyeonseop | yuchan-final | 두 브랜치 병합 |
|---|---|---|---|---|
| 1년 차 장바구니 / 기준 | 19,743 / 198 | 같음 | 같음 | 같음 |
| 빈발 상품 / 빈발 쌍 / 규칙 | 713 / 585 / 189 | 같음 | 같음 | 같음 |
| 네 support 수준의 빈발 쌍 | 62 / 585 / 4,364 / 26,111 | 같음 (A-Priori = PCY) | - | - |
| PCY 후보 (1%, B = 1,048,573) | 1,238 | 같음 | - | - |
| F2 2년 차 유지 | 134 / 189 | 같음 (CSV 바이트 동일) | - | 같음 |
| 규칙 표 `rules_y1` / `rules_season` | 189 / 315 | 바이트 동일 | - | - |
| H1 평균 D | 0.16185 | 같음 | 같음 | 0.1619 |
| H2 차이 (seed 0~4) | 0.0477 ~ 0.0512 | 같음 | 같음 | 같음 |
| H2 고객 단위 CI 하한 최솟값 | 4.360%p | - | 4.354%p (seed 변경 때문) | 4.354%p |
| T2 A-Priori 1% `n_candidates` | 253,828 | 252,748 (정의 통일) | - | - |
| T2 전체 실행 시간 | 약 50초 | 645초 | - | - |
| H1 1회 계산 시간 | 약 5초 | - | - | 약 17초 |

## `Hyeonseop` (알고리즘)

| # | 항목 | 판정 | 근거 |
|---|---|---|---|
| H-1 | 구현이 두 벌이다 (`role2_algorithms/` 패키지와 `src/` 래퍼) | 수정 요청 | `role2_algorithms/`에 `__init__.py`가 없어 루트에서 `python -m`으로 실행할 때만 import된다. `pyproject.toml`은 `basket_mining`으로 설치하는데 `src/`는 `role2_algorithms.basket_mining`으로 import한다. 해시와 메모리 공식이 래퍼에도 다시 있다 (`src/pcy.py:20-23, 58-63, 84-89`) |
| H-2 | A-Priori가 삼각 배열이 아니라 `Counter`다 | 수정 요청 (계획과 모순) | 계획 §3.1은 삼각 배열과 그 이유(쌍의 99.6%가 나타남)를 적었다. `memory_bytes`는 여전히 4·C(m,2)를 내고 "textbook model only" 라벨만 붙었다 |
| H-3 | `rules()` 순서 | 통과 | 정렬 키가 `main`과 같고, 규칙 표가 바이트 단위로 같다 |
| H-4 | `min_count` | 통과 | n > 0에서는 `main`과 차이 0건이다. n = 0에서만 1을 반환한다 |
| H-5 | 비트맵 바이트 `ceil(B/8)` | 통과 | 계획의 "버킷당 1비트"와 맞다. `main`의 `5//8 = 0`이 버그였다. 결과 CSV 값이 1바이트씩 바뀐다 |
| H-6 | `compare()` 열 | 수정 요청 | 리뷰 #4(후보 수 정의)는 해결됐다. 하지만 PCY 행의 `n_candidates_all`이 NaN이 되어 정의가 다시 섞였다. `possible_frequent_item_pairs`가 중복 열이다. `apriori.run()`의 `n_candidates`는 여전히 C(m,2)라서 `compare()`와 다르다 |
| H-7 | 3개 조합 | 통과 | 1%에서 A-Priori와 PCY 모두 103개이고 결과가 같다. 다만 `run_all` 출력에는 아직 없다 |
| H-8 | `role2_algorithms` 문서 | 수정 요청 | `docs/validation.md:38`에 "UCI 전체 데이터는 아직 실행하지 않았다"고 적혀 있다. 계획 밖의 CLI, TXT/CSV 입력, SPMF 설명이 있다. 문서 총 230줄이다 |
| - | 시간 비교의 공정성 (리뷰 #5) | 팀 결정 | 두 알고리즘 모두 순수 Python으로 맞춰져 공정해졌다. 대신 5~13배 느려졌고, 1%에서 "PCY가 빠르다"는 결론이 A-Priori가 빠르다(2.58초 대 3.24초)로 뒤집힌다 |
| - | 교재 테스트 (리뷰 #6) | 일부 해결 | lift 필터는 테스트하지만 conf 필터는 role2 테스트에만 있다. MMDS Example 6.1 대조는 없다 |

작성자에게 보낼 요청:

1. A-Priori 2차 패스를 삼각 배열로 되돌린다 (`main`의 로직 재사용). 되돌리지 않으려면 계획 §3.1을 고칠지 팀이 정한다.
2. PCY `n_candidates_all`을 `main` 정의로 되돌리고, `possible_frequent_item_pairs` 열을 지운다. `apriori.run()`의 `n_candidates`를 관측 후보 수로 맞춘다.
3. 구현을 한 곳에 둔다. `basket_mining`의 핵심을 `src/`로 옮기거나 import 경로를 하나로 정한다. io, CLI, examples, docs는 지운다.
4. 실데이터로 `python -m src.run_all --only T2`를 돌리고, 시간 변화와 결론이 뒤집힌 점을 PR 설명에 적는다.
5. `tests/test_textbook.py`에 confidence 필터로 걸러지는 예제를 추가한다.

## `yuchan-final` (평가)

| # | 항목 | 판정 | 근거 |
|---|---|---|---|
| Y-1 | `evaluate.py` 빈 입력 처리 | 통과 | H1, H2 결과가 `main`과 완전히 같다 |
| Y-2 | bootstrap seed 0 → `s`, `s + 10000` | 수정 요청 | 계획 §3.2는 "1,000회, seed 0"이다. CI 경계가 최대 0.046%p 바뀐다(판정은 같음). `h2.csv`는 다시 만들지 않아 코드와 결과가 서로 맞지 않는다 |
| Y-3 | H3 질문과 정답지를 `tests/`에 커밋 | 제외 | 계획 §3.4는 `agent-v1` 태그 전까지 레포 밖에 두고 SHA-256만 커밋하라고 한다. 공개 브랜치라 에이전트 담당도 볼 수 있다 |
| Y-3 | 문항 구성 | 제외 | 계획은 답 있는 24개(이름 바꾼 질문 6개 이상, 여러 번 호출 4개 이상, 성수기 4개)와 함정 6개다. 브랜치는 답 있는 20개, 함정 10개, 이름 바꾼 질문 0개, 여러 번 호출 0개, 성수기 5개다. 이러면 H3 조건 2(어려운 문항에서 라우터보다 많이 맞힘)를 평가할 수 없다 |
| Y-4 | `h3_grading.csv`, `h3_router_runs_v2.jsonl` | 제외 | Solar가 아니라 키워드 라우터를 1회 돌린 결과다(30/30). 질문이 라우터 키워드에 맞춰졌을 가능성을 배제할 수 없다 |
| Y-5 | `scripts/grade_h3.py` | 제외 | "I cannot answer"가 들어 있는지만 본다. 수치 허용 오차, 지어낸 수치 판정, 3회 중 2회, 채점자 2명, 정답지 SHA 기록이 없다 |
| Y-6 | `null_check`, `t5_sensitivity`, `timings` CSV | 제외 | 다른 PC(Windows, Python 3.13.9)에서 다시 만들었다. B1 null의 1회 시간이 30초라 seed가 100개에서 20개로 줄었다. T5는 seed 변경만 반영했고 여전히 bootstrap 100회다. `timings`는 알고리즘 브랜치가 측정 코드를 바꾸므로 곧 낡는다 |
| Y-7 | `null_model.py` 입력 검증 | 통과 | seed 1~2개로 `main`과 결과가 같다. 불가능한 입력에서 `fisher_greater`가 조용히 1.0을 돌려주는 점은 선택적으로 고친다 |

작성자에게 보낼 요청:

1. `src/evaluate.py:197-198`의 `seed=` 인자를 지워 seed 0으로 되돌린다.
2. `results/` CSV 3개를 `main` 버전으로 되돌린다. 다시 재는 것은 알고리즘 브랜치 병합 뒤 정한 PC에서 한다.
3. H3 파일 5개(`tests/h3_questions.csv`, `tests/h3_answer_key.csv`, `results/h3_grading.csv`, `results/h3_router_runs_v2.jsonl`, `scripts/grade_h3.py`)를 PR에서 뺀다.
4. (선택) 새 입력 검사를 확인하는 테스트를 1~2개 추가한다.

## `goeun` (에이전트, db57a5f)

판정: 수정 후 병합. 테스트 6종이 통과하고, 규칙 표(189 / 315)와 규칙 ID 순서가 `main`과 같다. 키와 데이터 반출 문제는 없다. `main`, `Hyeonseop`, `yuchan-final`과 충돌이 없다.

| # | 항목 | 판정 | 근거 |
|---|---|---|---|
| G-1 | `season_filter`를 정확한 일치로 바꿈 (`agent.py:116`) | 수정 요청 | 함정 입력("christmas 2011", "summer season")은 0개로 고쳐졌다. 하지만 "november 2010"은 여전히 0개다. "christmas season", "peak season", "크리스마스 성수기"가 315개에서 0개로 바뀌는 회귀가 생겼다. 성수기 문항이 틀릴 수 있다 |
| G-2 | 라우터가 연도가 있으면 질문 전체를 period로 넘김 (`agent.py:254`) | 수정 요청 | "Christmas 2010 bundles?"가 0개가 된다 |
| G-3 | `rules_for("")` | 통과 | 0개를 반환한다 |
| G-4 | `top_rules`의 limit ≤ 0 | 수정 요청 (low) | API만 1~500으로 제한한다. Solar는 도구를 직접 부르므로 도구에서 제한해야 한다 |
| G-5 | 라우터의 support/confidence 혼동, 끝 공백 상품명 | 그대로 | 리뷰 1회차 low 항목이 남아 있다 |
| G-6 | `--eval` 기록 | 부분 해결 | `tool_trace`가 추가됐다. `--key`는 여전히 선택이고, 질문 파일 SHA, 실행 ID, 재시도가 없다 |
| G-7 | 시스템 프롬프트 | 수정 요청 | "A → B에 순서가 없다"는 문장이 아직 없다 (`agent.py:141-144`) |
| G-8 | `answer_check.py` (답의 수치가 도구 출력에 있는지 점검) | 통과 | 채점이 아니라 점검이라고 스스로 밝힌다. 한계: lift를 반올림하면 "지어냄"으로 본다. 수치가 어느 규칙의 것인지는 보지 않는다. 붙여 넣기 방식에서는 허용 집합이 표 전체라 거의 걸러 내지 못한다 |
| G-9 | `api.py` 보안 | 통과, 수정 요청 (low) | 127.0.0.1에만 바인딩하고 표준 라이브러리만 쓴다. 경로 이동은 안 되고 traceback은 서버 로그에만 남는다. 다른 사이트가 보낸 POST도 처리해서 Solar 비용을 쓰게 할 수 있다. `Content-Length`가 숫자가 아니면 500이 난다 |
| G-10 | `web/index.html` XSS | 통과 | 출력을 일관되게 이스케이프한다 |
| G-11 | 범위와 크기 (약 800줄) | 팀 결정 | 계획 §5에는 web과 API가 없다. README 역할 표에는 "규칙 조회 API와 시연 화면"이 있다. 판정에는 쓰지 않는 시연용이다 |
| G-12 | ping 기록이 `results/agent_runs.jsonl`에 들어감 | 수정 요청 | `--ping` 도움말은 `solar_ping.jsonl`이라고 하는데 실제 기본값은 `agent_runs.jsonl`이다. docstring은 "forced tool call"인데 코드는 `tool_choice: "auto"`다. T6과 채점은 `method == "ping"`을 건너뛰어야 한다 |
| G-13 | `plan/upstage_terms_check.md` | 수정 요청 | "실제 API 접속은 아직 수행하지 않았다"는 문장이 같은 브랜치의 ping 성공 기록과 모순된다. 계정 요금제(무료 티어면 학습 이용 예외)가 적혀 있지 않다. `plan/`보다 `reviews/`가 맞는 위치다 |
| G-14 | 데이터 반출과 키 | 통과 | 규칙 표, 상품 코드와 이름, 질문만 보낸다. 기록에 키가 없다 |
| G-16 | 데모 예시 문장이 노출된 H3 질문과 같음 | 수정 요청 | "What should we bundle for the Christmas season?"이 `yuchan-final`의 H3Q08과 글자까지 같다. README는 "H3 질문 세트에서 온 것이 아니다"라고 적었다 |

작성자에게 보낼 요청:

1. `season_filter`가 기간을 파싱하게 한다. 성수기 단어, "2009-12", "2010-11", "december 2009", "november 2010"은 315개를 반환한다. 그 밖의 연도나 계절은 빈 결과다. 도구 설명에 허용 값을 적고, 라우터도 같은 파서를 쓴다. 테스트에 7개 경우를 추가한다 ("christmas 2011", "summer season", "november 2010", "christmas season", "peak season", "크리스마스 성수기", "Christmas 2010").
2. `agent.top_rules`에서 limit을 1~500으로 제한한다.
3. `--ping` 도움말과 docstring을 실제 동작에 맞춘다.
4. `upstage_terms_check.md`에 11/11 ping 결과와 계정 요금제를 적고, `reviews/`로 옮긴다.
5. 시스템 프롬프트에 "A → B means baskets with A also contain B; there is no order"를 넣는다.
6. `api.py`: POST는 `application/json`만 받고, Host가 127.0.0.1이나 localhost가 아니면 403을 낸다. `Content-Length` 오류는 400으로 낸다.
7. 데모 예시에서 H3Q08과 같은 문장을 바꾸고, README의 해당 문장을 고친다.

## 결정 (2026-11-11, 최영인)

| 항목 | 결정 |
|---|---|
| 병합 | 각 담당자가 수정 요청을 반영한 뒤 최영인이 병합한다. 순서는 `Hyeonseop` → `goeun` → `yuchan-final`이다 |
| H3 질문 | 노출된 30개는 버리고 새로 쓴다. 계획 §3.4 구성대로 쓰고, 레포 밖에 두고 SHA-256만 커밋한다 |
| 브랜치의 질문 원문 | `yuchan-final` PR에서 파일만 뺀다. 히스토리는 그대로 둔다 |
| 재현 리허설 | 최영인이 맡는다 |
| A-Priori 2차 패스 | 삼각 배열로 되돌린다 (계획 §3.1) |
| 구현 위치 | `src/` 한 곳에 둔다 |
| 시간 측정 | 두 알고리즘을 같은 방식(numpy)으로 맞춘 구현으로 잰다 |
| 기준 PC | 최영인의 Mac (`main` 결과를 만든 기기). null은 100회를 유지한다 |
| 3개 조합 수 | T2에 한 줄로 출력한다 |

## 최영인 몫 수정

로컬 브랜치 `worktree-agent-a75781705ff0eafae`의 커밋 `443efd0`에 있다. `.gitignore`가 심볼릭 링크도 무시한다. T1 로그에 장바구니 수(39,516)와 상품 수(4,707) 줄이 생겼고, 로그가 없으면 다시 만든다. F1에서 2011-12를 부분 월로 표시한다.
