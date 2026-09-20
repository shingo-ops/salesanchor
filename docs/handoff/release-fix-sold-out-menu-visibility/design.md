# design — fix-sold-out-menu-visibility

## 概要
サイドバー「解析管理」メニューのリンク先誤り修正 + MobileShell へのメニュー追加。

## 変更前後

### DesktopShell.tsx:191
```ts
// 変更前
{ to: "/super-admin/tcg-line-import",  labelKey: "nav.superAdminAnalysisRules" },

// 変更後
{ to: "/super-admin/analysis-rules",   labelKey: "nav.superAdminAnalysisRules" },
```

### MobileShell.tsx（追加）
```ts
// isSuperAdmin hook import 追加
import { useSuperAdmin } from "../hooks/useSuperAdmin";

// hook 呼び出し追加
const { isSuperAdmin } = useSuperAdmin();

// menuItems に SuperAdmin 項目追加（accountSettings の後）
...(isSuperAdmin
  ? [
      resolveItem(
        "superAdminAnalysisRules",
        "nav.superAdminAnalysisRules",
        <NAV_ICONS.saasAdmin size={ICON.base} aria-hidden="true" />,
        "/super-admin/analysis-rules",
      ),
    ]
  : []),
```

### routeTitles.ts（追加）
```ts
"/super-admin/analysis-rules":  "nav.superAdminAnalysisRules",
```

## 影響範囲

| 対象 | 影響 |
|------|------|
| DesktopShell.tsx | isSuperAdmin ユーザーのサイドバー「解析管理」クリック先が AnalysisRulesPage へ正しく遷移 |
| MobileShell.tsx | isSuperAdmin ユーザーのモバイルメニューに「解析管理」が表示される |
| routeTitles.ts | `/super-admin/analysis-rules` のページタイトルが正しく表示される |
| 非 SuperAdmin ユーザー | 影響なし（isSuperAdmin guard で保護） |

## 受入条件

| 基準 | 検証方法 |
|------|---------|
| デスクトップ: サイドバー「解析管理」クリック → `/super-admin/analysis-rules` へ遷移 | isSuperAdmin ユーザーでログイン→サイドバークリック→URLバー確認 |
| デスクトップ: 完売ルール管理画面（AnalysisRulesPage）が表示される | 遷移後に完売ルール一覧が描画されることを目視確認 |
| モバイル: 「…」メニューに「解析管理」項目が表示される | モバイル幅でログイン→…タップ→メニュー項目確認 |
| 非 SuperAdmin: 「解析管理」メニュー非表示 | 一般ユーザーでログイン→メニュー項目が存在しないことを確認 |
| ESLint: エラーゼロ | `npm run lint` で 0 errors |

## 外部事例

N/A — UIバグ修正（リンク先誤り・メニュー欠落）のため。既存パターン（saasAdminItems / useSuperAdmin / NAV_ICONS.saasAdmin）を踏襲。

## 守り手
- `useSuperAdmin` hook: `isSuperAdmin` が false のユーザーにはメニュー自体が描画されない
- App.tsx のルート定義側にも認可ガードが存在（AnalysisRulesPage の実装内）

## 戻し方
```bash
git revert <commit-sha>
```
影響範囲が3ファイル・UIのみのため、revert 一発で完全に元に戻る。
