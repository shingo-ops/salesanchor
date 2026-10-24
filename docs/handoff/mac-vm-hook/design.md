# design: AI が Mac で仮想マシンを作る命令を実行前に止める（mac-vm-hook）

この文書は何か(専門用語なしの1行): Claude が Mac で試験用の仮想マシンを作ろうとしたら、命令が動く前に止めて GitHub の試験場へ案内する見張りの設計。

親テーマ: [docs/specs/vm-test-on-gha/README.md](../../specs/vm-test-on-gha/README.md)（段階2）。段階1の設計: [../vm-test-on-gha/design.md](../vm-test-on-gha/design.md)
状態: 設計案作成済み・Opus 自己審査済み（§9）。KGI H1〜H6 は PO 承認済み（2026-10-17 チャット「y」）。実装は Sonnet に委任。

## 0. PO の願い（2026-10-17 チャット原文）
「hookで強制的に使えないようにしたい、出来る？検査をする場所はhookでgit hubと教えてローカルで通そうとしても技術的に防止させる」→ 設計着手に「y」。

## 1. KGI（○×で判定）
| # | 合格条件 | 測り方 | 合格ライン |
|---|---|---|---|
| H1 | AI が `colima start --profile x` を実行しようとすると止まる | Claude Code の Bash で実行させる | 実行前に拒否。案内文に `sandbox-test` が出る。前後の `colima list` が同じ |（vm-guard-allow: 見張りの説明文。実行する命令ではない）
| H2 | `limactl start foo`／`limactl create foo` も止まる | 同上（試験スクリプト） | 拒否（exit 2） |（vm-guard-allow: 見張りの説明文。実行する命令ではない）
| H3 | 開発用 DB の操作は今までどおり | `colima start`（profile 指定なし・`default`）／`colima stop`／`colima list`／`colima status` | 1件も止まらない。`colima start` 後に `default` が Running |
| H4 | 文章の中の文字列では止まらない | `echo`・`grep`・ヒアドキュメント本文・`git commit -m` に `colima start --profile x` を含める | 試験で 0 件拒否 |（vm-guard-allow: 見張りの説明文。実行する命令ではない）
| H5 | 例外は PO の許可券だけで、AI は自分で通せない | PO が `! bash scripts/permit-danger.sh "mac vm"` → 1回だけ通る。2回目は止まる。AI が券ファイルを作る操作は既存見張りで止まる | 3点とも期待どおり |
| H6 | 誤って止めることが無い | 導入後 7 日間、`~/.claude/logs/agent-events.jsonl` の `mac-vm-guard` 拒否記録を読む | 仮想マシン作成以外での拒否 0 件 |

## 2. 対象と対象外
- 対象（すべてリポジトリ外。py312-guard と同じ置き方）:
  - 新規 ~/.claude/scripts/mac-vm-guard.py（PreToolUse Bash フック、標準ライブラリのみ）
  - 新規 ~/.claude/scripts/tests/test_mac_vm_guard.py（H1〜H5 の試験。券は一時 HOME で作る）
  - 変更 ~/.claude/settings.json の PreToolUse Bash に1件追加（python-version-guard の直後）
- 対象（リポジトリ内・文書のみ）: docs/ops/runner-commands.md §10 に「AI は見張りで止まる・例外は許可券 "mac vm"」を2行追記。docs/specs/vm-test-on-gha/README.md に段階2の行。本 design.md・card.md・results.md。
- 対象外: 人が自分のターミナルで直接打つ命令（フックは AI の命令にだけ効く）／ Codex（Claude Code のフックは効かない。Codex 運用は現在カード実行のみで本件の観測事例なし）／ `default` の CPU・メモリ設定の変更／ 既存の `sa-private-ci` の起動（`--profile sa-private-ci` も止める対象。必要なら許可券）。

## 3. 止める形（判定の正本はこの表）
命令を引用符の外の `; && || |` 改行で分け、各部分の先頭語（`sudo`・`env`・`VAR=` は飛ばす。`/opt/homebrew/bin/colima` のような絶対パスは末尾名で見る）で判定する。
| 先頭語 | 次の語 | 判定 |
|---|---|---|
| `colima` | `start`・`create`・`restart` | profile（`-p`/`--profile`/`--profile=`/位置引数。値を取る旗は段階1の no-mac-vm-guard.sh と同じ一覧で飛ばす）が `default` 以外なら止める。無指定は `default`。環境変数 `COLIMA_PROFILE=` が付き `default` 以外でも止める |
| `limactl` | `start`・`create`・`clone` | 止める |
| `bash`/`sh`/`zsh` | `-c` | 引数の文字列を同じ規則で再判定（1段のみ） |
| その他（`echo`・`grep`・`git`・`cat` 等） | — | 止めない |
ヒアドキュメントの本文は判定前に取り除く（py312-guard の `strip_heredoc_bodies` と同じ）。

## 4. 止めたときの案内文（標準エラー、exit 2）
`🚫 BLOCKED [mac-vm-guard]: この Mac で試験用の仮想マシンは作れません（メモリ 8GB のため）。GitHub の試験場を使ってください: gh workflow run sandbox-test.yml --ref <ブランチ> -f test=<名前>（規則: docs/ops/runner-commands.md §10）。Mac 実機でしか試せない場合は PO に許可券 "mac vm" を依頼してください。`

## 5. 例外（許可券）
許可券置き場（リポジトリ外）の danger-permit-*.json のうち `op == "mac vm"`・`created_by == "manual"`・`expires_at` 未到来のものが1つあれば、それを削除して通す（1回限り）。発行は既存の scripts/permit-danger.sh（変更なし）。AI による券の作成は既存 agent-danger-hook.sh の「permits 自己発行ブロック」で止まる（同ファイル :156-170）。

## 6. 失敗時の扱い
内部エラー（JSON が読めない等）は通す（fail-open、py312-guard と同じ）。理由: 見張りの不具合で全 Bash が止まる被害の方が大きい。拒否・券消費・内部エラーは agent-events.jsonl に1行記録する（H6 の観測源）。

## 7. 代替案と選択理由
- A 採用: Claude Code の PreToolUse フック。原因（AI が作った 4GB の VM）に直接効き、既存の見張りと同じ置き方で保守が1か所。
- B 不採用: `colima` を包む同名スクリプトを PATH の前に置く。人の命令も止められるが、絶対パス `/opt/homebrew/bin/colima` で素通りし、Homebrew 更新・colima-idle-stop と干渉する恐れがある。
- C 不採用: colima 自体を削除。開発用 DB（default）が使えなくなる。

## 8. 外部・過去事例の参照と我々への応用
Claude Code 公式の hooks 仕様（PreToolUse・exit 2 で拒否し標準エラーを AI に返す）に従う。確認は実装時に Context7 か公式資料で行い results.md に出典を残す。同種の運用は本リポジトリ内の py312-guard（K1〜K7 合格、docs/handoff/py312-guard/results.md）が実績。社外の数値事例は本件の成否の根拠にならないため使わない。

## 9. Opus 自己審査（同一 AI による審査）
- 整合: 段階1（no-mac-vm-guard.sh、PR の追加行検査）と止める形を揃えた。規則の正本は runner-commands.md §10 の1か所のまま。
- 検証可能性: H1〜H5 は試験スクリプトと実機で○×、H6 はログで○×。
- リスク: 誤検知 → H4 の試験と H6 の7日観測。作業中の便D（PR #4404）が Mac で VM を作れなくなる → 想定どおり（sandbox-test へ）。
- 判定: APPROVE（KGI の PO 承認後に実装可）。

## 10. 維持の仕組み
- 守り手: PreToolUse フック mac-vm-guard（全 AI セッション・担当に自動適用）と CI の no-mac-vm-guard。点検は Opus（H6・K5）。
- 見張りは ~/.claude/scripts/（他の見張りと同じ場所。リポジトリ外）。試験は `python3 ~/.claude/scripts/tests/test_mac_vm_guard.py` で再実行できる。
- 戻し方: settings.json の1件を消す（または mac-vm-guard.py を退避）。
- K5（2026-10-31 `colima list`）で段階1・2をまとめて効果測定する。

## 11. 修正便 R1（H6 × への対応）
状態: 設計案作成済み・Opus 自己審査済み（§11-8）。PO は 2026-10-24 に「1（見張りを直す設計をつくる）」を選択。実装は PO の実装承認後に Sonnet へ委任。

### 11-1. 何が起きたか（観測事実。詳細は results.md「H6 7日観測」）
- 10/17〜10/24 の拒否 5件のうち 4件は `colima start 2>&1`／`colima start > file 2>&1` の形（profile 無指定＝§3 では default）で止まった。残り1件は記録が途中で切れているが、同じ形。
- 原因: `~/.claude/scripts/mac-vm-guard.py:81-103` の `colima_profile()` が、`-` で始まらない最初の語を位置引数の profile と読む。`2>&1`・`>`・リダイレクト先の語が profile 名になり、default 以外と判定される。再現: `/tmp/CC報告ファイル/mac-vm-hook/h6/fp-repro.txt`
- 設計との食い違い: §6 は「内部エラーも1行記録」と定めているが、`mac-vm-guard.py:180-181` と `:190-191` は記録せずに exit 0 で終わる。また `cmd_head` は先頭120文字で切られる（`:142`）ため、止めた命令を全文で検証できない。
- 同じ読み方は段階1の CI 検査 `scripts/ci/no-mac-vm-guard.sh:27-45` にもある（`2>&1` は `&` で切られて `2>` が残り、`>` もそのまま残る）。ただし 7日間に CI 側の誤検知は観測していない（未計測）。

### 11-2. KGI（○×で判定）
| # | 合格条件 | 測り方 | 合格ライン |
|---|---|---|---|
| R1-1 | default の起動はリダイレクト・背景実行・括弧付きでも止まらない | 試験に次の8件を足す: `colima start 2>&1 \| tail -5`／`colima start > /tmp/x.txt 2>&1; echo exit=$?`／`(colima start --cpu 2 --memory 4 --disk 20 > /tmp/x 2>&1)`／`colima start 2>/dev/null`／`colima start >> /tmp/x`／`colima start &> /tmp/x`／`colima start &`／`colima start < /dev/null` | 8件とも exit 0 |
| R1-2 | default 以外は、リダイレクトが前後にあっても止まる | 試験に次の5件を足す: `colima start -p foo 2>&1`／`colima start foo > /tmp/x`／`colima start > /tmp/x -p foo`／`colima start 2>&1 --profile=foo`／`COLIMA_PROFILE=foo colima start 2>&1`（vm-guard-allow: 見張りの試験の説明文。実行する命令ではない） | 5件とも exit 2 |
| R1-3 | 今までの試験が全部通る | `python3 ~/.claude/scripts/tests/test_mac_vm_guard.py` | 既存8件＋追加分すべて OK |
| R1-4 | 内部エラーが記録される | 試験: 一時 HOME で、壊れた JSON を標準入力に渡す | exit 0、かつ記録ファイルに `type: hook_internal_error` が1行 |
| R1-5 | 止めた記録で「どの部分が理由か」が分かる | 試験: `echo a; colima start -p foo 2>&1` を止める | 記録の `matched_part` が `colima start -p foo 2>&1`（300文字まで）（vm-guard-allow: 見張りの試験の説明文） |
| R1-6 | 入れ替えた後の7日間で誤って止めない（H6 の測り直し） | 入れ替え日から7日後に、§1 H6 と同じ手順で `hook_blocked` を全件判定 | §3 に当たらない拒否 0件、`hook_internal_error` 0件 |

### 11-3. 変更（対象は ~/.claude/scripts/ の2ファイルだけ。リポジトリ外・git 管理外）
1. 入れ替え前に退避: `cp ~/.claude/scripts/mac-vm-guard.py ~/.claude/scripts/mac-vm-guard.py.bak-r1`、`cp ~/.claude/scripts/tests/test_mac_vm_guard.py ~/.claude/scripts/tests/test_mac_vm_guard.py.bak-r1`
2. `mac-vm-guard.py` に関数 `drop_redirections(args)` を足す。`colima_profile()` の前で、次のものを語の並びから取り除く:
   - `^(\d+|&)?(>>?|>\||<<<|<>|<|>&|<&)(.*)$` に当たる語（例 `2>&1`・`>/tmp/x`・`&>`・`2>`）。後ろ（3番目の部分）が空のときは、次の1語（リダイレクト先）も取り除く。
   - 単独の `&`（背景実行）。
   - 部分の最後に付く閉じ括弧 `)`・`}`。語の末尾に付いている場合も外す。
3. `bad_part()`（`:111-117`）の colima の分かれ道で、`colima_profile(drop_redirections(args[1:]))` と呼ぶ。`args[0]` の判定（start/create/restart）も、末尾の `)` を外した語で行う。
4. 記録: `log_event()`（`:135-147`）に省略可の引数 `part` を足し、`matched_part` に止めた理由の部分を300文字まで入れる。`cmd_head` は今の120文字のまま（命令にほかの文字列が混ざっても記録が長くならないようにするため）。止めた部分を返すため、`bad_command()` は「止めた部分の文字列か None」を返す形に変える（呼び出し元は `main()` の1か所だけ）。
5. 内部エラー: `main()` の `except`（`:180-181`）と最外の `except`（`:190-191`）で `log_event('hook_internal_error', command か '', 例外の型名)` を呼んでから exit 0。`log_event` 自体の失敗は今までどおり黙る（fail-open は変えない）。
6. 試験 `test_mac_vm_guard.py` に R1-1・R1-2・R1-4・R1-5 の試験を足す。既存の試験は変えない。
- 触らない: 案内文（§4）、許可券（§5）、settings.json、`limactl` と `bash -c` の判定、ヒアドキュメントの処理、リポジトリ内のファイル。

### 11-4. 段階1 CI 側（`scripts/ci/no-mac-vm-guard.sh`）の扱い
同じ読み違いがあるが、R1 には入れない（一度に1つ変える）。R1-6 の合格後に、別の便 R2 として同じ規則（リダイレクトの語を取り除く）を CI 側に入れるか、PO に確認する。R2 はリポジトリ内の CI 検査の変更なので、別の PR になる。

### 11-5. 代替案
- A 採用: リダイレクトの語を取り除いてから profile を読む。§3 の表は変えずに、実装を §3 に寄せる。
- B 不採用: リダイレクトの語が出たら、そこで読むのをやめる。`colima start > x -p foo` のように後ろに profile がある形を見逃す（bash ではリダイレクトはどこに置いてもよい）。
- C 不採用: 位置引数の profile を読まない（`-p`/`--profile` だけ見る）。`colima start foo` を見逃し、§3 から外れる。

### 11-6. リスクと対処
- 取り除きすぎて、止めるべき命令を見逃す → R1-2 の5件で確かめる。
- 見張りの書き換えに失敗して全 Bash が止まる → fail-open は変えない。入れ替え直後に `echo ok` と R1-3 を実行して確かめる。
- 記録が増える → 1回の拒否につき1行のままで、`matched_part` は300文字まで。

### 11-7. 戻し方・測り方
- 戻し方: `.bak-r1` の2ファイルを元の名前に戻す（settings.json の変更は無い）。
- 測り方: R1-1〜R1-5 は入れ替え当日に試験で測る。R1-6 は入れ替え日から7日後に予約して測る。基準値は今回の H6（5件中4件が誤検知、1件は疑い。内部エラーは計測不能）。

### 11-8. Opus 自己審査（同一 AI による審査）
- 整合: §3 の表（profile 無指定は default）に実装を合わせる変更で、§3 自体は変えない。§6 の記録義務の入れ忘れを埋める。
- 根拠: 原因は `mac-vm-guard.py:81-103` と再現試験 `fp-repro.txt` で確かめた。shlex は `2>&1` を1語のまま返す。これは再現試験の結果（rc=2）と合う。
- 検証可能性: R1-1〜R1-5 は試験で○×、R1-6 は記録で○×。
- 範囲: リポジトリ外の2ファイルだけ。外から入るものはなく（標準ライブラリのみ）、フックの出入り（exit 0/2・標準エラー）も変えないので、Claude Code の hooks 仕様の新しい確認は要らない。
- 未解決: R2（CI 側）をやるかどうかは PO の判断。R1 の実装可否には影響しない。
- 判定: APPROVE（PO の実装承認後に実装可）。
