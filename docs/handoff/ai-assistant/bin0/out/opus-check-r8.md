# 便0-B 8回目 停止の確認（Opus・2026-11-28）

対象: origin/release/ai-assistant-bin0b ae6fcf261（2b7c88080 の上に 03a2398e1 道具の直し・ae6fcf261 停止の記録）。
読んだもの: 変更全文 diff.txt 1160 行（全部）・クラウドの実行記録 162 件（全部・次ページなし）・impl-report-b-r8.md・measure-b-r8.md・raw/r8-*。
Hermes 元ソース: 完成品の `hermes --version` が示す upstream 8fc03744 = GitHub NousResearch/hermes-agent 8fc0374447313e276f6b9a2764bfc750190c966a（2026-11-24）。`gh api` の contents（ref にこの番号）で読んだ。写しはリポジトリに置かない。完成品の中身と同じかは、9回目で容器の中の同じ行を grep して確かめる（まだ確かめていない）。

## 1 止まった理由（事実）

- 対照①（題づけ on）: 作り物の AI に chat が 2 回届いた（stream=True 1・stream=None 1、raw/r8-5-fakelog-c1.txt）。会話の GET は api_call_count=1・input 11・output 7（raw/r8-5d-probe-c1.txt）。
- カード card-bin0b-r8.md:75 の ○ の形は api_call_count 2。これは設計 design.md:88 で「未確認」と書いた見込みを、確かめずに ○ の形にした。**設計役（Opus）の入れ忘れ**。
- 元ソースの答え:
  - persistence/conversation/usage.py:3「auxiliary usage kept off the session counters」。:154 record_auxiliary_usage は「The session counters, cost fields and recent route are untouched」。
  - persistence/sqlite/conversation/_store/usage.py:238-270: 後ろの処理（vision・compression・title_generation・background_review、:245-251）は表 `session_model_usage` に task 名つきで書く。会話の数（sessions 表）には足さない。
  - 同 :51-59・:212-234: 本体の呼び出しも `session_model_usage` に task='' で書く。
  - 同 :274-298 auxiliary_usage_by_task: `session_model_usage WHERE task != ''` を足す。呼ぶ所は hermes_cli/oneshot.py:53（`-z --usage-file`）。
  - agent/title_generator.py:27-31・:822-824: 題づけは別の糸で走り、使った量を会話に付ける（ただし上の別の表へ）。
- 結論（事実）: 会話の api_call_count と使った量は「本体の呼び出しだけ」を数える仕組み。K9 の今の測り方（会話の数と返事の量を比べる）では、後ろの処理は原理的に見えない。

## 2 その他の不具合・ずれ（全部）

| # | 事実 | 根拠 | 扱い |
|---|---|---|---|
| a | 作り物の AI のログから system の頭（sys0）と最後の頭（last）を消した。形の指示が AI に届いた証拠が 8回目のログに残らない | 実行記録 03:36:28 の差分 | 設計で「形の指示の先頭の決まった文が届いたか ○×」だけを書く欄を足す（文そのものは書かない） |
| b | 試験 18 の作り物のデータを 1 回直した（1 回目 1 件失敗→直して 18 件合格）。直したのは試験のデータ（数えるたび 2 行ずつ減る形）で、台本の本体ではない | 実行記録 03:37:01・03:37:05・03:37:12、diff.txt:1124-1160 | 試験の意図（減らなければ止まる）は保たれている。○ |
| c | カードに無い足し: k9_ok の順（ずれ→0、読めない→-、他→1）・詰め直し後の起動待ち 180 秒で終了 6・probe の --keys-file・k7count の空ファイルで終了 2 | impl-report-b-r8.md | どれも止まる側に倒す足し。9 回目のカードに正式に書く |
| d | 頼みの文のファイル: 1 回目 32 行→同じ文を 1 つにまとめて 31 行 | 実行記録 03:37:29・03:37:34 | カードに「重なりは 1 つにまとめる」と行数の見込みを書く |
| e | push の時の「提出前の入口」が「origin/main との分岐点が見つかりません。終了コード 2」で判定できずに通した | 実行記録 03:39:29 | クラウドの写しの浅い取得が原因かは未確認。書類だけの枝で害は無い。記録だけ |
| f | commit の時に tools/claude-channels/intake/CLAUDE.md の LIMITS 未登録の警告 | 実行記録 03:37:44 | この件と無関係の既にある警告 |
| g | 終わりの見張りが「未追跡のファイルがある」と言った。作業場所は空。本店の写しの active-work.d のファイル | 実行記録 03:39:33-36 | 害なし |
| h | new-worktree.sh が新しい枝を origin/main 追跡で作り、すぐ origin/release へ付け替えた。HEAD=origin=2b7c88080 を確かめ済み | 実行記録 03:33:11-16 | ○ |
| i | 後片付け: 容器・置き場・固定設定 2 つ・鍵・頼みの文ファイルを消した | 実行記録 03:38:53-54 | ○ |

## 3 K9 の測り方の直し（第2.9版の材料）

- 本当の記録は state.db の `session_model_usage`。会話を消す前に、走っている容器の中で読み取り専用で数える:
  - task='' の api_call_count の合計 = 1（1 送信 1 回）
  - task!='' の行 = 0（後ろの処理 0 回）
- 対照①（題づけ on）: task='title_generation' の行が 1 つ出ることを先に確かめる（題づけは別の糸なので、出るまで待つ上限を決める）。出なければこの方法も使えないので止める。
- 対照③（題づけ off）: 3 部屋とも task!='' 0 行・task='' 1。
- 未確認（第2.9版で確かめる手順を入れる）:
  - 消す（DELETE）で `session_model_usage` の行も消えるか（K7 の残らない、に関わる）
  - HTTP の口で後ろの処理の量を返す所があるか（既定の枝の検索では oneshot.py だけ・8fc03744 では未確認）
  - 容器の中の python で読み取り専用（mode=ro）で開けるか・state.db の WAL と並んで読めるか
