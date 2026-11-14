# 1차 초안 리뷰 (1회차, 2026-11-05)

리뷰어 3명이 범위를 나눠 읽기 전용으로 검토했다. 수정은 하지 않았다. 점수는 범위별 참고값이다.

| 범위 | 점수 |
|---|---|
| 데이터·알고리즘 (`clean`, `apriori`, `pcy`, T1·T2·F1·F2) | 80 |
| 평가 (`evaluate`, `null_model`, T3–T5) | 88 |
| 에이전트·레포 위생 (`agent`, 정답지 테스트, T6) | 72 |

## 확인된 것

- 정제 행 수, 장바구니 39,516개, 1년 차 19,743개, 기준 198, 빈발 상품 713개, 빈발 쌍 585개, 규칙 189개가 plan과 같다. brute force로 대조했다.
- PCY와 A-Priori의 빈발 쌍이 4개 support 수준 × 2개 B에서 모두 같다.
- H1 나누기(첫 도달에서 멈춤, rng 순서), 유지 판정, H2 가리기, bootstrap에 누수나 off-by-one이 없다. 독립 구현으로 재계산했다.
- B1 HitRate(0.174)가 규칙(0.075)보다 높은 것은 커버리지 차이 때문이다. 버그가 아니다.

## 고칠 것 (심각한 순)

### high

1. `.gitignore`: `data/`, `.venv/`가 심볼릭 링크를 막지 못한다. 원본 체크아웃에는 링크가 없고, worktree(`.claude/worktrees/draft-v1`)의 `data`, `.venv` 링크만 미추적으로 보인다. 거기서 `git add -A`를 하면 커밋될 수 있다. 슬래시 없는 `data`, `.venv`로 바꾼다. **해결 (11/11):** 슬래시 없는 패턴으로 바꿨다. `git check-ignore`로 링크가 무시되는 것을 확인했다.
2. `src/agent.py` `season_filter`: 키워드를 부분 문자열로 맞춘다. "christmas 2011", "summer season" 같은 데이터에 없는 기간(함정)에도 315개를 반환한다. "november 2010"은 0개를 반환한다. 연도와 월을 파싱하거나 period를 enum으로 바꾼다.
3. TLS: venv Python(python.org 3.14)에 CA 인증서가 없어 Solar 호출이 `CERTIFICATE_VERIFY_FAILED`로 실패한다. `Install Certificates.command`를 실행하거나 `SSL_CERT_FILE=/etc/ssl/cert.pem`을 쓴다. README에 적는다. **해결 (11/5):** `agent.py`가 certifi CA 번들을 쓰고, README Solar 절에 적었다.

### medium

4. `src/pcy.py` T2: `n_candidates` 열의 정의가 섞였다. A-Priori 행은 C(m,2)(253,828), PCY 행은 실제 출현한 후보 수다. `n_candidates_all` 열은 이미 있다. A-Priori 행의 `n_candidates`를 `n_occurring`(252,748)으로 바꿔 PCY와 정의를 맞춘다.
5. `src/apriori.py` 2차 패스: Python 리스트에 모은 뒤 bincount한다. PCY는 numpy로 벡터화되어 있다. 그래서 시간·메모리 비교는 구현 차이를 반영한다. 구현 방식을 맞추거나, 보고서에 "구현 차이"라고 적는다.
6. `tests/test_textbook.py`: `rules()`의 conf/lift 필터를 지워도 테스트가 통과한다. 걸러지는 규칙이 생기는 예제를 추가한다. 교재 예제(MMDS Example 6.1)와 대조하는 테스트도 없다.
7. `tests/test_evaluate.py`: `_split` off-by-one, `_ci`, `top5_filter`, `drop_top1pct`, `merge_same_day`, changed 플래그를 테스트하지 않는다.
8. T5: `n_boot=100`으로 고정되어 있다. 1,000회도 한 줄에 약 5초라 시간 안에 끝난다. plan §6에 따라 1,000회로 바꾼다.
9. `src/agent.py --eval`: `--key` 없이도 돌고, 정답지 SHA가 null로 기록된다. 질문 파일 SHA와 실행 ID도 없다. HTTP 오류 한 번에 전체가 중단되고, 재시도가 없다.
10. 정답지 스키마: 한 행에 도구 하나라서 여러 번 호출하는 문항을 표현할 수 없다. `allowed_tools`, `rule_ids` 열이 없다.
11. 규칙 표(`rules_y1.csv`, `rules_season.csv`)를 `run_all`이 만들지 않고, 파일이 있으면 다시 만들지 않는다.

12. 접속 테스트(2026-11-05, `solar-pro4`): 수치 인용은 정확했다. 하지만 모델이 전건을 "먼저 산 상품"으로 설명했다. 장바구니에는 순서가 없다. 시스템 프롬프트에 "A → B는 A가 든 장바구니에 B도 들어 있다는 뜻이고, 순서는 없다"를 넣는다. Upstage 이용 약관 확인 기록도 아직 없다 (§3.4).

### low

- plan 수치 정정이 필요하다. 상품 수 4,877은 대문자 통일 전 값이고 실제는 4,707이다. 최대 장바구니 크기는 1,108이 아니라 1,106이다. plan은 동결이므로 보고서에 주석을 단다.
- T3에 상품 support 최댓값(0.162)이 없다 (plan §1).
- T1 로그에 장바구니 수와 상품 수 줄이 없다. `cleaning_log.csv`는 캐시를 처음 만들 때만 써진다. **해결 (11/11):** 장바구니 수(39,516)와 상품 수(4,707) 줄을 데이터에서 계산해 추가했다. 로그 파일이 없으면 캐시를 다시 만들어 로그도 다시 쓴다.
- 캐시 이름이 `lines_…`이다. plan은 `baskets_…`이다.
- `timings.csv`의 CPU가 "arm"으로만 기록된다.
- `min_count` 테스트가 없다. pytest가 없어 `python -m tests.x`로만 돈다. (README Reproduce 절에 실행 명령을 적었다.)
- 셔플 겹침 처리가 plan과 다르다(무작위 자리를 더해 같이 섞는다). 남은 겹침은 0이다.
- 라우터가 support 숫자를 confidence로 넣는다. 끝에 공백이 있는 상품명 22개를 매칭하지 못한다.
- `rules_for("")`가 189개 전부를 반환한다. `top_rules(limit=-1)`도 결과를 낸다.
- `.env` 탐색이 루트까지 올라간다. 기록되는 모델 ID가 응답 값이 아니라 상수다.
- 붙여 넣기 프롬프트에는 규칙 약 504개(31k자)가 들어간다. plan은 약 200개로 가정했다.
- F1의 2011-12는 9일뿐인 부분 월이다. 표시가 필요하다. **해결 (11/11):** 2011-12 막대를 회색으로 그리고 "partial month, excluded" 범례를 달았다. `f1_monthly_baskets.csv`는 그대로다.
- 가변 기본 인자 캐시와 `searchsorted` 역산은 학생이 설명하기 어렵다.

## 리뷰 이후 추가로 찾은 것 (11/5, 레포·문서 대조 점검)

- 3개 조합 개수(README Method 1, plan §1 "개수만 보조 보고")를 만드는 코드가 없다. support 1%의 빈발 3개 조합 수를 T2나 T3에 한 줄 추가한다.
- `run_all.py` T6: `agent_runs.jsonl`과 `h3_grades.csv`가 둘 다 생기면 `NotImplementedError`로 전체 실행이 멈춘다. 12/1 전까지는 경고만 출력하게 한다.
- F2: 사라진 상품 규칙 2개는 같은 쌍의 양방향이라 (0.766, 0) 한 점에 겹친다. 범례는 n=2인데 x는 하나만 보인다. 겹침을 표시하거나 주석을 단다. (범례가 점을 가리던 문제는 11/5에 범례를 왼쪽 위로 옮겨 고쳤다.)

## 초안 결과 (판정 전, 참고)

| 항목 | 값 |
|---|---|
| H1 평균 D (10 seed) | 0.162 (범위 0.108~0.214) → 기준 10%p 초과 |
| H2 규칙 − B0 | +0.048~0.051, 고객 단위 하한 최소 0.0436 → 기준 +2%p 통과 |
| T5 판정 줄 5개 | 모두 "안 바뀜" (n_boot=100) |
| PCY B=1,048,573 빈발 버킷 비율 | 1%에서 0.08%, 0.25%에서 5.4% |
| 셔플 null 우연 규칙 비율 | 주 0%, 0.25% 0.34%, B1 95%, 성수기 4.4% |
