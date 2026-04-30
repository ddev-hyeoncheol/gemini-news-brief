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

## 🏗️ 아키텍처 및 파이프라인 흐름

이 프로젝트는 로컬 실행보다 GCP 운영을 우선하며, 개발은 코드 작성에 집중하고 실행/스케줄링/배포는 Cloud Build + Cloud Run + BigQuery로 처리하는 구조를 지향합니다.

파이프라인은 스케줄러에 의해 단 한 번의 API 호출로 트리거되며, 내부적으로 여러 소스의 작업을 비동기로 완벽하게 분리하여 처리합니다.

1. **Trigger**: Cloud Scheduler가 Worker API의 `/ingest` 엔드포인트 호출
2. **Collect (수집)**: RSS 피드에서 `window` 시간 조건에 맞는 기사만 필터링(`target_count`)한 후, 해당 기사들의 본문을 병렬로 스크래핑(`collected_count`)
3. **Load (적재)**: 특정 소스의 수집이 끝나는 즉시 다른 소스를 대기하지 않고 BigQuery로 개별 적재 실행 (`loaded_count`)
4. **Response**: 모든 작업이 끝나면 소스별 파이프라인 결과를 종합하여 HTTP 상태 코드와 함께 반환
    - 전체 성공: `200 OK`
    - 일부 성공/일부 실패: `207 Multi-Status`
    - 전체 실패: `500 Internal Server Error`

## 🚀 배포 및 자동화 구성

이 프로젝트는 배포 과정의 모든 것을 자동화하여 개발 생산성을 극대화합니다.

- **통합 워크로드**: FastAPI 기반 API 서빙 및 Worker 서비스 단일 컨테이너 운영
- **스키마 동기화**: `TIME_PARTITIONING` 등이 적용된 BigQuery 데이터셋/테이블 생성 및 스키마 자동 업데이트
- **CI/CD**: Cloud Build를 통한 완벽한 배포 파이프라인 구축 (이미지 빌드 ➡️ BigQuery 스키마 동기화 ➡️ Cloud Run 배포)

## 🛠️ 환경 변수 (Environment Variables)

| 변수명        | 설명                                                         | 기본값                          |
| ------------- | ------------------------------------------------------------ | ------------------------------- |
| `BQ_TABLE_ID` | 데이터를 적재할 BigQuery 테이블 ID (`project.dataset.table`) | `gemini-news-brief.bronze.news` |
| `PORT`        | FastAPI 서버 포트 (Cloud Run 자동 주입)                      | `8080`                          |
| `LOG_LEVEL`   | 로깅 레벨 (`DEBUG`, `INFO`, `WARNING`, `ERROR`)              | `INFO`                          |

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
    python -m src.worker.main
    ```
    > 서버가 실행되면 `http://localhost:8080/docs`에서 Swagger UI를 확인할 수 있습니다.

## 📝 API 사용 예시 (Usage Example)

**POST `/ingest`**

파이프라인을 트리거하여 지정된 시간(`window`) 내의 뉴스를 수집하고 적재합니다.

**Request (cURL)**

```bash
curl -X POST "http://localhost:8080/ingest" \
     -H "Content-Type: application/json" \
     -d '{"window": 60}'
```

**Response (JSON)**
성공적으로 파이프라인이 완료되면 `200 OK` (일부 실패 시 `207 Multi-Status`)와 함께 각 소스별 `target_count`(타겟 수), `collected_count`(수집 성공 수), `loaded_count`(적재 성공 수) 등 상세한 퍼널(Funnel) 메트릭을 반환합니다.
