# Implement Workflow

기능 추가, 버그 수정, 문서 변경처럼 동작이나 산출물이 바뀌는 작업에 사용합니다.

## Procedure

1. 요청한 산출물, 변경 범위, 동작 변경 여부를 먼저 구분합니다.
2. `.agents/index.md`에서 작업에 필요한 domain rules와 cross-cutting rules를 추가로 선택합니다.
3. 관련 파일의 현재 diff와 기존 패턴을 읽고 사용자 변경과 충돌하는지 확인합니다.
4. 변경 범위는 요청된 동작과 주변 책임 경계에 맞게 좁힙니다.
5. 코드 변경은 기존 helper, factory, `.agents/rules/architecture.md`의 레이어 책임과 의존성 방향을 우선합니다.
6. 문서 변경은 canonical 원본과 중복 여부를 확인하고, 포인터로 충분한 내용은 재정의하지 않습니다.
7. 변경 후 영향 범위에 맞는 compile, import, test, 문서 검증을 실행합니다.
8. 최종 응답에 변경 요약, 검증 결과, 실행하지 못한 검증을 적습니다.

## Boundaries

- 파일 단위 요청은 `.agents/rules/core.md`의 파일 경계 우선 규칙을 따릅니다.
- 동작 보존 목적의 구조 개선은 `.agents/workflows/refactor.md`를 함께 따릅니다.
- **[CRITICAL]** 리뷰 요청은 `.agents/workflows/review.md`를 사용하고 파일 수정 없이 findings를 우선합니다.
- 현재 초점이나 임시 결정이 결과에 영향을 주면 `MEMORY.md`를 확인합니다.
