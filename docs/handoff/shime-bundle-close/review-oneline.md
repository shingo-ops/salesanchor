# review: 1行の並び〆（規則14）の設計審査の記録

対象: `docs/handoff/shime-bundle-close/design-oneline.md`
審査役: クラウドの architect（claude-opus-5-5、読むだけ）。同じ AI の別の起動による審査で、独立した第二者の審査ではない。

## 1回目（2026-11-17、commit f967dcb2c）: REVISE
判定: (1)○ (2)○ (3)× (4)× (5)△ (6)×

| # | 重さ | 指摘 | Opus の確かめ（実物） | 直し |
|---|---|---|---|---|
| 1 | 重 | 新しい match_status を `_RESOLVED_MATCH_STATUSES` に入れないと product_id が None で保存される | 事実。`backend/app/services/line_analysis_v102_svc.py:732-734` と :765 | §3-1 の3で定数を足すと決めた。T9 で product_id・pid_resolved・pid_basis を見る |
| 2 | 重 | 規則12が何も返さない商品の代わりの相手は、`build` の出力に condition_id・ref_message_id・ref_line が無いので作れない | 事実。`backend/app/services/gemini_raw_copy_v101.py:1366` だけが付ける。`_apply_soldout_targets` が `targets[0]["condition_id"]` を読む | §3-1 の2で、在庫の行から `_soldout_target` で作る形に変えた。在庫が無い商品は入れない。相手のある最初の商品を先頭にする。`soldout_posts` が空なら動かさない。T10・T11 を足した |
| 3 | 中 | 規則12に渡す並びが決まっていない | 事実。`_is_inherit_candidate` は添字で引き、12e の same_post はほかの件から作る | §3-1 の2の1で「i 番目だけを差し替えた並びを渡し、decisions.get(i) を取る」と書いた |
| 4 | 中 | `v102_replay_diff` の列に match_status が無く、段ごとの状態は記録できない | 事実。`backend/app/tools/v102_replay_diff.py:37-39` | 規則14を前に置いたので段ごとの状態は判定に要らない。K2 は列にある product と soldout_targets で見る形にした |
| 5 | 中 | `_apply_context_work` が先に片方に決めると規則14が動かない | 推測（審査役）。`_apply_context_work` は ambiguous を作品で決める（`gemini_raw_copy_v101.py:1277-1300`） | 規則14を `_apply_context_work` より前に移した。T8 に context の形を足した |
| 6 | 小 | 区切りの数の上限が無い。型番だけの区切りの扱いが書かれていない | 設計の抜け | 区切りは2つ以上5つ以下にした。型番だけは今の照合の結果をそのまま使い、K3 で変わった投稿を見る |

## 2回目（2026-11-17、commit a4da03b4a）: REVISE
判定: 1回目の指摘1〜6 すべて○。(2) 新しい食い違い × 。(3) 1回目の○を崩していない ○。

| # | 重さ | 指摘 | Opus の確かめ（実物） | 直し |
|---|---|---|---|---|
| 1 | 中 | 区切りごとに状態の語が違う形（「A 未開封、B 開封〆」）で、B の相手の状態を取り違える | 事実。`backend/app/services/tcg_analyzer_svc.py:938-953` は行全体で状態を決め、語が1つでも当たれば basis が `R{priority}:{語}` になる | §3-1 の対象の件に条件5「状態が語で決まっていない」を足した。T12 を足した |
| 2 | 小 | §3-1 の3の確かめが match_status だけで、`soldout_target_basis` の値を使う所を見ていない | 事実。値は `line_analysis_v102_svc.py:961` で condition_basis に書かれる。grep で使う所は5か所だけ・値で分ける所は無い | §3-1 の3に grep の結果と、実装の最初に流す grep を足した |
| 3 | 小 | K1 と §7 が「T1〜T9」のまま | 事実 | T1〜T13 に直した |
| 4 | 小 | 規則14の中の規則12が後の段より前に動き、same_post が最後の規則12と違い得る | 事実（`gemini_raw_copy_v102_soldout_ref.py:457-459`）。違いが出るのは同じ投稿で後に同じ商品に決まる件があるときだけで、閉じるのは過去の投稿の行 | 受け入れると §3-1 に書いた。T8 に同じ形を足した |
| 5 | 小 | 代わりの相手が、新しい投稿で完売になった在庫を相手にし得る | 事実（作り方が在庫の行だけを見ていた） | §3-1 の2の2を `_stranded_stock(...).get(〆の状態)` に変えた（12e と同じ見方）。T13 を足した |

## 3回目（2026-11-17、commit d78c426d1）: REVISE
判定: 2回目の指摘 1×（新1） 2○ 3○ 4×（新2） 5○。(2) × 。(3) 1回目・2回目の○を崩していない ○。

| # | 重さ | 指摘 | Opus の確かめ（実物） | 直し |
|---|---|---|---|---|
| 1 | 中 | 条件5を照合前の件の basis で見ると、箱系の商品にだけ効く状態の語を見落とす | 事実。`backend/app/services/gemini_raw_copy_v102_product_first.py:819-824` は商品が箱系で単位の区分が決め直しの対象のときだけ箱系で状態を決め直す。照合前の件は商品の分類が空 | 条件5を、組の全部の商品 p の `build(i, p)` の basis で見る形に変えた。T14 を足した |
| 2 | 小 | 先頭の商品は書く行が先頭の相手の状態で上書きされるので、同じ投稿に同じ (商品, 状態) の在庫の行があると両方が現行で残る | 事実。`backend/app/services/line_analysis_v102_svc.py:957-962` が `targets[0]` で上書き。`backend/app/services/tcg_analyzer_svc.py:2104-2117` は投稿ごとに順位を決める | 条件6「同じ投稿の在庫の件の商品と候補に組の商品が無い」を足した。same_post の受け入れの理由を書き直した。T15 を足した |
| 3 | 小 | T8 の「今の投稿の行を指さない」は相手が必ず過去の投稿から作られるので、何も確かめていない | 事実 | T8 の確かめを「書く行の (商品, 状態) が先頭の相手 (A, X) と同じ・B の相手が2つ目以降にある」に変えた |

## 4回目（2026-11-17、commit 8410649d0）: REVISE
判定: 3回目の指摘 1○ 2×（新2） 3○。same_post の受け入れの新しい理由は正しい ○。(2) × 。(3) 1〜3回目の○を崩していない ○。

| # | 重さ | 指摘 | Opus の確かめ（実物） | 直し |
|---|---|---|---|---|
| 1 | 中 | 条件5を `build(i, p)` で見ると、シングル系・バルク系等の分類の既定の basis（`R7:単品既定` 等）を語と見て、その分類を含む並び〆で規則14が動かない | 事実。`backend/app/services/gemini_raw_copy_v102_product_first.py:99-103` の値は `R\d+:` で始まり、`backend/app/services/gemini_raw_copy_v102_soldout_ref.py:43-54` の語でない既定の一覧（R4:単位既定・R5:パック既定）に入っていない。正の3投稿の商品を決めた後の basis は保存の列に無く未確認 | 分類の既定の5つは規則14の中だけ「語で決まっていない」と見る形にした（関数は変えない）。その商品の相手は2の2で作る。T16 を足した。正の3投稿への効きは K3 で見ると書いた |
| 2 | 小 | 条件6は候補しか見ないので、unmatched の在庫の件が後の段の `_apply_followup` で組の商品に決まる道を外せない | 事実。`backend/app/services/gemini_raw_copy_v102_followup.py:116-130` は unmatched も対象、候補の制約は :108 で ambiguous だけ | 条件6に「`followup_ref` があれば今の並びで `decide_followup` を流し、在庫の件が組の商品に決まるなら動かない」を足した。T15 に unmatched の形を足した |

## 5回目
未。
