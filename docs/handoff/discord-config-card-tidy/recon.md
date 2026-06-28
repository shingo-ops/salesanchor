# recon — Discord設定ページ Card整理（見やすさ改善）

**仕事名**: discord-config-card-tidy
**日付**: 2026-06-28
**対象ADR**: ADR-067
**担当**: architect / Planner

---

## 調査1: 整理対象ページ本体
- `frontend/src/pages/admin/DiscordConfigPage.tsx:49` — DiscordConfigPage 本体（default export）
- `frontend/src/pages/admin/DiscordConfigPage.tsx:251` — return 直下 `<PageLayout navKey="nav.discordConfig">` ／ `<div className="max-w-lg space-y-10">`
- `frontend/src/pages/admin/DiscordConfigPage.tsx:16` — 共通部品は PageLayout のみ。Card 未使用（全570行）

## 調査2: 現状のグループ構造（箱が無く section のみ）
- `frontend/src/pages/admin/DiscordConfigPage.tsx:254` — Guild ID グループ（見出し無し・`<section className="space-y-6">`）
- `frontend/src/pages/admin/DiscordConfigPage.tsx:284` — 自動セットアップ `<section className="space-y-4">`（タイトルは `<p>`）
- `frontend/src/pages/admin/DiscordConfigPage.tsx:377` — `<hr className="border-token-border" />`（唯一の仕切り）
- `frontend/src/pages/admin/DiscordConfigPage.tsx:379` — チケット機能設定 `<section className="space-y-6">`

## 調査3: 保存系（各 section 内に正しく配置済み）
- `frontend/src/pages/admin/DiscordConfigPage.tsx:114` — handleSave（guild_id 保存）
- `frontend/src/pages/admin/DiscordConfigPage.tsx:278` — Guild ID 保存ボタン
- `frontend/src/pages/admin/DiscordConfigPage.tsx:134` — handleTicketSave（チケット設定保存）
- `frontend/src/pages/admin/DiscordConfigPage.tsx:541` — チケット保存ボタン

## 調査4: Card 金型の実体と実画面採用
- `frontend/src/components/Card.tsx:27` — Card（variant: container/interactive/metric）
- `frontend/src/components/Card.tsx:34` — className を受け取り可（space-y を直接付与できる）
- `frontend/src/pages/commissions/CommissionsPage.tsx:135` — 実画面で `<Card variant="container">` 採用済み（実装の手本）
- `frontend/src/pages/sales/SalesPage.tsx:91` — 実画面で `<Card variant="metric">` 採用済み

## 調査5: Task 1E は停止状態（割り込みリスク無し）
- `docs/handoff/mobile-responsive/recon.md:115` — Task 1E 受け入れ基準「定義なし」
- `docs/handoff/mobile-responsive/recon.md:118` — Card「Preview専用」は「コメントのみ・技術的依存なし」
- `docs/CC_UI_GOVERNANCE.md:9` — 生タグより金型優先（Card採用はガバナンス順守）
