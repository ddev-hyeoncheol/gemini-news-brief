# CLAUDE.md

이 프로젝트에서 Claude가 따라야 할 규칙입니다.

## 프로젝트 설명

Gemini News Brief는 구글 클라우드 플랫폼(GCP) 환경에서 뉴스를 자동으로 수집 및 가공하고, 이를 API로 제공하는 서버리스(Serverless) 데이터 파이프라인 프로젝트입니다.

- **백엔드**: FastAPI 기반의 비동기 API 및 수집(Worker) 서비스
- **데이터베이스**: BigQuery를 활용한 뉴스 데이터 적재 및 스키마 관리
- **인프라 철학**: 로컬 환경은 코드 개발에만 집중하고, 실행/배포/스케줄링은 Cloud Build와 Cloud Run 등 클라우드 관리형 서비스에 전적으로 위임

## 아키텍처 및 코딩 가이드라인

AI 코딩 어시스턴트는 코드를 작성/수정할 때 다음의 핵심 설계 원칙을 반드시 준수합니다.

- **진정한 병렬 파이프라인 (End-to-End Parallelism)**: 여러 뉴스 소스를 처리할 때, 일괄(Batch) 대기 방식이 아닌 각 소스별로 `[Collect(수집) -> Load(적재)]` 과정을 독립적이고 연속적으로 수행하는 비동기(`asyncio.gather`) 구조를 지향합니다.
- **지연 평가(Lazy Evaluation) 기반 흐름**: `[Fetch -> Lookup -> Enrich -> Load]`의 4단계 파이프라인 흐름을 준수합니다. DB 조회(`Lookup`)를 통해 판별된 타겟 기사에 대해서만 스크래핑(`Enrich`)을 수행하여 네트워크 낭비를 막습니다.
- **플러그인 독립적 에러 핸들링 (Resilience)**: 도메인 플러그인(`CollectPlugin`, `BigQueryPlugin`) 내부에서 발생한 예외는 상위로 던지지(Throw) 않고, 자체적으로 캡처하여 `status="failed"` (또는 `partial`)와 `error_message`를 포함한 결과 객체로 조기 반환(Early Return)합니다.
- **단계별 데이터 스키마 분리 및 네이밍**:
    - 파이프라인 단계에 따라 전용 DTO 객체를 엄격히 분리합니다 (`IngestFetchResult`, `IngestLookupResult`, `IngestEnrichResult`, `IngestLoadResult`, `IngestSourceResult`).
    - 파이프라인 퍼널(Funnel) 지표를 명확히 추적합니다: `fetched_count` -> `lookup_count` -> `enriched_count` -> `loaded_count`.
- **의존성 주입 (Dependency Injection)**: FastAPI 라우터는 비즈니스 로직(Service, Plugin)을 직접 생성하지 않고 `Depends`를 통해 주입받아 테스트 용이성(Mocking)과 결합도 감소를 달성합니다.
- **이벤트 루프 안전성 확보 (Event Loop Safety)**: `asyncio.Semaphore`와 같은 비동기 락 객체들은 모듈 레벨에서 즉시 인스턴스화하지 않고, 첫 API 요청이 들어올 때 지연 초기화(Lazy Initialization)하여 FastAPI 이벤트 루프와의 충돌을 방지합니다.
- **상황에 맞는 HTTP 상태 코드**: 전체 파이프라인 결과에 따라 `200 OK`(전체 성공), `207 Multi-Status`(부분 성공), `500 Internal Server Error`(전체 실패)를 동적으로 반환합니다.

## 문서화 및 주석 규칙 (Documentation & Comments)

- **언어**: 모든 코드 내 주석과 Docstring은 **영어(English)**로 작성합니다.
- **명령문 사용 (Imperative Mood)**: 함수와 메서드의 Docstring은 동작을 지시하는 형태(예: "Return...", "Fetch..." 등)로 작성합니다. ("Returns...", "Fetches..." 등의 3인칭 단수 사용 지양)
- **문장 부호 및 대소문자**: 일반 인라인 주석(`#`)은 첫 글자를 대문자로 시작하며, 완전한 문장일 경우 마침표(`.`)로 끝냅니다.
- **의미 중심의 설명**: 데이터 모델(`models/entities`)과 DB 스키마(`bigquery/schema`)의 설명(Description)에는 파이프라인의 내부 구현 로직보다는 **데이터 자체의 비즈니스적 의미**에 집중하여 간결하게 작성합니다.

## 커밋 규칙

Angular Commit Convention을 따릅니다.

### 형식

```
[Type] Subject

- 부가 설명 1
- 부가 설명 2

Footer
```

### Type

- `[Build]`: 빌드 시스템 또는 외부 의존성 변경
- `[CI]`: CI/CD 설정 변경
- `[Docs]`: 문서 변경
- `[Feat]`: 새로운 기능 추가
- `[Fix]`: 버그 수정
- `[Perf]`: 성능 개선
- `[Refactor]`: 리팩토링 (기능 변화 없음)
- `[Test]`: 테스트 추가 또는 수정

### 규칙

- Type은 대괄호`[]`로 묶고, 첫 글자는 대문자로 작성한다.
- Subject는 한글로 간결하게 작성한다.
- Body는 선택 사항이며, `- ` 목록으로 부가 설명을 작성한다.
- Footer는 관련 이슈 번호를 참조할 때 사용한다.
- 커밋은 하나의 목적 단위로 나누어 작성한다. 여러 변경 사항을 하나의 커밋에 묶지 않는다.
- 사용자가 명시적으로 요청하지 않는 한, 원격 저장소에 Push 하지 않는다.
- 커밋 메시지에 Co-Authored-By를 포함하지 않는다.
- 커밋 메시지 예시:

    ```
    [Feat] 소셜 로그인 기능 추가

    - Google OAuth2 로그인 지원
    - GitHub OAuth2 로그인 지원
    ```
