# recon: 会話での同意を許可券の代わりにする仕組み（事実のみ）

調査基準: origin/main = 70c3eda3d0d2dae68621637376aa65a3ad71f5b0（2026-10-19、`git fetch origin` 後）。作業場所 /Users/tanizawashingo/worktrees/salesanchor/release-conversation-consent-permit（origin/main 起点）。
ただし A・D の一部は、リポジトリ外の実機ファイル（~/.claude/scripts/、~/.codex/salesanchor/、~/.claude/projects/…）を直接読んだ。実機の agent-danger-hook.sh はリポジトリの docs/handoff/design-approval-ticket/stage2-hooks/agent-danger-hook.sh と `cmp` で完全一致（467行）。
準備: executor-preflight は rc=0（PREFLIGHT OK、本店が origin/main より 3574 コミット遅れの WARN あり）。生出力は /tmp/CC報告ファイル/conversation-consent/preflight.txt。

## 0. 既存 ADR 検索の結果

- `git grep -il "permit|許可券|チケット" -- docs/adr/` の結果は4件（/tmp/CC報告ファイル/conversation-consent/adr-grep.txt）。
  - docs/adr/ADR-065-asyncpg-prepared-statement-cache-disable.md（無関係：permit の語が別の意味）【推測】
  - docs/adr/ADR-091-discord-bot-scope-definition.md（同上）【推測】
  - docs/adr/ADR-1003-go-delegation-to-opus.md:45（大量 DELETE 等は `scripts/permit-danger.sh` 等の運用で従来どおり人手で担保）
  - docs/adr/ADR-1024-ai-readonly-db-path.md:54,64（permit チケットを毎回渡す案を不採用にした記録）
- docs/adr/FEATURE-INDEX.md を `grep -i "permit|許可券|チケット"` したが一致 0 件。ADR-1011・ADR-1003・ADR-1015 の行も FEATURE-INDEX.md には無い（`grep "ADR-1011\|ADR-1003\|ADR-1015"` が 0 件）。
- ADR-1011（docs/adr/ADR-1011-permission-self-maintenance.md, 61行, ステータス Accepted `:5`）の主題は「autoMode.allow の SM- 文の週次保守」。「フックの変更は、今までどおり AI がパッチを作り PO が `!` で反映する」と明記（同 :39 付近の「範囲外」節の末尾）。会話同意・transcript への言及は 0 件。
- 「設計承認チケット」という語は ADR-1003 に 0 件（`grep -c` = 0）。design.md 段3 が予定する「ADR-1003 追補」（design.md:136）は未実施。
- 会話記録（transcript）を同意の根拠にする既存 ADR は、上の検索範囲では見つからなかった。語を変えた検索（transcript・同意）は未実施【未確認】。

## A. 危険操作を止める見張り役

### A-1 所在・登録

- 本体はすべてリポジトリ外 ~/.claude/scripts/。リポジトリ内の写しは docs/handoff/design-approval-ticket/stage2-hooks/（agent-danger-hook.sh / danger_sanitize.py / extract-pr-body.py / pr-body-guard.sh / worktree-access-guard.sh / worktree-only-guard.sh）。agent-danger-hook.sh と danger_sanitize.py は実機で `-r-xr-xr-x`（書込禁止）。pr-body-guard.sh は `-rwxr-xr-x`、extract-pr-body.py は `-rw-r--r--`（ls -la）。
- 登録: /Users/tanizawashingo/.claude/settings.json:238（worktree-only-guard, Bash）、:242（agent-danger-hook, Bash）、:254（pr-body-guard, Bash）。他に worktree-only-guard は Edit/Write にも登録（:272, :285 付近）。
- ほかに PreToolUse に /usr/local/bin/node のフックが Bash 用に複数、Read 用に1件登録されている（settings.json の hooks 一覧）。node フックの本体は「Application Support/agent-console」配下のため指示により読まない。【未確認】（これらが permit-danger.sh の AI 実行を止めるかは不明）
- psql-write-guard と permits-guard は独立ファイルではなく、どちらも agent-danger-hook.sh の中のブロック。

### A-2 agent-danger-hook.sh（/Users/tanizawashingo/.claude/scripts/agent-danger-hook.sh, 467行）

| 区間 | 検知するもの | 許可券の扱い |
|---|---|---|
| :67-76 | 照合前に danger_sanitize.py all でコマンド文字列から「ただの文字」を除いた SCAN_COMMAND を作る。失敗時は元の COMMAND | - |
| :88-154 psql-write-guard（SalesAnchor リポジトリのときだけ :82） | ssh/docker＋psql の `< file`、`-f`、`\| psql`、`-c "INSERT…/UPDATE/DELETE FROM/CREATE/ALTER/DROP/TRUNCATE/GRANT/REVOKE"`（:98-120）。SCAN_COMMAND に対して照合 | `python3 ~/.codex/salesanchor/permit_bridge.py consume-ticket` に INPUT 全体を渡す（:136）。出力が `consumed` なら通す（:139-144）。違えば exit 2（:152） |
| :156-190 permits-guard | COMMAND（サニタイズ前）に対する正規表現4種で `.claude/permits` への言及を検知（:168-173）。tilde/$HOME/絶対パス、相対、`'/.claude/permits`、`'.claude','permits'` 分割形 | 券は参照しない。検知したら `permits_self_issue_blocked` を agent-events.jsonl に記録（:183）して exit 2（:189）。**自己発行防止はこの文字列照合だけ** |
| :192-349 スコープ認識型削除ガード | `git clean` / `git stash`(破壊系) / `git checkout --` / `git restore`（:237-242）。本店のみブロック、worktree 内は `scope_destruct_worktree_allowed` を記録して通過（:292-295） | 本店のとき :302-331 の照合（下記 A-3） |
| :351-465 danger_ops 照合 | ~/.claude/agent-tokens.json の danger_ops を SCAN_COMMAND に部分一致（:393-400）。danger_ops は 17 語: DROP TABLE / DROP DATABASE / rm -rf / git push --force / git push -f / git reset --hard / DELETE FROM / TRUNCATE / git push origin main / git push origin develop / rm -r / git push -u origin main / git push -u origin develop / git push origin HEAD:main / git push origin HEAD:develop / git rebase / clasp push。grep/rg/cat/head/tail/less/sed -n の区間は事前に除外（:362-390） | :415-444 の照合（A-3）。通れば exit 0、無ければ `_hook_blocked_log` ＋ exit 2（:458-464） |

- 止めたとき `_hook_blocked_log`（:18-50）が agent-events.jsonl に `hook_blocked`（hook, reason, cmd_head 120字）を1行追記する。記録のみで判定には影響しない。

### A-3 許可券（~/.claude/permits/danger-permit-*.json）の照合・消費（汎用経路）

- :415-443 と :302-330 は同じ処理。glob で danger-permit-*.json を全部読み、`expires_at` を過ぎたものは削除（:430-434）、`op` と検知語（MATCHED）が**部分一致（どちらかがもう一方を含む）**なら券ファイルを `os.remove`（=消費）して `consumed`（:436-440）。
- この経路で照合するのは `op`・`expires_at` だけ。`created_by`・コマンド全文・cwd・session は見ない。
- 【事実】`p.get('op','').lower() in op_matched` の形のため、`op` が空文字の券は任意の検知語に部分一致する式になっている（:437）。発行スクリプト側は引数が空だと発行しない（permit-danger.sh:8-12）ので、通常は起きない。
- psql-write 経路だけは別: permit_bridge.py（~/.codex/salesanchor/permit_bridge.py, 105行）が券を探し、次をすべて満たすものを `unlink` して 30 秒有効の「受領書」（write-receipts/<sha256>.json）に変える（:46-67）。
  - `op == "psql write"`（完全一致）、`created_by == "manual"`、有効期間が 0 秒超 1800 秒以下、所有者が自分。
  - 受領書の鍵は sha256([command, realpath(cwd), session_id, tool_use_id])（:15-21）。つまり**コマンド全文と tool_use_id に束縛**される。
  - agent-danger-hook は `consume-ticket` を呼ぶ（:136）。もう一方（Codex 側の hook）が受領書を消費する設計（docstring :1-4）。Codex 側 adapter.py（790行）は読んでいない【未確認】。

### A-4 psql-write 以外のガード

- worktree-only-guard.sh（/Users/tanizawashingo/.claude/scripts/worktree-only-guard.sh, 128行）
  - main/develop への `git commit` を止める（:120-123）。`git push` の `--force/--force-with-lease` で origin develop/main を止める（:124-126）。旧クローン（crm-app-new, /private/tmp/*）の push/fetch を止める（:116-119）。
  - Write ツールで ~/.claude/permits/ 以下へ書くのを止める（:44-65）。Edit・NotebookEdit は `[ "$TOOL_NAME" = "Bash" ] || exit 0`（:68）で素通り（Edit にも登録はある :272 付近だが、この関数の中では Write だけ判定）。
  - 許可券は参照しない（permit なしで常に止まる。解除は PO の別手段）。
- permits-guard は A-2 に記載（agent-danger-hook 内）。
- gh-scope-guard.sh は gh-peek-*.json（別系統の券）を消費する（gh-scope-guard.sh:35,138,225-255）。発行元の scripts/permit-peek.sh は origin/main に存在しない（`ls` で No such file）。【事実】
- card-lint.sh:159 は「permit-danger.sh 経由にする」というカード文面の検査（許可の自己発行 L22）で、実行時の防御ではない。
- AI が `bash scripts/permit-danger.sh "<op>"` を Bash で直接実行できるかは、上記3本のフック内には禁止処理が無い（permits-guard は `.claude/permits` の文字列にしか反応しない。permit-danger.sh 実行コマンドにその文字列は含まれない）。node フックの挙動は【未確認】。ただし design.md:169 は「AI は単発の permit を発行できる」ことを受容リスクとして記録済み。
- agent-events.jsonl の種別件数（2026-10-19 15:27 時点、15.8MB）: stop 31968 / gh_scope_blocked 24961 / start 20027 / main_repo_write_blocked 6847 / danger_detected 6519 / worktree_bypass_blocked 4102 / hook_blocked 1627 / danger_permit_consumed 295 / gh_permit_consumed 199 / scope_destruct_permit_consumed 15 / permits_self_issue_blocked 134 / hook_permit_consumed 1。

## B. scripts/permit-danger.sh（origin/main, 44行）

- 引数 `<operation>` が空なら Usage で exit 1（:8-12）。
- ~/.claude/permits/danger-permit-<SAFE_OP>-<UTC日時>.json を作る（:15-19）。SAFE_OP は空白と `/` を `_` に変え英数・`_`・`-` 以外を除去（:18）。同じ秒に同じ op なら上書き（ファイル名が秒単位）。
- 中身（:31-36）: `{"op": <引数そのまま>, "created_at": "...Z", "expires_at": created+30分, "created_by": "manual"}`。署名・コマンド全文・cwd・session は持たない。
- 照合: A-3 のとおり op の部分一致（汎用）、psql write は完全一致＋created_by=manual（permit_bridge.py:55）。
- `created_by: "manual"` はスクリプトが固定で書く文字列で、AI が同じ形の JSON を書けば同じ値になる（書込禁止は A-2 の permits-guard と A-4 の Write 禁止に依存）。

## C. 既存設計

- docs/handoff/design-approval-ticket/design.md（285行）段3「設計承認チケット」は :87-137。
  - ops.yaml（kind は psql-write の1種のみ。cmd 完全一致＋sql_file の sha256 束縛。max_uses 既定1。期限既定72時間・上限7日。:89-107）。
  - 発行スクリプト scripts/approve-design.sh（PO が `!` で1回実行。表示してから ~/.claude/permits/design-approval-<id>.json を作る。`created_by: "po-bang"`。:108-124）。
  - AI の発行防止: コマンド文字列に `approve-design` が出たら exit 2（:125-127）。
  - 消費: agent-danger-hook.sh に `consume_design_ticket` を追加（:128-139）。
  - 受容するリスク: 「チケットのファイルは本人の署名を持たない。AI が文字列を分けて組み立てれば permits-guard を逃れて偽造できる」（design.md:169）。署名は偽造が1件でも見つかった時点で導入、と記載。
  - 段4: 機械で確かめたチケットのときだけ PreToolUse の `permissionDecision: "allow"` を返す案（:139-150）。
- 段3の未実装の確認（すべて事実）:
  - origin/main に scripts/approve-design.sh が無い（`ls` で No such file）。
  - `git grep -il "approve-design|consume_design_ticket" origin/main` の一致は docs/handoff/design-approval-ticket/design.md の1ファイルのみ。
  - 実機の agent-danger-hook.sh に `consume_design_ticket|approve-design|design-approval|ticket_used` は 0 件（`grep -c` = 0）。
  - ADR-1003 に「設計承認チケット」節が無い（0件）。
- 段1（hook_blocked の記録）と段2（danger_sanitize.py による誤検知修正）は実装済み。stage1-record.md / stage2-record.md（1198行）。
- design.md の受入試験 T3-1: 「PO の `!` 実行にも PreToolUse フックがかかるか」は実測前（recon.md:154、design.md:194）。【未確認】

## D. 会話記録 JSONL の形

調べた記録: ~/.claude/projects/-Users-tanizawashingo-salesanchor/e7a95d2c-3806-489c-a8b6-18b615c05730.jsonl（37227行、最近更新の大きいセッション）。集計スクリプトと生出力: /tmp/CC報告ファイル/conversation-consent/analyze2.py、jsonl-main2.txt（本文は載せない。下の例は30字以内）。

### D-1 行の種類（type）

トップレベル `type` は user / assistant / system / attachment / queue-operation / last-prompt / mode / permission-mode / ai-title / custom-title / agent-name / pr-link / api-request / api-request-blob など。「会話の発話」になるのは `user` と、人が処理中に打った分が入る `attachment`（下記）。

### D-2 `type:"user"` 行の内訳（message.content と origin）

| 件数 | content | origin | isMeta | 意味 |
|---|---|---|---|---|
| 2147 | 配列 [tool_result]（toolUseResult あり） | なし | なし | ツール結果 |
| 173 | 文字列 | `{"kind":"human"}` | なし | 人が打った入力（例 `▎ /tmp/CC報告ファイル/handoff-202610…`） |
| 3 | 文字列（貼り付け印あり） | `{"kind":"human"}` | なし | 人の入力（貼り付けを含む。例 `VMAXクライマックスに…`） |
| 227 | 文字列 | `{"kind":"peer", "body":…, "from":…, "handback":true, "senderTaskId":…}` | true | サブエージェント報告・他セッションからの通知（"[Subagent hand-back]"、"Another Claude session sent a …"） |
| 133 | 文字列 `<task-notification>…` | `{"kind":"task-notification"[, "producer":"session-task"]}` | なし | バックグラウンド作業の完了通知 |
| 45 | 文字列 "This session is being continued…" | なし | なし | 圧縮後の要約（compact_boundary と対） |
| 28 / 28 | 文字列 `<bash-input>…` / `<bash-stdout>…` | なし | なし | PO の `!` コマンドとその出力 |
| 3 | `<local-command-caveat>…` | なし | true | ローカルコマンド注意書き |
| 10 + 1 | "[Usage limit reached…" / "[Earlier usage-limit notes…" 等 | なし | true | 使用量通知 |
| 1 | `<system-reminder>…` | なし | true | システム通知 |

### D-3 「人が打った入力」を区別できるか（判定材料）

- 【事実】`origin.kind == "human"` が、人の入力と他の発生源を分ける唯一の明示フィールド。上表の人の入力 176 件はすべてこの値で、ツール結果・peer・task-notification・圧縮要約・`!` コマンドには付かない（origin なし、または別の kind）。
- 【事実】人が**AI の処理中に打った**入力は、`type:"user"` 行ではなく `type:"attachment"` 行の `attachment.type == "queued_command"` に入る（このファイルで human は 16 件、`commandMode:"prompt"`、`humanTurn` キーあり、`origin:{"kind":"human"}`、本文は `attachment.prompt`）。同じ queued_command でも task-notification（233件）や peer 報告（3件）は origin.kind が別。さらに `queue-operation`（enqueue 773 / dequeue 367 / remove 403）の content にも本文が出る。
- 【事実】人の入力 192 件（上の 176＋queued 16）の文字数は 最小1・中央値23・90%点197・最大1187。うち「数字1〜2桁」または y/n/はい/いいえ/ok だけのものは 56 件。1件は先頭が `▎` で、AI の報告文を貼ったとみられる文面（`origin.kind` は human）。
- 【事実】貼り付けも `origin.kind:"human"` になる。貼り付け印（"[Pasted" または `<pasted_content`）のあるものは 3 件。つまり origin.kind だけでは「人が自分で打った文」と「人が貼った AI の文」は区別できない。区別材料は本文の印（貼り付け印、先頭 `▎` など）に限られる。
- 【事実】`isMeta:true` が付くのは peer・local-command-caveat・usage・system-reminder 系（人の入力には付かない）。`userType` は全行 "external" で区別に使えない。`isSidechain` はこのメインファイルでは全 user/assistant/attachment 行が False。
- 【事実】`system` 行（535 stop_hook_summary、532 turn_duration、45 compact_boundary 等）は人の発話ではない。フック出力は `attachment.type == "hook_success"`（55件）に入る。
- 【未確認】フックが呼ばれた時点で、直前の人の入力がすでに transcript に書き込まれているか（書込みタイミング）。この記録からは判定できない。
- 【未確認】フック入力 JSON のうち、サブエージェント内の呼び出しで `transcript_path` がメインかサブのどちらを指すか、`agent_id` 等の識別子があるか。公式 hooks リファレンスは PO が確認済みとのことで本調査では再確認していない。

### D-4 サブエージェントの記録

- メイン記録とは別ファイル: `<セッションID>/subagents/agent-<id>.jsonl`（＋ agent-<id>.meta.json）。このセッションの下に 394 ファイル。
- meta.json の項目: agentType, description, toolUseId, spawnDepth, requestShape("background"), requestNonInteractive(true), model。
- サブ側の行は `isSidechain:true` と `agentId` が付く。サブ側の最初の user 文字列行（プロンプト）には `origin` が無い。つまり**サブエージェントの記録の user 行は origin.kind:"human" を持たない**（調べた1ファイルで確認）。

## E. 「外してよい止まり」2件＋集計の現状

### E-1 rm -rf の判定（agent-danger-hook.sh）

- 判定は検知語 "rm -rf" / "rm -r"（agent-tokens.json の danger_ops）を SCAN_COMMAND に**部分一致**（:393-400）。対象パスはフック本体では見ない。
- パスを見て外す処理は danger_sanitize.py の rm モード（:263-301 rm_allowed、:248-260 target_ok、:434-435）。外すのは「絶対パスだけ・`..` や `.git` を含まない・glob/変数/`~` なし・根そのものでない・cwd の worktree の下か /private/tmp/claude-501/ の下」の rm -r のみ。
- 実測（/tmp/CC報告ファイル/conversation-consent/sanitize_probe.py → sanitize_probe.out。danger_sanitize.py all を直接実行、フックは起動していない）:
  - worktree 内の絶対パス / /private/tmp/claude-501/ 内 / `&& echo` が後ろに付く worktree 内 → 検知語が消える（止まらない）。
  - /tmp/foo、相対パス `./build`、`$HOME/x` → 検知語が残る（止まる）。
- heredoc 内の文字: `cat`/`tee` でファイルに書く heredoc の本文は除く（danger_sanitize.py:304-313, 398-410）。実測で、`cat > worktree内/x.md <<'EOF'` の本文に rm -rf が有っても止まらない。`python3 - <<'EOF'` の本文は残る（止まる）。`$( … )` の中に入った cat heredoc も残る（止まる）。git commit -m の文面は除かれる（止まらない）。

### E-2 pr-body-guard が --body-file を読めず止まる箇所

- /Users/tanizawashingo/.claude/scripts/pr-body-guard.sh:148 で extract-pr-body.py を呼び、終了コード 3 のとき :154-158 で `BLOCKED [pr-body-guard]: --body-file を読み込めないため PR本文を検証できません` ＋ exit 2。
- extract-pr-body.py:85-119: `--body-file` の相対パスを cwd に解決して open し、OSError なら BodyFileUnreadable → :117-119 で exit(3)。
- フックは PreToolUse（コマンド実行前）に走る。そのため同じコマンド内で `cat > f <<EOF … EOF && gh pr create --body-file f` のようにファイルを作ると、フック実行時点ではファイルが無く読めず止まる。【推測】（コードから導いた説明。このパターンでの実機再現は未実施）
- pr-body-guard.sh:62 は heredoc モードのサニタイズで、本文の抽出は元の COMMAND に対して行う（:148）。

### E-3 stop-log-digest.sh（.claude/hooks/stop-log-digest.sh, 133行）の「ストップ」集計

- known_types は gh_scope_blocked / worktree_bypass_blocked / danger_detected / access_blocked / **stop**（:26-32）。`stop` は agent-stop-hook.sh:14 が**セッション終了のたびに**書く種別で、ブロックではない。
- `start`（agent-start-hook.sh:26 が書く）は known_types に無く "other" に入る（:100）。表示は固定6行（:114-115）で、total は counts の合計（:110）なので `start` も `other` 経由で「前日の総ストップ件数」に含まれる（:125）。
- `hook_blocked`（A-2 の記録）・`main_repo_write_blocked`・`danger_permit_consumed` なども同じく other に入る。
- 実ログの件数: stop 31968、start 20027（A-4 の件数表）。

## F. フックの変更をAI自身が反映できない制約

- 制約の根拠:
  - docs/handoff/design-approval-ticket/self-maintenance-design.md:44-48: 「AI がフックの写しを書き換えようとしたところ、PO の具体的な許可文があっても [Self-Modification] で止まった。同じ変更でも PO の `!` 実行（スクリプト）なら通った」（2026-10-13 実測）。Self-Modification は soft_deny で hard_deny ではない（:34）。
  - docs/adr/ADR-1011-permission-self-maintenance.md の範囲外節: ~/.claude/scripts/ の下のファイルと hooks は AI が自分では変えない。
  - design.md:249-251: 文書だけの作業でも「権限に関する設計」は自動判定に止められうる実例。
  - 実機のフック2本は `-r-xr-xr-x`（ls -la）。
- 反映手順（実例）: AI が試作を docs/handoff/<topic>/stage2-hooks/ に作り、PO が `! bash …/po-apply-stage2.sh` で本物へ反映する。
  - docs/handoff/design-approval-ticket/po-apply-stage2.sh: バックアップ（~/.claude/scripts/.backup/<日時>/、:10-14）→試作の試験→chmod u+w→cp→権限を戻す→本物の試験（`--real-home`）→1件でも不合格なら自動で戻して「ROLLED BACK」。permits に danger-permit-*.json が残っていれば何も変えず中止（:27-32）。VOICEVOX_MUTED が無いと中止（:24）。
  - 試験: scripts/dev/test-agent-hooks.sh（`<フックのあるディレクトリ> [--real-home]`）。
  - settings.json の登録変更も同方式: po-register-stage1.sh（＋ po_register_stage1.py）、po-register-stage2-allow.sh、po-register-self-maintenance.sh、po-unregister-self-maintenance.sh、po-remove-private-repo-rule.sh（同ディレクトリ）。po-register-stage1.sh は settings.json を `.bak-<日時>` に写してから Python で hooks を1件追加し、結果を表示。
  - stage2-record.md:183（PO が実行する1行の例）、:199（macOS bash 3.2 で変数直後の全角文字が変数名扱いになり止まった事故と修正）。

## 調査中にフック／制限で止まった事実

1. `ls`/`cat` を含む1本のコマンドの中に `~/.claude/permits` の文字列を入れたところ、permits-guard が exit 2 で止めた（"BLOCKED [permits-guard]"）。言い換えて同じ操作は再試行していない。permits の中身は一切読んでいない。券の形式は scripts/permit-danger.sh と permit_bridge.py のコードから読んだ。
2. `~/.claude/scripts/review-gate` を grep 対象に含めたところ、review-gate の gate.py が「review-gate の記録・台本には触れません」で止めた。同ディレクトリは読んでいない。以降は対象から外して他のファイルだけを調べた。
3. 指示された「Application Support/agent-console」配下は読んでいない（node フックの中身は【未確認】）。
