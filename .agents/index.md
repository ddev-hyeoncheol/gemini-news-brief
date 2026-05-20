# Agent Harness Index

현재 작업에 필요한 하네스 문서만 골라 읽기 위한 인덱스입니다.

## Always

- `.agents/rules/core.md`

## Workflows

코드나 문서 변경:

- `.agents/workflows/implement.md`

리뷰 요청:

- `.agents/workflows/review.md`

리팩토링:

- `.agents/workflows/refactor.md`

새 뉴스 source 추가:

- `.agents/workflows/add-news-source.md`

## Context

현재 리팩토링 방향, 임시 결정, 진행 중인 맥락이 작업 결과에 영향을 주는 경우:

- `MEMORY.md`

## Domain Rules

아키텍처, 레이어 책임, target, Provider 변경:

- `.agents/rules/architecture.md`

Ingest, Refine, count, 실패 전파 변경:

- `.agents/rules/pipeline.md`

Entity, Schema, BigQuery, Terraform, field description 변경:

- `.agents/rules/data-contracts.md`

## Cross-Cutting Rules

import, method order, docstring, comment, logging 변경:

- `.agents/rules/style.md`

## Special Rules

하네스 문서 추가/수정:

- `.agents/rules/harness-docs.md`

commit 요청:

- `.agents/rules/commit.md`

## Guardrail

`.agents/` 아래 모든 파일을 기본으로 한 번에 읽지 않습니다. 작업 범위가 여러 영역에 걸치면 해당 파일만 조합해서 읽습니다.
