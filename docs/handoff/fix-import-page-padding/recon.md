# recon: fix-import-page-padding

## 目的
TcgLineImportPage の hub-content div にパディングが欠けているため、コンテンツが左端に張り付いている問題を修正する。

## 調査結果

### 対象ファイル
- `frontend/src/pages/super-admin/TcgLineImportPage.tsx:282` — hub-content div に `padding` が未設定

### 比較対象（他パネル）
- `frontend/src/pages/super-admin/AnalysisRulesPage.tsx` — hub-content に `var(--space-6)` を適用済み（PR #3645 で修正）

### ADR確認
- `docs/adr/ADR-067-design-token-enforcement.md` — デザイントークン強制ルール
- `docs/adr/ADR-144-ui-component-governance.md` — UIガバナンス

### 変更前
```tsx
<div className="hub-content" style={{ overflowY: "auto" }}>
```

### 変更後
```tsx
<div className="hub-content" style={{ overflowY: "auto", padding: "var(--space-6)" }}>
```

## 影響範囲
- `frontend/src/pages/super-admin/TcgLineImportPage.tsx` のみ
- 他ページへの影響なし
