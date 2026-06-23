# recon — schedule rollback to #2443

**仕事名**: schedule rollback to #2443  
**日付**: 2026-06-22  
**対象ADR**: ADR-136  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/pages/schedule/SchedulePage.tsx:1` | schedule page の戻し対象を確認 |
| `frontend/src/pages/schedule/ScheduleSettingsPage.tsx:1` | settings page の戻し対象を確認 |
| `frontend/src/locales/ja.json:2486` | schedule 文言の戻し対象を確認 |
| `frontend/src/locales/en.json:2340` | schedule 文言の戻し対象を確認 |
| `backend/app/routers/calendar.py:1` | schedule API の戻し対象を確認 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | なし | 該当なし | ✅ 解消済み |

**未解決ゼロ確認**: 該当なし

---

## 補足

schedule 系のみを `#2443` 状態へ戻すための rollback 記録。
