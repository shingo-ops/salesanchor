# 現在地 — 閲覧ページの試験 2 本が期限切れのトークンで落ちる

**日付**: 2026-10-17　**基準**: origin/main 15114e878

## 事実
- backend/tests/test_viewer_tokens.py:134 の `test_iat_comparison_with_password_changed_at_fractional` と backend/tests/test_viewer_password.py:284 の `test_iat_floor_comparison_boundaries` は、固定日時 `datetime(2026, 10, 16, 10, 0, 0, 700000, tzinfo=timezone.utc)` をもとにトークンの iat を作る。
- トークンの exp は iat + 12 時間（test_viewer_tokens.py の `_token_at` は 43200 秒、test_viewer_password.py:169 は `viewer_tokens.VIEWER_TOKEN_TTL_SECONDS`）。そのため 2026-10-16 22:00 UTC を過ぎると期限切れになり、401 が返る。
- 2026-10-17 00:15Z の CI（Backend Tests run 38985273611、PR #4421）で、この 2 本が `assert 401 == 200` で落ちた。ほかの 6430 本は合格した（/tmp/CC報告ファイル/s6-get-audit/fix1-ci/failed.txt）。
- 手元でも、変更前は 2 failed / 32 passed だった（/tmp/CC報告ファイル/viewer-test-date/before.txt）。
- 2 本は f7797de7b（2026-10-16）で入った。同じファイルを触る open PR は無い（2026-10-17 に全 open PR の差分を確認）。
- 関係する ADR: 閲覧ページは ADR-1019。この ADR は試験の日付の決め方を定めていない。
