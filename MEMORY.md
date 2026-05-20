# MEMORY.md

이 파일은 에이전트가 다음 작업에서도 기억하면 좋은 현재 상태와 임시 합의를 담습니다. 오래가는 규칙은 `.agents/rules/`로 옮깁니다.

## Current Refactoring

- 리팩토링은 일반적으로 낮은 계층에서 높은 계층으로 진행합니다.
- 권장 순서: Entity, Schema, Store, Plugin, Service, Router, Entry, Infra/Docs.
- 현재 목표는 `target_table` 제거, path target 검증, `TransformPlugin`/Store 책임 분리, Entity/Terraform description 동기화입니다.

## Temporary Notes

- `BronzeStore._BRONZE_NEWS`는 아직 `"bronze.news"`로 하드코딩되어 있습니다.
- 멀티 프로젝트 테이블 ID 설정은 향후 리팩토링 대상이며, 모든 변경의 선행 조건은 아닙니다.
