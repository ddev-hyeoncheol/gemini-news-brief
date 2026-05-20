# Commit Rules

커밋 메시지 규칙의 원본은 `CONTRIBUTING.md`입니다.

commit 요청을 받으면:

1. `CONTRIBUTING.md`의 `Commit Message Convention`을 따릅니다.
2. 커밋 전 `git status --short`와 변경 diff를 확인합니다.
3. 커밋 메시지에 `Co-Authored-By`를 포함하지 않습니다.
4. `git commit -m`을 여러 번 사용할 때 각 `-m`은 별도 paragraph가 됩니다. Bullet list body는 하나의 body block으로 작성합니다.
