# Solar 실행 선택 연동

H4 확장에서 쓸 알고리즘 인터페이스다. 입력은 `src.clean.load_baskets()`의
`items` 열처럼 각 장바구니가 정렬되고 중복 제거된 상품 코드 목록이다.

```python
from src.mining_job import MiningJob

job = MiningJob(baskets, support=0.01, memory_budget_bytes=32 * 1024**2)
profile = job.profile()
# Solar가 profile을 보고 아래 설정을 골랐다고 가정한다.
pilot = job.pilot("pcy_large")
job.validate_setting("pcy_large")
result = job.run("pcy_large")
```

- `profile()`은 빈발 상품 수, 평균·최대 장바구니 크기, 쌍의 등장 횟수,
  두 PCY 설정의 버킷 통과율과 관측 후보 수 추정치, 설정별 메모리 추정치를 반환한다.
- `pilot()`은 기본 1,000건까지 중복 없이 표본을 뽑는다. 같은 시드를
  쓰면 표본이 같고, 지지도 비율은 유지하면서 절대 기준 건수를 다시 계산한다.
  반환값은 집계 시간과 후보·빈발 쌍 개수 등 요약값이다.
- `run()`은 전체 장바구니를 집계한다. 반환 형식은 기존 알고리즘과 같다.
  설정은 `apriori`, `pcy_small`(65,521개), `pcy_large`(1,048,573개)다.
  Solar에는 `profile()`과 `pilot()`의 요약값만 전달하면 된다.

메모리 검증은 기존 T2 저장 공간 모델을 기준으로 한다. Apriori는 삼각
배열 크기를 쓰고, PCY는 버킷 배열과 비트맵·후보 저장 공간 중 큰 값을
쓴다. PCY의 `n_candidates_estimate`는 두 상품이 모두 빈발하고 통과 버킷에
속하는 **서로 다른 관측 쌍**을 집계한다. 같은 쌍이 여러 번 등장해도 한 번만
반영한다. 표기는 아래와 같다.

- `exact`는 가능한 빈발 상품 쌍이 16,777,216개 이하일 때 쌍마다 한 비트를
  써서 정확히 센다. 비트 배열은 PCY 설정당 최대 2 MiB다.
- `bitmap_estimate`는 더 큰 입력에서 고정 크기 해시 비트 배열을 이용해 근사한다.
  비트가 95% 이상 채워지면 `upper_bound`로 표시하고 등장 횟수 기반 상한을 반환한다.

`validate_setting()`은 정확한 후보 수가 있으면 그 값으로, 근사한 경우에는
`modeled_memory_upper_bound_bytes`로 예산을 확인한다. 이 수치는 T2의 자료구조
저장 공간 모델에 해당한다. 프로세스 최대 메모리 측정과 강제 한도는
서버·평가에서 처리하며, 전체 실행 시간 비교에는 `profile()` 비용도 포함한다.

Online Retail II의 1년 차 19,743건과 2년치 38,700건에서 지지도
2%, 1%, 0.5%, 0.25%를 검증했다. 두 PCY 설정의 프로필 후보 수는
실제 집계 후보 수와 일치했고, 세 설정의 빈발 쌍과 빈도도 일치했다.

지지도 0.25%에서 큰 버킷 PCY는 두 입력 모두 자료구조 모델 기준
4,194,292 B였다. Apriori는 1년 차 8,229,624 B, 2년치 10,039,680 B였다.
같은 조건에 모델 예산 6 MiB를 적용하면 큰 버킷 PCY만 통과한다.

시험 집계 1회, 재선택 1회 제한과 실패 시 대체 방식은 작업을 관리하는
서버·에이전트에서 적용한다. 기존 H3 조회 도구는 기존 진입점으로 실행한다.

`python -m tests.test_mining_job`으로 설정 검증, 표본 집계, 고정 방식과
빈발 쌍 및 빈도 일치를 확인할 수 있다.
