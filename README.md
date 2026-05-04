# Gemini News Brief

Gemini News Brief는 GCP(Google Cloud Platform) 기반으로 뉴스 수집 및 가공 작업을 자동화하고, 이를 API로 제공하는 클라우드 네이티브(Cloud-Native) 서버리스 데이터 파이프라인 프로젝트입니다.

## 🎯 목표 및 철학

- **GCP 운영 우선주의**: 로컬 환경에서는 비즈니스 로직(크롤링/API) 개발에만 집중하고, 복잡한 인프라 설정과 실행/스케줄링은 클라우드 관리형 서비스에 전적으로 위임합니다.
- **고성능 데이터 파이프라인**: 병목 현상 없는 비동기 병렬 처리(End-to-End Parallelism)를 통해 뉴스 크롤링과 BigQuery 적재를 고속으로 수행합니다.
- **회복 탄력성 (Resilience)**: 특정 뉴스 소스에 장애가 발생해도 전체 파이프라인이 중단되지 않고 부분 성공(Partial Success)을 처리할 수 있는 견고한 에러 핸들링을 지향합니다.

## ⚙️ 기술 스택

- **Backend**: Python 3.12, FastAPI, Pydantic
- **Data/Scraping**: feedparser, newspaper3k
- **GCP Services**: BigQuery, Cloud Run, Cloud Build, Cloud Scheduler

## 🗂️ 프로젝트 구조

```
src/
├── api/
│   └── main.py                  # 공개 API 서비스 진입점 (헬스체크 등)
├── bigquery/
│   ├── setup_table.py           # 데이터셋·테이블 생성 및 스키마 동기화 스크립트
│   └── schema/
│       └── bronze/
│           └── news.py          # news 테이블 스키마 (파티션·클러스터링 포함)
├── core/
│   └── logger.py                # 로컬/GCP 환경 자동 전환 로거
├── models/
│   ├── entities/
│   │   └── news.py              # BronzeNewsModel (파이프라인 공통 엔티티)
│   └── schemas/
│       └── ingest.py            # 파이프라인 단계별 DTO (Fetch/Lookup/Enrich/Load)
└── worker/
    ├── main.py                  # Worker API 서비스 진입점
    ├── routers/
    │   └── ingest.py            # POST /ingest 엔드포인트
    ├── services/
    │   └── ingest.py            # 파이프라인 오케스트레이터 (IngestService)
    └── plugins/
        ├── collect.py           # 웹 통신 전담 플러그인 (fetch + enrich)
        ├── bigquery.py          # DB 통신 전담 플러그인 (lookup + load)
        └── sources/
            ├── base.py          # SourceBase 추상 기반 클래스
            └── yahoo_finance.py # Yahoo Finance 소스 구현체
```

## 🏗️ 아키텍처 및 파이프라인 흐름

이 프로젝트는 로컬 실행보다 GCP 운영을 우선하며, 개발은 코드 작성에 집중하고 실행/스케줄링/배포는 Cloud Build + Cloud Run + BigQuery로 처리하는 구조를 지향합니다.

파이프라인은 스케줄러에 의해 단 한 번의 API 호출로 트리거되며, 내부적으로 여러 소스의 작업을 비동기로 완벽하게 분리하여 처리합니다.

1. **Trigger**: Cloud Scheduler가 Worker API의 `/ingest` 엔드포인트를 호출합니다.
2. **Fetch (RSS 수집)**: 외부 언론사의 RSS 피드에서 전체 기사 목록(껍데기)을 빠르게 가져옵니다. (`fetched_count`)
3. **Lookup (중복 검사)**: BigQuery의 기존 데이터와 대조하여 신규/수정된 타겟 기사만 필터링합니다. (`lookup_count`)
4. **Enrich (본문 추출)**: 필터링된 타겟 기사들에 대해서만 `newspaper3k`를 통해 병렬로 본문을 스크래핑합니다. (`enriched_count`)
5. **Load (DB 적재)**: 내용이 완전히 채워진 기사들을 BigQuery에 병합(Upsert)합니다. (`loaded_count`)
6. **Response**: 모든 작업이 끝나면 소스별 파이프라인 결과를 종합하여 HTTP 상태 코드와 함께 반환합니다.
    - 전체 성공: `200 OK`
    - 일부 성공/일부 실패: `207 Multi-Status`
    - 전체 실패: `500 Internal Server Error`

## 💡 개발 주안점 (Design Considerations)

- **지연 평가(Lazy Evaluation)를 통한 리소스 최적화**: 무거운 작업인 스크래핑(`Enrich`)을 무작정 수행하지 않고, DB와 대조(`Lookup`)하여 반드시 필요한 타겟 기사에 대해서만 실행되도록 설계하여 네트워크 및 컴퓨팅 리소스를 획기적으로 절약했습니다.
- **도메인(Domain) 기반 플러그인 설계**: 파이프라인의 작업자들을 기능 단위가 아닌 통신 대상 도메인 기준으로 분리했습니다. `CollectPlugin`은 웹(Web) 통신을 전담하고, `BigQueryPlugin`은 데이터베이스(DB) 통신을 전담합니다.
- **비동기 이벤트 루프 안전성 확보**: `asyncio.Semaphore`와 같은 비동기 객체들을 모듈 레벨에서 즉시 생성하지 않고, FastAPI 앱의 이벤트 루프가 완전히 구동된 이후 첫 API 요청 시점에 생성되도록 지연 초기화(Lazy Initialization) 패턴을 적용하여 런타임 크래시를 방지했습니다.
- **회복 탄력성과 조기 종료(Early Return)**: 파이프라인 각 단계에서 에러가 발생하면 다음 단계로 전파하지 않고 즉시 격리(Isolation)합니다. 또한 `asyncio.gather(..., return_exceptions=True)`를 활용해 단일 기사 스크래핑 실패가 전체 프로세스를 중단시키지 않도록 구성했습니다.

## 🚀 배포 및 자동화 구성

이 프로젝트는 배포 과정의 모든 것을 자동화하여 개발 생산성을 극대화합니다.

- **통합 워크로드**: FastAPI 기반 API 서빙 및 Worker 서비스 단일 컨테이너 운영
- **스키마 동기화**: `TIME_PARTITIONING` 등이 적용된 BigQuery 데이터셋/테이블 생성 및 스키마 자동 업데이트
- **CI/CD**: Cloud Build를 통한 완벽한 배포 파이프라인 구축 (이미지 빌드 ➡️ BigQuery 스키마 동기화 ➡️ Cloud Run 배포)

## 🛠️ 환경 변수 (Environment Variables)

| 변수명      | 설명                                                                        | 기본값      |
| ----------- | --------------------------------------------------------------------------- | ----------- |
| `PORT`      | FastAPI 서버 포트 (Cloud Run 자동 주입)                                     | `8080`      |
| `LOG_LEVEL` | 로깅 레벨 (`DEBUG`, `INFO`, `WARNING`, `ERROR`)                             | `INFO`      |
| `K_SERVICE` | Cloud Run이 자동 주입하는 서비스명. 값이 있으면 GCP JSON 로그 포맷으로 전환 | (자동 주입) |

## 💻 로컬 실행 가이드 (Quick Start)

1. 프로젝트를 클론하고 의존성 패키지를 설치합니다.
    ```bash
    git clone https://github.com/ddev-hyeoncheol/gemini-news-brief.git
    cd gemini-news-brief
    pip install -r requirements.txt
    ```
2. (선택) 로컬에서 실제 BigQuery에 적재하려면 GCP 인증 정보를 설정합니다.
    ```bash
    export GOOGLE_APPLICATION_CREDENTIALS="path/to/your/service-account-key.json"
    ```
3. Uvicorn 서버를 실행합니다.

    ```bash
    uvicorn src.worker.main:app --host 0.0.0.0 --port 8080 --reload
    ```

    > 서버가 실행되면 `http://localhost:8080/docs`에서 Swagger UI를 확인할 수 있습니다.

    > **참고**: GCP 자격증명이 설정되지 않은 경우 `BigQueryPlugin`이 자동으로 Mock 모드로 전환되어, 실제 BigQuery 연결 없이도 파이프라인 전체 흐름을 테스트할 수 있습니다.

## 📝 API 사용 예시 (Usage Example)

**POST `/ingest`**

파이프라인을 트리거하여 등록된 모든 소스의 뉴스를 수집, 검사, 추출, 적재합니다.

**Request (cURL)**

```bash
curl -X POST "http://localhost:8080/ingest" \
     -H "Content-Type: application/json" \
     -d '{}'
```

**Response (JSON)**

성공적으로 파이프라인이 완료되면 `200 OK` (일부 실패 시 `207 Multi-Status`)와 함께 각 소스별 `fetched_count`(RSS 수집 항목 수), `lookup_count`(본문 추출 대상 수), `enriched_count`(본문 추출 성공 수), `loaded_count`(DB 적재 성공 수) 등 상세한 퍼널(Funnel) 메트릭을 반환합니다.

```json
{
    "executed_at": "2026-05-04T00:00:00Z",
    "status": "success",
    "fetched_count": 20,
    "lookup_count": 5,
    "enriched_count": 4,
    "loaded_count": 4,
    "sources": [
        {
            "source": "yahoo_finance",
            "status": "success",
            "fetched_count": 20,
            "lookup_count": 5,
            "enriched_count": 4,
            "loaded_count": 4,
            "started_at": "2026-05-04T00:00:00.100Z",
            "completed_at": "2026-05-04T00:00:03.200Z",
            "failed_phase": null,
            "error_message": null
        }
    ]
}
```

## 🔌 새 뉴스 소스 추가하기

1. `src/worker/plugins/sources/` 아래에 새 파일을 생성합니다.
2. `SourceBase`를 상속하고 `source`, `RSS_URL` 클래스 변수와 `fetch()` 메서드를 구현합니다.
    - `fetch()`는 RSS 항목을 `BronzeNewsModel` 리스트로 매핑하여 반환합니다.
    - `content`/`author`/`thumbnail_url`은 채우지 않습니다 (Enrich 단계에서 자동 처리).
    - `_fetch_feed()`, `_parse_image_url()`, `_parse_published_at()`, `make_news_id()` 헬퍼는 `SourceBase`에서 기본 제공됩니다.

    ```python
    from typing import ClassVar
    from src.models.entities.news import BronzeNewsModel
    from src.models.schemas.ingest import IngestRequest
    from src.worker.plugins.sources.base import SourceBase

    class CnbcSource(SourceBase):
        source: ClassVar[str] = "cnbc"
        RSS_URL: ClassVar[str] = "https://search.cnbc.com/rs/search/combinedcms/view.xml?..."

        async def fetch(self, request: IngestRequest) -> list[BronzeNewsModel]:
            feed = await self._fetch_feed()
            results = []
            for entry in feed.entries:
                published_at = self._parse_published_at(entry)
                if published_at is None:
                    continue
                results.append(BronzeNewsModel(
                    news_id=self.make_news_id(entry.get("link", "")),
                    source=self.source,
                    # ... 필드 매핑
                ))
            return results
    ```

3. `src/worker/services/ingest.py`의 `get_ingest_service()` 내 `source_plugins`에 추가합니다.

    ```python
    _ingest_service = IngestService(
        source_plugins=[
            CollectPlugin(source=YahooFinanceSource(semaphore=source_semaphore)),
            CollectPlugin(source=CnbcSource(semaphore=source_semaphore)),  # 추가
        ],
        db_plugin=BigQueryPlugin(semaphore=db_semaphore, client=bigquery_client),
    )
    ```
