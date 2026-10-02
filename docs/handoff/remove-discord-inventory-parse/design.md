# design: Discord 在庫取り込み機能の削除

- 日付: 2026-10-02
- 関連 recon: `docs/handoff/remove-discord-inventory-parse/recon.md`
- 関連 ADR: `docs/adr/ADR-1004-llm-usage-ledger.md`（`purpose='inventory_parse_fallback'`
  の扱い）、`docs/adr/ADR-135-release-stowaway-prevention.md`
  （1リリース1テーマ・危険パス確認）、`docs/adr/ADR-110-sa-translation-subsystem.md`
  （message_translator.py / `LLMConfigError`/`LLMParseError` の移設先が翻訳サブシステムと
  整合すること）

## 1. 決定

PO（しんごさん）2026-10-02「ｙ」により、休眠中の Discord 在庫取り込み機能（コード + UI）を
削除する。DB テーブルは本PRでは DROP しない（別PR・別GOで実施）。
作業中に判明した recon facts の誤り（inventory_aggregation.py は共有コードだった）は
Designer が2026-10-02に独立検証し、REMOVE対象から除外する決定を下した。同様に
`apply_inbound_items`（inventory_movements.py）は「在庫取り込みだけで使っているものは
削除、他の用途は残す」という PO ルールの適用対象と判断し、追加で削除範囲に含めた。

## 2. 削除したもの（REMOVE）

### バックエンド

- backend/app/discord_gateway/inbound_writer.py（516行、全削除）
- backend/app/services/inventory_parser.py（1244行、全削除。
  `_extract_offer_type_ship_timing` のみ offer_type_ship_timing.py へ移設）
- backend/app/services/inventory_parser_llm.py（399行、全削除。
  `LLMConfigError`/`LLMParseError` のみ llm_errors.py へ移設）
- backend/app/routers/super_admin_inbound.py（291行、全削除）
- backend/app/routers/parse_review.py（372行、全削除）
- `backend/app/main.py`: 上記2ルーターの import・`app.include_router` 登録を削除
- `backend/app/discord_gateway/client.py`: 休眠スタブ `_process_dm_message` /
  `_process_message` / `_resume_missed_messages`（いずれも呼び出し元ゼロ、`logger.debug`
  のみの no-op）を削除。`on_resumed` の docstring/ログ文言から削除済み概念への言及を除去
- `backend/app/services/inventory_movements.py`: `apply_inbound_items`・
  `_upsert_inventory_offer`・`MovementResult`・`ApplyResult`・
  `_CENTRAL_TENANT_SENTINEL`・`_OFFER_EXPIRY_HOURS` を削除（唯一の呼び出し元
  parse_review.py が削除されたため到達不能になっていた）。
  `InventoryApplyError`・`verify_invariant_for_product` は維持（441行 → 55行）
- `backend/app/routers/super_admin_suppliers.py`: `GET
  /super-admin/suppliers/{id}/parse-stats`・`SupplierParseStatRow` を削除
  （PO決定1、フロントエンド呼び出しゼロを確認済み）

### フロントエンド

- frontend/src/pages/super-admin/ParseReviewPage.tsx（917行）・
  `ParseReviewPage.css`（140行）
- `frontend/src/App.tsx`: import と `/super-admin/inbound/:id/review` ルートを削除
- `frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx`: 行クリックで
  `parse_review` 画面に遷移する `onRowClick` と、未使用になった `useNavigate`/`navigate`
  を削除（PO決定2。遷移元の ID と遷移先が期待する ID 空間が元々不一致だったことを recon で確認）
- `frontend/src/locales/ja.json` / en.json:
  `superAdmin.tabs.parseStats`・`superAdmin.parseReview.*`・`supplier.parseStats`
  （トップレベル `supplier` キー自体が `parseStats` のみだったため丸ごと削除）を両言語で削除

### テスト

全文削除（feature-only、`apply_inbound_items`/削除モジュールのみをテスト）:

- backend/tests/test_discord_bot_receiver.py
- backend/tests/test_inventory_parser_bench.py
- backend/tests/test_inventory_parser_llm.py
- backend/tests/test_inventory_parser_llm_real_api.py
- backend/tests/test_inventory_parser_real_samples.py
- backend/tests/test_inventory_parser_rule.py（offer_type_ship_timing のテストのみ
  test_offer_type_ship_timing.py へ移設）
- backend/tests/test_parse_review_approve.py
- backend/tests/test_parse_review_concurrency.py
- backend/tests/test_parse_review_rbac.py
- backend/tests/test_parse_review_reject.py
- backend/tests/test_super_admin_inbound_api.py
- backend/tests/test_f11_inventory_upsert.py（`apply_inbound_items` 直接呼び出しのみ、
  追加削除分）
- backend/tests/test_phase_a_apply_inbound_items.py（同上、追加削除分）
- backend/tests/test_inventory_movements_invariant.py（`apply_inbound_items` を
  削除済み `parse_review` HTTP エンドポイント経由で検証していたため削除、追加削除分）
- backend/tests/test_inventory_upsert_on_approve.py（同上、追加削除分）
- `backend/tests/fixtures/inventory_parser_samples/`（6ファイル）
- frontend/tests-e2e/super-admin-discord-inbound.spec.ts
- frontend/tests-e2e/super-admin-parse-review.spec.ts
- frontend/tests-e2e/parse-review-phase-a-warning.spec.ts
- frontend/tests-e2e/f11-ac11-3-parse-review-inventory-fields.spec.ts

UNSURE 判定結果（per-file）:

| ファイル | 判定 | 理由 |
|---|---|---|
| `backend/tests/test_inventory_sprint1_migrations.py` | 無変更で KEEP | `apply_inbound_items` を一切参照せず、migration/テーブル構造（`public_tables_exist`・`supplier_aliases_unique_constraint`・`discord_idempotency_structure`・`inventory_visibility_permissions`・`inventory_movements_arithmetic_trigger`・`knowledge_rules_pattern_type_check`）のみを検証 |
| backend/tests/test_f11_inventory_upsert.py | 全文削除 | 7関数全てが `apply_inbound_items` を直接 import・呼び出し |
| backend/tests/test_phase_a_apply_inbound_items.py | 全文削除 | 2関数とも `apply_inbound_items` を直接呼び出し |
| backend/tests/test_inventory_movements_invariant.py | 全文削除 | `apply_inbound_items` を直接ではなく、削除対象 test_parse_review_approve.py の `_client_with_overrides` 経由で `parse_review` HTTP エンドポイントを叩いていた |
| backend/tests/test_inventory_upsert_on_approve.py | 全文削除 | 同上 |

### CI スクリプト

- `scripts/check-condition-vocab.js`: `CODE_FILES` を空配列化（旧3ファイルが全て削除されたため）。
  `checkCodeFile()` は `existsSync` ガード＋空配列ループで no-op になりクラッシュしないことを
  ローカル実行で確認済み（`BASE_SHA=origin/main HEAD_SHA=HEAD node
  scripts/check-condition-vocab.js` → `✅ condition vocab gate PASSED`）。`JSON_FILES`
  のロケールチェックは変更なし
- `scripts/check_test_schema_dup.py`: `EXCLUDE_FILES` から削除済み
  test_inventory_parser_real_samples.py のエントリを除去

## 3. 維持したもの（KEEP、recon facts からの訂正）

- `backend/app/services/inventory_aggregation.py` / test_inventory_aggregation.py /
  test_inventory_aggregated.py / `backend/tests/fixtures/inventory_aggregation/`：
  テナント向け `GET /inventory/aggregated`（`inventory_aggregated_service.py` 経由）の
  共有コアロジック。Discord 機能とは無関係
- `inventory_aggregation_rules` テーブル：上記の参照先。DROP 対象として言及しない
- `backend/app/services/inventory_drift_detector.py`：Discord 機能への帰属が未証明のため
  対象範囲外（KEEP）
- `backend/app/services/phase_gate.py`：super_admin_phase_switch.py・tenant.py から
  今も使われる Phase 判定サービス。`apply_inbound_items` 削除後も他の呼び出し元が残るため
  KEEP（docstring の呼出元リストのみ更新）
- `public.v_supplier_parse_stats` ビュー：inventory_drift_detector.py が参照するため維持
  （super_admin_suppliers.py 側の endpoint のみ削除）

## 4. 基準・検証方法

| 基準 | 検証方法 |
|---|---|
| 削除対象モジュールの import 元が全て REMOVE 対象 or 削除テストのみであること | `git grep -n "<symbol>" -- backend frontend scripts` を削除前に実行し、REMOVE 対象外からの import が無いことを確認（2回 STOP して Designer に報告・承認を得た経緯あり） |
| 移設した `extract_offer_type_ship_timing` にレガシー語彙が無いこと | `grep -iE "shrink_yes\|shrink_no\|state_a_minus\|state_a\|state_b\|damaged"` が0件 |
| `app.main` の起動が壊れていないこと | `cd backend && python3 -c "import app.main"`（無出力 = 成功） |
| 関連バックエンドテストが通ること | `pytest -q --no-cov` で offer_type_ship_timing（40 passed）、extraction_judgement/message_translator/translation 系（155 passed）、discord_inbox/ticket_channel/reaction_writer/super_admin_suppliers/inventory_sprint1_migrations（20 passed, 15 skipped=DB未接続分） |
| ruff / lint が通ること | `python3 -m ruff check .`（tcg_migration の既存1件のみ、本PR起因ではない） |
| フロントエンドの型・lint・i18n整合性が崩れていないこと | `npx tsc --noEmit`（無出力）、`npx eslint --max-warnings=0 src/App.tsx src/pages/super-admin/components/NeedsReviewTabsPanel.tsx`（無出力）、`npm run check:i18n-missing-keys`（PASSED） |
| `NeedsReviewTabsPanel` の既存振る舞いが壊れていないこと | `npx vitest run src/pages/super-admin/components/NeedsReviewTabsPanel.test.tsx`（4 passed） |
| `check-condition-vocab.js` がクラッシュしないこと | `BASE_SHA=origin/main HEAD_SHA=HEAD node scripts/check-condition-vocab.js`（PASSED） |

## 5. grep 証跡（最終）と残存理由

```
backend/app/discord_gateway/dm_writer.py:4: docstring内の歴史的対比コメント（inbound_writerとは独立の経路、という説明。dm_writerはKEEP対象の別機能）
backend/app/routers/inventory_offers.py:10: 本PRで更新した削除経緯コメント（意図的）
backend/app/schemas/central_masters.py:27: knowledge_rules のパターン種別を説明する一般的コメント。カテゴリは gemini_extraction_svc.py / tcg_extraction.py（KEEP対象）が今も消費しており機能的な問題なし（コメントの字面のみ古い）
backend/app/services/inventory_aggregated_service.py:12: KEEP対象（§3参照）
backend/app/services/inventory_aggregation.py:389: KEEP対象（§3参照）
backend/app/services/inventory_movements.py:3,5: 本PRで追加した削除経緯の docstring（意図的）
backend/app/services/phase_gate.py:30: 本PRで更新した旧呼出元の記録コメント（意図的）
frontend/src/components/InventoryPicker.tsx:8: 歴史的コメント（用途説明にParseReviewPageの名前が残るが、コンポーネント自体はPurchaseOrdersFormModalで現役使用中）
frontend/src/components/InventorySearchBar.tsx:6: 同上
frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:43: central_masters.py と同種の一般的コメント
scripts/check-condition-vocab.js:12-13: 本PRで追加した削除経緯コメント（意図的）
scripts/migrate_inventory_sprint5_to_7.py:22: 過去の一時移行スクリプトのdocstring（履歴記録、実行コードではない）
scripts/run_all_migrations.sh:182: inventory_aggregation_rules（KEEP対象テーブル）のmigrationファイルを実行する行
```

いずれも機能的な依存（import/呼び出し）ではなく、コメント・KEEP対象コードのみ。

## 6. 影響範囲（呼び出し元の全走査結果）

- `LLMConfigError`/`LLMParseError`: leads.py / translation.py（router）/
  message_translator.py / translation.py（task）の4箇所を `llm_errors` import に変更済み、
  全て ruff/pytest で確認
- `extract_offer_type_ship_timing`: extraction_judgement_svc.py の1箇所のみ、import 文を
  `offer_type_ship_timing` に変更済み
- `apply_inbound_items` 削除の影響: 本番呼び出し元は parse_review.py（削除済み）のみだった
  ため影響範囲ゼロ。テスト4ファイルを削除
- main.py のルーター登録削除: 他のルーター登録順・`Depends` 構成に変更なし（import smoke で確認）

## 7. 弊害・リスク

- 本PRでは DB テーブル・ビュー（`discord_inbound_messages`・`discord_webhook_idempotency`・
  `parse_logs`・`inventory_movements`・`v_supplier_parse_stats` 等）は一切変更しない。
  コード削除後もテーブルは残存するため、別PRでDROPする際は改めてPOのGOが必要（ADR-135準拠）
- `apply_inbound_items` 削除後、`public.inventory_movements` への新規 INSERT 経路は
  本リポジトリ内に存在しなくなる（過去データの不変条件検証 `verify_invariant_for_product`
  のみ残る）。将来「在庫移行プロジェクト」で同テーブルへの書き込みを再設計する場合は
  本PRの削除内容を前提にゼロから実装する必要がある

## 8. 外部・過去事例

該当なし。本PRは機能の新規実装ではなく、スコープが確定した既存休眠コードの削除（PO承認済み）
であり、外部事例や過去の類似導入事例を参照する判断余地が無いため調査を実施していない。

## 9. 維持の仕組み（継続性）

- 削除範囲の正本はこの design.md と recon.md。復元が必要になった場合は本PRのコミット
  （削除前の内容）を `git log` から参照する
- offer_type_ship_timing.py / llm_errors.py は独立モジュール化したことで、今後
  Discord機能を再設計する際も TCG抽出パイプライン・翻訳機能のロジックに影響を与えずに
  変更できる
- 守り手: `backend/app/services/extraction_judgement_svc.py`（offer_type_ship_timing の
  利用者）, `backend/app/services/message_translator.py`（llm_errors の利用者）,
  `backend/app/routers/leads.py`, `backend/app/routers/translation.py`,
  `backend/app/tasks/translation.py`
