# 実装カード — S6 get-access-audit（担当: Sonnet）

**設計**: [design.md](design.md)（§3 が変更の正本）　**作業場所**: /Users/tanizawashingo/worktrees/salesanchor/release-s6-get-access-audit（ブランチ release/s6-get-access-audit）

## やること

1. 変更前の試験を書いて赤を確かめる
   - backend/tests/test_get_access_audit.py を新規作成し、design §5 の T1〜T4 を書く。
   - 変更前のコードで実行し、赤（ImportError・INSERT 0 回など）になる出力を /tmp/CC報告ファイル/s6-get-audit/impl/before.txt に保存する。
2. backend/app/middleware/audit.py を design §3 の 1〜5 どおりに変える。
3. 次を実行し、出力をそれぞれ /tmp/CC報告ファイル/s6-get-audit/impl/ に保存する。
   - 新しい試験（after.txt）
   - 既存の test_client_ip.py と test_security_hardening.py（existing.txt）
   - ruff check と ruff format --check（ruff.txt）
4. 1 コミットにまとめる（push はしない）。
   - 書式: `feat: S6 一覧の全件取得・ファイル出力の GET を記録し、閲覧の大量取得を検知する`
   - 末尾: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`

## 触るファイル

- backend/app/middleware/audit.py（変更）
- backend/tests/test_get_access_audit.py（新規）

これ以外は触らない。

## 実物点検（書く前に確かめる）

- audit.py の行番号が design（origin/main 449a77166）と合っているか。ずれていれば止めて報告する。
- `app.cache.get_redis` が同期関数で、非同期クライアントを返すか（cache.py:43）。
- test_client_ip.py:116-170 の AsyncSessionLocal の差し替え方と、test_security_hardening.py:419-476 の `_redis` の差し替え方。

## 想定分岐（こうなったら）

| 状況 | 対応 |
|---|---|
| 試験の中で `get_redis()` の差し替えが効かない（`_redis` が None 扱いになる） | 既存試験と同じ `patch("app.cache._redis", ...)` に合わせる。それでも効かなければ止めて報告 |
| ミドルウェア経由の試験で、Redis の incr が普段の GET に毎回呼ばれ、INSERT の数え方がずれる | T2 の「INSERT 0 回」は Redis を None（不通）にして確かめる。T4 は incr=501 を返す AsyncMock |
| `_insert_data_access` への切り出しで既存試験（test_client_ip.py の t6）が赤になる | 列・params の名前を変えていないか確かめる。直せなければ止めて報告 |
| ruff の指摘が触っていない行に出る | 直さない。そのまま報告 |
| フック・分類器に止められた | 言い換えて再試行しない。止めて原文を報告 |

## 守ること

- 各 Bash は `cd /Users/tanizawashingo/worktrees/salesanchor/release-s6-get-access-audit && ...` で始める。
- rm -rf は使わない。push と PR 作成はしない。
- 報告の 1 行目は DONE / BLOCKED: / NEEDS_DECISION: のどれか。生出力のパスを書き、結論は生出力に基づける。
