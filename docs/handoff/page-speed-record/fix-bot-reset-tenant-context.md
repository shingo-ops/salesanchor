# 実装カード: Bot 登録・更新・鍵の作り直しの保存直後に会社の文脈を付け直す

作成: POの委任に基づくClaude Opus（設計）。2026-10-31。前の直し（docs/handoff/page-speed-record/fix-bot-code-quote-subtitle.md）の本番確認で見つかった続きの不具合。

## 最初に読むもの
(1) scripts/agent-hooks/cloud/rules.md（必ず従う）
(2) AGENTS.md の「ブランチと作業場所」

## PO の承認
PO が 2026-10-31 に「見つけた不具合2つを直す」を選び（返事「1」）、「PRマージ、デプロイまで完走させてくれ」と依頼した。Bot をコード空欄で登録して 500 にならないことがその受け入れ条件で、この直しはその続き。範囲は下の 1 件だけ。

## 守ること
- `rm` は使わない。一時フォルダは `mktemp -d` で新しく作る。
- Python は `python3.12 -m venv "$(mktemp -d)/venv"`（無ければ `uv venv --python 3.12 <場所>`）で venv を作り、その venv の bin/pip・bin/python だけを使う。backend の試験に要る依存は backend/requirements*.txt から入れる。どちらでも作れなければ出力全文を書いて BLOCKED:。
- reset・rebase・force・merge・--no-verify は使わない。PR は作らない（コード変更を含むため、手元で作る）。push まで。

## 作業場所
枝 release/fix-bot-tenant-context-after-commit は、このカードだけを載せて push 済み。rules.md の「すでに push 済みの枝の続き」の手順で作業場所を作り、`git switch -C release/fix-bot-tenant-context-after-commit origin/release/fix-bot-tenant-context-after-commit` のあと `git rev-parse HEAD` と `git rev-parse origin/release/fix-bot-tenant-context-after-commit` が同じことを貼る。

## 事実（本番 2026-10-31 06:51:59 UTC・tenant 001）
- 前の直しの反映後、画面からコード空欄で Bot を登録すると 500。ログ: `InvalidTextRepresentationError: invalid input syntax for type integer: ""`。失敗した SQL は登録後の読み直し（`SELECT ... FROM tenant_001.bots b LEFT JOIN tenant_001.staff s ...`）。
- 行は保存されている（ai_ro.tenant_001__bots に id=2・06:51:58 作成）。つまり INSERT と commit は通り、commit の後の SELECT だけが落ちている。
- tenant_001.bots の行ごとの守り（RLS）は `tenant_id = current_tenant_id()`、audit_logs は `current_setting('app.tenant_id', true)::integer`（pg_policies）。commit の後は app.tenant_id が空になり、空文字を数字に変えようとして落ちる。
- backend/app/auth/dependencies.py:392 `reset_tenant_context(db, tenant_id)` が「commit の後に文脈を付け直す」関数（ADR-072 Phase 2.5）。companies.py:609-610 などは `await db.commit()` の直後に呼んでいる。bots.py は 1 か所も呼んでいない。
- bots.py で commit の後にテナントの表を読む箇所は 3 つ: create_bot（180 行の commit → 188 行の SELECT）、update_bot（240 → 242）、rotate_bot_api_key（271 → 273）。delete_bot（302）は commit の後に表を読まない。

## 変更（backend/app/routers/bots.py だけ）
(1) 24-29 行の import に `reset_tenant_context,` を足す（`require_permission,` の次、アルファベット順）:
```python
from app.auth.dependencies import (
    get_current_tenant,
    get_current_user,
    require_permission,
    reset_tenant_context,
    tenant_table_ref,
)
```
(2) create_bot の try の中、`await db.commit()`（180 行）の次の行に `await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5` を足す（try の中・同じ字下げ）。
(3) update_bot の `await db.commit()`（240 行）の次の行に同じ 1 行を足す。
(4) rotate_bot_api_key の `await db.commit()`（271 行）の次の行に同じ 1 行を足す。
- delete_bot・ほかの行・schema・migration は触らない。

## 試験（backend/tests/test_bots_owner_users.py の末尾に足す。既存の seeded 固定具と `_payload` の書き方に合わせる）
- `test_create_bot_resets_tenant_context_after_commit`: `app.routers.bots.reset_tenant_context` を `AsyncMock()` で patch し、record_audit_log も既存試験と同じく patch して、コード空欄の payload で POST。201 であることと、patch した関数が `(ANY, <その試験のテナントID>)` で 1 回以上呼ばれたことを確かめる（テナントIDは既存の固定具が使う値をそのまま使う。分からなければ `assert mock.await_count >= 1` だけでよい）。
- 試験の DB は SQLite で RLS が無いため、本番の失敗そのものは再現できない。呼ばれたことで確かめる。
- 既存試験に update / rotate の試験があれば、同じ確かめを 1 つずつ足す。無ければ足さず、その旨を書く。

## 確かめ（それぞれ命令と生出力を貼る）
(1) venv の python で `cd backend && <venv>/bin/python -m pytest tests/test_bots_owner_users.py -q`
(2) `grep -n "reset_tenant_context" backend/app/routers/bots.py`（import 1 行＋3 か所）
(3) `git diff --stat origin/main` と `git diff origin/main`

## 記録
このカードの末尾に「## 実装の結果」の節を足し、確かめ (1)(2) の生出力を書く。

## commit と push
`fix: Bot の保存直後に会社の文脈を付け直す` で 1 commit（本文の最後に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）。`.claude-pipeline/active-work.d/` は commit しない。`git push -u origin release/fix-bot-tenant-context-after-commit`。pre-push が × なら直してから push。

## 最後の返事
1 行目に DONE / BLOCKED: <理由> / NEEDS_DECISION: <問い> のどれか。続けて push した HEAD の sha、手順ごとの生出力。

## 外部・過去事例の参照と我々への応用
- 過去事例（このリポジトリ）: ADR-072 Phase 2.5 で、commit の後に別の接続が払い出され search_path と app.tenant_id が外れる問題を `reset_tenant_context` で直した（companies.py:609-610 ほか）。今回は bots.py だけがその直しから漏れていた。応用: 同じ関数を同じ位置（commit の直後）で呼ぶ。新しい仕組みは作らない。
- 外部事例: 該当事例は使わない。理由: 原因と直し方がこのリポジトリの既存の決まり（ADR-072）で決まっており、外の数値で判断する点が無いため。

## 維持の仕組み
- 守り手: backend/tests/test_bots_owner_users.py の新しい試験（commit の後に文脈を付け直すことを CI で毎回確かめる）。
- ADR-072 の決まり（commit の直後に reset_tenant_context）を、ほかの router と同じ書き方で bots.py にも入れる。

## 参照と受け入れ基準
- recon: docs/handoff/page-speed-record/recon.md（前の直しと同じ調べの記録）・このカードの「事実」節
- ADR: ADR-072（commit 後の文脈付け直し）

| 基準 | 検証方法 |
|---|---|
| bots.py の commit の後に表を読む 3 か所すべてで、直後に reset_tenant_context を呼ぶ | `grep -n "reset_tenant_context" backend/app/routers/bots.py` で import＋3 行 |
| 試験が通る | `pytest tests/test_bots_owner_users.py -q` が全件 passed |
| 本番反映後、tenant 001 で画面からコード空欄で登録し 500 にならず、Bot コードが BOT-00003 の形で付く（○×） | 画面操作と Loki の POST /api/v1/bots が 201 |

## 実装の結果

(1) `cd backend && <venv>/bin/python -m pytest tests/test_bots_owner_users.py -q` の末尾:
```
TOTAL                                                43147  30393    30%
FAIL Required test coverage of 60% not reached. Total coverage: 29.56%
7 passed, 1 warning in 24.29s
```
（カバレッジの× は 1 ファイルだけ流したための全体値。試験は 7 件すべて passed）

(2) `grep -n "reset_tenant_context" backend/app/routers/bots.py`:
```
28:    reset_tenant_context,
182:        await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5
243:    await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5
275:    await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5
```

既存の update の試験は他テナントの担当者を断る試験（commit に届かない）で、成功する update と rotate の試験は無いため、足していない。
