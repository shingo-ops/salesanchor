# recon — dist01-release-date（Release Date 列追加・発売日降順ソート）

## 現状（変更前）

`backend/app/services/tcg_distribution_svc.py`

- `DIST_HEADERS`: 10列（投稿日時 / Mark / Japanese Title / English Title / Condition / Unit Price / Quantity / Note_JA / Status / 提供者）
- ORDER BY: `ts.name NULLS LAST, p.code NULLS LAST, ar.id`

## 要件

- 11列目（Status の後・提供者の前）に `Release Date` を追加
- ORDER BY を `p.release_date DESC NULLS LAST, ts.name NULLS LAST, p.code NULLS LAST` に変更

## NULL 率（実測 2026-09-04）

707行中 `p.release_date IS NULL` = 62行 → NULL 率 8.8%

NULL 行は `NULLS LAST` で末尾に集約されるため、ほとんどの行は発売日順で表示される。

## 修正対象ファイル・行番号

`backend/app/services/tcg_distribution_svc.py`
- L40-53: `DIST_HEADERS` リスト（10→11列）
- L197: SELECT に `COALESCE(p.release_date::text, '') AS release_date` 追加
- L216: ORDER BY 変更
- L222-232: 返却リストに `row["release_date"]` 追加

## 関連 ADR

ADR-154（TCG PARITY-02）— 配信出力形式の管理方針
