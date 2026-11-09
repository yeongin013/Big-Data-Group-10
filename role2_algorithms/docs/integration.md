# 팀 코드 연결

`src/apriori.py`와 `src/pcy.py`는 기존 호출 형식을 유지하면서 `role2_algorithms/basket_mining`의 함수를 사용한다. 평가·Solar 코드는 기존처럼 호출할 수 있다.

## 기존 코드에서 사용

저장소 루트에서 실행한다. 이 경로는 팀 프로젝트의 pandas·NumPy 환경이 필요하다.

```python
from src import apriori, pcy

baskets = [("22423", "85123A"), ("22423", "85123A"), ("22423",)]
threshold = apriori.min_count(len(baskets), 0.5)
a = apriori.run(baskets, threshold)
p = pcy.run(baskets, threshold, n_buckets=65521)
assert a["pairs"] == p["pairs"]
rules = apriori.rules(a["pairs"], a["item_counts"], len(baskets))
```

`run(..., max_size=3)`을 지정하면 반환값의 `triples`에 빈발 삼중항도 들어간다. 기존 `rules()`는 쌍 규칙을 반환한다. 삼중항 규칙이 필요하면 아래 독립 API를 사용한다.

## 독립 API

저장소 루트 기준 import다. `role2_algorithms` 안에서 실행할 때는 앞의 `role2_algorithms.`를 빼면 된다.

```python
from role2_algorithms.basket_mining import BasketDataset, mine_pcy, generate_rules

dataset = BasketDataset.from_rows(baskets)
result = mine_pcy(dataset, min_count=2, n_buckets=65521, max_size=3)
rules = generate_rules(result, min_confidence=0.5, min_lift=1.0)
```

`MiningResult`의 주요 필드는 `item_counts`, `frequent_itemsets`, `stats`다. `of_size(2)`로 쌍만 선택할 수 있다. `Rule`에는 선행·후행 상품 목록, count, support, confidence, lift가 들어간다. 상품명·분석 기간·검증 결과는 연결하는 쪽에서 추가한다.

## T2 비교표에서 달라진 부분

- `n_candidates`는 두 알고리즘 모두 실제 관측한 후보 종류 수다.
- PCY의 `n_candidates_all`은 비교표에서 비워 둔다. 모든 가능한 쌍을 열거하는 진단 비용을 시간 측정에 넣지 않기 위해서다. `pcy.run()`으로 개별 실행하면 확인할 수 있다.
- `memory_bytes`와 `memory_pass*_bytes`는 기존 교재식 이론 모델이다. `memory_kind`로 구분한다.
- 실제 버킷 배열과 압축 비트맵 크기는 `actual_bucket_counter_payload_bytes`, `actual_bitmap_payload_bytes`에 기록한다. 이것도 객체 오버헤드를 포함한 전체 메모리는 아니다.
- `timings.csv`의 `tracemalloc_peak_bytes`는 실행 중 추적한 할당량이다. 입력 데이터 메모리는 제외한다.

기존 NumPy 구현과 처리 방식이 달라 실행 시간도 달라진다. 기존 결과 파일은 보관했고, 최종 보고서에 쓸 T2는 다시 실행해야 한다. 통합할 때는 `src`의 두 파일과 `role2_algorithms/basket_mining`을 함께 유지한다.

연결 검사: `python -m tests.test_role2_integration`
