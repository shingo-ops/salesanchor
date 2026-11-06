# recon: 見積シートへの自動反映（のりゆきさんの見積もり用タブ）

調査日: 2026-11-07（JST）／調査者: Claude Opus（設計担当）
対象: PO がコピーした「開発_見積もり のコピー」（持ち主 shingo@treasureislandjp.com、2026-11-06 11:45 UTC 作成）。元のシートは Drive の読み取りで「見つからない」（共有なし）。
生出力: `/tmp/CC報告ファイル/mitsumori/`（copy.xlsx・formulas.txt・mitsumori_sheet.txt・dist_svc.py）

## 1. 既存 ADR の検索
- `git grep -l -i -E "見積|estimate sheet|のりゆき|ADR-1066" origin/main -- docs/adr` → 見積に当たるのは SA アプリ内の見積・請求（ADR-101 ほか）だけ。今回はお客さんの Google シート側の仕組みで、SA の見積機能とは別。
- 配信の列と商品ID: `docs/adr/ADR-1066-distribution-sheet-15-columns-product-id.md`（Accepted 2026-11-06）。本設計はこの15列を入力に使う。
- `docs/adr/FEATURE-INDEX.md:14` 見積/請求 → ADR-101（SA アプリ内。対象外）。

## 2. シートの作り（観測事実）
タブは4枚: 見積もり用 / ポケ のコピー 2 のコピー 1（請求書）/ 在庫集計 / 為替。

### 2-1 見積もり用
- 見出し1行目: A `NO`, B `型番`, C `日本語名`, D `Item`, E `Unit price`, F 空, G `='為替'!B3`（USD）, H `='為替'!B5`（EUR）, I `AUD`, J `GBP`, K `SGD`, L `Kg/Total`, M `仕入平均単価`, N `仕入小計`, O `差益`（formulas.txt）。
- A3 以下は `=A2+1` の連番。
- 2〜95行目が箱物（ポケモン・ワンピース）、96〜106行目が特別な箱とカードのまとめ売り（D96 `precious collection boxes` 〜 D106 `Tag team RR full set 32cards`）。
- E は手入力の数字。シュリンクなしの8行だけ `=E(上の行)-1000`（E8,E10,E12,E14,E17,E19,E21,E23）。
- E が `ask` の行が9行（E57,E59,E61,E66,E67,E68,E69,E70 ほか）。
- G〜O の2行目以降は空（式も値も無い）。
- P71:P95 に `=D71&"("&C71&")"` の式（用途は未確認）。

### 2-2 請求書タブ（ポケ のコピー 2 のコピー 1）
- G4 以下: `=IFERROR(VLOOKUP(E4,'見積もり用'!$D$1:$E$107,2,false),"")` → Item 名で見積もり用の D 列を探し E 列の値段を拾う。探す範囲は107行目まで。
- H=`G*F`、I/J/K = H を為替で割ったユーロ・豪ドル・米ドル。C1/D1/E1 は GOOGLEFINANCE の為替。
- 明細は4〜24行目（21行）。この写しでは明細はすべて空。

### 2-3 在庫集計（SA の配信先）
- 15列: 投稿日時, Status, Mark, Japanese Title, English Title, Condition, Unit Price, Quantity, Ship_JA, Note_JA, 提供者, Release Date, Series, Search Keywords, 商品ID。1383行（見出し除く）。
- 例: ハドウシーカー（商品ID 466045）の Sealed box は11行（11,000円×50 〜 19,000円×200。仕入元の名前は社外秘のため書かない。生出力は `/tmp/CC報告ファイル/mitsumori/` に置く）。

## 3. SA の書き込み方（本線のコード）
- `backend/app/services/tcg_distribution_svc.py:682-684`（origin/main）: `worksheet.clear()` のあと `worksheet.append_rows(all_rows, value_input_option="RAW")`。→ 書き込みのたびにタブが一瞬空になる。
- 書き込みは Sheets API（サービスアカウント）。

## 4. 外部仕様（Context7 は月の上限で使えず、公式ページを直接確認）
- Apps Script のトリガーは、スクリプトや API の書き込みでは動かない: https://developers.google.com/apps-script/guides/triggers/installable ／ https://developers.google.com/apps-script/guides/triggers
- 時間で動くトリガーの1日の合計時間: 個人90分・Workspace 6時間: https://developers.google.com/apps-script/guides/services/quotas
- シートの関数 LET / LAMBDA / BYROW / MAP / REDUCE は提供あり: https://support.google.com/docs/answer/13190535 ほか

## 5. 未確認
- 元のシートに、ほかの請求書タブがあるか。
- 公開の価格表が IMPORTRANGE で見積もり用のどの範囲を読んでいるか（範囲が固定なら、行が増えたとき下の行が届かない）。
- P71:P95 の式の用途。
- 元のシートの持ち主のアカウント種別（関数案では影響なし）。

## 6. 追加の観測（2026-11-07、`/tmp/CC報告ファイル/mitsumori/est_probe.txt`）
- 在庫集計の値はすべて文字（例: Unit Price `'8300'`、Quantity `'200'`、Release Date `'2027-01-15'`）。SA が `value_input_option="RAW"` で書くため（`backend/app/services/tcg_distribution_svc.py:684`）。→ 式では `VALUE()` で数に直さないと大小比較が正しくならない。
- Mark 列は型番（例: ハドウシーカー = `M7`）。見積もり用 B2 の `M7` と一致する。→ 型番は Mark 列から取れる。
- 状態は16種（Sealed box 855行、Case 169、Damaged sealed box 81、No shrink box 75、ほか `未開封`・`PSA9` など）。
- シリーズは17種（ポケモン 914行、ワンピース 287行、ほか）。見積もり用の今の行はポケモンとワンピースだけ。
- 英語名が空の行は233行。
- 見積もり用の今の Item は日付つきの独自の名前（例: D2 `Aura Seeker (Nov27)`）。配信の English Title（`Aura Seeker`）とは違う。

## 7. 今の見積行を配信データで埋められるか（2026-11-07、手元の写しで試算）
- 試算の台本: scratchpad `est/sim.py`。生出力: `/tmp/CC報告ファイル/mitsumori/sim_out.txt`・`probe2.txt`。条件 10/50/100、状態 Sealed box と No shrink box。
- 式そのものではなく、design §3-2 の選び方を Python で同じ順に再現したもの。シートの式は未実行。
- 見積もり用 2〜95行（94行）の内訳:
  - 採用あり 75行
  - 在庫集計に商品が見つからない 13行（型番が空の行は日本語名の完全一致で探した。名前の書き方の違いで外れた行が含まれるかは未確認）
  - 商品はあるが条件に合う申し出が無い 6行（例: 19行 Inferno X no shrink、66・68・70行、72行 EGGHEAD CRISIS、94行 頂上決戦）
- 自動選定に出る組はポケモン＋ワンピースで111件。今の見積行（94行）に無い商品も多く出る。
- 英語名が2つの商品で同じ: 商品ID 68（OP-08 二つの伝説）と 83（OP-06 双璧の覇者）が、どちらも `TWO LEGENDS`。請求書の名前探しで取り違えが起きる。直す場所は SA の商品マスタ（シートではない）。
- 英語名が空のまま採用される行は12件（例: 30年セレブレイション、ストームエメラルダ、アビスアイ、決戦の刻）。
