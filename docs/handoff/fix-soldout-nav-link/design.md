# 解析管理ナビ リンク先修正 — 設計書

## 変更内容

### DesktopShell.tsx（saasAdminItems）
| 項目 | 変更前 | 変更後 |
|------|--------|--------|
| `to` プロパティ | `/super-admin/tcg-line-import` | `/super-admin/analysis-rules` |
| `labelKey` | `nav.superAdminAnalysisRules` | `nav.superAdminAnalysisRules`（変更なし） |

### routeTitles.ts
| 項目 | 変更前 | 変更後 |
|------|--------|--------|
| `/super-admin/analysis-rules` エントリ | 未登録 | `"nav.superAdminAnalysisRules"` を追加 |

## 検証方法

| 基準 | 検証方法 |
|------|---------|
| 「解析管理」メニュークリックで `/super-admin/analysis-rules` に遷移すること | ブラウザで super_admin アカウントでログインし、ナビ「解析管理」をクリックして URL を確認 |
| サイドバー「完売ルール」タブで SoldOutRulesPanel が表示されること | AnalysisRulesPage 上のサイドバー「完売ルール」をクリックして表示確認 |
| サイドバー「取り込み」クリックで `/super-admin/tcg-line-import` にリダイレクトされること | AnalysisRulesPage 上のサイドバー「取り込み」をクリックしてリダイレクト確認 |
| TypeScript 型エラーが発生しないこと | `npx tsc --noEmit` が 0 exit で完了 |

## 外部事例・過去事例の参照と我々への応用
該当なし（UIナビリンク修正のため外部事例不要）

## 維持の仕組み
- `NavItem` 型を使用しているため、型が変わればコンパイルエラーで検知可能
- routeTitles.ts のエントリはページ追加・削除時にメンテが必要（コメント記載済み）

## 守り手
- 既存の `AnalysisRulesSidebar` サブナビ（sold-out・import 等のタブ遷移）は変更なし
- `NavItem` 型を既存のまま使用（型追加・変更なし）
- i18n キー `nav.superAdminAnalysisRules` は ja.json/en.json に既存（新規追加なし）

## 影響範囲
- LINE取り込み: AnalysisRulesPage サイドバー経由で 1 クリックでアクセス可能（機能喪失なし）
- 完売ルール: サイドバーの「完売ルール」タブから直接アクセス可能に
- 変更ファイル数: 2（DesktopShell.tsx・routeTitles.ts）
- 戻し方: `to` を `/super-admin/tcg-line-import` に戻し、routeTitles の行を削除
