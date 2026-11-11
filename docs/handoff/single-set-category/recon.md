<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。 -->
# recon: 区分「シングルセット系」（シングルカードのまとめ売り）

> この文書は何か（専門用語なしの1行）:
> シングルカードのまとめ売りが「未開封」と出てしまう件について、今の仕組みと本番の値を事実で調べた記録。

親（あるべき姿）: [在庫管理](../../specs/inventory-management/README.md)。区分の判定の決めごとは [ADR-1031](../../adr/ADR-1031-single-and-promo-pack-conditions.md)。設計は [design.md](./design.md)。

- 調べた日: 2026-11-11（Opus）。
- コードは origin/main `d57728133` を読んだ（`git fetch` の後、refs/remotes/origin/main で確認）。
- 本番の値は reader 鍵（読み取りのみ）で読んだ。
- 仕入元名・原文は書かない。記録ファイル（リポジトリ外: ~/CC報告ファイル-keep/pika30-set-20261111/）には残した。
- 開発記録の区分（STANDARD-WORKFLOW §1.8）: 既存の延長。ADR-1031 の区分ごとの状態の群に、区分を 1 つ足す。前例は ADR-1035 追補（サプライ系）。

## 既存 ADR の検索

- `git grep -i "セット系\|シングル系\|kubun_type\|まとめ売り" docs/adr/` と `docs/adr/FEATURE-INDEX.md:21`（まとめ売り / N枚セット）→ ADR-1027（まとめ売りの読み取り。全部の行に当てる。2026-11-11 審査で見落としを指摘され追加）、 ADR-1031（シングル系・プロモパック系の状態の群）、ADR-1035（ブックレット系・サプライ系。区分を足す前例）、ADR-1041（区分ごとに取れる単位の表）、ADR-1021（区分の既定の状態）。
- 区分「シングルセット系」に当たる ADR は無い。

## 観点1 全体像（データの流れ）

1. 商品を先に決める: `backend/app/services/gemini_raw_copy_v102_product_first.py:932-943`。商品の区分は商品マスタの区分（`tcg_product_categories.kubun_type`）から引く（`backend/app/services/tcg_analyzer_svc.py:168-180`）。
2. 書かれた単位を読む: `backend/app/services/gemini_raw_copy_v102_product_first.py:944-947`。
3. 状態を決める: `backend/app/services/gemini_raw_copy_v102_product_first.py:948-950` → `_resolve_condition`（同 `:799-825`）。
4. 区分と状態から単位を決め直す: 同 `:858-890` `_resolve_unit_from_state`。
5. 区分ごとの単位の表で直す: 同 `:898-916` `_fix_unit_by_kubun`。
6. 状態の id を引いて書く: `backend/app/services/line_analysis_v102_svc.py:690-720`。

## 観点2 共用部品（ここでの「部品」＝区分名の定数・区分→群の表・状態の行）

| 部品 | 定義元 | 参照元 |
|---|---|---|
| 区分名の定数 | `backend/app/services/gemini_raw_copy_v102_product_first.py:48-56` | `backend/app/services/line_analysis_v102_svc.py:50-60`、`backend/app/services/v102_buyback_unit_svc.py:26`（`git grep` で確認） |
| 区分 → 状態の群・既定の状態・basis | 同 `:764-769` `_KUBUN_TO_VALUE_GROUP` | 同 `:780`、`:807` |
| 区分 → 群（状態の id を引く用） | `backend/app/services/line_analysis_v102_svc.py:690-695` `_SCOPED_GROUP_OF_KUBUN` | 同 `:700`。試験 `backend/tests/test_adr1035_booklet.py:158`、`backend/tests/test_supply_category.py:125` |
| 状態の行（群 single の 6 行） | 本番 DB（line_conditions） | 群の行の読み込み `backend/app/services/line_analysis_v102_svc.py:222`（群ごとに分けるのは `:224-227`） |

## 観点3 非共用部品

- 区分ごとの分岐が `_resolve_unit_from_state` の中に if で並ぶ（セット系 `:869-874`、サプライ系 `:875-879`）。今回の分岐も同じ場所に足す。表にまとめる余地はあるが、今回は前例と同じ形にそろえる（形を変えると既存の試験の意味が変わるため）。

## 観点4 ルールの所在

- ADR-1031（区分で状態の群を切り替える）、ADR-1035 追補（区分の単位を書かれた単位より優先する前例）、ADR-1041（区分ごとの単位の表）、ADR-1007（マスタの値は記録 SQL で入れる。migration にしない）、ADR-135（migration・deploy.yml・`scripts/` を含む PR の扱い。便1 は `scripts/` の台本 2 本を触るので当たる）、ADR-136（危険な PR の GO の手順）。

## 観点5 維持の仕組み（今、何が守っているか）

- 区分 → 群の対応は試験が守る: `backend/tests/test_adr1031_single_promo_pack.py`、`backend/tests/test_adr1035_booklet.py:158`、`backend/tests/test_supply_category.py:125`。
- セット系の単位は試験が守る: `backend/tests/test_gemini_raw_copy_v102_unit_state_set.py:97-145`。
- 状態の行の適用区分に「セット系」と書くと新しい区分にも部分一致で当たる点は、守り手が無い（設計で人手で守る）。

## 観点6 あるべき姿との対照

| あるべき姿（PO の言葉） | 今 | 判定 |
|---|---|---|
| まとめ売りは「未開封」ではない | セット系にすると Sealed box（事実 1・12） | 不足 |
| 状態はシングルと同じ | シングル系なら群 single で決まる（事実 3） | 一致（シングル系のとき） |
| まとめ売りとして数える（1 セットの値段） | シングル系・セット系とも、書かれた「(N枚)」等で単位が枚（事実 14） | 不足 |
| セットの中の分類としてシングルセットを作る | 区分「シングルセット系」は無い | 不足 |
| 余剰 | 該当なし（今の仕組みで捨てる物は無い） | — |

## 観点7 ノイズと境界

- 見る: v102 の判定・区分マスタ・v102 の現行行。
- 見ない: v6・v10・v101・shadow・GAS の判定（今回の商品の行は v102）。区分名「セット系」は単位の区分（`backend/app/services/tcg_unit_recovery_svc.py:98`）にも同じ文字で出るが、商品の区分とは別の値（ノイズ）。

## 事実

| # | 事実 | 根拠 |
|---|---|---|
| 1 | 区分「セット系」は、状態の語が無いと箱系と同じく Sealed box（未開封）になる | `backend/app/services/gemini_raw_copy_v102_product_first.py:53`, `:72`, `:810-815` |
| 2 | セット系の単位は、単位の語が無ければ Set。書かれた単位（枚など）はそのまま残る | `backend/app/services/gemini_raw_copy_v102_product_first.py:869-874` |
| 3 | シングル系の状態は群 single の行（PSA10／PSA9／PSA8／PSA7以下／Single／雑誌付き）だけで決め、語が無ければ Single・basis「R7:単品既定」 | `backend/app/services/gemini_raw_copy_v102_product_first.py:93`, `:97`, `:764-797`。本番の行は reader pk10.txt（6 行、適用区分はすべて「シングル系」） |
| 4 | 群の中の当て方は、状態の行の適用区分と渡した区分名の部分一致（`kbn in kubun`）。「シングル系」は「シングルセット系」に含まれないので、新しい区分名をそのまま渡すと群の行が1つも当たらない | `backend/app/services/tcg_analyzer_svc.py:791-821`, `:940`、呼び出し `backend/app/services/gemini_raw_copy_v102_product_first.py:783` |
| 5 | 状態の id は、区分 → 群の対応で群の中から引く（PSA10 が single と promo_pack の2行あるため） | `backend/app/services/line_analysis_v102_svc.py:690-704` |
| 6 | 区分ごとに取れる単位の表（ADR-1041）の本番の値は 箱系・プロモパック系・ブックレット系の3つ。セット系・シングル系は無い。表に無い区分では `_fix_unit_by_kubun` は何もしない | reader pk11.txt、`backend/app/services/gemini_raw_copy_v102_product_first.py:907-909` |
| 7 | 買取の箱の値段で単位を決める処理は、basis が R4 で始まる既定の状態だけを対象にする。R7 は対象外 | `backend/app/services/v102_buyback_unit_svc.py:159-172`, `:192-202`、`backend/app/services/gemini_raw_copy_v102_product_first.py:97` のコメント |
| 8 | 区分の一覧は画面（区分マスタ）が DB から読む。区分名をコードに直書きした画面は無い | `frontend/src/pages/product-categories/ProductCategoriesPage.tsx:29-53`、`frontend/src/pages/super-admin/components/ProductCategoriesMasterPanel.tsx:26-42`。`git grep "シングル系\|セット系" origin/main -- frontend` は 0 件 |
| 9 | 有効な区分は 6 つ（箱系 350 商品・シングル系 55・セット系 20・バルク系 24・プロモパック系 11・ブックレット系 5）。サプライ系の行は有効な一覧に無い | reader pk7.txt |
| 10 | セット系の 20 商品には、箱のセット（スペシャルセット・アタッシュケースセット・プレイマット＆カードセット等）と、シングルカードのまとめ売り（下の表）が混ざっている | reader pk7.txt（商品名） |
| 11 | ピカチュウ30種（466062）を 11/11 に PO が画面でシングル系 → セット系に変えた（audit_log id 1058） | reader（前の調べ） |
| 12 | 466062 を今のコードで解析し直す試走（11/11 16:12、書き込みなし）では、222 行が Set/Sealed box、17 行が Piece/Error。Error の 17 行は原文が「(N枚) ＠値段 在庫数」の形で、「(N枚)」の枚が単位として残り、セット系の箱の判定で状態が決まらなかった | 試走の記録 rejudge-dryrun-20261111-161233.out、pk6.txt |
| 13 | PO は「セット・未開封→未開封ではない、シングルカードのまとめ売りだから」と判断し、セットの中にシングルセットの区分を作り状態をシングルと同じにする案を出し、商品区分に作る案「1」を選んだ（2026-11-11） | 会話 |
| 14 | 466062 の「(N枚)」を含む行 23 行（置き換え済みを含む）は、今、単位 Piece・状態 Single。数量は在庫数の行・セット数の行から と正しく読まれ、値段も原文どおり（4,000〜7,500）。単位だけが枚になっている。「Nセット」と書かれた 6 行も単位は Piece | reader pk12.txt（2026-11-11 17:17 JST、23 行） |
| 15 | 試走で変わった項目は状態・basis・要確認だけで、数量・値段・単位は変わらなかった（17 行は状態・basis・要確認の 5 項目、1 行は状態の 3 項目） | 試走の changes.json を数えた（ssc-q2.txt） |
| 16 | 商品の区分の名前を条件に使う処理は、v102 の判定のほかは「箱系」（`backend/app/services/tcg_analyzer_svc.py:987`, `:1485`、`backend/app/services/tcg_work_comparison_svc.py:162`、`backend/app/services/v102_buyback_unit_svc.py:186`, `:387`）と「バルク系」（`backend/app/tasks/bundle_bulk_monitor.py:37-39`、`scripts/dev/bundle_replay.py:102`）だけ。新しい区分はどれにも当たらない | `git grep -n "kubun_type"`・`git grep -n "シングル系"`・`git grep -n "セット系"`（refs/remotes/origin/main、2026-11-11） |
| 17 | 新しい区分の試験に区分の一覧を持つ試験がある（`backend/tests/test_gemini_raw_copy_v102_product_first.py:636` `_VALID_KUBUNS`）。これは表の検査の作り例で、本番の区分の一覧とは別 | 同ファイル `:636-660` |
| 18 | まとめ売りの読み取り（ADR-1027）は区分を問わず全部の行に当たる。括弧の外の「N枚セット」の行は単位が中身の単位（Piece）・bundle_size=N になる。466062 の行のうち 41 行（うち現行 1）が Piece・bundle_size=30、ほかに Set 145 行・Piece（bundle_size なし）17 行・単位なし 40 行。466088 には Box の行が 8 行ある | `backend/app/services/line_analysis_v102_svc.py:1070-1085`, `:1184-1187`、`backend/app/services/v102_bundle_svc.py:82`, `:98-107`, `:176`、`docs/adr/ADR-1027-bundle-sale-reading.md`、reader ssc-bs1.txt（2026-11-11 17:28 JST、22 行） |
| 19 | 対象 5 商品の今の行（現行）: 466062 は単位なし（理由 unit_unknown）4 行・Piece 2 行（うち bundle_size=30 が 1）・Set 13 行（Sealed box 4・Single 9）。466088 は Box 1・Piece Error 6・Set Sealed box 16。466165 は Piece Error 1・Set Sealed box 2。465992 は Set Single 1、466031 は Set Sealed box 1 | reader ssc-bs2.txt（2026-11-11 20:51 JST） |
| 20 | 本番に単位 Set が有効で在る（`line_units` の code UN0005・canonical Set・is_active True、1 行）。#5 の分岐が使う set_unit はこの行を読む（`backend/app/services/gemini_raw_copy_v102_product_first.py:75`, `:181`, `:407-408`） | reader ssc-setunit.txt（2026-11-11 21:23 JST、1 行） |

## まとめ売りと見られる商品（名前から。中身の確認は便3 の候補表で行う）

この表の「今の現行行」は pk8.txt を読んだ時点の数。今の数は事実 19（ssc-bs2.txt）と下の未確認の欄（ssc-p13.txt、2026-11-12 04:29 JST）を正とする。

| 商品 id | 名前 | 今の現行行 | 今の現行行の状態（reader pk8.txt） |
|---|---|---|---|
| 466062 | 30th CELEBRATION ピカチュウN種コンプリートセット | 17 | Single 15・Sealed box 2 |
| 465992 | テラスタルフェス ブイズRRコンプ | 1 | Single 1 |
| 466031 | ナツコミ 2026 メタキラカード 全22種セット | 1 | Sealed box 1 |
| 466088 | 30th CELEBRATION カードセット9種セット プロモのみ（27枚） | 23 | Sealed box 17・Error 6 |
| 466165〜466173 | 30th CELEBRATION カードセット ○○ プロモのみ（3枚）9 商品 | 3（466165 のみ） | Sealed box 2・Error 1 |

## 未確認

- 上の 13 商品の実物の中身（名前からはシングルカードのまとめ売り。PO は 2026-11-12「1」で 13 商品すべての付け替えを決めた。今の区分は 13 商品ともセット系、現行行は 466062 が 19・466088 が 23・466165 が 3・465992 と 466031 が 1・ほかの 8 商品は 0。reader ssc-p13.txt）。
- v6・v10・v101・GAS の判定への影響（v102 以外は対象外。今回の商品の行は v102）。
