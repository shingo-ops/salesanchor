# 実装カード R3 — 見積書の宛名の試験の期待を住所3入りに直す（PR 5718）

- 根拠: PR 5718 の CI（Backend Tests の pytest-run-internal）で `tests/test_invoice_totals_pg.py::test_invoice_totals_pg_end_to_end` が落ちた。
  - 出た差: `'L1 L2 L3' != 'L1 L2'`
  - 設計 §3-5（K10・D4）で、見積書の宛名の住所に住所3を足した。試験の `:247` は住所3に `'L3'` を入れている。期待だけが古いまま。
- ブランチ: `release/customer-form-pc-layout-impl`（PR 5718 の head）

## 変える所（1か所だけ）

`backend/tests/test_invoice_totals_pg.py` の 261 行目

- 前: `    assert (b.address, b.city, b.state, b.postal_code) == ("L1 L2", "C953", "S953", "Z953")`
- 後: `    assert (b.address, b.city, b.state, b.postal_code) == ("L1 L2 L3", "C953", "S953", "Z953")`

## 触らない所

- 上の1行以外は全部触らない。`backend/app/` は触らない。

## 確かめ

- `git diff --stat origin/release/customer-form-pc-layout-impl` が上の1ファイル・1行だけ
- この試験は実の PostgreSQL が要るので、手元では流さない。CI で確かめる

## 想定の分岐

- 前の形の行が見つからない時は止めて BLOCKED:
