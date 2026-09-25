# Design: conditions テーブル match_type/effect 追加

## KGI
- conditions テーブルが tcg_status_master と同じルールパターン（match_type/effect）を持つ
- 既存の KEYWORD 動作を完全維持（後方互換）

## recon 参照
- `backend/app/services/tcg_analyzer_svc.py`: `load_condition_entries` / `resolve_condition_v2` / `_match_status_pattern`
- `backend/app/routers/conditions.py`: CRUD エンドポイント
- `backend/app/routers/super_admin_conditions.py`: SaaS 管理 CRUD + CSV
- `backend/app/schemas/condition.py`: ConditionBase / ConditionUpdate
- `backend/app/schemas/central_masters.py`: CentralConditionBase / CentralConditionUpdate
- ADR 検索: ADR-104/109/120 確認、conditions 固有の ADR なし

## 変更概要

| ファイル | 変更 |
|---|---|
| migrations/20260925_010000_conditions_add_match_type.sql | ALTER TABLE ADD COLUMN（additive-only） |
| backend/app/services/tcg_analyzer_svc.py | load_condition_entries に match_type/effect 取得追加、resolve_condition_v2 に KEYWORD/REGEX/LITERAL/DEFAULT 分岐 |
| backend/app/schemas/central_masters.py | CentralConditionBase/Update に match_type/effect フィールド追加 |
| backend/app/schemas/condition.py | ConditionBase/Update に match_type/effect フィールド追加 |
| backend/app/routers/super_admin_conditions.py | CRUD + CSV で match_type/effect を扱う |
| backend/app/routers/conditions.py | CRUD で match_type/effect を扱う |
| frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx | match_type/effect セレクタ追加 |
| frontend/src/locales/ja.json | 翻訳キー 8 件追加 |
| frontend/src/locales/en.json | 翻訳キー 8 件追加 |
| scripts/run_all_migrations.sh | migration 登録 |

## match_type 定義

| 値 | 意味 |
|---|---|
| KEYWORD | 既存 match_keyword 動作（デフォルト・後方互換） |
| REGEX | 正規表現マッチング（_match_status_pattern 経由） |
| LITERAL | 完全一致（_match_status_pattern 経由） |
| DEFAULT | 無条件ヒット（_match_status_pattern 経由） |

## effect 定義

| 値 | 意味 |
|---|---|
| OUTPUT | ヒット時に状態名を出力（デフォルト） |
| EXCLUDE | ヒット時に除外 |

## 検証方法

| 基準 | 検証方法 |
|---|---|
| 既存 KEYWORD 動作維持 | test_condition_vocab.py 全 PASS |
| migration が idempotent | IF NOT EXISTS / ADD COLUMN IF NOT EXISTS で冪等 |
| REGEX 不正パターン拒否 | super_admin_conditions.py で re.compile テスト |
| i18n キー同一 | ja.json 4179 = en.json 4179 |

## 外部・過去事例の参照と我々への応用
該当なし（内部テーブル構造の統一であり、外部ライブラリ・サービス非依存）。
tcg_status_master の match_type/effect パターンを conditions に横展開した内部リファクタリング。

## 維持の仕組み
守り手: REGEX 保存時に `re.compile(pattern)` でバリデーション（super_admin_conditions.py）、DEFAULT `'KEYWORD'` による既存データ保護、resolve_condition_v2 の KEYWORD パス分岐

- REGEX 保存時: `re.compile(pattern)` でバリデーション（super_admin_conditions.py）
- DEFAULT: `'KEYWORD'` で既存データ保護
- resolve_condition_v2: KEYWORD パスは既存 `match_keyword` を完全維持
