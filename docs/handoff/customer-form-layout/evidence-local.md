# 顧客登録フォーム 実物の測定記録（手元のブラウザ・Opus）

- 測った日: 2026-11-23
- 測った人: Claude Opus（手元の Playwright。ページを開いて入力欄の位置と幅を `getBoundingClientRect()` で読んだ）
- クラウド調べ（`release/customer-form-research` の research.md、fd4540a0）は公式ページが読めず未完。その穴をここで埋める。

## 1. Google Maps Platform「Place Autocomplete Address Form」見本

出典: https://developers.google.com/maps/documentation/javascript/examples/places-autocomplete-addressform
（見本の中身は https://maps-docs-team.web.app/samples/places-autocomplete-addressform/dist/）

| 欄（ラベル原文） | x | y | 幅 px | 高さ px | 全幅に対する割合 |
|---|---|---|---|---|---|
| 住所検索（gmp-place-autocomplete） | 27 | 110 | 385 | 50 | 96% |
| Street address* | 27 | 196 | 403 | 41 | 100% |
| Apartment, unit, suite, or floor # | 27 | 273 | 403 | 41 | 100% |
| City* | 27 | 350 | 403 | 41 | 100% |
| State/Province* | 27 | 427 | 201 | 41 | 50% |
| Postal code* | 237 | 427 | 188 | 41 | 47% |
| Country/Region* | 27 | 519 | 403 | 41 | 100% |

観測事実:
- City は1行を独占する。State と Postal code が同じ行（y=427）に半分ずつ並ぶ。
- 住所の行は2行（Street address と Apartment…）。
- 国は普通の文字入力欄（候補一覧の部品ではない）。住所検索で候補を選ぶと各欄が埋まる方式。

## 2. Stripe「Address Element」見本（docs ページ内の実物）

出典: https://docs.stripe.com/elements/address-element （iframe: js.stripe.com/v3/elements-inner-accessory-target-…）

| 欄（ラベル原文） | autocomplete 属性 | 幅 px | 高さ px |
|---|---|---|---|
| Full name | shipping name | 510 | 44 |
| Country or region（select） | shipping country | 510 | 44 |
| Address | shipping address-line1 | 510 | 44 |
| Address line 2 | shipping address-line2 | 498 | 44 |
| City | shipping address-level2 | 498 | 44 |
| State（select） | shipping address-level1 | 243 | 44 |
| ZIP code | shipping postal-code | 243 | 44 |

観測事実:
- Address line 2 以下は、住所を打つ前は畳まれていて同じ座標（526,172）に重なっていた。幅は描画済みの値。
- City は全幅（498）。State と ZIP code は同じ幅 243（約49%）で、半分ずつ1行に並ぶ形。
- 国は一覧から選ぶ select（打って候補を出す部品ではない）。
- どの入力欄にも maxLength は付いていない（-1）。

## 2b. Shopify Checkout（Allbirds の購入手続き・ゲスト・PO の Chrome で表示のみ・何も送信していない）

出典: https://www.allbirds.com/cart/<商品>:1 → /checkouts/cn/…/en-us（2026-11-23 表示）

| 欄（name / autocomplete） | y | 幅 px |
|---|---|---|
| countryCode（select・shipping country-name） | 462 | 500 |
| address1（shipping address-line1・虫眼鏡つき＝住所の候補） | 640 | 498 |
| address2（shipping address-line2） | 699 | 498 |
| city（shipping address-level2） | 758 | 158 |
| zone（select・shipping address-level1） | 757 | 160 |
| postalCode（shipping postal-code） | 758 | 158 |

観測事実:
- 国は「Delivery」の一番上の select（この店は米国だけ配送のため選択肢1つ）。打って候補を出す部品ではない。
- City・State・ZIP code の3つが1行に約3等分（158/160/158）で並ぶ。
- 住所は2行。maxLength は付いていない。
- Amazon（/a/addresses/add）はログイン画面に飛ばされたため未確認（PO のアカウントでログインはしていない）。

## 3. FedEx Ship API 公式の住所1行の上限

出典: FedEx Developer Portal Ship API の仕様 JSON
https://developer.fedex.com/wirc/json/api_groups/Ship/Shipment-Resource.json
（docs ページ https://developer.fedex.com/api/en-us/catalog/ship/v1/docs.html が読み込む資料）

`streetLines` の説明の原文（3か所のうち2か所）:
- "This is the combination of number, street name, etc. Maximum length per line is 35. … Streetlines more than 3 will be ignored. … For SmartPost Shipments, only 30 characters from the individual street lines will be printed on the labels."
- "… Max Length is 35. Note - For FedEx Ground Economy, a maximum of 30 characters will be printed on the label, excess characters will be truncated."
- 同じ資料で `city` は `"maxLength": 35`。

観測事実:
- FedEx の住所は 1行35文字・最大3行（4行目からは無視）。PO の「Address 1〜3・各35文字以内」と一致する。
- 一部の配送種別（SmartPost / Ground Economy）では、ラベルに印字されるのは30文字まで。

## 4. 未確認のまま残るもの

- Apple・Meta・OpenAI・Amazon・Shopify Checkout の実物（ログインや購入手続きの途中にしか出ない）。
- UPS・DHL の公式資料での上限（二次情報では UPS 35・DHL 35〜45 で割れている。research.md §2）。
- 欄の幅や並びを変えた効果の数値事例（research.md §3。数値ありの失敗事例は0件）。
