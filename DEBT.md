# Technical Debt

이 파일은 프로젝트 인프라, 설정 및 코드베이스의 장기적인 기술 부채를 추적하고 관리하기 위한 대장입니다.

## Infrastructure & Deployment

### [Security] Cloud Run Allows Unauthenticated Calls

- **설명**: 현재 `cloudbuild/cloudbuild.yml`에서 API와 Worker Cloud Run 서비스 모두 `--allow-unauthenticated` 인자로 배포됩니다.
- **영향**: Worker가 공개되면 악의적인 무단 호출로 파이프라인 비용이 청구되거나 데이터 수집이 오작동할 위험이 있습니다. API 공개는 현재 제품 요구에 맞춘 의도된 선택입니다.
- **해결 방안**: Worker 수동 테스트 흐름과 Cloud Scheduler OIDC 호출 구성이 정리되면 Worker 서비스는 `--no-allow-unauthenticated`로 전환하고, 호출 주체에 `roles/run.invoker` 권한을 부여합니다.

### [Deployment] Terraform Apply Trigger Separation

- **설명**: 로컬에서 `terraform plan`을 확인한 뒤 push하더라도, push trigger에서 `terraform apply`까지 자동 실행하면 Cloud Build 실행 시점의 원격 state, 권한, provider 환경 차이를 다시 확인하지 못합니다.
- **영향**: 실수로 push된 Terraform 변경이나 원격 state 차이가 즉시 GCP 인프라에 반영되어 BigQuery schema, 리소스, 비용 변경이 의도보다 빠르게 적용될 수 있습니다.
- **해결 방안**: 자동 push trigger는 `terraform init`, `terraform validate`, `terraform plan`까지 실행하고, `terraform apply`는 Cloud Build 수동 trigger 또는 plan 출력 확인 후 승인 단계로 분리합니다.

## Data Contract & Ingestion

### [Configuration] Hardcoded Store Physical Table IDs

- **설명**: `BronzeStore`와 `SilverStore` 내부의 테이블 식별 상수들(`_BRONZE_NEWS`, `_SILVER_NEWS`, `_SILVER_NEWS_AUGMENTED`)이 문자열 리터럴로 소스 코드 내에 하드코딩되어 있습니다.
- **영향**: 장기적으로 다중 프로젝트나 개발/상용 데이터셋 환경 분리 시 설정 관리가 번거로워질 수 있습니다.
- **해결 방안**: 해당 상수들을 제거하고 Pydantic `Settings` 또는 환경 설정 레이어를 통해 동적으로 주입받도록 구조를 이관해야 합니다.

## Testing & Verification

### [Gaps] Missing Core Logic Automated Tests

- **설명**: 현재 FastAPI 라우터, Batch 파이프라인 서비스, DB 플러그인 등 핵심 워크플로 및 데이터 정제 파이프라인을 검증하는 단위/통합 테스트가 존재하지 않습니다.
- **영향**: 코드베이스를 변경하거나 리팩토링할 때, 예외 처리 흐름이나 데이터 정제 파이프라인의 오작동 및 회귀 버그를 감지하기 어렵습니다.
- **해결 방안**: `pytest` 및 `httpx.AsyncClient`를 도입하여, 각 라우터 엔드포인트의 입력 검증, 모의(Mocking) DB/Gemini 동작, 그리고 멱등성 데이터 적재 흐름을 검증하는 테스트 코드를 구축해야 합니다.
