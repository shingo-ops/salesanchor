# ADR-1067: 会社の列を持つ public の 8 表に RLS を付ける（段階④）

| 項目 | 内容 |
|------|------|
| ステータス | Proposed（KGI-4〜6 と 5 便の順番を PO が決めるのを待つ） |
| 備考 | PO 2026-11-06「1」（問い「8 件すべてに守りを足す設計をする【おすすめ】：在庫の動きから順に、入口を1件ずつ調べて設計します。」への答え）。本 ADR は草案。PO 承認の後に Accepted へ進める |
| 起案日 | 2026-11-06 |
| 方針の決定者 | Shingo（PO） |
| 関連 | ADR-1018（public の RLS 段階①〜③・本 ADR はその続き）、ADR-1063（便5: RLS の無い会社ごとの表を CI で止める）、ADR-145（FORCE RLS の手本）、ADR-072（会社ごとのスキーマ）、ADR-131（接続ごとの文脈リセット）、ADR-136・ADR-1003（危険 PR の GO と委任） |
| 設計・根拠 | [design.md](../handoff/s1-rls-stage4/design.md)、[recon.md](../handoff/s1-rls-stage4/recon.md)、KGI [kgi.md](../specs/tenant-rls/kgi.md) KGI-4〜6 |

---

## What（何を決めたか）

1. 次の 8 表に RLS を付ける（ENABLE と FORCE、ポリシー 4 本）。
2. 型A（自社の行だけ読み書き。運営は読むだけ可）: `inventory_movements`・`discord_server_snapshots`・`discord_server_apply_runs`。
   - 読取: `tenant_id = 自社` または運営の文脈。
   - 作成・変更・削除: `tenant_id = 自社` のときだけ。
3. 型C（読取は全行可。作成・変更・削除は自社か運営の文脈のときだけ）: `tenant_discord_config`・`tenant_discord_ticket_config`・`google_webhook_subscriptions`・`tenant_llm_budgets`・`tenant_settings`。ADR-1018 段階③の案 C と同じ考え方。
4. 運営画面の 2 つの書込（AI の予算の保存、会社の段階の切替）は、書く直前に運営の文脈を張り、終わりに必ず外す。翻訳の見張りの通知時刻の書込（translation_monitor.py:206、文脈が外れた後に走る）は、書く直前に会社の文脈を張る（recon §7）。
5. 1 便に 1〜2 表ずつ、5 便に分けて出す（④-1 在庫の動き → ④-2 Discord の取込記録 2 表 → ④-3 Discord 設定 2 表 → ④-4 Google 通知 → ④-5 予算・会社設定）。各便で「出す → 本番で確かめる → 次」。
6. ADR-1063 便5 の CI 確かめは、8 表を理由「段階④で RLS を付ける予定（ADR-1067 便④-N）」で許可一覧に入れて始め、便ごとに 1 表ずつ消す。便④-5 の後に許可一覧から 8 表が消える。
7. 1 つの移行の中で ENABLE・FORCE・ポリシー 4 本をまとめ、`BEGIN;`〜`COMMIT;` で囲む。各 `CREATE POLICY` の前に `DROP POLICY IF EXISTS` を置く（移行は毎回すべて流れるため）。会社の比べ方は `NULLIF(current_setting('app.tenant_id', true), '')::INTEGER`（文脈を外した接続は空文字を持つため）。

## Why（なぜ）

- 便5 の確かめ（2026-11-06）で、会社の列を持つのに RLS の無い public の表が 18 見つかった。そのうちこの 8 表は会社ごとの行を持つ。今の守りは各 SQL の `WHERE tenant_id` 1 行だけで、書き忘れが 1 か所あると他社の行に届く。
- 型を 2 つに分けたのは、入口を全部数えた結果（recon §4・§6）。
  - 型A の 3 表は、会社の文脈の外から読む本番の入口が無い。
  - 型C の 5 表は、会社が決まる前に読む入口がある。Discord の受け口（client.py:108-126・:308、discord_role_sync.py:53-80）、Google の通知の受け口（google_webhook.py:212）、全社の点検（discord_own_staff_sync.py:24・google_webhook.py:395）、文脈なしの運営画面（super_admin_llm_budget.py・super_admin_phase_switch.py）。読取まで止めると、これらが黙って 0 行になる。
- 段階②b の教訓: 書込の入口に文脈が無いと、INSERT は 42501 で落ち、UPDATE は静かに 0 行になる。だから書込の入口を全部数えてから出す。運営画面の 2 つの書込には文脈を足す。
- PostgreSQL 16 公式文書「5.8. Row Security Policies」によると、表の持ち主は FORCE を付けないと RLS を通らない。また、ポリシーの無い表は全部拒否になる。だから FORCE を付け、ポリシーと同じ移行で有効にする（design §9）。
- 本番の行数は 8 表で計 17 行（recon §3）。tenant_id が空の行は 0。読取を全行可にしても、今より見える行は増えない。

## 戻し方

- 便ごとに、その便の表だけを戻す。`DROP POLICY IF EXISTS`（4 本）→ `ALTER TABLE … NO FORCE ROW LEVEL SECURITY` → `ALTER TABLE … DISABLE ROW LEVEL SECURITY`。行は消えない（design §7）。
- 運営の文脈を足すコード（便④-5）は、その PR を戻せばよい。

## 測り方

- KGI-4〜6（docs/specs/tenant-rls/kgi.md）。8 表の RLS の状態とポリシー数は、reader 鍵の道で `pg_class`・`pg_policies` を読む（読めることを 2026-11-06 に確認、recon §6 U6）。

## 触らない範囲

- 便5 の残り 10 表（共用の一覧 6、運営の記録 4）は本 ADR の対象外。理由つきで便5 の許可一覧に残す。
- 会社ごとのスキーマ（`tenant_XXX`）の表（ADR-072 の search_path で分離済み）。
