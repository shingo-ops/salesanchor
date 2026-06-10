# design — 見た目改善（A-2）: オーナーロール色修正

**仕事名**: 見た目改善（A-2）役割バッジ色修正  
**日付**: 2026-06-11  
**対象ADR**: ADR-067  
**recon**: docs/handoff/ui-consistency-a/recon.md

---

## 概要

`statusPresentation.ts` で `danger`（失敗・エラー・期限超過）に予約されている `#ef4444`（赤）が
オーナーロールのバッジ色に使われていた意味的誤用を修正する。

インディゴ `#6366f1` は権限レベルを表す意味ニュートラルな色であり、danger 予約色と衝突しない。

---

## 設計方針

| 項目 | 内容 |
|------|------|
| 変更箇所 | `backend/app/services/tenant.py:44` の `#ef4444` → `#6366f1` |
| 既存テナント対応 | 冪等 SQL マイグレーション（`migrations/20260611_010000_fix_owner_role_color.sql`） |
| WHERE 条件 | `is_system=TRUE AND color='#ef4444' AND priority=1000`（3条件 AND） |
| 根拠 | `is_system=TRUE` 単独では不足（migration 021/023 でシステム管理者にも付与）。`priority=1000` はオーナー固有 |

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `tenant.py` の seed 色が `#6366f1` | `grep "ef4444" backend/app/services/tenant.py` → 0件 |
| SQL WHERE が3条件 AND で絞り込む | `migrations/20260611_010000_fix_owner_role_color.sql` 確認 |
| 冪等（2回流して2回目が no-op） | NOTICE ログで `0 行を更新` 確認 |
| `{schema}` プレースホルダを含まない | `grep '{schema}' migrations/20260611_010000_fix_owner_role_color.sql` → 0件 |
| CI 全緑 | GitHub Actions |

---

## 外部・過去事例の参照と我々への応用

| 事例 | 概要 | 我々への応用 |
|------|------|------------|
| Material Design / Tailwind CSS カラーセマンティクス | `red` / `danger` を「エラー・警告」専用色として予約し、権限レベルには `indigo` / `violet` を推奨 | `statusPresentation.ts:45` の設計判断と一致。インディゴ採用の根拠を補強 |
| WCAG 2.1 色だけで意味を伝えない原則 | 色はステータスの補助であり、意味の唯一の手段にしてはならない | 今回は color 列（DB）のみで表示しているが、ロール名も併記されているため基準を満たしている |

---

## 関連ファイル

- `backend/app/services/tenant.py:44` — DEFAULT_ROLES オーナー color
- `migrations/20260611_010000_fix_owner_role_color.sql` — 既存テナント冪等 UPDATE
- `scripts/run_all_migrations.sh` — TOTAL=124 に追加済み
- `frontend/src/utils/statusPresentation.ts:45` — danger 予約色の根拠
- `frontend/src/pages/roles/RolesPage.tsx:370` — バッジ表示箇所
