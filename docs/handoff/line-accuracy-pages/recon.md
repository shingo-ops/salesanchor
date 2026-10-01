# recon：LINE解析「要確認」の移設と「解析精度管理（新方式）」

基準：origin/main（2026-10-01 に fetch）。調査はすべて読み取りのみ。設計書は同じ場所にある design.md。

## 既存 ADR の検索
- 対象の ADR
  - ADR-027（i18n）
  - ADR-067（デザイントークン）
  - ADR-144（UI ガバナンス）
  - ADR-158（要確認一覧。`frontend/src/App.tsx:306` のコメント）
  - ADR-1003（v7 の書き写しと判定の分離）
- 調べ方：ADR を「needs-review」「shadow」「accuracy」で検索した（docs/adr/FEATURE-INDEX.md を含む）。
- 結果：この設計の判断と食い違う ADR は見つからなかった。

## メニューとルート
- LINE解析ハブ：`frontend/src/pages/super-admin/AnalysisRulesPage.tsx:123-213`。切り替えは `?section=`（:135）。権限は `useSuperAdmin`（:122、:146-154）。
- サブメニューの定義：`frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx:10-35`（キーの型）、`:78-129`（項目）。
- 「要確認」の今の中身：`frontend/src/pages/super-admin/AnalysisRulesPage.tsx:89-112`（NeedsReviewPanel）。「準備中」を表示するだけ（ja.json:4321-4325）。
- ダッシュボードからの導線：`frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:931`、`:1459`、`:1552`
- 「解析精度管理」（旧方式）：`frontend/src/pages/super-admin/AnalysisRulesPage.tsx:56-87`
- 独立した要確認一覧
  - 本体：`frontend/src/pages/super-admin/NeedsReviewListPage.tsx`
  - 3タブ：`:459-470`
  - API の呼び出し：本番 `:166`、試運転 `:206`、詰まり `:239`、モーダル `:290`、`:309-310`
  - ルート：`frontend/src/App.tsx:97`、`:308-309`
  - メニュー：`frontend/src/components/DesktopShell.tsx:194`、`frontend/src/components/MobileShell.tsx:170-175`
  - 試験：`frontend/src/pages/super-admin/NeedsReviewListPage.test.tsx:7`、`:61`
  - i18n：`nav.superAdminNeedsReview`（ja.json:267、en.json:267）
  - コードからの参照は、上に挙げた箇所だけ。e2e からの参照はない。

## 部品
- SourceRawPane（`frontend/src/features/tcg-analysis-review/SourceRawPane.tsx:7`）
  - props：sourceMessageId、rawText、itemCount、jump
  - 強調は1行だけで、2.6秒で消える（:12、:29）。
  - 日本語が直書きされている（:30）。
  - 使っているのは `frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx:111` の1か所だけ。
- sourceRawLines：`frontend/src/features/tcg-analysis-review/sourceRawNavigation.ts:1-5`
- ItemComparison：`frontend/src/features/tcg-analysis-review/ItemComparison.tsx:15`、`:19`、`:30`。項目は6つで固定。onJumpToSourceLine は必須。
- Drawer：`frontend/src/components/Drawer.tsx:22-30`。幅は `Drawer.css:30` で 480px（変数で上書きはできる）。
- セクション用パネルの置き場所の慣例：`frontend/src/pages/super-admin/components/ExtractionErrorLogPanel.tsx`、`frontend/src/pages/super-admin/components/DbViewerPanel.tsx`（import は `frontend/src/pages/super-admin/AnalysisRulesPage.tsx:23-50`）

## バックエンド
- `backend/app/routers/tcg_shadow_review.py:28`（APIRouter に prefix なし）
  - `:33`、`:50`、`:70`：require_super_admin
  - `:41`、`:55`、`:75`：get_db
  - 戻り値は dict
- 登録：`backend/app/main.py:123`（import）、`:683-685`（prefix は /api/v1）
- サービス：`backend/app/services/tcg_shadow_review_svc.py:25-32`（共通の FROM）、`:45`、`:136`、`:231`
- 試験：`backend/tests/test_tcg_shadow_review.py:19-43`（mock と dependency_overrides）、`backend/tests/test_tcg_shadow_review_pg.py:13-64`、`backend/tests/test_extraction_shadow_tables_pg.py:52-64`（migration から表を作る）

## 単位と状態（本番 DB を読み取りのみで確認、2026-10-01）
- units の kubun
  - 箱系大（Case、MasterCarton）
  - 箱系（Box）
  - パック系（Pack）
  - 単品系（Piece：枚、pcs）
  - 複合（Set）
  - 除外（本）
  - 数量専用（点）
  - 条件つき（個）
  - 冊子系（Booklet：冊）
- conditions の CN0008 FLAG_SINGLE：app_kubun は「枚系,単位不明」
  - 定義元：`migrations/20260901_090000_add_condition_resolution_columns.sql:137`、`:150`、`:163`
  - 単位マスタには「枚系」という kubun が無い。
- FLAG_SINGLE になる経路：`backend/app/services/tcg_analyzer_svc.py:851-880`（R4 の最後の行。箱系とパック系以外の kubun はすべてここに落ちる）

## 精度の調査（設計の根拠）
- 一覧はこのフォルダの accuracy-evidence.md。生データは /tmp/CC報告ファイル/accuracy-eval/。
