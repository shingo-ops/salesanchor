# design: 状態を書かない箱の〆は、箱の仲間の状態をまとめて完売にする（規則12h）

状態: 設計審査済み（Opus の自己審査・§10。独立した審査ではない）。PO 承認済み（2026-11-10「1」＝この設計で進める。便1 の実装へ進む）。便2〜4 はそれぞれの PO の `!`・「切り替える」が要る。根拠は docs/handoff/shime-box-all-states/recon.md。
PO の発言: 2026-11-10「2,1」（先に〆の規則の直し方を設計し、次に語を本番へ足す）。2026-11-11「1」（便3 の結果を受け、値段か数を書いた〆ではほかの状態を消さない直しを足し、やり直しで確かめてから切り替えを聞く。§2 の条件 7・§9-2 のカード）。

## 1. 目的と成功条件

- 目的: 仕入元が「商品名＋〆」とだけ書いたとき、シュリンクなし等の箱の在庫が残ったままにならないようにする。「商品名＋有〆」のように状態を書いた〆と、在庫が残っていると書いた投稿では、ほかの状態の在庫は消さない。
- 利用者に見える変化: 状態を書かない箱の〆の後、在庫表に同じ商品の別の箱の状態が残らない（1 か月に約 14 件。recon §3 からの推計）。
- 対象: v102 の規則12（商品名を書いた〆が前の在庫を引き継ぐ）の、今は何もしない形（12d）だけ。
- 対象外: カートン・パック・シングル等、箱以外の群。〆の行に単位語がある件（規則12f のまま）。〆で商品が決まらない件（規則1〜11）。過去の〆のやり直し（入れた後の新しい投稿だけ）。指示文・Gemini・DB の形。

| 基準 | 検証方法 |
|---|---|
| K1 規則の単体: 12h が働く形・働かない形 6 つが期待どおり。設定が無いとき今と同じ | `backend/tests/` の pytest（DB 不要）。§9 カードの 6 つの試験が合格。既存の試験は、カード 3 で書き換える 6 か所を含めて全部合格 |
| K2 入れても変わらない: 設定が無いまま、同じ 134 投稿を反映の直前（今の本番）と直後（新しい本番）でやり直し、全列・全件で同じ（同じコードの 2 回が完全一致することは 2026-11-09 に確認済み） | `backend/app/tools/v102_replay_diff.py` の diff の結果で、変わった件 0 |
| K3 狙いの 21 件: 5 つの語を本番に入れた後（便2）、設定を記憶の中で差し込んだやり直し（便3）で、直る 13・壊す 0・直らない 1。残る 7 件は「特定の状態だけ」のまま | 21 件の投稿の soldout_targets を、記録フォルダの正解（Opus の原文判定）と突き合わせた表。数が違えば止めて PO へ |
| K4 ほかを壊さない: 直近 30 日の〆を含む投稿全部のやり直しで、相手が変わった件を全部並べ、Opus が原文で 1 件ずつ判定して誤り 0 | changed_any.tsv の行数＝判定表の行数。「誤り」の列が 0 |
| K5 本番の効果: 設定を入れた後 14 日の朝の〆点検で、「状態を書かない箱の〆の後に別の箱の状態が残る」の × が、入れる前 14 日より減る。「消しすぎ」の × は 0 | 朝の〆点検の記録（verdict.md）の数を、入れる前と後の 14 日で表にする |
| K6 戻せる: 設定の行を消すと今と同じ動き | K1 の「設定が無い」試験と、K2 と同じやり直し |
| K7 値段・数の除外（便3.5）: 便3 と同じ 204 投稿を、直した後のコードで設定を差し込んでやり直すと、便3 の S と比べて相手が変わるのは「値段×数の行の〆」1 件だけ（相手が無くなる）。ほかの相手は全部同じ | 便3 の S と新しい S の diff（soldout_targets の差の件数 1・その 1 件の投稿が記録フォルダの誤りの 1 件と同じ）。違えば止めて PO へ |

## 2. やり方（変更前後）

- 変更前（recon §2-1）: 候補の〆で、〆と同じ状態の在庫が前の投稿にあると 12d で何もしない（`backend/app/services/gemini_raw_copy_v102_soldout_ref.py:427-428`。便1 の後の main では `:462-467`）。
- 変更後: 12d で何もしない所の手前に 12h を足す。次の全部を満たすときだけ、〆の状態と、取り残された箱の仲間の状態を全部、完売の相手にする。
  1. 設定 `v102_shime_box_all_states` が読めている（無い・形が違うときは今と同じ）。
  2. 〆の件の状態が箱の仲間（状態マスタ `value_group='box'`）。
  3. 〆の状態が語で決まっていない（今の候補の条件のまま。語で決まった〆は候補に来ない）。
  4. 〆の状態の在庫が前の投稿にある（12d に来た形）。
  5. 取り残し（`_stranded_stock`）のうち〆の状態以外が 1 つ以上あり、その全部が箱の仲間。カートン・パック等が 1 つでも混ざれば今と同じ（何もしない）。
  6. 今の投稿の原文に、設定の `keep_words` のどれも含まれない（NFKC にして部分一致）。
  7. 〆の件に値段も数も無い（`price_normalized` と `quantity_normalized` がどちらも None）。どちらかがあれば今と同じ（12d で何もしない）。値段や数を書いた〆は「その行の品が売り切れた」意味で、商品の全部の状態の売り切れではないため（便3 の判定。§3-2）。
- 相手の並び: 先頭に〆の状態（最も新しい在庫の投稿の行）、続けて残りを `value_rank` の小さい順。先頭が〆の状態なので、〆の件の状態は変わらない（`backend/app/services/line_analysis_v102_svc.py:941-964` が先頭で上書きするため）。2 つ目以降は既にある表 `analysis_soldout_extra_targets` に入り、在庫表の今の行から外れる（recon §2-2）。
- 印は今の 12 と同じ `SOLDOUT_INHERIT`。
- 語と箱の仲間をコードに書かない: 語は設定、箱の仲間は状態マスタの `value_group` から読む（ADR-1041 の前例）。

## 3. 入れる順（一度に 1 つ・測ってから次）

| 便 | 中身 | 誰が | 測る |
|---|---|---|---|
| 1 | コード（設定が無ければ働かない）と試験。やり直しの道具に設定を差し込む口を足す | クラウドの Sonnet → PR → 審査役 → マージ → 本番反映 | K1・K2 |
| 2 | 5 つの語を本番の状態の表（CN0003）に足す（ADR-1007 の 5 つの SQL） | PO が `!` で実行 | 足す前後の件数・更新時刻。語だけでは〆の相手・在庫・状態の値が変わらないことは 2026-11-09 の 134 投稿で確認済み |
| 3 | 本番の写しでのやり直し（設定を記憶の中で差し込む） | PO が `!` で台本を実行 | K3・K4 |
| 3.5 | 条件 7（値段・数の除外）のコードと試験 → 便3 と同じやり直し | クラウドの Sonnet → PR → 審査役 → マージ → 本番反映。やり直しは PO が `!` | K1・K7 |
| 4 | 設定の行を入れる（切り替え） | PO の「切り替える」の後、PO が `!` | K5（14 日） |

- 便2（語）を便3・便4 の前に必ず入れる。語が無いまま設定を入れると「商品名＋有〆」型を消しすぎる（recon §3 の案 1b の壊す 3）。やり直しは main の `backend/app/tools/v102_replay_diff.py` で行い、この道具には語を記憶の中で足す口が無い。だから語は本番に先に入れる（語の試しの台本 `scripts/accuracy/condition_words/` は、2026-11-09 の試しの記録としてこの設計の PR で main に入れるが、便3 では使わない）。

## 3-2. 便3 の結果（2026-11-11 03:49〜04:54 JST・本番の写し・読み取りだけ）

社外秘の原文・件ごとの記録は Mac の記録フォルダだけに置く。ここには数だけを書く。

- 実行: 3 回とも終了コード 0・失敗 0。接続は READ ONLY。箱の仲間は 5 つ（id・value_rank）で、記録 SQL `docs/handoff/condition-value-rank/data/value_rank_commit.sql` と数と順が同じ（§6 の未確認は解けた）。
- 設定なしの 2 回の差は 0（途中で本番が動いた分は無い）。設定ありと設定なしの差は 12 件（K3 の狙いの件で変わった 6 と、それ以外で変わった 6。後の 6 を K4 で判定した）で、変わった列は `soldout_targets` と `soldout_target_basis` だけ。相手に Opened box と CN20261008072213 は 0 件。
- K3（投稿ごと）: 直る 6・壊す 0・直らない 8。期待の 13/0/1 と違う。直らない 8 件の内訳は、前の〆が先に同じ在庫を消している 4、もともと消す在庫が残っていない 2、カートンが残る（設計どおり）1、測れない 1。在庫で見ると、狙いの 14 件のうち消える 10・もともと無い 2・設計どおり残る 1・測れない 1。2026-10 の数え方は「前の〆が先に消す」つながりを数えていなかった。
- K4: 相手が増えた件を原文で判定し、正しい 5・誤り 1。誤りの 1 件は「値段×数」の行の〆で、意味はその行の品だけの売り切れ（K3 の「特定の状態だけ」7 件の 1 件と同じ型）。17 時間前の別の〆が同じ在庫を消しているので、在庫表への害は 0。
- 〆の件 27 件のうち、値段か数があるのはこの型の 2 件だけ（ほかは両方 None）。→ 条件 7 を足せば誤りは消え、直る件は減らない見込み。K7 で確かめる。
- 便4 で入れる設定の値: `{"keep_words": ["まだあります"]}`（便3 で差し込んだ値と同じ）。

## 4. 影響範囲

- 変わるコード: `backend/app/services/gemini_raw_copy_v102_soldout_ref.py`（12h）、`backend/app/services/gemini_raw_copy_v101.py:1310-1325`（相手を複数載せる・規則と今の投稿の行を渡す）、`backend/app/services/gemini_raw_copy_v102_product_first.py`（設定と箱の仲間を読む。`ProductFirstMasters` に 1 欄）、`backend/app/tools/v102_replay_diff.py`（設定の差し込み）。
- 呼び出し元: 本体のコードでは `decide_soldout_inherit` は `backend/app/services/gemini_raw_copy_v101.py:1314` だけ（`git grep` で確認）。試験では `backend/tests/test_gemini_raw_copy_v102_soldout_ref.py:562` が直接呼ぶ。新しい引数は既定値つきだが、戻り値の型が変わるので、試験の 6 か所（`:568`・`:649`・`:655`・`:720`・`:734`・`:741`）の期待値を組の形に書き換える（カード 3）。
- DB: 形は変えない。設定 1 行（便4）と状態の語（便2）だけ。
- 在庫表: 相手が増えた分だけ古い在庫の行が今の行でなくなる（既にある仕組み）。

## 5. 代替案

| 案 | 採否と理由 |
|---|---|
| 1 状態を書かない〆は全部の状態を消す | 採らない。壊す 7（recon §3） |
| 1b 箱の仲間だけ（語・在庫が残っていると書く語の除外なし） | 採らない。壊す 3 |
| **1d 1b＋語で決まった〆は除く＋在庫が残っていると書いた投稿は除く（この設計）** | 採る。直る 13・壊す 0・直らない 1 |
| 次の投稿を待って決める | 採らない。数時間後に同じ品を全状態で載せ直す仕入元が多く、売り切れか補充かを区別できない（recon の元の記録） |

## 6. リスクと対処

- 正解は Opus の原文判定だけで、件数 21 は小さい → K4 で 30 日の全件を見る。K5 で「消しすぎ」の × が出たら設定の行を消して戻す（1 行の DELETE。コードは戻さなくてよい）。
- Opened box・CN20261008072213 は箱の仲間だが、21 件に現れていない（未測定）→ K4 の一覧で、これらが相手に入った件を別に数えて PO に見せる。
- 本番の `value_group` の今の値は読み取り専用の鍵で読めない（recon §2-3）→ 便3 のやり直しで、道具が箱の仲間の一覧（id・順位）を標準出力に出し、それで確かめる。記録 SQL と違えば止めて PO へ。
- 設定を消しても、それまでに書いた 2 つ目以降の相手（`analysis_soldout_extra_targets` の行）は残る。消えた在庫が戻るかは未確認（試験していない） → 便4 の前に PO へ戻す。
- 値段や数を書いた〆（便3 で誤り 1）→ 条件 7 で除く（便3.5）。
- 設定にまだ無い、在庫が残っていると書く言い方 → 朝の点検で消しすぎが出たら、設定の `keep_words` に足す（コードは変えない）。

## 7. 維持の仕組み

- 守り手: `backend/tests/test_gemini_raw_copy_v102_soldout_ref.py`（K1 の試験。CI の pytest で PR ごとに走る）
- 規則は試験（K1）で守る。設定の形の検査は ADR-1041 の 2 つと同じ書き方。
- 朝の〆点検（11/15 まで続けている）を、設定を入れた後 14 日延ばして K5 を数える。
- 規則の決定は ADR-1073 に残す（Proposed）。

## 8. 外部・過去事例の参照と我々への応用

- 使わない。理由: 仕入元の書き方に合わせた自社の規則で、判断の根拠は自社の保存済みの投稿のやり直しだけで足りる。

## 9. 実装カード（便1。クラウドの Sonnet 向け・PO の実装承認の後に渡す）

0. 場所: origin/main から `release/shime-box-all-states-bin1`（`bash scripts/new-worktree.sh release/shime-box-all-states-bin1`）。
1. 読む（変えない）: `backend/app/services/gemini_raw_copy_v102_soldout_ref.py` 全部、`backend/app/services/gemini_raw_copy_v101.py:1285-1345` と `:1495-1505`、`backend/app/services/gemini_raw_copy_v102_product_first.py:126-175` と `:379-500`、`backend/app/services/line_analysis_v102_svc.py:941-975`、`backend/app/tools/v102_replay_diff.py` 全部、`backend/tests/test_gemini_raw_copy_v102_soldout_ref.py:540-745`、`backend/tests/test_v102_replay_diff.py` 全部。
2. `backend/app/services/gemini_raw_copy_v102_product_first.py`:
   - 定数 `_SHIME_BOX_ALL_STATES_KEY = "v102_shime_box_all_states"`。
   - dataclass `ShimeBoxAllStatesRule(keep_words: tuple[str, ...], box_ranks: Mapping[int, int])`（box_ranks は状態の id → value_rank）。
   - `ProductFirstMasters` の最後に `shime_box_all_states: ShimeBoxAllStatesRule | None = None`。
   - 純粋関数 `parse_shime_box_all_states(raw: str | None, box_ranks) -> ShimeBoxAllStatesRule | None`: 値が `{"keep_words": [空でない文字列, ...]}`（key はこれだけ・配列は 1 つ以上）なら規則、key が無いときは debug、形が違うときは warning を出して None。box_ranks が空なら warning で None。
   - `_load_shime_box_all_states(session)`: 設定を `_KUBUN_ALLOWED_UNITS_SQL` で読み、箱の仲間を `SELECT id, value_rank FROM public.conditions WHERE is_active = TRUE AND value_group = 'box'`（`load_condition_entries` が読む表と同じ。`backend/app/services/tcg_analyzer_svc.py:695-712`）の 2 つを読んで parse に渡す。SoldoutTarget・StockItem の condition_id が `public.conditions.id` と同じ番号であることを、1 で読むときに確かめる（`backend/app/services/line_analysis_v102_svc.py:879` が相手の condition_id の名前を `public.conditions` から引いている）。違えば止まる。`load_product_first_masters`（`:379`）で `shime_box_all_states=` に入れる。
3. `backend/app/services/gemini_raw_copy_v102_soldout_ref.py` の `decide_soldout_inherit` にキーワード引数 `box_rule: ShimeBoxAllStatesRule | None = None, post_text: str = ""` を足し、戻り値を `dict[int, tuple[SoldoutTarget, ...]]` に変える（12g・12e は 1 つの組）。既存の試験 `backend/tests/test_gemini_raw_copy_v102_soldout_ref.py` で `== {0: sr.SoldoutTarget(...)}` と書いた 6 か所（`:568`・`:649`・`:655`・`:720`・`:734`・`:741`）は、期待値を `{0: (sr.SoldoutTarget(...),)}` に書き換える。中の値は変えない。`list(...) == [0]`・`== {}` の形の試験は書き換えない。`:427-428` の `continue  # 12d` を次に置き換える:
   - 判定の順: まず `box_rule` が None なら `continue`。次に取り残し（`stranded`）に〆の状態があるかを見て、無ければ `continue`（在庫の行が最新でない）。そのうえで、〆の状態の id（取り残しの StockItem の condition_id）が box_ranks に無い、`post_text` に keep_words のどれかが含まれる（NFKC・部分一致）、取り残しの〆の状態以外が 0、取り残しの〆の状態以外に box_ranks に無い状態がある — のどれかなら `continue`（今と同じ）。
   - それ以外は、取り残しの〆の状態を先頭、残りを value_rank の小さい順にした SoldoutTarget の組を返す。〆の状態の id は取り残しの StockItem の condition_id を使う（canonical が〆の件の状態と同じもの）。
4. `backend/app/services/gemini_raw_copy_v101.py:1310-1325` の `_apply_soldout_inherit` に `box_rule` と `post_text`（今の投稿の原文。`lines` を `"\n"` でつないだもの）を渡し、組の全部を `soldout_targets` に並べる。`:1502` の呼び出しで `ctx.product_first.shime_box_all_states` と `"\n".join(lines)` を渡す。
5. 試験（`backend/tests/` の soldout_ref の試験ファイルに足す。架空のデータ・実在の会社名・人名・商品名を書かない）: (a) 働く: Sealed box の〆、前に Sealed box と No shrink box の在庫 → 相手 2 つ、先頭が Sealed box (b) 語で決まった〆 → 何もしない (c) keep_words を含む → 何もしない (d) 取り残しにカートンが混ざる → 何もしない (e) box_rule=None → 今と同じ（既存の 12d の試験と同じ結果） (f) parse の形の検査（正しい・key 違い・空配列・JSON でない）。
6. `backend/app/tools/v102_replay_diff.py` に `--shime-setting FILE`（任意。`--heading-setting`（`:59-60`（読み込み）・`:105`（`replay` の引数）・`:111-112`（差し替え）・`:191`（`add_argument`）・`:208`（渡す所））と同じ作り）: 指定時、masters の product_first の `shime_box_all_states` を、ファイルの JSON と本番の箱の仲間で作った規則に差し替える。標準出力に箱の仲間の一覧（id・value_rank）を出す。既存の試験ファイル `backend/tests/test_v102_replay_diff.py` に、`--shime-setting` の読み込みの試験を 1 つ足す。
7. 確かめ: `ruff check` の対象ファイル、`cd backend && python -m pytest -q tests/test_gemini_raw_copy_v102_soldout_ref.py tests/test_gemini_raw_copy_v102_product_first.py tests/test_v102_replay_diff.py`。
8. 合格基準（出力を貼り、判定は Opus）: ruff 合格／pytest の failed・error 0（カード 3 で書き換えた 6 か所を含む）／`git diff --stat origin/main..HEAD` に出るのは上のファイルだけ／migrations・workflows に差が無い。
9. 止まる条件: 1 で読んだ関数・引数・行がカードと違うとき、推測で直さず `NEEDS_DECISION:` で止まる。

## 9-2. 実装カード（便3.5 条件 7。クラウドの Sonnet 向け）

0. 場所: origin/main から `release/shime-box-price-guard-code`（`bash scripts/new-worktree.sh release/shime-box-price-guard-code --claude`）。
1. 読む（変えない）: `backend/app/services/gemini_raw_copy_v102_soldout_ref.py:415-480`（`_box_all_states_targets`・`decide_soldout_inherit`）、`backend/app/services/gemini_raw_copy_v101.py:1311-1333` と `:980-990`（件の `price_normalized`・`quantity_normalized`）、`backend/tests/test_gemini_raw_copy_v102_soldout_ref.py:612-625`（`_shime`）と `:855-945`（12h の試験）。
2. `backend/app/services/gemini_raw_copy_v102_soldout_ref.py` の `decide_soldout_inherit` の 12h の呼び出し（今の `box_targets = _box_all_states_targets(...)  # 12h` の行）を、〆の件 `item` の `price_normalized` と `quantity_normalized` がどちらも None のときだけ呼ぶ形に変える。判定は `item.get("price_normalized") is None and item.get("quantity_normalized") is None`（キーが無い件は None として読む。0 は値ありとして扱う）。どちらかが None でなければ 12h を呼ばず、そのまま `continue  # 12d`（今と同じ）。`_box_all_states_targets` の引数と中身・12g・12e・候補の条件（`_is_inherit_candidate`）は変えない。docstring の 12h の説明に「〆の件に値段も数も無いとき」を足す。
3. 試験（同じ試験ファイルの 12h の試験の並びに足す。架空のデータだけ）: (g) `_shime(price_normalized=26500)` → `{}`、`_shime(quantity_normalized=3)` → `{}`、`_shime(price_normalized=None, quantity_normalized=None)` → 12h が働く（既存の (a) と同じ相手）。(h) box_rule=None で値段つきの〆 → 今と同じ（`{}`）。(i) 既存の `test_extract_12h_puts_every_box_state_on_the_soldout_row`（`:924-929`）は、`_extract`（`:73-86`）が〆の行に「 3@1,500円」を足すので、条件 7 の後は 12h が働かず落ちる。次の 2 つに書き換える: ①試験の名前を `test_extract_12h_does_nothing_when_the_shime_line_has_a_price` に変え、同じ入力で `_targets(row) == []` を確かめる。②`_extract` に既定値つきの引数 `priced: bool = True` を足し、`False` のときは今の投稿の行に値段を足さず、Gemini の件にも `price`・`quantity` を入れない（既定値のままのほかの試験は変わらない）。新しい試験 `test_extract_12h_puts_every_box_state_on_the_soldout_row_when_the_shime_has_no_price` で、元の試験と同じ post・同じ master に `priced=False` を渡し、元の 2 つの assert（相手 `[(22, 1), (24, 1)]`・印 `SOLDOUT_INHERIT`）がそのまま通ることを確かめる。この 2 つ以外の既存の試験は変えない。
4. 確かめ: `ruff check backend/app/services/gemini_raw_copy_v102_soldout_ref.py backend/tests/test_gemini_raw_copy_v102_soldout_ref.py`、`cd backend && python -m pytest -q tests/test_gemini_raw_copy_v102_soldout_ref.py tests/test_gemini_raw_copy_v102_product_first.py tests/test_v102_replay_diff.py`。
5. 合格基準（出力を貼り、判定は Opus）: ruff 合格／pytest の failed・error 0／`git diff --stat origin/main..HEAD` に出るのは上の 2 ファイルだけ／migrations・workflows に差が無い。
6. 止まる条件: 1 で読んだ関数・行・キーの名前がカードと違うとき、推測で直さず `NEEDS_DECISION:` で止まる。3 の (i) のほかに落ちる試験が出たとき、または `priced=False` の試験が 2 つの assert 以外の所（解析の誤り等）で落ちるときも、直さず `NEEDS_DECISION:` で生の出力を返す。

## 10. 設計審査（Opus の自己審査・独立の審査ではない）

- 判定: APPROVE（便1 は実装可能）。便4（設定を入れる）は §6 の未解決が片付くまで不可。どれも PO の承認が前提。
- 根拠: 変える所は 12d の 1 か所で、今は何もしない形だけが変わる（ほかの規則の結果は変わらない）。相手を複数書く仕組みと在庫表の外し方は既にある（recon §2-2）。設定が無ければ今と同じで、戻しは設定の行を消すだけ。受入条件はどれも数か○×で判定できる。
- マージ前の審査役（Opus・2026-11-10）の指摘で直した点: 戻り値の型を変えたときの既存の試験 6 か所の書き換えをカード 3 と K1 に書いた。カード 2 の壊れた文、§8→§9、便3→便2、`backend/app/tools/v102_replay_diff.py` の行番号、試験ファイルの名指し、カード 3 の判定の順を直した。
- 自己審査で直した点: 状態の表の名前（`public.line_conditions` → `public.conditions`）、やり直しの道具（試しのブランチにしか無い道具 → main にある `backend/app/tools/v102_replay_diff.py`）、それに合わせて語を記憶の中で足さず本番へ先に入れる順へ変えた。
- 未解決: 本番の `value_group` の今の値（便3 の道具の出力で確かめる）。設定を消した後の古い相手の扱い（§6）。K3 の数が 13/0/1 と違ったときの扱いは PO に戻す。
- 便3.5 のマージ前の審査役（Opus・2026-11-11）の指摘で直した点: 値段・数が付く `_extract` を使う既存の試験の扱い（カード 3 の (i)）、キーが無い件の読み方（カード 2）、カード 0 の `--claude`、§3-2 の 12 件の内訳、§2 の行番号。
- 便3.5 の追記（2026-11-11・自己審査）: APPROVE。根拠: 変える所は 12h を呼ぶ手前の 1 か所で、値段か数がある〆は今と同じ 12d に戻るだけ（消す側に広がらない）。便3 の 27 件のうち値段か数を持つのは誤りの型の 2 件だけなので、直る件は減らない見込み。それを K7 で確かめる。未解決: 設定を消した後の古い相手の扱い（§6）は便4 の前に PO へ。
