# 팀 통합 안내

## 담당 경계

이 모듈의 책임은 정제된 바구니를 받아 항목집합·연관규칙을 계산하는 것이다. 원본 엑셀 처리, 날짜 분할, 통계적 기간 검증, 인기 상품 추천 기준선, Solar 호출은 포함하지 않는다. 나중에 합칠 때 이 Python API 앞뒤에 어댑터를 붙이면 된다.

## 기본 연결 예제

이 폴더에서 실행하거나, 팀 프로젝트에 `basket_mining` 패키지를 넣고 사용한다.

```python
from basket_mining import BasketDataset, mine_apriori, mine_pcy
from basket_mining import generate_rules, support_to_count

# ① 담당자가 만든 특정 기간의 장바구니 목록
rows = [("85123A", "22423"), ("85123A", "22423"), ("22423",)]
dataset = BasketDataset.from_rows(rows)
threshold = support_to_count(len(dataset), "0.5")

apriori = mine_apriori(dataset, min_count=threshold)
pcy = mine_pcy(dataset, min_count=threshold, n_buckets=65521)
assert apriori.frequent_itemsets == pcy.frequent_itemsets
rules = generate_rules(pcy, min_confidence=0.5, min_lift=1.0)

# ③·④ 담당자가 변환해 사용할 객체
for rule in rules:
    print(rule.antecedent, rule.consequent, rule.support, rule.confidence, rule.lift)
```

## 반환값

`MiningResult`:

- `item_counts`: 전체 단일 상품의 등장 횟수. 빈발 여부와 무관하게 포함.
- `frequent_itemsets`: `(상품, ...)` 정렬 튜플 → 등장 횟수. 빈발 1개·2개·옵션 3개 항목집합 포함.
- `of_size(2)`: 빈발 상품 쌍만 선택.
- `n_baskets`, `min_count`, `max_size`: 분석 기준.
- `stats`: 진단 수치. 상대 팀의 기존 이름과 같다고 가정하지 않는다.

`Rule`은 antecedent·consequent 튜플과 count·support·confidence·lift를 가진다. 상품명, 기간, 데이터 버전, 검증 결과, 최종 rule_id는 통합 단계에서 추가한다. 두 원본 코드가 공백 제거/문자열 변환으로 같아지는 정책도 확인한다.

## 합칠 때 결정할 사항

1. 최소 지지도를 바구니 수 기준으로 계산하며, 빈 바구니를 분모에 포함할지 맞춘다.
2. ①의 코드에서 이미 중복을 제거해도 여기서 다시 정규화할 수 있다. 성능 실험에서는 공통 입력 생성 후 각 함수를 비교한다.
3. 기존 GitHub는 Lift > 1, 이 모듈은 Lift >= min_lift의 포괄 경계다. 어떤 규칙을 채택할지 팀에서 명시한다.
4. 삼중항은 옵션이다. 기존 서비스가 단일 상품→단일 상품만 지원하면 먼저 쌍 규칙만 전달한다.
5. 성능 보고서의 후보 수 정의를 통일한다. 가능한 쌍과 관측한 쌍, 쌍 출현 횟수를 섞지 않는다.
6. 기존 결과 파일을 덮어쓰지 말고 별도 출력 폴더에서 재생성 후 차이를 확인한다.

## 이 프로젝트의 PCY 구현 선택

두 방법을 같은 희소 `Counter` 자료구조로 구현했다. 교재의 삼각 배열 A-Priori 대비 12바이트 후보 triple PCY라는 메모리 모델을 그대로 재현한 구현이 아니다. 최종 답의 정확성은 동일한 원리를 따르지만 실제 실행 시간은 Python 코드·자료구조·바구니 분포에도 영향을 받는다.

이 모듈은 학습과 역할 분리를 위한 초기 구현이다. 전체 UCI 데이터 성능과 팀의 최종 통합 결과는 해당 데이터·환경에서 다시 검증해야 한다.


## Hyeonseop 브랜치의 팀 연결

`src/apriori.py`, `src/pcy.py`는 이 독립 모듈을 호출하는 호환 어댑터로 교체했다.
기존 `run()`, `rules()`, `compare()` 호출은 유지된다. 기본은 상품 쌍이며 `run(..., max_size=3)`으로 삼중항도 반환한다.
팀 어댑터의 규칙은 기존과 같이 `lift > 1`을 유지한다. 독립 API 기본은 `lift >= 1`이다.
T2의 `n_candidates`는 두 알고리즘 모두 관측된 후보 종류 수다. PCY의 모든 가능한 통과 후보 수는 타이밍에 O(m²) 진단을 섞지 않도록 비교 CSV에서 비워 둔다.
기존 memory_bytes는 교재식 이론 모델로 남기고 memory_kind 열로 구분했다. 실제 PCY 배열 payload와 압축 비트맵 크기는 별도 열이다.
새 비교 코드는 이전 NumPy 벡터화 구현과 달라 속도와 측정값이 바뀐다. 기존 results 파일은 변경하지 않았으며 새 환경에서 T2를 다시 실행해야 한다.
독립 모듈만 복사하면 팀 어댑터가 실행되지 않으므로 통합 시 role2_algorithms/basket_mining 폴더도 함께 유지한다.

추가 검사: `python -m tests.test_role2_integration` (저장소 루트).
