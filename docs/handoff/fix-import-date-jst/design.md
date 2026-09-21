# design: fix-import-date-jst

## 目的

インポートタブの最近のインポート DataTable で `created_at` をJST日本語形式（例: `2026年9月21日 13:00`）で表示する。

## 変更内容

`frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx` の `created_at` 列定義に `renderCell` を追加。

変更前:
```typescript
{
  key: "created_at",
  header: t("analysisRules.dashboard.importDate"),
  width: "140px",
},
```

変更後:
```typescript
{
  key: "created_at",
  header: t("analysisRules.dashboard.importDate"),
  width: "180px",
  renderCell: (row: ImportTableRow) => {
    if (!row.created_at) return "-";
    return new Date(row.created_at).toLocaleString("ja-JP", {
      timeZone: "Asia/Tokyo",
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  },
},
```

## 検証方法

| 基準 | 検証方法 |
|------|----------|
| TypeScript エラーなし | `./node_modules/.bin/tsc --noEmit` が 0 exit |
| ESLint エラーなし | `./node_modules/.bin/eslint src/...` が 0 errors |
| 表示形式 | `2026年9月21日 13:00` 形式で表示される |
| タイムゾーン | UTC `04:00:00Z` → JST `13:00` に変換される |
| null ガード | `created_at` が null のとき `-` が表示される |

## 外部・過去事例の参照と我々への応用

`Intl.DateTimeFormat` / `toLocaleString` は MDN Web Docs で仕様が確立されており、Node.js v18+ および全主要ブラウザでサポート済み。

- `timeZone: "Asia/Tokyo"` を明示することでブラウザのシステムタイムゾーン設定に依存しない（サーバーサイドレンダリングや海外ユーザーでも JST が保証される）。
- `month: "long"` を `ja-JP` ロケールで使用すると `9月` 形式になる。
- 外部ライブラリ（dayjs/date-fns 等）は不要。ゼロコスト。

## 維持の仕組み

守り手: TypeScript 型検査 (`renderCell: (row: T, rowKey: string) => ReactNode`)。`ImportTableRow` 型で `created_at: string | null` が保証されるため、型エラーで誤変更を検知できる。
