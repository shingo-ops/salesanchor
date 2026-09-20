# Recon: release/mobile-analysis-menu

## 目的
MobileShellに「解析管理」メニュー項目を追加する（isSuperAdmin条件）。
PR #3604 でDesktopShell.tsxは修正済み。モバイル側の対応。

## 既存ADR検索結果
- ADR-027: i18n強制（全UI文字列はt("key")経由）— 適用済み
- ADR-067: デザイントークン強制（色・余白はCSS token参照）— 本変更では色変更なし
- ADR-137: MobileShell/DesktopShell分離（ADR-140 PR-B）— 分離構造を前提に追加
- ADR-140: ハンバーガー+Drawer → 下部タブバー刷新
- ADR-144: UIガバナンス（生select/生input/自作タブ/色直値禁止）— 適用済み

## 調査ファイル一覧（file:line）

### 変更対象
- `frontend/src/components/MobileShell.tsx:35-37` — import節: `useSuperAdmin` hookなし → 追加
- `frontend/src/components/MobileShell.tsx:71-74` — hook呼び出し: `isSuperAdmin` 取得追加
- `frontend/src/components/MobileShell.tsx:156-177` — menuItems: `analysisRules` 項目追加

### 参照（変更なし）
- `frontend/src/components/DesktopShell.tsx:35` — `useSuperAdmin` import パターン
- `frontend/src/components/DesktopShell.tsx:110` — `isSuperAdmin` 取得パターン
- `frontend/src/components/DesktopShell.tsx:190-193` — `saasAdminItems` 定義パターン
- `frontend/src/hooks/useSuperAdmin.ts` — hook実装（変更なし）
- `frontend/src/constants/icons.tsx:244-267` — `NAV_ICONS.saasAdmin` (CommandLine)
- `frontend/src/locales/ja.json:262` — `"superAdminAnalysisRules": "解析管理"` — 既存
- frontend/src/locales/en.json:262 — `"superAdminAnalysisRules": "Analysis Management"` — 既存（パスは frontend/src/locales/en.json）

## 触らないファイル
- `frontend/src/locales/ja.json` / `en.json` — i18nキーは既に存在
- `frontend/src/hooks/useSuperAdmin.ts` — 変更不要
- `frontend/src/components/DesktopShell.tsx` — PR #3604 で修正済み
