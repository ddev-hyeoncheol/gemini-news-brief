# AGENTS.md

작업 전 하네스 로드는 다음 순서로 진행합니다.

1. `.agents/rules/core.md`
2. `.agents/index.md`
3. `.agents/index.md`가 선택한 workflow/rule 파일
4. `MEMORY.md`는 `.agents/index.md`가 안내할 때만 읽습니다.

## Guardrail

- 선택한 하네스 파일 목록을 분석·도구 실행·파일 수정 전에 먼저 출력합니다.
- 출력은 `[Harness]` 제목과 실제 읽을 파일 경로의 `- ` 목록으로 작성합니다.
- `.agents/` 아래 모든 파일을 기본으로 한 번에 읽지 않습니다.
- 작업 범위가 여러 영역에 걸치면 필요한 파일만 조합해서 읽습니다.
