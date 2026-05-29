# Data Contract Rules

Entity, Schema DTO, BigQuery Terraform schema, field description 계약을 정의합니다.

## Models And Schemas

- Entity는 BigQuery에 저장되는 record shape를 정의합니다.
- Entity는 BigQuery에서 돌아오는 `loaded_at` 같은 extra field를 무시하되, 저장 모델 필드로 선언하지 않습니다.
- Schema DTO는 API 요청/응답, pipeline phase 결과, provider response 계약을 정의합니다.
- 요청 DTO는 사용자가 제공하는 최소 입력만 가지며 물리 table id를 받지 않습니다.
- `layer`와 `target`은 enum 또는 registry로 유효 조합을 제한하고 Terraform schema에 반영하지 않습니다.
- `status`, `failed_phase`, phase status는 `Literal` 또는 enum으로 제한합니다.
- count 필드는 pipeline 규칙의 실제 의미와 description을 일치시킵니다.
- Pipeline 응답 전용 필드인 count, failed_phase는 Terraform에 반영하지 않습니다.
- status, error_message는 BigQuery Entity 저장 필드로 선언된 경우에만 Terraform에 반영합니다.
- LLM DTO는 provider 응답 검증 계약이며, BigQuery에는 `SilverNewsAugmentedModel`로 변환된 필드만 저장합니다.

## BigQuery And Terraform

- BigQuery table id는 Store class 상수로 격리하고, 장기적으로 설정 계층으로만 이관합니다.
- Entity 필드 추가, 삭제, 이름 변경, 타입 변경, nullable 변경은 Terraform BigQuery schema와 같은 변경 단위에서 검토합니다.
- **[CRITICAL]** BigQuery column 삭제, rename, REQUIRED 전환처럼 기존 데이터 손실이나 적재 실패 위험이 있는 schema 변경은 사용자에게 명시 확인을 받습니다.
- Terraform `loaded_at` column은 Entity에 두지 않습니다.
- BigQuery JSON Load Job은 `defaultValueExpression`을 평가하지 않으므로 `BigQueryProvider.execute_load_json()`에서 `loaded_at`을 주입합니다.
- Store에서 주입하지 않는 DB 관리 컬럼을 추가하면 Entity `extra="ignore"` 동작과 조회 모델 생성을 함께 확인합니다.

## Field Descriptions

- Entity `Field(description=...)`과 Terraform BigQuery column description은 같은 저장 필드에서 동일하게 유지합니다.
- 같은 의미의 필드는 Bronze/Silver 계층에서 같은 description을 사용합니다.
- `raw_` 필드는 원천 데이터, `ai_` 필드는 LLM 생성, 분류, 정규화 값을 드러냅니다.
- DTO description은 API 입력과 pipeline 실행 결과 계약을 설명하며 BigQuery description과 억지로 맞추지 않습니다.
- Terraform description은 DB 사용자와 분석가가 보는 데이터 의미를 설명합니다.
- `loaded_at`은 application-injected load timestamp이며 database-managed라고 설명하지 않습니다.
