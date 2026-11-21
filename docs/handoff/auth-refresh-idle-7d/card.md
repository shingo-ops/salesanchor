# 実装カード: ADR-1084 7 日使わなければログインし直し

- 設計: docs/handoff/auth-refresh-idle-7d/design.md §4（変更前後のコードはここが正）
- ブランチ: release/auth-refresh-idle-7d（既にある。設計書の commit が載っている）
- PO 承認: 2026-11-21「2」（7 日使わなければログインし直し）

## 手順

1. `git fetch origin` の後、`bash scripts/new-worktree.sh release/auth-refresh-idle-7d` で作業場所を作り、そこへ移る（clone のまま commit しない）。`git log --oneline -1` が origin/release/auth-refresh-idle-7d の先頭と同じことを確かめる。
2. `./scripts/dev/executor-preflight.sh || exit 1`
3. backend/app/auth/self_tokens.py を design.md §4 のとおりに 2 か所変える（定数 `REFRESH_IDLE_TTL` を :25（`REFRESH_ABSOLUTE_TTL`）の次に足す・`rotate_refresh_token` の UPDATE に `AND created_at > :idle_cutoff` と引数 `"idle_cutoff": now - REFRESH_IDLE_TTL` を足す）。ほかの行は変えない。
4. backend/tests/test_self_auth.py の `test_refresh_rejected_after_absolute_30_days` の直後に、design.md §4 の試験 2 本をそのまま足す。
5. `cd backend && python -m pytest tests/test_self_auth.py -q --no-cov` を流し、出力をファイルに書き出して全部読む。全件通ること（新しい 2 本を含む）。DB が無くて流せないときは、その出力をそのまま報告に書く（推測で合格と書かない）。
6. `git diff origin/release/auth-refresh-idle-7d --stat` で、変わったのが上の 2 ファイルだけであることを確かめる。
7. commit（文: `feat(auth): reject refresh after 7 days idle (ADR-1084)`）して `git -C <作業場所の絶対パス> push origin release/auth-refresh-idle-7d` を単独で流す。PR は作らない。

## 想定分岐

- §4 の「変更前」と実物が違う → 変えずに BLOCKED: で終え、違いを書く。
- 試験が落ちる → 直さずに出力を貼って BLOCKED: で終える。
- 見張りに止められる → 言い換えず、止めた命令と文面を書いて BLOCKED: で終える。

## 終わり方

最後の行に DONE: <commit の sha> か BLOCKED: <理由> を書く。
