# 검증 기록

## 11월 7일: 알고리즘 단독 검사

Python 3.14.0에서 실행했다.

```powershell
cd role2_algorithms
python -m unittest discover -s tests -v
```

10개 테스트가 통과했다. 무작위 데이터는 고정 시드 20261107로 100개를 만들고, 버킷 수 1·2·5·101에서 최대 삼중항까지 전수 계산과 대조했다.

확인한 항목은 손계산 빈도, 해시 충돌, 비트맵 크기 올림, 중복 제거, 빈 입력, 최소 지지도 경계, 규칙 필터, 삼중항 가지치기, 파일 입출력이다.

| 예제 실행 | 결과 |
|---|---|
| A-Priori, 최소 횟수 3 | 바구니 8개, 빈발 쌍 3개, 규칙 6개 |
| PCY, 최소 횟수 2, 버킷 5, 삼중항 포함 | 빈발 쌍 5개, 삼중항 2개, 규칙 16개 |
| 지지도 0.375·0.25, 버킷 1·5·101 비교 | 비교표 8행, 최종 항목집합 일치 |

SPMF Retail 파일 앞 1,000개 바구니도 읽어 지지도 0.02·0.01, 버킷 101·65521로 실행했다. 두 알고리즘의 결과가 일치했다. 반복 1회로 파일 연결만 확인했으므로 성능 비교 근거로 사용하지 않는다.

## 11월 9일: 팀 코드 연결 검사

`src/apriori.py`, `src/pcy.py`를 연결한 뒤 아래 검사가 모두 통과했다.

```powershell
python -m tests.test_textbook
python -m tests.test_pcy_hash
python -m tests.test_evaluate
python -m tests.test_answer_key
python -m tests.test_role2_integration
```

새 연결 테스트는 2개다. 독립 테스트 10개도 다시 통과했다. 기존 PCY 테스트의 비트맵 바이트 내림 계산은 올림으로 수정했다. 팀의 Lift > 1 기준은 유지했다.

UCI 전체 데이터와 Solar API는 아직 실행하지 않았다. 기존 결과 CSV·그래프도 변경하지 않았다.
