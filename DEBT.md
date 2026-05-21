# Technical Debt

이 파일은 프로젝트 인프라, 설정 및 코드베이스의 장기적인 기술 부채를 추적하고 관리하기 위한 대장입니다.

## Infrastructure & Deployment

### [Security] Worker 서비스의 비인증 호출 허용
- **설명**: 현재 [cloudbuild.yml](file:///Users/supergrammer/WorkSpace/GitRepository/ddev-hyeoncheol/gemini-news-brief/cloudbuild/cloudbuild.yml)에서 `gemini-news-brief-fastapi-worker`를 배포할 때 `--allow-unauthenticated` 인자가 부여되어 외부 공개에 노출되어 있습니다.
- **영향**: 악의적인 무단 호출로 파이프라인 비용이 청구되거나 데이터 수집이 오작동할 위험이 있습니다.
- **해결 방안**: Worker 서비스 배포 시 `--no-allow-unauthenticated` 옵션으로 전환하고, 호출 트리거 주체(Cloud Scheduler, Pub/Sub 등)에 OIDC 토큰 인증 정보를 부여하여 내부 보안 연결을 완성해야 합니다.

## Resolved

### [Infra-Standard] GCR (gcr.io) 사용 유지 (해결: 2026-05-21)
- **조치**: 테라폼에 Artifact Registry 리포지토리 리소스를 추가하고 `cloudbuild.yml` 이미지 경로를 `${_REGION}-docker.pkg.dev` 구조로 갱신함.

### [Redundancy] Terraform Apply 시 -auto-approve 중복 전달 (해결: 2026-05-21)
- **조치**: `cloudbuild.terraform.yml` 내 apply args를 `["apply", "tfplan"]`으로 단일화함.
