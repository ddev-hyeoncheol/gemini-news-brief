# MEMORY.md

이 파일은 에이전트가 다음 작업에서도 기억하면 좋은 현재 상태와 임시 합의를 담습니다. 오래가는 규칙은 `.agents/rules/`로 옮깁니다.

## Current Focus

- v0.1.0 이후 파이프라인은 application-layer orchestration을 줄이고 BigQuery-native 구조로 이관하는 방향을 검토합니다.
- 목표 흐름은 Cloud Run collector -> Cloud Storage `bronze/news/...` 파일 적재 -> BigQuery external/BigLake table -> Dataform SQLX -> `silver.news` / `silver.news_augmented` / embedding / serving relation 생성입니다.
- Dataform은 Cloud Storage 파일을 직접 읽지 않고, BigQuery external/BigLake table을 source로 사용합니다.
- 정기 배치는 Dataform workflow configuration 기반 실행을 우선합니다.
- 수집 완료 직후 실행은 데이터 파일 자체가 아니라 `_SUCCESS.json` 또는 `manifest.json` 같은 marker object finalized 이벤트를 기준으로 Eventarc가 Cloud Run orchestrator를 호출하는 구조를 검토합니다.

## Temporary Notes

- Cloud Run orchestrator는 object prefix, marker 파일, `batch_id`/`executed_at`을 검증하고 Dataform workflow invocation을 생성하는 얇은 조정 계층으로 둡니다.
- Eventarc 재시도와 중복 전달 가능성을 고려해 같은 `batch_id`가 두 번 들어와도 결과가 깨지지 않는 멱등 실행을 전제로 설계합니다.
- `silver.news`, `silver.news_augmented`, embedding, serving output은 Dataform이 관리하는 BigQuery relation으로 보고, 실제 저장 위치는 BigQuery로 유지합니다.
- BigQuery AI functions 적용 범위는 `silver.news_augmented`부터 검토합니다.
