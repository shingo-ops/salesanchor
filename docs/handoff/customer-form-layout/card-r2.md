# 実装カード R2 — 「Contact Person」の見出しを他の見出しと同じ左端にそろえる（PR 5718）

- 根拠: `eval-report.md` §5「Contact Person の見出しが左端から約 8px ずれた」。
  - 前（main）は `padding: "0 var(--spacing-2)"` で、`--spacing-2` が未定義のため余白 0 だった。
  - 今は設計 §4 で正しい名前 `--space-2`（8px）に直したため、余白が効き始めた。
  - 同じ画面の他の見出し（`RegisterPage.tsx:323`・`:511`、`RegisterAddressPage.tsx:228`、`RegisterChangeBillingPage.tsx:246`）は余白を持たない。前の見た目（左端そろい）に戻す。
- ブランチ: `release/customer-form-pc-layout-impl`（PR 5718 の head）

## 変える所（1か所だけ）

`frontend/src/pages/register/RegisterPage.tsx` の連絡先の見出し（`{t("registration.contactInfo")}` の直前の `<legend`）

- 前: `<legend style={{ fontWeight: "var(--font-weight-bold)", padding: "0 var(--space-2)" }}>`
- 後: `<legend style={{ fontWeight: "var(--font-weight-bold)" }}>`

## 触らない所

- 上の1行以外は全部触らない。

## 確かめ

- `git diff --stat origin/release/customer-form-pc-layout-impl` が上の1ファイル・1行だけ
- `cd frontend && npx tsc --noEmit -p .` が通る（生出力を残す）

## 想定の分岐

- 前の形の行が見つからない時は止めて BLOCKED:
