# recon — schedule-8issues-fix

**仕事名**: スケジュールページ 8件本番バグ修正  
**日付**: 2026-06-21  
**対象ADR**: ADR-027  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/lib/api.ts:49-57` | `getIdToken()` が `Promise.race` で保護されていなかった（#8 根本原因） |
| `frontend/src/lib/api.ts:66-125` | `request()` 関数 — `getAuthHeaders()` が reject すると async 関数が reject する |
| `frontend/src/pages/schedule/SchedulePageImpl.tsx:847` | `Promise.allSettled` で2本の API 呼び出しをラップ — allSettled は絶対に reject しない |
| `frontend/src/pages/schedule/SchedulePageImpl.tsx:866-869` | `finally { if (!cancelled) setLoading(false); }` — 全経路で必達 |
| `frontend/src/pages/schedule/SchedulePageImpl.tsx:1015` | `<h1 className="schedule-shell__title">{t("schedule.title")}</h1>` — タイトル残存確認（#5） |
| `frontend/src/pages/schedule.css:22` | `.schedule-page` に padding なし（#1 根本原因） |
| `frontend/src/pages/schedule.css:42` | 修正後: `padding: var(--page-padding-y) var(--page-padding-x)` 追加 |
| `frontend/src/pages/schedule.css:51` | 修正後: `padding-right: var(--page-header-avatar-clearance)` 追加（#7） |
| `frontend/src/tokens.css:181-182` | `--page-padding-x: var(--space-6)` / `--page-padding-y: 10px` 定義済み |
| `frontend/src/tokens.css:189-194` | `--avatar-zone-right` / `--avatar-zone-width` / `--page-header-avatar-clearance` 定義済み |
| `frontend/src/tokens.css:84-85` | `--space-10px` / `--space-14px` 定義済み |
| `frontend/src/tokens.css:362-363` | `--schedule-rail-bg` / `--schedule-rail-border` 定義済み |
| `frontend/src/locales/ja.json:63` | `common.notAuthenticated` の直下に `authTimeout` を追加（ADR-027準拠） |
| `frontend/src/locales/en.json:63` | 同上（ja/en 同一キー必須） |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | `Promise.allSettled` 内の reject が `finally` に到達するか | `SchedulePageImpl.tsx:847` の allSettled は常に resolve → `finally` 必達を確認 | ✅ 解消済み |
| 2 | `--page-header-avatar-clearance` の未定義リスク | `tokens.css:194` に既存定義確認済み、新規追加ゼロ | ✅ 解消済み |
| 3 | #4 カレンダーラベルの空表示はコード変更要否 | `calendars.config.ts` は `calendar.label` を直接参照、stale bundle 問題のみ → deploy で解消 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
