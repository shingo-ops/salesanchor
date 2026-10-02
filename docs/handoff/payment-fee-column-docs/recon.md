<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# recon — payment-fee-column-docs

**仕事名**: payment-fee-column-docs  
**日付**: 2026-10-02  
**対象ADR**: ADR-なし（PO方針確立のみ・ADR起案不要）  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `migrations/20261002_160000_create_payment_fee_settings.sql:1` | payment_fee_settingsテーブル作成migrationが存在し、全15カラム定義済み |
| `backend/app/schemas/payment_fee_setting.py:1` | Pydantic schemaが存在し、Field定義が確認済み |
| `scripts/run_all_migrations.sh:1` | migration適用スクリプトが存在し、既存migrationが登録済み |
| `backend/CLAUDE.md:1` | backend固有ルールファイルが存在し、Migration適用経路セクションが確認済み |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | COMMENT ON COLUMNは既存データ・スキーマへの影響があるか | PostgreSQL公式仕様確認: additive-only、既存データ・構造変更なし | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

- COMMENT ON COLUMN はメタデータ付与のみ（DDL上の変更なし・RLSや型に影響しない）
- Pydantic description はSwagger UIに自動反映（OpenAPI spec経由）
- run_all_migrations.sh への追記は冪等（何度実行してもコメントが上書きされるだけ）
