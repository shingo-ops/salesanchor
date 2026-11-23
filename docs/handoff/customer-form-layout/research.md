# 顧客登録フォーム レイアウト調査（未完・ネットワーク制限あり）

- 調べた日: 2026-11-23
- 調べた人: クラウドの Sonnet（claude-sonnet-5-5）
- 検索の数: WebSearch 7 回（標準モード）／WebFetch 6 回すべて失敗
- 確認日（下表すべて）: 2026-11-23

## 0. 最初に読むこと（この調査の限界）

- **WebFetch は全件失敗した。** `developers.google.com` / `docs.stripe.com` / `www.fedex.com` / `www.ups.com` / `baymard.com` は、このクラウドの許可ドメイン外で名前解決できなかった（getaddrinfo ENOTFOUND）。これらを許可すれば再調査できる。
- 実際のページや公式資料を読めていない。以下は **WebSearch が返した要約文（二次情報）** のみが根拠。実測 px・画面の並びは一つも確認できていない。
- Meta・OpenAI・Shopify Checkout・Amazon・Apple Store の住所フォームは、検索でも内容が得られなかった。すべて「未確認」。
- 数値は検索要約に書かれていたものだけ転記した。作った数値は無い。

## 1. 大手の住所フォーム比較表

| 社 | 欄の並び（1行に何を並べるか） | 各欄の幅 | 国の選び方 | 電話の国番号 | Address Line の数・上限 | 超えたときの知らせ方 | 出典・確認日 |
|---|---|---|---|---|---|---|---|
| Google（Maps Platform 住所フォーム見本） | 未確認 | 未確認 | 未確認 | 未確認 | 未確認 | 未確認 | 取得失敗（developers.google.com 名前解決不可）。2026-11-23 |
| Google Pay / Store | 未確認 | 未確認 | 未確認 | 未確認 | 未確認 | 未確認 | 未確認。2026-11-23 |
| Apple（Apple Store 配送先） | 未確認 | 未確認 | 未確認 | 未確認 | 未確認 | 未確認 | 未確認。2026-11-23 |
| Meta | 未確認 | 未確認 | 未確認 | 未確認 | 未確認 | 未確認 | 未確認。2026-11-23 |
| OpenAI（請求先） | 未確認 | 未確認 | 未確認 | 未確認 | 未確認 | 未確認 | 未確認。2026-11-23 |
| Stripe（Address Element） | 並び・行の分け方は未確認。氏名欄が既定で出る（`name` で split/organization に切替可）。電話は `fields.phone` で always/auto/never | 未確認 | 国を選ぶと、対応国では住所の候補が出る（対応国: AU, BE, BR, CA, CH, DE, ES, FR, GB, IE, IN, IT, JP, MX。古い版は9か国。ライブのページで要確認）。候補は Google Maps Places ライブラリを使う。236 の国別住所形式に対応（右から左も含む） | 電話欄の有無のみ確認（国番号欄の形・幅は未確認） | 未確認 | 未確認 | 検索結果の要約（https://docs.stripe.com/elements/address-element ほか）。ページ本体は読めていない。2026-11-23 |
| Shopify Checkout | 未確認 | 未確認 | 未確認 | 未確認 | 未確認 | 未確認 | 未確認（検索に出ず）。2026-11-23 |
| Amazon | 未確認 | 未確認 | 未確認 | 未確認 | 未確認 | 未確認 | 未確認（検索に出ず）。2026-11-23 |

### 補足（表に入れにくい二次情報）

- Baymard（要約経由）: 1行に2〜3欄を並べても、同じ一つの対象に属する欄（例: City と ZIP）で、ほかが1列なら問題が出にくい。複数列レイアウト全般は、被験者がつまずくことが多かった。Etsy の1列レイアウトが ZIP と City だけ例外的に並べていると言及。出典: https://baymard.com/blog/avoid-multi-column-forms（要約のみ）。
- Baymard（要約経由）: ZIP から City/State を自動入力する場合、City/State は ZIP の**下**に常時表示するのが最も安全。ZIP の上に出ると見落とす人が多い。出典: https://baymard.com/blog/zip-code-auto-detection（要約のみ）。
- Baymard（要約経由）: 欄の幅は想定入力長に合わせる。固定長は正確な長さ、ZIP のように平均が既定幅とずれる欄は幅を変える。出典: https://baymard.com/blog/form-field-usability-matching-user-expectations（要約のみ・数値なし）。
- 学術（要約経由）: 欄の大きさを入力長の合図と受け取る人が多く、幅が合わないと誤答が増えるとされる（Couper ら、Beaumont ら。2023 年の論文経由）。出典: https://doc.rero.ch/record/301906/files/iwc23-0033.pdf（要約のみ・数値なし）。

## 2. 運送会社の住所1行の文字数上限（35 の根拠）

公式資料（FedEx・UPS・DHL の仕様書）は **取得失敗**（www.fedex.com / www.ups.com が名前解決不可）。以下は二次情報で、**35 の根拠としては「未確認」扱い**。

| 運送会社 | 1行の上限（二次情報） | 出典 | 状態 |
|---|---|---|---|
| FedEx | 35 文字 | ShippyPro ブログ https://www.shippypro.com/blog/en/streetlines.too.long-how-to-fix-address-limit-errors-for-fedex-ups ／ ShippingEasy https://support.shippingeasy.com/hc/en-us/articles/4407007257115 ／ Ordoro https://support.ordoro.com/what-are-the-character-limits-per-field-for-fedex-labels/ | 公式未確認 |
| UPS | 35 文字（Shopify コミュニティに UPS の「exceeds 35 characters」エラーの報告あり） | 同上 ／ https://community.shopify.com/t/urgent-help-ups-the-address-line-youre-shipping-from-exceeds-35-characters-to-spain/54740 | 公式未確認 |
| DHL | 資料により不一致。Shopify の案内は Address 1 で 35、ShippyPro の表は 35〜45（サービス・仕向地で変わる）、DHL 自身の住所録の取込ガイドは Address 1・2 とも 45（ラベル印刷とは別の文脈） | https://help.shopify.com/en/manual/shipping/shopify-shipping/troubleshooting-labels ／ https://mydhl.express.dhl/ba/en/address-book-import/create-edit-field-guidelines.html | 不一致・公式未確認 |

- 注意（二次情報）: 文字数が収まっても、文字幅の違いで切れることがある（Ordoro）。非ローマ字・記号は国際発送で弾かれやすい（ShippyPro）。
- 結論: 「35 文字」は FedEx・UPS で複数の二次情報が一致するが、DHL は 35〜45 で割れている。最も厳しい値に合わせるなら 35 は安全側。ただし**公式資料での確認は済んでいない**。

## 3. 外部の事例（5W2H・数値あり／なし）

要約経由のため、いつ・誰に・いくらで は不明な項目が多い。数値が無いものは件数に数えない。

### 3-1. 数値ありの成功

**事例A: Google Chrome の自動入力（Autofill）**
- いつ: 2024 年の公開記事（公開日の詳細は未確認）
- どこが: ブラウザの住所・カード等の自動入力（住所の「候補表示」そのものではない）
- 誰に: 利用統計の共有に同意した米国の Chrome 利用者
- 何を: フォームに自動入力を使った場合の効果
- なぜ: チェックアウトの離脱を減らすため（Google の説明）
- どうやって: 自動入力の利用有無の比較（手法の詳細は未確認）
- いくらで: 未確認
- 数値: フォーム放棄が平均 75% 減、入力時間が平均 35% 短縮。ゲスト購入で自動入力を使った場合、購入完了率が 45% 高い（Shopify の指標として同記事内に引用）。
- 注意: Google 自身の内部データ。自動入力であり、住所候補の入力方式とは別物。地域で成功率は大きく変わると Google が注記。
- 出典: https://blog.google/products/chrome/chrome-autofill/ ／ 確認日 2026-11-23（要約のみ）

**事例B: Universal Yums の住所自動補完**
- いつ: 未確認（記事の公開日は未確認）
- どこが: 購入時の住所入力に住所自動補完を追加
- 誰に: 同社の購入者（規模は未確認）
- 何を: 住所の自動補完
- なぜ・どうやって・いくらで: 未確認
- 数値: 購入完了率（conversion）が約 1.5% 改善
- 注意: 「約 1.5%」が相対か絶対かは未確認。ベンダー経由の事例の可能性。
- 出典: https://devpress.com/address-autocomplete-improved-conversions-by-1-5/ ／ 確認日 2026-11-23（検索の見出しと要約のみ）

→ **数値ありの成功は 2 件（要求の 3 件に未達）。**

### 3-2. 数値が不十分で件数に数えないもの

- **Shopify（Google Autocomplete）**: 住所の自動入力でモバイルの時間がおよそ 20% 短縮、住所の誤りも減ったと報告。conversion は「増えた」とのみで数値なし。→ 時間短縮の数値はあるが一次資料を読めておらず、成功の確定件数には入れず参考。出典: https://www.shopify.com/pk/blog/google-autocomplete ／ 2026-11-23。
- **Fabletics（Smarty 事例）**: A/B テストで、特に海外の購入者で新規注文の完了が増えたとされるが、見えた範囲に百分率なし → **数値なし**。出典: https://www.smarty.com/documents/fabletics-case-study.pdf ／ 2026-11-23。PDF 本体を読めば数値があるかもしれない（未確認）。
- **Tavour（Statsig 事例・失敗→改善）**: 住所自動補完を一部の利用者に出したところ、対照群より離脱が多かった。仮説は、スクロールなしで見える候補が少なく「まだ候補がある」と伝わらなかったこと。小さい画面で悪化。候補をスクロールなしでより多く見せる設計に変えて有効化し、新規ユーザーの有効化率が「2 桁ポイント」上がったと会社は報告。→ 具体的な基準値・標本数は無く**数値なし扱い（件数に入れない）**。ただし失敗要因が候補表示の見え方に結びつく点は我々に有用。出典: https://statsig.com/customers/tavour ／ https://statsig.com/blog/free-beer ／ 2026-11-23。
- **Baymard の複数列フォーム**: 複数列で被験者がつまずくという定性的な知見のみ → **数値なし**。
- **Baymard の ZIP 自動検出**: ZIP を離れないと City/State が出ない設計で問題が出た（定性）。**数値なし**。

→ **数値ありの失敗事例は 0 件（要求の 3 件に未達）。** 数値を作らず、未達のまま報告する。

## 4. 成功と失敗の要因（数値と結びつけられる範囲）

- 数値と結べたのは「自動入力で放棄 75% 減・時間 35% 短縮」（事例A）と「conversion 約 1.5% 改善」（事例B）だけ。要因は「打つ量を減らすこと」で、候補表示方式の優劣を比べた数値ではない。
- 失敗側は、Tavour の「候補が少なくしか見えず離脱が増えた」という定性的な要因のみ。数値化はされていない。
- よって、**「入力欄の幅・並び・文字数の知らせ方」を変えた事例の数値は、今回は一つも得られていない。**

## 5. 我々のフォームに当てはめる注意（推測を含む・推測と明記）

- 規模の違い（事実）: 上の数値は消費者向け EC・大規模サービスの値。我々は海外の卸のお客様が1回入れる B2B 登録で、母数がずっと小さい。同じ割合で効く保証は無い。
- 適用の限界（事実）: 数値の主体は「自動入力」で、「欄の幅」「City/State/ZIP の並べ方」「文字数警告」の効果を示すものではない。
- 推測: 国の入力を「打つと候補が出る」方式にする場合、Tavour の教訓から、候補を十分な数見せ、スクロールが要ることが分かる見せ方にするとよい（推測。数値の裏づけなし）。
- 推測: ZIP から City/State を出す方式にするなら、Baymard に従い City/State は ZIP の下に常時表示する（定性的な指針）。
- 推測: City と State を1行、State と ZIP を1行という案は、Baymard の「同じ対象に属する欄なら2〜3欄を並べてよい」とは整合するが、他の欄は1列に保つこと（定性的）。
- 推測: Address Line 35 文字は FedEx・UPS の二次情報と一致。DHL は 35〜45 で割れており、公式での確認が先。

## 6. 次にやること（再調査に必要な条件）

1. 次のドメインを許可して再実行: `developers.google.com`、`docs.stripe.com`、`baymard.com`、`www.nngroup.com`、`www.fedex.com`、`www.ups.com`、`www.dhl.com`、`mydhl.express.dhl`、`shopify.dev` / `help.shopify.com`、`www.smarty.com`、`statsig.com`。
2. Apple・Meta・OpenAI・Amazon は実ページ（ログイン要・動的描画）のため、WebFetch では読めない公算が高い。ブラウザ操作が使える環境での実測が要る。
3. 数値あり事例が必要なら、Baymard の有料ガイドラインや各社の技術ブログを直接読む必要がある。
