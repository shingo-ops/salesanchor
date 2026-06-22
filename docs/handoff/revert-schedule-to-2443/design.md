# Phase 3 設計 — schedule rollback to #2443

**対象ADR**: ADR-136  
**recon**: docs/handoff/revert-schedule-to-2443/recon.md  
**日付**: 2026-06-22  
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 該当なし。今回の変更は既存の schedule UI / locale / backend を `#2443` へ戻す hotfix で、外部事例の追加設計を必要としない。

---

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| schedule 系ファイルが `#2443` の内容に戻っている | `git diff 8bf87e8...` で一致確認 |
| i18n の schedule キーが欠落していない | `npm run check:i18n-dashboard-schedule` |
| frontend build が通る | `npm run build` |

