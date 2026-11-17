# Upstage 이용 조건 확인

- 확인일: 2026-11-11 (KST). Solar 접속 시험 성공: 일반 응답과 자동 도구 선택에 성공했고, 요청 모델은 solar-pro4, 응답 모델은 solar-pro4-260806이었다. 결과는 results/agent_runs.jsonl에 기록했다.
- [Upstage 이용약관, 2026-05-06](https://www.upstage.ai/terms-of-service/update-may-06-2026), 제22조: 일반적인 입력·출력 데이터는 서비스 제공·운영에 필요한 범위의 예외를 두고 저장하지 않으며, 별도 사전 동의가 없으면 서비스 개선이나 학습에 쓰지 않는다고 명시한다. 무료 서비스에는 서비스 개선과 AI 연구·학습을 위한 이용 예외가 있다.
- [Upstage 개인정보 처리방침, 2026-11-02](https://www.upstage.ai/privacy-policy/updated-nov-02-2026): 무료 티어 API 요청·응답 데이터 처리와 API 로깅을 별도로 기재한다. 별도 동의 여부는 확인하지 않았다.
- 2026-11-17 Upstage Console Billing 확인: Default Organization에 무료 Welcome coupon 크레딧이 있고, 등록된 결제수단·자동 충전·결제 내역은 없었다. 화면에 별도 요금제 명칭은 표시되지 않았으므로 무료 크레딧 이용 상태로 기록한다. 무료 서비스의 데이터 이용 예외를 고려해 고객 관련 정보를 보내지 않는다.
- [공식 도구 호출 문서](https://console.upstage.ai/docs/capabilities/generate/tool-calling)는 Chat Completions와 `solar-pro4` 도구 호출 예시를 제공한다. 문서 확인만으로 실제 접속 성공을 의미하지 않는다.
- 프로젝트에서 API로 보내는 데이터는 상품 단위 규칙표와 질문으로 제한하고 고객 관련 정보를 보내지 않는다. 질문에도 고객 관련 정보를 넣지 않는다.
