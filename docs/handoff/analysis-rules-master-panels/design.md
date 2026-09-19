# 設計: analysis-rules-master-panels

## 目的
解析管理ページ（/super-admin/analysis-rules）の左サイドバーに「マスタ管理」グループを追加し、商品マスタ・仕入元マスタへアクセスできるようにする。既存のスタンドアロンルートは残置。

## 変更方針

### パネル抽出パターン
- TcgProductMasterPage / SupplierMasterPage のロジック・UI をそのまま流用
- 除去: PageLayout ラッパー、useSuperAdmin ガード（親の AnalysisRulesPage が既にチェック済み）
- 移動: ヘッダーアクションボタン群を ContentToolbar right スロットに配置

### サイドバー拡張
- AnalysisRulesSidebarKey の型ユニオンに 2 キー追加
- 第3の hub-subnav-section としてマスタ管理グループを末尾に追加

### ナビゲーション整理
- DesktopShell の saasAdminItems から /super-admin/supplier-master と /super-admin/tcg-product-master を削除
- analysis-rules 経由でアクセス可能になるため、サイドバー上の重複エントリを除去

## KGI / KPI（PO が画面・出力で○×を一義に判定できる粒度）

| 基準 | 検証方法 |
|------|---------|
| /super-admin/analysis-rules を開いたとき左サイドバーに「マスタ管理」グループが表示される | ブラウザで画面確認 |
| 「商品マスタ」をクリックすると右エリアに商品一覧テーブルが表示される | ブラウザで画面確認 |
| 「仕入元マスタ」をクリックすると右エリアに仕入元一覧テーブルが表示される | ブラウザで画面確認 |
| DesktopShell のサイドバーに supplier-master / tcg-product-master のリンクが表示されない | ブラウザで画面確認 |
| /super-admin/supplier-master（スタンドアロン）が引き続き動作する | URL直打ちで確認 |
| /super-admin/tcg-product-master（スタンドアロン）が引き続き動作する | URL直打ちで確認 |
| npm run lint 0 errors | CI確認 |
| npm run check:all 全項目 exit 0 | CI確認 |

## 弊害・守り手
- DesktopShell のリンク削除により既存ブックマークが切れる可能性あり → スタンドアロンルートは維持するため直打ちは引き続き動作
- SupplierMasterPanel から authLoading/isSuperAdmin ガードを除去 → 親 AnalysisRulesPage が同等チェックを実施済みのため問題なし

## 外部・過去事例の参照と我々への応用

- 既存の `frontend/src/pages/super-admin/components/SoldOutRulesPanel.tsx` および `frontend/src/pages/super-admin/components/DateRulesPanel.tsx` が同パターン（hub-content 内パネル・PageLayout なし・useSuperAdmin ガードなし）の先例として機能。同じ設計を踏襲した。
- AnalysisRulesPage 内の AccuracyManagementPanel（同ファイル内インライン定義）も先例。

## 維持の仕組み

守り手: AnalysisRulesSidebarKey 型ユニオン（`frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx`） — 新規キーを追加した際にパネルの条件レンダリングが漏れると TypeScript が型エラーを出す。lint CI（0 errors 必須）が守り手として機能。

## 戻し方
- DesktopShell の 2 項目を元に戻す（git revert または手動編集）
- AnalysisRulesPage / AnalysisRulesSidebar から追加箇所を削除
- 2 新規ファイルを削除
