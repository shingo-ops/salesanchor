# ADR-1045: 仕入元の原文の書き写しは、送る前に機械で照らして止める

| 項目 | 内容 |
|------|------|
| ステータス | Proposed（実装の許可は PO から出ている。フックの登録は ADR-1011:39 により PO が `!` で行い、その後に採用へ変更） |
| 備考 | PO 2026-10-25「1」：見張りだけ作る。main の既存の書き写しに見える語句は書き換えない |
| 起案日 | 2026-10-25 |
| 方針の決定者 | Shingo（PO） |
| 関連 | ADR-1043（社外秘の正解表は公開リポジトリに置かない）、ADR-075（秘密情報の扱い）、ADR-1029（review-gate。原本を repo に置く前例）、ADR-1011（フックは AI がパッチ・PO が反映） |
| 設計・根拠 | [design.md](../handoff/confidential-quote-guard/design.md)、[recon.md](../handoff/confidential-quote-guard/recon.md) |

---

## What（何を決めたか）

1. Mac で AI が打つ `git push`（足した行）と、`gh pr create/edit/comment/review/merge`・`gh issue create/edit/comment`・`gh release create/edit`・`gh repo edit`（本文・題名・notes・説明）を、PreToolUse:Bash の見張り `guard.py` で照らす。照らすのは決まった形だけ（push は `git -C <絶対パス> push [-u] origin <ref>`、gh の本文は `--body-file <絶対パス>`／`-F <絶対パス>` か一重引用符の `--body '…'`／`-b '…'`）。決まりの外の形は、命令文から作業場所や出どころを推し量らず、すべて止める。変数・展開で git／gh の字を隠せる形、`git remote set-url`／`add`、push の送り方を変える設定（`push.followTags`・`remote.*.push` など）、`git replace`（と `refs/replace` がある repo の push）、`.git/hooks/` への書き込み、`gh release` の添付ファイル・`--notes-from-tag`・`upload` も止める。`gh gist` と、git の送信系の命令（`send-pack`・`http-push`）、include や `.git/config` の書き込み、`refs/remotes` を書き換える操作も止める。push で見る差分は、作業場所の設定（`diff.relative` など）に左右されない下回りの `rev-list` と `diff-tree` で、送る commit のそれぞれが足した行にする。注釈つきタグの文面も照らす。
2. 「」『』の中の語句が、(1) 4 文字以上、(2) 除外表（状態の言葉の写し・商品名の写し・一般語の表）に無い、(3) 原文の置き場のどれかのファイルにそのまま現れる、の全部を満たすと exit 2 で止める。
3. 原本は `scripts/agent-hooks/confidential-quote-guard/`（guard.py・install.sh・rollback.sh・tests/）。原文・表の中身・語句は repo に入れない。表は Mac の社外秘フォルダ（`~/CC報告ファイル-keep/confid-guard/`）に置く。
4. 表が読めない・空、差分が取れない、本文の出どころが決まらないときは止める（全部拒否に倒す）。環境変数で飛ばす抜け道は作らない。誤って止まったときの直し方は、一般語の表に理由つきで足すことだけ（Opus 判断）。
5. 止めた記録は日時・見張りの名前・ファイル:行・件数だけ。語句は記録しない。
6. 見比べる相手（原文の置き場）は、本番の投稿原文（`ai_ro.public__source_messages` の `raw_text`、is_active に関係なく全行。2026-10-25 時点で 3,812 行・約 279 万字）だけにする（PO 決定「1」2026-10-25）。`fetch_corpus.py` が毎日 1 回、ADR-1024 の読み取り専用の道で、鍵付きフォルダに 1 ファイル（600）へ取り直す。正本は本番の記録 1 か所のまま。以前の 2 経路（R2-raw、check3）は外す。
7. 写しが 2 日より古ければ guard は止める（exit 2）。取り直しは LaunchAgent（毎日 06:30、install.sh が登録・rollback.sh が外す）。失敗時は前の写しを残して 0 以外で終わり、前回の半分未満に減ったときは置き換えず止める。週の点検（`weekly-check.sh`）で写しの日付と件数の増減を数える。

## Why（なぜ）

- 2026-10-25、設計書 PR で仕入元の投稿の文面の切れ端を「」で引用したまま `git push` し、公開リポジトリに出た（recon §1）。決まりは文書にあったが、照らす仕組みが無かった。
- 既存の秘密情報の検査（gitleaks）は鍵の「形」を見るもので、自社だけが持つ原文との照合はできない。原文は GitHub に置けないので、GitHub 側の CI では照合できない。送る前の Mac 側の見張りで止める。

## 受け入れるリスク

- 狙いは、AI がうっかり書き写したまま送ること。見張りを通らない手段（Edit／Write ツール、台本ファイル、PO の手作業）を使って意図して回り込む形は見分けない。

- 「」の外にそのまま書き写した文面は止められない（便2 で範囲を広げるか、K3 の数を見て決める）。
- main にすでにある書き写しに見える語句は書き換えない（足した行だけを見るので作業は止まらない）。
- GitHub に残った閉じた PR の中身は対象外（PO 判断「2」）。
- `gh api` で本文を付ける道と、取り込み操作に本文を付ける道は対象外（使うようになったら足す）。
- 誤って止まる（商品名・一般語）。商品名の写しが古いと新商品名で止まる。週の点検で取り直す。
- コミットの文面は照らさない（便2で検討）。コミットから本文が自動で付く `--fill` 系（`-f`・`--fill`・`--fill-first`・`--fill-verbose`）は照らせないので止める。
- 展開の止め方は命令の位置と git／gh の副命令で決める。命令の位置（代入・`env` などの後ろ、`;`・`&&`・`||`・`|`・`&`・改行・`(` の後ろ）の字句に `$`・バッククォート・glob（`?`・`*`・`[`）・行末の `\` があれば止める。命令が git のときは前置きの選択肢（`-C <値>`・`-c <値>`・`--git-dir` など）を飛ばし、副命令の字句に展開・引用の崩れ・glob があるか、前置きの値に展開があれば止める。gh は 1 つ目と 2 つ目の字句（`pr comment` など）に展開があれば止める。副命令が文字どおり読めて送らない種類（一覧の正は guard.py の `SAFE_SUBS`。主な例は commit・status・log・diff・add・show・fetch・merge・checkout・switch・stash・rebase・reset・pull・grep・rev-list・ls-remote など。`tag` は `-l`／`--list` つき、`config` は `--get*`／`--list` つきのときだけ）なら、後ろの引数の `$` は通す（`git -C <絶対パス> commit -m "$(cat <<'EOF' … EOF)"`、`git status | awk '{print $2}'`）。push・gh の本文・config や remote の書き込みの値に `$` かバッククォートがあれば止める。`$( … )`・バッククォートの中は、命令の位置が git・gh・`$…` なら同じ規則で調べる（`cat <<'EOF'` は通す。heredoc の本文は命令として読まないので、本文の「git push」では止まらない）。字句に分けられないとき（引用の閉じ忘れなど）は、`git`／`gh` と `$`・バッククォート・行末 `\` が同時にあれば止める。`sed -n` のように読むだけでも書き込み印に当たれば止まる（読むときは `cat` か `grep`）。`git config <key>`（`--get` なしの読み取り）も止まる。`[ -f x ]` も止まる。
- gh の群は pr／issue／release／repo の 4 つで、群の位置（gh のすぐ次の字句）にあるときだけ見る（値やパイプ先など別の位置の同じ語は見ない）。群のあとに `-R`／`--repo`（`--repo=…` も）があるときは、その印と値を飛ばして操作を読む（飛ばした先の操作の語に変数・展開があれば止める。`gh pr --help`／`-h` は通す。群だけで操作が無い形と、`-h`／`--help` 以外の `-` で始まる字句は止める）。`gist` は現れる位置を問わず止める。`gh alias set`／`import` は展開の検査で止める。`-R` の値が無い形は gh 自身が失敗する（実機で `gh pr -R comment 1` が `unknown command "1" for "gh pr"` で失敗することを確認）ので、受け入れる。（`gh pr -R o/r comment …` は gh の本文として照らし、`gh pr -R o/r view 1` は通す）。それ以外の `-` で始まる字句が群と操作のあいだにあれば、決まりの外として止める。sh／bash／zsh など shell の名前が命令の位置（解析器の単純な命令ごとの命令の語。改行・`env`／`command`・代入・`|&` の後ろも含む）にあり、`-c` が無いまま、`<<<`・`<<`・`|` のあと・`-s` のどれかで文字列を渡す形は、`-c` のときと同じく、命令全体から loose の目印（git と push、gh と本文の印）を探し、当たれば止める。理由の文は 2 つに分ける: 命令の位置の字句が git／gh 以外の展開・glob・`[` のときは「命令の名前に変数・展開・glob・[ は使えません。命令名を字で書くか、test を使ってください」、git／gh のときは従来の「git／gh の命令に変数や展開は使えません。値を書き出して単独で流してください」。
- `git grep push`・`git log --grep push`・`echo … push` のように、字句として git と push が並ぶ読むだけの命令も止まる。探すときは Grep ツールを使う。
- shell を呼ぶ命令と、本文に push の字を含む heredoc のコミットが同じ命令にあると、本文も照らす対象になるため止まる（例: `bash x.sh && git commit -F - <<'EOF' … push …`）。別々の命令で流す。
- `(( … ))` の中の `<<`、入れ子のバッククォート（`` `echo \`…\`` ``）、`git rebase -x` のように送らない下位命令に命令文を渡す形は、読み取り器が命令として読まないので照らさない（受け入れるリスク）。
- 「」が複数行にまたがる形と、半角の `｢｣` は照らさない（便2 で範囲を広げるときに扱う）。
- `gh alias set`・`gh alias import` は止める。gh は `gh alias list` を読み、呼ばれた 1 つ目の字句が別名の名前なら止める（gh に最初から入っている別名 `co` があるので「別名が 1 つでもあれば止める」にはしない。組み込みの命令は別名で上書きできない）。push には効かないので push では見ない。`git remote rename`・`git remote remove` も止める。origin に URL が複数あるときは `git remote get-url --push --all origin` のすべてを見て、表の repo が 1 つでもあれば照らす。`gh pr/issue close`・`reopen` の `--comment`／`-c` と、`new`（`create` と同じ扱い）も照らす。
- commit は heredoc か `-F <絶対パス>` で書ける。
- 決まった形以外の push と gh の本文は止まるので、作業の手間が増える（push は単独のコマンドで流す。本文は Write で作ったファイルを `--body-file <絶対パス>` で渡す）。
- 台本ファイル（`bash script.sh`）の中から push する場合は照らさない。`git rebase -x` や `git bisect run` のように送らない下位命令へ命令文や台本を渡す形も、台本を走らせる形として照らさない。
- 見張りを通らない手段（PO の手作業、見張りが読まない Edit／Write ツール、台本ファイルの中、別のプログラム）で書いた設定は見分けられない。具体的には、`alias`・`pushurl`・`pushInsteadOf`・`include`、追跡ブランチ（`refs/remotes`）を見張りの外で書き換えると、別名経由の push や、手で進めた追跡ブランチ分の差し引きを見分けられない。見張りを通る Bash で書き換える形と、`--local`／`--worktree` の設定に別名・pushurl・pushInsteadOf・include がある状態の決まった形の push は止める。global の `include` は止めない。
- `git notes` など、ここに挙げた以外の置き場は照らさない。
- `gh api` のほか、`gh workflow`・`gh label`・`gh project` など、今回の一覧に無い gh の操作は照らさない。
- 送る途中の commit に書き写しがあると、新しい commit で消しても止まる（履歴ごと送られるため）。直すには commit の書き直しか作り直しが要り、書き直しは Opus の指示を待つ。
- PO が手で（Claude を通さず）push する場合は照らさない。git の送信前フックには移せなかった（多くの worktree で `frontend/.husky/_` が無く、フックが走らない。recon §4-2）。
- `sh -c "…"`・`eval` の中の push や gh は、目印に当たれば止めるが、当たらなければ読めない。
- フックに渡された JSON が壊れているときは通す（全部の Bash を止めないため）。
- 環境変数 `CONFID_CORPUS_MAX_AGE_DAYS` は試験用で、写しの古さの上限を 2 日より短くする方向だけ効く（`min(環境変数, 2)`）。延ばす抜け道にはならない。
- 取り直し（`fetch_corpus.py`）は読み取りに失敗したら 2 分おいて最大 3 回まで試す（デプロイ中の約 70 秒の停止を越えるため）。ログは件数と日時だけ。

## 戻し方

PO が `!` で `rollback.sh` を流す。settings.json の登録 1 つと、毎日の取り直し（LaunchAgent）を外す。表・原文の写し・スクリプトは残してよい（登録が無ければ動かない）。

## 検証

design.md §4 の受入表。`tests/test_guard.py` が 1 行 1 試験、K1 は「#4727 の記録（79ec6fa76）が止まる」だけとする(PO 決定「1」2026-10-26)。#4729 の記録(f13e335fb)は、残る当たりが一般語の表に入れた 1 語だけ(審査合格の 18060e58f にも出る)で書き写しの証拠が残らないため、K1 から外した。根拠は実測の件数のみ(許可表なしで f13e335fb は1種類で止まるが、その語は一般語)。`tests/test_fetch.py` が取り直しの試験（本番には繋がない偽の読み取り口を使う）。
