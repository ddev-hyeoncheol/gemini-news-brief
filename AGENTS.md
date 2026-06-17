# AGENTS.md

사용자의 매 요청(새로운 메시지와 대화 턴)마다, 이전에 같은 파일을 읽었더라도 하네스 로드를 생략하지 않습니다.

1. `.agents/rules/core.md`
2. `.agents/index.md`
3. `.agents/index.md`가 선택한 workflow/rule/context 파일
4. `MEMORY.md`는 `.agents/index.md`가 안내할 때만 읽습니다.

## Guardrail

- **[CRITICAL]** 최초 분석·도구 실행·파일 수정 전에 `.agents/rules/core.md`와 `.agents/index.md`를 `[Harness]`로 가장 먼저 출력합니다.
- `.agents/index.md` 확인 후 추가로 읽을 파일이 있으면 읽기 전에 `[Harness]`로 추가 출력합니다.
- 출력은 `[Harness]` 제목과 실제 읽을 파일의 저장소 기준 상대 경로의 `- ` 목록으로 작성합니다.
- `.agents/` 아래 모든 파일을 기본으로 한 번에 읽지 않습니다.
- 작업 범위가 여러 영역에 걸치면 필요한 파일만 조합해서 읽습니다.
