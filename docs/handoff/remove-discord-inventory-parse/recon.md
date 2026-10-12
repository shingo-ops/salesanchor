# recon: Discord 在庫取り込み機能の削除

- 日付: 2026-10-02
- PO承認: 2026-10-02「ｙ」（コード + UI 先行削除。DB テーブルは本PRでは DROP しない）
- 対象ブランチ: `release/remove-discord-inventory-parse`（`origin/main` 55d99a97e から分岐）

## 1. ADR 検索（着手前必須）

`git grep -i "discord.*in[bv]entory\|parse_review\|inbound_writer" docs/adr/` および
`docs/adr/FEATURE-INDEX.md` を検索した。

- `ADR-146` は `backend/app/discord_gateway/client.py:1,9-12`（旧コメント）でのみ言及されており、
  **`docs/adr/` 配下に ADR-146 のドキュメントファイルは存在しない**（`ls docs/adr/ | grep -i 146` 0件）。
  つまり ADR-146「案ア」は実装コメントのみで、承認済み ADR 文書としては存在しない。
- `ADR-093 Phase 3b`（offer_type/ship_timing 判定）は実装コメントに複数箇所存在するが、
  同様に `docs/adr/` に ADR-093 の独立ファイルは見当たらない（ADR番号はコメント上の管理番号のみ）。
- `ADR SA-06`（解析精度サマリー `v_supplier_parse_stats`）もコメント上の管理番号のみ。

## 2. 対象機能の構造（origin/main 55d99a97e 時点）

### 2.1 Discord Bot Gateway

- `backend/app/discord_gateway/client.py:283-295` `on_message` は guild メッセージのみ
  `_process_guild_message` → `ticket_channel_writer.process_ticket_channel_message` に委譲。
  DM は `message.guild is None` で早期 return（B方式対象外、F7/PO決定）。
- 旧 `_process_dm_message` / `_process_message` / `_resume_missed_messages`
  （client.py:327-337、削除前）は **いずれも `on_message`/`on_resumed` から呼ばれていない**
  休眠スタブ（本文 `logger.debug` のみ）。呼び出し元ゼロを `git grep` で確認済み。

### 2.2 inventory_parser.py / inventory_parser_llm.py

- backend/app/services/inventory_parser.py（1244行、削除前）: ルールベース在庫メッセージ解析
  (`parse_raw_content` / `parse_inventory_message`)。呼び出し元は
  backend/app/discord_gateway/inbound_writer.py:427 のみ（他は docstring コメント or
  削除対象テスト）。
- backend/app/services/inventory_parser_llm.py（399行、削除前）: Gemini フォールバック解析。
  呼び出し元は inventory_parser.py 内部のみ（遅延 import）。
- 例外として `_extract_offer_type_ship_timing`
  (inventory_parser.py:518-541、旧) は
  `backend/app/services/extraction_judgement_svc.py:18` が import しており、
  **TCG 抽出パイプライン（Gemini書き写し/判定分離、KEEP対象）が依存する共有ロジック**。
  → `backend/app/services/offer_type_ship_timing.py` へ移設（public 名
  `extract_offer_type_ship_timing`）。移設先に禁止語彙
  (shrink_yes/shrink_no/state_a_minus/state_a/state_b/damaged) が無いことを
  `grep -iE` で確認済み（マッチ0件）。
- `LLMConfigError` / `LLMParseError`
  (inventory_parser_llm.py:48-56、旧) は
  `backend/app/routers/leads.py:1253`、`backend/app/routers/translation.py:32`、
  `backend/app/services/message_translator.py:28`、`backend/app/tasks/translation.py:16`
  の **4箇所から import されており、翻訳機能（KEEP対象）が共有**。
  → `backend/app/services/llm_errors.py` へ移設。

### 2.3 super_admin_inbound.py / parse_review.py

- backend/app/routers/super_admin_inbound.py（291行、削除前）: Discord 受信メッセージ一覧API。
  `backend/app/main.py` に `super_admin_inbound.router` として登録（旧580-583行）。
  フロントエンド呼び出しは frontend/tests-e2e/super-admin-discord-inbound.spec.ts のみ
  （e2eテスト、削除対象）。
- backend/app/routers/parse_review.py（372行、削除前）: 解析結果レビュー承認/却下API。
  `backend/app/main.py` に `parse_review.router` として登録（旧584-587行）。
  `apply_inbound_items`（inventory_movements.py:181、旧）を呼ぶ唯一の呼び出し元
  （parse_review.py:199）。

### 2.4 【訂正1】inventory_movements.py は apply_inbound_items を含めて feature-only だった

当初 recon facts は「KEEP: inventory_movements and its writers if shared」としたが、
実際に `git grep -n "apply_inbound_items" -- backend frontend scripts` で確認した結果、
本番コードからの呼び出し元は **parse_review.py:199 の1箇所のみ**だった
（他の出現は docstring コメント、または `apply_inbound_items` を直接呼ぶ
削除対象テストのみ）。

さらに inventory_movements.py 内の他シンボルの使用範囲を全て確認:

| symbol | 他ファイルからの使用 |
|---|---|
| `_upsert_inventory_offer` | なし（`apply_inbound_items` 内部からのみ呼ばれる private helper） |
| `MovementResult` | なし |
| `ApplyResult` | なし（テストの docstring コメントのみ） |
| `InventoryApplyError` | parse_review.py（削除済み）、かつ `verify_invariant_for_product` 内部（KEEP） |
| `_CENTRAL_TENANT_SENTINEL` | なし |
| `_OFFER_EXPIRY_HOURS` | なし |
| `verify_invariant_for_product` | 本番コードからの呼び出し元なし（独立した不変条件検証ヘルパ、将来のテスト/運用確認用として維持） |

→ PO/Designer 判断（2026-10-02、「在庫取り込みだけで使っているものは削除、他の用途は残す」ルール適用）:
`apply_inbound_items` と、それだけに使われていた
`_upsert_inventory_offer` / `MovementResult` / `ApplyResult` /
`_CENTRAL_TENANT_SENTINEL` / `_OFFER_EXPIRY_HOURS` を削除。
`InventoryApplyError` と `verify_invariant_for_product`（`public.inventory_movements`
テーブル自体の不変条件検証、Discord機能と無関係に独立して有用）は維持。
結果、inventory_movements.py は 441行 → 55行。

### 2.5 【訂正2】inventory_movements_invariant / inventory_upsert_on_approve テストの扱い

UNSURE指定だった test_inventory_movements_invariant.py と
test_inventory_upsert_on_approve.py は `apply_inbound_items` を直接 import せず、
削除対象 test_parse_review_approve.py:190 の `_client_with_overrides` ヘルパーを import し、
`POST /api/v1/super-admin/parse-review/{inbound_id}/approve`（parse_review ルーター、削除対象）
を実際に叩いて検証していた。PO/Designer 決定（オプションA）: 両ファイルとも削除。
`apply_inbound_items` を直接呼ぶ不変条件/UPSERT テストは
test_f11_inventory_upsert.py・test_phase_a_apply_inbound_items.py
（いずれも `apply_inbound_items` のみをテストしており全文削除）に残っていたが、
`apply_inbound_items` 自体の削除に伴い、これら2ファイルも全文削除。

### 2.6 【訂正3】inventory_aggregation.py は SHARED と判明、REMOVE対象から除外

当初 recon facts は `backend/app/services/inventory_aggregation.py` を REMOVE 対象としたが、
実際には `backend/app/services/inventory_aggregated_service.py:12` が
`AggregationResult` / `aggregate_inventory_offers` / `load_aggregation_rules` を import し、
`backend/app/routers/inventory_aggregated.py:26` の `get_aggregated_inventory`
（テナント向け `GET /inventory/aggregated`、`backend/app/main.py:59,605` でルーター登録）
から使われている**本番稼働中の共有コード**だった。
inventory_aggregation.py:389 は `public.inventory_aggregation_rules` テーブルを
参照している。Discord 在庫取り込みとは無関係のため、本PRでは
**inventory_aggregation.py / test_inventory_aggregation.py /
test_inventory_aggregated.py / `backend/tests/fixtures/inventory_aggregation/` /
`inventory_aggregation_rules` テーブルを KEEP（REMOVE対象から除外）**。
`backend/app/services/inventory_drift_detector.py` も同様に対象範囲外（Discord 機能への
帰属が未証明）として KEEP。

### 2.7 PO決定1: super_admin_suppliers.py の parse-stats エンドポイント削除

`GET /super-admin/suppliers/{id}/parse-stats`（`super_admin_suppliers.py:617-668`、旧）の
フロントエンド呼び出しを `git grep -n "parse-stats" -- frontend/src` で確認した結果、
**0件**（frontend/src/locales/{ja,en}.json の表示文字列 `"parseStats"` のみで、
実際に fetch する React コードは存在しない）。ゼロ呼び出し元を確認した上で削除。
参照していた `public.v_supplier_parse_stats` ビューは inventory_drift_detector.py
（KEEP対象）も参照しているため、ビュー自体は本PRで変更しない。

### 2.8 PO決定2: NeedsReviewTabsPanel.tsx のナビゲーション除去

`frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx:465`（旧）の
`navigate(`/super-admin/inbound/${item.source_message_id}/review`)` を検証:

- `item.source_message_id` は `backend/app/services/tcg_analysis_review_svc.py:38,200`
  の `ej.source_message_id::text`（TCG 抽出パイプラインの `source_messages.id`）。
- 遷移先 parse_review.py（旧）の `inbound_id: int`（`parse_review.py:112,146,288`）は
  `public.discord_inbound_messages.id` を指す、**全く別のID空間**。
- つまりこの画面遷移は TCG 抽出パイプラインの `source_message_id` を Discord 在庫取り込みの
  `inbound_id` として渡していた**既に型不整合だった（実質的に機能していなかった可能性が高い）**
  リンクだった。削除は安全。
- `navigate`/`useNavigate` はファイル内で他に使用箇所なし（削除後に未使用 import は残さない）。

## 3. 本番データ件数（2026-10-02 時点、PO報告値）

- `discord_inbound_messages`: 129件（最新 2026-06-25）
- `discord_webhook_idempotency`: 111件
- `parse_logs`: 0件
- `inventory_aggregation_rules`: 4件（※ KEEP 対象テーブル、本PRでは変更なし）

これらのテーブルは本PRでは DROP しない（別PRでPOのGOを得て実施）。

## 4. grep 証跡（最終コミット後）

`git grep -n -e inventory_parser -e inbound_writer -e parse_review -e super_admin_inbound
-e inventory_aggregation -e inventory_drift_detector -e ParseReviewPage -e apply_inbound_items
-- backend/app frontend/src scripts` の残存一覧と理由は `design.md §5` に記載。
