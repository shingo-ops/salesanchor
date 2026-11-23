# design: 登録フォームの最初の配送先を「いつもの配送先」にする

recon: `docs/handoff/register-delivery-default/recon.md`

## 1. 目的（PO の言葉）

別の配送先を入れて登録したときも「いつもの配送先」の印が付くようにする（PO 2026-11-24「1」）。書き出しの配送先の欄が空になる問題を無くす。

## 2. 対象／対象外

- 対象: `backend/app/routers/registration_tokens.py` の `register_customer` の住所の保存（305-347 行）と、試験 `backend/tests/test_public_register_company.py`。
- 対象外: フロント（`frontend/src/pages/register/RegisterPage.tsx`）、`add_address`（ADR-127 で false 固定のまま）、`change_billing`、請求先の is_default（送られた値のまま。`already_registered` の 409 判定を変えない）、migration。

## 3. 変更前後

- 変更前: 配送先の is_default は送られた値のまま。「配送先住所を登録する」の道では false。
- 変更後: 配送先は、その会社にまだ default の配送先が無ければ、送られた中の最初の配送先を true にする。2 件目以降と、すでに default がある会社では false。請求先はこれまでどおり。

## 4. 代替案と選んだ理由

- 案A（選択）: サーバーで決める。フロントが何を送っても同じ結果になり、正本が 1 か所（サーバー）に決まる。すでに default の配送先がある会社でも一意制約にぶつからない。
- 案B: `frontend/src/pages/register/RegisterPage.tsx` で `is_default: true` を付ける。1 行で済むが、サーバーは送られた値を信じたままで、別の送り手や今後の画面変更で同じ漏れが起きる。
- 案C: 何もしない。書き出しの配送先が空のまま。

## 5. リスクと対処

- すでに default の配送先がある会社に register を送ると、以前は「請求先と同じ」の道で一意制約にぶつかり 409 になり得た。変更後は配送先が false で入るので 409 にならない。請求先の 409 判定は変えないため、登録済みの会社の二重登録はこれまでどおり 409。
- 戻し方: この PR を revert する（migration 無し）。

## 6. 受入条件

| 基準 | 検証方法 |
|---|---|
| 配送先を is_default=false で送っても、保存された配送先が true | 新しい試験 1（SQLite・CI） |
| 「請求先と同じ」（true で送る）も true のまま | 既存の試験 `test_creates_company_when_lead_has_none` に配送先 true の確認を足す |
| すでに default の配送先がある会社では、送った配送先は false で入り 200 | 新しい試験 2 |
| 本番 tenant_001 で「配送先住所を登録する」を選んで送ると、新しい配送先が is_default=True | 反映後に Opus が Chrome で送信し reader で読む |
| 会社一覧の書き出しの配送先列が埋まる会社が増える（tenant_001 の新しい会社） | reader で default の配送先を数える（配送先あり＝default あり） |

## 7. 維持の仕組み

- 守り手: CI の backend 試験（`backend/tests/test_public_register_company.py` の 2 件）。
- 試験 2 件が CI の必須の試験で毎回走る。サーバーで決めるため、フロントの変更でこの漏れは戻らない。

## 8. 外部・過去事例の参照と我々への応用

不要。理由: 社内の 1 か所の値の決め方の直しで、外部の数値で決める判断が無い。

## 9. Opus 審査（同一 AI の自己審査）

- 既存 ADR との整合: ADR-127 の add_address false 固定・請求先の降格を変えない。ADR-126 の already_registered の 409 は請求先の一意制約で残る。ADR-097（登録フォーム）に登録時の配送先の default を決めた文は無く、この直しで食い違わない。→ 整合。
- 実物との照合: 行番号は origin/main fc20983a4 で確認（recon §2）。
- 受入条件は CI と reader で○×が出る。
- 判定: APPROVE。未解決事項なし。
