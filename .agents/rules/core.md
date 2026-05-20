# Core Rules

이 규칙은 이 저장소의 모든 작업에 적용합니다.

## Basic Behavior

- 사용자가 명시적으로 코드나 문서 변경을 요청하기 전에는 파일을 변경하지 않습니다.
- 설계나 리팩토링을 논의하는 중에는 수정안보다 문제 정의, 영향 범위, 선택지를 먼저 설명합니다.
- 사용자가 파일 단위 작업을 원하면 컴파일이 일시적으로 깨지더라도 요청한 파일 경계를 우선합니다.
- 작업 전 `git status --short`를 실행합니다.
- 사용자가 만든 변경을 되돌리지 않습니다. 관련 없는 변경은 무시하고, 관련 변경은 읽고 맞춰갑니다.
- destructive git 명령, commit, push는 사용자의 명시 요청 없이는 수행하지 않습니다.
- 의존성 설치, 네트워크 접근, 외부 서비스 호출은 사용자 승인 없이 수행하지 않습니다.

## Validation

로컬 검증은 conda 환경 `gemini-news-brief`를 사용합니다.

자주 쓰는 명령:

```bash
conda run -n gemini-news-brief python -m compileall src
conda run -n gemini-news-brief python -m compileall src/models/schemas/ingest.py
```

API import 또는 OpenAPI 검증이 필요하면 같은 conda 환경에서 실행합니다.
