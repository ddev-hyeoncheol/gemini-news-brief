# Architecture Rules

저장소의 레이어 책임, 의존성 방향, target, Provider 동작을 정의합니다.

## Layer Responsibilities

| 레이어                  | 주요 경로                        | 핵심 책임                                                               |
| :---------------------- | :------------------------------- | :---------------------------------------------------------------------- |
| Entry                   | `src/api/`, `src/worker/main.py` | 앱 초기화, lifespan, router 등록을 수행합니다.                          |
| Router                  | `src/worker/routers/`            | HTTP 요청/응답과 path target 검증을 수행합니다.                         |
| Service                 | `src/worker/services/`           | 파이프라인 흐름 제어, 결과 집계, factory 기반 Plugin 조립을 담당합니다. |
| Plugin / Source / Store | `src/worker/plugins/`            | RSS 수집, BigQuery 접근, AI 증강 같은 외부 도메인 작업을 격리합니다.    |
| Provider                | `src/providers/`                 | 외부 client 초기화와 호출 실행을 담당합니다.                            |
| Entity / Schema         | `src/models/`                    | BigQuery 저장 모델과 API/파이프라인 DTO 계약을 정의합니다.              |
| Core / Config           | `src/core/`, `src/config/`       | 공통 로깅, FastAPI dependency, transient helper, 런타임 설정을 둡니다.  |
| Infra                   | `terraform/`, `cloudbuild/`      | BigQuery, Cloud Run, Cloud Build 설정을 관리합니다.                     |

## Boundaries & Dependencies

- 의존성은 Entry -> Router -> Service -> Plugin -> Source/Store/Provider 방향으로 흐르며, Entity/Schema는 필요한 하위 계약으로만 참조합니다.
- Router는 비즈니스 로직을 만들지 않고 `src.models.schemas`와 Service factory만 참조합니다.
- Service는 흐름 제어와 집계를 담당하며, concrete Source, Store, Plugin 조립은 dependency factory 내부로 한정합니다.
- Service는 Store SQL, BigQuery job, LLM 요청 세부사항을 직접 다루지 않습니다.
- Service는 순수 Entity 변환을 수행할 수 있지만 외부 I/O와 provider 호출은 Plugin/Store로 위임합니다.
- Plugin은 도메인 외부 작업을 조율하며 Entity/Schema DTO를 결과 계약으로 사용합니다.
- `AiPlugin`은 LLM 증강 조율과 응답 매핑 외의 Router, Service, Store 책임을 겸하지 않습니다.
- `SourcePlugin.run_fetch()`에 `BatchRequest` 객체 대신 `executed_at: datetime`만 직접 전달하여 결합도를 최소화합니다.
- Store는 물리 BigQuery table id, SQL, Load Job을 캡슐화하고 상위 orchestration DTO를 역import하지 않습니다.
- Provider는 외부 client 호출만 관리하며 Entity/Schema 변환 책임을 갖지 않습니다.
- Entity는 다른 하위 Entity 외의 상위 레이어를 import하지 않습니다.
- Schema는 Entity를 참조할 수 있지만 Router, Service, Plugin, Store를 import하지 않습니다.
- `asyncio.Semaphore`처럼 event loop에 종속되는 객체는 모듈 레벨에서 만들지 않습니다.

## Target Rules

- 파이프라인 target은 물리 테이블명이 아니라 실행할 논리 작업입니다.
- API 형태는 `POST /batch/run` 및 `POST /batch/{layer}/{target}`로 통일합니다.
- 현재 지원하는 layer와 target의 유효 조합은 `bronze/news`, `silver/news`, `silver/news-augmented`입니다.
- 요청 body에 `target_table`이나 물리 table id를 넣지 않습니다.
- Router는 path target을 enum 또는 registry로 검증합니다.
- 물리 BigQuery table id는 현재 Store class 상수로 격리하고, 장기적으로 설정 계층으로만 이관합니다.

## Provider Rules

- Provider는 외부 client 초기화와 주입된 semaphore 기반 동시성 제한을 관리합니다. Retry는 Gemini처럼 transient API 오류가 있는 provider에만 둡니다.
- `BigQueryProvider`는 GCP 환경(`K_SERVICE`)이 아니고 명시 credentials도 없으면 client를 `None`으로 유지합니다.
- BigQuery client가 없어도 앱 시작은 가능하지만 DB 단계 실행 시 `RuntimeError`가 발생합니다.
- `GeminiProvider`는 `GEMINI_API_KEY_FREE`가 없으면 client를 만들지 않습니다.
- Gemini client가 없거나 호출이 실패해도 augmentation 단계에서 실패 record를 생성하는 흐름을 유지합니다.
