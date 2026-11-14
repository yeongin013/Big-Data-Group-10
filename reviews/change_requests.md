# 담당자별 수정 요청 (2026-11-14)

근거: [`merge_review.md`](merge_review.md) (브랜치 병합 검토, 11/11)와 [`draft1_review.md`](draft1_review.md) (1차 리뷰)에서 아직 열려 있는 항목. 11/14 기준으로 `Hyeonseop`(f874e91)과 `goeun`(db57a5f)에는 11/11 이후 새 커밋이 없다. `yuchan-final`에는 11/14에 `dcd8756`이 올라왔다 (유찬 절 끝의 "11/14 커밋 `dcd8756` 검토" 참고).

진행 방법:

1. 각자 자기 브랜치에서 아래 항목을 고치고 푸시한다.
2. 고친 항목은 이 파일의 체크박스를 채우거나 PR 설명에 번호로 적는다.
3. 최영인이 `Hyeonseop` → `goeun` → `yuchan-final` 순서로 병합한다.
4. 병합 뒤 기준 수치(빈발 상품 713, 빈발 쌍 585, 규칙 189, Y2 유지 134/189, PCY 후보 1,238)가 그대로인지 확인한다.

## 이현섭 (A-Priori·PCY, `Hyeonseop`)

판정: 수정 후 병합.

- [ ] 1. A-Priori 2차 패스를 `Counter`에서 삼각 배열로 되돌린다 (계획 §3.1, 11/11 결정).
- [ ] 2. 구현을 `src/` 한 곳에 둔다. `role2_algorithms/`의 핵심을 옮기고 io, CLI, examples, docs는 지운다.
- [ ] 3. PCY `n_candidates_all`을 `main` 정의로 되돌리고 `possible_frequent_item_pairs` 열을 지운다. `apriori.run()`의 `n_candidates`는 실제로 나타난 후보 수(1%에서 252,748)로 맞춘다.
- [ ] 4. 두 알고리즘을 같은 방식(numpy)으로 맞춘 뒤 실데이터로 `python -m src.run_all --only T2`를 돌리고, 시간 결과를 PR 설명에 적는다. 지금 브랜치는 T2가 645초 걸리고 "PCY가 빠르다"는 결론이 뒤집힌다.
- [ ] 5. T2 출력에 support 1%의 빈발 3개 조합 수(103개)를 한 줄 넣는다 (11/11 결정).
- [ ] 6. `tests/test_textbook.py`에 confidence 필터로 걸러지는 규칙이 생기는 예제를 넣는다. MMDS Example 6.1과 대조하는 테스트가 있으면 더 좋다 (1차 리뷰 #6).

## 정고은 (Solar 에이전트·API, `goeun`)

판정: 수정 후 병합.

- [ ] 1. `season_filter`가 기간을 파싱하게 한다.
  - 315개를 반환하는 입력: 성수기 표현("christmas season", "peak season", "크리스마스 성수기" 등), "2009-12", "2010-11", "december 2009", "november 2010"
  - 0개를 반환하는 입력: 그 밖의 연도나 계절
  - 도구 설명에 허용 값을 적고, 라우터도 같은 파서를 쓴다
  - 테스트에 7개 경우를 넣는다: "christmas 2011", "summer season", "november 2010", "christmas season", "peak season", "크리스마스 성수기", "Christmas 2010"
- [ ] 2. 시스템 프롬프트에 "A → B means baskets with A also contain B; there is no order"를 넣는다. 접속 테스트에서 모델이 전건을 "먼저 산 상품"으로 설명했다.
- [ ] 3. `top_rules` 도구 안에서 limit을 1~500으로 제한한다. 지금은 API에서만 막아서, Solar가 도구를 직접 부르면 막히지 않는다.
- [ ] 4. `--eval`은 `--key`를 필수로 받는다. 질문 파일 SHA, 실행 ID, HTTP 재시도를 기록한다 (1차 리뷰 #9).
- [ ] 5. `--ping` 도움말과 docstring을 실제 동작(`agent_runs.jsonl`, `tool_choice: "auto"`)에 맞춘다. T6과 채점에서는 `method == "ping"`인 행을 건너뛴다.
- [ ] 6. `plan/upstage_terms_check.md`에 11/11 ping 결과와 계정 요금제를 적고 `reviews/`로 옮긴다. 지금 문서의 "실제 API 접속은 아직 수행하지 않았다"는 같은 브랜치의 ping 기록과 모순된다.
- [ ] 7. `src/api.py`
  - POST는 `application/json`만 받는다
  - Host가 127.0.0.1이나 localhost가 아니면 403을 낸다
  - `Content-Length`가 잘못되면 500이 아니라 400을 낸다
- [ ] 8. 데모 예시 문장 "What should we bundle for the Christmas season?"을 다른 문장으로 바꾸고 README의 해당 문장도 고친다. 노출된 옛 H3 질문과 글자까지 같다.
- [ ] low. `rules_y1.csv`, `rules_season.csv`를 `run_all`이 만들게 한다 (1차 리뷰 #11).
- [ ] low. 라우터가 support 숫자를 confidence로 넣는 문제를 고친다. 끝에 공백이 있는 상품명 22개도 매칭되게 한다.
- [ ] low. 기록하는 모델 ID를 상수가 아니라 응답 값으로 남긴다.

H3 질문과 정답지는 `agent-v1` 태그 전까지 에이전트 담당에게 공개하지 않는다 (계획 §3.4). 위 항목은 1차 리뷰와 병합 검토에서 나온 것이고, 새 질문 세트와는 관계없다.

## 유찬 (규칙 검증·기준선·측정, `yuchan-final`)

판정: 일부만 수정 후 병합.

- [ ] 1. `src/evaluate.py:197-198`의 `seed=` 인자를 지워 bootstrap seed를 0으로 되돌린다 (계획 §3.2).
- [ ] 2. `results/`의 `null_check.csv`, `t5_sensitivity.csv`, `timings.csv`를 `main` 버전으로 되돌린다. 다시 재는 것은 알고리즘 브랜치를 병합한 뒤 기준 PC(최영인의 Mac)에서 한다.
- [ ] 3. H3 파일 5개를 PR에서 뺀다: `tests/h3_questions.csv`, `tests/h3_answer_key.csv`, `results/h3_grading.csv`, `results/h3_router_runs_v2.jsonl`, `scripts/grade_h3.py`. 히스토리는 그대로 둔다.
- [ ] 4. T5 bootstrap을 100회에서 1,000회로 바꾼다 (계획 §6, 1차 리뷰 #8).
- [ ] 5. `tests/test_evaluate.py`에 `_split` off-by-one, `_ci`, `top5_filter`, `drop_top1pct`, `merge_same_day`, changed 플래그 테스트를 넣는다 (1차 리뷰 #7).
- [ ] 6. T3에 상품 support 최댓값(0.162)을 넣는다. `timings.csv`의 CPU를 "arm" 대신 실제 모델명으로 적는다.
- [ ] 7. `run_all.py` T6: `agent_runs.jsonl`과 `h3_grades.csv`가 둘 다 있으면 `NotImplementedError`로 멈추지 말고 경고만 낸다.
- [ ] 8. 새 H3 질문 초안을 검토한다. 파일은 레포 밖에 있고, 최영인이 따로 공유한다. 11/17에 질문 파일 SHA-256을 커밋한다.
- [ ] 선택. 새 입력 검사를 확인하는 테스트를 1~2개 넣는다.

### 11/14 커밋 `dcd8756` 검토 ("Submit weekly T3 and T5 results")

이 커밋은 `results/`의 CSV 3개(`null_check.csv`, `t5_sensitivity.csv`, `timings.csv`)만 바꿨다. 위 요청은 모두 그대로 열려 있다.

- 요청 2와 반대다. 세 CSV를 `main` 버전으로 되돌리지 않고, 다른 기기에서 다시 만들어 덮어썼다.
- `null_check.csv`의 `support_0.25`, `b1` 행이 100회에서 20회로 줄었다. 11/11 결정은 100회 유지다. 1회 시간도 `main`보다 2~5배 길다(`b1` 25.9초 대 5.5초).
- CSV를 브랜치 코드로 다시 만들 수 없다. `null_check.csv`에 `max_product_support` 열이 생기고 `seconds` 열이 없어졌다. 그런데 브랜치의 `src/`에는 `max_product_support`를 만드는 코드가 없고, `null_model.py:132`는 아직 `seconds`를 쓴다. 커밋하지 않은 코드로 만들었거나 손으로 고친 파일이다.
- `t5_sensitivity.csv`의 `min_ci_cust_lo`가 바뀌었다(기준 줄 0.04336 → 0.04360). 요청 1(seed)을 반영하지 않았기 때문이다. 판정(H1 No, H2 Yes, changed 모두 False)은 같다.
- T5 bootstrap은 여전히 100회다 (`run_all.py:108`, 요청 4).
- H3 파일 5개가 그대로 있다 (요청 3).

추가 요청:

- [ ] 9. `max_product_support`를 만드는 코드를 커밋한다 (요청 6의 일부). 결과 CSV는 코드와 함께만 바꾼다.
- [ ] 10. `dcd8756`의 CSV 3개를 `main` 버전으로 되돌린다. 결과는 병합 뒤 기준 PC에서 `run_all`로 다시 만든다.

## 최영인 (데이터·재현)

- [x] 재현 1차 리허설 (T1, T2, 11/14). clean clone 결과가 커밋된 CSV와 같다. 다른 것은 기기마다 다른 `timings.csv`뿐이다.
- [x] `scripts/download_data.py`가 certifi 인증서 묶음을 쓴다. 리허설에서 python.org Python이 `CERTIFICATE_VERIFY_FAILED`로 멈춘 문제를 고쳤다.
- [x] H3 질문 30개 초안 (레포 밖)
- [ ] 위 수정 요청을 각 담당자에게 전달한다.
- [ ] 유찬 검토 뒤 질문 파일 SHA-256을 커밋한다 (11/17).
- [ ] 수정이 들어오면 세 브랜치를 순서대로 병합하고, 기준 PC에서 `run_all` 전체를 다시 돌려 `results/`를 커밋한다.
- [ ] 문서에 12주차 리포트를 쓴다 (11/16).
- [ ] low. 보고서에 계획 수치 정정 주석을 단다: 상품 4,877 → 4,707, 최대 장바구니 1,108 → 1,106. 캐시 이름(`lines_`, 계획은 `baskets_`) 차이도 적는다.
