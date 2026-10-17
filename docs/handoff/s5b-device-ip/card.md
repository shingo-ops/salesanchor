# 実装カード — 端末登録も共通の関数で接続元 IP を決める

設計: docs/handoff/s5b-device-ip/design.md（APPROVE）　PO 承認: 2026-10-17「y」　作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-s5b-device-ip（ブランチ release/s5b-device-ip）

## 手順

1. `./scripts/dev/executor-preflight.sh` を実行する。
2. backend/tests/test_line_import_devices.py に T1・T2（design §4）を足す。既存の `client` fixture を使い、`patch.object(svc, 'start', new_callable=AsyncMock)` で service を置き換え、`start.await_args.args[3]` を確かめる。送る本文は `{'token_hash': 'a'*64, 'name': 'Termux'}`。
3. 変更前のコードで T1 が赤、T2 が緑であることを確かめる。生出力は /tmp/CC報告ファイル/device-ip/impl/before.txt に保存する。
4. backend/app/routers/line_import_devices.py を design §2 のとおり変える。import は既存の `from app...` の並びに合わせる。
5. `tests/test_line_import_devices.py` と `tests/test_client_ip*.py`（あれば）を実行し、after.txt に保存する。ruff check と ruff format --check の結果を ruff.txt に、git diff を diff.txt に保存する。
6. コミットメッセージは `fix: 端末登録の接続元を共通の関数で決める（S5 別便）`。末尾に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>` を付ける。そのうえで push する。PR は作らない。

## 触らない

- service
- migrations
- nginx
- tools/
- ほかのルーター
- 既存の試験のアサーション

## 想定される分岐

- TestClient の接続元が `'testclient'` でない場合は、実際の値に合わせて T2 を書く。その値は報告に原文で書く。
- 変更前に T1 が緑になる場合は、止めて報告する。
- ruff format の指摘が触っていない行だけにある場合は、直さずに報告する。
