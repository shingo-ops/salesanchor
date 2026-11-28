# recon: 郵便番号が空のときの補完（見積もり 999077・eLogi 0000000）の自動試験

調べた日: 2026-11-25（origin/main `88c3fccd1` 基準。`git show origin/main:<path>` で読んだ）

## 背景（PO 2026-11-25）
- 香港あての送り先は郵便番号を空で登録する（PO「空でも見積もり、ラベルが作成できたのであれば空で登録する」）。
- 空のときにアプリが補う値を、自動の試験で守る（PO「1,2を順番に進める」の2）。
- 本番 FedEx・eLogi での実地確認は、FedEx 本番申請後の動作確認で行う（PO 指示で後回し。本書の範囲外）。

## 既存 ADR の検索結果
- `docs/adr/FEATURE-INDEX.md:20` 発送/FedEx → ADR-103 / ADR-123 / ADR-128 / ADR-125 / ADR-129。
- `docs/adr/ADR-126-registration-form-input-contract-v2.md` §5「出口補完2件」: ZIP 空欄なら eLogi 出口で `0000000` を入れる。DB には保存しない。
- 同 ADR 受け入れ条件「ZIP空欄で登録した顧客の eLogi CSV に埋め値が出力され、DB（company_addresses.zip / order_shipping_details.zip_code）は空のままである」は `[ ]`（未チェック）。
- `docs/adr/ADR-125-fedex-rates-stage1.md`: 郵便番号・代表値の記述は無い（grep "postal|郵便|代表" で0件）。

## 現在のコード（事実）
| 場所 | 中身 |
|---|---|
| `backend/app/services/fedex_rates.py:86` | `_REPRESENTATIVE_POSTAL_CODES` の `"HK": "999077",    # Hong Kong (postal code not used)` |
| `backend/app/services/fedex_rates.py:307-308`（`get_rates` 内） | `origin_zip = origin_postal_code or _REPRESENTATIVE_POSTAL_CODES.get(origin_cc, "000000")` / `dest_zip = destination_postal_code or _REPRESENTATIVE_POSTAL_CODES.get(dest_cc, "000000")` → `recipient.address.postalCode` に入れて `httpx.post(f"{base_url}/rate/v1/rates/quotes", json=payload, ...)` |
| `backend/app/services/invoice_totals.py:202-207` | `destination_postal_code(ship_to, bill_to)`: 国を持つ写しの `postal_code or None` を返す |
| `backend/app/routers/order_shipping_details.py:327-328`（`_build_csv_entry` 内） | `if not shipping.get("zip_code"): shipping["zip_code"] = "0000000"` |
| `backend/app/services/shipping_carriers/elogi.py:113` | `_s(shipping.get("zip_code"))` を `ZIP2` 列（`:74`）に出す |

行番号は `git grep -n ... origin/main` で照合済み（2026-11-25）。

## 既存の試験（事実）
- `git grep -n -E "0000000|999077|_build_csv_entry|_REPRESENTATIVE_POSTAL_CODES" origin/main -- backend/tests` → 該当0件（UUID 等の無関係な一致のみ）。
- `backend/tests/test_fedex_rates.py:585` `test_rate_precision_approximate_when_no_postal_code`: `get_rates` を丸ごと差し替えており、FedEx に送る郵便番号は見ていない。
- `backend/tests/test_order_shipping_details.py:251` `test_single_csv_without_shipping_row`: 受取人が空であることだけを見る。ZIP2 列（`data[17]`）は見ていない。
- `backend/tests/test_order_shipping_details.py:214` `test_single_csv_returns_19_columns`: ZIP あり（`100-0001`）の場合だけ `data[17]` を見る。
- `backend/tests/test_invoice_totals.py:258-263`: `destination_postal_code` は値ありと両方 None だけ。空文字・None の郵便番号は見ていない。

## FedEx 試し用での実測（2026-11-25・試験用の会社の sandbox 鍵）
香港あて（JP 1070062 → HK Kowloon・1kg・INTERNATIONAL_PRIORITY）:
| 郵便番号 | Rates | Ship |
|---|---|---|
| 欄なし | 422 | 200 ラベルあり |
| 空 | 200（4件） | 200 ラベルあり |
| 0 / 0000000 / 999077 / Hong Kong | 200（4件） | 200 ラベルあり |
| 000000 | 503（FedEx 側の一時停止） | 200 ラベルあり |
本番環境・eLogi は未確認。

## 未確認
- 本番 FedEx（apis.fedex.com）と eLogi の香港あて（郵便番号空）の受け付け。FedEx 本番申請後に確かめる。
