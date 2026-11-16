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

## 2回目
未。
