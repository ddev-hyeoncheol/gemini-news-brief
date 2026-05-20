# Architecture Rules

아키텍처, 레이어 책임, target, Provider 동작을 수정할 때 읽습니다.

## Layer Responsibilities

| 레이어   | 주요 경로                               | 책임                                                    |
| -------- | --------------------------------------- | ------------------------------------------------------- |
| Entry    | `src/api/main.py`, `src/worker/main.py` | FastAPI 앱 생성, lifespan 리소스 초기화, 라우터 등록    |
| Router   | `src/worker/routers/*.py`               | HTTP 요청/응답, path/body 파라미터 해석, 상태 코드 결정 |
| Service  | `src/worker/services/*.py`              | 파이프라인 순서 제어, 단계별 결과 집계                  |
| Plugin   | `src/worker/plugins/*.py`               | 수집, DB 접근, 변환 같은 외부 작업 조율                 |
| Source   | `src/worker/plugins/sources/*.py`       | 뉴스 소스별 RSS/HTML 수집                               |
| Store    | `src/worker/plugins/stores/*.py`        | BigQuery 테이블별 조회, 삭제, 적재                      |
| Provider | `src/providers/*.py`                    | 외부 클라이언트와 동시성 리소스 관리                    |
| Entity   | `src/models/entities/*.py`              | BigQuery 테이블 데이터 모델                             |
| Schema   | `src/models/schemas/*.py`               | API, 파이프라인, 중간 결과 DTO                          |
| Infra    | `terraform/*.tf`, `cloudbuild/*.yml`    | BigQuery, Cloud Run, Cloud Build 설정                   |

## Boundaries

- Router는 Service를 주입받고 비즈니스 로직을 만들지 않습니다.
- Service는 파이프라인 흐름과 집계만 담당합니다.
- Plugin은 수집, DB 접근, 변환 같은 도메인별 외부 작업을 조율합니다.
- Store는 물리 BigQuery 테이블명, SQL, Load Job 세부사항을 캡슐화합니다.
- Provider는 외부 client 초기화, semaphore, retry 정책을 관리합니다.
- `asyncio.Semaphore`처럼 event loop에 종속되는 객체는 모듈 레벨에서 만들지 않습니다.

## Target Rules

- 파이프라인 target은 물리 테이블명이 아니라 실행할 작업입니다.
- 권장 API 형태는 `POST /ingest/{target}`, `POST /refine/{target}`입니다.
- 현재 의미상 target은 `ingest/news`, `refine/news`, `refine/news-augmented`입니다.
- 요청 body에 `target_table`이나 물리 테이블명을 넣지 않습니다.
- Router는 path target을 enum 또는 registry로 검증합니다.
- Store 또는 설정 계층만 물리 BigQuery 테이블명을 알아야 합니다.

## Provider Rules

- `BigQueryProvider`는 GCP 환경(`K_SERVICE`)이 아니고 명시 credentials도 없으면 client를 `None`으로 유지합니다.
- BigQuery client가 없어도 앱 시작은 가능하지만 DB 단계에서는 `RuntimeError`가 발생합니다.
- `GeminiProvider`는 `GEMINI_API_KEY_FREE`가 없으면 client를 만들지 않습니다.
- Gemini client가 없거나 호출이 실패해도 augmentation 단계에서 실패 record를 생성하는 흐름을 유지합니다.
