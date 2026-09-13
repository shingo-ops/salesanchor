# ソード&シールド期 ポケモン商品カタログ（登録候補44商品）

この文書は何か（専門用語なしの1行）: 商品マスタにまだ入っていないポケモン商品44件について、正式名称・英語名・型番・発売日を外部で調べて確定させた一覧。

親（recon）へのリンク: ./recon.md
親（設計仕様書）へのリンク: ../../specs/product-master/README.md

- 仕事名: tcg-product-master-growth
- 日付: 2026-09-05
- 対象ADR: ADR-154
- 担当: architect
- 状態: 調査完了・未登録（migration は別便）

## 0. 調べ方と出典

エキスパンションマークと発売日は tcg-hokan.com のエキスパンションマーク早見表を起点とし、商品ごとに公式サイト（pokemon-card.com）で裏を取った。英語名は Bulbapedia と TCG Republic のカテゴリ一覧を突き合わせて確定した。いずれも複数の独立した情報源で一致を確認している。

既存マスタとの突き合わせは、2026-09-04 実測の全271件（当時）に対して行った。拡張パック30件（S1W〜S12a）はすべて登録済みであり、本一覧には含まない。

## 1. 前提（2026-09-04 実測）

- 商品マスタ 296件（PM0296 まで）
- ポケモン商品 178件（登録済み・突き合わせ実施時点は271件中）
- ソード&シールド期の拡張パック30件はすべて登録済み

## 2. 登録候補44商品

| # | マーク | 日本語名 | 英語名 | 発売日 |
|---|---|---|---|---|
| 1 | SA | スターターセットV 草 | V Starter Set Grass | 2019-11-29 |
| 2 | SA | スターターセットV 炎 | V Starter Set Fire | 2019-11-29 |
| 3 | SA | スターターセットV 水 | V Starter Set Water | 2019-11-29 |
| 4 | SA | スターターセットV 雷 | V Starter Set Lightning | 2019-11-29 |
| 5 | SA | スターターセットV 闘 | V Starter Set Fighting | 2019-11-29 |
| 6 | SA | スターターセットV5 コンプリートバトルボックス | V5 Starter Set Complete Battle Box | 2019-11-29 |
| 7 | SA | トイザらス限定 トリプルスターターセットV | Toys R Us Limited Triple V Starter Set | 2019-11-29 |
| 8 | SA | セブン-イレブン限定スペシャルセット スターターセットV炎 | V Starter Set Fire 7-Eleven Limited Special Set | 2019-11-29 |
| 9 | SB | プレミアムトレーナーボックス ソード＆シールド | Sword & Shield Premium Trainer Box | 2019-12-06 |
| 10 | SP1 | ザシアン＋ザマゼンタBOX | Zacian + Zamazenta Box | 2019-12-27 |
| 11 | SC | スターターセットVMAX リザードン | Charizard VMAX Starter Set | 2020-03-27 |
| 12 | SC | スターターセットVMAX オーロンゲ | Grimmsnarl VMAX Starter Set | 2020-03-27 |
| 13 | SD | Vスタートデッキ草 フシギバナ | Grass Venusaur V Deck | 2020-07-10 |
| 14 | SD | Vスタートデッキ炎 ガオガエン | Fire Incineroar V Deck | 2020-07-10 |
| 15 | SD | Vスタートデッキ水 ホエルオー | Water Wailord V Deck | 2020-07-10 |
| 16 | SD | Vスタートデッキ雷 ピカチュウ | Lightning Pikachu V Deck | 2020-07-10 |
| 17 | SD | Vスタートデッキ超 ミュウ | Psychic Mew V Deck | 2020-07-10 |
| 18 | SD | Vスタートデッキ闘 ルカリオ | Fighting Lucario V Deck | 2020-07-10 |
| 19 | SD | Vスタートデッキ悪 ガラルヤドラン | Darkness Galarian Slowbro V Deck | 2020-07-10 |
| 20 | SD | Vスタートデッキ鋼 ジュラルドン | Metal Duraludon V Deck | 2020-07-10 |
| 21 | SD | Vスタートデッキ無色 イーブイ | Colorless Eevee V Deck | 2020-07-10 |
| 22 | SP2 | VMAXスペシャルセット | VMAX Special Set | 2020-10-23 |
| 23 | SEF | スターターセットVMAX フシギバナ | Venusaur VMAX Starter Set | 2020-12-04 |
| 24 | SEK | スターターセットVMAX カメックス | Blastoise VMAX Starter Set | 2020-12-04 |
| 25 | SEF | VMAX 対戦トリプルスターターセット | VMAX Battle Triple Starter Set | 2020-12-04 |
| 26 | SF | プレミアムトレーナーボックス ICHIGEKI | Premium Trainer Box ICHIGEKI | 2021-01-22 |
| 27 | SF | プレミアムトレーナーボックス RENGEKI | Premium Trainer Box RENGEKI | 2021-01-22 |
| 28 | SP3 | ジャンボパックセット 白銀のランス＆漆黒のガイスト | Jumbo Pack Set Silver Lance & Jet-Black Spirit | 2021-04-23 |
| 29 | SP4 | VMAXスペシャルセット イーブイヒーローズ | VMAX Special Set Eevee Heroes | 2021-05-28 |
| 30 | SH | ファミリーポケモンカードゲーム（ソード＆シールド） | Sword & Shield Family Pokemon Card Game | 2021-07-09 |
| 31 | SH | いつでもどこでもファミリーポケモンカードゲーム | Anytime Anywhere Family Pokemon Card Game | 2021-07-09 |
| 32 | SP5 | スペシャルカードセット ミュウツーV-UNION | Mewtwo V-UNION Special Card Set | 2021-08-20 |
| 33 | SP5 | スペシャルカードセット ゲッコウガV-UNION | Greninja V-UNION Special Card Set | 2021-08-20 |
| 34 | SP5 | スペシャルカードセット ザシアンV-UNION | Zacian V-UNION Special Card Set | 2021-08-20 |
| 35 | SJ | スペシャルデッキセット ザシアン・ザマゼンタ vs ムゲンダイナ | Zacian & Zamazenta vs Eternatus Special Deck Set | 2021-11-05 |
| 36 | SI | スタートデッキ100 | Start Deck 100 | 2021-12-17 |
| 37 | SI | スタートデッキ100 コロコロコミックVer. | Start Deck 100 CoroCoro Comic Version | 2021-12-17 |
| 38 | SK | プレミアムトレーナーボックス VSTAR | VSTAR Premium Trainer Box | 2022-01-14 |
| 39 | SLL | スターターセットVSTAR ルカリオ | Lucario VSTAR Starter Set | 2022-02-25 |
| 40 | SLD | スターターセットVSTAR ダークライ | Darkrai VSTAR Starter Set | 2022-02-25 |
| 41 | SPZ | VSTAR&VMAX ハイクラスデッキ ゼラオラ | Zeraora VSTAR & VMAX High-Class Deck | 2022-07-15 |
| 42 | SPD | VSTAR&VMAX ハイクラスデッキ デオキシス | Deoxys VSTAR & VMAX High-Class Deck | 2022-07-15 |
| 43 | SP6 | VSTARスペシャルセット | VSTAR Special Set | 2022-08-05 |
| 44 | SO | スペシャルデッキセット リザードンVSTAR vs レックウザVMAX | Charizard VSTAR vs Rayquaza VMAX Special Deck Set | 2022-11-04 |

## 3. 確度が低い項目（名指し）

| # | 項目 | 状態 |
|---|---|---|
| 6, 7, 8 | スターターセットV の関連3商品の発売日 | スターターセットV本体と同日と仮置き。個別の発売日は未確認 |
| 25 | VMAX 対戦トリプルスターターセットのマーク | SEF と仮置き。専用マークの有無は未確認 |
| 31 | いつでもどこでもファミリーポケモンカードゲームの英語名 | Bulbapedia のカテゴリ名が1件のみ。他ソース未確認 |
| 37 | スタートデッキ100 コロコロコミックVer. の発売日 | 通常版と同日と仮置き |

## 4. 登録時の設計方針（未実施）

- 大分類 DIV01 TCG / 作品 IP001 Pokemon / メーカー MK001 The Pokemon Company / 商品区分 PC_BOX
- category_class は Box
- 型番はキーワードに使わない（mark 欄にのみ記録）。2026-09-04 PO判断
- 検索キーワードは商品名ベースで作る
- N種セットを単品が拾わないよう、単品側に除外キーワード「種セット」を付ける。2026-09-04 PO判断

## 5. 未実施の作業

| # | 作業 | 状態 |
|---|---|---|
| 1 | 44商品のキーワード設計 | 未着手 |
| 2 | 実データ1792行に対する衝突シミュレーション | 未実施 |
| 3 | 実行前バックアップ | 未実施 |
| 4 | migration の作成と登録 | 未実施 |
| 5 | 既存 PM0064 / PM0065 の英語名確認（Gengar VMAX High-Class Deck / Inteleon VMAX High-Class Deck） | 未実施 |
| 6 | 既存 PM0200 のマーク MBB が MC の誤りか否かの判断 | PO判断待ち |

## 6. 範囲の区切り（2026-09-04 PO判断）

エキスパンションマーク早見表に載っている商品を基本範囲とする。表に載っていない公式商品は、調査の過程で自然に見つかったものだけ拾い、探しには行かない。本一覧では #6・#7・#8・#25・#37 の5件がこれに該当する。
