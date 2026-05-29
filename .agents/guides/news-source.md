# News Source Guide

새 RSS 기반 뉴스 source를 `bronze/news` 흐름에 추가할 때 참고하는 가이드입니다.

## Procedure

1. `.agents/rules/architecture.md`, `.agents/rules/pipeline.md`, `.agents/rules/data-contract.md`를 함께 적용합니다.
2. `src/worker/plugins/sources/` 아래에 `SourcePlugin` 구현체를 추가합니다.
3. `source`는 DB와 응답에 남는 안정적인 lower_snake_case 식별자로 정의합니다.
4. `RSS_URL`과 `run_fetch(request: BatchRequest)`를 정의합니다.
5. `run_fetch()`는 `request.executed_at`을 사용해 RSS item을 `BronzeNewsModel` 리스트로 매핑합니다.
6. `run_fetch()`는 각 source의 RSS fetch가 제공하는 항목을 Bronze RSS 필드와 `metadata`에 맞춰 채웁니다.
7. URL 기반 식별자는 `SourcePlugin.make_id()`를 사용해 안정적으로 생성합니다.
8. source별 부가 값은 기존 필드에 맞추고, 새 저장 필드가 아니면 `metadata`에 둡니다.
9. 기본 feed helper는 `SourcePlugin._fetch_feed()`를 우선 사용하고, image/date 파싱은 source별 schema와 `run_fetch()` 내부 helper로 필요한 범위에서 정의합니다.
10. 기본 enrich가 부족할 때만 source 전용 enrich helper를 추가하고 반환 key 계약을 보존합니다.
11. 현재 등록은 `src/worker/services/batch.py`의 `get_batch_service()`에서 `source_plugins` 리스트에 `NewSource(semaphore=source_semaphore)`를 추가합니다.

## Boundaries

- 새 source 추가만으로 `BatchTarget`을 늘리지 않습니다. 현재 `bronze/news` 수집 단계는 등록된 모든 source를 실행합니다.
- `SourcePlugin.run_fetch()`의 요청 객체 결합은 현재 인터페이스로만 유지하고 새 입력은 수집에 필요한 최소 값으로 제한합니다.
- `BronzeNewsModel`이나 Terraform schema 변경은 기존 Bronze 계약으로 표현할 수 없을 때만 검토합니다.
- Enrich 실패 record 보존과 `count` 의미는 pipeline 규칙을 따릅니다.
- 기존 source의 `source` 식별자는 DB와 응답 계약에 남으므로 rename하지 않습니다.
- 검증은 새 source 파일과 `src/worker/services/batch.py`를 중심으로 compile 또는 import 검증을 실행합니다.

## Candidate RSS Feed URLs

다음은 프로젝트에서 검토했거나 제공 중인 RSS 피드 소스 URL 정보입니다.

- **Yahoo Finance**: `https://finance.yahoo.com/news/rssindex` (또는 `https://finance.yahoo.com/rss/`)
- **CNBC**: `https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=15839069`
- **BBC Business**: `https://feeds.bbci.co.uk/news/business/rss.xml`
- **The Guardian**: `https://www.theguardian.com/business/economics/rss`
