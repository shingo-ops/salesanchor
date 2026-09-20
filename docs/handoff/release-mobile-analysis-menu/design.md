# Design: release/mobile-analysis-menu

## recon参照
docs/handoff/release-mobile-analysis-menu/recon.md

## ADR参照
- ADR-027: i18n強制 (`docs/adr/ADR-027-ui-internationalization.md`)
  - 追加テキスト: `t("nav.superAdminAnalysisRules")` — ja.json/en.json 既存キーを使用
- ADR-144: UIガバナンス (`docs/CC_UI_GOVERNANCE.md`)
  - 既存 `NavItemList` / `resolveItem` ユーティリティを使用（生input等は不使用）

## 変更概要
MobileShell.tsxのMoreSheetメニューに「解析管理」を追加する。
DesktopShell.tsxのsaasAdminItemsパターンを踏襲し、`isSuperAdmin=true`の場合のみ表示。

## 設計方針
1. `useSuperAdmin` hookをimportし `isSuperAdmin` を取得
2. `menuItems` 配列末尾（accountSettingsの後）に `isSuperAdmin` spread条件で追加
3. アイコン: `NAV_ICONS.saasAdmin`（CommandLine）— DesktopShellのSaaS管理者セクションと意味的に一致
4. パス: `/super-admin/analysis-rules`（DesktopShellと同一）
5. labelKey: `"nav.superAdminAnalysisRules"`（ja.json/en.json既存キー）

## 成功基準

| 基準 | 検証方法 |
|------|---------|
| isSuperAdmin=trueのモバイルユーザーが「解析管理」を見られる | MoreSheetを開き項目が表示される |
| isSuperAdmin=falseのユーザーに項目が表示されない | 一般ユーザーでMoreSheet確認 |
| `/super-admin/analysis-rules` にナビゲートされる | タップ後URLを確認 |
| lintエラーなし | `cd frontend && npm run lint` 成功 |
| DesktopShellの既存動作に影響なし | デスクトップ表示で目視確認 |

## 守り手
- `frontend/src/components/MobileShell.tsx` — 本変更の対象ファイル

## 外部事例
N/A（UIメニュー追加・既存hookとパターンの踏襲）

## 触るファイル
- `frontend/src/components/MobileShell.tsx` — メニュー項目追加
- `docs/handoff/release-mobile-analysis-menu/recon.md` — 調査記録
- `docs/handoff/release-mobile-analysis-menu/design.md` — 設計記録（本ファイル）

## 削除するファイル
なし
