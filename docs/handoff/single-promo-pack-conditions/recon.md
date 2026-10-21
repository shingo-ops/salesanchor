# recon: シングル系の状態5つ と プロモパック系の区分（v102）

起案 2026-10-19（Opus）。基準 origin/main `b0299d3fc`。本番は AI 用読み取り専用の道（ADR-1024）で 2026-10-19 07:11 JST に取得した v102 現行行 4,424 行。
試算・取得の生データは社外秘のため本リポジトリに置かない（仕入元の原文を含む）。ここには件数とコードの位置だけを書く。

## 既存 ADR の検索

`git grep -il "FLAG_SINGLE\|value_group\|kubun_type\|単位不明" docs/adr/` と `docs/adr/FEATURE-INDEX.md` で以下を確認した。

- ADR-1023 状態の価値順（value_group / value_rank）。本件はこの群を2つ（single / promo_pack）足す。
- ADR-1021 バルク系の既定状態 Bulk（区分で既定状態を決める前例。basis「R6:バルク既定」）。
- ADR-1007 状態マスタなどの値は migration でなく、記録した SQL で入れる。
- ADR-158 置き換え済み投稿の行も配信に残る（配信件数の数え方）。

## 現在地（file:line）

1. 状態の照合の主ループは `backend/app/services/tcg_analyzer_svc.py:918-934` にある。適用区分は `app_kubun_matches`（`:772-801`）で比べ、部分一致で判定する（「単位不明」は空か「不明」のときだけ当たる）。
2. 語が当たらないときの既定は次のとおり（`backend/app/services/tcg_analyzer_svc.py:936-982`）。
   - 箱系大は Case、箱系は Sealed box（`:939-944`）。
   - パック系は Searched pack（`:949-962`）。
   - 照合した商品が箱系なら、箱系としてもう一度判定する（R4c、`:967-979`）。
   - それ以外は `FLAG_SINGLE` + 「R4:単位既定:単位不明」（`:981-982`）。
3. v102 は `FLAG_SINGLE` + 単位不明を Error（CN0012）と要確認 condition_unknown に変える（`backend/app/services/gemini_raw_copy_v102_product_first.py:560-567`）。
4. v102 の区分の分岐は `backend/app/services/gemini_raw_copy_v102_product_first.py:570-589` にある。
   - 箱系とセット系の商品は、単位区分を箱系に置き換えて判定する（`:574-579`）。
   - バルク系は Bulk にする（`:581-587`）。
5. シングル系（kubun_type「シングル系」）の商品には、専用の分岐が無い。単品の単位 Piece は単位区分「単品系」のため、CN0008（適用区分「枚系,単位不明」）に当たらず、2. の既定から Error になる。
6. 複数の行が当たったときは、価値の低い行（value_rank が最大の行）を採る（`backend/app/services/tcg_analyzer_svc.py:848-866`、ADR-1023）。
7. REGEX の行は `re.search` をそのまま使う。小文字化と全角の正規化はしない（`backend/app/services/tcg_analyzer_svc.py:1332-1344`）。REGEX の行は主ループで使える（`:835-841`）。
8. KEYWORD の英数字の語の境界は、英字だけで判定する（数字は境界にならない）。このため「psa10ar」は PSA10 に当たらず、PSA1 に当たる（下の本番の観測の 4.）。
9. 状態マスタの全行を読むのは `load_condition_entries`（`backend/app/services/tcg_analyzer_svc.py:652-769`）。v6・v10・v101・shadow・単位の復元も同じ関数を使う。v102 は `load_v102_masters`（`backend/app/services/line_analysis_v102_svc.py:201-217`）から呼ぶ。
10. v102 は、状態の名前をマスタで引けないとき `FLAG_SINGLE` に落とす（`backend/app/services/line_analysis_v102_svc.py:630-641` `_condition_columns`）。
11. 配信は `FLAG_%` と effect EXCLUDE だけを外す（`backend/app/services/tcg_distribution_svc.py:230-239`）。名前の一覧は持たないので、新しい状態名はそのまま配信に出る。
12. 並び順の群は `backend/app/services/tcg_result_order.py:11` の `VALUE_GROUP_ORDER = ("case","box","pack")`。一覧に無い群は「順位なし」として最後に並ぶ。
13. 状態の色は `frontend/src/features/inventory/conditionBadge.ts:1-37` で決める。一覧に無い名前は既定の色になる。
14. `backend/app/services/condition_vocab.py` と `inventory_aggregation.py:79-82,186-199,259-323` は public.inventory 側の名前の一覧で、v102 の配信の経路では使わない。今ある Searched pack・Opened box・Bulk も、この一覧には入っていない。
15. DB の制約は次のとおり。
   - `line_conditions_value_group_check` が許す値は box / case / pack だけ。
   - `uq_conditions_code` で code は一意。canonical には一意の制約が無い。
   - `tcg_product_categories.kubun_type` には CHECK 制約が無い。

## 本番の観測（読み取りのみ・件数）

1. 区分ごとの v102 現行行は、箱系 2,645、バルク系 33、セット系 85、シングル系 85、区分なし 1,576。
2. 今のコードで試算を再現すると、4,400/4,424 行（99.46%）が本番と一致した。不一致の 24 行は、後段で上書きされた行。
3. 案（design.md）を当てると、変わるのはシングル系の 85 行だけで、他の区分の変化は 0 行。
   - Error→Single 64
   - Searched pack→Single 10
   - FLAG_SINGLE→Single 8
   - Error→PSA10 1
   - Case→Single 1
   - Unsearched pack→Single 1
4. PSA の行を REGEX にした場合、PSA を含む本番の 212 行で KEYWORD 案と違うのは 1 行だけ。「psa10ar…」が PSA7以下（誤り）から PSA10 に直る。
5. 新しく配信に出る行は、48 時間の窓ありで 15 行、窓なしで 30 行。配信から外れる行は 0。
6. プロモパック候補 6 商品（440525・466083・466059・466077・424595・440456）は、今はシングル系（区分 2）。
   - 現行行は 24 行（440456 は 0 行）。
   - 原文に「開封済」「PSA10」「鑑定」と書かれた行は 0。
   - プロモパック系へ移すと、24 行すべてが「未開封」になる。
7. 「開封済み」「PSA10」の判定は、本番に実例が無いため、作った例文で確かめた。
   - 「未開封」「開封前」「新品未開封」「開封していない」「開封なし」は「開封済み」に当たらない。

## 未確認

- 既存のテストへの影響（まだ実行していない。実装の便で CI を回して確かめる）。
- GAS 在庫一覧の本番の版で、新しい状態名がどう出るか（読んだのは 10/18 に取得した写しで、色は既定、絞り込みの候補は値から自動で増える）。
- 466059・424595・440456 がパック形であることを示す公式の出典。今は非公式の出典が 1 つずつしかない。
