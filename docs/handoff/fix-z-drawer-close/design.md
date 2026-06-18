# Phase 3 設計 — fix-z-drawer-close

**対象ADR**: ADR-137
**recon**: docs/handoff/fix-z-drawer-close/recon.md
**日付**: 2026-06-17
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

該当なし：z-index 1段階引き上げは1行の数値変更。外部事例を参照するまでもなく、スタック順（drawer > avatar > backdrop）という業界標準の原則に従うだけ。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| --z-drawer(301) > --z-avatar(300) となる | `frontend/src/tokens.css:126-127` の値確認 |
| user-drawer-close ボタンを直接クリックできる | Playwright: `desktop-shell.spec.ts:59` |
| mobile でも user-drawer-close を直接クリックできる | Playwright: `mobile-shell.spec.ts:131` |
| build 後に width<= 構文が 0 件 | `npm run build` PASS |
| 既存 KGI-1〜5 非退行 | Playwright 16/16 PASS |

---

## 技術 How・KPI

- 変更箇所: `frontend/src/tokens.css` の `--z-drawer` を 299 → 301
- KPI: E2E 16/16 PASS、check:all EXIT:0、width<= 0件
- 技術選択: トークン1行変更のみ。MobileShell/DesktopShell 構造変更なし

---

## 弊害・トレードオフ

- --z-drawer(301) > --z-avatar(300) となるため、drawer が avatar-btn の前面に来る
- 副作用: avatar-btn がdrawer オープン時に隠れる可能性があるが、avatar-btn は drawer を開くためのボタンであり、drawer が開いている間は不要なため問題なし
- --z-modal(400) には届かないため modal との競合なし
