# ADR-1070: 接続を貸し出しに戻すたびに会社の文脈を消す（Bx）

| 項目 | 内容 |
|------|------|
| ステータス | Proposed（便2 の本番確認の後に決定済みへ進める） |
| 備考 | PO 2026-11-07「1」（S1 段階⑤の前に、接続の返却時に文脈を消す仕組みを先に作って本番に出す選択への答え）。設計の判断は委任（opus-delegation）に基づき Opus が行う |
| 起案日 | 2026-11-07 |
| 方針の決定者 | Shingo（PO） |
| 関連 | ADR-131（get_db の finally で文脈を戻す）、ADR-072（会社ごとのスキーマと commit 後の reset_tenant_context）、ADR-065（準備済み文のキャッシュ）、ADR-1067（S1 段階④）、ADR-135・ADR-136（危険 PR） |
| 設計・根拠 | [design-pool-reset.md](../handoff/s1-rls-stage5/design-pool-reset.md)、[recon-pool-reset.md](../handoff/s1-rls-stage5/recon-pool-reset.md)、[recon-pool-reset-m9.md](../handoff/s1-rls-stage5/recon-pool-reset-m9.md)、[xtenant-evidence.md](../handoff/s1-rls-stage5/xtenant-evidence.md) |

---

## What（何を決めたか）

1. backend/app/database.py の async `engine`（postgresql のとき）だけに、`pool_reset_on_return=None` と pool の `reset` イベントのハンドラを付ける。ハンドラは rollback → `RESET ALL` → commit の順に流し、捨てる接続（`reset_state.terminate_only`）には何もしない。
2. `admin_engine` と、作業台本・Celery の同期 engine には付けない。
3. 2 便に分ける。便1 は、commit・rollback の後に文脈を張り直していない 7 か所（設計 §4-1）に `reset_tenant_context(db, tenant_id)` を足すだけ。便2 は Bx だけ。便1 を本番で測ってから便2 を出す。

## Why（なぜ）

- commit の後に流した `SET` は自動で始まった取引の中にあり、session の close の rollback で取り消される。そのため get_db の finally の `clear_tenant_context`（dependencies.py:386-405）は commit の後には効かず、会社の番号・運営者の印・探す場所が接続に残る（recon m1: 返却後も `is_operator='true'`）。pool が 2 本以上だと、別の要求が前の要求の会社の文脈を見た（recon m7: 20 回中 20 回）。
- SQLAlchemy 公式の PostgreSQL の例は「RESET ALL の後に rollback」。この順だと RESET ALL 自体が rollback で取り消される（recon m1 の A）。rollback を先にし、最後に commit で確定させる形（Bx）だけが、返した接続を idle・文脈空にした（recon m1・m2・m7）。
- `DISCARD ALL` は準備済み文も消す（ADR-065 と衝突）。backend/app は一時表・サーバー側カーソルを使っていない（設計 §2）ので `RESET ALL` だけで足りる。
- 速さ: 1 回の貸し借りで中央値 +0.44ms（recon m5）。
- Bx の後は、文脈を張り忘れたコードは「前の値で偶然動く」でなく 0 行・例外になる（漏れない側に倒れる）。その箇所を全部数え（m9）、Bx で新たに壊れる 7 か所は便1 で先に直す。Bx の前から動いていない既存の不具合（Discord の配信失敗通知・ロール同期の記録など）は退行ではないので混ぜない（設計 §4-3）。

## 戻し方

- 便ごとに、その便の PR を revert して配備する。DB の変更は無い。

## 測り方

- 設計 §6 の K1〜K6（health の応答、本番ログのエラー件数、Celery の既存エラーの件数、借りた直後の文脈が空の試験、`idle in transaction` の残り 0、会社1 の画面確認）。基準値は 2026-11-07 実測。

## 触らない範囲

- admin_engine・同期 engine の返却処理。
- 設計 §4-3 の既存不具合 6 件、Celery の既存の `Exception closing connection`（設計 §7 R4）。
- scripts/lint_tenant_schema.py の Rule C の範囲を広げること（後続の候補）。
