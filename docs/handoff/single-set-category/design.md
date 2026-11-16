<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# design: 区分「シングルセット系」（シングルカードのまとめ売り）

> この文書は何か（専門用語なしの1行）:
> シングルカードのまとめ売りを、在庫の表で「未開封」ではなく「シングル・1セット」と出すための作り方。

親（あるべき姿）: [在庫管理](../../specs/inventory-management/README.md)。現状の調べは [recon.md](./recon.md)（docs/handoff/single-set-category/recon.md）。決めごとは [ADR-1031](../../adr/ADR-1031-single-and-promo-pack-conditions.md) の追補 What 6。型は ADR-1035 追補（サプライ系）の設計 [supply-category/design.md](../supply-category/design.md) に合わせる。

状態: **方針は PO が決めた**（2026-11-11「1」＝商品区分に作る）。設計の起案は 2026-11-11、Opus。設計は審査 5 回目で APPROVE（2026-11-11）。**PO の承認と作業開始の許可**: 2026-11-12「1」（作り方の書類を保存して作業を始める）。便1 の本番反映は別に PO の「GO #番号」を受ける（ADR-136）。審査は末尾。

## 1. あるべき姿（PO の言葉）

> セット・未開封→未開封ではない、シングルカードのまとめ売りだから

> セットの中で分類でシングルセットを登録して、状態をシングルと同じにするのはどう？

> （選択肢）1. 商品区分に「シングルセット」を作る → PO「1」

> （選択肢）1. まとめ売りの商品は、書き方に関わらず単位を「セット」にそろえる → PO「1」（2026-11-11。「N枚セット」と書いた行も、10月17日のまとめ売りの出し方＝ADR-1027 に当てない）

使う人から見て変わること:
- 「ピカチュウN種コンプリートセット」などのまとめ売りが、在庫の表で 状態「Single」・単位「Set」として並ぶ。「未開封」とは出ない。
- 「PSA10」などの語があれば、シングルと同じくその状態になる。
- 「(N枚) ＠値段 在庫数」のように中身の枚数が書かれていても、単位は「Set」になる（例: 値段は 1 セットの値段、数量はセットの数のまま）。要確認（Error）に回らない。
- かっこの外に「N枚セット」と書いた行も、単位「Set」で、商品名に「N枚セット」は付かない。単位の語が無い行も「Set」になる。
- 商品マスタの区分の一覧に「Single set」（シングルセット系）が増える。

## 2. KGI（○×で判定）

| # | 合格条件 | 測り方 | 合格ライン |
|---|---|---|---|
| 1 | まとめ売りの商品（便3 で PO が y をした商品）の v102 現行行のうち、状態の群（`line_conditions.value_group`）が single でない行（Sealed box・Error 等。便3 の手順 3 で外した job の行は数えず、件数を別に PO に見せる。〆の件で状態を前の行から写した行＝condition_basis が `SOLDOUT_REF` か `SOLDOUT_INHERIT` の行（`backend/app/services/line_analysis_v102_svc.py:136`・`:958`、`backend/app/services/gemini_raw_copy_v102_soldout_ref.py:33`、`backend/app/services/gemini_raw_copy_v101.py:1330`）で、状態の群（`line_conditions.value_group`）が single でないものは数えず、別に PO に見せる。写した元の行は本番の表に残らない（同 `:964-1000`）ので、元の job では見分けない） | reader で数える | 0 行 |
| 2 | 同じ商品の v102 現行行のうち、単位が Set 以外の行・単位が空の行・bundle_size が入った行（便3 の手順 3 で外した job の行は数えず、件数を別に PO に見せる。〆の件の単位の写しは単位が空の行だけに効く＝同 `:953`・`:926` なので、Set が入るシングルセット系の行には効かず、除外は要らない） | reader で数える | 0 行 |
| 3 | まとめ売りの商品以外の行で、PO に見せていない 商品・状態・単位・数量・値段 の変化 | 試走の変化の一覧と、書いた後の読み直しを突き合わせる | 0 行 |

## 3. KPI

達成 KGI 数 ◯/3（便3 の再解析の後に数える）。

## 4. recon（要点。詳細と file:line は recon.md）

- 区分「セット系」は状態の語が無いと Sealed box になる（recon 事実 1）。
- シングル系の状態は群 single の 6 行で決まり、語が無ければ Single（事実 3）。
- 群の行の当て方は区分名の部分一致で、「シングル系」は「シングルセット系」に当たらない（事実 4）。
- 「(N枚)」を含む行は、今、数量・値段は正しく、単位だけが枚になっている（事実 14、本番 23 行で確認）。
- 区分名を条件に使うほかの処理（箱系・バルク系）は、新しい区分に当たらない（事実 16）。
- まとめ売りの読み取り（ADR-1027）は区分を問わず全部の行に当たり、かっこの外の「N枚セット」を単位 Piece・bundle_size=30 にする。466062 にこの行が 41 行（うち現行 1）ある（事実 18）。
- 466062 の現行 4 行は単位が空（unit_unknown）。466088・466165 に Piece／Error・Box の行がある（事実 19）。

## 5. design（作り方。3 便に分ける。変更は一度に 1 つ）

### 便1：コード（区分の行が無いうちは今と同じ動き）

| # | 場所 | 前 | 後 |
|---|---|---|---|
| 1 | `backend/app/services/gemini_raw_copy_v102_product_first.py:48-56` 区分の定数 | シングルセット系は無い | `PRODUCT_KUBUN_SINGLE_SET = "シングルセット系"` を足す。コメント「状態はシングル系と同じ群・同じ既定（Single）。単位は書かれた語に関わらず Set（ADR-1031 What 6）」 |
| 2 | 同 `:764-769` `_KUBUN_TO_VALUE_GROUP` | 4 行 | `PRODUCT_KUBUN_SINGLE_SET: (VALUE_GROUP_SINGLE, CONDITION_SINGLE_DEFAULT, BASIS_SINGLE_DEFAULT)` を足す（シングル系と同じ値） |
| 3 | 同 `:769` の直後に新しい表 | — | `_KUBUN_MATCHED_AS = {PRODUCT_KUBUN_SINGLE_SET: PRODUCT_KUBUN_SINGLE}`。意味は「状態の行の適用区分と当てるときに使う区分名」。コメントに recon 事実 4（部分一致では当たらない）を書く |
| 4 | 同 `:782-784` `_resolve_scoped_condition` の中の `resolve_condition_v2(block, "", product_kubun, ...)` | 3 番目の引数が `product_kubun` | `_KUBUN_MATCHED_AS.get(product_kubun, product_kubun)` にする。プロモパック系の要確認の分岐（同 `:788-795`）は変えない |
| 5 | 同 `:858-890` `_resolve_unit_from_state` の先頭 | セット系・サプライ系だけ別の分岐 | 「シングルセット系で `masters.set_unit` があれば、書かれた単位・単位の語が無いことに関わらず単位 Set」の分岐を、関数の最初の分岐として足す。返す値は `(masters["set_unit"], <Set の unit_kubun>, {**unit_basis, UNIT_BASIS_FROM_CATEGORY: PRODUCT_KUBUN_SINGLE_SET, "single_set_unit_from": <書かれた単位>})`（`UNIT_BASIS_FROM_CATEGORY` は同 `:79` の既存の定数。セット系の分岐 `:872` と同じ書き方）。`single_set_unit_from` は書かれた単位が空でも Set でもないときだけ入れる新しいキー（`kubun_unit_from` は「区分の単位の表で置き換えた前の単位」の意味なので使い回さない＝審査 推奨4）。Set の unit_kubun の取り方はセット系の分岐（同 `:869-874`）と同じ。`masters.set_unit` が無いときは何もしない（今と同じ） |
| 6 | 同 `:72` `PRODUCT_KUBUNS_DEFAULTING_TO_BOX` | 箱系・セット系 | 変えない（シングルセット系は入れない） |
| 7 | `backend/app/services/line_analysis_v102_svc.py:690-695` `_SCOPED_GROUP_OF_KUBUN` | 4 つ | シングルセット系 → single を足す（状態の id を single 群の中で引く。PSA10 の2行の取り違えを防ぐ） |
| 8 | `backend/app/services/v102_buyback_unit_svc.py:192-203` `is_candidate` | — | 変えない。対象は「状態の basis が R4 の既定」（同 `:159-172`）か「箱系」（同 `:184-189`）だけ。シングルセット系の既定の basis は R7 なので対象に入らない。K1 の試験で確かめる |
| 9 | `backend/app/services/line_analysis_v102_svc.py:50-60` の読み込み | — | `PRODUCT_KUBUN_SINGLE_SET` を足す |
| 10 | `backend/app/services/line_analysis_v102_svc.py:1184-1187` まとめ売りの読み取り（説明文 `:1073`・コメント `:1187` も） | 全部の行に `_apply_bundle` | 判定を 1 か所に置く小さな関数 `_reads_bundle(item) -> bool`（`item.get("product_category") != PRODUCT_KUBUN_SINGLE_SET`）を `_apply_bundle`（同 `:1070`）の直前に足す。:1184-1187 は `_apply_bundle(...) if _reads_bundle(item) else values` にする。コメント「ADR-1027 追記 2026-11-11：シングルセット系は当てない（PO「1」）」。`_apply_bundle` の処理は変えない（ほかの区分は今と同じ）。説明文 `:1073` の「全ての行に当てる」とコメント `:1187` の「全ての行」に「シングルセット系を除く（ADR-1027 追記 2026-11-11）」を足す |
| 11 | `scripts/dev/bundle_replay.py:36`・`:98-106` 規則の当て直しの台本 | 全部の行に当てる。判定はループの中に直書き | ①`:36` の `_BULK_KUBUN` の次の行に `_SINGLE_SET_KUBUN = "シングルセット系"` を足す（コメントは :36 と同じ形で「= gemini_raw_copy_v102_product_first.PRODUCT_KUBUN_SINGLE_SET。一致は test_single_set_category.py で固定」）。②`:99-104` を関数 `replay_row(r, unit_words, set_words) -> (before, res, is_bulk)` に切り出し、`main` のループはそれを呼ぶだけにする（出力の形・数は今と同じ）。③`replay_row` の中で `kubun_type` がシングルセット系の行は before・res とも None を返す（本番と同じ数を出すため。ADR-1027 維持の仕組み）。④説明文 `:1`・`:13-14` に「シングルセット系の行は当てない。区分名だけは写す（:36 と同じ理由）」を足す |
| 12 | `scripts/accuracy/llm_compare/fhd_snapshot.py:87-88` 精度試験の変換器 | 本番の `_write_results` と同じ式で全部の行に `_apply_bundle` | 本番と同じく `S._apply_bundle(...) if S._reads_bundle(it) else v` にする（この台本の check は本番の写しと比べ、説明の無い差が 1 件でもあれば止まる＝同 :8-9。本番だけ変えると、便3 の後にシングルセット系の行が差になる）。この変換器は本番の worker の /app を読む（同 :5-6）ので、便1 の本番反映の後に使う |
| 12b | `scripts/accuracy/llm_compare/README.md:21` 写しの記録 | 変換器の sha256 `cd63545e…` | #12 の後の sha256 に書き換え、「2026-11-11 シングルセット系をまとめ売りの読み取りから外した（ADR-1027 追記）。便1 の本番反映の後に使う」を足す |
| 13 | 試験 | — | 新しい試験ファイル backend/tests/test_single_set_category.py を足す（受入 K1a〜K1c）。既存の試験ファイルは変えない |

触らない範囲:
- 状態の行（DB の line_conditions）・区分ごとの単位の表（ADR-1041 の設定）・買取の処理・セット系とシングル系の判定・画面（区分の一覧は DB から読む。recon 事実 8）。
- `_apply_bundle`・`detect_bundle` の中・相場の照らし合わせ・買取の処理の中は変えない。
- migration・deploy.yml は触らない。`scripts/` の 2 本（#11・#12）と説明書（#12b）は手で動かす読み取り専用の台本で、本番の動きは変えない。ただし process-artifacts gate は `scripts/` 全体を危険な道として承認を求める（`docs/adr/ADR-135-release-stowaway-prevention.md:39-41`）ので、便1 の PR は ADR-136 の GO の手順を通す。
- ほかに `_apply_bundle`・`detect_bundle` を呼ぶ所は無い（origin/main で `git grep`。本番 `backend/app/services/line_analysis_v102_svc.py:1185`、台本 2 本だけ。/tmp/CC報告ファイル/ssc-rev2b.txt）。

実装カード（便1 の実装承認の後に作る）で、各行の変更前後のコードを全文で書く。

### 便2：区分 1 行（記録 SQL。migration には書かない＝ADR-1007）

| 表 | 入れる値 |
|---|---|
| tcg_product_categories | code `PC_SINGLE_SET`・display_name `Single set`・kubun_type `シングルセット系`・is_active TRUE・tenant_id NULL（共用） |

- 順序: 便1 のコードが本番に出てから入れる。
- 01_precheck で、code と kubun_type が今の行と重ならないことを確かめる。
- この時点では、どの商品もこの区分に入っていないので、解析の結果は変わらない。

### 便3：商品の付け替え（候補表 → PO の y → 付け替え → 試走 → PO の了解 → 再解析）

1. 候補表を PO に見せる（recon「まとめ売りと見られる商品」の 13 商品。商品ごとに名前・中身・今の現行行の数）。PO が y をした商品だけを付け替える。
   - PO の決定（2026-11-12「1」）: 13 商品すべてを付け替える（465992・466031・466062・466088・466165〜466173）。一覧は reader で読んだ名前・今の区分（13 商品ともセット系）・今の現行行の数（/tmp/CC報告ファイル/ssc-p13.txt、2026-11-12 04:29 JST）。中身は名前から読んだもので、実物は確かめていない。
2. 付け替えは記録 SQL（前後の区分と audit を残す）。
3. 対象の job を選ぶ: 付け替えた商品の v102 の行を持つ job（置き換え済みも含む）。人の手で直した跡がある job・v102 でない job・完了していない job は外す（466062 で使った試走の台本と同じ選び方を、商品の一覧に広げる）。外した job の数と行の数は PO に見せる。外した job の id の一覧はファイルに残し（/tmp/CC報告ファイル/ と記録の置き場の両方）、K5 の reader の数え方はこの一覧を使って外す。
4. 解析し直す順は、投稿の日時の古い順にする。〆の件は前の投稿の行の状態を写し（`backend/app/services/line_analysis_v102_svc.py:941-963`）、価格の引き継ぎは前の投稿の行の値段を読む（同 `:1350-1368`）ので、前の投稿を先に直しておく。
5. 試走（書き込みなし）で、対象の行と、同じ投稿のほかの商品の行の変化を全部集め、PO に見せる。道具: 本物の `_write_results` を、最後に取り消す取引の中で通す台本（まとめ売り・相場・〆・引き継ぎまで通すため。`backend/app/tools/v102_replay_diff.py` はまとめ売りを当てないので使わない。466062 の試走の台本はリポジトリに無く、どこまで通すかは確かめていない）。便3 の実装カードで台本を作り、その出力を K6 の changes.json とする。この台本は書き込んでから取り消すので、書く権限が要る。PO が `!` で流し、ロック待ちの上限（ADR-1037）を付け、成否に関わらず必ず取り消す（最後に ROLLBACK、途中で落ちても取引を閉じる）。精度試験の `scripts/accuracy/llm_compare/fhd_snapshot.py`（読み取り専用の取引）とは別の道具。集める項目: 商品・状態・単位・数量・値段・price_basis（引き継ぎの印 INHERIT: の増減）・bundle_size・要確認・理由。
6. PO の了解の後、試走と同じ変化の仕入元だけを書く（試走と違えば飛ばす）。書く前の全行を残す。

### 値の決め方の理由

1. 区分を新しく作る: PO の決定「1」。区分を見て状態の決め方を選ぶ今の作り（ADR-1031）をそのまま使える。決め方の置き場所はコードの区分の表 1 か所のまま。
2. 状態の群はシングル系と同じ（行を足さない）: PO「状態をシングルと同じにする」。PSA10 などの語の当て方もシングル系と同じになる。
3. 当てるときは区分名をシングル系に読み替える（便1 #3・#4）: 状態の行の適用区分は「シングル系」で、部分一致では新しい区分名に当たらない（recon 事実 4）。行の適用区分を書き換える方法は、6 行を書き換え、ほかの道（v6 等）の当たりにも効くので採らない。
4. 単位は書かれた語に関わらず Set: まとめ売りの原文は「(N枚)」と中身の枚数を書く（recon 事実 12・14）。枚を残すと、1 セットの値段が 1 枚の値段に見える。サプライ系の「N枚入」と同じ理由（ADR-1035 追補）。
5. まとめ売りの読み取りに当てない（便1 #10〜#12）: PO「1」。商品そのものがまとめなので、「N枚セット」の行だけ単位が枚・商品名に「N枚セット」が付くと、同じ商品が2通りに出る（recon 事実 18）。外すかどうかの判定は関数 `_reads_bundle` の1か所に置き、本番と精度試験の変換器はそれを呼ぶ。当て直しの台本は純関数だけを読む作り（`scripts/dev/bundle_replay.py:36` の注記）なので区分名を写し、一致を試験で固定する（`_BULK_KUBUN` と同じ前例）。まとめ売りの規則（`backend/app/services/v102_bundle_svc.py`）は変えない。
6. 区分名「シングルセット系」・表示名「Single set」: PO の言葉「シングルセット」に、区分名の書き方（〜系）と表示名の書き方（英語）を合わせた。

### 代替案

1. **細分類に「シングルセット」を作る**: 採らない。PO が「1」（商品区分）を選んだ。解析が区分と細分類の2か所を見ることになる。
2. **まとめ売りをシングル系に戻す**: 採らない。単位が枚のままで、1 セットの値段が 1 枚の値段に見える（recon 事実 14）。
3. **状態の行の適用区分に「シングルセット系」を足す**: 採らない（理由 3）。

## 6. 弊害・トレードオフ

| 弊害・リスク | 対処 |
|---|---|
| 区分名の部分一致: 将来、適用区分「セット系」の状態の行を作ると、「シングルセット系」にも当たる（`backend/app/services/tcg_analyzer_svc.py:818-819`） | 今「セット」を含む適用区分の行は 0 件（reader pk10.txt）。シングルセット系は群の行だけで判定し、当てるときはシングル系の名前を渡す（便1 #4）ので、この経路は通らない。維持の仕組みに人手の確かめを書く |
| まとめ売りの投稿で、バラ 1 枚の値段を書いた行まで Set になる | 商品の照合が「まとめ売りの商品」に当たった行だけが対象。試走の変化を PO に見せてから書く（便3） |
| コードより先に値を入れると、新しい区分の商品が Error になる | 順序を固定する: ①便1 の本番反映 → ②便2 → ③便3 |
| 同じ投稿のほかの商品の行も変わる（解析し直しは投稿ごと） | 試走で全部集めて PO に見せる。了解した変化と同じ仕入元だけ書く |
| 区分の分岐が 1 つ増え、`_resolve_unit_from_state` の if が 3 つになる | 前例（サプライ系）と同じ形にそろえ、試験で区分ごとに縛る |
| 〆の規則 11b は R4 の basis だけを既定扱いにする | R7 はシングル系と同じ扱いになる。変えない |
| 相場との照らし合わせ（`backend/app/services/line_analysis_v102_svc.py:1027-1034`、`backend/app/services/v102_unit_price_check_svc.py`）: シングルセット系の行は bundle_size が無いので照らし合わせの対象に入る。便3 の途中は、ほかの投稿の Piece の相場が残り、Set にした行に要確認の理由 unit_price_mismatch が付くことがある | 便3 の試走で、要確認・理由の変化も集めて PO に見せる。付いた行は、全部を解析し直した後にもう一度試走して消えるかを数える |
| まとめ売りの読み取りを外すので、まとめ売りに無い「決まらない」（bundle_unverified）の要確認も付かなくなる | シングルセット系はもともと商品がまとめなので、要確認にする理由が無い。K1 で確かめる |
| 価格の引き継ぎ（`backend/app/services/line_analysis_v102_svc.py:1376-1421`）は bundle_size の入った行を外す（同 `:1383`）。シングルセット系の行は bundle_size が入らなくなるので、値段が無く数がある行に、48 時間以内の同じ仕入元・同じ商品・同じ状態の値段が新しく引き継がれる。引き継ぎ元は bundle_size の無い行だけ（同 `:1359`）だが、前の行の単位は見ない（同 `:1350-1368`）ので、前の行が bundle_size の無い Piece の行（recon 事実 18・19 の Piece の行等）なら 1 枚の値段が 1 セットに入りうる | 解析し直しは古い投稿から（便3 手順 4）で、前の行も Set にそろえてから引き継ぐ。試走で price_basis の INHERIT: の増減を集めて PO に見せる（便3 手順 5）。増えた行は 1 行ずつ前の行の単位を見せる |
| 〆の件は前の投稿の行の状態を写す（`backend/app/services/line_analysis_v102_svc.py:941-963`）。人の手で直した跡があって外した job の行が Sealed box のままなら、それを写した〆の件も Sealed box のまま残る | KGI 1・2 で外した job の行は別に数えて PO に見せる。外した job の扱いは便3 の後に PO に聞く（未解決に書く） |

## 7. 外部・過去事例の参照と我々への応用

- 社内の前例 ADR-1035 追補（サプライ系）: 区分を 1 つ足し、書かれた単位（枚入）より区分の単位を優先した。同じ理由・同じ形で使う。
- 社内の前例 ADR-1031: 区分ごとに状態の群を切り替える仕組み。群の行はそのまま使う。
- 外部事例: 該当なし。社内の区分と状態の決めごとで、外部の数値を根拠にする種類の話ではないため。

## 8. 受入条件

| 基準 | 検証方法 |
|---|---|
| K1a 判定の段（`resolve_product_first` を呼ぶ）: シングルセット系の商品で「(N枚) ＠値段 在庫数」が 単位 Set・状態 Single・basis R7・`single_set_unit_from` が Piece／単位の語が無い行も単位 Set・`single_set_unit_from` なし／「PSA10」の語があれば状態 PSA10／書かれた単位が Set なら `single_set_unit_from` なし／`masters.set_unit` が無ければ、同じ入力のシングル系と同じ単位（書かれた単位のまま、単位の語が無ければ状態の単位＝`backend/app/services/gemini_raw_copy_v102_product_first.py:880-890`）／セット系の商品は今と同じ Sealed box／シングル系の商品の単位は今と同じ | CI（新しい試験ファイル） |
| K1b 書き込みの段（本物の `_write_results` を偽の接続で呼び、INSERT に渡る値を見る。前例 `backend/tests/test_v102_bulk_price.py:150-155` の `_write`。式を試験に写さない。masters には `product_first`（`scoped_cond_entries` に single 群の行。作り方は `backend/tests/test_adr1031_single_promo_pack.py:71-75`）と単位の別名（`backend/tests/test_v102_bulk_price.py:147` の `ALIASES_MASTERS` 相当）を入れる。渡す件は unit "Set"・condition "Single"・condition_basis "R7:単品既定"・product_category シングルセット系・unit_basis `{"alias": None}`（`backend/app/services/v102_buyback_unit_svc.py:165-167` は unit_basis が Mapping でないとすぐ False を返す。Mapping を渡して、False が R7 の既定によることを確かめる）。`is_buyback_candidate` は INSERT の列ではないので直接呼んで False を見る）: シングルセット系の「12枚セット @2500円 在庫4」が 単位 Set・bundle_size None・数量 4・値段 2500・要確認なし／同じ本文のセット系・シングル系の行は今と同じ（Piece・bundle_size=12）／状態の id が single 群の行（`_scoped_condition_id`）／`is_buyback_candidate` が False | CI（新しい試験ファイル） |
| K1c 当て直しの台本と精度試験の変換器: ①`_SINGLE_SET_KUBUN` が `PRODUCT_KUBUN_SINGLE_SET` と同じ値／②`replay_row` に kubun_type シングルセット系・本文「12枚セット @2500円 在庫4」の行を渡すと before・res とも None、kubun_type セット系の同じ行は今と同じ当たり（kind decided・N 12）／③`_reads_bundle` がシングルセット系だけ False／④`scripts/accuracy/llm_compare/fhd_snapshot.py` の本文に `S._reads_bundle(` がある（文字で確かめる。この台本は本番の worker で動くため CI では走らせない） | CI（新しい試験ファイル）。台本は `backend/tests/test_v102_bundle.py:193-198` と同じ読み込み方（`importlib` で読み、`main` は走らない）で `replay_row` を呼ぶ |
| K2 既存の試験が通ること。既存の試験ファイルに変更が無いこと（`backend/tests/test_v102_bundle.py:193-198` の `_BULK_KUBUN` の試験も今のまま通る） | CI と `git diff --name-only` |
| K3 便1 の本番反映の時点で、シングルセット系の商品が 0 件であること（＝新しい分岐を通る行が無い） | reader で区分ごとの商品数を数える |
| K4 便2 の後、区分 PC_SINGLE_SET が 1 件あり、ほかの区分の行が変わっていないこと | 記録 SQL の 03_verify |
| K5 便3 の再解析の後、KGI 1・2 が 0 行 | reader で数える |
| K6 便3 で、KGI 3 が 0 行。試走で要確認・理由・bundle_size の変化も集める | 試走の changes.json と、書いた後の reader の読み直しを突き合わせる |

## 9. 戻し方

- 便1: コードを revert する。区分の行が無ければ今と同じ動き。
- 便2: 区分の行を is_active=false にする（商品が付いていない間だけ）。
- 便3: 商品を元の区分に戻し、書く前の全行（before_snapshot）を見て対象の job を再解析する。

## 10. 接触面分析（6面）

逆参照: 変更する名前（`_KUBUN_TO_VALUE_GROUP`・`_SCOPED_GROUP_OF_KUBUN`・`_resolve_unit_from_state`・`_apply_bundle`・`detect_bundle`・区分名「シングル系」「セット系」・kubun_type）を origin/main 全体で `git grep` した（recon 事実 16・17。`_apply_bundle`・`detect_bundle` は 2026-11-11 f3ff55057 で、本番 1 か所と台本 2 本）。

| 面 | 影響 |
|---|---|
| ①人 | PO・管理者: 区分の一覧に「Single set」が 1 つ増える。まとめ売りの商品を登録するとき、この区分を選ぶ（維持の仕組み） |
| ②エージェント | 商品マスタの登録をする担当: 候補表の区分の欄で、箱のセットとまとめ売りを分ける。並行セッションへの周知は台帳（active-work.d）で行う |
| ③機械 | まとめ売りの読み取り（`_apply_bundle`）はシングルセット系を外す。当て直しの台本（`scripts/dev/bundle_replay.py`）と精度試験の変換器（`scripts/accuracy/llm_compare/fhd_snapshot.py`）も同じに外す。価格の引き継ぎがシングルセット系の行に新しく効く（弊害の表）。CI の試験: 新しい試験 1 本。既存の試験は変えない（`backend/tests/test_adr1035_booklet.py:158` 等は辞書の 1 キーだけ見るので、キーが増えても通る）。定期の作業（`backend/app/tasks/bundle_bulk_monitor.py`）はバルク系だけを数えるので影響なし |
| ④データ | 便2 で区分 1 行、便3 で商品の区分と v102 の行が変わる。共用マスタ（tenant_id NULL）。テナントの在庫の行は再解析で書き換わる。すべて試走 → PO の了解の後 |
| ⑤本番 | 便1 は migration なし。ただし `scripts/` を触るので ADR-136 の手順（PO の「GO #番号」を受けてからマージ・PR 本文に GO 記録）を通す。便2・便3 は記録 SQL と再解析（PO の ! 実行）。監視の変更なし |
| ⑥外部 | 閲覧ページのお客さん: まとめ売りの行が「Single・Set」で見える。外部 API の変更なし |

## 11. 審査（Architect・同じ AI による自己審査。独立した第二者のレビューではない）

**判定: APPROVE（2026-11-11 reviewer の指摘と PO「1」を反映した後。便1 は実装可能。便2・便3 は前の便の本番反映の後。便3 の商品は PO が 2026-11-12「1」で 13 商品すべてと決めた）**

- 既存仕様との整合: ADR-1031 の群の仕組み・ADR-1035 の区分の単位の前例・ADR-1007（値は記録 SQL）・ADR-1041（表は変えない）に沿う。migration・deploy.yml は無い。`scripts/` を触るので ADR-135 の危険な道に当たり、ADR-136 の GO の手順を通す（便1 触らない範囲）。
- 根拠: 変更箇所はすべて file:line で確かめた（recon）。部分一致で当たらないことはコード `backend/app/services/tcg_analyzer_svc.py:818-819` で確かめた。買取の対象外は `backend/app/services/v102_buyback_unit_svc.py:159-172`、`:192-203` で確かめた。実際の動きは K1 の試験で確かめる。数量・値段が今正しいことは本番 23 行で確かめた（recon 事実 14）。
- 受入条件: K1〜K6 はすべて CI か reader の数で ○× が決まる。
- 実装範囲: 便1 の変更は 5 ファイル（v102 の判定・v102 の書き込み・当て直しの台本・精度試験の変換器とその説明書）＋試験 1 本。触らない範囲を明記した。
- 未解決: 人の手で直した跡がある投稿の扱い（便3 の後に PO に聞く）。便1 の実装を止めない。

## 12. 審査（reviewer・別の Opus の起動による審査）

**判定: REVISE（2026-11-11。読み取りのみ・d57728133 で照合）**

| # | 重さ | 指摘 | 対応 |
|---|---|---|---|
| 1 | 必須 | まとめ売りの読み取り（ADR-1027）を調べていない。`backend/app/services/line_analysis_v102_svc.py:1184-1187` が全部の行に `_apply_bundle` を当て、括弧の外の「N枚セット」は単位 Piece・bundle_size=30 に書き換える（同 `:1085`、`backend/app/services/v102_bundle_svc.py:82`, `:176`）。便1 で Set にしても書き込みの前に戻る。ADR-1027 What 3「単位は中身の単位」と食い違う | Opus が本番で確かめた: 466062 に Piece・bundle_size=30 の行が 41 行（うち現行 1）ある（recon 事実 18）。シングルセット系をまとめ売りの読み取りから外すか、ADR-1027 の表し方を受け入れるかは PO の判断。PO に1件聞く |
| 2 | 必須 | K1 の数量・値段を確かめる関数が決まっていない（`resolve_product_first` は数量・値段を返さない。列になるのは `backend/app/services/line_analysis_v102_svc.py:770-771`） | 指摘 1 の答えの後、K1 を「`resolve_product_first`」と「`_analysis_values`／`_apply_bundle` の後」の2段に分けて書く |
| 3 | 推奨 | 相場との照らし合わせ（`backend/app/services/v102_unit_price_check_svc.py`）で、便3 の途中に要確認の理由が付きうる | 弊害の表に足し、便3 の試走で要確認の変化も PO に見せる |
| 4 | 推奨 | 記録キー `kubun_unit_from` を別の意味で使い回す | 新しいキーにする |
| 5 | 推奨 | recon の書き違い3か所（定数の参照元・箱系の一覧の抜け・`:223`→`:222`） | recon を直す |
| 6 | 推奨 | ADR-1031 の追補で「関連」「測り方」「維持の仕組み」に行が無い | 足す |
| 7 | 推奨 | 便1 #3〜#5 の変更後のコードの形を書く。親の仕様書に子の一覧が無い | 足す |

状態: 指摘 1 は PO「1」（2026-11-11）で決まり、便1 #10・#11、K1b・K1c、ADR-1027 追記に反映した。指摘 2 は K1a／K1b に分けた。指摘 3 は弊害の表と K6、指摘 4 は新しいキー `single_set_unit_from`、指摘 5 は recon、指摘 6 は ADR-1031 の「関連」「測り方」「維持の仕組み」、指摘 7 は便1 #5・#10 に後の形を書き、索引 `docs/specs/README.md` に行を足した。

### 2 回目の審査

**判定: REVISE（2026-11-11。書類の直しだけ。前の 7 件は全部直っていると確認。ほかの区分に影響が無いこと・単位が空の行も Set になること・file:line はすべて一致と確認）**

| # | 重さ | 指摘 | 対応 |
|---|---|---|---|
| 1 | 必須 | 精度試験の変換器 `scripts/accuracy/llm_compare/fhd_snapshot.py:87-88` も `_apply_bundle` を本番と同じ式で呼ぶ。check は説明の無い差で止まる | 便1 #12 に足した。判定は関数 `_reads_bundle` の 1 か所（#10）。接触面③・逆参照・runbook・ADR-1027 追記に書いた |
| 2 | 必須 | K1c が決まっていない。K2「既存の試験は変えない」とぶつかる | 定数 `_SINGLE_SET_KUBUN` の置き場（:36 の次）・一致の試験・`replay_row` の切り出しを便1 #11 と K1c に書いた。試験は新しいファイルだけ |
| 3 | 推奨 | KGI 1・2 は〆の写しと外した job で 0 にならないことがある | KGI 1・2 で外した job の行を数えず別に見せる。解析し直しは古い投稿から（便3 手順 4）。弊害の表に足した |
| 4 | 推奨 | 価格の引き継ぎがシングルセット系の行に新しく効く | 弊害の表に足し、便3 の試走の項目に price_basis を足した |
| 5 | 推奨 | 理由の番号の並び・維持の仕組みの位置 | 番号を 1〜6 に直し、維持の仕組みを末尾に移した |

### 3 回目の審査

**判定: REVISE（2026-11-11。書類の直しだけ。2 回目の 5 件は本文に入っていると確認。便1 の表の行番号は全部一致。`replay_row` の切り出しで既存の動き・既存の試験は変わらないと確認。まとめ売りの判定を写す所は本番と台本 2 本だけと確認）**

| # | 重さ | 指摘 | 対応 |
|---|---|---|---|
| 1 | 必須 | ADR-135/136 の扱いが §5 と §10⑤・§11・recon 観点4 で食い違う（`scripts/check-process-artifacts.js:1025`） | §10⑤・§11・recon 観点4 を「scripts/ を触るので ADR-136 の GO の手順」にそろえた |
| 2 | 必須 | K1b が式を試験に写す形で、本番が `_reads_bundle` を呼び忘れても通る。変換器を見張る試験が無い | K1b を本物の `_write_results` を偽の接続で呼ぶ形に変えた。K1c ④で変換器の本文を確かめる |
| 3 | 推奨 | 変換器の説明書の sha256 の記録が合わなくなる。変換器は本番反映の後に使う | 便1 #12b と #12 の注記に足した |
| 4 | 推奨 | 価格の引き継ぎの例が誤り（引き継ぎ元は bundle_size の無い行だけ＝`:1359`） | 例を bundle_size の無い Piece の行に直した |
| 5 | 推奨 | 「全ての行」と書いた古い説明が残る | ADR-1027 What 2 に注記。便1 #10・#11 に説明文とコメントの書き換えを足した |
| 6 | 推奨 | K1a の set_unit が無いときの答え | シングル系と同じ単位と書いた |
| 7 | 推奨 | KGI 2 の〆の除外の見分け方 | KGI 2 は除外が要らない理由を書いた。KGI 1 に condition_basis `SOLDOUT_REF` で見分ける除外を書いた |

### 4 回目の審査

**判定: REVISE（2026-11-11。必須 1・推奨 4。3 回目の 7 件は解消と確認。便1 #1〜#12b の行番号は f3ff55057 で全部一致。K1c ② の当たり（decided・N 30・Piece）を純関数で動かして確認）**

| # | 重さ | 指摘 | 対応 |
|---|---|---|---|
| 1 | 必須 | KGI 1 の〆の除外が SOLDOUT_REF だけ。SOLDOUT_INHERIT も状態を写す。写した元の行は本番の表に残らず、reader で見分けられない | 2 つの basis の行で状態が single 群の外のものを数えず、別に見せる形にした（元の job では見分けない） |
| 2 | 推奨 | K1b の材料（masters の product_first・渡す件・`is_buyback_candidate` の確かめ方） | K1b に書いた |
| 3 | 推奨 | #5 は既存の定数 `UNIT_BASIS_FROM_CATEGORY` を使う | #5 を直した |
| 4 | 推奨 | 便3 の試走の道具が決まっていない | 便3 手順 5 に「本物の `_write_results` を取り消す取引の中で通す台本を便3 の実装カードで作る」と書いた |
| 5 | 推奨 | 索引の行が完売の規則の子に入っている | 在庫管理の直下に移した |

### 5 回目の審査

判定: APPROVE（設計合格）。必須の指摘なし。推奨 4 件を下のとおり反映した。生の出力は /tmp/CC報告ファイル/ に残した。

| # | 区分 | 指摘 | 直し |
|---|---|---|---|
| 1 | 推奨 | K1b の `is_buyback_candidate` が False でも、unit_basis が無いとすぐ False になるので意味が無い | K1b に unit_basis `{"alias": None}` を渡すと書いた |
| 2 | 推奨 | 外した job の一覧が K5 の数え方とつながっていない | 便3 手順 3 で一覧をファイルに残し、K5 がそれを使うと書いた |
| 3 | 推奨 | KGI 1 の「single 群の外」と「Sealed box／Error」の言い方がそろっていない | KGI 1 を `line_conditions.value_group` が single でない行にそろえた |
| 4 | 推奨 | 便3 の試走は書いて取り消すので書く権限が要る | PO の `!` 実行・ロック待ちの上限（ADR-1037）・必ず取り消すを便3 手順 5 に書いた |

審査で確かめていなかったことの確認:
- 本番に単位 Set（`line_units` の code UN0005）が有効で在るか: 在る（2026-11-11 reader で 1 行、canonical Set・is_active True。/tmp/CC報告ファイル/ssc-setunit.txt）。recon 事実 20。
- K1b が偽の接続で `_unit_price_mismatches` を通るか・SOLDOUT_INHERIT の道が #5 の分岐に届くか: 確かめていない。K1b は便1 の CI で通るかで決まる（通らなければ実装役が止まって返す）。SOLDOUT_INHERIT は状態を写す道で単位の分岐には関わらず、KGI 1 で別に数える。

試験の本文の例は、仕入元の原文に無い数で組んだ（「12枚セット @2500円 在庫4」。2026-11-12 に confidential-quote-guard の原文の写しと照らして当たりなし）。原文と同じ語句は公開の置き場へ送れない。

## 13. 維持の仕組み

- 守り手: backend/tests/test_single_set_category.py（便1 で足す。区分の状態の群・単位 Set・まとめ売りの読み取りの対象外・当て直しの台本と精度試験の変換器の対象外・台本の区分名の写しの一致・買取の対象外を縛る）
- 対象: シングルセット系の商品が Sealed box や枚の単位に戻ること。本番と台本 2 本で、まとめ売りの読み取りの対象がずれること。
- 人手で守る: 状態の行の適用区分に「セット系」を書くときは、シングルセット系に当たらないことを確かめる（部分一致のため。機械で見張る仕組みが無い）。まとめ売りの商品を登録するときはシングルセット系、箱のセットはセット系を選ぶ（登録規則 C3 の候補表に区分を書く）。担当は Opus（記録 SQL・候補表を作るときに、この設計と照らす）。
