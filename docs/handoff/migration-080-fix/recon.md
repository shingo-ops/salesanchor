# recon — migration-080-fix

**仕事名**: migration-080-fix
**日付**: 2026-06-22
**対象ADR**: ADR-135
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `scripts/run_all_migrations.sh:152` | `run_py scripts/migrate_20260620_080000_calendar_category_backfill.py` — 参照が存在するが git 未追跡のため VPS で file not found |
| `scripts/migrate_20260620_080000_calendar_category_backfill.py:1` | 新規追跡対象ファイル（ローカルにあり、git add 漏れ） |
| `backend/app/services/calendar_category_utils.py:1` | backfill で import する依存モジュール（git 追跡済み） |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | backfill が冪等かどうか | スクリプト内 WHERE category IS NULL を確認 | ✅ 解消済み |
| 2 | `calendar_category_utils` が追跡済みか | `git ls-files backend/app/services/calendar_category_utils.py` で確認 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み

---
