# H4 Solar 선택 연동 초안

기존 H3 에이전트를 바꾸지 않는 별도 모듈 `src.mining_selection`이다. `MiningSelector(job, strategy, emit=...)`에 `MiningJob`과 선택 이력 저장 콜백을 넘긴다. `select()`는 실행 설정을 반환한다. 서버가 프로세스 실행 실패를 감지하면 같은 객체의 `reselect(failed_setting, reason)`을 최대 한 번 호출한다. 작업 저장, 재시작 복구, 프로세스 격리와 정확한 최대 메모리 측정은 서버 담당이 구현한다.

- `rules`: 모델 메모리 예산을 통과한 설정 중 Apriori, 작은 PCY, 큰 PCY 순서로 선택한다. 팀의 비교 기준으로 확정됐다(결정 A, 11/24, `reviews/h4_progress.md`).
- `solar_once`: 표본 시험 없이 Solar에 한 번 선택을 요청한다.
- `solar_pilot`: Solar가 `pilot`을 최대 한 번 요청하고 `choose`로 최종 선택한다. 표본 결과는 전체 결과가 아님을 표시한다. 전체 실행 실패 시 재선택을 한 번 지원한다.
- Solar 오류, 타임아웃 또는 잘못된 선택이 계속되면 유효한 규칙 기반 설정으로 전환한다. 예산 내 설정이 없으면 실패한다. 메모리 검사는 `MiningJob` 모델 추정치이며 OS 강제 한도가 아니다.
- `history`에는 `profile`, `pilot`, `solar_choice`, `invalid_tool_call`, `reselection`, `fallback`, `selected`, `failed` 이벤트가 순서대로 쌓이고, `emit(event)`으로 서버에 전달할 수 있다. profile과 pilot은 상품별 고객 데이터가 아닌 집계만 포함해야 한다.

시연 화면은 `POST /api/jobs`에 `dataset`, `support`, `memory_budget_bytes`, `strategy`, 선택적 ISO 8601 `deadline`을 보낸다. 응답의 `id` 또는 `job_id`, `status`, `history`를 표시하고, 완료 후 `GET /api/jobs/{id}/results` 링크를 노출한다. SQLite 작업 서버(`src/jobs.py`)와 이 엔드포인트는 11/24에 만들어 연결했다. 화면에서 제출한 작업이 완료까지 가는 것은 11/25에 확인했다(`reviews/h4_progress.md`). CSV는 `GET /api/jobs/{id}/results?format=csv`로 받는다. `deadline`은 저장만 하고 적용하지 않는다.

검증: `python -m tests.test_mining_selection`, `python -m tests.test_mining_job`, `python -m tests.test_jobs`. 테스트는 공개되지 않은 H3 질문과 정답지를 사용하지 않는다. 선택 후 전체 집계는 작업 서버의 별도 프로세스에서 실행해야 한다.
