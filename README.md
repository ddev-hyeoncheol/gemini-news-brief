# Gemini News Brief

Gemini News Brief는 GCP 기반으로 뉴스 수집/가공 작업을 자동화하고, Cloud Run으로 API를 서빙하는 것을 목표로 하는 프로젝트입니다.

## 목표

- 뉴스 크롤링과 후처리 작업을 클라우드에서 자동 실행
- 데이터 적재와 스키마 관리를 BigQuery 중심으로 운영
- API/Worker를 Cloud Run에 배포해 서비스 제공
- 로컬에서는 복잡한 인프라 설정 없이 개발에만 집중

## 현재 구성

- FastAPI 기반 API 서비스
- FastAPI 기반 Worker 서비스
- BigQuery 데이터셋/테이블 생성 및 스키마 업데이트 스크립트
- Cloud Build를 통한 이미지 빌드, BigQuery 셋업, Cloud Run 배포 자동화

## 배포 방향

이 프로젝트는 로컬 실행보다 GCP 운영을 우선합니다.
개발은 코드 작성에 집중하고, 실행/스케줄링/배포는 Cloud Build + Cloud Run + BigQuery로 처리하는 구조를 지향합니다.
