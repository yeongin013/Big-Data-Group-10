# A-Priori / PCY

상품 쌍과 삼중항을 찾고 연관규칙을 계산하는 코드다. 알고리즘, 규칙 계산, 파일 입출력, 성능 측정을 나눠 작성했다.

기존 프로젝트에서는 `src/apriori.py`, `src/pcy.py`를 그대로 호출하면 된다. 두 파일이 이 폴더의 구현을 연결한다.

## 실행

아래 예제는 Python 3.10 이상에서 추가 패키지 없이 실행할 수 있다. 저장소 루트에서 시작한다.

```powershell
cd role2_algorithms
python -m unittest discover -s tests -v
python -m basket_mining mine --algorithm apriori --input examples/baskets.json --min-count 3 --out outputs/apriori
python -m basket_mining mine --algorithm pcy --input examples/baskets.json --min-count 3 --buckets 5 --out outputs/pcy
```

결과는 `itemsets.json`과 `rules.csv`에 저장된다. 삼중항까지 구하려면 `--max-size 3`을 추가한다. 지지도 비율을 쓸 때는 `--min-count` 대신 `--min-support 0.01`을 지정한다.

## 파일 구성

| 파일 | 내용 |
|---|---|
| `basket_mining/models.py` | 장바구니와 결과 자료형 |
| `basket_mining/thresholds.py` | 지지도 비율을 최소 등장 횟수로 변환 |
| `basket_mining/algorithms/apriori.py` | A-Priori 쌍 탐색 |
| `basket_mining/algorithms/pcy.py` | PCY 쌍 탐색, 버킷과 비트맵 |
| `basket_mining/extensions/triples.py` | 빈발 쌍에서 삼중항으로 확장 |
| `basket_mining/rules.py` | Support, Confidence, Lift 계산 |
| `basket_mining/io.py` | 입력 읽기와 결과 저장 |
| `basket_mining/benchmark.py` | 시간·메모리 측정 |

## 예제 결과

`examples/baskets.json`에는 8개 장바구니가 있다.

- 상품 빈도: a=5, b=5, c=4, d=3, e=2
- 최소 횟수 3의 빈발 쌍: ab=4, ac=3, bc=3
- 최소 횟수 2의 빈발 삼중항: abc=2, abd=2
- a → b: Support=0.5, Confidence=0.8, Lift=1.28

## 성능 비교

```powershell
python -m basket_mining benchmark --input examples/baskets.json --supports 0.375 0.25 --buckets 1 5 101 --repeats 3 --out outputs/benchmark
```

`comparison.csv`와 `environment.json`을 만든다. PCY와 A-Priori의 최종 항목집합이 다르면 중단한다. 입력 파일을 실제 장바구니 파일로 바꿔 같은 명령으로 실험할 수 있다.

| 주요 결과 열 | 의미 |
|---|---|
| `possible_frequent_item_pairs` | 빈발 상품 m개로 가능한 쌍 C(m,2) |
| `pair_candidates_observed` | 필터 후 실제 카운팅한 서로 다른 쌍 수 |
| `pair_occurrences_examined` | 2차 패스에서 검사한 쌍의 총 출현 횟수 |
| `pair_count_updates` | 필터를 통과해 카운트를 증가시킨 횟수 |
| `frequent_bucket_ratio` | 빈발 버킷 비율 |
| `bucket_counter_bytes` / `bitmap_payload_bytes` | PCY 배열 / 압축 비트맵의 데이터 크기 |
| `median_seconds` | 워밍업 1회 후 반복 측정한 시간의 중앙값 |
| `tracemalloc_peak_bytes` | 별도 실행에서 추적한 최대 메모리 할당량 |

시간과 메모리 측정에서 입력 파일 읽기와 정규화는 제외한다. `tracemalloc` 값은 전체 프로세스 RAM 사용량과 다르다. 두 방법 모두 희소 `Counter`를 사용하며 PCY가 항상 빠르다고 가정하지 않는다.

## 입력과 계산 기준

- JSON: 상품 목록의 목록. 예: `[["a", "b"], ["b", "c"]]`
- CSV: `basket_id,product_id` 열을 가진 주문 행 데이터.
- TXT: 한 줄에 공백으로 구분한 상품 ID. 순차 패턴·효용 데이터 형식은 지원하지 않는다.
- 상품 ID는 문자열로 바꾸고 앞뒤 공백과 바구니 안의 중복을 제거한다. 정수 `1`과 문자열 `"1"`은 같은 상품이다.
- JSON과 Python 입력의 빈 바구니는 분모에 포함한다. TXT의 빈 줄은 건너뛰며 주문 행 CSV는 빈 바구니를 표현하지 못한다.
- 삼중항은 두 방법 모두 빈발 쌍을 이용한 A-Priori 방식으로 확장한다.
- 이 모듈의 기본 필터는 Confidence ≥ 0.5, Lift ≥ 1이다. 기존 `src/apriori.rules()`에서는 팀 기준인 Lift > 1을 유지한다.

현재는 입력과 후보를 메모리에 올리는 방식이다. 전체 데이터 성능은 별도 측정이 필요하다.

[알고리즘 설명](docs/learning_guide.md) · [팀 코드 연결](docs/integration.md) · [검증 기록](docs/validation.md)
