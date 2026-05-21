# Technical Debt

이 파일은 프로젝트 인프라, 설정 및 코드베이스의 장기적인 기술 부채를 추적하고 관리하기 위한 대장입니다.

## Infrastructure & Deployment

### [Security] Worker 서비스의 비인증 호출 허용

- **설명**: 현재 [cloudbuild.yml](file:///Users/supergrammer/WorkSpace/GitRepository/ddev-hyeoncheol/gemini-news-brief/cloudbuild/cloudbuild.yml)에서 `gemini-news-brief-fastapi-worker`를 배포할 때 `--allow-unauthenticated` 인자가 부여되어 외부 공개에 노출되어 있습니다.
- **영향**: 악의적인 무단 호출로 파이프라인 비용이 청구되거나 데이터 수집이 오작동할 위험이 있습니다.
- **해결 방안**: Worker 서비스 배포 시 `--no-allow-unauthenticated` 옵션으로 전환하고, 호출 트리거 주체(Cloud Scheduler, Pub/Sub 등)에 OIDC 토큰 인증 정보를 부여하여 내부 보안 연결을 완성해야 합니다.

## Source Ingestion

### [Contract] RSS updated_at 파싱 기준 정렬

- **설명**: `YahooFinanceSource`는 RSS entry의 `updated_parsed`가 있어도 읽지 않고 `updated_at=published_at`으로 저장합니다.
- **영향**: 소스가 별도 update timestamp를 제공하는 경우 Bronze lookup이 실제 기사 갱신을 감지하지 못해 재수집 대상에서 빠질 수 있습니다.
- **해결 방안**: `SourceBase`에 updated timestamp 파서 또는 source별 helper를 추가하고, Yahoo Finance fetch에서 `updated_parsed`를 우선 사용하되 없으면 `published_at`으로 fallback합니다.

## Data Contract & Ingestion

### [Configuration] Store 물리 테이블 ID 하드코딩

- **설명**: `BronzeStore`와 `SilverStore` 내부의 테이블 식별 상수들(`_BRONZE_NEWS`, `_SILVER_NEWS`, `_SILVER_NEWS_AUGMENTED`)이 문자열 리터럴로 소스 코드 내에 하드코딩되어 있습니다.
- **영향**: 장기적으로 다중 프로젝트나 개발/상용 데이터셋 환경 분리 시 설정 관리가 번거로워질 수 있습니다.
- **해결 방안**: 해당 상수들을 제거하고 Pydantic `Settings` 또는 환경 설정 레이어를 통해 동적으로 주입받도록 구조를 이관해야 합니다.

## Testing & Verification

### [Gaps] 핵심 로직에 대한 자동화 테스트(Unit/Integration Test) 누락

- **설명**: `src/simple_test.py`는 단순 Feedparser 및 Newspaper3k 모듈의 연동 테스트 스크립트일 뿐, FastAPI 라우터, Ingest/Refine 파이프라인 서비스, DB 플러그인 등 핵심 워크플로를 검증하는 단위/통합 테스트가 존재하지 않습니다.
- **영향**: 코드베이스를 변경하거나 리팩토링할 때, 예외 처리 흐름이나 데이터 정제 파이프라인의 오작동 및 회귀 버그를 감지하기 어렵습니다.
- **해결 방안**: `pytest` 및 `httpx.AsyncClient`를 도입하여, 각 라우터 엔드포인트의 입력 검증, 모의(Mocking) DB/Gemini 동작, 그리고 멱등성 데이터 적재 흐름을 검증하는 테스트 코드를 구축해야 합니다.

## Resolved

### [Infra-Standard] GCR (gcr.io) 사용 유지 (해결: 2026-05-21)

- **조치**: 테라폼에 Artifact Registry 리포지토리 리소스를 추가하고 `cloudbuild.yml` 이미지 경로를 `${_REGION}-docker.pkg.dev` 구조로 갱신함.

### [Redundancy] Terraform Apply 시 -auto-approve 중복 전달 (해결: 2026-05-21)

- **조치**: `cloudbuild.terraform.yml` 내 apply args를 `["apply", "tfplan"]`으로 단일화함.

### [Contract] loaded_at 컬럼의 테라폼 defaultValueExpression 정의와 애플리케이션 직접 주입 이원화 (해결: 2026-05-21)

- **조치**: 테라폼 BigQuery 스키마 정의(`bigquery-bronze.tf`, `bigquery-silver.tf`)에서 `defaultValueExpression` 설정을 제거하여 백엔드(`StoreBase.execute_load_json()`)에서의 주입 계약으로 단일화하고 코드 주석을 보완함.

