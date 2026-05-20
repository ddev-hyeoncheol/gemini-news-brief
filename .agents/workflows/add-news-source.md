# Add News Source Workflow

새 뉴스 source를 추가할 때 읽습니다.

1. `src/worker/plugins/sources/` 아래에 `SourceBase` 구현체를 추가합니다.
2. `source`, `RSS_URL`, `fetch()`를 정의합니다.
3. `fetch()`에서 RSS 데이터를 `BronzeNewsModel`로 매핑하되, 스크래핑이 필요한 본문, 작성자, 썸네일 필드는 채우지 않습니다.
4. enrich 전용 필드는 `SourceBase.enrich()`와 source helper에서 처리합니다.
5. Service factory 또는 source registry에 source를 등록합니다.
