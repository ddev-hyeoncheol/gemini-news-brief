# Pipeline Rules

Ingest, Refine, count 의미, 실패 전파를 수정할 때 읽습니다.

## Ingest

흐름은 `Fetch -> Lookup -> Enrich -> Load`입니다.

- `Fetch`: RSS/목록 데이터를 수집하고 `BronzeNewsModel`로 매핑합니다.
- `Lookup`: 기존 `bronze.news`와 비교해 신규 또는 갱신 대상을 남깁니다.
- `Enrich`: Lookup 대상만 본문, 작성자, 썸네일을 스크래핑합니다.
- `Load`: enrich 결과를 `bronze.news`에 append 적재합니다.
- `CollectPlugin.enrich()`는 스크래핑 실패도 `enriched_items`에 포함할 수 있습니다.
- 실패 항목도 `status_code`와 오류 메타데이터를 DB에 남깁니다.
- `enriched_count`는 본문 추출 성공 수이고, `loaded_count`는 DB 적재 항목 수입니다.

## Refine

흐름은 `Extract -> Transform -> Load`입니다.

- `news`: 성공적으로 enrich된 bronze news를 `silver.news`로 정규화합니다.
- `news-augmented`: `silver.news`를 Gemini로 분석해 `silver.news_augmented`에 적재합니다.
- Silver load는 동일 `executed_at` 배치를 먼저 삭제한 뒤 적재합니다.
- AI 증강은 chunk 단위로 Gemini를 호출합니다.
- Gemini chunk가 실패하면 해당 chunk의 item을 실패 record로 남깁니다.
