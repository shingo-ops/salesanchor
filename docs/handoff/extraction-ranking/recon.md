<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# recon — extraction-ranking

**仕事名**: extraction-ranking  
**日付**: 2026-09-25  
**対象ADR**: ADR-138（funnel-dashboard-stage1）/ ADR-027（i18n）/ ADR-144（UI governance）  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:52` | `DashboardTab = "import" \| "extraction" \| "analysis" \| "distribution"` — 抽出タブが既存定義済み |
| `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:300` | `const [activeTab, setActiveTab] = useState<DashboardTab>("extraction")` — 初期タブが抽出 |
| `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:516` | `{activeTab === "extraction" && (` — 抽出タブの描画開始位置 |
| `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:993` | `// Extraction Tab` — ExtractionTabContent 関数の開始 |
| `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:1007` | `function ExtractionTabContent(...)` — 抽出タブコンポーネント本体 |
| `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:1033` | `const extractionSupplierRows = supplierData ? [...supplierData.suppliers].sort(...)` — 既存の提供者別テーブルデータ（error→empty→done→pending 昇順ソート） |
| `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:1049` | `const extractionSupplierColumns: DataTableColumn<ExtractionSupplierRow>[]` — 既存DataTable列定義（5列: 提供者名・抽出状態・成功・エラー・商品なし） |
| `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:33` | `import { Card } from "../../../components/Card"` — Card金型インポート確認済み |
| `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:35` | `import { Badge } from "../../../components/Badge"` — Badge金型インポート確認済み |
| `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:36` | `import { DataTable } from "../../../components/DataTable"` — DataTable金型インポート確認済み |
| `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:181` | `extraction_by_supplier: ExtractionBySupplierItem[]` — `PipelineSummary` 型に提供者別集計フィールド存在 |
| `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:525` | `<ExtractionTabContent data={data} supplierData={supplierData}` — ExtractionTabContent 呼び出し箇所 |
| `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:1294` | `{data.extraction_by_supplier.filter((s) => s.error_count > 0).length > 0 && (` — 既存エラー提供者フィルタ（`extraction_by_supplier`利用箇所） |
| `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:1398` | `const bottleneck = metrics.reduce((worst, m) => (m.rate < worst.rate ? m : worst))` — `worst` パターン既存参照（AnalysisTabContent内） |
| `frontend/src/pages/dashboard/FunnelReasonsPage.tsx:72` | `<span className="frr-rank">{i + 1}</span>` — 既存ランキングバッジ実装（frr-rankパターン） |
| `frontend/src/pages/dashboard/FunnelReasonsPage.css:86` | `.frr-rank { ... var(--dashboard-rank-badge) ... }` — ランキングバッジCSS定義（流用元） |
| `frontend/src/tokens.css:343` | `--dashboard-rank-badge: 20px` — ランキングバッジサイズトークン定義 |
| `frontend/src/tokens.css:432` | `--comp-card-radius` / `--comp-card-padding` — Card デザイントークン確認済み |
| `frontend/src/tokens.css:468` | `--comp-badge-radius` / `--comp-badge-height-sm` — Badge デザイントークン確認済み |
| `backend/app/routers/tcg_analysis_dashboard.py:102` | `@router.get(...)` — `pipeline-summary` エンドポイント定義 |
| `backend/app/routers/tcg_analysis_dashboard.py:297` | `@router.get(...)` / `async def supplier_pipeline` — `supplier-pipeline` エンドポイント（提供者別ジョブ集計） |
| `backend/app/routers/tcg_analysis_dashboard.py:94` | `extraction_by_supplier: list[ExtractionBySupplierItem]` — PipelineSummary レスポンス型 |
| `backend/app/services/tcg_analysis_dashboard_svc.py:22` | `extraction_jobs GROUP BY status` — ジョブ状態別件数クエリ |
| `backend/app/services/tcg_analysis_dashboard_svc.py:79` | `JOIN extraction_items ei ON ei.extraction_job_id = ej.id` — extraction_items と extraction_jobs の JOIN確認 |
| `backend/app/services/tcg_analysis_dashboard_svc.py:435` | `FROM supplier_channels sc JOIN source_messages sm ... LEFT JOIN extraction_jobs ej ...` — 提供者→source_messages→extraction_jobs の結合パス |
| `backend/app/services/tcg_analysis_dashboard_svc.py:56` | `SUM(CASE WHEN pid_resolved THEN 1 ELSE 0 END) AS pid_resolved_count` — 商品ID解決率はanalysis_results.pid_resolvedで算出 |
| `backend/app/tasks/tcg_extraction.py:285` | `raw_product_name, raw_quantity, raw_price, ... resolved_product_code` — extraction_items への書き込みフィールド確認 |
| `frontend/src/locales/ja.json:3962` | `"analysisRules": { "dashboard": { ... } }` — 既存i18nキー（supplierTableTitle等）確認済み |
| `frontend/src/locales/ja.json:4100` | `"extractionSupplierTitle" / "extractionSupplierDone" / "extractionSupplierError"` — 抽出関連キー末尾確認 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 商品レベル（raw_product_name別）の解決率を返す専用APIが存在するか | `backend/app/services/tcg_analysis_dashboard_svc.py` と `backend/app/routers/tcg_analysis_dashboard.py` の全エンドポイントを走査 | ✅ 解消済み: 存在しない。提供者別集計（supplier-pipeline）のみ存在。商品別解決率ランキングAPIは新規追加が必要 |
| 2 | extraction_items の raw_product_name フィールドが実在するか | `backend/app/tasks/tcg_extraction.py:285` で確認 | ✅ 解消済み: 実在する |
| 3 | extraction_jobs と supplier_channels の結合パスが存在するか | `backend/app/services/tcg_analysis_dashboard_svc.py:435` で確認 | ✅ 解消済み: `supplier_channels → source_messages → extraction_jobs` パスが存在する |
| 4 | 既存ランキング表示UIパターン（frr-rank）が流用可能か | `frontend/src/pages/dashboard/FunnelReasonsPage.tsx:72` と `FunnelReasonsPage.css:86` で確認 | ✅ 解消済み: 流用可能。`frr-rank` + `var(--dashboard-rank-badge)` のパターンが存在 |
| 5 | ADR-144 が求める金型コンポーネントが抽出タブで既に使われているか | `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:33` で確認 | ✅ 解消済み: Card / Badge / DataTable はすべて既存インポート済み |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

- **スキーマ**: TCGパイプラインテーブルは `public` スキーマに移行済み（ADR-1002・PR #pipeline-public-migration）。クエリ内の `{TCG_SCHEMA}` は `public` に解決される
- **pid_resolved**: analysis_results.pid_resolved（BOOL）が商品ID解決の判定フィールド。提供者ランキングには `pid_unresolved` 件数の高い順を利用する
- **解決率ランキングの2軸**: 設計として「提供者ワーストN」と「商品ワーストN（raw_product_name別未解決率）」の2軸が考えられるが、商品軸は新規SQL必要
- **既存DataTable**: AnalysisDashboardPanel内で既に `extractionSupplierRows` を DataTable に渡している。ランキングセクションはこのテーブルの前に挿入するのが自然
