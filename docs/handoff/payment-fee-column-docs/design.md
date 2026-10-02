<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# 設計 — payment-fee-column-docs

**対象ADR**: ADR-なし（PO方針確立のみ）  
**recon**: docs/handoff/payment-fee-column-docs/recon.md  
**日付**: 2026-10-02  
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- PostgreSQL公式: COMMENT ON COLUMN はカタログテーブル（pg_description）にメタデータを格納するadditive操作。既存データ・スキーマ・インデックス・RLSへの影響ゼロ。→ 応用: additive-only原則（ADR-045）と完全に整合するため、POGOなしで適用可能
- FastAPI/Pydantic公式: Field(description=...)はOpenAPI spec（/openapi.json）に自動反映され、Swagger UI（/docs）で即時確認可能。→ 応用: 追加コスト最小でAPI文書化品質を大幅向上

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 全15カラムにCOMMENT ONが付与される | 本番適用後 `\d+ public.payment_fee_settings` でコメント確認 |
| Swagger UIで全Fieldのdescriptionが表示される | `/docs` の PaymentFeeSettingResponse スキーマ表示を目視確認 |
| migration-guardがCIでパスする | CI `.github/workflows/migration-guard.yml` 緑 |

---

## 技術 How・KPI

- KPI: payment_fee_settings 全15カラムにSQLコメント付与（0→15）、全Pydantic Fieldにdescription付与（0→15）
- 技術選択: COMMENT ON COLUMN（PostgreSQL標準DDL）+ Pydantic Field(description=...)（FastAPI標準）

---

## 弊害・トレードオフ

- COMMENT ON COLUMNはDDL操作のためトランザクション内で実行されるが、ロック取得は瞬間的（高トラフィック時も影響なし）

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | COMMENT ON COLUMN migration作成 | Generator |
| 2 | Pydantic schema Field description追加 | Generator |
| 3 | backend/CLAUDE.md ルール追加 | Generator |
| 4 | run_all_migrations.sh 登録 | Generator |

---

## 維持の仕組み

守り手: backend/CLAUDE.md

- 新規テーブル作成時にCOMMENT ON COLUMNを付与するルールをbackend/CLAUDE.mdに記載
- 新規Pydantic schema作成時にField(description=...)を記載するルールをbackend/CLAUDE.mdに記載
- migration-guard CIが新規migrationのdeploy.yml登録漏れを検知

---

## 継続

- 完了後の監視: 本番適用後 `\d+ public.payment_fee_settings` で確認
- 次フェーズへの引き継ぎ: 今後の全新規テーブル・schemaでこのパターンを標準適用
