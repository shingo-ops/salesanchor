# design: analysis panel layout fix

## KGI

ダッシュボード以外の全サブメニューパネル（accuracy-management / needs-review / product-master / product-categories-master / product-kinds-master / status-master / supplier-master / conditions-master / unit-master / note-master）で、左パディングが付きスクロールが動作する。

| 基準 | 検証方法 |
|---|---|
| 各パネルに左パディングが存在する | ブラウザDevToolsで `.analysis-panel-content` の computed padding-left が `var(--space-6)` 相当（24px等）であること |
| 各パネルがスクロール可能 | 内容が高さを超えるパネルでスクロールバーが出現すること |
| ダッシュボードに影響なし | ダッシュボードの動作・見た目が変わらないこと |

## 方針

### Option A: ラッパー div を AnalysisRulesPage.tsx に追加（採用）

**理由**: 問題の発生場所（レイアウト責任）がページコンポーネントにある。パネル側は再利用性を維持するため変更しない。

```tsx
{activeSection !== "dashboard" && (
  <div className="analysis-panel-content">
    {/* 非ダッシュボードパネルをここに列挙 */}
  </div>
)}
```

```css
/* AnalysisRulesPage.css */
.analysis-panel-content {
  padding: var(--space-6);
  overflow-y: auto;
  height: 100%;
}
```

### 不採用案

- `hub-shell.css` に直接追加: 他ページに影響・ADR-144 違反
- 各パネルコンポーネントに追加: パディングが重複する可能性・再利用時に問題

## 影響範囲

- 変更するファイル: `AnalysisRulesPage.tsx`（1ページのみ）、`AnalysisRulesPage.css`（新規）
- 影響を受けるパネル: 上記10パネル（全て非ダッシュボード）
- 影響を受けないパネル: AnalysisDashboardPanel（`activeSection === "dashboard"` の条件が残る）
- 他ページへの影響: なし（クラス名 `analysis-panel-content` は本ファイル限定）

## 戻し方

`AnalysisRulesPage.tsx` の wrapper div を削除し、`AnalysisRulesPage.css` を削除する。

## 外部・過去事例の参照と我々への応用

ManagementCenterPage（`frontend/src/pages/management-center/ManagementCenterPage.css`）は `/* styles moved to frontend/src/hub-shell.css */` のみで、hub-shell.css に移行済み。AnalysisRulesPage は hub-shell クラスを使いつつページ固有のラッパークラスを独自 CSS ファイルに定義する同様の分離パターンを採用する。

## 維持の仕組み

守り手: ADR-144（hub-shell.css 変更禁止）・ADR-067（デザイントークン）。新規パネルを追加した場合は `activeSection !== "dashboard"` ブランチに列挙するだけでラッパーが自動適用される。
