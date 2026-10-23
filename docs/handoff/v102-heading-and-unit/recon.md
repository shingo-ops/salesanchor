# recon: 状態の見出しと、区分に合わない単位（v102）

基準: origin/main `cc000952f`（2026-10-23 fetch）。調べた人: Opus（読み取りは Sonnet に任せ、生出力は社外秘フォルダ `~/CC報告ファイル-keep/shime-auto-check/heading-fix/formal-recon/`）。
設計: [design.md](./design.md)

## 1. 既存 ADR の検索

- キーワード: 単位・区分・見出し・v102・状態。`docs/adr/FEATURE-INDEX.md` で当たるのは 21 行目（まとめ売り / ADR-1027）だけ。
- 関係する ADR:
  - ADR-1035 `docs/adr/ADR-1035-condition-unit-and-booklet-category.md`: 状態ごとの単位（Case／Box／Pack）と区分「ブックレット系」。What 2 では、状態が原文の語で決まったら状態の単位を優先する。
  - ADR-1036 `docs/adr/ADR-1036-price-decides-unit.md`: 単位が「個」・無記入の箱系の行は、値段で Box／Case／Pack を決める。
  - ADR-1031: シングル系・プロモパック系の状態は、その群の行だけで決める。
  - ADR-1023: 状態の価値順（R4／R5 の判定）。
  - ADR-1007: 値は記録した SQL で入れる。
- 区分ごとに取れる単位を決めた ADR は無い。状態の見出し（品目の上の行に書いた状態の語）を扱う ADR も無い。→ 新しく ADR-1041 を起案する。

## 2. 単位の決まり方（今）

- `resolve_product_first` は `backend/app/services/gemini_raw_copy_v102_product_first.py:718-762`。次の順に処理する。
  1. 商品を照合する（:731-742）。
  2. 単位の語を探す。`find_unit_product_first` を呼ぶ（:743-745。本体は :511-538、1 行の中の探し方は `_find_in_line` :485-510）。
  3. `resolve_unit_v2` で語を単位にする（:746。本体は `backend/app/services/tcg_analyzer_svc.py:817-842`）。
  4. 状態を決める。`_resolve_condition`（:747-749。本体は :624-650）。
  5. 状態から単位を決め直す。`_resolve_unit_from_state`（:750-753。本体は :683-715）。
  6. 結果を返す（:754-762）。単位が区分に合うかは、どこでも見ていない。
- `_resolve_unit_from_state`（`backend/app/services/gemini_raw_copy_v102_product_first.py:683-715`）は、次のように単位を決め直す。
  - セット系（:694-699）: 単位の語が無いときだけ Set にする。語があればそのまま。
  - サプライ系（:700-704）: 状態の単位にする。
  - それ以外（:705-715）: 次のどちらかのときは状態の単位に置き換える（:705）。
    - 単位が無い。
    - 箱系で、単位の区分が「条件つき」（個）。
  - 状態が語で決まった（R1〜R3）ときは、状態の単位を優先する（:712-714。ADR-1035 What 2）。
  - 「箱系なのに Set」「プロモパック系なのに Case」のような、区分に合わない語の単位は残る。
- 状態の単位は `masters.condition_unit` から引く（:372）。もとは `_CONDITION_UNIT_SQL`（:152-157）で、`public.line_conditions` を `public.line_units` に結合して作る。
- 区分と状態の群の対応 `_KUBUN_TO_VALUE_GROUP` は :589-594 にあり、シングル・プロモパック・ブックレット・サプライの 4 区分だけを持つ。箱系・セット系・バルク系は入っていない。
- 定数: `PRODUCT_KUBUN_BOX = "箱系"` は :48、`PRODUCT_KUBUN_SET = "セット系"` は :52、`BOX_RECHECK_UNIT_KUBUNS` は :65、`UNIT_KUBUN_REPLACEABLE_FOR_BOX` は :69。
- 値段で単位を決める処理（ADR-1036）は、保存処理の中で後から動く。
  - 呼び出しは `backend/app/services/line_analysis_v102_svc.py:967`（候補判定）と :979（適用）。
  - 対象は `is_candidate`（`backend/app/services/v102_buyback_unit_svc.py:192-203`）。セット系は除く。箱系では、単位の語で決まっていない行（`_unit_not_decided_by_word` :175-181）だけが対象。
  - 決める単位は Box／Case／Pack だけ（:41-42）。

## 3. 単位と区分のマスタ

- 単位の表は `public.line_units`（列 id／code／canonical／kubun／is_active）。別名の表は `public.line_unit_aliases`。
  - 改名の記録: `migrations/20260922_080000_rename_line_analysis_tables.sql`。
  - migration には単位の INSERT が無い。過去の調べ（`docs/handoff/supply-category/recon.md:17`）では、Case／Box／Pack／Piece／Set／本／点／個／Booklet／MasterCarton の 10 行。
  - 本番の今の行は 8 節（2026-10-23 に読み取り）。
- 区分の表は `public.tcg_product_categories`（列 id／code／display_name／kubun_type／is_active）。定義は `migrations/20260919_020000_master_ssot_public_tables.sql:283`。
  - 区分ごとの単位の制約を持つ列・表は無い。allowed_unit など 6 種類の語で migrations と backend/app を grep して 0 件。
- 設定の表は `public.tcg_distribution_settings`（key／value）。値段で単位を決める処理も、ここから帯の数字を読む（`backend/app/services/v102_buyback_unit_svc.py:67` と :206-211）。設定が無いか、正しくない形なら、警告を出して何もしない（:209-210）。

## 4. 要確認の理由「単位不明」

- 既にある。
  - コード定数: `backend/app/services/gemini_raw_copy_v101.py:1271` と `backend/app/services/line_analysis_v102_svc.py:881`。
  - 画面の文字: `frontend/src/locales/ja.json:4060` と `frontend/src/locales/en.json:4060`。
  - 理由の一覧: `backend/app/data/review_reason_labels_ja.json:28`。
- 新しい理由コードは足さない。`backend/tests/test_review_reason_codes_consistency.py` には触れない。

## 5. 状態の決まり方と見出し（今）

- `_resolve_condition` は `backend/app/services/gemini_raw_copy_v102_product_first.py:624-650`。
  - 渡されるのは、品目の選択行を連ねた block だけ（:747-749）。投稿全文 `lines` は `resolve_product_first` まで来ているが、状態の判定には渡していない。
  - 中で `resolve_condition_v2` を呼ぶ。本体は `backend/app/services/tcg_analyzer_svc.py:882-996`。既定の規則は R4（単位既定）が :949-957、R5（パック既定）が :959-975。
- 上の行の見出しを探す前例が `_heading`（`backend/app/services/v102_status_context.py:109-117`）にある。
  - 在庫・予約の見出しを探す。
  - 語と規則は `tcg_status_master` の行から読み、コードには書かない（:3-5）。
- 状態の語は、状態マスタの各行の検索の形で判定している（`_entry_hit`。本体は `backend/app/services/tcg_analyzer_svc.py:845`、product_first では :37 で import。`_other_kubun_hits` :653-666 でも使う）。

## 6. 試算（社外秘フォルダ。この文書には件数だけ書く）

- 単位の表（案T）: `~/CC報告ファイル-keep/shime-auto-check/heading-fix/kubun-unit-sim/`。
  - 見本 100 投稿で、商品 97.8%・状態 93.0% は変わらない。単位は 93.7% → 95.3%。正解のある行で悪化は 0。
  - 直近 30 日（4873 行）で変わるのは 46 行。
    - 置き換え 30 行。うち 2 行（マスターカートン → ケース）は、表に MasterCarton を入れ忘れたための誤り。
    - 単位不明が新たに付く行 16 行。いずれも前から要確認なので、要確認の行数は増えない。
  - 3 商品の区分を箱系に直すと、さらに 4 行が直る。
  - この試算は、値段で単位を決める処理（`backend/app/services/line_analysis_v102_svc.py:967-979`）を通していない。→ 設計 K2 で、保存処理まで通して確かめる。
- 状態の見出し（案D2）: `~/CC報告ファイル-keep/shime-auto-check/heading-fix/sim3/`。
  - 見本 100 投稿で変化 0、本番 11 投稿で変化 0、追加 2 投稿で 31 行が変わり、31 行とも正しかった。
  - 試算では語の一部（傷あり・サーチ不明・開封）と記号を、試算の道具に直接書いた。設計では、これらを状態マスタと設定の表から読む形に変える。→ 再試算 `~/CC報告ファイル-keep/shime-auto-check/heading-fix/sim4-dbwords/`: 状態マスタと単位の別名から読む形でも、変わる行は同じ 31 行。
- 判定の記録: 社外秘フォルダ `~/CC報告ファイル-keep/shime-auto-check/heading-fix/defaulted/` の判定の文書。

## 7. 未確認

- 466089 の現行の行が 2 行ある理由（日時違いの再解析で両方が現行）。この設計の判断には使わない。

## 8. 本番の読み取り（2026-10-23、reader 鍵、生出力は社外秘フォルダ `~/CC報告ファイル-keep/shime-auto-check/heading-fix/formal-recon2/`）

- `line_units` 10 行。Set は区分「複合」、MasterCarton は区分「箱系大」、Case は箱系大、Box は箱系、Pack はパック系、Piece は単品系、本は除外、点は数量専用、個は条件つき、Booklet は冊子系。すべて有効。
- 「複合」は箱系の再判定の区分（`backend/app/services/gemini_raw_copy_v102_product_first.py:65-67`）に入る。別名「セット」「Set」「set」「SET」の 4 行は、どれも Set を指す。
- `tcg_product_categories` 6 行。id 1 は箱系、id 4 はセット系、ほかにシングル系・バルク系・プロモパック系・ブックレット系。すべて有効。
- 3 商品（466089／466090／466091）は、どれも区分 id 4（セット系）、共用（tenant_id 空）、有効。
- 3 商品の v102 の現行の行は 4 行（466089 が 2 行、ほかは 1 行ずつ）。どれも単位 Set・状態 Sealed box・根拠 `R4:単位既定`・要確認なし。
