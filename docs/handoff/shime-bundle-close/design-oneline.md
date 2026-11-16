# design: 1行に品名を並べて〆る投稿（品名A、品名B〆）で、並んだ商品をすべて閉じる（規則14）

関連 recon: `docs/handoff/shime-bundle-close/recon-oneline.md`
親の設計: `docs/handoff/shime-bundle-close/design.md`（縦に並べて〆る形。便1 本番済・便2 本番の表に行を追加済・便3 試験前）
関連 ADR: ADR-1073（規則12h・箱の仲間）、ADR-158（商品単位の差分更新）、ADR-1003（委任 GO）、ADR-135（main にマージ＝本番投入可）。〆の相手を複数の商品に広げる決まりは前例の設計 `docs/handoff/v102-shime-multi-targets/design.md`（規則8〜11）が正。

状態: 設計案作成済み（草案。2026-11-16、Opus。行番号は 2026-11-17 の origin/main 2adefae2e で確かめ直した）。PO の方針の決定 2026-11-16「1」（1行に品名を並べて〆る形を、まとめ〆の直しに加えてから便3の試験をする）。設計審査 1回目 REVISE（2026-11-17、指摘6件。`docs/handoff/shime-bundle-close/review-oneline.md`）→ 直し済み。2回目 REVISE（2026-11-17、新しい指摘5件）→ 直し済み。3回目 REVISE（2026-11-17、新しい指摘3件）→ 直し済み。4回目 REVISE（2026-11-17、新しい指摘2件）→ 直し済み。5回目 APPROVE（2026-11-17、小さい指摘1件・参考1件）→ 小さい指摘は直し済み。設計審査済み。PO の実装承認は未。実装は未着手。

## 1. 目的と成功条件
- 目的: 「品名A、品名B〆」のように1行に品名を区切って並べた〆で、並んだ商品をすべて Sold out にする。今は2品とも閉じないか、片方だけ閉じる（recon §2: 直近30日の3投稿すべて）。
- 利用者に見える変化: 在庫の画面で、1行でまとめて〆られた商品が全部「売り切れ」になる。今それらの投稿で出ている「商品が複数」の要確認が消える。
- 変えないもの: 縦に並べて〆る形（親の設計）、1品だけの〆、状態や等級を並べた〆、価格や数のある行、指示書（Gemini への指示文）。

| 基準 | 検証方法 |
|---|---|
| K0 今の数（基準値） | 測定済み（recon §2）: 直近30日で本物の1行の並び〆は3投稿、3投稿とも並んだ商品のうち少なくとも1つが閉じていない（閉じていない商品は5つ（2+2+1。内訳は作業記録 `oneline/`））。 |
| K1 単体試験 | §3-2 の T1〜T16 と、既存の `backend/tests/test_gemini_raw_copy_v102_soldout_ref.py`・`backend/tests/test_gemini_raw_copy_v101.py`・`backend/tests/test_line_analysis_v102_svc.py` が CI で緑。既存の試験は書き換えない |
| K2 正の3投稿で並んだ商品が全部閉じる | 本番の別のコンテナで `python -m app.tools.v102_replay_diff` を直す前のコード（今の本番）と直した後のコード（ブランチ）で流し、diff を見る。○ = 3投稿とも、行に並んだ商品のうち「同じ仕入元の過去48時間に In Stock の行がある商品」が全部、件の (商品, 状態) か `soldout_targets` に入る。× = 1つでも入らない |
| K3 ほかの投稿が変わらない | K2 と同じ道具で、直近30日の v102 の投稿のうち「Sold out・1行だけ・照合が ambiguous の件」を1件以上持つ投稿を全部（数は流す前に読み取り鍵で数えて記録）流す。○ = 前後で結果が変わった投稿が、正の3投稿だけ。× = それ以外が1投稿でも変わる（目で見て PO に報告し、直すまで先へ進まない） |
| K4 本番で1行の並び〆の閉じ漏れが無い | 反映から14日、毎朝の〆の点検の手順2c で「まとめ〆の閉じ漏れ」のうち1行の形が0件、かつ「消しすぎ」0件 |

## 2. 方針と、採らなかった案
- **受け取り側だけで直す（案C）**。Gemini は1行を1件で返す（今の f_dm も、試験前の f_bc も）。照合は行全体で行い、候補2つの ambiguous になる（recon §3）。そこで、後処理に新しい規則14を足し、行を区切りで分けて区切りごとに照合し、区切りがそれぞれ別の1商品に決まったときだけ、全部の商品を〆の相手にする。
  - 指示書を変えないので、便2で本番に足した行（f_bc）を作り直さずに済み、便3の試験の形（293回）も変わらない。
  - Gemini を呼ばずに、保存済みの件のやり直し（`v102_replay_diff`）で全部の投稿の前後を比べられる（K2・K3）。
- 採らなかった案:
  - 案A 指示書に「1行に並んだ品名は品名ごとに1件」を足す: 2件が同じ1行を持つので、親の設計 §3-1 の条件5（自分の名前の行）で2件目が落ちる。受け取り側の直しも要り、便2の行の作り直しと便3の試験のやり直しが要る。
  - 案B 照合の前に行を区切りで割って件を増やす: 行番号と件の数が変わり、要確認・発送日・F2 など行番号を使う所すべてに影響が出る。
  - 案D 規則10（複数語なしで2商品以上なら決めない）をゆるめる: 区切りの無い「パック、商品名〆」等も通ってしまう（recon §2 の負の例）。

## 3. 変更の内容（コードの PR 1本。`backend/app/services` を触るので GO 記録が要る）

### 3-1. 規則14（1行の並び〆）
1. 判定の関数を `backend/app/services/gemini_raw_copy_v102_soldout_ref.py` に足す（純粋な関数。DB を読まない）。名前の例 `split_list_shime(text, sold_out_words, match) -> tuple[int, ...] | None`。`match` は区切り1つを照合して商品 ID か None を返す関数（呼ぶ側が `match_text_g2` で作る）。
   - 次の全部に当たるときだけ、区切りの順の商品 ID の組を返す。1つでも外れれば None（全部か無しか。片方だけ閉じることはしない）。
     1. 〆の言葉（`ctx.sold_out_words`。「〆」「完売」等）を全部取り除いた残りを、区切りの字 `、` `,` `，` `/` `／` で分けると、空でない区切りが2つ以上5つ以下。「・」「&」「＆」は区切りにしない（商品名の中に出るため。recon §2）。
     2. どの区切りにも数字だけの語が無い（値段と数を並べた行を除く）。
     3. 区切りごとの照合が全部 matched で、商品が全部違う。
2. 呼び出しを `backend/app/services/gemini_raw_copy_v101.py` `_extract_v102`（:1494-、後処理の呼び出しは :1543-1556）に足す。名前の例 `_apply_list_shime(extracted, build, lines, ctx.product_first, soldout_posts, ctx.sold_out_words, fixed_products, box_rule, post_text)`。
   - 置く所: `if ctx.product_first is not None:` の中の先頭、`_apply_context_work` より前。`soldout_posts` が空なら呼ばない（相手を作れないため。今の `if soldout_posts:` と同じ条件）。前に置く理由: `_apply_context_work`（:1277-1300）と `_apply_followup` は ambiguous の件を片方の商品に決めてしまう（11/16 は `_apply_followup` が片方に決めた）。区切りが全部別の商品に決まるのは作品の手がかりより強い根拠なので、先に決める。
   - 対象の件: 次の全部に当たる件だけ。
     1. 完売の件（`status_effect` が除外・`status` が Sold out）で、price と quantity がどちらも無い。
     2. `lines` の行がちょうど1行。
     3. `match_status` が ambiguous で、規則14の商品の組が全部その件の候補（`match_candidates`）にある。
     4. 人が決めた商品が無い（`fixed_products` に無い）。
     5. 件の状態が語で決まっていない。規則14の組の**全部の商品 p について** `build(i, p)` の `condition_basis` を `condition_decided_by_word` で見て、全部 False のときだけ動かす。ただし商品の分類の既定（`R7:単品既定`・`R6:バルク既定`・`R8:プロモパック既定`・`R9:ブックレット既定`・`R10:サプライ既定`。`backend/app/services/gemini_raw_copy_v102_product_first.py:99-103`。flag_note の接頭辞を除いた basis がこの5つのどれかと同じ物）は、行の語ではなくその商品の分類から決まるので、規則14の中だけ「語で決まっていない」と見る（`condition_decided_by_word` は `R\d+:` に当たるので True を返す。`backend/app/services/gemini_raw_copy_v102_soldout_ref.py:43-54`。この関数自体は変えない）。この形の商品は2の1の規則12では相手が出ない（規則12は語で決まった件を外す）ので、2の2で `build(i, 商品)` の状態（例: Single）の在庫から相手を作る。照合前の件では見ない（照合前は商品の分類が空なので、商品が箱系で単位の区分が「条件つき・複合・数量専用」のときだけ箱系として状態を決め直す道（`backend/app/services/gemini_raw_copy_v102_product_first.py:819-824`）を通らず、箱系にだけ効く語（開封など）を見落とすため）。理由: 状態は行全体から決まる（`backend/app/services/tcg_analyzer_svc.py:938-953` `resolve_condition_v2` は状態の語が1つでも当たれば basis を `R{priority}:{語}` にする）ので、「品名A 未開封、品名B 開封〆」のように区切りごとに状態の語が違うと、B の相手の状態を取り違える。状態の語がある1行の並び〆は、今と同じく閉じない（悪くはならない）。正の3投稿のうち2投稿は状態が決まっていない（理由 condition_unknown。作業記録 `oneline/it.txt`）。これは照合前の件の理由で、商品を決めた後の `build(i, p)` の basis は保存の列に無く確かめていない（未確認）。K3 のやり直しで、正の3投稿が規則14で閉じるかを見る。
     6. 同じ投稿のほかの件のうち完売でない件（在庫の件）の `product_id` と `match_candidates` に、組の商品が1つも無い。あわせて `followup_ref` があるときは、今の並びで `decide_followup`（`backend/app/services/gemini_raw_copy_v102_followup.py:116-130`）を流し、在庫の件が組の商品に決まるなら動かない。渡す値は後の段の `_apply_followup` と同じにする（`build_reference_lines(ref_text, masters)`・`units=unit_words(unit_alias_to_info)`・`plural_words=masters.followup_plural_words`。`backend/app/services/gemini_raw_copy_v101.py:1310-1313`）。違う値を渡すと、後の段では決まる在庫の件を見落とす（unmatched の在庫の件は候補を持たないまま、後の段の `_apply_followup`（`backend/app/services/gemini_raw_copy_v101.py:1544-1547`）で組の商品に決まり得るため。候補の制約は ambiguous にしか掛からない（同 `gemini_raw_copy_v102_followup.py:108`））。理由: 先頭の商品の書く行は、先頭の相手の状態で上書きされる（`backend/app/services/line_analysis_v102_svc.py:957-962`）。同じ投稿に同じ (商品, 状態) の在庫の行があると、同じ投稿の行どうしは現行の順位が同じになり（`backend/app/services/tcg_analyzer_svc.py:2104-2117`）、売り切れと在庫ありの行が両方とも現行のまま残る。規則14は後の段より前に動くので、後で決まる件も候補で見る。
   - 完売の相手（`soldout_targets`）は、商品ごとに次の順で求める。
     1. 規則12: `extracted` の i 番目だけを `build(i, 商品)` に差し替えた並びを `decide_soldout_inherit(並び, soldout_posts, fixed_products, box_rule=box_rule, post_text=post_text)` に渡し、`decisions.get(i)` を取る（12d・12e・12g・12h は今のまま）。
     2. 1が無いとき: `_stranded_stock(商品, soldout_posts, same_post)` から〆の状態（`build(i, 商品)` の `_shime_condition`）の物を取り、あれば `_soldout_target(商品, 〆の状態, 投稿, 在庫の行)` で1つ作る（`gemini_raw_copy_v102_soldout_ref.py:380-397`・:409。same_post は1の並びで規則12が作るのと同じ値）。`_stranded_stock` は、その状態の行（在庫・完売）がある最も新しい投稿を見て、そこに在庫の行があるときだけ返すので、新しい投稿ですでに完売になった在庫は相手にしない（12e と同じ）。12d に当たる件（〆と同じ状態の在庫が前にある件）はここに来る。
     3. 1も2も無い商品は、閉じる在庫が無いので相手に入れない。
   - 件の作り直し: 相手のある商品のうち区切りの順で最初の物を「先頭の商品」とし、`build(i, 先頭の商品)` で作り直す。相手のある商品が1つも無ければ、規則14は何もしない（件は今のまま）。相手は先頭の商品の物を先に、残りを区切りの順に並べ、(商品, 状態) の重なりは最初だけ残す（書く行の状態が先頭の相手で上書きされるため。`backend/app/services/line_analysis_v102_svc.py:944-967`。相手は必ず condition_id・ref_message_id・ref_line を持つ（`analysis_soldout_extra_targets` の NOT NULL の列））。
   - 作り直した件に付ける物: `match_status` は新しい定数 `matched_list_shime`、根拠の欄 `product_list_shime` に区切りの字と区切りの順の商品 ID、`soldout_target_basis` は新しい定数 `SOLDOUT_LIST_SHIME`。
   - 規則12を後の段より前に流すことの食い違い（受け入れる）: 1の規則12は `_apply_context_work`・`_apply_followup` の前の並びで動くので、同じ投稿のほかの件の商品がまだ決まっていない。そのため same_post（`gemini_raw_copy_v102_soldout_ref.py:457-459`）に入らない状態があり、最後に流す規則12と結果が違い得る。在庫の件は条件6で除いたので、違い得るのは「同じ投稿に、後の段で同じ商品に決まる別の完売の件がある」ときだけ。そのとき増え得る相手は、同じ商品をどちらにせよ売り切れにする相手なので、在庫ありを売り切れに変える向きの違いは出ない。K3 で変わった投稿を目で見る。
   - 後の段で上書きされないこと（審査で実物を確かめ済み）: `_apply_context_work`・`_apply_followup`（`backend/app/services/gemini_raw_copy_v102_followup.py:125`）・`_apply_soldout_ref`（`gemini_raw_copy_v102_soldout_ref.py:159`）は ambiguous / unmatched の件だけを見る。規則12は `soldout_targets` を持つ件を外す（`_is_inherit_candidate` :374）。
3. 保存で商品が決まった扱いにする: `backend/app/services/line_analysis_v102_svc.py:732-734` の `_RESOLVED_MATCH_STATUSES` に `matched_list_shime` を足す（足さないと :765 で product_id が None・pid_resolved が False で保存され、先頭の商品も閉じない）。pid_basis は :786 で `V102:matched_list_shime` になる。2026-11-17 に origin/main で `SOLDOUT_INHERIT`・`SOLDOUT_REF`（`soldout_target_basis` の値。`line_analysis_v102_svc.py:961` で condition_basis に書かれる）を grep し、使うのは `gemini_raw_copy_v101.py:46`・:1371、`gemini_raw_copy_v102_soldout_ref.py:33`、`line_analysis_v102_svc.py:138`・:961 だけで、値を読んで分ける所が無いことを確かめた（`condition_decided_by_word` も `R\d+:` で始まらない値は語と見ない）。同じ日に `matched_followup`・`matched_soldout_ref` を使う所も grep し、`backend/app` の4ファイル（`gemini_raw_copy_v101.py`・`gemini_raw_copy_v102_followup.py`・`gemini_raw_copy_v102_soldout_ref.py`・`gemini_raw_copy_v102_product_first.py`）と保存の1か所だけで、`frontend/src`・`scripts` には無いことを確かめた。実装の最初に `matched_list_shime`・`SOLDOUT_LIST_SHIME` の比べ先として同じ2つの grep を流し、ほかに出たら止めて Opus に戻す。
4. 触らないもの: 指示書（DB の行・定数）、`parse_v101_response` と親の設計の5条件、規則1〜13、`backend/app/tools/v102_replay_diff.py`、DB の形、migrations/、deploy.yml、scripts/。`line_analysis_v102_svc.py` は3の1行だけ。

### 3-2. 試験（新しく足す。既存の試験は書き換えない）
- T1: 「品名A、品名B〆」（A・B は試験用の名簿で別の商品）→ 規則14の組は (A, B)。
- T2: 区切りが「,」「，」「/」「／」でも T1 と同じ。「・」「&」では None。区切りが6つなら None。
- T3: 片方の区切りが商品に決まらない（「パック、品名B〆」）→ None。
- T4: 2つの区切りが同じ商品（「品名A 未開封、品名A バラ〆」）→ None。
- T5: 試験用に作った「値段,数×個数 〆」の形（数字だけの区切り）→ None。
- T6: `_extract_v102` に T1 の件（ambiguous・候補 A,B・完売・price/quantity なし・1行）と、A・B それぞれに In Stock の行がある過去の投稿を渡す → 件は A で作り直され `match_status` は `matched_list_shime`、`soldout_targets` は A の相手が先頭で B の相手が続く。どの相手も condition_id・ref_message_id・ref_line を持つ。
- T7: T6 で、件に価格がある・2行ある・人が決めた商品がある・`soldout_posts` が空、のどれかなら規則14は動かない（今と同じ結果）。
- T8: T6 で、直前の投稿（`followup_ref`）が A だけを含む場合と、前後の件の作品が A だけを指す場合（`_apply_context_work` が A に決める形）の両方で、件は規則14で決まり B も相手に入る（11/16 の形）。あわせて、件の書く行の (商品, 状態) が A の相手の先頭 (A, X) と同じで、B の相手が `soldout_targets` の2つ目以降にあること。
- T9: T6 の件を `line_analysis_v102_svc` の保存まで通す → A の行は product_id が A・pid_resolved が True・pid_basis が `V102:matched_list_shime`・Sold out、B は `analysis_soldout_extra_targets` に1行。
- T10: A に在庫の行が無く B だけにある → 件は B で作り直され、相手は B だけ。A にも B にも無い → 件は今のまま。
- T11: A の過去の在庫が〆と同じ状態（規則12d で何も返らない形）→ 3-1 の2の2で A の相手が1つ作られる。
- T12: 「品名A 未開封、品名B 開封〆」のように状態の語がある（件の condition_basis が `R2:…` 等）→ 規則14は動かない（今と同じ結果）。
- T13: T11 で、A の〆の状態の行がより新しい投稿で完売になっている → 3-1 の2の2は A の相手を作らない。
- T14: 箱系の商品 A・B で、単位の区分が「条件つき」、行に箱系にだけ効く状態の語がある（照合前の件は `R4:単位既定` 系で、`build(i, A)` の後だけ語で決まる形）→ 規則14は動かない。
- T15: 同じ投稿に、候補に A を含む在庫の件（完売でない件）がある → 規則14は動かない。あわせて、候補を持たない unmatched の在庫の件が `followup_ref` で A に決まる形 → 規則14は動かない。この形は、単位の語を含む直前の投稿の行で作り、`_apply_followup` と同じ units・plural_words を渡していることを確かめる。
- T16: シングル系の商品 A と箱系の商品 B で行に状態の語が無い（A の `build(i, A)` の basis が `R7:単品既定`）→ 規則14は動き、A の相手は Single の在庫の行から2の2で作られる。

## 4. 影響範囲
- 結果が変わるのは、§3-1 の対象の件の6条件と規則14の3条件が全部当たり、相手のある商品が1つ以上ある件だけ。直近30日では正の3投稿だけのはず（K3 で確かめる）。
- 呼び出し元: `_extract_v102` は v102 の解析・作り直し・`prompt_ab`・`v102_replay_diff` から呼ばれる。どれも同じ後処理を通るので、試験の道具でも同じ結果になる。v101 の経路（`extract_v101_items`）は通らないので変わらない。
- 便3の試験（K2・K3、293回）は、規則14が先に本番に入っていても、ほかの投稿の結果は変わらない（K3 で確かめる）ので、試験の形・費用はそのまま。

## 5. リスクと対処
- 区切りで分けた語が偶然別の商品に当たり、並びでない〆で余計な商品を閉じる（消しすぎ）→ 全部か無しか・候補の中に限る・数字だけの語を除く、の3つで狭くする。K3 で直近30日の全部の対象の件を流して確かめ、K4 の「消しすぎ」で見張る。1件でも出たら戻す（PR を revert する）。
- 区切りが型番だけで1商品に決まった場合も、今の照合（`match_text_g2`）の結果をそのまま使う（行全体の照合と同じ決まり）。K3 で型番だけの区切りで変わった投稿があれば目で見て PO に報告する。
- 区切りの照合が型番だけで決まらず、本物の並び〆でも動かない（11/04 の投稿のように型番だけを並べた形）→ 閉じ漏れは今と同じで、悪くはならない。K2 で数え、動かなければ PO に報告する（名簿に検索ワードを足すかは別に決める）。
- 新しい `match_status` の値が、どこかで「知らない値」として要確認や表示の崩れになる → §3-1 の3で実装の最初に全部挙げる。
- 戻し方: 規則14は新しい関数と1か所の呼び出しだけなので、PR を revert すれば元に戻る。保存済みの `analysis_soldout_extra_targets` の行は、次の作り直しで今の規則の結果に置き換わる（DELETE してから INSERT する。`backend/app/services/line_analysis_v102_svc.py` `_DELETE_EXTRA_TARGETS_SQL`）。

## 6. 進め方と GO
1. 設計審査（クラウドの architect opus）→ 実装カード → PO の実装の承認（便1と同じく委任の範囲かを確かめる）→ クラウドの Sonnet が実装。recon §4 の未確認2点は、規則14を `_apply_context_work`・`_apply_followup` より前に置いたので結果を左右しない。K2 で、正の3投稿の件の product と soldout_targets（`v102_replay_diff` の列 :37-39 にある）を見て判定する。
2. CI 緑 → reviewer(opus) を新しく起動して APPROVE → K2・K3 を本番の別のコンテナで流す（Opus が読む。社外秘の作業記録に保存）→ ADR-1003 の3条件で GO（委任に基づく Opus 発行）→ マージ・反映。
3. 反映の後に便3の試験（親の設計 §3-4）。PO の決定「1」のとおり、規則14が先。
4. K4 は毎朝の〆の点検で14日見る。

## 7. 維持の仕組み
- 守り手: Opus（ccopusgo の設計担当）。
- 毎朝の〆の点検（agent-console の定期実行、手順2c）が「まとめ〆の閉じ漏れ」を毎日数える。1行の形も同じ欄で数え、点検の記録に「1行の形」と書き分ける。
- T1〜T16 が、規則14の条件が崩れたら CI で止める。

## 8. 外部・過去事例の参照と我々への応用
- 外部事例: 該当なし。理由: 仕入元ごとの〆の書き方に合わせた後処理の規則で、外の事例に同じ数の根拠は無い。
- 過去事例（このリポジトリ）: 複数の商品を閉じる受け皿（`soldout_targets` と `analysis_soldout_extra_targets`）は規則11（`docs/handoff/v102-shime-multi-targets/design.md`）で作られ本番で動いている。規則14はこの受け皿に相手を並べるだけで、DB の形を変えない。保存済みの件のやり直しで前後を比べる測り方は、規則12h（ADR-1073、`docs/handoff/shime-box-all-states/`）と同じ。

## 9. 未解決
- recon §4 の未確認2点は K2 の結果で見る（規則14を先に置いたので、段ごとの状態は判定に要らない）。
- K3 の対象の投稿の数（流す前に読み取り鍵で数えて記録する）。
