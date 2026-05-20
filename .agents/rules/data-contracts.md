# Data Contract Rules

Entity, Schema, BigQuery, Terraform schema, field description을 수정할 때 읽습니다.

## Models And Schemas

- Entity는 BigQuery 테이블에 저장되는 데이터 모양을 표현합니다.
- Schema DTO는 API 요청/응답 또는 파이프라인 중간 결과를 표현합니다.
- 요청 DTO는 사용자가 제공해야 하는 최소 입력만 가집니다.
- 물리 테이블명은 요청 DTO에 포함하지 않습니다.
- `target`은 enum 또는 registry로 제한합니다.
- 상태값은 `Literal` 또는 enum으로 제한합니다.
- count 필드 이름과 description은 실제 의미를 드러내야 합니다.
- DTO-only 필드인 target, count, phase status는 Terraform에 반영하지 않습니다.

## BigQuery And Terraform

- BigQuery 테이블명은 Store 또는 설정 계층이 소유합니다.
- `loaded_at`은 Entity 필드가 아니며 `StoreBase.execute_load_json()`에서 주입합니다.
- Entity 변경은 Terraform BigQuery schema와 함께 검토합니다.
- Terraform schema 변경 시 Entity 필드명, 타입, nullable 여부, description을 함께 확인합니다.

## Field Descriptions

- Entity `Field(description=...)` 값은 BigQuery column description과 동기화합니다.
- 같은 의미의 필드는 Bronze/Silver 계층에서 같은 description을 사용합니다.
- `_raw` 필드는 원천 데이터, `ai_` 필드는 LLM 생성/분류/정규화 값을 드러냅니다.
- DTO description은 API와 파이프라인 실행 계약을 설명합니다.
- Terraform BigQuery description은 DB 사용자와 분석가가 보는 메타데이터입니다.
- `loaded_at`은 database-managed라고 설명하지 않습니다.
