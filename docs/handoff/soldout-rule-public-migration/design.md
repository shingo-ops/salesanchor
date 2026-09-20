# design: analysis_rule 13テーブル publicスキーマ移行

## 目的

完売ルール（analysis_rule_*）テーブルをテナントスキーマから public スキーマに移行し、
マスタ系テーブル（products 等）と同様の SSOT（Single Source of Truth）構造にする。

これにより、アプリ画面・CSV 管理からの完売ルール CRUD が
テナント境界を超えて単一スキーマで運用できるようになる。

---

## recon / ADR 参照

- recon.md: `docs/handoff/soldout-rule-public-migration/recon.md`
- 前例ADR: ADR-090（products統一）, ADR-143（inventory public v2）, ADR-1001（TCG products→public）
- スキーマ強制ルール: ADR-072（テナントスキーマプレフィックス）
  - 今回は analysis_rule を public に「昇格」させるため ADR-072 の例外に該当
  - extraction_jobs / extraction_items / source_messages はテナントスキーマのまま維持

---

## 変更前後の比較

| 項目 | 変更前 | 変更後 |
|------|-------|-------|
| テーブル所在 | tenant_001.analysis_* / tenant_004.analysis_* | public.analysis_* |
| バックエンドSQL | `{TCG_SCHEMA}.analysis_*` | `public.analysis_*` |
| cross-schema FK | テナント内FK + source_messages FK | public内FK + source_message_id は UUID型のみ保持（FK制約なし） |
| テナントID列 | なし（元々なし） | なし（productsパターン踏襲） |
| データseed | sold_out / date_format 2行（tenant_001のみ） | なし（テーブルの有無のみ） |
| 冪等性 | CREATE TABLE IF NOT EXISTS + ON CONFLICT DO NOTHING | CREATE TABLE IF NOT EXISTS（INSERTなし） |

---

## 成功基準と検証方法

| 基準 | 検証方法 |
|------|---------|
| マイグレーションSQL が冪等で2回実行しても差分なし | `psql -f migration.sql` を2回実行してエラー0を確認 |
| `public.analysis_policies` テーブルが存在する | `\d public.analysis_policies` で定義を確認 |
| バックエンドの Python 構文エラーなし | `python -c "import ast; ast.parse(open(...).read()); print('OK')"` |
| 既存の extraction_jobs / extraction_items / source_messages 参照が変更されていない | `grep -n "TCG_SCHEMA.*extraction" backend/app/tasks/tcg_analysis_rule.py` |
| item_corrections_svc.py が public.analysis_rule_run_results を参照 | `grep "public.analysis_rule_run_results" backend/app/services/item_corrections_svc.py` |
| tcg_distribution_svc.py が public.analysis_rule_runs を参照 | `grep "public.analysis_rule_runs" backend/app/services/tcg_distribution_svc.py` |

---

## 外部事例欄

該当なし（内部スキーマ移行のため）

---

## 守り手

- **migration-guard CI**: `migrations/` の変更があると自動でCIゲートが起動
- **IF NOT EXISTS 冪等性**: 全DDLに `CREATE TABLE IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS` を付与
- **cross-schema FK 省略**: `source_messages` / `extraction_items` への FK は意図的に省略（テナントスキーマ参照回避）
- **データINSERTなし**: migration はテーブルの有無のみ管理。seed データは別途アプリ側または後続migrationで投入

---

## 影響範囲

### 変更するファイル（4ファイル）
1. `backend/app/services/tcg_analysis_rule_svc.py`: SQL 38箇所（analysis_* のみ）
2. `backend/app/tasks/tcg_analysis_rule.py`: SQL 10箇所（analysis_* のみ）
3. `backend/app/services/item_corrections_svc.py`: 行82（analysis_rule_run_results）
4. `backend/app/services/tcg_distribution_svc.py`: 行725（analysis_rule_runs）

### 変更しないもの
- `{TCG_SCHEMA}.extraction_jobs` / `extraction_items` / `source_messages`: テナントスキーマのまま
- `tenant_001` / `tenant_004` の既存 analysis_* テーブル: 削除しない（並行存在）
- フロントエンド: API インターフェースは変わらないため変更不要

---

## ロールバック方法

1. バックエンドファイルを `public.analysis_` → `{TCG_SCHEMA}.analysis_` に戻す（git revert）
2. public スキーマのテーブルは DROP しない（データが入っていなければ無害）
3. 本番適用前であれば PR を close して release ブランチを破棄するだけでよい
