# design: 郵便番号が空のときの補完を自動試験で守る（香港あて）

状態: 設計審査済み（Opus 自己審査）。PO の実装承認 2026-11-25「1」。試験 T1〜T4 はクラウドの担当が追加済み。
参照: docs/handoff/hk-zip-fallback-tests/recon.md、ADR-126 §5（出口補完）、ADR-125（FedEx 見積もり）、FEATURE-INDEX.md:20

## 1. 目的（KGI）
香港あての送り先は郵便番号を空で登録する（PO 2026-11-25）。空のとき、アプリは2か所で値を補う。
- 見積もり: FedEx へ `999077` を送る（`backend/app/services/fedex_rates.py:86,307-308`）
- eLogi の発送 CSV: `0000000` を入れる（`backend/app/routers/order_shipping_details.py:327-328`）。DB は空のまま（ADR-126 §5）

今はこの2つを確かめる試験が0本（recon.md「既存の試験」）。将来この行が消えたり変わったりしても CI は緑のまま通る。
**KGI: この補完が壊れる変更を入れると、必須の CI が赤になる。**

## 2. 対象と対象外
- 対象: 試験ファイル3つへの試験の追加だけ。
  - `backend/tests/test_fedex_rates.py`
  - `backend/tests/test_order_shipping_details.py`
  - `backend/tests/test_invoice_totals.py`
- 対象外（触らない）: `backend/app/` 以下の製品コード全部、DB・migration、CI 設定、画面。
- 対象外: 本番 FedEx・eLogi での実地確認（FedEx 本番申請後の動作確認で行う・PO 指示）。

## 3. 変更内容（追加する試験）
### T1 見積もり: 香港で郵便番号が空なら 999077 を送る（`backend/tests/test_fedex_rates.py` の `class TestGetRates` に追加）
既存 `test_success_returns_quotes`（:162）と同じ形で `httpx.post` を `side_effect=[_mock_token_resp(), _mock_rates_resp()]` で差し替える。配達日数の呼び出しは例外を握りつぶす（`backend/app/services/fedex_rates.py:458,468`）ので2つで足りる。
```python
@pytest.mark.parametrize("dest_zip", [None, ""])
def test_hk_empty_postal_code_sends_representative_999077(self, dest_zip):
    with patch("httpx.post", side_effect=[_mock_token_resp(), _mock_rates_resp()]) as m:
        get_rates(tenant_id=1, environment="sandbox", client_id="cid", client_secret="csec",
                  account_number="123456789", origin_country_code="JP",
                  destination_country_code="HK", weight_kg=Decimal("1.0"),
                  destination_postal_code=dest_zip)
    rates_call = m.call_args_list[1]
    assert rates_call.args[0].endswith("/rate/v1/rates/quotes")
    addr = rates_call.kwargs["json"]["requestedShipment"]["recipient"]["address"]
    assert addr["countryCode"] == "HK"
    assert addr["postalCode"] == "999077"
```
### T2 見積もり: 郵便番号があればそのまま送る（同クラス）
T1 と同じ形で `destination_postal_code="0"` → `addr["postalCode"] == "0"`。補完が入力値を上書きしないことを守る。

### T3 eLogi CSV: 香港で郵便番号が空なら ZIP 列は 0000000・DB は空（`backend/tests/test_order_shipping_details.py` の CSV 試験の並びに追加）
既存 `test_single_csv_returns_19_columns`（:214）と同じ形。`zip_code` を送らない。
```python
async def test_single_csv_hk_empty_zip_fills_0000000(self, client):
    order_id = await _create_order(client, "ORD-SHIP-CSV-HK")
    res = await client.post(f"/api/v1/orders/{order_id}/shipping", json={
        "recipient_name": "Recipient HK", "country_code": "HK",
        "state_code": "Kowloon", "city": "Cheung Sha Wan", "address1": "1 Test Road"})
    assert res.status_code == 201, res.text
    csv_res = await client.get(f"/api/v1/orders/{order_id}/shipping/elogi-csv")
    assert csv_res.status_code == 200
    data = list(csv.reader(StringIO(csv_res.text)))[1]
    assert data[14] == "HK"
    assert data[17] == "0000000"
    got = await client.get(f"/api/v1/orders/{order_id}/shipping")
    assert got.json()["zip_code"] is None   # DB は空のまま（ADR-126 §5）
```
POST の成功コード 201 は既存 `test_create_shipping_for_order`（:46、:68 で `== 201`）で確認済み。

### T4 見積書の届け先郵便番号: 香港で空なら None を返す（`backend/tests/test_invoice_totals.py` の :258-263 の並びに追加）
```python
def test_destination_postal_code_hk_empty_returns_none():
    assert destination_postal_code({"country": "HK", "postal_code": None}, None) is None
    assert destination_postal_code({"country": "HK", "postal_code": ""}, None) is None
```
None が `get_rates` に渡ると T1 の補完が効く。T1 と T4 で「会社の送り先が空→見積もりは 999077」の道がつながる。

## 4. 代替案と選んだ理由
| 案 | 採否 | 理由 |
|---|---|---|
| A 試験だけ足す | 採用 | 製品の動きは変えず、壊れたら CI で分かる。最小 |
| B 製品コードに香港専用の分岐を足す | 不採用 | 今の補完で sandbox では通った（recon.md 実測）。動きを変える根拠が無い |
| C 本番 FedEx に定期的に試し送りする | 不採用 | 料金と本物の発送が発生する。本番申請も未完了 |

## 5. リスクと対処
| リスク | 対処 |
|---|---|
| 試験が共有 DB を使い他の試験とぶつかる（T3） | 既存の CSV 試験と同じ `client` 部品・別の注文番号を使う |
| T3 の州・市の値が欄の決まりで弾かれる | 実装時に POST の返事を見て、弾かれたら英字の別の値に替える（意図は「郵便番号を送らない」だけ） |
| 将来 PO の判断で補完値自体を変える | そのときは試験の期待値も同じ PR で直す。試験は「黙って変わる」のを止めるためのもの |

## 6. 受け入れ基準
| 基準 | 検証方法 |
|---|---|
| K1 T1〜T4 の試験が追加され、PR の必須 CI（pytest）が緑 | PR の Checks 画面で pytest が success・追加した試験名が実行ログに出る |
| K2 補完を消すと試験が赤になる | クラウドの担当が一時的に `backend/app/services/fedex_rates.py:308` の補完と `backend/app/routers/order_shipping_details.py:327-328` を外して試験を回し、T1・T3 が失敗する生出力を PR に貼る（外した変更は commit しない） |
| K3 製品コードは1行も変わらない | `git diff origin/main...HEAD --name-only` が `backend/tests/` の3ファイルと本 docs・台帳だけ |

区分: ADR-1015 の B-3（テストと正本でない docs だけ）。ADR-126 の未チェック項目へのチェックは正本の変更になるため本 PR に含めず、合流後に別の書類 PR で行う。

## 7. 外部・過去事例の参照と我々への応用
不要。理由: 自社コードの既存の動きを試験で固定するだけ。FedEx 側の挙動は自社の sandbox 実測（recon.md）を根拠にし、外部の事例を成功の証明に使わない。

## 8. 維持の仕組み
- 守り手: 必須 CI の pytest（backend/tests/test_fedex_rates.py・backend/tests/test_order_shipping_details.py・backend/tests/test_invoice_totals.py）。補完を変える PR は自動で赤になる。
- 本番での実地確認: 記録済み（PO 2026-11-25）。FedEx 本番申請後の動作確認で香港あて（郵便番号空）を見積もり・ラベルの両方で試す。

## 9. 実装カード（PO の実装承認後にクラウドの担当へ渡す）
- 場所: `bash scripts/new-worktree.sh` で作った `release/hk-zip-fallback-tests` の作業場所（本 docs と同じブランチ）。
- 作業: §3 の T1〜T4 を追加。§2 の対象外は触らない。
- 試験は手元の Mac で回さない。PR の CI とクラウドで回す。
- K2 の一時的な外しはクラウド内だけ。commit しない。
- 止まる条件: 既存の試験の部品・戻り値が本書の想定と違う／製品コードを直さないと通らない → 直さずに止めて報告。

## 審査
審査の記録は [review-opus.md](./review-opus.md)。
