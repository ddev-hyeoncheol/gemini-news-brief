# Review Workflow

사용자가 리뷰를 요청하면 파일 수정 없이 코드 리뷰 관점으로 응답합니다.

## Output Order

- 지적 사항을 먼저 제시하고 심각도 순서로 정렬합니다.
- 각 지적 사항은 파일과 줄 번호, 실제 영향에 근거합니다.
- 문제가 없으면 명확히 말하고 남은 테스트 공백이나 잔여 위험을 언급합니다.
- 요약, 질문, 변경 설명은 지적 사항 뒤에만 둡니다.

## Procedure

1. 리뷰 대상 diff와 관련 현재 파일을 확인합니다.
2. `.agents/index.md`에서 대상 변경에 맞는 domain rules와 cross-cutting rules를 추가로 선택합니다.
3. 버그, 동작 회귀, 데이터 손실, 책임 경계 위반, 위험한 모호성을 먼저 찾습니다.
4. pipeline 변경은 `failed`, `partial`, `skipped`, count 의미와 HTTP 전파를 확인합니다.
5. Entity, Schema, BigQuery, Terraform 변경은 field description과 schema 동기화를 확인합니다.
6. Provider나 외부 호출 변경은 semaphore, retry, blocking I/O 배치를 확인합니다.
7. import, method order, docstring, comment, logging은 관련 rules에 맞춰 확인합니다.
8. compile, import, test 검증이 변경 위험도와 맞는지 확인합니다.

## Boundaries

- 리뷰 중 파일을 수정하지 않습니다. 사용자가 수정까지 요청하면 implement workflow로 전환합니다.
- 세부 규칙은 이 파일에 반복하지 않고 관련 rules 파일을 근거로 삼습니다.
- 테스트 누락은 구체적 동작 위험이 있으면 지적 사항으로, 단순 미실행이면 잔여 위험으로 적습니다.
