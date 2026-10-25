# Opus 審査記録: 段階1 便1（クラウドでだけ動く見張り）

- 審査者: Reviewer エージェント（Opus・新規起動）
- 日付: 2026-10-23
- 対象: PR #4666 / ブランチ `release/cloud-parity-design` / 審査時 HEAD f7142b60f55bc3201708f4eb20b42ae932b8ab64
- 判定: **REQUEST_CHANGES**（直すべき点 1 件。ほかは指摘のみ）

## テスト結果（生出力）
- `bash scripts/agent-hooks/cloud/test.sh`: /tmp/CC報告ファイル/cloud-parity-bin1/review-test.txt（終了コード 0、「全件OK」、K6 34件中逸脱0件、K7 1秒以上 17件・負荷 24.0）
- 審査役の追加試験（止め漏れ・止めすぎ）: /tmp/CC報告ファイル/cloud-parity-bin1/review-probe.txt

## 根拠（確認したこと）
1. 手元で動かない（K6）: `scripts/agent-hooks/cloud/dispatch.sh:2` が先頭で `CLAUDE_CODE_REMOTE` が `true` 以外なら exit 0。test.sh の K6 で 34件すべて exit 0・出力なし。
2. `.claude/settings.json`: JSON として読める。重複キーなし。差分の削除行 0。既存の SessionStart 3件・SubagentStop・TeammateIdle・PreToolUse(SubagentHandback) はそのままで、SessionStart に1件、PreToolUse に2件（Bash / `mcp__github__.*`）、Stop を新設。最上位のキー順も main と同じ。
3. 秘密: 差分にトークン形式・Webhook URL・鍵の並びは無い（grep で 0 件）。`danger_ops.json` は危険語 17 件の文字列配列のみ。`sync_danger_ops.py:15` は正本から `danger_ops` だけを取り出し、他のキーは出力しない。正本ファイルの中身は審査役は読んでいない。
4. 社外秘: docs/handoff/cloud-parity/ の 4 文書と rules.md に仕入元名は見当たらない。
5. K1・K2・K4・K5 は test.sh の各ケースで期待どおり（止める／通す）。

## 指摘

### 直すべき点（REQUEST_CHANGES の理由）
- **K3 の止め漏れ: PR の head ではなく手元の HEAD を見ている**
  `scripts/agent-hooks/cloud/guard_pre_tool.py:152-159`（`changed_files` が常に `origin/main...HEAD`）と `:219`。
  `mcp__github__create_pull_request` は `tool_input.head` で任意の枝を指定でき、`gh pr create --head <枝>` も同じ。手元の HEAD が docs だけ（または main と同じ）なら、コードを含む別の枝の PR が通る。
  再現（review-probe.txt）: HEAD に差分の無い場所で、head=別のコード枝・本文に節あり → exit 0（2 が期待）。
  recon §3 のとおりクラウドの PR 作成は MCP が主な道で、MCP の push_files 等で手元を切り替えずに枝を作れるため、現実に起きうる。
  直し方の例: MCP は `tool_input.head`、gh は `--head` の値があればその枝（`origin/<head>`）を比べる。取れなければ止める（fail-closed）。test.sh に「head が別のコード枝」のケースを足す。

### 指摘のみ（今回は止めない。別カードでよい）
- K1 の止め漏れ（手元の agent-danger-hook と同じ作りの持ち込み。手元より弱くはなっていない）: `guard_pre_tool.py:70` の区切りに単独の `&` が無く、`:55-65` は `<(`／`>(` を見ないため、`cat a & <危険操作>` や `cat <(<危険操作>)` が読み取り扱いで消され通る。並べ替えた書き方（例: `rm` の `-fr`）も一覧に無いので通る。
- K2 の止め漏れ: `curl` での merge API、`gh api graphql` の mergePullRequest は止まらない。現状クラウドの `gh` は無効（recon §3）なので影響は小さい。MCP の `push_files` 等による main への直接書込は見張り対象外（Branch Protection 頼み）。
- 止めすぎ: 命令文に `truncate` の語があるだけで止まる（例: `python3 -c` の中身）。`ssh-keygen -f prod_key.pub` が「本番への ssh」で止まる（`guard_pre_tool.py:117`、`\bssh\b` が `ssh-keygen` に当たる）。普通の `git log`／`git diff`／`git commit -m`／`gh pr list`／`pytest` は通ることを確認済み。
- `dispatch.sh:8-12` は入力 JSON が壊れていると EVENT が空になり exit 0（通す）。`guard_pre_tool.py:200` の fail-closed は dispatch 経由では届かない。
- 一覧の語の直書き: `guard_pre_tool.py:93` の正規表現に一覧の語が1つ、design.md の K1 行に5つ含まれる（card-1 §1-2(a) の「直接書かない」と食い違い。害は無い）。
- K7: 負荷 24.0 の機械で 17 件が 1 秒以上。参考値。クラウドでの実測で確かめる。

## 再審査（2026-10-23・HEAD beceecd3c）

- 審査者: Reviewer エージェント（Opus・新規起動）
- 対象: PR #4666 / 審査時 HEAD beceecd3c833dc9f8f8e6decea9b5f2693c4b6ac（前回 23c146ec6 からの差分は dispatch.sh・guard_pre_tool.py・test.sh の3件）
- 判定: **REQUEST_CHANGES**（直すべき点 1 件）

### テスト結果（生出力）
- `bash scripts/agent-hooks/cloud/test.sh`: /tmp/CC報告ファイル/cloud-parity-bin1/review2-test.txt（終了コード 0、「全件OK」、K6 50件中逸脱0件、K7 1秒以上 0件・負荷 26.1）
- 審査役の追加試験: /tmp/CC報告ファイル/cloud-parity-bin1/review2-probe.txt

### 確認できたこと
1. K3 の作成元の取り方: MCP は `tool_input.head`（無い・空・文字列でない → 止める）、gh は `--head`／`-H`、gh api は `-f/-F/--field/--raw-field head=`。`owner:` は外して枝名だけにし、`_BRANCH_OK`（`guard_pre_tool.py:175`、先頭に `-` 不可・空白や `;` 不可）で不正なら止める。`-x`・`--upload-pack=x`・`o:-x`・`a;b`・数値・`a..b`・存在しない枝はすべて止まった（probe）。fetch の引数は検査済みの枝名だけで、`-` 始まりは通らない。
2. fetch は `git fetch -q origin <枝>` のみ。作業ツリー・現在の枝・未保存ファイルは変わらない（probe: fetch 後も `## main...origin/main`・`?? WIP.txt` のまま）。
3. 単独 `&`（`guard_pre_tool.py:70,73`）、`<(`（`:57`）、`ssh-keygen` の誤検知（`:117`）、`dispatch.sh:12,15-18` の壊れた JSON で止める、はいずれも test.sh と probe で期待どおり。`ls 2>&1 | head`・`sleep 0 & wait`・`git status` は通る。配列 JSON・空入力も dispatch で止まる。
4. 手元（`CLAUDE_CODE_REMOTE` 未設定）: `dispatch.sh:2` で先に exit 0。test.sh K6 50件・probe（壊れた JSON、K3 の不正 head）とも exit 0・出力なし。
5. 秘密・社外秘: 今回の差分にトークン形式・Webhook URL・鍵の並びは 0 件。追加は scripts の3件のみで文書の追加なし。test.sh の宛先は `t@example.invalid`。

### 直すべき点（REQUEST_CHANGES の理由）
- **K3 の止め漏れ: 手元に古い `origin/<枝>` があると fetch せずにそれを見る**
  `scripts/agent-hooks/cloud/guard_pre_tool.py:166-172`。fetch は「最初の diff が失敗したとき」だけで、手元に追跡参照があれば古いままの中身で判定する。
  再現（review2-probe.txt 1行目）: docs だけの枝を手元に取り込んだ後、リモートだけでその枝にコード（src/late.py）を足す → MCP head=その枝・本文に節あり → exit 0（2 が期待）。
  前回指摘の理由そのもの（MCP の push_files 等は手元の追跡参照を更新しない）と同じ道で起きる。最初に docs を git push してから MCP でコードを足す流れで通る。
  直し方の例: 判定の前に必ず fetch し、fetch が失敗したら止める（fail-closed）。fetch は `+refs/heads/<枝>:refs/remotes/origin/<枝>` のように取り込み先を明示するか、`FETCH_HEAD` と比べる（clone の fetch 設定に依存しない）。test.sh に「手元の追跡参照が古い」ケースを足す。

### 指摘のみ（今回は止めない）
- gh の作成元の取り方の漏れ（クラウドの gh は無効なので影響は小さい）: `gh api ... -fhead=<枝>`（詰め書き）は取れず手元の HEAD で判定される。`gh pr create --head A --head B` は最初の A で判定されるが gh は最後の B を使う（`guard_pre_tool.py:186-187`）。
- `owner:枝` の owner を見ていない（`:191-192`）。別 owner（fork）の同名枝でも手元の origin で判定する。
- `>(` は `<(` と違い読み取り扱いの除外条件に無い（`:57`）。今回の probe（`tee >(…)`）は止まったが、`tee` が一覧外だったため。

## 再々審査（2026-10-23・HEAD f71baa18c）

- 審査者: Reviewer エージェント（Opus・新規起動）
- 対象: PR #4666 / 審査時 HEAD f71baa18c148214614052dad11bd0bd2728fa3ba（前回 beceecd3c からのコード差分は guard_pre_tool.py・test.sh の2件）
- 判定: **APPROVE**（直すべき点 0 件。指摘のみ 2 件）

### テスト結果（生出力）
- `bash scripts/agent-hooks/cloud/test.sh`: /tmp/CC報告ファイル/cloud-parity-bin1/review3-test.txt（終了コード 0、「全件OK」、K6 54件中逸脱0件、K7 1秒以上 0件・負荷 24.3）
- 審査役の追加試験: /tmp/CC報告ファイル/cloud-parity-bin1/review3-probe.txt

### 確認できたこと
1. 前回の直すべき点（古い追跡参照で判定する K3 の漏れ）は直っている。`guard_pre_tool.py:166-174` で head があれば判定の前に毎回 `git fetch -q origin +refs/heads/main:refs/remotes/origin/main +refs/heads/<枝>:refs/remotes/origin/<枝>` を行い、取り込み先を明示している。fetch が失敗したら RuntimeError → `check_pr_create`（`:222-225`）で止める（fail-closed）。
   - 再現（probe 1）: 使い捨ての bare リポジトリで docs だけの枝を取り込んだ後、別 clone からその枝に src/late.py を push → MCP head=その枝・本文に節あり → exit 2（src/late.py を理由に止まる）。取り込み後の `origin/docsonly` はリモートの sha と一致。
   - fetch 設定が main だけの single-branch clone でも同じく止まり、`origin/<枝>` が作られる（probe 2）。docs だけの未取り込み枝は通る（probe 3）。origin 不通は止まる（probe 4）。`a..b`・`x.lock` は refspec 不正で止まる（probe 6, 7）。
2. 取り込みは作業ツリー・現在の枝・未保存ファイルを変えない（probe 1: 前後とも `## main...origin/main` / ` M README.md` / `?? WIP.txt`、HEAD 同一）。手元（`CLAUDE_CODE_REMOTE` 未設定）は `dispatch.sh:2` で先に exit 0 し、取り込みも走らない（probe 17: `origin/docs3` が作られていない）。test.sh K6 54件も逸脱 0。
3. gh の head の取り方（`:188-194`）: 複数指定は最後を使う（probe 13, 14 と test.sh「--head 2回」）、`-fhead=` の詰め書きも取れる（test.sh）。`>(` は読み取り扱いから外れた（`:57`、test.sh「>( の中に危険語」で止まる。危険語なしの `cat >(head -1)` は通る＝probe 15）。
4. 秘密・社外秘: 今回の差分にトークン形式・Webhook URL・鍵・URL は 0 件。仕入元名なし。test.sh の宛先は `t@example.invalid`。

### 直すべき点（REQUEST_CHANGES の理由）
- なし

### 指摘のみ（今回は止めない）
- 「最後の指定を使う」変更で gh の道に新しい止め漏れが出た（前回までは止まっていた）。`:188-190` の正規表現は命令文全体を見るため、実際の `--head` より後ろにある本文中の `-H <枝>`／`--head <枝>`、または gh api の末尾のヘッダ `-H 'X-A:<枝>'` が「最後の指定」になる。再現（probe 8, 9, 10）: 実際の head はコード枝、本文や末尾ヘッダに docs だけの枝名 → exit 0（2 が期待）。クラウドの gh は無効（recon.md:24）で、PR 作成は MCP の道（今回直った）を通るため影響は小さい。直すなら本文・ヘッダの値を引数として読み飛ばす（shlex で分けて、`--body`/`-b`/`-H`(gh api) の次の語を除く）。
- 止めすぎ: gh api で `-H 'Accept: …'` を `-f head=` より後ろに書くと、枝名が空と読まれて止まる（probe 12）。前に書けば通る（probe 11）。

## 本線取り込み後の確認（2026-10-23・HEAD 6a44570e0）

- 審査者: Opus（審査役・新規起動）
- 対象: merge commit 6a44570e09bbf8090ea53ebf9b2d5388c172f1ed（本線 33294fe9a の取り込み。親は bc0a2e241 と 33294fe9a）
- 判定: APPROVE（取り込みで PR の中身は変わっていない）
- 確認したこと:
  - `git diff origin/main...HEAD --name-only` は承認時と同じ13件（.claude/settings.json、scripts/agent-hooks/cloud/ 8件、docs/handoff/cloud-parity/ 4件）
  - `git diff bc0a2e241 HEAD -- <13件>` は空（.claude/settings.json を含め差分なし）
  - 取り込みで入った本線側の変更は4件（ADR-1032 追記、doc-agenda-nav カード、master-register-rules-guard.py の正規表現、その試験）。scripts/agent-hooks/cloud/ と .claude/settings.json はこれらを参照していない（grep 0件）。cloud/dispatch.sh が呼ぶのは同じ階層の guard_pre_tool.py・guard_stop.py・session_start.py のみ
- テスト結果: `/tmp/CC報告ファイル/cloud-parity-bin1/review4-test.txt`（全件OK・終了コード0）。差分の生出力: `/tmp/CC報告ファイル/cloud-parity-bin1/review4-diff.txt`

## 別カード 指摘1・2 の対処（PR #4728）

- 直したこと: `guard_pre_tool.py` の `head_branch` の Bash の道を、命令文全体への正規表現から、`shlex` で語に分けて `gh pr create` / `gh api` の引数として読む方式に変えた。本文・ヘッダなど「値を取る選択肢」の値は作成元として読まない（止め漏れ＝指摘1 を解消）。
- 直したこと: gh api の `-H`/`--header` は値ごと読み飛ばすので、`-H 'Accept: …'` が `-f head=` より後ろにあっても枝名と誤読されない（止めすぎ＝指摘2 を解消）。引用符が閉じていない命令は止める側に倒す。
- 試験: `scripts/agent-hooks/cloud/test.sh` に H1〜H5 を追加（H1 本文中の -H／H2 本文中の --head／H3 末尾ヘッダ／H4 Accept ヘッダが後ろ／H5 引用符未閉）。H6 は既存ケースが同じ結果であること。
- 追補 R1 の対処（2026-10-25）: shlex は語の途中の # 以降を捨てるため、`_midword_hash` を足し、引用符の外で語の途中に # がある命令は ValueError（止める側）にした。試験 H7〜H10 を追加。
- 追補 R2 の対処（2026-10-25）: `_midword_hash` が語の頭の # を行末まで読み飛ばす（コメント内の引用符で誤読しない）。行の継ぎ目（\ の次が改行）の直後の # と、引用符の外の `$'` は True（止める側）。試験 H11〜H15 を追加。
- 追補 R3 の対処（2026-10-25）: `_midword_hash` の語の頭の判定を、直前の文字ではなく「区切り直後か」の旗（`\` で逃がした文字・閉じ引用符の直後は語の途中）に変更。`\r` は区切りにせず、命令文に `\r` があれば `_bash_head` が止める。H5 を shlex の道の試験に戻し、H16〜H19 を追加。
- 追補 R4 の対処（2026-10-25）: 「読める形だけ読み、それ以外は止める」に寄せた。`_bash_head` は heredoc 本文を取り除かず命令文そのものを読み、引用符・逃がし・コメントの外に区切り（`&&` `||` `;` `|` `&` `|&`）以外の記号の並び（`;(` `(` `)` `<<` `<<<` `<` `>` など）があれば止める（`_check_symbols`）。命令文の中の `gh pr create` と `gh api` の出現数が1つでない、または shlex で見つけた作成の命令の数と合わなければ止める。試験 H20〜H26 を追加。
- 追補 R5 の対処（2026-10-25）: 書き方を1つずつ追う方式（R4 の記号の並び・出現数の検査）をやめ、PR 作成と判定された Bash の命令は「gh だけの1行」しか読まない方針に切り替えた（`_check_simple`）。引用符の外は英数字・空白・`_-./:=,@+%^` だけ、単引用符の中は自由、二重引用符の中は `$` バッククォート `\` があれば止め、先頭が `gh pr create` / `gh api` でなければ止める。理由: 変数・置き換え・`bash -c`・逃がした記号などで本物を隠し、見える囮の docs 枝を置く形を書き方ごとに追いきれないため（クラウドの gh は無効で PR 作成は MCP が主、止めすぎの害は小さい）。`_check_symbols` と出現数の検査は削除。期待を通る→止まるに変えた既存ケース: H9・H15・H19。試験 H27〜H32 を追加。

## 別カード 指摘3 の対処（PR #<番号>）

- 直したこと: `guard_pre_tool.py` の `check_merge`（Bash の道）に、既存3条件の後ろへ「送る道具（gh api・curl・wget・httpie）がある命令で、`/pulls/<n>/merge` への PUT、`mergePullRequest` / `enablePullRequestAutoMerge`（GraphQL）、`repos/…/merges`（枝の直接まとめ）のどれかがあれば止める」条件を足した。
- 直したこと: 送る道具の無い命令（grep など）と、PUT 指定の無い `…/merge` の読み取り、GraphQL の読取り（query）は止めない。
- 試験: `scripts/agent-hooks/cloud/test.sh` に M1〜M8 を追加（M1 curl PUT／M2 curl --request=PUT／M3 GraphQL マージ／M4 GraphQL 自動マージ予約／M5 …/merges／M6 curl GET／M7 grep／M8 GraphQL 読取）。M9 は既存ケースの結果が変わらないこと（B8 の時間試験は負荷で変更前から NG）。
