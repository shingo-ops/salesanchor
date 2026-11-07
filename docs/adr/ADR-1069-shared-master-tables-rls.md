# ADR-1069: 会社の行も足せる public の 6 表と別名の入口 2 つに RLS を効かせる（段階⑤）

| 項目 | 内容 |
|------|------|
| ステータス | Proposed（目標は PO が決めた。備考を参照。便⑤-4 の本番確認の後に決定済みへ進める） |
| 備考 | PO 2026-11-07「ｃ1」（6 表を許可一覧に載せ、次の段で RLS を付ける）。2026-11-07 PO「1」（問い「この目標で承認する【おすすめ】：設計を書き、確かめてから、1〜2表ずつ作って本番に出すところまで進めます。」への答え）で KGI-7〜9 を承認 |
| 起案日 | 2026-11-07 |
| 方針の決定者 | Shingo（PO） |
| 関連 | ADR-1067（段階④・型C の手本）、ADR-1018（段階①〜③）、ADR-1063（便5: RLS の無い会社ごとの表を CI で止める）、ADR-145（FORCE RLS）、ADR-131（接続ごとの文脈リセット）、ADR-136・ADR-1003（危険 PR の GO と委任） |
| 設計・根拠 | [design.md](../handoff/s1-rls-stage5/design.md)、[recon.md](../handoff/s1-rls-stage5/recon.md)、KGI [kgi.md](../specs/tenant-rls/kgi.md) KGI-7〜9 |

---

## What（何を決めたか）

1. 次の 6 表に型C の RLS を付ける（ENABLE と FORCE、ポリシー 4 本。読取は全行可、作成・変更・削除は自社か運営の文脈のときだけ）: `line_conditions`・`line_units`・`tcg_note_master`・`tcg_status_master`・`tcg_product_categories`・`payment_fee_settings`。ポリシーの書き方は ADR-1067 What 7 と同じ。
2. 別名の入口（ビュー）`public.conditions`・`public.units` に `security_invoker = true` を付け、元の表の権限と RLS を「ビューを使う人」に効かせる。ビューを作り直す古い移行 3 本にも同じ設定を書き、デプロイのたびに設定が一時的に消えないようにする。
3. RLS を付ける前の便（⑤-1）でビューの設定だけを先に出す。その後 1 便 2 表ずつ（⑤-2 状態・単位 → ⑤-3 注記・在庫状況 → ⑤-4 商品区分・決済手数料）。各便で「出す → 本番で確かめる → 次」。
4. 運営画面の書込 23 本は、その表に RLS が付く便で運営の文脈に包む。包み方は運営の仕入先画面の既存の仕組み（super_admin_suppliers.py:58）を共通の場所へ移して使う。
5. 行に鍵を掛ける 2 か所（状態の確定、商品詳細の保存）は、鍵の前に取引の中だけ効く運営の文脈（`SET LOCAL app.is_operator = 'true'`）を張る。表ごと鍵を掛ける案は選ばない。
6. CI の確かめ（scripts/check_public_tenant_rls.py）に「指定したビューが読む人の権限で読む設定を持つ」を足す。指定の正本は backend/app/ops/tenant_rls_allowlist.py の 1 か所。許可一覧は便ごとに 2 表ずつ消し、11 → 5 にする。

## Why（なぜ）

- 6 表の今の守りは各 SQL の `WHERE tenant_id` 1 行だけ。会社の画面からの書込で書き忘れが 1 か所あると、共用の行や他社の行を書き換えられる（recon §4-1）。
- 型C にしたのは、解析と会社の画面が共用の行を読むため（recon §4-3）。読取を絞ると解析が止まる。本番の 171 行はすべて共用で、読取を全行可にしても見える行は増えない（recon §2-1）。
- ビューは既定で持ち主（superuser）の権限で元の表を読む。元の表に RLS を付けても、ビュー経由では素通りする（PostgreSQL 16 公式文書「CREATE VIEW」、recon §3）。`CREATE OR REPLACE VIEW` は設定を置き換えるため、古い移行も直さないとデプロイのたびに数秒の穴ができる。
- 段階②b の教訓: 書込の入口に文脈が無いと INSERT は 42501、UPDATE・DELETE は静かに 0 行になる。だから運営画面の書込 23 本を全部数えて包む（recon §4-2）。
- `SELECT … FOR SHARE` は RLS で黙って 0 行の鍵になる（PostgreSQL 16 公式文書「CREATE POLICY」）。鍵を掛ける全 41 か所のうち 6 表に触る 2 か所を直す（recon §5）。表ごとの鍵は新しい行の追加まで待たせ、待ちの組み合わせが変わるので選ばなかった。

## 戻し方

- ADR-1067 の戻し方と同じ順と道（戻しの PR と GO → 走っているデプロイ 0 件 → 無制限鍵で戻しの SQL → 確かめ → 戻しの PR を入れる → デプロイ → もう一度確かめ）。
- ⑤-2〜⑤-4: その便の表のポリシー 4 本を消し、NO FORCE・DISABLE。行は消えない。
- ⑤-1: `ALTER VIEW … RESET (security_invoker)`。⑤-2〜⑤-4 をすべて戻した後だけ戻す（先に戻すとビュー経由の書込が RLS を素通りする）。

## 測り方

- KGI-7〜9（docs/specs/tenant-rls/kgi.md）。RLS の状態・ポリシー数・ビューの設定・行数は reader 鍵の道で読む。受入条件の表は design §5。

## 触らない範囲

- 別名の表（`line_condition_aliases`・`line_unit_aliases`）とそのビュー。
- 許可一覧に残る 5 表（`meta_page_routing`・`llm_usage_events`・`data_deletion_logs`・`tenant_deletion_audit`・`products_category_classification_backup`）。
- 会社ごとのスキーマ（`tenant_XXX`）の表、画面（frontend）、読取の絞り込み。
