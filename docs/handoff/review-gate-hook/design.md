# design — マージ前の Opus 審査をフックで強制する

- 状態: 設計審査済み（architect APPROVE 第5回 2026-10-18、/tmp/CC報告ファイル/review-gate-hook/arch-review-5.md）。第5版（KGI R1〜R7 は PO「y」2026-10-18。architect REVISE 第1回の指摘 1〜11・第2回の指摘 1〜8 を反映）
- 関連: [recon.md](recon.md)・[ADR-1029](../../adr/ADR-1029-review-gate-hook.md)・ADR-1011（フックは AI がパッチ、PO が `!` で反映）・ADR-1003・ADR-136
- PO 原文（2026-10-18）: 「これをhookで矯正してくれ、工程を飛ばすことなくopusに審査を依頼すること」

## 1. あるべき姿

AI（Opus でも Sonnet でも）が PR をマージしようとしたとき、その PR の「今の HEAD」に Opus の審査役（reviewer）の APPROVE が無ければ、フックが止める。審査を飛ばすことが仕組みとしてできない。

## 2. KGI（PO 承認済み）

| # | 成功条件（○×） |
|---|---|
| R1 | APPROVE の無い PR をマージしようとすると止まり、「Opus の審査役を起動してください」と出る |
| R2 | 今の HEAD に APPROVE があればマージは通る |
| R3 | APPROVE の後に HEAD が変わると、また止まる |
| R4 | REQUEST_CHANGES・REJECT のときは記録されず、止まったまま |
| R5 | 審査役を Opus 以外の model で起動しようとすると止まる |
| R6 | AI が記録の置き場に直接書こうとすると止まる（Bash・Write/Edit の両方） |
| R7 | 試験の台本がリポジトリにあり、フックを変えたら毎回流せる（CI で自動実行） |

対象外: GitHub の Branch Protection・Ruleset は変えない。GitHub 画面からのマージと Actions の自動マージ（台帳 DONE 化）はフックの外。

## 3. KPI

- K-a: 導入後、AI のマージ操作のうち記録なしで通った件数 = 0（gate の log で数える）
- K-b: 導入後の誤った止め（APPROVE 済みなのに止まった）件数。0 でなければ原因を記録して直す

## 4. recon（要点。詳細は recon.md）

- 審査役は SubagentHandback で報告を返す。公式は「報告は PreToolUse/PostToolUse を SubagentHandback に当てて `tool_input.message` で読む」「会話記録は遅れて書かれることがある」とする（recon.md §1）。→ 記録の起点は PostToolUse の SubagentHandback。
- 報告本文に VERDICT 行が無い（recon.md §2）。→ reviewer.md に決まった最後の行を足す。
- マージの入口（recon.md §3）。gh-pr-merge-safe.sh は引数 `--merge` だけで、PR 番号は worktree 直下の `.pr-number` から読む（scripts/gh-pr-merge-safe.sh:35-36,52,88）。check-pr-merge-ready.py は引数 2 個固定で、確認だけのモードは無い（:153,195-198）。

## 5. design

### 5-1. 置くもの（リポジトリ。PR で審査する）

| ファイル | 役割 |
|---|---|
| scripts/agent-hooks/review-gate/record.py | PostToolUse（matcher `SubagentHandback`）。審査結果を記録する |
| scripts/agent-hooks/review-gate/gate.py | PreToolUse（matcher `Bash\|Write\|Edit\|MultiEdit\|NotebookEdit\|Agent`）。関所 |
| scripts/agent-hooks/review-gate/test_review_gate.sh | 試験。偽の gh・偽の meta.json・偽の入力 JSON で §8 の全行を確かめる |
| scripts/agent-hooks/review-gate/reviewer-verdict-rule.md | 審査役の最後の行の決まり（5-4 の文）。reviewer.md 2 か所の元 |
| scripts/agent-hooks/review-gate/install.sh | PO が `!` で実行（5-5） |
| scripts/agent-hooks/review-gate/rollback.sh | PO が `!` で実行（5-5） |
| .github/workflows/agent-hooks-test.yml | test_review_gate.sh を流す。`on.pull_request` は branches 指定なし、paths は `scripts/agent-hooks/**`・`.github/workflows/agent-hooks-test.yml`・`.claude/agents/reviewer.md`（既存 hook-test.yml の `branches: [develop]` は写さない） |
| .claude/agents/reviewer.md | Outputs 節に 5-4 の文を足す |

両スクリプトとも Python 3 標準ライブラリだけを使う。止めるときは理由を stderr に出して exit 2（recon.md §1・§4）。記録の置き場は環境変数 `REVIEW_GATE_DIR`（既定 `~/.claude/review-gate`）、gh は環境変数 `REVIEW_GATE_GH`（既定は PATH の gh、無ければ /opt/homebrew/bin/gh）。どちらもフックを起動する Claude の環境から来るので、AI の Bash からは変えられない。

### 5-2. record.py（記録する側）

1. stdin の JSON から `tool_name`・`agent_type`・`agent_id`・`tool_input.message`・`transcript_path`・`cwd` を読む。`tool_name != "SubagentHandback"` か `agent_type != "reviewer"` なら何もせず exit 0（本流の会話には agent_type が無いので当たらない）。
2. model の確認:
   - `id` = `agent_id` の頭に `agent-` があれば外したもの。
   - meta.json の場所は transcript_path の形で 2 通り（サブエージェントの中の PostToolUse で transcript_path がどちらを指すかは未確認のため）:
     - transcript_path のファイル名が `agent-*.jsonl` で親ディレクトリが `subagents`: 同じディレクトリの agent-<id>.meta.json。
     - それ以外（本流の記録）: transcript_path の `.jsonl` を除いたディレクトリ + /subagents/agent-<id>.meta.json。
   - `agentType == "reviewer"` かつ `model` に `opus` を含むこと。見つからない・違う → 記録しない。
   - meta.json と同じディレクトリの `agent-<id>.jsonl`（`<id>` は上で `agent-` を外したもの）があれば、その中の assistant の `message.model` が全部 `claude-opus` で始まること（1 件でも違えば記録しない。ファイルが無い・assistant 0 件は遅れのため可）。
3. `tool_input.message` の中で、正規表現 `^VERDICT: (APPROVE|REQUEST_CHANGES|REJECT) on ([0-9a-f]{40}) PR #(\d+)\s*$`（複数行モード）に当たる最後の 1 件を取る。無ければ記録しない。
4. `APPROVE` 以外なら記録しない（R4）。
5. `gh pr view <N> --json headRefOid,url` を `cwd` で実行し、headRefOid が VERDICT の sha と完全一致するときだけ記録する。`owner/repo` は常に url（`https://github.com/<owner>/<repo>/pull/<N>`）から作る。
6. 記録先: $REVIEW_GATE_DIR/records/<owner>__<repo>-<N>-<sha>.json。中身: pr・repo・head・verdict・agent_id・meta_model・recorded_at（UTC ISO8601）。ディレクトリ 700、ファイル 600。
7. 結果（記録した／しなかった理由）を `$REVIEW_GATE_DIR/log.jsonl` に 1 行足す。審査役の報告を妨げないため、常に exit 0。

### 5-3. gate.py（関所）

stdin の JSON の `tool_name` で分ける。

**(a) 記録の置き場と記録台本を守る（R6）**
- Write/Edit/MultiEdit: `tool_input.file_path`、NotebookEdit: `tool_input.notebook_path` を `~` 展開・絶対化（`cwd` 基準）して、`$REVIEW_GATE_DIR` の下なら止める。
- Bash: 5-3(c) の区切りごとに、次のどれかを含めば止める（読むだけでも止める。ヒアドキュメントの本文も対象）: `.claude/review-gate`・`review-gate/records`・`review-gate/log`・review-gate/record.py・`.claude/scripts/review-gate`・`REVIEW_GATE_DIR`・`REVIEW_GATE_GH`・`$REVIEW_GATE_DIR` の実パス。
- 例外: 区切りの先頭が `bash scripts/agent-hooks/review-gate/test_review_gate.sh` の区切りだけは通す（例外はその区切りにだけ効く。同じ command の他の区切りは検査する）。試験は自分の一時ディレクトリを使う。
- 記録台本 record.py を AI が直接呼んで偽の記録を作る道は、これで塞ぐ（`scripts/agent-hooks/review-gate/record.py` は review-gate/record.py を含む）。

**(b) 審査役の model（R5）**
- Agent: `subagent_type == "reviewer"` で、`model` が指定されていて `opus` を含まなければ止める。未指定は reviewer.md の `model: opus` が使われるので通す。

**(c) マージの関所（R1〜R3）**
- 前処理: ヒアドキュメント（`<<TAG`・`<<'TAG'`・`<<"TAG"`・`<<-TAG` の次の行から TAG だけの行まで）の本文を、shlex にかける前に取り除く（(a) の文字検査は取り除く前の全文にもかける）。
- 区切り: `sh = shlex.shlex(command, posix=True, punctuation_chars=';&|()<>\n')`、`sh.whitespace = ' \t\r'`、`sh.whitespace_split = True` で語に分ける（既定の `punctuation_chars=True` は改行を捨てるので使わない）。`;`・`&`・`|`・改行の文字だけでできた語を区切りとする。引用の中の改行は区切らない。shlex が失敗したら（引用符の閉じ忘れ等）その command は止める。
- 区切りごとに、先頭の `(`・`{`・`!`・`then`・`do`・`else`・`elif`・`env`・`command`・`exec`・`time`・`nohup`・`VAR=値` の語を飛ばし、残った最初の語を basename で比べる（`/opt/homebrew/bin/gh` は gh）。先頭が `cd <dir>` の区切りは、その後の区切りの作業場所を `<dir>`（`~` を展開してから `cwd` 基準で絶対化）とする。
- 入れ子（同じ判定 (a)・(c) に入れ直す。入れ直せなければ止める。`eval` は受け入れるリスク）:
  1. 区切りの先頭が `bash`・`sh`・`zsh` で `-c <文>` があれば `<文>`。
  2. コマンドの文字列（区切り語に引用符が付いたヒアドキュメント `<<'TAG'`・`<<"TAG"` の本文は bash が展開しないただの文字なので取り除いた後、引用符なし `<<TAG` の本文は残した文字列）から、`$(` から対応する `)` まで（かっこの深さを数える）と、対になったバッククォートの間を取り出す。shlex の語には頼らない（引用の外の `$(...)` は複数の語に分かれるため）。対にならなければ止める。
  3. ヒアドキュメントを受ける区切りの先頭が `bash`・`sh`・`zsh`・`python`・`python3` なら、その本文。
  4. 区切りの先頭が `bash`・`sh`・`zsh` で `-c` もスクリプトファイルの引数も無い（標準入力から読む）とき、またはパイプの後ろの区切りがそれのとき: 中身が分からないので、コマンドの全文に `merge` を含めば止める。
- 関所にかける形（shlex の語で判定する。引用の中は 1 語になるので、文字を含むだけの `grep -rn "gh pr merge"`・`git commit -m "..."`・`gh pr create --body "..."` は当たらない。`timeout`・`xargs`・`sudo`・`caffeinate` などの前置きがあっても当たるよう、先頭の語には頼らない）:
  1. 区切りの中のどこかに、basename が `gh` の語・`pr`・`merge` の 3 語がこの順に続く。同じ区切りに、旗の値の位置ではない値なしの `--disable-auto`（`--disable-auto=…` は数えない）があれば通す。
  2. 区切りの中に basename が `scripts/gh-pr-merge-safe.sh` の語がある。
  3. 区切りの中に basename が `scripts/dev/check-pr-merge-ready.py` の語がある。
  4. 区切りの中に basename が `gh` の語・`api` が続き、区切りの語に `/merge`・`mergePullRequest`・`enablePullRequestAutoMerge` のどれかを含む。
  5. 区切りの中に basename が `curl` の語があり、区切りの語に `api.github.com` と `/merge` を含む。
  - 2・3 の例外: 区切りの先頭の語（5-3(c) の飛ばし一覧を飛ばした後）が、読むだけの道具 `grep`・`rg`・`cat`・`head`・`tail`・`sed`・`awk`・`less`・`wc`・`ls`・`git`・`diff`・`stat`・`file`・`shellcheck` のときは当てない。それ以外（`bash`・`python3`・`timeout`・直接実行など）は当てる。
- PR 番号:
  - 形1: `merge` の後ろで、`-` で始まらず値を取る旗（`--repo/-R`・`--match-head-commit`・`--subject/-t`・`--body/-b`・`--body-file/-F`・`--author-email/-A`）の値でもない最初の語が `#?\d+`。URL `.../pull/<N>` 形も可。
  - 形2: 作業場所で `git rev-parse --show-toplevel` を取り、その直下の `.pr-number` の中身（空白を除いて数字だけ）。
  - 形3: `scripts/dev/check-pr-merge-ready.py` の後ろの最初の語が `\d+`。
  - 形4・5: `pulls/(\d+)/merge`。GraphQL（番号が取れない）は止める。
  - 番号が取れなければ止める（「PR 番号を明示してください」）。
- HEAD の確認: `gh pr view <N> --json headRefOid,url`（`--repo/-R` があれば渡す）を作業場所で実行。失敗したら止める（fail closed）。`owner/repo` は url から作る。
- records/<owner>__<repo>-<N>-<headRefOid>.json があり、verdict が APPROVE で head が一致すれば、その区切りは通す。1 つの command に関所の区切りが複数あれば、全部が通るときだけ通す。
- `gh pr merge` に `--auto` があるときは、さらに `--match-head-commit <40桁>` があり記録の head と一致する場合だけ通す（予約後に HEAD が変わったまま自動マージされる恐れを塞ぐ。GitHub 側の予約解除条件は未確認のため止める側に倒す）。
- 止めるときの文:
  `review-gate: PR #<N> の今の HEAD <sha の先頭 9 桁> に Opus 審査役の APPROVE がありません。Opus の審査役（subagent_type: reviewer）を起動し、報告の最後の行に「VERDICT: APPROVE on <40桁sha> PR #<N>」を書かせてください。`
- 判定は `$REVIEW_GATE_DIR/log.jsonl` に 1 行足す（K-a・K-b の数え元）。当たらない Bash は正規表現の前段（`merge|review-gate|REVIEW_GATE` を含まない）で即 exit 0。
- Sonnet の Bash にも同じフックがかかる（recon.md §1）。

**(d) 第6版の追加（コード審査 review-4503.md・review-4503-r2.md の指摘。どれも止める側に倒す）**
- bash の値つき旗: `-o`・`-O`・`+o`・`+O`・`--rcfile`・`--init-file` と、`o` か `O` を含む短い旗のまとまり（`-euo` 等）は次の語を値として飛ばしてから `-c` を探す。
- `bash -c $'…'`・`$"…"`（中身を確かめられない引用）で全文に merge を含めば止める。
- `python`・`python3`・`perl`・`ruby`・`node`・`php` の `-c`・`-e`・`-E` の本文、およびこれらにヒアドキュメントで渡す本文に、単語としての `merge`（前後が英字・`_` でない。`mergeable`・`merged` は当たらない）か `mergePullRequest`・`enablePullRequestAutoMerge` を含めば止める。
- `GH_REPO`・`GH_HOST` の代入（`VAR=値` の前置き・`export`・独立した代入のどれでも）が command のどこかにあり、関所にかける区切りがあれば止める（gh の照合先が変わるため）。
- `-R<値>`・`--repo=<値>` のくっついた形も読む。PR を URL で渡したら、その URL の owner/repo で `gh pr view N --repo owner/repo` を行い、記録の名前は返った url の owner/repo を使う。
- 番号でも URL でもない位置引数（ブランチ名等）が merge の後ろにあれば、番号なしとして止める。位置引数が無いときだけ `.pr-number` を使う。
- 作業場所の追跡: `cd` と `pushd` を追う。行き先が `$REVIEW_GATE_DIR` の下ならその区切りで止める。`popd` の後は作業場所が分からないものとし、その後に関所にかける区切りがあれば止める。
- here-string（`<<<`）: 受け手が shell（`bash`・`sh`・`zsh`・`dash`・`ksh`・`source`・`.`）か `python`・`python3`・`perl`・`ruby`・`node`・`php` で、渡す文字列に単語としての `merge` を含めば止める（第7版。コード審査 review-4503-r3.md）。
- shell の一覧に `dash`・`ksh` を足し、`osascript -e` も `-c`・`-e` の本文と同じに扱う（第7版）。
- `xargs` の後ろに来た `gh pr merge`・`gh-pr-merge-safe.sh`・`check-pr-merge-ready.py` は、番号が後から足されうるので常に止める（第7版）。
- `gh api` と `curl` の merge は、パス `repos/<owner>/<repo>/pulls/<N>/merge` から owner/repo も取り、`gh pr view N --repo owner/repo` で照合する。owner/repo が取れなければ止める（第7版）。
- `--repo`・`-R`・`--match-head-commit` が同じ区切りに 2 回以上あれば止める（第7版）。
- `gh pr merge` で URL の owner/repo と `--repo`・`-R` の値が両方あり、大文字小文字を無視して一致しなければ止める（gh がどちらを使うか未確認のため。第7版）。
- (a) の文字検査は、連続する `/` を 1 本にしてから照合する（`//` でのすり抜けを塞ぐ。実装中に見つけて追加）。
- merge の位置引数が 2 個以上なら、`--disable-auto` があっても止める（gh の位置引数は 1 個まで）。
- (a) の試験台本の例外は、区切りの語が `scripts/agent-hooks/review-gate/test_review_gate.sh` と完全に一致するときだけ（末尾一致はしない）。

### 5-4. 審査役の最後の行の決まり（reviewer-verdict-rule.md の中身）

「審査結果を SubagentHandback で返すとき、message の最後の行を必ず `VERDICT: <APPROVE|REQUEST_CHANGES|REJECT> on <40桁のHEAD sha> PR #<番号>` にする。sha は審査の直前に `gh pr view <番号> --json headRefOid -q .headRefOid` で取る。この行が無い・sha が違うと、マージの関所（ADR-1029）を通らない。」

### 5-5. install.sh / rollback.sh（PO が `!` で実行。ADR-1011:39）

- install.sh:
  1. record.py・gate.py を `~/.claude/scripts/review-gate/` へ写し chmod 555。
  2. `~/.claude/review-gate/records` を 700 で作る。
  3. ~/.claude/settings.json を `settings.json.bak-review-gate-<UTC時刻>` に写す。
  4. python3 で hooks に 2 件を足す（既にあれば足さない＝何度流しても同じ）: PreToolUse matcher `Bash|Write|Edit|MultiEdit|NotebookEdit|Agent` → `python3 ~/.claude/scripts/review-gate/gate.py`、PostToolUse matcher `SubagentHandback` → `python3 ~/.claude/scripts/review-gate/record.py`。JSON として読めるか確認。
  5. 関所は全リポジトリにかかるため、~/.claude/agents/reviewer.md を `.bak-review-gate-<UTC時刻>` に写してから、末尾に印 `<!-- review-gate:ADR-1029 -->` つきで reviewer-verdict-rule.md の中身を足す（印があれば足さない）。
  6. 写した先の gate.py・record.py に対して test_review_gate.sh を流し、全部 PASS で `INSTALL_OK`。
- rollback.sh: settings.json を .bak に写してから上の 2 件だけを外し、~/.claude/agents/reviewer.md の印の節だけを外す（他の変更を巻き戻さないため、.bak の丸ごと戻しはしない）。外した結果空になった hooks の項目（`PreToolUse` 等）は、install 時の .bak に無かった項目だけを消す。`ROLLBACK_OK`。
- 往復試験: 一時の settings.json・reviewer.md に install→rollback を流し、導入前と完全一致（cmp）すること。install から呼ぶ試験では `REVIEW_GATE_SKIP_ROUNDTRIP=1` で往復試験を飛ばす（再帰防止）。

## 6. 弊害と対処

| 弊害 | 対処 |
|---|---|
| 正しく APPROVE したのに VERDICT 行が無く止まる | 止めの文で行の形を示す。reviewer.md 2 か所に決まりを書く。K-b で数える |
| gh が一時的に失敗して止まる | 止める側に倒す（安全優先）。再実行で通る |
| 記録の置き場・記録台本を読むだけでも止まる | 意図どおり（偽の記録を作る道を塞ぐため）。中身は PO が見る |
| 引用符の閉じ忘れなど shlex で読めない command は止まる | 意図どおり（読めないものは通さない）。ヒアドキュメントの本文は先に取り除くので `don't` などでは止まらない |
| 会話記録の assistant に opus 以外の model（`<synthetic>` 等）が混じると記録されない | このセッションの reviewer 13 件・181 発言では 0 件（/tmp/CC報告ファイル/review-gate-hook/arch/reviewer-models.txt）。K-b で数える |
| 区切りの中に引用された文が `; gh pr merge 1` を含むと誤って区切られる | shlex は引用の中を区切らない。閉じていない引用は上の行で止まる |
| 難読化（変数で組み立てる・eval 等）・GitHub 画面・Actions の自動マージ | 受け入れるリスク（ADR-1029） |
| 導入後、AI の Bash で `git add scripts/agent-hooks/review-gate/record.py` のように記録台本の名前を書くと止まる | 台本を直すときは Write/Edit（リポジトリ側は守りの外）と `git add scripts/agent-hooks` のようにディレクトリ単位で行う。CLAUDE 側の手順として design 本書に残す |
| 導入後、台本名を `--body "..."`・ヒアドキュメント・`git commit -m` の文字列や `chmod +x`・`bash -n` に書くと止まる | 台本を直す PR の本文は `--body-file <パス>` で渡す。誤止めは K-b で数える（architect 第5回、/tmp/CC報告ファイル/review-gate-hook/arch-review-5.md） |
| PO の `!` 実行（install.sh・rollback.sh）が関所にかかるか | 【未確認】。かかって止まった場合は、PO にターミナルで直接 `bash <パス>` を実行してもらう |
| `python3 -c`・`node -e` の本文に単語としての merge（`"merge" in title`・`merge-base`）があると止まる | gh の JSON は `--jq`・`-q` か jq で読む。git は `python3 -c` の外で叩く |
| 毎回の Bash で python3 が起動する | 前段の文字検査で当たらなければ即 exit 0 |

## 7. 外部・過去事例の参照と我々への応用

- 該当事例を使わない。理由: 「Claude Code のサブエージェント審査結果を記録してマージを止める」直接の公開事例は確認できていない。仕組みは公式の hooks 仕様（recon.md §1）だけに依る。

## 8. 受入基準

試験（test_review_gate.sh）は一時ディレクトリを `REVIEW_GATE_DIR` に、偽 gh を `REVIEW_GATE_GH` にして流す。偽 gh は `pr view` に決まった headRefOid と url `https://github.com/o/r/pull/<N>` を返す。

| 基準 | 検証方法（期待） |
|---|---|
| R1 | 記録なしで `gh pr merge 1 --merge` → exit 2・stderr に「Opus の審査役」 |
| R1 | 記録なしで `python3 scripts/dev/check-pr-merge-ready.py 1 release/x` → exit 2 |
| R1 | 記録なしで `gh api -X PUT repos/o/r/pulls/1/merge` → exit 2 |
| R1 | 記録なしで `curl -X PUT https://api.github.com/repos/o/r/pulls/1/merge` → exit 2 |
| R1 | `gh pr merge 1 --disable-auto; gh pr merge 1 --merge`（記録なし）→ exit 2 |
| R1 | `gh pr merge 1 --merge && gh pr merge 2 --merge`（1 だけ記録あり）→ exit 2 |
| R1 | `gh pr merge --merge`（番号なし）→ exit 2 |
| R1 | 記録なしで `ls`＋改行＋`gh pr merge 1 --merge` → exit 2 |
| R1 | 記録なしで `(gh pr merge 1 --merge)`・`if true; then gh pr merge 1 --merge; fi`・`/opt/homebrew/bin/gh pr merge 1 --merge`・`env A=1 gh pr merge 1 --merge` → すべて exit 2 |
| R1 | 記録なしで `bash -c "gh pr merge 1 --merge"`・`echo $(gh pr merge 1 --merge)`・`` echo `gh pr merge 1 --merge` `` → すべて exit 2 |
| R1 | 記録なしで `timeout 120 gh pr merge 1 --merge`・`echo 1 \| xargs gh pr merge`・`sudo gh pr merge 1 --merge`・`caffeinate -i gh pr merge 1 --merge`・`timeout 60 bash scripts/gh-pr-merge-safe.sh --merge` → すべて exit 2 |
| R1 | 記録なしで bash にヒアドキュメントで `gh pr merge 1 --merge` を渡す形・`echo "gh pr merge 1 --merge" \| bash` → すべて exit 2 |
| R2 | 記録ありで `gh pr merge 1 --merge` → exit 0 |
| R2 | `.pr-number`=1 の一時 git 作業場所で `cd <dir> && bash scripts/gh-pr-merge-safe.sh --merge`（記録あり）→ exit 0、記録なし → exit 2 |
| R2 | 本物: 導入後の最初の PR で reviewer APPROVE → マージが通る（log.jsonl で記録と通過を確認） |
| R3 | 記録ありのまま偽 gh の headRefOid を変える → exit 2 |
| R3 | 記録ありで `gh pr merge 1 --auto --merge`（--match-head-commit なし）→ exit 2、記録の head と同じ `--match-head-commit` つき → exit 0 |
| R4 | VERDICT が REQUEST_CHANGES・REJECT の入力で record.py → 記録 0 件・その後の gate exit 2 |
| R4 | meta.json の model が sonnet → 記録 0 件。VERDICT の sha が HEAD と違う → 記録 0 件。agent_type が reviewer 以外 → 記録 0 件 |
| R4 | VERDICT APPROVE・meta opus・sha 一致 → 記録 1 件（ファイル名 o__r-1-<sha>.json）。transcript_path が本流の形（`<s>.jsonl`）と自分の形（`<s>/subagents/agent-<id>.jsonl`）の両方、agent_id が `xxx` と `agent-xxx` の両方で、それぞれ記録 1 件 |
| R5 | Agent `subagent_type: reviewer, model: sonnet` → exit 2。`model: opus` と未指定 → exit 0 |
| R6 | Bash `echo x > ~/.claude/review-gate/records/a.json`・`cd ~/.claude && echo x > review-gate/records/a.json`・`python3 ~/.claude/scripts/review-gate/record.py < x.json`・`python3 scripts/agent-hooks/review-gate/record.py < x.json`・`bash scripts/agent-hooks/review-gate/test_review_gate.sh && python3 ~/.claude/scripts/review-gate/record.py < x.json` → すべて exit 2 |
| R6 | Write・Edit・MultiEdit（file_path）と NotebookEdit（notebook_path）が `$REVIEW_GATE_DIR` の下 → すべて exit 2 |
| R1（第6版） | 記録は PR 1 だけで次がすべて exit 2: `bash -o pipefail -c "gh pr merge 2 --merge"`・`bash -euo pipefail -c "…2…"`・`gh pr merge 2 --merge --disable-auto=false`・`gh pr merge 2 -R o/r --disable-auto x`（値の位置）・`gh pr merge release/x --merge`・`gh pr merge https://github.com/o/r2/pull/1`・`GH_REPO=o/r2 gh pr merge 1`・`export GH_REPO=o/r2; gh pr merge 1`・`gh pr merge -Ro/r2 1`・`gh -Ro/r2 pr merge 1`・`bash -c $'gh pr merge 2'`・`python3 -c "import os;os.system('gh pr merge 2')"`・`perl -e 'system("gh pr merge 2")'`・`python3` にヒアドキュメントで os.system のマージを渡す形・`popd; gh pr merge 1` |
| R6（第6版） | `cd ~/.claude/review-gate && ls`・`pushd ~/.claude/review-gate; echo x > records/a.json`・語が「x/ で始まり末尾が試験台本名」の区切りで置き場に書く形 → すべて exit 2 |
| 誤止めなし（第6版） | `gh pr view 1 --json mergeable \| python3 -c "import json,sys;print(json.load(sys.stdin)['mergeable'])"`・`gh pr view 1 --json mergeable,mergeStateStatus`・`git merge origin/main`・`git log --merges` → すべて exit 0 |
| R1（第7版） | 記録は o/r の PR 1 だけで次がすべて exit 2: `bash <<< "gh pr merge 2 --merge"`・`python3 <<< "import os;os.system('gh pr merge 2')"`・`source /dev/stdin <<< "gh pr merge 2"`・`.pr-number`=1 の作業場所で `echo 2 \| xargs gh pr merge --merge`・`gh api -X PUT repos/o/r2/pulls/1/merge`・`curl -X PUT https://api.github.com/repos/o/r2/pulls/1/merge`・`gh pr merge 1 --repo o/r --repo o/r2`・`gh pr merge 1 --merge --match-head-commit <記録sha> --match-head-commit <別sha>`・`dash -c "gh pr merge 2"`・`ksh -c "gh pr merge 2"`・`osascript -e 'do shell script "gh pr merge 2"'` |
| R2（第7版） | 記録ありで `gh api -X PUT repos/o/r/pulls/1/merge`・`gh pr merge https://github.com/o/r/pull/1 --merge --repo o/r` → exit 0。`--repo o/r2` との不一致 → exit 2 |
| 往復 | 一時 settings.json・reviewer.md に install→rollback → 導入前と cmp で一致（導入前から空の hooks 項目がある形も含む） |
| R7 | agent-hooks-test.yml が この PR で走り緑（PR のチェック欄で確認） |
| 誤止めなし | `ls`・`grep -n x scripts/dev/check-pr-merge-ready.py`・`git diff -- scripts/gh-pr-merge-safe.sh`・`gh pr create --body "gh pr merge 1"`・`git commit -m "gh-pr-merge-safe.sh"`・`gh pr merge 1 --disable-auto`・`bash scripts/agent-hooks/review-gate/test_review_gate.sh`・ヒアドキュメントの本文に閉じない引用符（`don't merge yet`）がある `gh pr create`（本文はヒアドキュメントで渡す形）・`git commit -m "$(cat <<'EOF'` で始まり本文に `1)`・バッククォート 3 個の並び・閉じない引用符を含むコミット・`grep -rn "gh pr merge" docs` → すべて exit 0 |

## 9. 維持の仕組み

- 守り手: Opus（設計・審査の起動）、CI agent-hooks-test.yml（試験）、PO（install.sh の `!` 実行）

- フックを変えるときは scripts/agent-hooks/review-gate/ を PR で直し、CI の試験が緑になってから PO が install.sh を `!` で流す（ADR-1011:39）。
- AGENTS.md に「マージ前は reviewer(opus) の VERDICT 行つき APPROVE が必須（ADR-1029 のフックで強制）」の 1 行を足す。

## 10. 接触面

- 変わる: ~/.claude/settings.json の hooks（2 件追加）・~/.claude/agents/reviewer.md（末尾 1 節）・~/.claude/scripts/review-gate/（新規）＝いずれも PO 実行の install.sh。リポジトリでは .claude/agents/reviewer.md・AGENTS.md・新規 workflow 1 本・docs/adr/README.md（再生成）。
- 範囲: 関所はユーザー設定なので、このリポジトリ以外の AI のマージにもかかる。~/.claude/agents/reviewer.md にも決まりを足すので、他のリポジトリでも同じ手順で通る。
- 変わらない: 製品コード・DB・本番・Branch Protection・既存のフック 5 本・scripts/dev/check-pr-merge-ready.py・scripts/gh-pr-merge-safe.sh。

## 11. 未解決

- PostToolUse の SubagentHandback の実物の入力 JSON は導入後の 1 件目で確かめる（R2 と同時）。取れなければ止まる側に倒れる（マージできない）ので、その場合は rollback.sh で外して直す。
