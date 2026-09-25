# recon: fix-dropzone-border

## 調査結果

### 問題の特定

`frontend/src/pages/super-admin/components/AnalysisDashboardPanel.css:42` にて:

```css
.analysis-dashboard-dropzone {
  border: 2px dashed var(--color-border);
```

`--color-border` が使用されているが、プロジェクト内の全CSSファイルを調査した結果、このカスタムプロパティは**一切定義されていない**ことを確認した。

```bash
grep -rn "^\s*--color-border\s*:" frontend/src --include="*.css"
# → 0件（完全に未定義）
```

### 影響確認

- `AnalysisDashboardPanel.css:78` にも同様に `var(--color-border)` が使用されている（window-input ボーダー）
- SVGアイコンは正常表示（HTML構造に問題なし）
- CSS カスタムプロパティが未定義 → `border` が初期値 `none` にフォールバック → 破線が不可視

### 正しいトークン確認

`frontend/src/index.css` で定義済みのボーダートークン:

```
--border: #e2e8f0;          (ライト) / #334155 (ダーク)
--border-strong: #cbd5e0;   (ライト) / #475569 (ダーク)
```

### 関連ADR

- ADR-067: デザイントークン強制（定義済みトークンのみ使用すること）
