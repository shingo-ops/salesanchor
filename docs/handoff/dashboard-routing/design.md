# design — ダッシュボードルーティング修正

**仕事名**: ダッシュボードデフォルトタブ変更＋セクション状態URL保持  
**日付**: 2026-09-25  
**参照 recon**: `docs/handoff/dashboard-routing/recon.md`

---

## KGI / KPI

| 基準 | 検証方法 |
|------|---------|
| ダッシュボードを開いたとき最初に表示されるタブが「Import」である | ブラウザでページを開き、Import タブがアクティブなことを目視確認 |
| `?section=product-master` などのURLでページを開くと、対応セクションが表示される | URLに `?section=product-master` を付けてアクセス |
| サブナビのリンクをクリックした後リロードしても同じセクションが表示される | セクション移動後 F5 でリロードし、同じセクションが表示されることを確認 |

---

## 変更内容

### 1. デフォルトタブを Import に変更

`frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:300`

変更前: `useState<DashboardTab>("extraction")`  
変更後: `useState<DashboardTab>("import")`

### 2. セクション状態を URL searchParams で保持

`frontend/src/pages/super-admin/AnalysisRulesPage.tsx`

- `useSearchParams` を `react-router-dom` から追加 import
- `initialSection` を `searchParams.get("section")` から読み込み（デフォルト: `"dashboard"`）
- `handleSectionChange` で `setSearchParams({ section: key }, { replace: true })` を呼び出し

---

## 影響範囲

- `AnalysisDashboardPanel`: タブ初期値のみ変更。APIコール・レンダリングロジックは不変
- `AnalysisRulesPage`: `handleSectionChange` に URL 更新処理を追加。既存の `navigate("/super-admin/tcg-line-import")` 分岐は維持

---

## 関連 ADR

- **ADR-138**（ファネル型目標対比ダッシュボード 第1弾）: ダッシュボード UI の基本構成を規定。本作業はそのタブ初期値・URL 状態保持を整合させるもの。

## 外部・過去事例の参照と我々への応用

- React Router `useSearchParams` による URL 状態保持は公式推奨パターン（React Router v6 docs）
- `replace: true` オプションで履歴を汚さずに URL を更新するのが標準的な実装
- 既存コードベースで `useNavigate` は使用済みのため、同一 import から `useSearchParams` を追加する形は実績あり

---

## 維持の仕組み

- URL searchParams でセクションを保持するため、ブックマーク・共有リンクでも同じセクションが開く
- `replace: true` により「戻る」ボタンの動作に影響しない
- 守り手: 人手で守る（ロジック変更）
