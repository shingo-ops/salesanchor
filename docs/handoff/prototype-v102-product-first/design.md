# Design: prototype-v102-product-first

## 参照
- recon: docs/handoff/prototype-v102-product-first/recon.md
- ADR-155: docs/adr/ADR-155-product-master-ssot-csv-app.md（判定の言葉はマスタから読む）

## KGI
prompt_ab の v102（recompute を含む）で、1件ごとに商品・商品の分類・単位・状態が「商品先行」の流れで出て、記録（product_id・product_category・match_status・match_candidates・unit_basis・condition_basis）から判断の根拠が追える。v101 以前の出力、本番 v6、試運転は変わらない。

## 設計
- 新規 backend/app/services/gemini_raw_copy_v102_product_first.py（v101 を import しない）
  - 材料: load_product_entries、load_product_kubun_type_map（既存）、line_conditions.unit_id → line_units.canonical、line_unit_ignore_phrases の is_active=true。商品・分類・状態の単位が空なら ValueError。言い回しの表は空でもよい。
  - 単位: 価格の行 → 在庫の行 → 名前の行 → その他の行。価格の行は今の位置の条件、見つからなければ区切りの照合（別名の前後が行の端・空白・記号・数字）。区切りの照合で当たった別名は、(a) 照合で当たった商品の検索ワードの語の範囲、(b) 単位にしない言い回しの範囲（正規化・空白0個以上）の中なら採らない。
  - 状態: 商品が箱系で単位区分が 空・不明・条件つき・複合・数量専用 → 箱系で resolve_condition_v2。商品も単位も不明で単位既定の落ち先（R4:単位既定:単位不明）なら状態「不明」＋理由 condition_unknown。補った区分と適用区分が違う状態の行にも当たる場合は、箱系の結果のまま理由 condition_multiple_candidates と code 一覧を残す（適用区分が空の行・単品の行は対象外）。
  - 状態から単位: 単位なし、または単位区分が「条件つき」で商品が箱系のとき、状態の unit_id の単位を当てる。
  - 区分の値（箱系・不明・条件つき等）は定数 1 か所にまとめ、どのマスタの値かをコメントに書く。
- backend/app/services/gemini_raw_copy_v101.py: V101Context に product_first（既定 None）、extract_v101_items に product_first 引数。v102_fixes=True かつ渡されたときだけ新しい流れ。
- backend/app/tools/prompt_ab.py / prompt_ab_recompute.py: _load_v10_masters(session, product_first=True) で v102 のときだけ読む。
- 触らない: tcg_analyzer_svc.py / extraction_shadow_svc.py / tcg_extraction.py、resolve_condition_v2 / resolve_unit_v2 / match_product / find_unit_alias の中身。

## 基準と検証方法
|基準|検証方法|
|---|---|
|単位なし×箱系・シュリンク付き・難あり×個 が期待の状態と単位|backend/tests/test_gemini_raw_copy_v102_product_first.py|
|カートン（名前の行・価格の行）が Case・Case|同上|
|言い回しの表で除外、空なら採る、数字の後ろは今のまま|同上|
|検索ワードの範囲の別名を採らない|同上|
|商品不明×単位不明が状態「不明」・理由 condition_unknown|同上|
|別区分にも当たる場合 condition_multiple_candidates|同上|
|v101（v102_fixes=False）・v10.2 の出力が不変|test_gemini_raw_copy_v101.py ほか既存テスト failed 0|
|v6・試運転を触っていない|git diff --name-only origin/main...HEAD に 3 ファイルが無い|
|試算の結果|PO 検査 40/40、意図しない変化 0（手元の試算）|

## 外部・過去事例の参照と我々への応用
- 過去事例: 社内の R4c（商品分類既定）が同じ発想（商品の分類で単位区分の不足を補う）。本便は同じ比較を v102 の道具の中で、定数にまとめて行う。
- 外部事例: 商品マスタを先に引いてから属性（単位・状態）を決める「エンティティ解決先行」の抽出手法（商品カタログ照合を属性抽出の前段に置く一般的な設計）。応用: 照合結果と除外理由を記録に残し、人が確認できる形にした。

## 維持の仕組み
- 判定の言葉はマスタから読む（ADR-155）。言い回しは画面（便1）から登録する。
- 区分の値の比較は定数 1 か所。テストが期待値を固定し、CI が常時検査する。
- マスタが空なら黙って続けず止める。

## 触るファイル
触るファイル: backend/app/services/gemini_raw_copy_v101.py, backend/app/services/gemini_raw_copy_v102_product_first.py, backend/app/tools/prompt_ab.py, backend/app/tools/prompt_ab_recompute.py, backend/tests/test_gemini_raw_copy_v102_product_first.py, backend/tests/test_prompt_ab.py, docs/handoff/prototype-v102-product-first/design.md, docs/handoff/prototype-v102-product-first/recon.md

## 追記（商品が決まらない件の理由）
- 件の review に、unmatched は product_not_in_master、ambiguous は product_multiple（候補の id）、matched で boundary_dropped があれば product_boundary（消えた候補の id）を足す。試運転（extraction_shadow_svc.py）の要確認と同じ判定。状態・単位・商品の値は変えない。
- 触るファイル: backend/app/services/gemini_raw_copy_v102_product_first.py, backend/tests/test_gemini_raw_copy_v102_product_first.py

## 追記（作品をまたぐ曖昧な商品を前後の商品の作品で決める）
- PO 決定（2026-10-08）：(a) 前後の商品が同じ作品なら決める。(b) 片側だけ・(c) 前後2件ずつの多数決は、落とす候補の作品がその投稿に無いときだけ決める。それ以外は要確認。
- 手がかりは1回目に matched の件だけ（この処理で決めた件は手がかりにしない）。決めた件は match_status=matched_context・product_context（rule・手がかり・落とした候補）を持ち、決めた商品の分類で単位・状態を作り直す。決まらない件は product_multiple に context_reason を足す。product_first なし・v101 の出力は不変。
- 基準と検証方法：

|基準|検証方法|
|---|---|
|試算（手元 sim2.py）と同じ決定|保存済み応答と本番マスタ相当で作り直し、決定・理由が試算と全件一致（r1 51/51・101/101、r2 53/53・100/100、不一致0）|
|対象外の件は変わらない|main と本便のコードで同じ作り直しをして対象外の全欄の差分0件（r1 2,268件・r2 2,266件）|
|既存の出力を壊さない|pytest（新規19件＋既存の v101/v102/prompt_ab 系）|

- 触るファイル: backend/app/services/gemini_raw_copy_v102_context_work.py, backend/app/services/gemini_raw_copy_v101.py, backend/app/services/gemini_raw_copy_v102_product_first.py, backend/tests/test_gemini_raw_copy_v102_context_work.py, docs/handoff/prototype-v102-product-first/design.md, docs/handoff/prototype-v102-product-first/recon.md

## 追記（品番らしい値は原文の書き方のまま前後が区切られているときだけ当たり）
- 規則：match_product に strict_codes（既定 False）を足し、試作版 resolve_product_first だけ True で呼ぶ。True のとき、product_code・mark・検索ワードの各語のうち「fold 後の文字が英数字・区切り文字・記号(P*/S*)だけで、英字を含み、英数字が3文字以上」の値は、値の英数字を順に並べて文字の間に区切り文字（空白・ハイフン類・中黒・下線・ピリオド・アポストロフィ類。改行は除く）を0個以上許す正規表現に当たり、かつ前後が [a-z0-9] でないときだけ当たり。値の中の記号はパターンに入れない。かな・漢字を含む値、数字だけの値、2文字以下の値は今のまま。False のときは1文字も変えない。v6・試運転・tcg_shadow_review は変えない。
- 基準と検証方法：

|基準|検証方法|
|---|---|
|試算と同じ結果|保存済み応答＋本番マスタ相当で、after3 の全件（r1 3,350・r2 3,352）の match_product の候補の変化が strict-sim/v2 の status_changes.tsv と全件一致（Re:ゼロ Vol.4 の候補外しは起きないのが正しい）。結果 6,702/6,702 一致|
|本番・試運転の照合は不変|strict なしの match_product の出力が main と全件同じ（after3 の 6,702件で cmp 一致）＋テスト|
|前後の商品で決める処理と合わせて矛盾なし|response_text から作り直し、matched_context の件数と一覧を main と比較（件数のみ PR に記載）|
|境界で外れた候補は要確認に回る（意図した動き）|作り直しで product_boundary の要確認の増減を main と比較（r1 489→723、r2 492→726。一覧は手元の compare_boundary.txt）|

- strict で外れた候補は boundary_dropped に入り、商品の境目の要確認（product_boundary）が付く。「境界のせいで外れたもの」を要確認に回す安全側の動きで、意図どおり。

- 触るファイル: backend/app/services/extraction_judgement_svc.py, backend/app/services/gemini_raw_copy_v102_product_first.py, backend/tests/test_extraction_judgement_svc.py, docs/handoff/prototype-v102-product-first/design.md, docs/handoff/prototype-v102-product-first/recon.md

## 追記（候補が複数残った件に「より詳しく当たった候補」を提案する）
- PO 決定（2026-10-08）：「要確認にも残すのではなく要確認に回し人が整備して次回から解析できるようにする、要確認に回したものを配信しない」。選べた候補も商品は決めない（match_status は ambiguous・product_id は None・単位・状態は今のまま）。要確認 product_multiple に suggested_product_id・suggest_rule（S1 か S4）・suggest_dropped を添える。新しい kind・matched_score という状態は作らない。
- 規則（試算 score-sim/v2 の S1・S4 と同じ）：対象は照合が ambiguous の件（前後の商品で決める処理のあと、なお ambiguous の件）。候補ごとに M（品番か記号が当たった＝1）・K（当たった検索ワードがある＝1）。S1＝M+K の最高点がちょうど1つならその候補。S1 で決まらなければ S4：候補ごとの「当たった語の集合」（当たった検索ワードと当たった品番・記号を正規化したもの）で、候補 A の全語が候補 B のどれかの語の部分文字列なら B は A を包む。ほかの全候補を包み自分は誰にも包まれない候補がちょうど1つならその候補。それ以外は提案しない。
- 根拠は新しい欄 product_score（rule・scores＝候補 id ごとの M・K・words）。提案が付いた件だけに付く。
- MatchResult に既定値つきで code_hits（品番・記号が当たった候補 id）と code_hit_values（当たった値。S4 の語の集合に要る）を足す。既存の欄・判定は変えない（v6・試運転の出力は不変）。
- 基準と検証方法：

|基準|検証方法|
|---|---|
|試算と同じ提案|保存済み応答＋本番マスタ相当（build8.py の変更込み）で作り直し、suggested_product_id の (投稿, 価格行, 商品) が score-sim/v2 の S1+S4（matched_context を除く）と全件一致（r1 121/121・r2 120/120）|
|対象外は不変|main と本便で、product_score と suggested_* 以外の全欄の差分0（r1 3,697件・r2 3,697件）|
|v6・試運転の照合は不変|strict なし・ありの match_product の既存欄が main と全件同じ（cmp 一致）＋テスト|

- 外部事例：曖昧な候補から根拠の強い候補を提案し、確定は人に回す運用（人が確認する前提の自動提案・human-in-the-loop）。今回は PO 決定の S1・S4 に限定し、決まらない件は提案しない。
- 守り手：backend/tests/test_gemini_raw_copy_v102_score_select.py（S1・S4・決めない・前後の商品で決めた件は不変・product_first なしの出力不変）。
- 触るファイル: backend/app/services/extraction_judgement_svc.py, backend/app/services/gemini_raw_copy_v102_score_select.py, backend/app/services/gemini_raw_copy_v102_product_first.py, backend/app/services/gemini_raw_copy_v101.py, backend/tests/test_gemini_raw_copy_v102_score_select.py, docs/handoff/prototype-v102-product-first/design.md, docs/handoff/prototype-v102-product-first/recon.md

## 追記（商品の境目を要確認の理由から外す・2026-10-08）
PO 決定（2026-10-08「3つともy」）：商品の境目（product_boundary）で件を要確認に回さず、配信の対象にする。落ちた候補の一覧は透明性のため残す。

- _product_reviews から boundary_dropped の分岐と定数 REVIEW_PRODUCT_BOUNDARY を外す（ほかの参照なし）。
- resolve_product_first の戻り dict に match_boundary_dropped（落ちた候補の id の一覧・要確認ではない控え）を足す。
- v101 の extra に match_boundary_dropped を足し、出力の行に同名の欄で残す。落とした件（_rejected_row）は空の一覧。
- 試運転 extraction_shadow_svc.py・MatchResult・v6・単位・状態・context_work・score_select の判定・DB・マスタ・フロントは触らない。

|基準|検証方法|
|---|---|
|要確認から消える|本番 recompute（after9 入力 r1/r2）で review の kind=product_boundary が 0 件|
|ほかは不変|product_id・match_status・unit・condition・ほかの review の kind の件数がデプロイ前と同じ|
|控えが残る|match_boundary_dropped が空でない行の数が、デプロイ前の product_boundary の件数と同じ|

- 外部事例：検知した「疑わしい」印のうち、人手で全件検証して誤検知 0 だったルールを、人の確認キューから外して記録だけ残す運用（アラート疲れを避けるため根拠が固まった警告を降格し、監査用ログとして保持する）。
- 守り手：backend/tests/test_gemini_raw_copy_v102_product_first.py（test_matched_with_boundary_dropped_keeps_record_without_product_boundary_review・test_matched_without_boundary_dropped_has_no_product_review）。
- 触るファイル: backend/app/services/gemini_raw_copy_v102_product_first.py, backend/app/services/gemini_raw_copy_v101.py, backend/tests/test_gemini_raw_copy_v102_product_first.py, docs/handoff/prototype-v102-product-first/design.md, docs/handoff/prototype-v102-product-first/recon.md

## 追記（除外ワードにも前後が区切られているときだけ当たりを当てる）
- PO 決定（2026-10-08「3つともy」）。規則：match_product の strict_codes=True（試作版 v102 だけ）のとき、除外ワードの各値に _strict_code_hits を当て、None でなければその結果で判定。None（2文字以下・数字だけ・日本語を含む等）は今どおり正規化した部分一致。strict_codes=False（v6・試運転）は1文字も変えない。_is_candidate の呼び出しは変えない。
- 基準と検証方法：

|基準|検証方法|
|---|---|
|試算と同じ|本番 recompute（after9 入力 r1/r2）で、デプロイ前後の v102 の判定差分が 0 件（product_id・match_status・candidates）|
|v6・試運転不変|strict なしの match_product の既存テストと出力が main と同じ|
|3rd が当たる|テスト（strict・除外 SAR・原文 3rd ANNIVERSARY SET が matched）が通る|

- 外部事例：除外ワードは語の境界で見る（単語単位の否定フィルタ。全文検索の stop word・NG ワード判定は部分文字列でなく token 単位が一般的）。品番と同じ規則に揃える。
- 守り手：backend/tests/test_extraction_judgement_svc.py の TestExcludeKeywordsStrictCodes（strict・SAR・anniversary、strict・SAR 区切りあり、2文字は部分一致、PSA10、strict なしは不変）。
- 触るファイル: backend/app/services/extraction_judgement_svc.py, backend/tests/test_extraction_judgement_svc.py, docs/handoff/prototype-v102-product-first/design.md, docs/handoff/prototype-v102-product-first/recon.md

## 追記（型番で決めない中分類を中分類マスタの印で持つ）
PO 決定（2026-10-09）：ポケモンは型番だけで投稿されないため、試作版 v102 の照合で型番を使わない。方式は「中分類マスタに印の項目を1つ足し、ポケモンにだけ印を付ける」。

- migrations/20261009_100000_type_master_match_by_code.sql：public.type_master に match_by_code BOOLEAN NOT NULL DEFAULT TRUE を足す（構造のみ。値の UPDATE は書かない）。印の値（ポケモン＝type_master.id 1 を FALSE）はデプロイ後に運用の手順（DRY-RUN→COMMIT）で付ける。
- load_product_first_masters が `SELECT id FROM public.type_master WHERE match_by_code = FALSE` で印の付いた中分類 id を読み、新しい純粋関数 apply_name_only_works で商品リストを変換する。
- apply_name_only_works：有効な全商品の product_code・mark を normalize_for_match した値の集合を作り、work_id が印の中分類の商品だけ、product_code=None・mark=None・検索ワードのうち「normalize_for_match した語全体がその集合に入る語」を除く。除外ワード・ほかの商品は変えない。印の中分類が無ければ同じ内容を返す。
- 触らない：extraction_judgement_svc.py（match_product ほか）・extraction_shadow_svc.py の load_product_entries・tcg_analyzer_svc.py（v6）・tcg_shadow_review_svc.py・フロント（印の編集画面は今回作らない）・マスタのデータ。
- 基準と検証方法：

|基準|検証方法|
|---|---|
|列がある|デプロイ後に information_schema.columns で public.type_master.match_by_code が存在（BOOLEAN・NOT NULL・既定 TRUE）|
|印が TRUE（全件の既定）なら不変|印を付ける前に本番 recompute（after14 入力）の差分が 0 件。テスト：印なしで変換前後の entries が同じ|
|印が FALSE の商品は型番を使わない|テスト：product_code・mark が None、型番と同じ検索ワードだけ消え、名前の検索ワードは残る。別作品の品番と同じ語も消える。変換後の match_product(strict_codes=True) で型番だけのテキストは決まらず、名前を含むテキストは決まる|
|v6・試運転・レビュー画面は不変|共有関数を触っていない（git diff）＋既存テスト全通過|
|マスタのデータは不変|migration に UPDATE・INSERT・DELETE が無い（目視と grep）|

- 外部事例：検索の同義語・識別子の扱いをカテゴリごとの設定で切り替える運用（EC サイト検索で型番検索をカテゴリ属性のフラグで有効・無効にする構成。対象の付け替えは設定の変更だけで済み、コードは変えない）。
- 維持の仕組み：対象の追加・解除は type_master.match_by_code の値の変更だけ（コード変更なし）。変換は純粋関数なのでテストで固定。守り手：backend/tests/test_gemini_raw_copy_v102_name_only.py。
- 触るファイル: migrations/20261009_100000_type_master_match_by_code.sql, backend/app/services/gemini_raw_copy_v102_product_first.py, backend/tests/test_gemini_raw_copy_v102_name_only.py, backend/tests/test_gemini_raw_copy_v102_product_first.py, docs/handoff/prototype-v102-product-first/design.md, docs/handoff/prototype-v102-product-first/recon.md
