# Recon: ルールテーブル統一 / conditions UI v2

## 調査日: 2026-09-25

## 概要
本 recon は「状態ルール UI 改善 + condition_def_id / unit_id プルダウン追加」（design-v2.md）に対応する調査記録。
前便 design.md（match_type/effect 追加）の recon を引き継ぎ、v2 対象ファイルを追記・更新する。

---

## 主要ファイル一覧

| 項目 | ファイル:行 |
|------|-----------|
| `resolve_condition_v2` 定義 | `backend/app/services/tcg_analyzer_svc.py:787` |
| `load_condition_entries` 定義 | `backend/app/services/tcg_analyzer_svc.py:646` |
| `ConditionsMasterPanel` コンポーネント定義 | `frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:85` |
| `condition_definitions` テーブル作成 migration | `migrations/20260921_090000_create_condition_definitions.sql:27` |
| `line_conditions` → `conditions` VIEW 作成（初出） | `migrations/20260922_080000_rename_line_analysis_tables.sql:83` |
| `conditions` VIEW 再作成（本便対象 migration） | `migrations/20260925_020000_conditions_add_def_unit_note.sql:43` |
| `ConditionBase` スキーマ | `backend/app/schemas/condition.py:12` |
| `CentralConditionBase` スキーマ | `backend/app/schemas/central_masters.py:465` |
| テナント向け conditions ルーター | `backend/app/routers/conditions.py:126` |
| SaaS 管理向け conditions ルーター | `backend/app/routers/super_admin_conditions.py:127` |

---

## line_conditions / conditions VIEW の関係

- **実テーブル**: `public.line_conditions`（LINE 解析パイプライン用 状態マスタ）
- **後方互換 VIEW**: `public.conditions`（`TABLE public.line_conditions` の alias）
- VIEW 初作成: `migrations/20260922_080000_rename_line_analysis_tables.sql:83`
  - `public.conditions` を `public.line_conditions` にリネーム後、`CREATE VIEW public.conditions AS TABLE public.line_conditions` を生成
- 本便での再作成: `migrations/20260925_020000_conditions_add_def_unit_note.sql:43`
  - `unit_id` / `condition_def_id` / `note` 追加後に `CREATE OR REPLACE VIEW public.conditions AS TABLE public.line_conditions` で更新

---

## ADR 検索結果

- `git grep -i docs/adr/` + `docs/adr/FEATURE-INDEX.md` を確認
- conditions テーブル固有の ADR なし
- 関連する上位 ADR: ADR-104（解析パイプライン）, ADR-109（共用マスタ）, ADR-120（SSoT 整備）
- match_type/effect パターンは tcg_status_master の実装から横展開（ADR 記録なし）

---

## 変更前後の比較

### line_conditions テーブル（変更前）
- unit_id, condition_def_id, note カラムなし
- `conditions` VIEW は既存カラムのみ反映

### line_conditions テーブル（変更後）
- `condition_def_id INTEGER REFERENCES public.condition_definitions(id) ON DELETE SET NULL`
- `unit_id INTEGER REFERENCES public.units(id) ON DELETE SET NULL`
- `note TEXT NOT NULL DEFAULT ''`
- `conditions` VIEW を `CREATE OR REPLACE VIEW` で更新

### ConditionsMasterPanel（変更前）
- code / canonical / app_kubun / priority / match_type / effect / search_kw / exclude_kw / is_active / 別名管理ボタン

### ConditionsMasterPanel（変更後）
- 質問形式ラベル + condition_def_id プルダウン + unit_id プルダウン + 出力プレビュー
- code / canonical / 別名管理ボタン 非表示
