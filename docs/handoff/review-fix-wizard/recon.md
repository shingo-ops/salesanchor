<!-- recon: 要確認スライドの「直す」欄を質問形式（ウィザード）にする調査。事実のみ。推測は「未確認」に分離 -->
# recon — 要確認スライド「直す」欄のウィザード化

**仕事名**: review-fix-wizard  
**日付**: 2026-10-14  
**対象ADR**: 該当ADRなし（`docs/adr` を `ProductMasterDrawer|review-ack|ReviewItemDrawer|要確認` で grep。ヒットは `docs/adr/ADR-057-lp-premium-restyle.md` のみで無関係。UIは ADR-027 / ADR-144 の規約に従う）  
**担当**: 調査担当（サブエージェント）

---

## 1. 現状の「直す」欄

| 引用先 | 確認内容 |
|---|---|
| `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx:78-118` | 「直す」section。ReviewProductFixForm(:81) → ConditionReviewPanel(:82) → 「修正する」Button(:84)＋ヒント(:87) → 理由一覧(:89-116) |
| `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx:99-109` | 理由ごとの「このままで良い」。条件は `is_v102===true` かつ `ackable!==false` かつ未ack |
| `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx:48-62` | `acknowledge(code)`。postReviewAck → notice → onRefresh |
| `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx:121-130` | ProductMasterDrawer を isProductDrawerOpen で開く。onSaved で閉じて onRefresh |
| `frontend/src/features/tcg-analysis-review/ReviewProductFixForm.tsx` | 商品の付け替え（AsyncCombobox → postProductCorrection → onRefresh） |
| `frontend/src/features/tcg-analysis-review/ConditionReviewPanel.tsx:25-27` | 状態の確認／訂正の表示条件 `relevant` |
| `frontend/src/features/tcg-analysis-review/reviewActions.ts:30-59` | postProductCorrection(:30-38) / postReviewAck(:41-46) / searchProductCandidates・Options(:49-59) |
| `frontend/src/features/tcg-analysis-review/reviewIssues.ts:2` | AtomicReviewIssueId 一覧 |

## 2. ProductMasterDrawer（`frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx`、530行）

- 分岐 `MasterMaintenanceSection` :505-511（PRODUCT_MASTER_UNREGISTERED→Registration／PRODUCT_ID_UNRESOLVED→SearchKeyword／EXCLUDED→Excluded／解決済み→ProductAssign）。本体 :515-530。
- **RegistrationSection** :88-274。入力 = 大分類・作品・メーカー・商品カテゴリ（自作 SearchSelect :49-84）、mark :202、日本語タイトル :206、英語タイトル :210、発売日 :214、検索キーワード :218、除外キーワード :222。必須 :131-134（kind・work・manufacturer・category・japanese_title）。
  - API: GET `/tcg/products/registration-form` :119、POST `/tcg/products/check-duplicates` :140、POST `/tcg/products` :153（`force: confirmed`）。重複あり→candidates 再表示 :163-167。成功文言 :178-186。
  - 成功後に **onSaved は呼ばれない**（:507 で未受け渡し）。
- **SearchKeywordSection** :278-381。GET `/tcg/products/search?query=` :292、POST `/tcg/products/${product_id}/search-keywords` body `{new_keyword: item.gemini.name}` :301-304（追記語は固定、編集不可）。onSaved 呼ばれない。
- **ExcludedSection** :385-395 は表示のみ（API なし）。「編集機能は今後のリリースで追加予定」。
- **ProductAssignSection** :401-501。「商品を変更する」「確認済みとして記録」とも postProductCorrection。成功で `onSaved?.()`。この部分だけ `t("superAdmin.supplierQuality.productAssign.*")`。
- 規約違反の現状: 生 `<input>` :69,202,206,210,214,243,339,463／`<textarea>` :218,222／`<datalist>` :79／生 `<button>` 複数。日本語直書きが :72,176-233,238-269,310-392,519-522 ほか多数（`useTranslation` は :402 の ProductAssignSection のみ）。`eslint-disable local/no-japanese-literal` は :237,:248 のみ。ESLint ルールは `frontend/eslint.config.js:31` で warn。
- 使用箇所は2か所のみ: `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx:17`、`frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx:6,41,119,134-139`。
- CSS `pmd-*` は `frontend/src/features/tcg-analysis-review/supplier-detail-view.css:107` 以降。SupplierDetailView の :8 が import、ReviewItemDrawer は review-item-drawer.css のみ（:23）。`frontend/src/pages/super-admin/AnalysisRulesPage.tsx:23,47` が両方 import（同一ページでは読み込まれる。バンドル分割は未確認）。

## 3. backend

権限はすべて `require_super_admin`（定義 `backend/app/auth/dependencies.py:491-516`。`is_super_admin` が偽なら 403）。付与箇所 `backend/app/routers/tcg_product_master.py:146,172,191,219,258,287,327`、`backend/app/routers/item_corrections.py:136,187`。

| 操作 | 引用先 | 事実 |
|---|---|---|
| 登録フォーム取得 | `backend/app/routers/tcg_product_master.py:137-156`／`backend/app/services/tcg_product_master_svc.py:43-124` | `pid_resolved` が真だと `PRODUCT_MASTER_V2_ALREADY_RESOLVED`(404) :77-78。選択肢は is_active のみ :91-122 |
| 商品検索 | `backend/app/routers/tcg_product_master.py:164-175`／`backend/app/services/tcg_product_master_svc.py:132-178` | name ILIKE・最大10件。`product_id` と `product_uuid` はどちらも products.id::text |
| 重複チェック | `backend/app/routers/tcg_product_master.py:183-202`／`backend/app/services/tcg_product_master_svc.py:186-289` | 同名 or（同一分類かつ同mark／同search_keywords）。mark・キーワードが空だと同一分類だけでは候補にならない |
| 新規登録 | `backend/app/routers/tcg_product_master.py:210-242`／`backend/app/services/tcg_product_master_svc.py:331-482` | 重複あり＋force無し→`ok:false, DUPLICATE_CANDIDATE`(HTTP 200)。products と product_search_keywords／product_exclude_keywords を INSERT。**抽出アイテムへの紐付け・analysis_results 更新・再解析キューは無し** |
| 検索キーワード追記 | `backend/app/routers/tcg_product_master.py:250-271`／`backend/app/services/tcg_product_master_svc.py:490-552` | path は int。再解析なし。重複は `KEYWORD_ALREADY_EXISTS` |
| 除外キーワード追記 | `backend/app/routers/tcg_product_master.py:279-300`／`backend/app/services/tcg_product_master_svc.py:560-622` | 商品単位。**呼ぶフロントのコードは見つからなかった**（テスト `backend/tests/test_tcg_product_master.py:437-505` のみ）。`docs/handoff/shadow-remove/recon.md:47` の「ProductMasterDrawer の :302 が使う」は現行コードと不一致 |
| 補正保存 | `backend/app/routers/item_corrections.py:127-170`／`backend/app/services/item_corrections_svc.py:16-76` | product_id 補正は analysis_results を MANUAL・pid_resolved=TRUE に更新。v102 は保存後 `enqueue_v102_reanalyze` :168-169。v102 では is_active な products の整数 id のみ許可 `backend/app/services/v102_human_decisions_svc.py:220-230,281-285` |
| 状態の確認／訂正 | `backend/app/routers/item_corrections.py:138-149`／`backend/app/services/tcg_condition_review_svc.py` | condition_review と fields は併用不可 :72-85 |
| 「このままで良い」 | `backend/app/routers/item_corrections.py:178-198`／`backend/app/services/v102_human_decisions_svc.py:243-258,288-311` | **v102 専用**（非v102は409）。常に再解析キュー :197 |
| 非ackable | `backend/app/services/review_reason_codes_svc.py:17` | `condition_unknown` のみ |
| 判断の反映 | `backend/app/services/line_analysis_v102_svc.py:31-50` | ack は理由を除去、商品判断は MANUAL、状態判断は condition_unknown 等を除去 |

## 4. 理由コード

- 定義表 `public.review_reason_codes`（`migrations/20261009_200000_create_review_reason_codes.sql:2-7`）。初期データ `docs/handoff/v102-prod-switch/data/review_reason_codes/README.md` 配下の seed（計37行）。翻訳 `frontend/src/locales/ja.json` の `reviewReason.*`。整合テスト `backend/tests/test_review_reason_codes_consistency.py`。
- fix_stage=analysis（システム側）: pid_unresolved, multi_candidate, note_unmatched, empty_box*, unit_unresolved, price_unresolved, excluded, unit_unknown, category_unknown, product_not_in_master, product_multiple, condition_multiple_candidates, condition_unknown, extract_exception, quantity_unresolved, price_source_mismatch, quantity_source_mismatch, value_out_of_range, item_mapping_mismatch, unit_price_mismatch。fix_stage=extraction（書き写し側）: item_shape_invalid, price_not_in_lines, duplicate_price_line, ship, condition, quantity_no_number, possible_footer_line, heading_ship_with_own_ship, no_items, possible_missing_item, gemini_unsure(_invalid), response_unreadable, quantity_not_in_text, gemini_gap_suspect。
- `review_issues` 算出 `backend/app/services/tcg_analysis_review_svc.py:120-140,304-311`。PRODUCT_MASTER_UNREGISTERED のときは PRODUCT_ID_UNRESOLVED も同時に付く。
- 生成元: `backend/app/services/line_analysis_v102_svc.py:90-97`、`backend/app/services/gemini_raw_copy_v102_product_first.py:80-84`、`backend/app/services/tcg_analyzer_svc.py:1212,1214,1686`。
- **EXCLUDED の原因**: analysis_results.exclusion が非空のとき。v102 は `item.status_effect`（`backend/app/services/line_analysis_v102_svc.py:687`）、v6 は状態の EXCLUDE 効果（`backend/app/services/tcg_analyzer_svc.py:1270-1296`）。一方、商品マスタの除外キーワードは商品候補から外す用途（`backend/app/services/gemini_raw_copy_v102_product_first.py:235,243,249`）。

## 5. 金型 `frontend/src/components/`

- 使える: Tabs.tsx、Select.tsx、AsyncCombobox.tsx、TextField.tsx、Textarea.tsx、Button.tsx、`Callout`、`Card`、`ListRow`、`ConfirmModal`、`Modal`、`Drawer`、`Stack`、`TwoColumn`。
- **無い**: Radio／Segmented／ChoiceCard／RadioGroup／Stepper。生 radio の既存例は `frontend/src/pages/register/RegisterPage.tsx:458`、`frontend/src/pages/roles/RolesPage.tsx:463`（自前 radiogroup）。
- `docs/CC_UI_GOVERNANCE.md:9-15`: 金型が無ければ実装せず止めて報告、PO許可後に Xxx.tsx+Xxx.css+Xxx.stories.tsx で登録。禁止（CI赤）:19-27 は生 select／生 input(text 系)／自作タブ／色直値／px 直値。例外は `ui-allow: 理由 (#番号)` :31-44。
- ゲート `scripts/check-ui-governance.js`（input 検出 :10,166,211）。ProductMasterDrawer の生 input に ui-allow は無い。ゲートが「変更ファイルのみ」を検査するかは未確認（`scripts/check-ui-governance.js` 内の diff 判定は未読）。

## 6. 試験・story・e2e の文言依存

- `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.test.tsx`: ProductMasterDrawer・ConditionReviewPanel・ItemComparison を vi.mock(:10-14)。英語文言に依存（:85-89 "Fix"、:99-105 "Product"／"Reassign to this product"／"Register or exclude in the product master"）。「直す」欄の構造・文言変更で壊れる。
- `frontend/src/features/tcg-analysis-review/ReviewProductFixForm.test.tsx`: "Current: Old Product"、"Reassigned"、"Failed to reassign" 等に依存。
- `frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.drawer.test.tsx`: ReviewItemDrawer を実物で使用。"Keep as is" で `/tcg/items/v102-item/review-ack` に `{source_message_id, codes:["product_not_in_master"]}`、ackable=false では1個のみ、v6 では出ない、api.post 回数。
- Story: `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.stories.tsx`。ProductMasterDrawer の story・専用テストは無い。
- e2e `frontend/tests-e2e/` に ReviewItemDrawer／ProductMasterDrawer／「直す」依存の spec は見つからなかった。

## 7. 既存設計との関係

- `docs/handoff/review-inline-edit/design.md:18-24`: 「商品の新規登録」「ProductMasterDrawer の手作り部品の置き換え」は当時の**対象外**（別課題）と明記。今回のウィザードはこの別課題に当たる。
- `docs/handoff/parity03-product-master-drawer-fe/design.md:55-66`: 除外キーワード編集 API 実装時に ExcludedSection の文言を差し替える TODO あり。API 自体は実装済み（上記 §3）だが差し替えは未実施。

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|---|---|---|
| 1 | 「除外する」が保存する対象（商品の除外語か、状態による除外の解除か） | PO／設計判断 | 未解決 |
| 2 | EXCLUDED の実原因が ExcludedSection の文言（商品マスタの除外キーワード）と一致するか | コード上は status_effect 由来に見える。実データ確認が必要 | 未確認 |
| 3 | 新規登録・キーワード追記後に即時反映を期待させるか（現状は再解析なし＝「次回解析で反映」） | PO／設計判断 | 未解決 |
| 4 | 理由コード別に「正しい直し方」の対応表（どのコードにどの選択肢を出すか） | コード上に対応表は無い。設計で定義 | 未解決 |
| 5 | 選択肢 UI を Tabs／Select／新規金型のどれにするか（Radio 等の金型が無い） | PO許可（`docs/CC_UI_GOVERNANCE.md:9-15`） | 未解決 |
| 6 | UI ゲートが既存の生 input を許容するか（差分のみ検査か） | `scripts/check-ui-governance.js` の判定を読む | 未確認 |
| 7 | `pmd-*` CSS のバンドル分割時の読込 | ビルド確認 | 未確認 |
| 8 | ack は v102 専用。非v102 の件に「このままで良い」を出すか | 設計判断 | 未解決 |

**未解決ゼロ確認**: 未解決あり（上表 1,3,4,5,8 は設計判断、2,6,7 は未確認）
