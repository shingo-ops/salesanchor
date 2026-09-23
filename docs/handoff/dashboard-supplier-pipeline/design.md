# design: dashboard-supplier-pipeline

## KGI

提供者別パイプライン可視化により、問題のある提供者をオペレーターが即座に特定できる。
4タブ全てに提供者テーブルを表示し、severity=danger の提供者が上部に表示されること。

## 変更の設計

### 新規API: GET /tcg/analysis-dashboard/supplier-pipeline

`backend/app/services/tcg_analysis_dashboard_svc.py` に `get_supplier_pipeline()` を追加。
`backend/app/routers/tcg_analysis_dashboard.py` に `supplier-pipeline` エンドポイントと Pydantic スキーマを追加。

レスポンス形式:
```json
{
  "suppliers": [
    {
      "name": "提供者A",
      "import_count": 120,
      "extraction_success_rate": 0.95,
      "analysis_success_rate": 0.88,
      "distribution_rate": 0.72,
      "severity": "danger"  // "danger" | "warning" | "ok"
    }
  ]
}
```

severity 判定基準:
- danger: いずれかの率が 70% 未満
- warning: いずれかの率が 85% 未満
- ok: 全て 85% 以上

### フロントエンド: 4タブ共通「問題先出し」パターン

`frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx` に以下を追加:
- 問題バナー: タブごとに問題のある提供者数を表示
- 提供者テーブル: severity 降順ソート（danger → warning → ok）
- 既存の KPI カード・トレンドグラフは下部に温存

スタイルは `AnalysisDashboardPanel.css` に追加（デザイントークン使用）。

### i18n

`frontend/src/locales/ja.json` / `frontend/src/locales/en.json` に 16 キー追加。
全 UI 文字列は `t("key")` 経由。ハードコード禁止。

## 影響範囲

- 新規エンドポイントのみ追加（既存エンドポイント変更なし）
- 既存 KPI カード・トレンドグラフは下部に移動（削除なし）
- migrations なし（DB スキーマ変更なし）

## 外部・過去事例の参照と我々への応用

「問題先出し」パターン（problems first）は既存の `docs/handoff/analysis-dashboard/design.md` でも採用済み。
同一プロジェクト内の実装パターンを踏襲し、severity 分類による visual hierarchy を統一する。

## 維持の仕組み

守り手: super-admin ページ担当エンジニア
API は SELECT 専用のため副作用なし。新規提供者は自動的にテーブルに反映される。
