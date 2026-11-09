# 역할 ②: 독립 알고리즘 개발 모듈

A-Priori, PCY, 상품 쌍·삼중항, 연관규칙, 비교 실험을 구현했다. 기존 GitHub 구현을 수정하지 않고 별도 폴더에 작성한 코드다. 다른 담당자의 전처리·평가·Solar 구현 없이 실행할 수 있다.

Python 3.10 이상 / 실행 의존성은 표준 라이브러리뿐이다. 가상환경이나 `pip install` 없이 예제로 시작할 수 있다. 이 폴더 안에서 명령을 실행한다.

## 1. 바로 실행

PowerShell:

```powershell
cd role2_algorithms
python -m unittest discover -s tests -v
python -m basket_mining mine --algorithm apriori --input examples/baskets.json --min-count 3 --out outputs/apriori
python -m basket_mining mine --algorithm pcy --input examples/baskets.json --min-count 3 --buckets 5 --out outputs/pcy
```

각 폴더에 `itemsets.json`(빈발 항목집합·진단 지표·입력 체크섬), `rules.csv`(방향 있는 연관규칙)가 생성된다. 상품 ID 목록은 JSON 배열로 저장하므로 상품 ID에 구분 문자가 있어도 해석이 가능하다.

삼중항까지 계산:

```powershell
python -m basket_mining mine --algorithm pcy --input examples/baskets.json --min-count 2 --buckets 5 --max-size 3 --out outputs/triples
```

최소 지지도를 비율로 지정할 때는 `--min-count` 대신 `--min-support 0.01`을 쓴다. 두 옵션을 동시에 주는 것은 금지한다. 최소 횟수는 `ceil(비율 × 장바구니 수)`이며, Decimal로 계산해 흔한 부동소수점 올림 오류를 피한다.

## 2. 구조: 어디에 무엇이 있는가

```text
basket_mining/
  models.py                 자료형과 입력 계약
  thresholds.py             지지도 비율 → 최소 횟수 변환
  algorithms/
    apriori.py              A-Priori 상품 쌍 탐색만
    pcy.py                  PCY 상품 쌍 탐색·버킷·압축 비트맵만
  extensions/
    triples.py              두 알고리즘 뒤에 공통 적용하는 삼중항 확장
  rules.py                  지지도·신뢰도·향상도와 규칙 생성
  io.py                     JSON·CSV·TXT 읽기 / 결과 저장
  benchmark.py              시간·메모리 측정 / 결과 일치 확인
  __main__.py               명령행 인자를 각 기능에 연결
tests/                      손계산·독립 전수계산·경계값 검증
examples/                   같은 예제를 JSON과 주문 행 CSV로 제공
docs/learning_guide.md       코드 이해 순서와 손계산
docs/integration.md          다른 담당자와 합칠 때 바꿀 지점
```

알고리즘 파일은 파일을 열거나 네트워크를 호출하지 않는다. 규칙 생성은 알고리즘 구현에 포함하지 않는다. 파일 형식이 달라지면 `io.py`만 바꾸고, Solar나 API와 합칠 때는 공개 Python 함수를 호출하면 된다.

## 3. 예제의 정답

`examples/baskets.json`은 직접 만든 8개 장바구니 예제이며 교재 원문 예제를 복제한 것은 아니다.

| 항목 | 등장한 장바구니 수 |
|---|---:|
| a / b / c / d / e | 각각 5 / 5 / 4 / 3 / 2 |
| ab / ac / bc | 각각 4 / 3 / 3 |
| ad / bd / cd / de | 각각 2 / 2 / 1 / 1 |

최소 횟수 3이면 빈발 쌍은 `ab:4, ac:3, bc:3`이다. 최소 횟수 2이면 빈발 삼중항은 `abc:2, abd:2`다. `a → b`는 Support=0.5, Confidence=0.8, Lift=1.28이다. 이는 구매 순서나 인과를 의미하지 않는다.

## 4. 비교 실험

빠른 예제 실험:

```powershell
python -m basket_mining benchmark --input examples/baskets.json --supports 0.375 0.25 --buckets 1 5 101 --repeats 3 --out outputs/benchmark
```

`comparison.csv`와 `environment.json`을 생성한다. 모든 조건에서 PCY의 최종 빈발 항목집합을 A-Priori와 대조하며, 다르면 실험이 실패한다. 독립적인 정답은 별도의 테스트에서 전수 계산과 비교한다.

팀의 실험 조건 예시:

```powershell
python -m basket_mining benchmark --input YOUR_BASKETS.json --supports 0.02 0.01 0.005 0.0025 --buckets 65521 1048573 --repeats 5 --out outputs/full_benchmark
```

`YOUR_BASKETS.json`은 실제 파일 경로로 교체한다. 먼저 작은 데이터로 검증한 뒤 전체 데이터를 실행한다. 버킷 1개는 충돌 검증용이며 실제 속도 개선을 기대하는 설정이 아니다.

### 결과 열의 뜻

| 열 | 정의 |
|---|---|
| possible_frequent_item_pairs | 빈발 단일 상품 m개로 가능한 쌍 C(m,2). PCY 가지치기 이전의 공통 기준 |
| pair_candidates_observed | 각 방법의 필터 후 쌍 카운터에 실제로 들어간 서로 다른 쌍 수 |
| pair_occurrences_examined | 2차 패스에서 검사한 빈발 상품 쌍의 출현 횟수. 같은 쌍이 여러 바구니에 있으면 여러 번 |
| pair_count_updates | 필터 후 실제 쌍 카운트를 증가시킨 횟수 |
| frequent_bucket_ratio | 빈발 버킷 수 / 전체 버킷 수. A-Priori에는 해당 없음 |
| bucket_counter_bytes | PCY 1차 패스의 정수 배열 데이터 공간. 전체 메모리 아님 |
| bitmap_payload_bytes | 실제로 압축된 비트맵의 데이터 공간: ceil(B/8). 객체 오버헤드 제외 |
| median_seconds | 워밍업 1회 후 반복 실행한 시간의 중앙값 |
| tracemalloc_peak_bytes | 별도 실행에서 추적한 최대 할당량. 미리 읽은 입력 메모리는 제외되며 전체 프로세스 RAM/RSS와 다름 |

두 구현 모두 같은 `Counter` 기반 희소 카운팅을 사용한다. A-Priori의 삼각 행렬 버전과 비교하는 실험은 아니다. PCY도 모든 쌍을 훑는 비용과 해싱 비용이 있으므로 항상 빠르거나 메모리를 덜 쓴다고 가정하지 않는다. 작은 표본의 실행 시간으로 전체 데이터 성능을 주장하지 않는다.

## 5. 입력·정책·범위

- 한 장바구니에서 상품을 여러 개 사도 한 번만 센다. 정렬과 중복 제거는 공통 입력 정규화 단계에서 한다.
- 정수 ID와 문자열 ID는 문자열로 변환한다. `1`과 `"1"`은 같은 상품으로 취급한다. 앞뒤 공백을 제거한다. 결측·빈 상품 ID는 오류다.
- Python/JSON 입력의 빈 장바구니는 분모에 포함한다. TXT의 빈 줄은 서식으로 취급해 건너뛰고, 주문 행 CSV는 빈 바구니를 표현할 수 없다. 빈 바구니가 의미 있으면 JSON 또는 Python API를 쓴다.
- CSV는 `basket_id,product_id` 열이 필요하다. 원본 엑셀의 취소·반품·비상품 처리나 날짜 분리는 ① 담당자가 수행한다.
- TXT는 한 줄에 공백으로 구분된 상품 ID 집합이다. SPMF의 순차 패턴·효용 데이터 형식은 직접 읽지 않으며 별도 어댑터가 필요하다.
- 기본 max_size는 2이고 옵션 3까지 지원한다. 4개 이상 항목집합은 지원 범위 밖이다.
- PCY는 상품 쌍에 적용한다. 삼중항은 두 알고리즘이 찾은 빈발 쌍에서 공통 A-Priori 방식으로 확장한다.
- 연관규칙은 `confidence >= min_confidence`, `lift >= min_lift`로 필터한다. 기본값은 0.5와 1.0이다. 팀의 기존 코드가 `lift > 1`이면 경계 정책을 합의해 변경해야 한다.
- 재현 가능한 교육용 인메모리 구현이다. 입력 전체·카운터·삼중항 후보가 RAM에 들어가야 한다. 스트리밍·분산 서버·멀티스레드 버전은 구현하지 않았다.
- 이미 만들어진 팀 코드와 달리 공통 희소 카운터와 실제 압축 비트맵을 사용한다. 기존 결과 CSV와 숫자·성능 열이 일치한다고 가정하지 않는다.

## 6. 읽기 시작할 곳

먼저 [학습 안내](docs/learning_guide.md)를 따라 예제와 `apriori.py`를 읽는다. 다음은 `pcy.py`, `rules.py`, 삼중항 확장 순서다. 통합 작업은 [연결 안내](docs/integration.md)를 참고한다. 팀 공통 코드와 독립된 역할 ② 구현이다.
