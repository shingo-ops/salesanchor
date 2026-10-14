<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ。行番号は origin/main fb836a69c（#4265 マージ後）基準 -->
# Phase 2 recon — review-fix-column（要確認スライドの「採用元」→「修正」列）

**日付**: 2026-10-14  
**調査**: Sonnet（読み取りのみ）＋ Opus の実物確認。生出力はリポジトリ外 /private/tmp/claude-501/.../scratchpad/f/・f2/ と /tmp/CC報告ファイル/fixcol-prod-corrections.txt

## 0. 既存 ADR の検索結果
- `git grep -il "corrections|要確認|review" origin/main -- docs/adr/` は約65件が当たったが、要確認スライド・item_corrections・analysis-results を本文で扱う ADR は無い。`docs/adr/FEATURE-INDEX.md` にも要確認の行は無い（ADR-100 取り込み/解析のみ）。
- 守る ADR: `docs/adr/ADR-144-ui-component-governance.md`（金型）、`docs/adr/ADR-067-design-token-enforcement.md`（トークン）、`docs/adr/ADR-027-ui-internationalization.md`（i18n）。
- 設計の正本は handoff: `docs/handoff/review-fix-wizard/design.md`、`docs/handoff/review-inline-edit/design.md`、`docs/handoff/v102-prod-switch/design.md` §13-3〜§13-5。

## 1. 「採用元」列
- `frontend/src/locales/ja.json:4650` `tcgAnalysisReview.compareColumns.source = "採用元"`（en: "Source"）。使用は `frontend/src/features/tcg-analysis-review/ItemComparison.tsx:76` の1か所。
- 値は API の値ではなく `frontend/src/features/tcg-analysis-review/ItemComparison.tsx:30-39` の systemCell() が作る文言（Gemini抽出値を採用／System確定／未解決／—）。
- 同じ表（readOnly）を使う画面は2つ: `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx:45`（要確認スライド）と `frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx:116`（仕入元詳細）。
- 表は10行（`frontend/src/features/tcg-analysis-review/ItemComparison.tsx:45-62` buildComparisonRows: name/quantity/price/unit/state/memo＋原文位置・作品・商品ID・販売状況）。DataTable に onRowClick は無い（`frontend/src/features/tcg-analysis-review/ItemComparison.tsx:82`）。値を変える部品は無い。

## 2. 要確認スライド（ReviewItemDrawer）
- `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx:36` Drawer タイトル「要確認の商品」（`frontend/src/locales/ja.json:3763` reviewItem.drawerTitle）。
- 理由は「直す」見出しの中、「確認が必要な理由」見出し付きで出る（`frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx:50-66`）。出どころ行 `:54`、gemini_gap_suspect は GapSuspectNote（`:61-63`）。
- `ReviewFixWizard`（`frontend/src/features/tcg-analysis-review/ReviewFixWizard.tsx`）の choice は内部 state（`:53`）、外から初期値を渡す prop は無い（`:45-49`）。出し分けは availableFixChoices（`:36-43`）。

## 3. 一覧表（NeedsReviewTabsPanel）
- `frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx:166-173` 列 inline_fix に ReviewRowActions（frontend/src/features/tcg-analysis-review/ReviewRowActions.tsx）。商品の AsyncCombobox（選んだ瞬間に保存）と「このままで良い」。追加は ef4c96000（2026-10-13、`docs/handoff/review-inline-edit/design.md`）。
- `frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx:70` drawerItem は行オブジェクトのコピー。`:199` onRowClick={setDrawerItem}、`:210-216` ReviewItemDrawer。保存後は reloadKey で一覧を再取得（`:75-109`）するが drawerItem は差し替わらない → スライド内の表は古いまま。

## 4. 修正値の正本（DB）
- 正本は `public.item_corrections`（`migrations/20260921_110000_pipeline_tables_public.sql:321-334`、追記のみ）。
- 商品付け替え: `backend/app/services/item_corrections_svc.py:59-73` が同じトランザクションで analysis_results の product_id と `pid_basis='MANUAL'` を更新。v102 再解析でも `_apply_decisions` が判断と同じ商品なら `pid_basis='MANUAL'` を付け直す（`backend/app/services/line_analysis_v102_svc.py:790-801`、定数 `:101`）。
- 状態: `backend/app/services/tcg_condition_review_svc.py:348-359` が analysis_results の condition_id・condition_canonical・`condition_basis='MANUAL_CONDITION_REVIEW'` を同期更新。再解析も同じ値を付け直す（`backend/app/services/line_analysis_v102_svc.py:802-804`、定数 `:102`）。
- 一覧 API（`backend/app/services/tcg_analysis_review_svc.py:194-248`）は `system.pid_basis` を返す（`:224`、`:288`）。`condition_basis` は返していない。人の値・日時は返さない。
- 付け替えの human_value は整数 id 文字列（`frontend/src/features/tcg-analysis-review/reviewActions.ts:34-41` の product_uuid は `p.id::text`、`backend/app/services/tcg_product_master_svc.py:151`）。

## 5. 不具合（実物で確認）: 「状態を直す」の保存が必ず 422
- `backend/app/routers/item_corrections.py:60` `ConditionReviewRequest.condition_id: UUID`。
- 状態の id は整数（`public.conditions.id` INTEGER、`migrations/20260919_020000_master_ssot_public_tables.sql:145-146`）。画面が送る値は `/tcg/conditions/review-options` の `id::text`（`backend/app/services/tcg_condition_review_svc.py:268-272`）と `review.condition_id`（`frontend/src/features/tcg-analysis-review/ConditionReviewPanel.tsx:55`）。
- サービスは整数前提: `backend/app/services/tcg_condition_review_svc.py:286` `int(request["condition_id"])`。
- Opus 実行: pydantic で `UUID` 型に `'5'` → `ValidationError uuid_parsing`。
- 本番（2026-10-14、読み取り専用 SELECT）: item_corrections の field_name='condition_review' は **0 行**、review_ack も 0 行、product_id は 387 行（全て整数形、最新 2026-09-16）。生出力 /tmp/CC報告ファイル/fixcol-prod-corrections.txt。
- テスト `backend/tests/test_item_corrections.py:155-157` は UUID を渡しているため、この不一致を検出できていない。

## 6. 部品（金型）
- DataTable（`frontend/src/components/DataTable.tsx`）: onRowClick（`:78`、Enter/Space 対応 `:254-264`）、selectedKeys（`:65`）を渡すだけで選択行の見た目（`frontend/src/components/DataTable.css:138-145`）。
- 赤字: Text 金型は無い。トークン `--danger-text`（`frontend/src/index.css:53` ライト / `:246` ダーク）。既存の赤字はクラスで `color: var(--danger)` 等（例 `frontend/src/components/FormField.css:40`）。
- Callout は warning/info のみ（`frontend/src/components/Callout.tsx:13`）。ChoiceCardGroup（#4265 で登録済み）。

## 7. 状態の表示名
- system.condition は英語の canonical（例 Empty box）。日本語は Empty box→「空箱」のみ（`frontend/src/locales/ja.json:3712`、`frontend/src/features/tcg-analysis-review/ConditionReviewPanel.tsx:50`）。
