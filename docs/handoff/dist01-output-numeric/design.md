# design — dist01 output numeric（小数点除去）

参照: `docs/handoff/dist01-output-numeric/recon.md`

## KGI / 検証基準

| 基準 | 検証方法 |
|------|---------|
| スプレッドシートの Unit Price / Quantity が整数文字列で書き込まれる | デプロイ後に `POST /tcg/distribution/run` を実行し、A列の値を目視確認 |
| `200.00` ではなく `200` が書き込まれること | gspread `ws.get("F2:G2")` で確認 |

## 修正方針

`fetch_output_rows` の SELECT 句を2行変更する（他カラム・他クエリへの影響なし）。

```sql
-- 変更前
COALESCE(ar.price_normalized::text, '')     AS unit_price,
COALESCE(ar.quantity_normalized::text, '')  AS quantity,

-- 変更後
COALESCE(ROUND(ar.price_normalized)::bigint::text, '')   AS unit_price,
COALESCE(ROUND(ar.quantity_normalized)::bigint::text, '') AS quantity,
```

## 影響範囲

- 修正箇所: `backend/app/services/tcg_distribution_svc.py:192-193`（2行のみ）
- `fetch_output_rows` の呼び出し元: `run_distribution`（同ファイル内）のみ
- `fetch_preview_data` は別関数・別クエリのため影響なし

## 外部・過去事例

NUMERIC(14,2)::text は PostgreSQL 標準動作で小数点2桁を付与する。
Google Sheets への数値書き込みで小数点を除去するには SQL 側で整数化するのが確実
（gspread 側でフォーマットするより変換漏れが少ない）。

## 戻し方

`ROUND(x)::bigint::text` → `x::text` に戻す（1行変更×2）。
