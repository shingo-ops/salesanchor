# recon — fix-z-drawer-close

**仕事名**: fix-z-drawer-close
**日付**: 2026-06-17
**対象ADR**: ADR-137
**担当**: architect

---

## 背景

PR-R2-D（#2271）残タスク。`avatar-btn`（z-index:300）が `user-drawer`（z-index:299）の前面に重なるため、`user-drawer-close` ボタンを直接クリックできない。

---

## file:line 引用表

| 引用先 | 確認内容 |
|--------|---------|
| `frontend/src/tokens.css:126` | --z-drawer: 301 — 変更後の値（旧:299）|
| `frontend/src/tokens.css:127` | --z-avatar: 300 — avatar-btn の z-index |
| `frontend/src/tokens.css:180` | --avatar-zone-z: var(--z-avatar) — avatar-btn が参照するエイリアス |
| `frontend/src/topbar.css:125` | .avatar-btn の z-index: var(--avatar-zone-z)、position:fixed |
| `frontend/src/topbar.css:160` | .user-drawer の z-index: var(--z-drawer)、drawer のスタック位置 |
| `frontend/tests-e2e/desktop-shell.spec.ts:59` | 修正後: user-drawer-close 直接クリックテスト |
| `frontend/tests-e2e/mobile-shell.spec.ts:131` | 追加: mobile avatar → user-drawer-close 直接クリックテスト |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | --z-drawer を何に設定するべきか | --z-avatar(300) + 1 = 301 で drawer > avatar かつ --z-modal(400) より下 | ✅ 解消済み |
| 2 | mobile では問題が発生しているか | mobile-topbar-avatar は in-flow（position:fixed 不使用）のため z-index 競合なし | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
