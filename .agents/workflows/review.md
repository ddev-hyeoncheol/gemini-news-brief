# Review Workflow

사용자가 리뷰를 요청하면 코드 리뷰 관점으로 응답합니다.

- 지적 사항을 먼저 제시하고 심각도 순서로 정렬합니다.
- 각 지적 사항은 파일과 줄 번호에 근거합니다.
- 버그, 동작 회귀, 책임 경계 위반, 누락된 테스트, 위험한 모호성을 우선합니다.
- 문제가 없으면 명확히 말하고 남은 테스트 공백이나 잔여 위험을 언급합니다.

체크리스트:

1. 책임 경계와 target 처리가 `.agents/rules/architecture.md`와 맞는지 확인합니다.
2. import, method order, docstring, comment, logging이 `.agents/rules/style.md`와 맞는지 확인합니다.
3. `failed`, `partial`, `skipped` 상태 결정과 전파를 확인합니다.
4. Entity, Schema, Terraform description 변경 필요 여부를 확인합니다.
5. semaphore, retry, blocking I/O 배치를 확인합니다.
6. compile, import, test 검증이 변경 범위와 맞는지 확인합니다.
