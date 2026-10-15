# review: Mac の自動お手入れの見張り（mac-jobs-watch）

この文書は何か(専門用語なしの1行): 設計とコードの審査の結果を残す記録。

審査は同じ AI（Claude Opus）の別の起動による自己審査で、独立した第二者レビューではない。生の審査結果は /tmp/CC報告ファイル/ac-heavy/mac-jobs-watch/ に置いた。

## 設計審査

| 回 | 日付 | 判定 | 主な指摘 | 反映 |
|---|---|---|---|---|
| 1 | 2026-10-15 | REVISE | HIGH-1 停止失敗の行が次の行で隠れ見逃す／HIGH-2 自動片付けのロックが残ると見張りも黙る／MED-1〜7（送信失敗時の状態、ログイン直後の誤報、04:00 直後の誤報、試験の不足、dj-err の扱い、K4 の手順、眠りの扱い）／LOW-1〜4 | design §3 を出来事型（既読位置）・古いロックの判定・起動直後の待ち・04:00 の猶予・送信ごとの状態更新に改訂。§4 試験を ㉑ まで追加。MED-7 は【未確認】として §4 の観察で確かめる |
| 2 | 2026-10-15 | REVISE（軽） | N-MED-1 外したラベルの unloaded の復旧が未定（K4 の 2 回目が不合格になる）／N-MED-2 K4 の状態ファイルの置き場の自己矛盾／LOW 8 件 | §3-3 に unloaded の一まとまり判定を追記、K4 を `D/state/state` に修正、試験 ㉒〜㉔、K5 の空行対策、plist の XML 逃がし、K3 の副作用、手順書の二重持ちの注記を追記 |
| 2 の反映確認 | 2026-10-15 | APPROVE | 審査役が「1〜2 文の書き足し 2 か所で足り、3 回目の全体審査は不要。反映差分を Opus が確かめれば足りる」とした。Opus が N-MED-1・N-MED-2 の反映を design.md の該当文で確認 | — |

残る未確認: 眠りの時間が launchd の 1800 秒に数えられるか（MED-7）、launchd がログイン時の常駐を全部読み込んでから RunAtLoad を始めるか（N-LOW-1）。

## コード審査

- 1回目（Opus architect）: REVISE。MED-1（dj-stale の誤った復旧通知）・MED-2（試験 m01〜m08 が中身のない合格）・LOW-1〜6。生出力: /tmp/CC報告ファイル/ac-heavy/mac-jobs-watch/review-code1.md
- 対処: 設計 8a8eff529（dj-stale の判定条件を「判定する回」側へ移動・curl --max-time 20・plist は本体の終了コードを返す）、実装 7276de562。LOW-5（ロック競合）・LOW-6（状態置き場が書けない）は記録のみ（design.md リスク表）。
- Opus 再確認（2026-10-15 実測）: /bin/bash で PASS=147 FAIL=0、plutil OK、mjw_judged の dj-stale 行は 3 条件（起きていた回・起動が直近04:00より前・04:00+猶予以降）、curl に --max-time 20。変異試験 12/12 を試験が検出（impl2/mutation.txt）。生出力: /tmp/CC報告ファイル/ac-heavy/mac-jobs-watch/impl2/
- 判定: APPROVE（Opus 確認・同一AIによる審査）
