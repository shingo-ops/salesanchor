# recon — dist01 output numeric（小数点除去）

## 調査対象

`fetch_output_rows` が `price_normalized` / `quantity_normalized` を `::text` で出力するため、
Google Sheets に "16400.00" のような小数点付き文字列が書き込まれる。

## 根本原因

`backend/app/services/tcg_distribution_svc.py:192-193`

```python
# 修正前:
COALESCE(ar.price_normalized::text, '')                 AS unit_price,
COALESCE(ar.quantity_normalized::text, '')              AS quantity,
```

`NUMERIC(14,2)` を `::text` でそのまま文字列化すると PostgreSQL は小数点2桁を付与する。

## スキーマ確認

`tenant_004.analysis_results`:
- `price_normalized NUMERIC(14,2)` — 実在 ✓
- `quantity_normalized NUMERIC(14,2)` — 実在 ✓

## 修正内容

`ROUND(x)::bigint::text` で整数に丸めてから文字列化（1行変更×2）。

## 一時対応記録（2026-09-04）

初回配信時、コンテナ `/app` が読み取り専用（bind mount なし）だったため、
`docker exec python3 -c` のスクリプト内でモンキーパッチを適用して対応。
本PRにより恒久化する。
