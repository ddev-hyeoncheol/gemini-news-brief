# Gemini News Brief 프로젝트 장기 전환 계획

## 1. 전체 방향성

이 프로젝트의 장기 목표는 단일 배치 애플리케이션 안에서 수집, 정제, AI 처리, 서빙을 모두 수행하는 구조에서 벗어나, 각 계층의 책임을 명확히 분리한 데이터 플랫폼 구조로 전환하는 것이다.

현재 구조는 `BatchService.run_pipeline()` 안에서 `BRONZE NEWS → SILVER NEWS → SILVER NEWS_AUGMENTED`가 순차 실행되는 형태이다. 즉 수집, 정제, AI 증강이 하나의 파이프라인 호출 안에 강하게 결합되어 있다.

또한 현재 Bronze 저장은 `BronzeStore.load_bronze_news()`에서 BigQuery `bronze.news`에 직접 JSON load job을 수행하는 방식이다. 장기적으로 Bronze는 BigQuery가 아니라 Cloud Storage 기반 Data Lake로 옮기고, BigQuery는 Silver 이후의 정제·분석·서빙 준비 계층으로 사용하는 방향이 맞다.

최종 목표 구조는 다음과 같다.

```text
Ingest Project
  → Cloud Storage Bronze Data Lake

Warehouse Project
  → BigQuery external/staging
  → Dataform
  → silver.news
  → silver.news_augmented
  → mart / serving export

Serving Project
  → Firestore / Search / Vector DB
  → Cloud Run API
  → User-facing service
```

단, `silver.news → silver.news_augmented`는 단기적으로 기존 Gemini API 기반 Cloud Run worker를 유지하되, 장기적으로 Vertex AI 기반 처리로 전환한다.

---

## 2. 프로젝트 분리 기준

장기적으로 프로젝트는 최소 3개 경계로 나눈다.

```text
1. Ingest
2. Warehouse
3. Serving
```

AI augmentation은 처음에는 Warehouse 내부 기능으로 둔다. 이후 Vertex AI 사용량, 모델 실험, embedding, batch prediction, retry/fallback 구조가 커지면 별도 `enrichment` 프로젝트로 분리할 수 있다.

따라서 단계별 목표는 다음과 같다.

```text
초기 목표:
  Ingest / Warehouse / Serving 3개 경계

확장 목표:
  Ingest / Warehouse / Enrichment / Serving 4개 경계
```

---

## 3. Ingest Project 계획

### 3.1 역할

Ingest의 책임은 외부 뉴스 데이터를 가져와 raw 형태로 안전하게 저장하는 것이다. 수집 로직의 BigQuery 의존성을 완전히 배제하기 위해, 중복 수집 방지(이미 수집된 기사 검사)는 Firestore를 활용하여 수행한다.

Ingest가 담당할 작업은 다음이다.

```text
- RSS feed fetch
- source별 entry parsing
- Firestore 기반 중복 수집 필터링 (entry_url 또는 news_id 존재 검사)
- newspaper4k 기반 HTML enrich (신규 기사에 한함)
- BronzeNewsModel 생성
- GCS JSONL 저장
- _SUCCESS.json 또는 manifest.json 저장
```

Ingest가 담당하지 않을 작업은 다음이다.

```text
- BigQuery silver.news 생성
- BigQuery를 통한 수집 중복 조회 및 적재
- Dataform transformation
- LLM augmentation
- serving API
- 사용자 검색/조회
```

### 3.2 저장 위치

Bronze raw는 Cloud Storage에 JSONL로 저장한다.

추천 경로는 다음과 같다.

```text
gs://{bucket}/bronze/news/data/source={source}/dt={YYYY-MM-DD}/hour={HH}/batch_id={batch_id}/part-00000.jsonl

gs://{bucket}/bronze/news/manifests/source={source}/dt={YYYY-MM-DD}/hour={HH}/batch_id={batch_id}/_SUCCESS.json
```

`data`와 `manifests`를 분리하는 이유는 BigQuery external table 또는 load job이 `part-*.jsonl`만 읽도록 하기 위해서다. `_SUCCESS.json`이 같은 wildcard에 섞이면 schema mismatch가 발생할 수 있습니다.

### 3.3 Ingest 완료 기준

Ingest는 다음 조건을 만족하면 완료된 것으로 본다.

```text
- Firestore 조회를 통해 중복 기사는 스크래핑 단계 진입 전에 필터링됨
- 10분 단위 batch_id 생성
- source별 JSONL 파일 생성
- source별 _SUCCESS.json 생성
- GCS에 저장된 JSONL을 Python에서 재독해 가능
- BigQuery에 직접 bronze.news를 쓰지 않음
- Cloud Run Job 또는 Cloud Run Service에서 독립 실행 가능
```

---

## 4. Warehouse Project 계획

### 4.1 역할

Warehouse는 Cloud Storage Bronze raw를 BigQuery 분석 계층으로 정제하는 영역이다.

Warehouse가 담당할 작업은 다음이다.

```text
- GCS Bronze JSONL external table 또는 staging table 구성
- Dataform 기반 silver.news 생성
- Overwrite 방식으로 재처리 시 멱등성을 보장하는 쿼리 적용
- partition / clustering
- data quality assertion
- mart table/view 생성
- serving export source 생성
```

기존 Python of `SilverNewsModel.from_bronze_news()`는 `status == "success"`이고 `content is not None`인 row만 통과시키며, `canonical_url or entry_url`을 대표 URL로 사용한다. 이 로직은 SQL로 옮기기 적합하다.

### 4.2 Dataform 도입 방향

Dataform은 `bronze raw → silver.news` 변환의 중심이 된다.

초기에는 다음 구조를 추천한다.

```text
GCS JSONL
  → BigQuery external table: bronze_ext.news_raw
  → Dataform incremental table: silver.news (Overwrite 기반 멱등성 쿼리)
```

장기적으로 데이터량이 늘거나 external table 성능/안정성 문제가 생기면 다음 구조로 전환한다.

```text
GCS JSONL
  → BigQuery native staging table: bronze_staging.news_raw
  → Dataform incremental table: silver.news
```

### 4.3 silver.news 설계

`silver.news`는 정제된 뉴스 원문 테이블이다.

주요 필드는 현재 모델을 유지한다.

```text
executed_at
news_id
source
title
url
published_at
updated_at
raw_authors
raw_content
image_url
thumbnail_url
language
loaded_at (Dataform SQL에서 CURRENT_TIMESTAMP()를 기본값으로 사용)
```

권장 partition과 clustering은 다음이다.

```text
Partition:
  DATE(published_at)

Clustering:
  source
  news_id
```

### 4.4 dedupe 및 멱등성 정책

Bronze raw는 append-only로 두고, 중복 제거는 Silver에서 수행한다.

기본 dedupe 및 멱등성 적재 기준은 다음이다.

```text
news_id 기준 latest successful record 선택
동일 news_id가 여러 batch에 있으면 published_at 또는 loaded_at 기준 최신 row 선택
배치 재처리 시 동일 executed_at 데이터가 중복 적재되지 않도록 Overwrite 쿼리를 사용해 멱등성 보장
```

초기에는 단순하게 `ROW_NUMBER()`로 처리한다.

```sql
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY news_id
  ORDER BY executed_at DESC, loaded_at DESC
) = 1
```

### 4.5 Warehouse 완료 기준

Warehouse는 다음 조건을 만족하면 완료된 것으로 본다.

```text
- GCS Bronze JSONL을 BigQuery에서 읽을 수 있음
- Dataform으로 silver.news 생성 가능
- silver.news가 partitioned / clustered table로 생성됨
- news_id 중복 제거 및 Overwrite 기반의 멱등성 적재 가능
- assertion 실패 시 workflow 실패 처리 가능
- Python _run_silver_news 의존도 제거
```

---

## 5. AI Augmentation / Vertex AI 전환 계획

### 5.1 현재 위치

현재 `silver.news → silver.news_augmented`는 Python worker에서 Gemini provider를 호출하는 구조다. 현재 `BatchService`도 `SILVER NEWS_AUGMENTED` 단계를 pipeline task로 포함하고 있다.

단기적으로는 이 구조를 유지하되, `silver.news` 생성은 Dataform으로 넘기고, AI augmentation worker는 `silver.news`를 읽어 `silver.news_augmented`에 적재하는 역할만 맡긴다.

### 5.2 단기 구조

```text
Dataform
  → silver.news

Cloud Run AI Augment Worker
  → BigQuery silver.news extract
  → Gemini API call
  → BigQuery silver.news_augmented load
```

### 5.3 장기 Vertex AI 구조

장기적으로는 다음 구조로 전환한다.

```text
BigQuery silver.news
  → Vertex AI Gemini / Batch Prediction / Generative AI API
  → silver.news_augmented
```

또는 더 분리하면 다음과 같다.

```text
silver.news
  → enrichment input table
  → Vertex AI processing
  → enrichment result table
  → Dataform merge
  → silver.news_augmented
```

### 5.4 provider abstraction

Vertex AI 전환을 쉽게 하기 위해 먼저 provider interface를 분리한다.

```text
AiProvider
  - GeminiApiProvider
  - VertexAiProvider
```

현재는 Gemini API를 직접 쓰더라도, 상위 service는 provider 구현체를 몰라야 한다.

권장 interface는 다음과 같다.

```python
class AiNewsAugmentationProvider:
    async def augment_news_batch(
        self,
        items: list[SilverNewsModel],
    ) -> list[SilverNewsAugmentedModel]:
        ...
```

### 5.5 silver.news_augmented 유지 전략

`silver.news_augmented`는 장기적으로도 BigQuery에 유지한다.

필수 metadata는 다음이다.

```text
model_provider
model_version
prompt_version
schema_version
executed_at
news_id
loaded_at
```

Vertex AI로 전환하더라도 `model_provider = "vertex_ai"` 또는 `model_provider = "google_vertex_ai"`처럼 명확히 남긴다.

### 5.6 AI Augmentation 완료 기준

```text
- silver.news 생성과 AI augmentation 실행이 분리됨
- AI worker는 silver.news만 source로 사용
- provider interface가 Gemini API / Vertex AI 교체 가능하도록 분리됨
- silver.news_augmented에 model_provider/model_version 기록
- failed item retry 가능
- 이미 augmented된 news_id skip 가능
```

---

## 6. Serving Project 계획

### 6.1 역할

Serving은 사용자-facing API와 검색/조회 최적화 계층이다.

Serving이 담당할 작업은 다음이다.

```text
- 최신 뉴스 목록 API
- 뉴스 상세 API
- 카테고리/시장 엔티티 기반 조회
- 검색 API
- embedding/vector search
- Firestore 또는 별도 serving DB 관리
- cache
```

Serving이 직접 BigQuery `silver` 전체를 읽는 구조는 피한다. 대신 Warehouse에서 serving 전용 mart/export를 만든다.

```text
BigQuery mart.latest_news
BigQuery mart.news_search_source
BigQuery mart.market_entity_news
```

Serving은 이 mart를 기반으로 Firestore/Search/Vector DB에 필요한 subset만 복제한다.

### 6.2 Serving 저장소

초기에는 Firestore를 serving DB로 사용할 수 있다.

```text
Firestore collections:
  news
  news_by_category
  news_by_market_entity
  latest_news
```

검색이 중요해지면 별도 검색 계층을 둔다.

```text
초기:
  Firestore

중기:
  Firestore + embedding table

장기:
  Vector DB / Vertex AI Vector Search / AlloyDB pgvector 등 검토
```

### 6.3 Serving 완료 기준

```text
- BigQuery silver/mart와 serving DB가 분리됨
- 사용자 API는 BigQuery raw/silver에 직접 의존하지 않음
- Firestore 또는 search index에 serving subset 적재 가능
- serving API는 독립 Cloud Run service로 실행 가능
```

---

## 7. Terraform 전환 계획

Terraform도 서비스 경계에 맞춰 나눈다.

단, 초기에는 state를 바로 나누지 않는다. 먼저 module 경계를 만든다.

### 7.1 단기 구조

```text
terraform/
  storage-lake.tf
  bigquery-silver.tf
  dataform.tf
  cloud-run-ingest.tf
  cloud-run-augment.tf
  cloud-scheduler.tf
  artifact-registry.tf
  iam.tf
```

### 7.2 중기 구조

```text
terraform/
  modules/
    shared/
    ingest/
    warehouse/
    enrichment/
    serving/

  envs/
    dev/
      main.tf
      variables.tf
      outputs.tf
      terraform.tfvars
```

### 7.3 장기 구조

```text
terraform/
  envs/
    prod/
      foundation/
      ingest/
      warehouse/
      enrichment/
      serving/
```

state 분리는 운영 안정성이 필요해진 뒤 진행한다.

권장 순서는 다음이다.

```text
1. foundation
2. warehouse
3. ingest
4. enrichment
5. serving
```

---

## 8. GCP Project 분리 계획

처음에는 하나의 GCP project 안에서 논리적으로 분리한다.

```text
gemini-news-brief-dev
  - Cloud Run ingest
  - Cloud Run augment
  - GCS data lake
  - BigQuery
  - Dataform
  - Firestore
```

장기적으로는 다음처럼 분리한다.

```text
gemini-news-ingest-prod
  - Cloud Run Ingest
  - Cloud Scheduler
  - source secrets

gemini-news-warehouse-prod
  - GCS Data Lake
  - BigQuery
  - Dataform

gemini-news-enrichment-prod
  - Vertex AI
  - Cloud Run AI orchestrator
  - enrichment service account

gemini-news-serving-prod
  - Cloud Run API
  - Firestore
  - Search / Vector DB
```

다만 4개 project 분리는 최종 단계다. 처음부터 나누면 IAM, Terraform, 배포 복잡도가 너무 커진다.

---

## 9. 실행 로드맵

### Phase 0. Contract 정리

목표는 schema와 데이터 계약을 먼저 확정하는 것이다.

작업:

```text
- BronzeNewsModel schema 확정
- SilverNewsModel schema 확정
- SilverNewsAugmentedModel schema 확정
- GCS JSONL schema version 정의
- batch_id 규칙 정의
- Firestore 수집 중복 여부 인덱스 스키마 정의
```

완료 기준:

```text
- schema_version 명시
- GCS path convention 문서화
```

---

### Phase 1. Ingest 분리

목표는 Bronze 수집을 BigQuery에서 Cloud Storage로 옮기는 것이다.

작업:

```text
- CloudStorageProvider 추가
- BronzeLakeStore 추가
- FirestoreProvider 및 중복 필터 로직 추가
- requirements.txt에 google-cloud-storage, google-cloud-firestore 추가
- GCS bucket 및 Firestore 설정 추가
- Bronze load를 BigQuery에서 GCS JSONL로 변경
- /batch/bronze/news 독립 실행 검증
```

완료 기준:

```text
- BigQuery bronze.news에 쓰지 않음
- GCS에 batch별 JSONL 생성
- Firestore에 수집 이력 기록 및 중복 필터 작동
- GCS JSONL 재독해 가능
```

---

### Phase 2. Dataform 기반 Silver 전환

목표는 Python의 `_run_silver_news()`를 Dataform으로 대체하는 것이다.

작업:

```text
- Dataform repository 구성
- bronze_ext.news_raw external table 생성
- silver.news incremental table 생성 (Overwrite 멱등성 쿼리 적용)
- dedupe SQL 작성
- assertions 추가
- 기존 Python Silver transform 비활성화
```

완료 기준:

```text
- Dataform 실행만으로 silver.news 생성 가능
- content 없는 row 제외
- failed row 제외
- news_id dedupe 및 멱등성 덮어쓰기 적용
- partition/clustering 적용
```

---

### Phase 3. AI Augmentation 분리

목표는 AI 처리 단계를 Dataform Silver 이후 독립 실행되도록 만드는 것이다.

작업:

```text
- AI worker를 /batch/silver/news_augmented 전용으로 단순화
- silver.news에서 미처리 row만 추출
- silver.news_augmented에 append 또는 merge
- provider interface 추가
- GeminiApiProvider를 interface 구현체로 이동
```

완료 기준:

```text
- full pipeline 없이 augmentation만 실행 가능
- 이미 처리된 news_id skip 가능
- failed item retry 가능
- model_provider/model_version 기록
```

---

### Phase 4. Vertex AI 전환 준비

목표는 Gemini API 직접 호출 구조를 Vertex AI로 교체 가능한 구조로 만드는 것이다.

작업:

```text
- VertexAiProvider 추가
- provider selection config 추가
- prompt_version 관리
- schema validation 유지
- 비용/token/latency logging 표준화
- Gemini API와 Vertex AI 결과 비교
```

완료 기준:

```text
- 동일 Silver input으로 Gemini API / Vertex AI A/B 실행 가능
- silver.news_augmented schema 변경 없이 provider 교체 가능
- model_provider로 결과 출처 구분 가능
```

---

### Phase 5. Serving 분리

목표는 사용자-facing 조회 계층을 BigQuery 분석 계층에서 분리하는 것이다.

작업:

```text
- mart.latest_news 생성
- mart.news_search_source 생성
- Firestore serving collection 설계
- BigQuery mart → Firestore export job 생성
- Cloud Run serving API 추가
```

완료 기준:

```text
- 사용자는 BigQuery silver를 직접 조회하지 않음
- Serving API가 Firestore/search index를 통해 응답
- Warehouse 장애와 Serving 장애가 분리됨
```

---

### Phase 6. Terraform / GCP Project 분리

목표는 운영 경계를 인프라 경계로 확장하는 것이다.

작업:

```text
- Terraform modules 분리
- envs/dev, envs/prod 구성
- shared / ingest / warehouse / enrichment / serving module 정리
- remote state 분리 검토
- GCP project 분리 검토
- cross-project IAM 구성
```

완료 기준:

```text
- ingest 변경이 warehouse 리소스를 직접 건드리지 않음
- serving 배포가 ingest/warehouse와 독립됨
- Vertex AI 권한이 enrichment 영역에 격리됨
```

---

## 10. 우선순위

가장 먼저 해야 할 순서는 다음이다.

```text
1. GCS Bronze Data Lake 전환 및 Firestore 중복 체크 연동
2. Dataform으로 silver.news 생성 (Overwrite 멱등성 쿼리)
3. AI augmentation 독립 실행
4. Vertex AI provider abstraction
5. Serving 저장소 분리
6. Terraform module 분리
7. GCP project/state 분리
```

즉 지금 당장 해야 할 핵심은 **Ingest 분리와 Bronze 저장소 전환 및 중복 제거 분리**이다.
Serving이나 GCP project 분리는 나중에 해도 된다.

---

## 11. 최종 목표 아키텍처

최종적으로 프로젝트는 다음 구조를 지향한다.

```text
[Ingest]
Cloud Scheduler
  → Cloud Run Ingest (Firestore로 중복 체크)
  → GCS Bronze JSONL

[Warehouse]
Dataform
  → BigQuery bronze external/staging
  → BigQuery silver.news (Overwrite 멱등성 보장)
  → BigQuery mart.*

[Enrichment]
Cloud Run or Vertex AI
  → BigQuery silver.news
  → Vertex AI Gemini
  → BigQuery silver.news_augmented

[Serving]
Export Job
  → Firestore / Search / Vector DB
  → Cloud Run API
```

이 구조의 핵심은 다음이다.

```text
- Bronze는 Data Lake
- Ingest 중복 관리는 Firestore를 활용해 BigQuery 완전 분리
- Silver는 BigQuery 정제 계층
- Augmented는 AI enrichment 계층
- Mart는 serving 준비 계층
- Serving은 별도 low-latency 조회 계층
```

---

## 12. 판단 기준

앞으로 기능을 추가할 때는 아래 기준으로 위치를 결정한다.

```text
외부에서 데이터를 가져오는가?
  → Ingest

GCS/BigQuery 데이터를 SQL로 정제하는가?
  → Warehouse / Dataform

LLM, embedding, model provider가 필요한가?
  → Enrichment / Vertex AI

사용자 요청을 직접 처리하는가?
  → Serving

공통 schema나 utility인가?
  → shared package
```

이 기준을 유지하면 프로젝트가 커져도 책임 경계가 무너지지 않는다.
