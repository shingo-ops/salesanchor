# design: fix-analysis-unique-index

## 対象ADR
ADR-072（write endpoint のテナントコンテキストリセット）、共用マスタSSOT方針

## KGI
`public.analysis_results` の `ON CONFLICT (extraction_item_id)` が成功し、解析ジョブが `ANALYSIS_FAILED` でなくなる。

## KPI（観測可能な事象）

| 基準 | 検証方法 |
|------|---------|
| pg_indexes に8件のインデックスが存在する | `SELECT indexname FROM pg_indexes WHERE schemaname='public' AND tablename='analysis_results'` で8件以上 |
| 解析ジョブが成功する | extraction_job の status が `analyzed` になる |
| ANALYSIS_FAILED が発生しない | analysis_results に新規レコードが upsert される |

## 変更方針

- インデックス追加のみ（データ変更なし）
- 全て `IF NOT EXISTS` で冪等（二重適用しても安全）
- tenant_001 の既存インデックス名に合わせた命名

## 影響範囲
- `public.analysis_results` テーブルのみ
- 呼び出し元: pipeline の解析サービス（tcg_analyzer_svc.py）

## 戻し方
インデックス削除: `DROP INDEX IF EXISTS <indexname>` で即時ロールバック可能。データ変更なしのため完全無害。

## 外部事例
PostgreSQL 公式: `ON CONFLICT` には対応するユニーク制約またはユニークインデックスが必須。
https://www.postgresql.org/docs/current/sql-insert.html#SQL-ON-CONFLICT
