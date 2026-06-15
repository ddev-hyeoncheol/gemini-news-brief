# News Source Guide

새 RSS 기반 뉴스 source를 `bronze/news` 흐름에 추가할 때 참고하는 가이드입니다.

## Procedure

1. `.agents/rules/architecture.md`, `.agents/rules/pipeline.md`, `.agents/rules/data-contract.md`를 함께 적용합니다.
2. `src/worker/plugins/sources/` 아래에 `SourcePlugin` 구현체를 추가합니다.
3. `src/models/schemas/sources/` 아래에 source별 RSS entry DTO를 추가합니다.
4. `source`는 DB와 응답에 남는 안정적인 lower_snake_case 식별자로 정의합니다.
5. `RSS_URL`과 `run_fetch(executed_at: datetime)`를 정의합니다.
6. `RSS_ENTRY_STORAGE_FIELDS`, `RSS_ENTRY_METADATA_FIELDS`, `RSS_ENTRY_IGNORED_FIELDS`로 저장, metadata, 무시 필드를 구분합니다.
7. `run_fetch()`는 `_warn_unknown_fields()`를 사용하여 신규 RSS 필드 유입(Drift)을 로깅하고, DTO 검증 후 RSS item을 `BronzeNewsModel` 리스트로 매핑합니다.
8. URL 기반 식별자는 `SourcePlugin._make_id()`로 생성합니다.
9. source별 부가 값은 기존 필드에 맞추고, 새 저장 필드가 아니면 `metadata`에 둡니다.
10. 기본 helper는 `SourcePlugin._fetch_feed()`를 우선 사용하고, date/image 파싱은 source 내부 helper로 제한합니다.
11. 배포 대상 source만 `get_batch_service()`의 `source_plugins` 리스트에 등록합니다.

## Boundaries

- 새 source 추가만으로 `BatchTarget`을 늘리지 않습니다. 현재 `bronze/news` 수집 단계는 등록된 모든 source를 실행합니다.
- `SourcePlugin.run_fetch()`에는 `BatchRequest` 객체 대신 `executed_at: datetime`만 넘깁니다.
- `BronzeNewsModel`이나 Terraform schema 변경은 기존 Bronze 계약으로 표현할 수 없을 때만 검토합니다.
- Enrich 실패 record 보존과 `count` 의미는 pipeline 규칙을 따릅니다.
- 기존 source의 `source` 식별자는 DB와 응답 계약에 남으므로 rename하지 않습니다.
- 검증은 source 구현체, source DTO, feed sample, 등록한 경우 `src/worker/services/batch.py`를 중심으로 실행합니다.
