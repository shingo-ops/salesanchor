# Phase 3 設計 — 社外秘の原文の書き写しを送る前に止める（confidential-quote-guard）

> この文書は何か(専門用語なしの1行):
> 仕入元の投稿の文面を書類に書き写したまま送ろうとしたら、送る前に機械で止める見張りの設計。

親へのリンク: [個人側検問の正本化(local-hooks-ssot)](../../specs/local-hooks-ssot/README.md)（既存テーマの延長として扱う。STANDARD-WORKFLOW §1.8 の「既存仕様書の延長」。個人側の見張りを 1 本足すため）

- recon: [recon.md](recon.md)
- 関係する仕様: `docs/specs/local-hooks-ssot/README.md`（個人側の見張りは原本を repo に置き、PR で変える）。前例の置き場 `scripts/agent-hooks/review-gate/`（ADR-1029）
- 関係する ADR: ADR-1043（社外秘の正解表は公開リポジトリに置かない、`docs/adr/ADR-1043-accuracy-gold-in-db.md:21`）、ADR-075（秘密情報の扱い、`docs/adr/ADR-075-github-secrets-only-policy.md`）
- 状態: 設計案。PO の方針「2」（2026-10-25：照合の仕組みだけ作り、残っている文面はそのままにする）を受けた設計。実装は PO にこの設計を見せてから。
- 審査: 同一 AI（Opus）の自己審査。独立した第二者レビューではない。

## 1. 目的と KGI

- 目的: 仕入元の投稿の文面を、AI が repo の書類やプログラムに書き写して公開の置き場へ送ることを、送る前に機械で止める。
- 利用者に見える変化: PO から見た変化は無い。AI が文面を書き写した書類を送ろうとすると、その場で止まり、どの行のどの語句かが AI に示される。
- KGI（○× で判定）:
  - K1（PO 決定「1」2026-10-26 で改訂）: 10/25 に文面が漏れた記録のうち、#4727 のコミット（79ec6fa76）を送ろうとすると止まる（exit 2 で 1 語以上を示す）。#4729 のコミット（f13e335fb）は K1 から外す。残る当たりが、状態の一般語として一般語の表に入れた 1 語だけ（審査合格の 18060e58f にも同じ語が出る）で、書き写しの証拠が残らないため。
  - K2: 審査に合格した記録（#4730 のコミット）は止まらない。
  - K3: いま main にある docs と backend/tests を全部当てたとき止まる語句（recon §4-1 で 324 種類）を Opus が 1 つずつ見て、全部が「原文の書き写し」か「除外表に足したもの」のどちらかに分かれる（どちらでもないものが 0）。便1 で判定し、表は社外秘フォルダに置く。
  - K4: 1 回の照合は 2 秒以内。

## 2. 対象と対象外

- 対象: Mac で AI が行う次の操作。見るのは、送る差分で足した行と本文の、「」と『』の中の語句。
  - `git push`（足した行）
  - `gh pr create`／`gh pr edit`／`gh pr comment`／`gh pr review`、`gh issue create`／`gh issue comment` の本文（付け方は §3 の「動く条件」のとおり、短い形や標準入力も含む）。審査の結果を PR のコメントに書くことが多く、公開の置き場へ出る道になるため、PR 本文と同じに扱う。
- 対象外:
  - すでに GitHub に残っている閉じた PR の中身（PO 判断「2」）。
  - 「」の外にそのまま書き写した文面（§7 弊害で扱う。今回は数えるだけ）。
  - main の書類にすでにある書き写しに見える語句（recon §4-1 で約 140 種類）の書き換え。見張りは足した行だけを見るので、そのままでも作業は止まらない。書き換えるかは PO の判断（recon §5 の 3）。
  - 社外秘フォルダに置いていない原文（照らす相手が無い）。
  - GitHub 側の CI での照合（原文を GitHub に置けないため、できない）。
  - `gh api` で本文を付けて書く道と、取り込み操作に本文を付ける道（今の作業で使わないため。使うようになったら次の便で足す）。

## 3. 変える内容

- 新しい見張りの原本を repo の scripts/agent-hooks/confidential-quote-guard/（便1 で作る）に置く（guard.py・install.sh・rollback.sh・テスト）。review-gate（ADR-1029）と同じ形。原本には原文も語句も入れない（置き場の場所は Mac の表から読む）。
- install.sh が原本を ~/.claude/scripts に写し、~/.claude/settings.json の PreToolUse:Bash に pr-body-guard.sh の前で登録する。写したものと原本が一字一句同じかを diff で確かめる（local-hooks-ssot の H3 の考え方）。
- 動く条件: コマンドの中に、字句として `git` と `push` がこの順で現れるとき、または字句として `gh` のあとに §2 の gh の操作（`pr create/edit/comment/review`・`issue create/comment`）が現れるとき。字句は `shlex.shlex(posix=True, punctuation_chars=True, whitespace_split=True)` で分ける。読めないときは、粗い目印（`git`…`push`、`gh`…`pr|issue`）で見て、当たれば止める。`bash -c`・`sh -c`・`eval` を使う形は、目印に当たれば止める。
- 通す形（allow-list）: 命令文から作業場所や本文の出どころを推し量らない。決まった形に完全に一致するときだけ照らし、それ以外はすべて止める（照らせないものは通さない）。
  1. push は `git -C <絶対パス> push [-u|--set-upstream] origin <ref>` だけ。`<ref>` は `HEAD` か、英数字と `/._-` だけのブランチ名（先頭 `-`・`..` は不可）。後ろに付けてよいのは `2>&1` と `> <絶対パス>`／`>> <絶対パス>` だけ。`;`・`&&`・`||`・`|`・`&`・改行・`$`・バッククォート・heredoc・`cd`・`( )`・`<` は、引用符の外に 1 つでもあれば止める。`--force`・`-f`・`--force-with-lease`・`--no-verify`・`--mirror`・`--all`・`--tags`・`--delete`・`:ref` なども決まりの外なので止める。止めた理由の文は「git push は `git -C <worktree の絶対パス> push -u origin <ブランチ>` の形で、ほかの命令とつなげずに単独で流してください」。
  2. gh の本文は、(a) `--body-file`／`-F` の後ろが絶対パス、(b) 一重引用符で囲んだ `--body`／`-b` の値、の 2 つだけ。(a) はそのファイルを読んで照らし、(b) はその文字列を照らす。相対パス・`-`・`/dev/*`・heredoc・`$`・バッククォート・二重引用符・引用なしの本文・`--fill`／`--fill-first`／`--fill-verbose`／`--editor`／`-e`／`--web`／`-w`／`--template`／`--recover`・本文指定が 2 つ・`-dF` のような短い指定の束ね書きは止める。gh も単独のコマンドで流す（区切り・`cd` があれば止める）。止めた理由の文は「本文は Write で作ったファイルを `--body-file <絶対パス>` で渡してください」。本文の無い gh（`pr edit --add-label` など）と、`gh api`・`gh pr view` などは対象外。
  3. 引用符の外に書けるのは英数字と `_@%+=:,./-` だけ。二重引用符の中の `$`・バッククォート・`\`・`!` は止める。自前の字句分けと shlex の結果が食い違ったら止める。
- 照らす repo: 本文はどの repo でも照らす。足した行は、置き場の表に並べた repo（最初は shingo-ops/salesanchor だけ）の push のときだけ照らす。repo は `git -C <絶対パス>` の `<絶対パス>` の origin の URL で決める。表に無い repo の push は照らさずに通す（形が決まりの外なら、repo に関係なく止める）。パスが存在しない・git の repo でない・表に並んだ repo で `origin/main` が無い・sha が取れない・差分が取れない・表が無い／古い／壊れているときは止める（全部拒否に倒す）。
- 照らすもの:
  1. push の追加行。送る ref の sha を `git -C <絶対パス> rev-parse <ref>` で取り、`origin/<ブランチ名>` があればその merge-base から、なければ `origin/main` との merge-base から、sha までの差分の追加行（全ファイル）。`HEAD` のブランチ名は `git symbolic-ref` で決める。
  2. gh の本文。上の (a) のファイルの中身、または (b) の文字列。
- 作業場所を推し量る処理（`cd`・`-C` 以外の場所決め・`pushd`・heredoc の中身の読み取り・命令文から ref を読む処理）は持たない。理由: 5 回の審査で、命令文を正規表現や shlex で読んで作業場所や本文の出どころを推し量る作りは、直すたびに新しい穴が開いた（F1〜F4、重い 1/2、重い 1、重い 1、重い A/B）。決まった形だけ通す作りなら、読み間違いが「止まる」側にしか倒れない。
- 送信前フック（git の pre-push）に移さなかった理由（事実）: 今の環境では多くの worktree で pre-push が走らない。(1) `core.hooksPath` は共有設定（`/Users/tanizawashingo/salesanchor/.git/config`）の 1 つだけで、値は `frontend/.husky/_`。`extensions.worktreeConfig` が無効のため `git config --worktree` は使えない。(2) `scripts/new-worktree.sh:115` の `git -C <worktree> config core.hooksPath frontend/.husky` も共有設定を書き換える（一時リポジトリで再現）が、`frontend/package.json` の `prepare`（husky）が `frontend/.husky/_` に書き戻す。(3) `frontend/.husky/_`（husky の置き場、.gitignore 対象）がある worktree は、`~/worktrees/salesanchor` 配下 51 個のうち 4 個だけ。この worktree にも無く、`git rev-parse --git-path hooks/pre-push` が指す `frontend/.husky/_/pre-push` が存在しない。worktree の土台（new-worktree.sh と既存 51 個）に手を入れるのはこのテーマの範囲を超えるため、送信前フックはやめた。
- 止める決まり: 次の 3 つを全部満たす語句が 1 つでもあれば exit 2。
  1. 「」または『』の中にあり、4 文字以上。
  2. 除外表に無い。除外表は「状態の言葉の写し」「商品名の写し」「一般語の表」の 3 つ。数字と区切りだけの語句も止めない。
  3. 原文の置き場のどれかのファイルに、そのまま現れる。
- 止めたときの表示: ファイル名と行番号と語句。表示先は AI の画面だけで、送らないので外には出ない。「形の説明に書き換える」よう案内を付ける。
- 止めた記録: 既存の見張りと同じ `_hook_blocked_log`（agent-events.jsonl に 1 行足す。pr-body-guard.sh:12・:158 と同じ）で、日時・見張りの名前・ファイル名と行番号・止めた語句の数だけを残す。語句そのものは記録に書かない（記録も社外秘にしないため）。local-hooks-ssot の H7（いつ・何を・なぜ）に当たる。
- 原文の置き場（PO 決定「1」2026-10-25）: 本番の投稿原文（`ai_ro.public__source_messages` の `raw_text`）だけを、見比べる相手にする。2026-10-25 に ADR-1024 の道で数えた結果は 3,812 行・約 279 万字（うち is_active が真は 228 行・約 8 万字）。is_active に関係なく全行を使う（取り下げた投稿も社外秘だから）。以前の 2 経路（R2-raw の msgs_*.tsv と check3 の msgs/*.txt、計 120 ファイル）は外す。正本は本番の記録 1 か所のまま。
- 原文の写し: `scripts/agent-hooks/confidential-quote-guard/fetch_corpus.py` が毎日 1 回、本番から鍵付きフォルダ（`~/CC報告ファイル-keep/confid-guard/`、700）に 1 ファイル（`source-messages.txt`、600）だけ取り直す。読み取りは ADR-1024 の道だけ（読み取り専用の鍵、ai_ro の同名ビュー、SQL は標準入力から 1 文ずつ）。manual-only の鍵は使わない。読み取り台本は 1 つの値を 10,240 字で切るので、8,000 字ずつに分けて取って繋ぎ、本番の件数・文字数の合計と一致を確かめる。一時ファイルに書き、一致してから置き換える。途中で失敗したら前の写しを残して 0 以外で終わる。前回の半分未満に減ったときも置き換えず止める。件数・文字数・日時は別ファイル（`source-messages.meta`、本文なし）に残す。
- 写しが古いとき: guard は、原文の写しが 2 日より古ければ止める（exit 2、「原文の写しが古い」）。古い写しで通すと新しい投稿を照らせないため。
- 毎日の取り直し: LaunchAgent（`jp.salesanchor.confidential-quote-guard-fetch.plist`、毎日 06:30、RunAtLoad=true・KeepAlive=false）。原本は repo、install.sh が写して登録、rollback.sh が外す（PO が `!` で流す）。多重起動は mkdir ロック＋trap で防ぐ。
- 原文の置き場の表（confidential-corpus.conf）: `corpus:` の行は上の写し 1 つだけ。`repo:` の行は変えない。
- 商品名の写し: 共用の商品マスタ（公開して困らない名前）の商品名・シリーズ名・検索ワードを、読み取り専用の道（ADR-1024）で取り出して Mac の社外秘フォルダに置く。recon §4-1 の 170 種類はここと一般語の表で消す想定。写しが古くなると新商品名で誤って止まるので、週の点検で取り直す。
- 一般語の表（confidential-allow.txt）: 1 行 1 語で、語ごとに足した理由を書く。最初は、ダメージの有無の言い方のように、状態の写しに無い状態の一般語を入れる。足すのは Opus の判断でよい。足したら記録に残し、週の点検で見直す。
- 置き場の表が無い、空、または読めないときは止める（全部拒否に倒す）。表示で理由を示す。
- 抜け道は作らない（環境変数で飛ばす仕組みは無し）。誤って止まったときの直し方は、一般語の表に足すことだけ。

## 4. 受入条件

| 基準 | 検証方法 |
|---|---|
| K1 #4727 の記録（79ec6fa76）が止まる | そのコミットを子に置いた作り物の repo で、決まった形の push（`git -C <絶対パス> push -u origin HEAD`）を見張りに渡し、exit 2 で 1 語以上を示すことを確かめる。種類数は参考に残す。#4729 の記録（f13e335fb）は K1 の対象外（一般語の表に入れた 1 語だけが残る）で、rc は参考に記録する |
| K2 #4730 の記録が通る | 同じ方法で 18060e58f を渡し、exit 0 を確かめる |
| K3 既存の書類で説明できない停止 0 | main の docs と backend/tests を全部当てた一覧を Opus が 1 語ずつ判定し、表に残す（社外秘フォルダに置く） |
| K4 2 秒以内 | 上の 3 回の time の値 |
| 置き場が無いと止まる | 表を空にした試しで exit 2 |
| 表に無い repo は通る・表にある repo で差分が取れないと止まる | origin/main の無い作り物の repo で 2 通りを試し、exit 0 と exit 2 |
| コメントの本文も照らす | 作り物の原文の語句を入れて、(a) `--body-file <絶対>`・`-F <絶対>`・`--body-file=<絶対>`、(b) `--body '…'`・`-b '…'`・`--body='…'` がどれも exit 2。語句を入れない同じ形は exit 0 |
| 決まりの外の gh の形は止まる | 相対パス・`-`・`/dev/stdin`・`/dev/fd/*`・heredoc・`$(cat …)`・二重引用符・`--fill*`・`--editor`・`--web`・`--template`・`--recover`・本文 2 つ・束ね書き・パイプ・`&&`・`cd` つきが、中身が clean でもすべて exit 2 |
| 本文のファイルが読めないと止まる | 存在しないファイルを `--body-file` と `-F` に渡して、どちらも exit 2 |
| 決まりの外の push は止まる | `cd <絶対> && git push`・`git push origin HEAD 2>&1 \| tail`・`git -C <相対> push`・`--force-with-lease`・`--no-verify`・`GIT_DIR=… git push`・審査の J1・G1〜G3・B1〜B5・A1・A3・C2・C3・E7・E8 が、中身が clean でもすべて exit 2 |
| 別のブランチを送るときも照らす | 作り物の語句を足したブランチを、別のブランチにいるまま `git -C <絶対> push -u origin <そのブランチ>` で送ろうとして exit 2 |
| 場所の条件 | 表に無い repo は exit 0、パスが存在しない・git の repo でない・origin/main が無い表の repo は exit 2 |
| 止めた記録が残る | 止めた試しのあと agent-events.jsonl の最後の行に、見張りの名前・日時・件数があり、語句が無い |
| 見張りのテスト | scripts/agent-hooks/confidential-quote-guard/ に作り物の原文で試すテストを置く（本物の原文はテストに入れない）。止まる・通る・置き場なし・除外表・「」の外は止めない、の 5 つ |

## 5. 外部・過去事例の参照と我々への応用

- 社内の前例: worktree-only-guard.sh、review-gate（マージ前の審査記録を照らして止める。原本は `scripts/agent-hooks/review-gate/gate.py`、配り方は同じフォルダの install.sh・rollback.sh）、pr-body-guard.sh。どれも「送る・マージする前に、決まりを機械で照らして止める」形で、この設計も同じ形にする。止めるときの終わり方（exit 2）と、コマンドから作業場所を決めるやり方を、pr-body-guard.sh にそろえる。
- 社内の前例 2: 秘密情報の検査（`.gitleaks.toml`）は、形で見つけて除外表で誤検知を消す作り。この設計の一般語の表も同じ考え方にする。
- 外部の数値事例: 使わない。照らす相手が「自社だけが持つ原文」で、外の事例の数値はこの誤検知率の根拠にならないため。代わりに K1〜K3 の実測で決める。

## 6. 影響範囲

- 呼び出し元: Mac で AI が打つ `git push` と §2 の gh の操作の全部（どの repo でも）。足した行を照らすのは表に並べた repo だけなので、ほかの repo の push は照らさずに通る。本文はどの repo でも照らす（照合の時間は K4 で測る）。
- 変えないもの: 製品のコード、DB、本番、GitHub の CI。repo で足すのは、見張りの原本（scripts/agent-hooks の下）と ADR と AGENTS.md・FEATURE-INDEX の追記（§8）。

## 7. 弊害とその対処

- 「」の外に書き写すと止められない: 照らす範囲を広げると自分の言葉で止まりやすい。今回は、K3 の一覧で「」の外にも同じ語句があるかを数えるだけにする。数が多ければ次の便で範囲を広げる。
- 誤って止まり、作業が止まる: 一般語の表に足せば直る。足した語は週の点検で見直す。
- 原文の置き場が増えても表に入らないと、すり抜ける: 原文を取る道具の出力先を表に入れる決まりを、実装の便の ADR に書く。週の点検で、社外秘フォルダの新しいフォルダが表に入っているかを数える。
- push のたびに 0.4 秒前後かかる: K4 で上限 2 秒を確かめる。

## 8. 計画

- 便1（この設計の実装・1 回）:
  - 見張りの原本・install.sh・rollback.sh・テストを repo に作る（担当: Sonnet）。表 2 つと商品名の写しは Mac の社外秘フォルダに作る（repo に入れない）。
  - PR がマージされたあと、PO が `!` で install.sh を流して写し、登録する（ADR-1011:39「フックの変更は AI がパッチを作り、PO が `!` で反映する」、前例 `scripts/agent-hooks/review-gate/install.sh:2`）。AI は settings.json を自分で書き換えない。
  - repo 側では ADR を起案し、AGENTS.md に新しい必須の照合を 1 行足す（新しい必須チェックの追加にあたるため）。FEATURE-INDEX に 1 行足す。
  - K1〜K4 を測る。
- 便2（必要なら）: 「」の外への広げ方。K3 の数を見てから決める。

## 9. 戻し方

- PO が `!` で rollback.sh（便1 で scripts/agent-hooks/confidential-quote-guard/ に作る）を流し、settings.json の登録 1 つを外す（review-gate と同じ形）。変える前の settings.json は日付付きの写しで残す。
- rollback.sh は毎日の取り直し（LaunchAgent）も外す。表 2 つ・原文の写し・スクリプトは消さずに残してよい（登録が無ければ動かない）。

## 10. 審査（同一 AI の自己審査）

- 結論: APPROVE（設計として）。#4736 の reviewer（opus）の REVISE（A〜K）を受けて、実行する人（PO の `!`）・止めた記録・写しのずれの点検・コメントの本文・照らす repo の決め方を足した。最初の案では見張りを Mac のホームにだけ置く形だったが、local-hooks-ssot（原本を repo に置く）と食い違うため、review-gate と同じ置き方に直した。
- 根拠: 止める決まりは K1 の 79ec6fa76 を止め、K2 で止まる 1 語は一般語の表で消える（f13e335fb は PO 決定「1」2026-10-26 で K1 から外した）。既存の書類に当てた試し（recon §4-1）で、商品名で誤って止まることが分かったため、除外表に商品名の写しを足した。止める場所（PreToolUse:Bash、exit 2）は既存の見張りと同じ形（recon §2）。
- 未解決:
  - 原文の置き場は、本番の投稿原文に決まった（PO 決定「1」2026-10-25。17 フォルダの調べは不要になった）。
  - main にすでにある書き写しに見える約 140 種類の扱い（PO 判断。この設計の実装とは独立）。

## 維持の仕組み

- 守り手: 人手で守る。理由: 関所の本体（scripts/agent-hooks/confidential-quote-guard/guard.py）は便1 で作るため、この設計の段階ではまだ無い。それまでは Opus が書いたあと原文と照らす（この PR でも実施）。便1 のあとの守り手は guard.py と、下の週の点検。
- 対象: guard.py と fetch_corpus.py の原本と ~/.claude/scripts に写したもの、confidential-corpus.conf、confidential-allow.txt、商品名の写し。
- 週の点検（agent-console の定期実行。Opus が結果を見る）で、次の 5 つを数える。
  - 原本（origin/main の guard.py）と写したもの（~/.claude/scripts）の diff。1 行でも違えば知らせる（local-hooks-ssot の H4・H5）。
  - 一般語の表の行数と、その週に足した語。
  - 商品名の写しの日付（7 日より古ければ取り直す）。
  - 原文の写しの日付（2 日より古ければ知らせる。毎日の取り直しが止まっている印）。
  - 原文の写しの件数が前回より減っていないか（減っていれば知らせる。取り直しの時点で半分未満なら置き換えずに止まる）。
- 決まりの正本: 便1 の ADR。
