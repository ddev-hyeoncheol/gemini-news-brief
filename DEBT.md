# Technical Debt

이 파일은 프로젝트 인프라, 설정 및 코드베이스의 장기적인 기술 부채를 추적하고 관리하기 위한 대장입니다.

## Infrastructure & Deployment

### [Security] Cloud Run Allows Unauthenticated Calls

- **설명**: 현재 `cloudbuild/cloudbuild.yml`에서 API와 Worker Cloud Run 서비스 모두 `--allow-unauthenticated` 인자로 배포됩니다.
- **영향**: Worker가 공개되면 악의적인 무단 호출로 파이프라인 비용이 청구되거나 데이터 수집이 오작동할 위험이 있습니다. API 공개가 의도된 설계인지도 별도로 확정해야 합니다.
- **해결 방안**: Worker 서비스는 `--no-allow-unauthenticated`로 전환하고, 호출 트리거 주체(Cloud Scheduler, Pub/Sub 등)에 OIDC 토큰 인증 정보를 부여합니다. API 서비스의 공개 여부는 제품 요구에 맞춰 명시적으로 결정합니다.

## Source Ingestion

### [Contract] RSS updated_at Parsing Alignment

- **설명**: `YahooFinanceSource`는 RSS entry의 `updated_parsed`가 있어도 읽지 않아 Bronze `updated_at`에 원천 업데이트 시각을 보존하지 못합니다.
- **영향**: 소스가 별도 update timestamp를 제공하는 경우 Bronze lookup이 실제 기사 갱신을 감지하지 못해 재수집 대상에서 빠질 수 있습니다.
- **해결 방안**: Yahoo Finance `run_fetch()`에서 `updated_parsed`가 있으면 `updated_at`으로 파싱하고, 없거나 유효하지 않으면 Bronze nullable 계약에 따라 `None`으로 저장합니다.

### [Cleanup] Deferred Source Schema Metadata Cleanup

- **설명**: CNBC, BBC Business, The Guardian 등 타 source 스키마에는 현재 수집 대상이 아닌 불필요/중복 RSS 메타데이터 필드가 남아 있습니다.
- **영향**: 새 source 확장 시 schema 기준이 흐려지고, metadata 정리 범위가 source 작업과 섞일 수 있습니다.
- **해결 방안**: 각 source를 실제 수집 대상으로 활성화할 때 Bronze RSS 필드와 `metadata` 보존 기준에 맞춰 schema 필드를 정리합니다.

## Data Contract & Ingestion

### [Configuration] Hardcoded Store Physical Table IDs

- **설명**: `BronzeStore`와 `SilverStore` 내부의 테이블 식별 상수들(`_BRONZE_NEWS`, `_SILVER_NEWS`, `_SILVER_NEWS_AUGMENTED`)이 문자열 리터럴로 소스 코드 내에 하드코딩되어 있습니다.
- **영향**: 장기적으로 다중 프로젝트나 개발/상용 데이터셋 환경 분리 시 설정 관리가 번거로워질 수 있습니다.
- **해결 방안**: 해당 상수들을 제거하고 Pydantic `Settings` 또는 환경 설정 레이어를 통해 동적으로 주입받도록 구조를 이관해야 합니다.

## Testing & Verification

### [Gaps] Missing Core Logic Automated Tests

- **설명**: `src/simple_test.py`는 단순 Feedparser 및 Newspaper 모듈의 연동 테스트 스크립트일 뿐, FastAPI 라우터, Batch 파이프라인 서비스, DB 플러그인 등 핵심 워크플로를 검증하는 단위/통합 테스트가 존재하지 않습니다.
- **영향**: 코드베이스를 변경하거나 리팩토링할 때, 예외 처리 흐름이나 데이터 정제 파이프라인의 오작동 및 회귀 버그를 감지하기 어렵습니다.
- **해결 방안**: `pytest` 및 `httpx.AsyncClient`를 도입하여, 각 라우터 엔드포인트의 입력 검증, 모의(Mocking) DB/Gemini 동작, 그리고 멱등성 데이터 적재 흐름을 검증하는 테스트 코드를 구축해야 합니다.
