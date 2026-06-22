# recon — codex-schedule-i18n-main

**仕事名**: codex-schedule-i18n-main  
**日付**: 2026-06-22  
**対象ADR**: ADR-027  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|---|---|
| `frontend/src/pages/schedule/ScheduleSettingsPage.tsx:1-11` | `schedule.css` を読み込み、設定ページのレイアウトが正本の2カラム構成に乗る前提を確認 |
| `frontend/src/pages/admin/DiscordConfigPage.tsx:66-68` | チケット設定の初期ウェルカム文言が `t("discordTicketConfig.welcomeTemplateDefault")` に切り替わっている |
| `frontend/src/pages/admin/DiscordConfigPage.tsx:444-459` | ウェルカムメッセージ欄が i18n キー経由のラベル/placeholder/hint で描画される |
| `frontend/src/locales/ja.json:2599-2614` | `discordTicketConfig.welcomeTemplateDefault` を日本語 locale に追加済み |
| `frontend/src/locales/en.json:2599-2614` | `discordTicketConfig.welcomeTemplateDefault` を英語 locale に追加済み |
| `frontend/scripts/check-i18n-dashboard-schedule.js:1-80` | dashboard / schedule / common / nav の literal `t()` を両 locale で照合する新規ガード |
| `frontend/package.json:25-43` | 新規 i18n ガードを `check:i18n-dashboard-schedule` と `check:all` に接続 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|---|---|---|
| 1 | dashboard の生キー表示が他ページへ波及していないか | `npm run check:i18n-dashboard-schedule` / `npm run build` 実行 | ✅ 解消済み |
| 2 | 設定ページの右ペインに「他のメンバー」が残っていないか | `Schedule Settings.dc.html` 正本とスクリーンショット突合 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

この修正は i18n キー欠落の再発防止と、Schedule Settings の表示崩れの是正を同時に含む。
