# AGENTS.md

이 문서는 이 저장소에서 AI 코딩 에이전트가 따라야 할 canonical 작업 규칙입니다.

- `README.md`: 사용자·운영자를 위한 프로젝트 설명
- `AGENTS.md`: 에이전트가 분석·수정·리뷰할 때 따라야 하는 규칙
- `CLAUDE.md`: `AGENTS.md`를 가리키는 호환용 포인터

## 기본 행동 원칙

- 사용자가 명시적으로 코드 작성이나 수정을 요청하기 전에는 파일을 변경하지 않습니다.
- 설계나 리팩토링을 논의하는 중에는 수정안보다 문제 정의, 영향 범위, 선택지를 먼저 설명합니다.
- 사용자가 “파일 단위” 작업을 원하면 컴파일이 일시적으로 깨지더라도 파일 단위 변경을 우선합니다.
- 작업 전 `git status --short`로 변경 상태를 확인합니다.
- 사용자가 만든 변경을 되돌리지 않습니다. unrelated 변경은 무시하고, 관련 변경은 함께 읽고 맞춰갑니다.
- destructive git 명령, commit, push는 사용자의 명시 요청 없이는 수행하지 않습니다.
- 검증은 기본적으로 conda 환경 `gemini-news-brief`에서 실행합니다.
    - 예: `conda run -n gemini-news-brief python -m compileall src`

## 프로젝트 개요

Gemini News Brief는 FastAPI Worker/API, BigQuery, Gemini API를 사용하는 뉴스 ETL 파이프라인입니다.

현재 구현의 핵심 흐름:

- Ingest: Yahoo Finance RSS를 수집하고 기사 본문을 enrich한 뒤 `bronze.news`에 적재합니다.
- Refine `news`: `bronze.news`를 정규화해 `silver.news`에 적재합니다.
- Refine `news-augmented`: `silver.news`를 Gemini로 분석·요약·번역해 `silver.news_augmented`에 적재합니다.
- API 서비스와 Worker 서비스는 같은 Docker 이미지에서 Cloud Run command/args로 분리 실행됩니다.

## 레이어 책임

| 레이어   | 주요 경로                               | 책임                                                    |
| -------- | --------------------------------------- | ------------------------------------------------------- |
| Entry    | `src/api/main.py`, `src/worker/main.py` | FastAPI 앱 생성, lifespan 리소스 초기화, 라우터 등록    |
| Router   | `src/worker/routers/*.py`               | HTTP 요청/응답, path/body 파라미터 해석, 상태 코드 결정 |
| Service  | `src/worker/services/*.py`              | 파이프라인 순서 제어, 단계별 결과 집계                  |
| Plugin   | `src/worker/plugins/*.py`               | 외부 도메인 작업 조율: 수집, DB 접근, 변환              |
| Source   | `src/worker/plugins/sources/*.py`       | RSS/HTML 등 뉴스 소스별 수집 구현                       |
| Store    | `src/worker/plugins/stores/*.py`        | BigQuery 테이블별 조회·삭제·적재                        |
| Provider | `src/providers/*.py`                    | 외부 클라이언트 초기화와 동시성 리소스 관리             |
| Entity   | `src/models/entities/*.py`              | BigQuery 테이블과 대응되는 데이터 모델                  |
| Schema   | `src/models/schemas/*.py`               | API/파이프라인 요청·응답·중간 결과 DTO                  |
| Infra    | `terraform/*.tf`, `cloudbuild/*.yml`    | BigQuery/Cloud Run/Cloud Build 설정                     |

## 아키텍처 규칙

- Router는 비즈니스 로직을 직접 만들지 않고 `Depends`로 Service를 주입받습니다.
- Service는 파이프라인 흐름과 집계만 담당합니다. 웹 요청, SQL, LLM 호출 세부사항을 직접 처리하지 않습니다.
- Plugin은 도메인별 외부 작업을 조율합니다.
    - `CollectPlugin`: 외부 뉴스 웹/RSS 통신
    - `IngestDbPlugin`, `RefineDbPlugin`: BigQuery Store 호출 조율
    - `TransformPlugin`: Entity 변환과 LLM 증강 조율
- Store는 물리 BigQuery 테이블명, SQL, Load Job 세부사항을 캡슐화합니다.
- Provider는 BigQuery/Gemini 클라이언트 초기화와 semaphore를 관리합니다.
- `asyncio.Semaphore` 같은 이벤트 루프 종속 객체는 모듈 레벨에서 만들지 않고 FastAPI lifespan에서 생성합니다.
- Router나 API 요청 DTO는 `bronze.news`, `silver.news` 같은 물리 테이블명을 직접 받지 않습니다.
- 여러 처리 대상을 다룰 때는 `/{target}` path parameter와 enum/registry 검증을 우선합니다.

## Target 처리 규칙

파이프라인 target은 물리 테이블명이 아니라 “실행할 작업”을 의미합니다.

권장 API 형태:

```text
POST /ingest/{target}
POST /refine/{target}
```

현재 의미상 target:

```text
ingest/news
refine/news
refine/news-augmented
```

규칙:

- 요청 body에 `target_table` 같은 물리 테이블명을 넣지 않습니다.
- Router는 path target을 enum 또는 registry로 검증합니다.
- Service와 Plugin은 target을 명시적으로 전달받아 분기합니다.
- Store 계층만 물리 BigQuery 테이블명을 알고 있어야 합니다.

## 파이프라인 규칙

### Ingest

기본 흐름은 `Fetch -> Lookup -> Enrich -> Load`입니다.

- `Fetch`: RSS/목록 데이터를 수집하고 `BronzeNewsModel`로 매핑합니다.
- `Lookup`: 기존 `bronze.news`와 비교해 신규 또는 갱신 대상만 남깁니다.
- `Enrich`: Lookup 대상만 본문/작성자/썸네일을 스크래핑합니다.
- `Load`: enrich 결과를 `bronze.news`에 append 적재합니다.

주의:

- `CollectPlugin.enrich()`는 일부 기사 스크래핑 실패도 `enriched_items`에 포함할 수 있습니다.
- 실패 항목도 `status_code`와 오류 메타데이터를 DB에 남기는 것이 목적입니다.
- `enriched_count`는 실제 본문 추출 성공 수입니다.
- `loaded_count`는 DB 적재 항목 수이므로 `enriched_count`보다 클 수 있습니다.

### Refine

기본 흐름은 `Extract -> Transform -> Load`입니다.

- `news`: `bronze.news`에서 성공적으로 본문 수집된 뉴스를 추출해 `silver.news` 모델로 정규화합니다.
- `news-augmented`: `silver.news`를 Gemini로 분석해 `silver.news_augmented`에 적재합니다.

주의:

- Silver 계층 load는 동일 `executed_at` 배치 데이터를 먼저 삭제한 뒤 다시 적재하는 idempotent 패턴입니다.
- AI 증강은 chunk 단위로 Gemini를 호출합니다.
- Gemini chunk 실패 시 해당 chunk의 item은 실패 record로 남깁니다.

## 모델과 스키마 규칙

- Entity는 BigQuery 테이블에 저장되는 데이터 모양을 표현합니다.
- Schema DTO는 API 요청/응답 또는 파이프라인 단계별 결과를 표현합니다.
- 요청 DTO는 사용자가 제공해야 하는 최소 입력만 가집니다.
- 물리 테이블명은 요청 DTO에 포함하지 않습니다.
- `target`은 enum 또는 registry로 제한합니다.
- 상태값은 `Literal` 또는 enum으로 제한합니다.
- count 필드는 이름과 description이 실제 의미를 정확히 드러내야 합니다.
- Entity 변경은 Terraform BigQuery schema와 함께 검토합니다.
- DTO-only 변경은 Terraform에 반영하지 않습니다.

## 문서화 및 주석 규칙

### 공통

- 코드 주석, docstring, Pydantic `Field(description=...)`, Terraform BigQuery `description`은 영어로 작성합니다.
- 설명은 짧고 구체적으로 씁니다.
- 실제로 보장하지 않는 표현은 쓰지 않습니다.
    - URL canonicalization을 하지 않으면 `Canonical news item URL` 대신 `Source news item URL`을 사용합니다.
- 데이터 모델과 DB schema description은 내부 구현보다 데이터의 의미를 우선 설명합니다.

### Docstring

- 함수와 메서드 docstring은 imperative mood를 사용합니다.
    - Good: `Return ...`, `Fetch ...`, `Transform ...`
    - Avoid: `Returns ...`, `Fetches ...`, `Transforms ...`
- 클래스 docstring은 객체의 책임을 설명합니다.
- 코드 흐름을 그대로 반복 설명하지 않습니다.
- private helper라도 외부 제약, 예외 정책, 복잡한 규칙이 있으면 docstring을 둡니다.

### Inline Comment

- 코드만 읽어도 알 수 있는 내용은 주석으로 쓰지 않습니다.
- 왜 필요한지, 어떤 외부 제약 때문인지, 어떤 예외를 방지하는지 설명할 때만 사용합니다.
- 첫 글자는 대문자로 시작합니다.
- 완전한 문장이면 마침표로 끝냅니다.
- TODO는 이유와 방향을 함께 적습니다.
    - 예: `# TODO(refactor): Split target-specific transformation logic into dedicated classes.`

### Entity Field Description

`src/models/entities/*.py`의 `Field(description=...)`은 BigQuery 컬럼 description과 동기화되어야 합니다.

규칙:

- 데이터 자체의 의미를 설명합니다.
- 같은 의미의 필드는 Bronze/Silver 계층에서 같은 description을 사용합니다.
- `_raw` 필드는 원천 데이터임을 드러냅니다.
- `ai_` 필드는 LLM이 생성·분류·정규화한 값임을 드러냅니다.
- 파이프라인 내부 구현을 과하게 드러내지 않습니다.

권장 예시:

```text
executed_at: Batch execution timestamp
news_id: Stable unique news item identifier
published_at: News item publication timestamp
url: Source news item URL
content_raw: Raw news item body text
ai_summary: Korean summary of the news item
```

### DTO Field Description

`src/models/schemas/*.py`의 description은 API와 파이프라인 실행 결과 계약을 설명합니다.

- BigQuery description과 반드시 일치할 필요는 없습니다.
- `target`, `status`, `*_count`, `failed_phase`, `error_message`는 실행 상태 관점에서 설명합니다.
- 요청 DTO description은 사용자가 제공할 입력 의미를 설명합니다.

### Terraform BigQuery Description

Terraform BigQuery schema description은 DB 사용자와 분석가가 보는 메타데이터입니다.

- Entity와 1:1 대응되는 컬럼 description은 Entity `Field(description=...)`과 동일하게 유지합니다.
- Entity에 없는 DB 관리 또는 적재 관리 컬럼은 Terraform에서만 설명합니다.
- `loaded_at`은 Pydantic Entity에는 없고, 현재 `StoreBase.execute_load_json()`에서 적재 직전에 주입됩니다.
- `loaded_at`을 설명할 때 실제 동작과 다르게 “database-managed”라고 쓰지 않습니다.
- Entity description을 바꾸면 같은 변경 단위에서 Terraform description도 함께 검토합니다.
- DTO-only 필드인 target, count, phase status는 Terraform에 반영하지 않습니다.

## BigQuery 규칙

- BigQuery 테이블명은 Store 또는 설정 계층에 둡니다.
- Store는 table id, SQL, load job 설정을 캡슐화합니다.
- `loaded_at`은 Entity에 두지 않습니다.
- JSON Load Job은 BigQuery default expression을 평가하지 않으므로 `StoreBase.execute_load_json()`에서 `loaded_at`을 주입합니다.
- `BronzeStore._BRONZE_NEWS`는 현재 `"bronze.news"`로 고정되어 있습니다. 멀티 프로젝트 환경에서는 project/table id 설정을 명시해야 합니다.
- Terraform schema 변경 시 Entity 필드명, 타입, nullable 여부, description을 함께 확인합니다.

## Provider와 인증 동작

- `BigQueryProvider`는 GCP 환경(`K_SERVICE`)이 아니고 명시 credentials도 없으면 client를 `None`으로 유지합니다.
- BigQuery client가 없으면 앱 시작은 가능하지만 DB 단계 실행 시 `RuntimeError`가 발생하고 pipeline 결과는 실패로 격리됩니다.
- `GeminiProvider`는 `GEMINI_API_KEY_FREE`가 없으면 client를 만들지 않습니다.
- Gemini client가 없거나 호출이 실패하면 augmentation 단계에서 실패 record를 생성하는 흐름을 유지합니다.
- 외부 API transient error는 provider 계층에서 retry 정책을 관리합니다.

## 새 뉴스 소스 추가 규칙

1. `src/worker/plugins/sources/` 아래에 `SourceBase` 구현체를 추가합니다.
2. `source`, `RSS_URL`, `fetch()`를 반드시 정의합니다.
3. `fetch()`는 RSS 데이터를 `BronzeNewsModel`로 매핑하되, 본문/작성자/썸네일처럼 스크래핑이 필요한 필드는 채우지 않습니다.
4. Enrich가 필요한 필드는 `SourceBase.enrich()`와 source helper에 맡깁니다.
5. 소스 등록은 Service factory 또는 source registry에서 처리합니다.

현재 등록된 소스:

- `YahooFinanceSource`

## 로컬 검증

기본 Python 환경은 conda `gemini-news-brief`입니다.

자주 쓰는 검증:

```bash
conda run -n gemini-news-brief python -m compileall src
conda run -n gemini-news-brief python -m compileall src/models/schemas/ingest.py
```

API import 또는 OpenAPI 확인이 필요하면 같은 conda 환경에서 실행합니다.

의존성 설치, 네트워크 접근, 외부 서비스 호출이 필요한 명령은 사용자 승인 없이 수행하지 않습니다.

## 현재 리팩토링 방향

진행 중인 리팩토링은 낮은 계층에서 높은 계층으로 진행합니다.

권장 순서:

1. `src/models/entities/*.py`
2. `src/models/schemas/*.py`
3. `src/worker/plugins/stores/*.py`
4. `src/worker/plugins/*.py`
5. `src/worker/services/*.py`
6. `src/worker/routers/*.py`
7. `src/worker/main.py`, `src/api/main.py`
8. `terraform/*.tf`, `cloudbuild/*.yml`, `README.md`

중요한 리팩토링 목표:

- 요청 body에서 `target_table` 제거
- path target + enum/registry 검증 도입
- TransformPlugin 책임 분리
- Store 책임 분리
- Entity description과 Terraform schema description 동기화
- BigQuery table id 하드코딩 제거 또는 설정 계층으로 이동

## 커밋 규칙

Angular Commit Convention을 따릅니다.

형식:

```text
[Type] Subject

- 부가 설명 1
- 부가 설명 2

Footer
```

Type:

- `[Build]`: 빌드 시스템 또는 외부 의존성 변경
- `[CI]`: CI/CD 설정 변경
- `[Docs]`: 문서 변경
- `[Feat]`: 새로운 기능 추가
- `[Fix]`: 버그 수정
- `[Perf]`: 성능 개선
- `[Refactor]`: 리팩토링
- `[Test]`: 테스트 추가 또는 수정

규칙:

- Type은 대괄호로 감싸고 첫 글자는 대문자로 작성합니다.
- Subject는 한글로 간결하게 작성합니다.
- Body는 선택 사항이며 `- ` 목록으로 작성합니다.
- 커밋은 하나의 목적 단위로 나눕니다.
- 사용자가 명시적으로 요청하지 않는 한 push하지 않습니다.
- 커밋 메시지에 `Co-Authored-By`를 포함하지 않습니다.
