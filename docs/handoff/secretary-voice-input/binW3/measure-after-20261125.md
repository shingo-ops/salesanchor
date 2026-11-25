# 便W3 反映後の測り（2026-11-25）

- 対象: PR #5754（合流 8514935472e986d631624b9178c32a4bc4add88b・2026-11-25 04:47:48Z）。配備（deploy.yml の実行 45549208528）は 04:53:22Z に成功。本番のサーバーの git の先頭は 8514935472e986d631624b9178c32a4bc4add88b。本番の backend の中に `afternoon_hours` と `edit_dropped` があることを grep で確かめた（secretary_dates.py 1 行・assistant.py 6 行）。
- 道: 本番の使い捨て容器（`docker compose -p astro-webapp run --rm --no-deps -T backend python -`）から `http://secretary-codex:8090/intent`（model gpt-5.6-terra）。読むだけ（記録・予定は作られない）。1 件ずつ順に流した。
- 台本: `docs/handoff/secretary-voice-input/binW3/probe_after.py`（118 件・04:56:10Z 開始）。数え方: `docs/handoff/secretary-voice-input/binW3/judge_after.py`。
- 生の結果: `docs/handoff/secretary-voice-input/binW3/probe-after-20261125.jsonl`（118 行・200 以外 0 件・中央値 6.21 秒・最大 12.2 秒）・`docs/handoff/secretary-voice-input/binW3/regress-after-20261125.tsv`（23 件＋見出し）。
- カルテ: 打ち合わせ 2026-11-30 15:00〜16:00（+09:00）・今は 2026-11-25 20:00（新しい頼みは 20:00 と 09:00 の 2 通り）。

## 結果

| # | 合格ライン | 結果 | 判定 |
|---|---|---|---|
| Y1 | 試験が緑・素の 1〜6時が 13〜18時になった数 48 回中 48 回 | 48/48（新しい頼み 24・「あさってN時にして」12・「N時に変えて」12）。PR #5754 の CI で pytest・画面の試験とも合格。直す前の下調べ（`docs/handoff/secretary-voice-input/binW3/probe-before-20261125.jsonl` の素の 1〜6時の行を AI の読んだ始まりで数えた）は 48 回中 13 回が 12 時より前 | ○ |
| Y2 | 7〜11時の 40 回中 40 回が朝のまま | 40/40 | ○ |
| Y3 | backend と画面の試験が緑 | PR #5754 の CI で pytest（SQLite + PostgreSQL RLS）・Frontend unit tests とも合格 | ○ |
| Y4 | 直す頼みの読み落とし 0 回・お願いします類で作られる 14/14 | 読み落とし 0/16・作られる 14/14 | ○ |
| Y5 | 決まり帳の試し 23/23 | 23/23（invoice 8・event 8・unknown 4・rule 3・中央値 5.77 秒・最大 9.04 秒） | ○ |
| Y6 | 追加の費用 0 円・新しいサービス 0 件・指示文は変えない | 合流で変わった製品ファイルは backend 3・試験 2・frontend 3・openapi 1 の 9 件。容器・指示文・依存の変更 0 件。呼び先は今までの /intent だけ | ○ |

- Y4 の数え方の注: 直す頼み 8 種 × 2 = 16 回のうち 14 回が `edited` 真。残り 2 回は「はい、3時からにして」。AI は 2 回とも始まり 2026-11-30T15:00:00+09:00 と読み、カルテが既に 15:00 なので変わった欄なし（`edited` 偽が正しい）。下調べ（`docs/handoff/secretary-voice-input/recon.md` 169 行）と同じ数え方で、読み落とし 0。数える台本 `judge_after.py` はこの 2 回を「YES NG」とし「[14, 16]」と出すが、台本は値が変わらない場合を分けていないためで、読み落としではない（次の便で台本側を直す候補）。
- 審査 L4 の注: 台本には本番の口の Meet の分かれが無い。「はい、Meetも付けて」の `edited` 真・add_meet 真は台本の上の値で、本番の口の値とは違うことがある（設計 §18-11）。Meet の扱いは今回の直しの範囲の外。
- 審査役の止めない指摘（PR #5754）: ①`frontend/src/features/secretary/secretaryApi.ts` の `edit_dropped` に説明の注釈が無い ②「4時から7時」は終わりも 19:00 になる（設計どおり・今回の測りの外） ③「04時」のような 0 付きの書き方は対象外（設計 §18-2）。いずれも次の便の候補として残す。
