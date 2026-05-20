# Harness Documentation Rules

하네스 문서를 추가하거나 수정할 때만 읽습니다.

## File Roles

- `AGENTS.md`: 하네스 진입점입니다. 항상 읽을 파일만 안내합니다.
- `.agents/index.md`: 작업별로 읽을 문서를 안내하는 라우터입니다.
- `.agents/rules/`: 오래가는 작업 규칙을 둡니다.
- `.agents/workflows/`: 순서가 중요한 작업 절차를 둡니다.
- 판단 기준: 항상 지켜야 할 제약은 rules, 순서대로 수행할 작업은 workflows에 둡니다.
- `MEMORY.md`: 현재 상태, 임시 합의, 진행 중인 방향을 둡니다.
- `CONTRIBUTING.md`: 사람과 AI가 함께 따르는 기여 규칙의 원본입니다.

## Writing Style

- Markdown header는 영어로 작성합니다.
- 본문 설명은 한국어로 작성합니다.
- 코드 식별자, 명령, 경로, 로그 예시는 원문 그대로 작성합니다.
- 규칙은 짧고 판단 가능하게 씁니다.
- 일반론보다 이 저장소에서 틀리기 쉬운 내용을 우선합니다.

## Size

- `AGENTS.md`는 20줄 이하를 목표로 합니다.
- `.agents/index.md`에는 라우팅만 둡니다.
- 개별 rules/workflows 파일은 가능하면 60줄 이하로 유지합니다.
- 파일이 커지면 역할 기준으로 분리합니다.

## Duplication

- 같은 규칙은 한 곳만 canonical로 둡니다.
- 다른 파일에서는 링크나 짧은 포인터만 둡니다.
- 프로젝트 상태나 임시 결정은 rules가 아니라 `MEMORY.md`에 둡니다.
- commit 규칙처럼 사람과 AI가 함께 따르는 규칙은 `CONTRIBUTING.md`를 canonical로 둡니다.

## Maintenance

- 하네스 파일을 추가, 삭제, 이동하면 `.agents/index.md`의 라우팅을 함께 확인합니다.
- 파일명이나 규칙명을 바꾸면 `AGENTS.md`, `MEMORY.md`, `.agents/`, `CONTRIBUTING.md`에 남은 stale reference를 검색합니다.
- `MEMORY.md`는 현재 방향이나 임시 결정이 작업 결과에 영향을 줄 때만 읽도록 라우팅합니다.
