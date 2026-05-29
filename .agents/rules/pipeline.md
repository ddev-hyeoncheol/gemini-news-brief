# Pipeline Rules

Batch pipeline, bronze/silver count 의미, 실패 전파 계약을 정의합니다.

## Bronze News

- 흐름은 `Fetch -> 1차 Lookup -> Enrich -> news_id 재계산 -> 2차 Lookup -> Load`입니다.
- `Fetch`는 RSS/목록 데이터를 `BronzeNewsModel`로 매핑하며, `entry_url` 기반의 UUID v5로 임시 `news_id`를 생성합니다.
- `1차 Lookup`은 `entry_url` 기반 `news_id`로 기존 `bronze.news`를 조회하여 이미 수집된 기사를 필터링하고 스크래핑 후보를 최소화합니다.
- `Enrich`는 1차 필터를 통과한 기사들에 대해서만 본문, 작성자, 썸네일을 스크래핑하여 `canonical_url`을 추출합니다.
- `news_id 재계산`은 획득한 `canonical_url` (없다면 `entry_url` fallback)을 기반으로 최종 UUID v5 `news_id`를 갱신합니다.
- `2차 Lookup`은 최종 `news_id` 기준으로 DB에 중복 조회를 다시 한 번 수행하여 최종적으로 중복을 차단합니다.
- `Load`는 2차 Lookup을 최종 통과한 진짜 신규 canonical 레코드들을 `bronze.news`에 append 적재합니다.
- Enrich item 실패는 phase 실패가 아니라 `status`, `status_code`, `error_message`를 가진 bronze record로 보존합니다.
- Enrich phase status는 성공 item만 있으면 `success`, 하나라도 item 실패가 있으면 `partial`입니다.
- Bronze count는 DB 적재 대상 item 수입니다.
- 실패 record 보존 때문에 DB 적재 대상 item 수는 본문 추출 성공 item 수보다 클 수 있습니다.
- Fetch, Lookup, Enrich, Load phase 예외는 해당 source pipeline을 `failed`로 중단합니다.
- 모든 source가 `failed`이면 전체 bronze status는 `failed`, 일부만 실패하거나 partial이면 `partial`입니다.

## Silver News

- 흐름은 `Extract -> Transform -> Load`입니다.
- `news`는 `executed_at`이 일치하는 bronze record를 추출하고, `status_code == 200`이며 content가 있는 item만 `silver.news`로 정규화합니다.
- `news-augmented`는 `silver.news`를 Gemini로 분석해 `silver.news_augmented` record로 변환합니다.
- **[CRITICAL]** Silver load는 동일 `executed_at` 배치를 먼저 삭제한 뒤 다시 적재하는 idempotent replace 계약을 유지합니다. 추출/변환된 items가 완전히 비어 있어도 기존 배치 데이터는 삭제하고, 적재할 row가 없으므로 JSON load job만 생략합니다.
- AI 증강은 deterministic chunk 단위로 Gemini를 호출합니다.
- Gemini chunk 실패나 result 누락은 transform phase 실패가 아니라 failed augmented record로 보존합니다.
- Augmentation transform count는 성공 augmented record 수이고, load count는 성공과 실패를 포함한 적재 record 수입니다.
- Transform이 `partial`이어도 Load phase는 실행해 성공/실패 record를 함께 적재합니다.
- Extract, Transform, Load phase 예외는 `failed_phase`와 `error_message`를 담아 `failed`로 전파합니다.
- Router는 pipeline status가 `partial`이면 HTTP 207, `failed`이면 HTTP 500으로 응답합니다.
