# MEMORY.md

이 파일은 에이전트가 다음 작업에서도 기억하면 좋은 현재 상태와 임시 합의를 담습니다. 오래가는 규칙은 `.agents/rules/`로 옮깁니다.

## Current Focus

- v0.1.0 이후 파이프라인은 application-layer orchestration을 줄이고 BigQuery-native 구조로 이관하는 방향을 검토합니다.
- 목표 흐름은 Cloud Run 수집/파싱 -> Cloud Storage landing/archive -> BigQuery external/BigLake table -> Dataform SQLX -> `silver.news` / `silver.news_augmented`입니다.
- Dataform은 Cloud Storage 파일을 직접 읽지 않고, BigQuery external/BigLake table을 source로 사용합니다.
- 초기 운영은 Dataform workflow configuration 기반 정기 실행을 우선하고, 수집 완료 직후 실행이 필요해지면 Pub/Sub 또는 Eventarc + Workflows/Cloud Run + Dataform workflow invocation을 검토합니다.

## Temporary Notes

- `silver.news`와 `silver.news_augmented`는 Dataform이 관리하는 BigQuery relation으로 보고, 실제 저장 위치는 BigQuery로 유지합니다.
- BigQuery AI functions 적용 범위는 `silver.news_augmented`부터 검토합니다.
