# Style Rules

import, method order, docstring, comment, logging을 수정할 때 읽습니다.

## Imports

- import 그룹은 Python 표준 라이브러리, third-party package, first-party `src.*` 순서로 작성합니다.
- 각 그룹 사이에는 빈 줄 하나를 두고, 그룹 내부는 가능한 한 알파벳순으로 정렬합니다.
- 같은 패키지 import는 가능한 한 한 그룹으로 묶습니다.
- `TYPE_CHECKING`은 순환 import를 피해야 할 때만 사용합니다.

## Methods

- 공개 파이프라인 메서드는 가능하면 `ETL단계_레이어_테이블명` 형태로 작성합니다.
- helper 이름은 반환값이나 처리 대상을 드러냅니다.
- Pydantic Entity 생성 helper는 반환 모델명을 포함합니다.
- 메서드는 public phase, orchestration helper, 호출 순서의 private helper, model creation helper 순서로 배치합니다.
- 레이어별 순서는 Provider, Store, Plugin, Service의 기존 패턴을 따릅니다.
- 같은 개념의 메서드는 같은 동사와 명사 구조를 유지합니다. 예: `transform_*`, `load_*`, `_create_*_model`.
- 함수 인자는 가능한 한 구체적인 Entity 또는 Schema 타입으로 명시합니다.

## Documentation And Comments

- 코드 주석, docstring, Pydantic `Field(description=...)`, Terraform BigQuery `description`은 영어로 작성합니다.
- 설명은 짧고 구체적으로 쓰고, 코드가 보장하지 않는 동작을 설명하지 않습니다.
- 함수와 메서드 docstring은 `Return ...`, `Fetch ...`, `Transform ...`처럼 imperative mood를 사용합니다.
- 클래스 docstring은 객체의 책임을 설명합니다.
- inline comment는 필요한 이유, 외부 제약, 예외 방지 목적을 설명할 때만 사용합니다.
- TODO comment는 이유와 방향을 함께 포함합니다.

## Logging

- 애플리케이션 로그 메시지는 영어로 작성합니다.
- 기본 형식은 `<Layer> <operation> [scope] <outcome> | key: value`입니다.
- source나 target을 `[]` prefix로 표현하지 말고 key-value 필드를 사용합니다.
- 레이어 이름은 `App`, `Router`, `Plugin`, `Store`, `Provider`처럼 책임 단위를 드러냅니다.
- item/chunk 단위 실패에는 scope를 사용하고, method 전체 실패에는 scope를 쓰지 않습니다.
- 자주 쓰는 필드는 `target`, `source`, `table`, `provider`, `method`, `news_id`, `batch_id`, `count`, `total`, `reason`, `error`, `status`, `status_code`입니다.

예시:

```text
Router request received | endpoint: refine, target: news
Plugin transform item failed | target: news-augmented, news_id: ..., batch_id: ..., reason: llm result missing
Store load skipped | table: bronze.news, reason: no items
```
