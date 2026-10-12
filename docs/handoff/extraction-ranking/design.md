<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — extraction-ranking

**対象ADR**: ADR-138（funnel-dashboard-stage1）/ ADR-027（i18n）/ ADR-144（UI governance）
**recon**: `docs/handoff/extraction-ranking/recon.md`
**日付**: 2026-09-25
**担当**: Planner

---

## 目的

抽出タブ（ExtractionTabContent、`frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:1007`）に「提供者ワーストランキング（エラー件数上位3）」と「商品ワーストランキング（raw_product_name別 未解決率上位3）」を追加し、問題を一目で把握できるようにする。

## 対象

- **backend**: `backend/app/routers/tcg_analysis_dashboard.py` / `backend/app/services/tcg_analysis_dashboard_svc.py` に商品ランキングAPI（1エンドポイント）を追加
- **frontend**: `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx` の ExtractionTabContent に2つのランキングセクションを追加
- **i18n**: `frontend/src/locales/ja.json` / `frontend/src/locales/en.json` に新規キーを追加

## 対象外

- 他タブ（import / analysis / distribution）への変更
- DBスキーマ変更・新テーブル作成
- テナント向け（非 super_admin）画面への変更

## 変更前後

| 項目 | 変更前 | 変更後 |
|------|-------|-------|
| 提供者別抽出状況テーブル | 全提供者を DataTable 表示 | 変更なし（既存テーブルは維持） |
| ワーストランキング | なし | テーブルの上に「提供者ワースト3」「商品ワースト3」セクションを追加 |
| 商品別未解決率API | なし | GET /api/v1/tcg/analysis-dashboard/product-resolution-ranking を追加 |
| i18nキー | extractionSupplierTitle 等（既存） | extractionWorstSupplierTitle 等（新規6キー追加） |

---

## 外部・過去事例の参照と我々への応用

該当なし：今回は既存UIパターン（frr-rank / FunnelReasonsPage）の踏襲であり、外部ライブラリ・外部サービスは不要と判断。既存の Card、Badge、DataTable 金型のみで実装可能（`frontend/src/pages/dashboard/FunnelReasonsPage.tsx:72` / `frontend/src/pages/dashboard/FunnelReasonsPage.css:86`）。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 抽出タブに「提供者ワースト3」セクションが表示される（エラー件数降順） | Evaluator（Playwright: 抽出タブを開き .adp-extraction-rank-supplier が存在することを確認） |
| 抽出タブに「商品ワースト3」セクションが表示される（未解決率降順） | Evaluator（Playwright: .adp-extraction-rank-product が存在することを確認） |
| GET /api/v1/tcg/analysis-dashboard/product-resolution-ranking が [{raw_product_name, total, unresolved, unresolved_rate}] を返す | pytest backend/tests/test_tcg_analysis_review.py::test_product_resolution_ranking（実装後に追加） |
| ランキングが0件のとき「データがありません」が表示される | Evaluator（Playwright: データ0件の状態で analysisRules.dashboard.noData テキストを確認） |
| 全UIテキストが t("key") 経由（ハードコード日本語なし） | `grep -rn` でAnalysisDashboardPanel.tsx内の日本語直書きが0件 |
| ja.json と en.json の新規キーが同一 | CI i18n lint（npm run lint:i18n） |
| 新規コンポーネントで生select/生input/色直値を使っていない | CI ADR-144 UI governance gate |

---

## 技術 How・KPI

### API設計

- エンドポイント: GET /api/v1/tcg/analysis-dashboard/product-resolution-ranking?limit=3
- 認証: require_super_admin（既存エンドポイントと同一。`backend/app/routers/tcg_analysis_dashboard.py:102` 参照）
- SQL骨格（`backend/app/services/tcg_analysis_dashboard_svc.py` に追加）:

```sql
SELECT
  ei.raw_product_name,
  COUNT(ar.id) AS total,
  COUNT(ar.id) FILTER (WHERE ar.pid_resolved = false) AS unresolved,
  ROUND(
    COUNT(ar.id) FILTER (WHERE ar.pid_resolved = false)::numeric
    / NULLIF(COUNT(ar.id), 0) * 100, 1
  ) AS unresolved_rate
FROM public.extraction_items ei
JOIN public.extraction_jobs ej ON ej.id = ei.extraction_job_id
JOIN public.analysis_results ar ON ar.extraction_item_id = ei.id
WHERE ei.raw_product_name IS NOT NULL
GROUP BY ei.raw_product_name
HAVING COUNT(ar.id) >= 3
ORDER BY unresolved_rate DESC, unresolved DESC
LIMIT :limit
```

- レスポンス型（`backend/app/routers/tcg_analysis_dashboard.py` に追加）:

```python
class ProductResolutionRankItem(BaseModel):
    raw_product_name: str
    total: int
    unresolved: int
    unresolved_rate: float  # 0.0〜100.0
```

### フロントエンド設計

- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:1007` の ExtractionTabContent 内、既存「提供者テーブル」セクション（analysis-dashboard-supplier-section）の前に2つのランキングセクションを挿入
- **提供者ワーストセクション**: supplierData.suppliers をエラー件数降順でソートし上位3件を表示。既存データ再利用のため API追加不要（`frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:1033` の extractionSupplierRows から派生）
- **商品ワーストセクション**: 新規API product-resolution-ranking を呼び出し上位3件を表示
- ランキングバッジ: `frontend/src/pages/dashboard/FunnelReasonsPage.tsx:72` の frr-rank パターンを踏襲。`frontend/src/tokens.css:343` の var(--dashboard-rank-badge) を使用
- バッジ色: 1位=var(--danger) / 2位=var(--warning) / 3位=Badge variant="neutral"
- UI金型: Card、Badge、Button、DataTable（すべて `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:33-37` でインポート済み）
- デザイントークン: --dashboard-rank-badge（`frontend/src/tokens.css:343`）/ --comp-card-*（`frontend/src/tokens.css:438-445`）/ var(--danger) / var(--warning) / var(--success)
- CSSクラス命名:
  - .adp-extraction-rank-supplier — 提供者ワーストセクション
  - .adp-extraction-rank-product — 商品ワーストセクション
  - .adp-extraction-rank-row — ランク行
  - .adp-extraction-rank-badge — ランクバッジ

### i18nキー（新規6件）

| キー | ja | en |
|-----|----|----|
| analysisRules.dashboard.extractionWorstSupplierTitle | 提供者ワースト | Supplier Worst |
| analysisRules.dashboard.extractionWorstProductTitle | 商品ワースト（未解決率） | Product Worst (Unresolved) |
| analysisRules.dashboard.extractionRankErrorCount | エラー件数 | Error Count |
| analysisRules.dashboard.extractionRankUnresolvedRate | 未解決率 | Unresolved Rate |
| analysisRules.dashboard.extractionRankTotal | 総件数 | Total |
| analysisRules.dashboard.extractionRankSuffix | 位 | # |

### KPI

- 抽出タブ初期表示でランキングセクションが200ms以内にレンダリング（提供者ランキングは既存データ流用のため追加fetch不要）
- 商品ランキングAPIのレスポンスタイム: p95 < 300ms

---

## 弊害・トレードオフ

- **母数フィルタ（HAVING COUNT >= 3）**: 母数が少ない商品名は除外される。まずは固定値3で実装し、問題があれば設定化 → 対策: POに説明し必要なら定数化
- **raw_product_name の表記ゆれ**: 同じ商品でも微妙に異なる名前で登録されている場合、順位が分散する可能性がある。今フェーズは表記ゆれ統合は対象外（ADR-158 商品レベル supersession が将来対応予定）
- **既存テーブルとの見た目の重複**: 提供者ワーストは既存の提供者テーブルと同じデータを使う。ランキングはトップ3の要約、テーブルは全件詳細という使い分けを UIコメントで明示する

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `backend/app/services/tcg_analysis_dashboard_svc.py` に get_product_resolution_ranking(db, limit) 関数を追加 | Generator |
| 2 | `backend/app/routers/tcg_analysis_dashboard.py` に ProductResolutionRankItem モデルと product-resolution-ranking エンドポイントを追加 | Generator |
| 3 | backend/tests/ に test_product_resolution_ranking テストを追加 | Generator |
| 4 | `frontend/src/locales/ja.json` / `frontend/src/locales/en.json` に新規i18nキー6件を追加 | Generator |
| 5 | `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx` の ExtractionTabContent に2ランキングセクションを追加（既存テーブルの前に挿入） | Generator |
| 6 | Playwright Evaluator でランキングセクションの表示確認 | Evaluator |

---

## 継続

- 完了後の監視: 商品ランキングAPIのレスポンスタイムを Grafana で1週間観察
- 次フェーズへの引き継ぎ: 表記ゆれ統合（ADR-158）完了後、raw_product_name → product_code でのランキング再設計を検討

## 維持の仕組み

守り手:
  - i18n lint（npm run lint:i18n）: ja/en キー同一性を自動チェック
  - UI governance gate（ADR-144）: 生select/生input/色直値の混入防止
  - process-artifacts gate: このrecon/design の引用パス実在確認
