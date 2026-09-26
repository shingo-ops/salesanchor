<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# recon — pipeline-tables-public

**仕事名**: pipeline-tables-public  
**日付**: 2026-09-21  
**対象ADR**: ADR-100  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `.github/workflows/migration-guard.yml:224` | PUBLIC_TABLES allowlist 現在地。17テーブル追加が必要 |
| `migrations/20260919_020000_master_ssot_public_tables.sql:1` | 先行SSoT移行のパターン確認（CREATE TABLE IF NOT EXISTS） |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 17テーブルのFKグラフ（作成順序） | DDLを読み込みCカテゴリ→B→A→D→E→Fの順を確認 | ✅ 解消済み |
| 2 | analysis_run_snapshots.unit_id/condition_idの型 | 本番DDL照合（UUIDのまま維持） | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

- Step 1はDDL-onlyでデータ操作なし
- CREATE TABLE IF NOT EXISTS で冪等性を確保
- migration-guard PUBLIC_TABLES allowlistに17テーブルを追加
