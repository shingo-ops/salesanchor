# recon — schedule-nowrap-sticky

**仕事名**: schedule-nowrap-sticky
**日付**: 2026-06-21
**対象ADR**: ADR-067
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/pages/schedule.css:37` | `.schedule-page { display: flex; flex-direction: column; min-height: 0 }` — 高さ制約なし（height: 100% 追加で修正） |
| `frontend/src/pages/schedule.css:174` | `.schedule-shell__content { display: grid; align-items: start }` — stretch に変更で main が高さ充填 |
| `frontend/src/pages/schedule.css:350` | `.schedule-main__surface { display: flex; flex-direction: column; min-height: 0 }` — flex: 1 追加で充填 |
| `frontend/src/pages/schedule.css:520` | `.schedule-grid__days { display: grid; grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr)) }` — 1024px で 137px < 160px → 折り返しバグの根本原因 |
| `frontend/src/pages/schedule.css:398` | `.schedule-grid__header { display: grid }` — sticky 化対象 |
| `frontend/src/pages/schedule.css:500` | `.schedule-grid__allday-row { min-height: var(--schedule-allday-row-h) }` — sticky 化対象 |
| `frontend/src/pages-layout.css:62` | `.page-layout-header { flex-shrink: 0 }` — sticky 化対象（全ページ共通） |
| `frontend/src/topbar.css:7` | `.app-topbar { position: sticky; top: 0; z-index: var(--z-topbar) }` — z-index 100、高さ var(--topbar-height) = 56px |
| `frontend/src/sidebar.css:273` | `.app-body { flex: 1; display: flex; flex-direction: column; overflow: hidden }` — app-content の親 |
| `frontend/src/topbar.css:97` | `.app-content { flex: 1; overflow-y: auto }` — ページレベルスクロールコンテナ |
| `frontend/src/pages/schedule/SchedulePageImpl.tsx:1098` | `<div ref={gridScrollRef} className="schedule-grid__viewport">` — 現状は overflow 未設定 |
| `frontend/src/tokens.css:340` | `--schedule-mini-size: 46px` — day head 円形サイズ |
| `frontend/src/tokens.css:352` | `--schedule-row-height: 48px` |
| `frontend/src/tokens.css:154` | `--topbar-height: 56px` |
| `frontend/src/tokens.css:122` | `--z-topbar: 100` |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | `--schedule-day-head-h` の正確な値 | tokens.css から計算: 8+18+2+46+8 = 82px | ✅ 解消済み |
| 2 | `.schedule-grid__viewport` に overflow がなぜないか | SchedulePageImpl.tsx:1098 確認、CSS ルール未定義 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み

---
