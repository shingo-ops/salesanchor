# recon — schedule-settings-i18n-fix

**仕事名**: schedule-settings-i18n-fix
**日付**: 2026-06-22
**対象ADR**: ADR-027
**担当**: Hikky-dev

---

## 概要

`/schedule/settings` ページタイトルが生キー `"nav.scheduleSettings"` として表示されるバグを調査。

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/pages/schedule/ScheduleSettingsPage.tsx:110` | 権限なしパス: `navKey="nav.scheduleSettings"` を PageLayout に渡している |
| `frontend/src/pages/schedule/ScheduleSettingsPage.tsx:119` | メインレンダリングパス: 同じく `navKey="nav.scheduleSettings"` |
| `frontend/src/config/routeTitles.ts:36` | `/schedule/settings` → `"nav.scheduleSettings"` のブラウザタブタイトルマッピング |
| `frontend/src/locales/ja.json:120` | `nav.schedule: "スケジュール"` が存在するが `nav.scheduleSettings` は欠落 |
| `frontend/src/locales/en.json:120` | 同上（`nav.schedule: "Schedule"` のみ・`scheduleSettings` 欠落） |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | `#2472` revert で旧 ScheduleSettingsPage（259行版）が復元されたが、`nav.scheduleSettings` キーが追加されていたか | locales git log で確認 | ✅ 解消済み（追加なし＝今回のバグ原因） |

**未解決ゼロ確認**: 全て解消済み
