# recon: 要確認を CSV で直してアプリに戻す

- 基準: origin/main `b05cdd4e595108b0b4f35e3e66917e9970f4fd16`（2026-10-13）。調査は Sonnet（読み取りのみ）、確認は Opus。生出力はリポジトリ外の記録に置く（~/CC報告ファイル-keep/review-sheet-20261012/writeback-recon-facts.md・writeback-auth-facts.md）。
- PO の決定（2026-10-13）：戻す方法は CSV（「CSV（おすすめ）：既存の安全な仕組みを使い回します」を選択）。

## 1. ADR の検索
- `docs/adr/ADR-154-tcg-parity02-gas-python-migration.md:70`：配信は needs_review=false の行に限る。
- `docs/adr/ADR-027-ui-internationalization.md`：UI 文字列は t()。ja/en は同じ鍵。
- ADR-144（`docs/CC_UI_GOVERNANCE.md`）：UI は金型を使う。生の select・input・自作のタブ・色の直値は禁止。
- 要確認を CSV で直すことを決めた ADR は無い（grep の範囲）。

## 2. 人が要確認を直す既存の経路（すべて require_super_admin＝Firebase ID トークン＋MFA）
- 認証：`backend/app/auth/dependencies.py:72-191`（get_current_user・Firebase verify_id_token :144・MFA 必須 :153-160）、`backend/app/auth/dependencies.py:443-471`（require_super_admin）。
- 商品の訂正：`backend/app/routers/item_corrections.py:127-169`。v102 の件は products.is_active を検査し（invalid_product_values）、save_corrections が item_corrections に1行を追記する。product_id なら analysis_results を pid_basis='MANUAL' で更新し、v102 の件なら enqueue_v102_reanalyze を積む。
- 「このままで良い」：`backend/app/routers/item_corrections.py:177-206`。検査は non_ackable_codes・未登録コード・v102 か・source_message_id の一致。保存は `backend/app/services/v102_human_decisions_svc.py:243-258` の save_review_ack。
- corrected_by は current_user.email（TEXT・FK なし）。本番の item_corrections は 862 行で、v102 系の field_name は 0 行。
- 再解析は enqueue_v102_reanalyze（`backend/app/tasks/tcg_extraction.py:743`）。その後の配信の予約は schedule_distribution（:697）。

## 3. CSV の前例（同じ形を使い回す）
- 商品マスタの CSV：`backend/app/routers/tcg_product_import.py`（GET export・POST import/preview は検査のみ・POST import/commit は confirmed_digest の不一致で 409）。上限は 2 MiB・.csv・UTF-8。行の版（revision＝SHA256）と、数式注入の対策は `backend/app/services/tcg_product_roundtrip_svc.py:44-53, :96-98`。
- 画面：`frontend/src/features/tcg-product-import/TcgProductImportPanel.tsx`・`TcgProductImportPreview.tsx`。金型は TextField・ContentToolbar・Button・HeaderButton・DataTable。画面側でも 2MiB・.csv・空ファイルを事前に検査している。

## 4. 要確認の一覧（出力の正本）
- `backend/app/services/tcg_analysis_review_svc.py` の fetch_analysis_results（status_tab=NEEDS_REVIEW）。シートへの出力は `backend/app/services/tcg_review_sheet_svc.py` の 13 列（2026-10-12 本番反映 #4172）。

## 5. 商品の番号
- public.products の有効な商品は 1,363 行。product_code は 1,351 行に値があり、一意（uq_public_products_code）。値の無い 12 行は、番号では選べない。

## 6. 確認する人
- is_super_admin は2人（treasureislandjp.com と jarvis-test.local）。

## 7. 未確認
- product_code の値の無い 12 行の内訳。
