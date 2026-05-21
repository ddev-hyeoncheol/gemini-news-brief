# Pipeline Rules

Ingest, Refine, count 의미, 실패 전파 계약을 정의합니다.

## Ingest

- 흐름은 `Fetch -> Lookup -> Enrich -> Load`입니다.
- `Fetch`는 RSS/목록 데이터를 `BronzeNewsModel`로 매핑합니다.
- `Lookup`은 기존 `bronze.news`와 비교해 신규 또는 갱신 대상만 남깁니다.
- `Enrich`는 Lookup 대상의 본문, 작성자, 썸네일을 스크래핑합니다.
- `Load`는 enrich 결과 전체를 `bronze.news`에 append 적재합니다.
- Enrich item 실패는 phase 실패가 아니라 `status_code`와 `metadata.error_message`를 가진 bronze record로 보존합니다.
- Enrich phase status는 성공 item만 있으면 `success`, 하나라도 item 실패가 있으면 `partial`입니다.
- `enriched_count`는 본문 추출 성공 item 수이고, `loaded_count`는 DB 적재 대상 item 수입니다.
- `loaded_count`는 실패 record 보존 때문에 `enriched_count`보다 클 수 있습니다.
- Fetch, Lookup, Enrich, Load phase 예외는 해당 source pipeline을 `failed`로 중단합니다.
- 모든 source가 `failed`이면 전체 ingest status는 `failed`, 일부만 실패하거나 partial이면 `partial`입니다.

## Refine

- 흐름은 `Extract -> Transform -> Load`입니다.
- `news`는 `executed_at`이 일치하는 bronze record를 추출하고, `status_code == 200`이며 content가 있는 item만 `silver.news`로 정규화합니다.
- `news-augmented`는 `silver.news`를 Gemini로 분석해 `silver.news_augmented` record로 변환합니다.
- **[CRITICAL]** Silver load는 동일 `executed_at` 배치를 먼저 삭제한 뒤 다시 적재하는 idempotent replace 계약을 유지합니다.
- AI 증강은 deterministic chunk 단위로 Gemini를 호출합니다.
- Gemini chunk 실패나 result 누락은 transform phase 실패가 아니라 failed augmented record로 보존합니다.
- Augmentation `transformed_count`는 성공 augmented record 수이고, `loaded_count`는 성공과 실패를 포함한 적재 record 수입니다.
- Transform이 `partial`이어도 Load phase는 실행해 성공/실패 record를 함께 적재합니다.
- Extract, Transform, Load phase 예외는 `failed_phase`와 `error_message`를 담아 `failed`로 전파합니다.
- Router는 pipeline status가 `partial`이면 HTTP 207, `failed`이면 HTTP 500으로 응답합니다.
