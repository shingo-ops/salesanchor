# 設計 — schedule-settings-i18n-fix

**対象ADR**: ADR-027
**recon**: docs/handoff/schedule-settings-i18n-fix/recon.md
**日付**: 2026-06-22
**担当**: Hikky-dev

---

## 外部・過去事例の参照と我々への応用

該当なし：i18next の missing key フォールバック（キーをそのまま表示）は公知の既知挙動。外部事例参照不要。修正は locales への 1 キー追加のみで完結する。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `ja.json` の `nav.scheduleSettings` が `"スケジュール設定"` | `git diff origin/main -- frontend/src/locales/ja.json` で +1行確認 |
| `en.json` の `nav.scheduleSettings` が `"Schedule Settings"` | `git diff origin/main -- frontend/src/locales/en.json` で +1行確認 |
| `/schedule/settings` のページタイトルが生キー表示にならない | 本番デプロイ後にページ目視確認 |
| 変更ファイルが locales 2件 + active-work.md のみ | `git diff --stat origin/main...HEAD` で 3ファイルのみを確認 |

---

## 技術 How

i18next は存在しないキーを受け取ると、そのキー文字列をそのまま表示する（デフォルト fallback）。
`#2472` revert で復元された `ScheduleSettingsPage.tsx`（259行版）が `navKey="nav.scheduleSettings"` を参照しているが、両ロケールにそのキーが存在しない。
修正: `nav.schedule` の直下に `nav.scheduleSettings` を追加する（ADR-027 準拠・`t()` 経由で自動適用）。

---

## 弊害・トレードオフ

- 変更は locales のみ。TSX / routeTitles.ts は触らない。
- 他ページへの波及なし。

---

## 継続

- デプロイ後に `/schedule/settings` でタイトル表示を目視確認。
