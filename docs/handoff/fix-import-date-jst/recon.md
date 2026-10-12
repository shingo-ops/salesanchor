# recon: fix-import-date-jst

## 問題

インポートタブの「最近のインポート」DataTable の `created_at` 列が UTC ISO 文字列（例: `2026-09-21T04:00:00Z`）のまま表示されている。

## 調査結果

### 現在の表示箇所

`frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:464-467`

```typescript
{
  key: "created_at",
  header: t("analysisRules.dashboard.importDate"),
  width: "140px",
},
```

`renderCell` が未設定のため、DataTable が `String(row["created_at"])` をそのまま表示。

### DataTable の `renderCell` サポート

`frontend/src/components/DataTable.tsx:38`

```typescript
renderCell?: (row: T, rowKey: string) => ReactNode;
```

`renderCell` プロパティが存在し、カスタムセルレンダリングが可能。

### データ型

`frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:124`

```typescript
created_at: string | null;
```

### 関連 ADR

- ADR-027: UI 文字列の国際化ルール（`t()` 経由）
- ADR-067: デザイントークン強制
- ADR-144: UIガバナンス
