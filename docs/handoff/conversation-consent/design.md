# design: 会話での同意を許可券の代わりにする（＋不要な停止の解消）

改訂: §13 改訂1（2026-10-26、見張りの異常の数え方を分ける。自己審査済み。PO 実装承認 2026-10-26: 選択肢「1. この設計で作るのを承認する」に「1」と回答）。
状態: PO 承認済み（2026-10-19、PO が選択肢「1. この設計で進める → 審査役の確認後に Sonnet に作らせる」に「1」と回答）。Architect 審査 1回目 REVISE → 第2版、2回目 REVISE → 第3版、3回目 REVISE（HIGH 0・P1〜P5・Q1〜Q7）→ 第4版で反映（§12）。§7 の受け入れるリスク R1 は PO が受容（2026-10-19、選択肢「1.【おすすめ】受け入れて進める」に PO 原文「1,定期実行に追加された権限などをチェックするセッションを開く仕組みを入れて定期的にチェックする」）。受容の言葉と日付を ADR-1033 に書いてから便1をマージする。PO の追加条件は §9 の定期点検（K13）で満たす。
ADR 案: ADR-1033（番号は起票時に再確認）。
根拠: 同じフォルダの recon.md（origin/main 70c3eda3d 基準）。停止の仕分けは /tmp/CC報告ファイル/stop-triage/triage.md。審査は /tmp/CC報告ファイル/conversation-consent/architect-review.md・architect-review-2.md。

## 1. 目的（PO の言葉）

- 「会話の中で合意した事項であれば許可して再度許可を発行しなくても進めてほしい」（2026-10-19）
- 「権限不足で毎回止まるのをやめ、本当に判断が必要な時だけ止まりたい」（同日）

利用者に見える変化:
- 前: 危険な操作のたびに、PO が `! bash scripts/permit-danger.sh "<op>"` を打つ。
- 後: AI が操作を具体的に書いて番号で聞く。PO が「1」を打つと、その操作だけが1回通る。

## 2. 成功条件（○×で判定）

| # | 基準 | 検証方法 |
|---|---|---|
| K0 | フックが動く時点で、PO の直前の入力が会話記録に書かれている | 反映後、consent_check が呼ばれるたびに `consent_probe`（H の uuid・timestamp、now）を書く。consent-audit.py が後から記録を読み、「後から見て直前の人の入力が typed の『1』だった呼び出し」を数える。そのうち「probe の now より前の timestamp を持ち、probe が見た H より新しい人の入力」が記録にあるものを遅れ1件とする。`tool_use_id` が probe にあれば、時刻ではなく記録の順で見る: 記録の中のその tool_use 行より前で最も近い人の入力を本当の直前の入力とし、それが probe の H の uuid と違えば遅れ1件（S4）。対象の呼び出しが20件たまった時点で遅れ0件なら○、1件でもあれば×で §6 の案 F に切り替える設計に戻す（P5）。事前の目安として Opus が consent-audit.py --probe を打ってよい（判定には使わない） |
| K1 | 同意票の操作に PO が「1」だけで答えると、その完全一致のコマンドが1回だけ通る | T1（本物のフック・本物の会話で1件。単体試験に `1. 上の同意票の操作を実行する【おすすめ】…` の行の例を含む、S5） |
| K2 | 同じ同意票の同じ操作は、順に2回でも並行に2本でも、通るのは1回だけ | T2（順次と並行の2本） |
| K3 | PO の「1」から30分を過ぎると止まる | T3（部品の関数に時刻を引数で渡す単体試験） |
| K4 | コマンドが1文字でも違うと止まる | T4 |
| K5 | 次の場合は止まる: 貼り付け／サブエージェントの報告（peer）／task-notification／`!` の出力／channel（Discord）／promptSource が typed 以外（queued を含む）／サブエージェントからの呼び出し（agent_id キーあり）／同意票が tool_use の中にだけある／同意票が H の前の最後の AI の text ブロックに無い／同意票の後、最初の人の入力が「1」でない／同意票と H の間に queued の入力か compact の行がある／末尾 4MB に H か同意票が無い | T5（偽の記録を作った単体試験。偽の行は実物の会話記録の行からキーの組を写して作る（user 行は最上位 origin、queued は attachment.origin）。4MB の境目が行の途中にある例、最後の行が改行で終わっていない例、「1」の後に画像つきの入力がある例を含む、S5） |
| K6 | 除外（§4-4）に当たるコマンド、`$` かバッククォートを含む操作は、同意があっても止まる | T6 |
| K7 | AI が会話記録・同意の台帳を Bash/Write/Edit/MultiEdit/NotebookEdit で触ろうとする、または端末への入力注入（tmux・agent-console の /chat/queue・osascript）を行おうとすると止まり、`consent_guard_blocked` が1行書かれる | T7 |
| K8 | rm -rf の対象が「/tmp/CC報告ファイル/ の下」「/private/tmp/CC報告ファイル/ の下」「/private/tmp/claude-501/ の下」「作業場所の下（相対パスを含む）」なら止まらない。根そのもの・`..`・`.git`・`$X`・`*`・`?`・`[`・`{..,x}`・`~`・`\`・`!`・コマンド内に cd/pushd/popd/`(`/`bash -c`/`sh -c`/eval があるときの相対パスは、根の下でも止まる | T8（`/private/tmp/claude-501/$X`、`/private/tmp/claude-501/*`、`/tmp/CC報告ファイル/{..,x}`、`cd ~ && rm -rf x`、`(cd /; rm -rf x)` を止める例を含む） |
| K9 | PR 本文ファイルが読めずに止めたとき、止めた理由の文が「本文ファイルを Write で先に作り、別のコマンドで gh を実行する」と手順を示す | T9 |
| K10 | 朝の要約が「止めた回数」（§4-6(c) の種別だけ）と「記録の行」と「ほかの見張りの記録（未分類）」を分けて出し、1件の停止を二重に数えない | T10（記録の見本で試験）＋翌朝の表示を目視 |
| K11 | 反映後7日で、hook_blocked のうち「§4-6(a) の根の下で、glob・変数・`~` を含まない rm -rf」が0件 | agent-events.jsonl を理由別に集計（反映前7日と比較） |
| K12 | 反映後7日で、danger_permit_consumed（PO が許可券を使った回数）が反映前7日より減る | 同上 |

## 3. 現状（recon より）

- 危険語は agent-danger-hook.sh が部分一致で止める。最初に当たった1語で照合を打ち切る（:393-400）。許可券は op の部分一致と期限だけで消費する（recon.md:36, :42-43）。
- psql write だけは、コマンド全文に束縛した受領書に変える（recon.md:45-47）。受領書は Codex 側の hook が消費するもので（permit_bridge.py:1-3）、Claude Code の Bash の登録に Codex の hook は無い（settings.json 実測、architect-review-2 N6）。
- 人の入力は、会話記録の `origin.kind=="human"` で見分けられる。貼り付けも human になる（recon.md:112-115）。AI の処理中に打った入力は `attachment.queued_command` に入り、打った時点ではなく差し込まれた時点で記録に入る（recon.md:113）。
- サブエージェントの記録には human の行がない（recon.md:125）。
- 公式 hooks リファレンスは、transcript が非同期に書かれ、遅れることがあると明記している（arch/hooks.md:736）。
- agent-console は端末へ文字を送れる。tmux の ac-* セッションには、同じユーザーの Bash から send-keys できる（architect-review H2）。`/api/agent/reservations`・`/api/agent/routines` は新しいセッションへ送る口で、今の会話への注入にはならない（ac-reserve.mjs:1, ac-routine.mjs:1）。
- rm -rf は、作業場所の中か /private/tmp/claude-501/ の下の絶対パスだけを外す。ABS_PATH_RE は `[A-Za-z0-9_./@%+,:=-]` だけで、日本語に一致しない。`$ * ? [ { ~` を弾くことで「変数・glob なし」を保証している（danger_sanitize.py:245, :248-260）。
- settings.json の worktree-only-guard の matcher は Write・Edit だけで、MultiEdit・NotebookEdit は無い（architect-review-2 N7 実測）。
- 会話記録は 1億バイトを超えるのが普通（上位5件 123〜170MB、architect-review-2 N2）。
- フックは AI が自分では書き換えられない。PO が `!` で反映する（recon.md:155-160）。

## 4. 変更後の仕組み

### 4-1 同意票の文法（AI が書く形）

PO への返事の本文（ツール呼び出しの中ではない）の、**最後の text ブロック**に次を書く。見やすさのためコードブロックで囲むことを推奨するが、判定の条件ではない（判定は行単位）。

```
[同意票]
操作1: <コマンド全文1行>
操作2: <コマンド全文1行>
```

- 見出しの行は `^\[同意票\]$`。操作の行は `^操作([1-9]|10): (.+)$`。最大10行。改行を含むコマンドは書けない（heredoc 入りは不可。スクリプトのファイルにして `bash <ファイル>` を操作にする）。
- 操作に `$` かバッククォートを含めたら、その操作は不可（PO が見た文字と実際の動きを揃えるため、L2）。ファイルを読む操作（`bash <file>`・`-f <file>`・`< <file>`）の中身は束縛しない（§7 R6）。
- 同じ text ブロックに、`1. 上の同意票の操作を実行する` で始まる行を必ず置く（後ろに【おすすめ】と「選ぶとどうなるか」を続けてよい）。実行番号は "1" に固定。
- PO には日常語で「何に・何をするか」を説明する。
- 1つの返事に同意票は1つまで。2つあれば無効（止まる）。

### 4-2 同意の判定（新しい部品 consent_check.py）

置き場所: ~/.claude/scripts/consent_check.py（試作 docs/handoff/conversation-consent/hooks/consent_check.py）。

呼び方（N8）: `python3 ~/.claude/scripts/consent_check.py < <フックの入力 JSON>`。部品は標準入力の JSON から `tool_input.command`（サニタイズ前の元の COMMAND）を自分で読む。通すときだけ標準出力に `allow` を出して終了コード 0。それ以外は標準出力に何も出さず終了コード 2（理由は agent-events.jsonl に書く）。中の関数 `check(hook_input: dict, command: str, now: datetime) -> tuple[bool, str]` が判定し、単体試験はこの関数を直接呼ぶ。例外が起きたら必ず False。

判定（すべて満たしたときだけ True。この順に見て、外れた時点で不可）:
1. hook_input に `agent_id` キーが無い（値が空でも、キーがあれば不可）。
2. transcript_path が、本物のホーム（環境変数 HOME ではなく pwd モジュールで引く。danger_sanitize.py:26 と同じ）の `.claude/projects/` の下の `.jsonl` である。Codex から来た入力はこの形にならないので必ず不可。
3. 記録の末尾 4MB を読む。読み始めが 0 でなければ、最初の改行までを捨てる。改行で終わっていない最後の1行は捨てる。それ以外に JSON でない行があれば不可。
4. 末尾から順に見て、**最後の人の入力 H** を探す。人の入力とは次のどれか（P1・P2、会話記録の実物の形）:
   - `type=="user"`・`origin.kind=="human"`（content の型は問わない。画像つきの入力は content が配列になる）
   - `type=="attachment"`・`attachment.type=="queued_command"`・`attachment.origin.kind=="human"`（attachment 行の最上位に origin は無い）
5. H が `type=="user"` かつ `promptSource=="typed"` かつ content が文字列であり、その前後の空白を除くと "1" と完全一致する（queued の「1」・配列の content は不可。貼り付け印は "1" と一致しないので自然に除かれる）。
6. H より前で最も近い、`type=="assistant"`・`isSidechain` が false の行を1行だけ見る（message.id でまとめない。会話記録の assistant 行は1行に1種類のブロックだけ）。その行のブロックが text でなければ不可。text なら、その中に、同意票の見出しの行がちょうど1つと、前後の空白を除いて `1. 上の同意票の操作を実行する` で**始まる**行がちょうど1つある（後ろに【おすすめ】などが付いてもよい、P4）。操作の行は見出しの行より後ろにあるものだけを数え、操作の前後の空白を除いて比べる（Q4）。その text ブロックから H までの間に、ほかの人の入力（4 の定義。queued を含む）も、compact の行（`isCompactSummary` か `type=="system"`・`subtype=="compact_boundary"`）も無い。末尾 4MB の中に H かその text ブロックが無ければ不可。
7. H の timestamp から `now` までが30分以内。
8. command の前後の空白を除いたものが、同意票のどれかの操作と完全一致し、その操作に `$`・バッククォートが無い。
9. 除外（§4-4）に当たらない。除外はコマンド全体に当てる。
   - 補足（Reviewer L5 で追認）: 見出しより後ろの操作の行が0件、または同じ操作番号が2回以上あれば不可（どちらも止める側）。
10. 台帳 ~/.claude/logs/consent-used.jsonl に、鍵（その text ブロックの sha256, H の timestamp, 操作番号）がまだ無い（L3: session_id を鍵に入れない）。照合と追記は、`fcntl.flock` で排他した中で行う（O_NOFOLLOW・所有者確認つき。permit_bridge.py:39-41 と同じ書き方）。追記できなければ不可。

通したら、agent-events.jsonl に `consent_consumed`（session・鍵・cmd_head）を1行書く。呼ばれるたびに `consent_probe`（session・H の uuid と timestamp・H が typed の "1" だったか・now。本文は書かない）も書く。K0 の判定がつくまで続ける（P5）。probe は判定の結果に関係なく finally で1行書き、H が無ければ uuid・timestamp は null。フック入力の `tool_use_id` も書く（フック入力にあるかは作るときに実物で確かめ、無ければ省く）。now と記録の timestamp はどちらも UTC の aware datetime で比べる（S3）。

### 4-3 部品を呼ぶ場所（agent-danger-hook.sh）

| 場所 | 今 | 変更後 |
|---|---|---|
| psql write（:127-152） | permit_bridge.py consume-ticket の結果が `consumed` なら通す、違えば exit 2 | consume-ticket が `consumed` でないとき、danger_ops と同じく consent_check.py に入力 JSON を渡し、`allow` なら exit 0。**permit_bridge.py は変えない**（N6） |
| 本店の破壊系 git（:302-346） | 許可券の照合、無ければ exit 2 | **変えない**（本店での git clean / stash / checkout -- / restore は同意の対象にしない） |
| danger_ops（:415-464） | 許可券の照合、無ければ hook_blocked ＋ exit 2 | 許可券が無いとき、consent_check.py に入力 JSON を渡す。`allow` なら exit 0。それ以外は今どおり hook_blocked ＋ exit 2 |

- 入力 JSON は、agent-danger-hook.sh:14 の `INPUT=$(cat)` を `printf '%s' "$INPUT" | python3 ~/.claude/scripts/consent_check.py` で渡す（Q1）。
- 通すときは exit 0 だけを返す。`permissionDecision: allow` は返さない（Claude Code 本体の判定はそのまま残す）。
- 試験のために、部品の場所を環境変数 CONSENT_CHECK で差し替えられる（既存の DANGER_SANITIZER と同じ型。Bash ツールからはフックの環境を変えられない、Reviewer L3 で追認）。
- 触らない範囲: permits-guard（:156-190）の位置と判定、danger_sanitize の呼び出し（:67-76）、worktree-only-guard の force push 判定（:124-126）、permit_bridge.py。

### 4-4 同意では通さない操作（除外。consent_check.py の中の正規表現の一覧）

コマンド全体に対して、どれか1つに当たれば不可。

| 正規表現（考え方） | 理由 |
|---|---|
| `git push` で、引数に `main` か `develop` の語（`HEAD:main`、`-u origin main` を含む）がある。語は部分一致で見るので `release/fix-main-menu` も当たるが、止まる側なので受け入れる | CLAUDE.md: main/develop への直接 push 禁止 |
| `git push` で、`--force`・`-f`・`--force-with-lease` があり、refspec（ブランチ名）が1つも無い（`git push --force origin` を含む） | 送り先のブランチが分からないため |
| `git push` に `--delete` か `:` で始まる refspec がある | 長命ブランチの消失防止 |
| `git reset --hard` | CLAUDE.md の不可逆操作 |
| `DROP DATABASE` | 戻せない |
| `clasp push` | ローカルからの clasp push は禁止（CI 経由、feedback_gas_clasp_local_push） |
| `\.claude/permits`、settings(\.local)?\.json（正規表現）、`\.claude/scripts/`、`\.codex/salesanchor/` | 見張り役そのものを弱める |
| `gh api` で `branches/.*/protection` か `rulesets` | Branch Protection・Ruleset |
| workflow-lint\.yml（正規表現） | CLAUDE.md の不可逆操作 |
| §4-5 の Bash の見張りの5条件（会話記録・`consent-used`・tmux の入力注入・osascript keystroke・`/chat/queue`） | psql の経路（:92-154）は permits-guard・§4-5・本店の破壊系 git より前で exit 0 するため、経路の順に関係なく同じ結果にする（P3） |
| `git clean`・`git stash`・`git checkout --`・`git restore`（agent-danger-hook.sh:238-241 と同じ4つの正規表現を、コマンド全体に re.search で当てる、S7） | 同上。本店の破壊系 git を同意の対象にしない方針（§4-3）を psql の経路でも守る（P3） |

- 今も検知していない操作（`gh api` の Ruleset 変更、settings の変更など）は、この設計では検知を足さない。除外に入れておくのは、将来検知語に入れたときに同意で通らないようにするため。
- main への直接 commit の停止（10件）は同意の対象にしない。作業場所で作業すれば起きない、AI 側の手順の誤りとして扱う。

### 4-5 偽造を防ぐ見張り（K7）

止めたときは、どの見張りも agent-events.jsonl に `consent_guard_blocked`（どの条件か・kind・cmd_head・cmd_sha・cmd_len。改訂1、§13）を1行書いてから exit 2。このうち偽造の疑い（kind が inject・write）の件数が R1 の見つける手段になる（§7）。

- Bash（agent-danger-hook.sh の permits-guard の直後に、同じ書き方で足す）: コマンドに次のどれかがあれば止める。
  - `.claude/projects/` と `.jsonl` の両方
  - `consent-used`
  - `tmux` と（`send-keys`・`paste-buffer`・`load-buffer`・`set-buffer` のどれか）
  - `osascript` と `keystroke`
  - `127.0.0.1` か `localhost` と `/chat/queue`
  - 止める文: 「会話記録・同意の台帳を Bash で触ることはできません。読むだけなら Read/Grep ツールを使ってください。突き合わせと K0 の目安は `python3 scripts/dev/consent-audit.py` を使ってください」
  - 読み取り専用の例外は作らない（N4: どちらでも R1 の水準は変わらず、規則が単純な方を選ぶ）。
- scripts/dev/consent-audit.py（新規・リポジトリ内）: 記録と台帳のパスをスクリプトの中で組み立てる（コマンドにパスが出ないので上の見張りに当たらない）。読み取りだけ。
  - `--probe <session_id>`: その会話の記録で最後の人の入力が見つかるか・時刻の差を出す（本文は出さない）。
  - `--audit`: 過去7日の consent-used の各鍵について、記録の中に対応する同意票と typed の「1」があるかを数える。`consent_guard_blocked` の件数も数える。
  - `--permissions`（`--audit` と併用）: §9 の4項目目。settings.json・settings.local.json の `permissions.allow` と `hooks`、~/.claude/permits の券を前回の写しと比べ、増減を出したうえで写しを更新する。値（秘密になりうる文字列）は出さず、項目名と件数だけを出す。
- Write・Edit・MultiEdit・NotebookEdit（worktree-only-guard.sh を対象に入れる。新しい判定は :43 の TOOL_NAME の直後、:45 の Write の判定より前に置く。Write の判定は :66 で exit 0 するため、後ろに置くと Write が漏れる、Q2）: 入力の `file_path` と `notebook_path` の両方を見る。小文字に揃えた realpath が、本物のホームの `.claude/projects/` の下の `.jsonl` か `.claude/logs/consent-used.jsonl` なら止める。
- settings.json: 既存の `Write`・`Edit` の登録（worktree-access-guard.sh と同居）は変えず、matcher `MultiEdit|NotebookEdit`・command は worktree-only-guard.sh だけの登録を**1件足す（必須、N7・Q2）**。追加は po-apply-consent.sh の中で行い、po-rollback-consent.sh が元に戻す。
- `/api/agent/reservations`・`/api/agent/routines` は見張らない（今の会話への注入にならないため、L5）。
- 文字列照合の水準で、悪意への完全な対策ではない（§7 R1）。

### 4-6 不要な停止の解消

- (a) rm -rf（danger_sanitize.py の rm_allowed・target_ok :248-301）:
  - 許可する根: `/tmp/CC報告ファイル/`、`/private/tmp/CC報告ファイル/`、`/private/tmp/claude-501/`（既存）、cwd の作業場所の根（既存）。根の側も対象の側も realpath してから（/tmp→/private/tmp）前方一致で比べる。根そのものは不可。
  - ABS_PATH_RE（:245）は、今の許可文字 `[A-Za-z0-9_./@%+,:=-]` に、**非ASCII文字（ord>127）だけ**を足す（N1）。`$ * ? [ ] { } ~ \ !` とバッククォート・空白・引用符は引き続き不可。
  - 相対パス: 同じ文字の検査を当てたうえで、コマンド全体に `cd`・`pushd`・`popd`・`(`・`bash -c`・`sh -c`・`eval` のどれも無いときだけ、`realpath(join(cwd, t))` が作業場所の根の下で、`.git` を含まなければ許可する。cwd は worktree-only-guard と同じく `tool_input.workdir` があればそれ、無ければフック入力の `cwd` を使う（Q5）。
  - 絶対・相対とも、対象の末尾が `/` のもの、およびコマンド全体に `re.search(r'\bln\b', コマンド全体)` が当たるものは不可（`/bin/ln` も当たる。`ls -ln` なども止まるが止まる側なので受け入れる。T8 に `/bin/ln -s ~ /tmp/CC報告ファイル/x && rm -rf /tmp/CC報告ファイル/x/y` を止める例、S2）（同じコマンドで作ったリンクを経由してリンク先を消す道を塞ぐ、Q7）。
- (b) pr-body-guard: 本文を同じコマンドの heredoc から読む仕組みは作らない。--body-file が読めないときの止める文（pr-body-guard.sh:154-158）を「本文ファイルを Write で先に作り、別のコマンドで gh を実行してください」に変える。あわせて docs/ai-agents/executor-checklist.md に同じ手順を1行足す。この停止は PO には上がらず、AI がやり直すだけ。
- (c) stop-log-digest.sh（.claude/hooks/stop-log-digest.sh :26-32, :100-125）。種別の一覧はこの設計で確定する（N9）:
  - 「止めた回数」= `hook_blocked` ＋ `consent_guard_blocked` の件数。`hook_blocked` を書くのは agent-danger-hook.sh・gh-scope-guard.sh・pr-body-guard.sh・worktree-only-guard.sh・launch_guard_for_sim.py・python-version-guard.py・mac-vm-guard.py（architect-review-2 N9 の grep 実測）。
  - 「ほかの見張りの記録（未分類）」= `gh_scope_blocked`・`worktree_bypass_blocked`・`main_repo_write_blocked`・`access_blocked`（worktree-access-guard.sh:108。上書き変数で通したときも記録が残るため、止めた回数には足さない、Q3）。書き手（node フック側か）と、1件の停止ごとの記録かが未確認なので、止めた回数には足さず別の行に種別ごとの件数で出す。
  - 「記録の行」= 上のどれにも当たらない種別（stop・start・danger_detected・*_consumed・*_allowed・consent_probe ほか）。danger_detected は検知の記録なので止めた回数に数えない。
  - 「前日の総ストップ件数」の行は「止めた回数」に置き換える。

### 4-7 返事の型と文書

- ~/.claude/CLAUDE.md の「POへのチャット」に1行足す: 「危険操作を聞くときは同意票（design §4-1）を返事の最後の text に書き、選択肢1の行を、太字などの飾りなしで `1. 上の同意票の操作を実行する` から書き始める（後ろに【おすすめ】と説明を続けてよい）」（S6）。ADR 承認後に Opus が編集する。
- リポジトリの CLAUDE.md:40（`scripts/permit-danger.sh` の行）に「会話の同意票でも可（ADR-1033、除外あり）」を足す（90行の上限内）。
- ADR-1033 に書くこと: ADR-1003:45 を参照し、許可券の代わりに同意票も使えるとする。同意票は ADR-136 の「GO #PR番号」の代わりにならない。「受け入れたリスク」に R1 と PO の受容の言葉・日付を書く。
- PO への案内に「『1』の後で取り消すときは Esc で止める」を書く（R2）。

## 5. 対象と対象外

- 対象（リポジトリ外・PO の `!` で反映）: ~/.claude/scripts/agent-danger-hook.sh、consent_check.py（新規）、danger_sanitize.py、pr-body-guard.sh、worktree-only-guard.sh、~/.claude/settings.json（既存の登録は変えず、matcher `MultiEdit|NotebookEdit`・worktree-only-guard.sh だけの登録を1件足すだけ、S1）。
- 対象（リポジトリ内）: docs/handoff/conversation-consent/hooks/（試作）、po-apply-consent.sh、po-rollback-consent.sh、scripts/dev/test-agent-hooks.sh（T1〜T10）、scripts/dev/consent-audit.py（新規）、.claude/hooks/stop-log-digest.sh、docs/ai-agents/executor-checklist.md（1行）、CLAUDE.md:40（1行）、ADR-1033、docs/adr/README.md（再生成）。
- po-apply-consent.sh のバックアップ対象は、上の「リポジトリ外」の全ファイルと ~/.codex/salesanchor/permit_bridge.py（変えないが、念のため写しを取る）。
- 対象外: permit_bridge.py の中身、agent-console の node フック、Claude Code 本体の自動判定、review-gate、permit-danger.sh 本体（残す）、extract-pr-body.py。

## 6. 代替案

| 案 | 採否 | 理由 |
|---|---|---|
| A 会話記録を読んで同意を判定（本案） | 採用 | PO の操作が「1」だけで済む。コマンド全文に束縛できる |
| B 設計承認チケット（design-approval-ticket 段3） | 不採用 | 設計ごとに PO の `!` が1回要る |
| C 危険語の検知をやめる | 不採用 | 本番データの削除が誰の確認もなしに通る |
| D 返事に同意票の ID を打ってもらう | 不採用 | 「1」だけで答えたい PO の希望に反する。§4-2 の6で取り違えを防ぐ |
| E pr-body-guard で同じコマンドの heredoc を読む | 不採用 | 書込みの重複・引用なし区切りなどで検査を逃れる道が増える。止まっても PO には上がらない |
| F UserPromptSubmit フックで、PO が送った時点の入力を別の台帳に記録し、それを H とする | 予備 | 記録の遅れ（K0）に左右されない。台帳が1つ増えるので、K0 が×になったときの戻り先にする（L6） |

## 7. リスクと対処

| # | リスク | 対処 |
|---|---|---|
| R1 | **受け入れるリスク（PO の受容が必要）**: AI が、文字を分けて組み立てるなどで §4-5 の見張りを逃れると、端末に「1」を送り込んだり記録に偽の行を足したりして、自分で同意を作れる。記録の突き合わせだけでは見分けられない | 文字列照合で止める（§4-5）。今の許可券も、AI が permit-danger.sh を実行すれば作れる水準（shell のフックに permit-danger.sh 実行の禁止が無いことは事実、recon.md:59。node フックと Claude Code 本体の自動判定がそれを止めるかは未確認）で、それより弱くはならない。**見つける手段**: `consent_guard_blocked` のうち偽造の疑い（kind が inject・write）が1件でも記録されたら、この仕組みを止めて（po-rollback-consent.sh）PO に報告する。週次の consent-audit.py --audit でこの件数を数える。なお agent-events.jsonl と consent-audit.py は AI が Write/Edit で書き換えられるので、見つける手段自体も消せる（受け入れるリスクの範囲、Q6） |
| R2 | 受け入れるリスク: PO が「1」の直後に取り消しを打っても、記録への書込みが遅れると見落として通る | 取り消すときは Esc で止める（Claude Code の中断）ことを PO への案内に書く |
| R3 | フックの時点で PO の返事が記録に無い | K0 で実測。×なら案 F に切り替える設計に戻す。無いときは止まるだけで、安全側に倒れる |
| R4 | サブエージェントの危険操作が止まる | 仕様どおり。Opus が実行する |
| R5 | 試作の不具合でフック全体が止まる | po-apply 方式（バックアップ→試験→不合格なら自動で戻す） |
| R6 | 受け入れるリスク: 操作が `bash <file>` などファイルを読む形のとき、「1」の後にファイルの中身を書き換えられる | 今の許可券と同じ水準（許可券もファイルの中身を束縛しない）。中身の束縛（sha256）は今回は入れない |
| R7 | 未確認: `--fork-session` などで同じ記録の行が別の会話に写ったときの扱い | 台帳の鍵に session_id を入れない（§4-2 の10）ので、写っても同じ鍵になり2回目は止まる |

戻し方: `! bash docs/handoff/conversation-consent/po-rollback-consent.sh`（po-apply が作るバックアップから全ファイルを戻す。settings.json の matcher も戻る）。

## 8. 実装の分け方（Sonnet へ）

- 便1: §4-2〜4-6(b) の試作、consent-audit.py、試験 T1〜T9、po-apply-consent.sh（settings.json の matcher 追加を含む）、po-rollback-consent.sh、ADR-1033、CLAUDE.md:40、executor-checklist.md。
- 便2: §4-6(c) stop-log-digest.sh（リポジトリ内だけ）と T10。
- PO の作業: R1 の受容（チャットで番号を答える）。便1のマージ後に `! bash docs/handoff/conversation-consent/po-apply-consent.sh` を1回打つ。
- K0 は反映後の本物の利用で測る（§2）。20回に届くまでは、Opus が agent-events.jsonl の `consent_probe` を consent-audit.py で数えて確かめる。

## 9. 維持の仕組み

- 担当: Opus。週次の保守（ADR-1011 の定期実行）に、`python3 scripts/dev/consent-audit.py --audit`（台帳と記録の突き合わせ、`consent_guard_blocked` の件数）と K11・K12 の集計を足す。`consent_guard_blocked` のうち偽造の疑い（kind が inject・write）が1件以上なら R1 の対処に従う。
- **権限の定期点検（PO の追加条件、2026-10-19）**: agent-console の定期実行に「同意と権限の週次点検」を1件登録し、毎週月曜 09:30 に点検用のセッションを開く。そのセッションは `python3 scripts/dev/consent-audit.py --audit --permissions` を実行し、次の4つを数えて前週と比べる。
  1. 同意で通った操作（consent_consumed）の件数と、そのうち記録に同意票と typed の「1」が見つからないもの（0件が正常）
  2. 偽造を防ぐ見張りが止めた件のうち偽造の疑い（consent_guard_blocked の kind が inject・write、0件が正常）。読み取りの空振りは参考の件数で異常にしない
  3. 許可券の発行・消費の件数（danger_permit_consumed ほか）
  4. 権限の設定の増減: ~/.claude/settings.json と settings.local.json の `permissions.allow`・`hooks` の登録、~/.claude/permits の券を、前回の写し（~/.claude/logs/permission-snapshot.json。consent-audit.py が書く）と比べて、増えた・消えたものの一覧
  - 1・2 が1件以上、または 4 に PO の承認記録（ADR・PR）で説明できない増減があれば、点検セッションが PO に報告する（3行型）。1・2 が1件以上なら、あわせて R1 の対処（仕組みを止める案）を選択肢に出す。異常が無ければ報告しない（結果は /tmp/CC報告ファイル/consent-weekly/ に残す）。
  - 登録は便1の反映後に Opus が agent-console の定期実行の公式手順（ac-routine）で行う。サブエージェントは agent-console のパスを触れないため、Opus が行う。
  - K13: 登録後の最初の月曜に点検セッションが開き、/tmp/CC報告ファイル/consent-weekly/ に4項目の結果が書かれていれば○。
- 試験は scripts/dev/test-agent-hooks.sh に入り、po-apply のたびに走る。
- **試験の記録と本物の検知を分ける（Reviewer M3）**: `--real-home` の試験は見張りをわざと当てるので、本物の agent-events.jsonl に consent_guard_blocked が書かれる。test-agent-hooks.sh は `--real-home` のとき、開始時に ~/.claude/logs/consent-selftest-windows.jsonl へ `{"start": <UTC>}` を、終了時（trap EXIT）に `{"end": <UTC>}` を1行ずつ書く。consent-audit.py --audit は、start と end がそろい長さが30分以内の区間に入る consent_guard_blocked を「試験の区間の件数」として別に数え、2 の判定（0件が正常）からは除く。区間の数と除いた件数は毎回の結果に出す（PO の反映の回数と合わない区間があれば異常として報告する）。区間の台帳も AI が書けるので、改ざんの水準は R1・Q6 と同じ。
- 守り手: scripts/dev/test-agent-hooks.sh（po-apply のたびに T1〜T9 を走らせ、1件でも不合格なら反映を戻す）

## 10. 外部・過去事例の参照と我々への応用

該当事例なし。会話記録を同意の根拠にする公開事例は、今回の調査では探していない。根拠は Claude Code 公式の hooks リファレンス（common input の transcript_path・agent_id、transcript の非同期書込み、UserPromptSubmit。code.claude.com/docs/en/hooks、2026-10-19 確認）だけ。成功は K0〜K12 の実測で判定する。

## 11. 設計審査

- 1回目: Architect（Opus サブエージェント）REVISE。HIGH 6・MEDIUM 8・LOW 5（architect-review.md）。
- 2回目: REVISE。HIGH 1（N1）・MEDIUM 8（N2〜N9）・LOW 6（architect-review-2.md）。R1 は PO の受容と2条件つきで受け入れてよいとの判定。
- 3回目: REVISE。HIGH 0・MEDIUM 5（P1〜P5）・LOW 7（Q1〜Q7）（architect-review-3.md）→ 第4版で全件反映。
- 4回目: **APPROVE**（HIGH 0・MEDIUM 0・LOW 7、architect-review-4.md、Ready For Generator: true）。LOW S1〜S7 は第5版で反映。便1のマージは R1 の PO 受容を ADR-1033 に書いた後。
- 便1の実装審査（Reviewer、/tmp/CC報告ファイル/conversation-consent/reviewer-bin1.md）: REVISE（MEDIUM 3・LOW 7）。第6版で、M1 は設計どおり部分一致に戻す（審査中に Opus が出した完全一致への変更は撤回。`HEAD:heads/main` のような短縮形を逃すため）、M2 は main を取り込み README を再生成、M3 は §9 の試験区間の分離、L3・L5 は本文に追認として追記。

## 12. 審査指摘の反映表

| 指摘 | 反映先 |
|---|---|
| H1 古い同意票 | §4-2 の4〜6 |
| H2 端末への注入 | §4-5（Bash の見張り）、§7 R1（PO の受容） |
| H3 Write/Edit の置き場所 | §4-5、§5 |
| H4 cd と相対パス | §4-6(a)、K8 |
| H5 排他 | §4-2 の10、K2 |
| H6 粒度 | §4-1 文法、§4-2 部品、§4-3 表、§4-4 一覧 |
| M1 除外 | §4-4 |
| M2 根と日本語 | §4-6(a)、K8（N1 で補正） |
| M3 heredoc | §4-6(b)、§6 E |
| M4 Codex | §4-2 の2（N6 で補正） |
| M5 文書 | §4-7 |
| M6 書込みの遅れ | K0、§7 R2・R3（N5 で補正） |
| M7 二重計上 | §4-6(c)、K10（N9 で補正） |
| M8 票の読み場所 | §4-1、§4-2 の6（N3 で補正） |
| L1〜L5（1回目） | §4-2、§4-6(b) |
| N1 ABS_PATH_RE | §4-6(a)（非ASCIIだけ足す・根も realpath）、K8、T8 |
| N2 末尾読み | §4-2 の3、K5、T5 |
| N3 queued と票の位置 | §4-1（最後の text ブロック）、§4-2 の4〜6、K5 |
| N4 見張りの止めすぎ | §4-5（consent-audit.py・止める文）、§9 |
| N5 K0 の測り方 | K0、§4-2（consent_probe）、§8 |
| N6 permit_bridge | §3、§4-3、§5（変えない） |
| N7 matcher | §4-5、§5、§7 戻し方 |
| N8 呼び方 | §4-2 冒頭、§4-1（コードブロックは条件でない） |
| N9 種別一覧 | §4-6(c)、K10 |
| L1 refspec | §4-4 |
| L2 `$` とファイル | §4-1、§4-2 の8、K6、§7 R6 |
| L3 鍵 | §4-2 の10、§7 R7 |
| L4 K11 の対象 | K11 |
| L5 `~` とreservations | §4-2 の2、§4-5、§3 |
| L6 UserPromptSubmit | §6 F |
| R1 の2条件 | 状態行、§4-7、§7 R1、§9 |
| P1 queued の origin の位置 | §4-2 の4。T5 の偽の記録は実物の行のキーの組を写して作る |
| P2 画像つきの入力 | §4-2 の4・5。T5 に「1 の後に画像つきの入力」の例を足す |
| P3 psql の経路の素通し | §4-4（除外に2行追加） |
| P4 【おすすめ】との衝突 | §4-1、§4-2 の6（行頭一致）。T1 に【おすすめ】つきの例を入れる |
| P5 K0 の遅れの見分け | K0、§4-2（consent_probe の項目） |
| Q1〜Q7 | §4-3、§4-5、§4-6(a)(c)、§4-2 の6、§7 R1 |

## 13. 改訂1: 見張りの「異常」の数え方を、偽造の疑いと読み取りの空振りに分ける（2026-10-26）

状態: 設計案（Opus 作成・自己審査済み、§13-9）。PO が「異常と数えるのを書き足しと送り込みだけに絞る設計の直しを作る」を選択（2026-10-26 週次点検の報告への返事「1」）。実装は PO の実装承認の後。止め方（§4-5 の止める条件）は変えない。

### 13-1 目的（PO の選択）

- 週次点検の「異常」を、同意の偽造につながる操作（記録・台帳への書き足し、端末への「1」の送り込み）が見張りに当たったときだけにする。
- 読むだけで止められた件（空振り）は、引き続き止めるが、異常に数えず参考の件数として出す。

利用者に見える変化:
- 前: AI が調べ物で会話の記録を読むたびに数が増え、毎週「異常」の報告が PO に届く（2026-10-26: 56件、偽造の形は0件）。
- 後: 偽造の疑いが1件以上の週だけ PO に報告が届く。空振りの件数は保存ファイルにだけ出る。

### 13-2 現状（観測事実）

- 2026-10-19〜10-26 の consent_guard_blocked は69行。13行が試験の区間内、残り56行（transcript 52・consent-used 4）。区間外に tmux-inject・osascript-keystroke・chat-queue・transcript-or-ledger-write は0行（~/CC報告ファイル-keep/consent-weekly/20261026-guard-blocked-analysis.md、同 -raw.txt）。
- 記録の項目は ts・type・hook・condition・cmd_head（先頭120字）だけ（docs/handoff/conversation-consent/hooks/agent-danger-hook.sh:60-93）。Bash の条件 transcript・consent-used は、読み取りと書き込みを区別しない（同:242-255）。
- consent-audit.py の分け方は時刻（試験の区間）だけ（scripts/dev/consent-audit.py:187-200）。異常は `abnormal = unmatched > 0 or guard_real > 0 or n_reasons > 0`（同:1021）。
- 週次点検の指示文は「2 の consent_guard_blocked が1件以上なら異常」（docs/handoff/permission-delegation/routine.json:12）。前回の結果を /tmp から読むため、/tmp が消えると比べられない（2026-10-26 に発生）。
- 点検中の Opus 自身の集計コマンドと記録の書き出しも、文字列に記録のパスを含んだだけで2回止められた（2026-10-26）。

### 13-3 変更後の仕組み

(a) 見張りの記録に「種類」を足す（hooks/agent-danger-hook.sh の _consent_guard_log、hooks/worktree-only-guard.sh:67）。止める条件・止める文・exit 2 は変えない。

| condition | kind | 異常に数えるか |
|---|---|---|
| tmux-inject・osascript-keystroke・chat-queue | `inject` | 数える |
| transcript-or-ledger-write（Write・Edit・MultiEdit・NotebookEdit） | `write` | 数える |
| transcript・consent-used で、下の「書き込みの形」に当たる | `write` | 数える |
| transcript・consent-used で、書き込みの形に当たらない | `read` | 数えない（参考） |

- 書き込みの形（Bash。迷う形は `write` 側に倒す）: 次のどれか1つでも当たれば `write`。
  1. `>`・`>>`・`>|`・`tee`（`-a` を含む）の書き先の語に `.claude/projects/` か `consent-used` を含む。
  2. `sed -i`・`perl -i`・`cp`・`mv`・`dd`・`truncate`・`rm`・`ln`・`install`・`rsync`・`touch`・`chmod` が語としてあり、コマンド内に `.claude/projects/` か `consent-used` がある。
  3. `python`・`python3`・`node`・`perl`・`ruby` の行内コード（`-c`・`-e`・heredoc）に `.claude/projects/` か `consent-used` があり、かつ `open(` に `'w'`・`'a'`・`'x'`・`+` のどれか、`.write(`・`write_text`・`write_bytes`・`writeFile`・`appendFile`・`os.replace`・`os.rename`・`shutil.` のどれかがある。
  4. `cd` の行き先に `.claude/projects/` を含み、同じコマンドに 1〜3 の書き込みの語（書き先は問わない）がある。
- 4000字を超えるコマンドは調べずに write とする（判定の時間切れを防ぐため。2026-10-26 審査 HIGH-1）。判定には1秒の時間の上限を付け、超えたら write とする（2026-10-26 再審査）。
- 足す項目: `kind`（上の表）、`cmd_sha`（マスク前のコマンド全文の sha256 先頭16桁）、`cmd_len`（文字数）。cmd_head は今のまま（マスク・120字）。
- 書き込みの形の判定は、§4-5 と同じく文字列照合の水準（R1 の範囲）。判定の関数は consent_check.py に置かず、agent-danger-hook.sh の CONSENT_GUARD の python の中に足す（新しいファイルを増やさない）。

(b) consent-audit.py --audit の2行目を分ける（scripts/dev/consent-audit.py:187-200 count_guard_split、:1009-1010 の出力、:1021 の異常）。

- 出力の形（1行のまま）: `2. consent_guard_blocked: 疑い <S> 件（0件が正常）／読み取りの空振り <R> 件（参考）（試験の区間 <W> 個・区間内で除いた件数 <I>）`
- 疑い S = 試験の区間外で、kind が `inject`・`write` のもの。kind が無い旧形式の行は、condition が inject 系・transcript-or-ledger-write なら疑い。Bash の旧形式は cmd_head に (a) の書き込みの形を当て、当たれば疑い、当たらなければ空振り。
- 読み取りの空振り R = 試験の区間外で、kind が `read`（旧形式で書き込みの形に当たらない Bash を含む）。
- 異常: `abnormal = unmatched > 0 or guard_suspect > 0 or n_reasons > 0`。R は異常に使わない。
- 疑いが1件以上のときは、その行の ts・hook・condition・cmd_sha・cmd_len を `GUARD_SUSPECT=` の行で1件ずつ出す（cmd_head は出さない）。
- 既存の行の形（`PERMISSION_CHANGES=`・`REVIEW_DUE=`・`ABNORMAL=`）は変えない（permission-delegation/design.md:207）。

(c) 週次点検の指示文（docs/handoff/permission-delegation/routine.json:12 と、agent-console に登録済みの同じ定期実行）。

- 手順3の判定「2 の consent_guard_blocked が1件以上なら異常」を「2 の『疑い』が1件以上なら異常」に変える。
- 前回の結果は ~/CC報告ファイル-keep/consent-weekly/ の1つ前のファイルから読む（/tmp は消えるため）。
- 手順7の「同意票関連の異常」は、1行目の不一致か2の疑いのこと、と書き直す。

(d) 文書: §4-5 の冒頭、§7 R1 の「見つける手段」、§9 の 2 と冒頭の担当の行、ADR-1033 の「見つける手段」（:42）と「維持の仕組み」（:56-57）の「consent_guard_blocked が1件でも」を「consent_guard_blocked のうち偽造の疑い（kind が inject・write）が1件でも」に変える。ADR 変更後は `node scripts/generate-adr-index.js`。

### 13-4 対象と対象外

- 対象（リポジトリ内）: hooks/agent-danger-hook.sh・hooks/worktree-only-guard.sh（試作）、scripts/dev/consent-audit.py、scripts/dev/consent-unit-tests.py、scripts/dev/test-agent-hooks.sh、docs/handoff/permission-delegation/routine.json、本書、ADR-1033、docs/adr/README.md（再生成）。
- 対象（リポジトリ外・PO の `!` で反映）: ~/.claude/scripts/agent-danger-hook.sh・worktree-only-guard.sh（po-apply-consent.sh で写す。§13-10 で `--update` を足す。初回の流れは変えない）。agent-console の定期実行の指示文は Opus が公式手順で書き換える（§9 と同じ。サブエージェントは触らない）。
- 対象外: 止める条件と止める文（§4-5）、consent_check.py、settings.json、po-rollback-consent.sh、既にある agent-events.jsonl の行（書き換えない）。読み取りを止めないようにする変更（PO は数え方だけを選んだ。N4 の判断は維持）。

### 13-5 代替案

| 案 | 採否 | 理由 |
|---|---|---|
| A 記録に kind を足し、点検で疑いと空振りを分ける（本案） | 採用 | 止め方を変えずに数え方だけ直せる。旧形式の行も cmd_head で分けられる |
| B 点検だけで cmd_head（120字）から分ける | 不採用 | 120字の後ろの書き込みを見落とす（2026-10-26 の調査で未確認として残った点）。A は全文で判定する |
| C 読み取りは止めない（例外を作る） | 不採用 | PO が選んだのは数え方の直し。N4 の判断（規則が単純な方）を変える理由が出ていない |
| D 今のまま、毎週 Opus が中身を見て報告 | 不採用 | 毎週 PO に報告が届き、本当の疑いが埋もれる |

### 13-6 リスクと対処

| # | リスク | 対処 |
|---|---|---|
| R8 | 書き込みの形の判定を、文字を分けるなどで逃れると、疑いが空振りに数えられる | R1 と同じ水準（受け入れ済みの範囲。止め方は変わらないので、止まること自体は今と同じ）。迷う形は write 側に倒す。空振りの件数も毎週出すので、急に増えれば Opus が気づける |
| R9 | 書き込みの形が広すぎて、/tmp へ書き出すだけの python も疑いになる | 疑いの行は cmd_sha・cmd_len で特定でき、Opus が中身を確かめて PO に報告する。K16 で件数を測り、多ければ判定を直す改訂を出す |
| R10 | 反映前後の旧形式の行を、cmd_head だけで空振りと数える | 旧形式は反映後7日で点検の期間から外れる。反映後最初の点検の結果に、旧形式の件数を併記する |

戻し方: リポジトリ側はこの PR の revert。フックは `! bash docs/handoff/conversation-consent/po-rollback-consent.sh`（反映時のバックアップへ戻す）。kind が無い記録も (b) で読めるので、フックだけ戻しても点検は動く。

### 13-7 成功条件

| # | 基準 | 検証方法 |
|---|---|---|
| K14 | 見張りに当てたとき、記録の行に kind・cmd_sha・cmd_len が入り、kind が §13-3(a) の表どおり | test-agent-hooks.sh T7 を拡張: 読み取り例（`grep x <記録のパス>`）→ read、書き込み例（(a) の1〜4 の各1件以上、`>>`・`tee -a`・`sed -i`・python の `open(...,'a')`・`cd` の後の `>`）→ write、tmux 等 → inject、Write/Edit → write。全件一致で○ |
| K15 | consent-audit.py --audit が、疑いと空振りを分けて出し、空振りだけの週は ABNORMAL=no | consent-unit-tests.py: (1) read 3件だけ → ABNORMAL=no・疑い0・空振り3 (2) write 1件 → ABNORMAL=yes・GUARD_SUSPECT=1行 (3) 旧形式の Bash で cmd_head に `>> ~/.claude/projects/x.jsonl` → 疑い (4) 旧形式の Bash で `grep x ~/.claude/projects/y.jsonl` → 空振り (5) 試験の区間内の write → 除外。全件一致で○ |
| K16 | 反映後最初の週次点検で、疑い0件・ABNORMAL=no（ほかの理由が無い場合）。疑いが出たら、全件を Opus が cmd_sha で特定し本物か空振りかを報告 | 週次点検の保存ファイル（~/CC報告ファイル-keep/consent-weekly/） |
| K17 | 週次点検が前回の結果を ~/CC報告ファイル-keep/consent-weekly/ から読み、試験の区間の数を比べられる | 反映後最初の点検の結果に、前回のファイル名が書かれていれば○ |

### 13-8 実装の分け方（Sonnet へ・1便）

- 便R1: §13-3(a)(b)(d) と routine.json:12（(c) のリポジトリ側）、試験 K14・K15。PR 1本。フックのパスを含むため、マージ後に PO が `! bash docs/handoff/conversation-consent/po-apply-consent.sh --update` を1回打つ（試験が不合格なら自動で戻る。§13-10）。
- 反映後に Opus: agent-console の定期実行の指示文を routine.json と同じに書き換える（ac-routine の公式手順）。K16・K17 は次の月曜の点検で測る。

### 13-9 設計審査（Opus の自己審査。独立した第二者の審査ではない）

判定: APPROVE（HIGH 0・MEDIUM 0・LOW 2）。
- 整合: 止める条件（§4-5・K7）を変えないので T1〜T9 の既存の期待は変わらない（T7 は件数の期待 7・6 を保ち、項目の確認を足すだけ）。ABNORMAL 系の行の形を変えない（permission-delegation/design.md:207）。R1 の受容の範囲を広げない（判定の文字列照合は R1 と同じ水準・R8）。
- 根拠: 56件の内訳と条件は保存した生データ、行番号は origin/main 900afee29 の worktree で確認。
- 検証可能性: K14・K15 は試験で○×、K16・K17 は保存ファイルで○×。
- LOW-1: 書き込みの形 3 の語の一覧は網羅でない（R8・R9 で受け入れ、K16 で測る）。
- LOW-2: agent-console の定期実行の指示文は agent-console 側にも写しがあり、二重管理になっている（今回は routine.json を正にして写すだけ。二重管理の解消は対象外）。
- 未解決の前提: なし。PO の判断が要るのは実装の承認と、反映（po-apply-consent.sh）の実行の2点。

### 13-10 反映の道の追加: po-apply-consent.sh `--update`（2026-10-26・設計の入れ忘れの補い）

- 観測事実: 便R1（#4779）のマージ後、PO が引数なしで po-apply-consent.sh を打ったところ、「反映済み（consent_check.py が既にある）。何も変更しません。」で終わった（同スクリプト :24-27 は初回専用）。手元の agent-danger-hook.sh・worktree-only-guard.sh は #4779 の前の版のまま（afbd1dc61^1 と一致）、残る3ファイルは試作と一致。§13-4 の「中身は変えない」は、2回目以降の入れ替えの道が無いことを見落とした設計の入れ忘れ。
- 判断（Opus・ADR-1003 の範囲）: PO が承認した成果は「便R1 の見張りが手元に入ること」。`--update` はその成果を届ける手段で、見張りの止める条件・settings.json・同意の台帳を変えない。設計の外へ出る変更ではないため、PO への再承認は求めず記録する。
- `--update` の流れ: 前提の確認（初回と同じ＋consent_check.py が無ければ「初回は --update なしで」と exit 1）→ バックアップ（5ファイル・settings.json・permit_bridge.py）→ 試作の試験 → 試作と本物で中身が違うファイルだけ入れ替え（0件なら「差なし」で exit 0）→ settings.json は触らない → 本物の試験 → 不合格なら入れ替えたファイルだけバックアップから戻す（戻せなければ exit 3）。po-rollback-consent.sh は consent_check.py を消すため使わない。
- 対象外: 引数なしの初回の流れ、po-rollback-consent.sh、settings.json。
- 成功条件: K18 偽の HOME で (a) 差あり→入れ替えて合格 (b) 差なし→何も変えない (c) consent_check.py 無し→exit 1 (d) 本物の試験が不合格→入れ替えた分だけ戻る (e) 引数なし→従来どおり、が全件 PASS。K19 PO の実行後、~/.claude/scripts の2ファイルが試作と cmp で一致し、本物の試験が合格。
- 戻し方: スクリプトはこの PR の revert。反映後のフックは、実行時に出るバックアップのフォルダから2ファイルを戻す。

## 14. 改訂2: 件の窓へ、決まった一文だけを送る口（case-say）（2026-11-05）

状態: 設計案 第6版（§14-10。サーバー側で宛先を決める形）。6回目の審査の前。PO 承認前。実装・反映は PO の実装承認の後。§14-3〜14-8 の第5版（手元の部品 case-say.py）は採用しない（§14-9 の判断）。§14-1・14-2 の目的と観測事実は第6版でも使う。
向きの決定: PO 2026-11-05、選択肢「2. 作業画面アプリの裏側で件の窓を確かめる形に作り直す」に「2」と回答（作業画面アプリ = PO の Mac の agent-console。Sales Anchor 本番のサーバーではない）。
きっかけ: PO 2026-11-05、選択肢「2. 私が打てるように見張りを見直す設計から始める（しんごさんの手間は減ります。ただ見張りを弱めることになるので、別の設計と審査が要り、試験は先になります）」に「2」と回答。

### 14-1 目的と、見える変化

- 目的: Discord の件のセッション（agent-console の役割 discord-case）の試験で、段階ごとの指示の一文を Opus が送れるようにし、PO の打ち込みを無くす。§4-5 の偽造を防ぐ見張りの水準は下げない。
- 前: 試験の段階ごとに、PO が件の窓へ「<置き場>/<ファイル> を読み、書いてある手順を順に行ってください。」を打つ（前の手順書で7回）。
- 後: Opus が `python3 ~/.claude/scripts/case-say.py <件の id> <手順ファイル名>` を1行打つと、その件の窓にだけ、決まった形の一文が入る。PO は件をアプリで開くだけ。

### 14-2 現状（観測事実）

- §4-5 の Bash の見張りは、コマンドの文字に `tmux` と `send-keys` 等があれば止める（docs/handoff/conversation-consent/hooks/agent-danger-hook.sh:256-257）。目的は AI が端末へ「1」を送り込んで同意を作ること（§7 R1、ADR-1033:21・:34）を防ぐこと。
- 2026-11-04 の件の受入で、Opus から件の窓への tmux の送信がこの見張りで止まった。言い換えず PO が打った（~/kb/04-records/cloud-case-ai-20261030/164-room-retest/10-v0501-acceptance.md:29）。
- 件のセッションは同意票を使わない・作らない（agent-console docs/handoff/discord-pdca/design.md:12）。件の窓で「1」が打たれても、同意の判定（§4-2）は Opus の会話記録だけを見るので、Opus の同意にはならない（§4-2 の 2・4〜6）。
- 予約（ac-reserve）で件を開いて指示を渡す道は、作りで閉じている: 件の役割は `reservable:false` が必須（agent-console server/config.ts:160-161）、reserveRoles に入れられない（同 :317-319）、起動の入口でも拒む（server/launch.ts:48）。
- 画面のチャットの送信口（/chat/queue）は認証の内側（server/chat-routes.ts:31）。サーバー秘密かセッショントークンが要る（server/auth.ts:63）。Opus はどちらも持たず、秘密を読むことは禁止なので使わない。
- サーバーは、端末へ人の指示を入れてよいかを `claude agents --json` の行で判定する: status が idle で waitingFor が無いときだけ（server/agents.ts:76-88）。waiting のとき Enter を送ると、許可の確認の既定の選択肢を押す恐れがある（同 :76-77 の注釈）。行には pid・status・sessionId・waitingFor がある（同 :36-47）。
- 開いているセッションの台帳 dataDir/open-sessions.json の件の項目には branch・claudeSessionId・cwd・id・name・roleId がある（10-v0501-acceptance.md:22）。端末は tmux のソケット `-L agent-console` のセッション `ac-<id>`（agent-console docs/handoff/discord-pdca/room-design.md:25）。
- 件の置き場 R は `/private/tmp/CC報告ファイル/discord-case/<id>`（server/case-sandbox.ts:62、tmp は realpath）。
- 部屋の中から `tmux -L agent-console` への接続は失敗する（room-design.md:25 の G7。11/04 の受入で部屋は有効）。
- Opus の Bash から `claude agents --json` は動く（2026-11-05 実測: exit 0・12行・全行に sessionId・status は busy 8／idle 4。キーは cwd・kind・name・pid・sessionId・startedAt・status。件は開いていない時点）。
- （第2版で追加）件の Claude は `claude agents --json` の行で見分ける作りになっていない。サーバーは件の会話の番号を、件の設定の置き場 CH = `<dataDir>/case-home/<id>`（server/case-sandbox.ts:66）の `sessions/<pid>.json` から、件の端末の子孫の pid だけで読む（server/case-agents.ts:38-42、server/hub.ts:659-676）。ふつうの agents の行に同じ番号があれば、件の番号を外す（server/hub.ts:674）。
- （第2版で追加）サーバーは端末とプロセスを、tmux の窓の pid の子孫で結ぶ（server/process-tree.ts:40、server/hub.ts:323）。台帳の番号では結ばない。
- （第2版で追加）件の作業場所 W は `<H>/worktrees/discord-cases/<id>`（server/case-clone.ts:46-48、server/case-sandbox.ts:61）。
- （第2版で追加）`~/.claude/sessions/<pid>.json` のキー（2026-11-05 実測・24個のうち1つ）: status・pid・sessionId・cwd ほか。status の値は idle 5・busy 1・shell 6。同じ時に `claude agents --json` は idle 5・busy 7。待ちの印（wait を含むキー）は、どちらにも無かった（その時に待ちのセッションが無い）。
- （第2版で追加）`CLAUDE_CONFIG_DIR` を空の置き場にして `claude agents --json` を手元で試そうとしたが、local-agent-guard に止められた。言い換えて試していない。
- （第3版で追加）`ps -o pid=,comm=` で、手元の `~/.claude/sessions/<pid>.json` の pid のうち生きている8つは、どれも comm が `claude`（2026-11-05 実測）。実行ファイルの場所を `lsof -d txt` で確かめようとしたコマンドは、`claude` の語を含むため local-agent-guard に止められた。言い換えて試していない。
- （第5版で追加）件の端末の起動の命令は、agent-console の設定で `["/bin/zsh", "-c", "source \"$AC_CASE_SHELL\" && ccdiscordcase"]` と決まっている（agent-console agent-console.config.json:47、つなぎ直しは :48）。サーバーはこの命令で tmux の窓を作る（server/sessions.ts:379 で役割の command を渡し、:704 の newSession で作る）。tmux の窓の起動の命令（`#{pane_start_command}`）は、窓を作った時に決まる。後から変えるには tmux の命令で窓の中身を入れ替える必要があり、そのときは中で動いている本体が止まる。
- 未確認: 件の `CH/sessions/<pid>.json` が、件の入力待ちで status=idle になり、作業中と許可の確認の待ちで idle 以外になるか。件の Claude の OS 上の作業場所（cwd）が W か。部屋（sandbox-exec から exec）で動く件の本体の comm が `claude` か。件の pane_pid が本体そのものか、その間にあるプロセスの作業場所がすべて W か（第4版）。`tmux display -p '#{pane_start_command}'` が件の窓で返す文字の正確な形（第5版）。§14-7 の K20 で最初に測る。

### 14-3 変更後の仕組み

(a) 新しい部品 `case-say.py`（試作 docs/handoff/conversation-consent/hooks/case-say.py、本物 ~/.claude/scripts/case-say.py。PO の `!` の po-apply-consent.sh `--update` で写す）。

- 呼び方: `python3 ~/.claude/scripts/case-say.py <件の id> <手順ファイル名>`。送る文を引数で渡す手段は作らない。
- 送る文は部品が組み立てる1種類だけ: `<R>/<手順ファイル名> を読み、書いてある手順を順に行ってください。`（R は 14-2 の置き場）。任意の文は送れない。文には数字が入る（R の中の件の id・手順ファイル名）が、文が「1」だけになることはなく、必ず決まった前後の文字がつく（第3版で言い方を直した。2回目の審査 MEDIUM）。
- 置き場の決め方: dataDir は agent-console の既定の場所 `~/Library/Application Support/agent-console`（agent-console README.md:314）、H は自分のホームを部品の中で組み立てる。W の比べ方（第5版・4回目の審査 MEDIUM）: W の期待値は `realpath(H)` に `/worktrees/discord-cases/<id>` をつないだ文字とし、W 自体は realpath にしない。W を lstat して、リンクでなく自分が持ち主のフォルダであることを確かめる。OS が返す作業場所（lsof の n 行）は、この文字と完全一致で比べる。dataDir の realpath が無いときは断る。設定で dataDir を変えた Mac には対応しない（断る）。
- 宛先は、書き換えられる台帳ではなく、OS が返す事実で結ぶ（第2版。審査 HIGH の直し）。台帳（open-sessions.json）は補助の確認にだけ使う。
- 判定（この順。外れたら何も送らず exit 2、理由を標準エラーと agent-events.jsonl の `case_say_refused` に書く。第3版で、状態を見る判定2〜4を最後に回し、その直後に文字を入れる形にした）:
  1. 件の id が UUID の形（小文字の16進と `-`）。手順ファイル名が `^[A-Za-z0-9._-]{1,64}\.md$` で、`..` を含まない。止めの印 `<dataDir>/case-say-blocked/<id>` が無い（判定後の送り方を参照）。
  ※ 下の判定6・5を先に行い、判定2〜4は最後に行う（番号は第2版のまま）。
  2. 窓の起動の形と pid: （第5版・4回目の審査 HIGH の直し。本線）`tmux -L agent-console display -p -t =ac-<id> '#{pane_start_command}'` が、件の起動の命令（14-2 の agent-console.config.json:47 の形。K20 で測った正確な文字を部品に固定で持つ）と完全一致する。合わなければ断る（理由 `pane_not_case_start`）。Opus の窓や、ほかのふつうの窓は、この命令で起動していないので断られる。続けて `tmux -L agent-console display -p -t =ac-<id> '#{pane_pid}'` が正の整数を1つ返す。子孫の pid の集合 F を `ps -axo pid=,ppid=` から作る（server/process-tree.ts:40 と同じ作り）。（第3版・2回目の審査 HIGH の直し）同じ `ps` の結果から、部品自身の pid とその祖先（ppid をたどって pid 1 まで）を集め、1つでも F に入っていたら断る（理由 `caller_in_case_pane`）。Opus が自分の窓の id を渡し、CH・W・状態ファイル・台帳を偽って `cd W` から部品を呼んでも、部品は自分の窓の子孫なのでここで断られる。ただし、部品を親から切り離して呼ぶ（二重の後ろ起動・nohup・setsid）と祖先が pid 1 に変わり、この確かめは外せる（3回目の審査 HIGH）。そのため祖先の確かめは補助とし、本線は次の「根の作業場所」とする。
     （第4版・3回目の審査 HIGH の直し）根の作業場所: 窓の pane_pid の OS 上の作業場所（`lsof -a -p <pane_pid> -d cwd -Fn`）の realpath が W と一致し、かつ pane_pid から P までの親子の道（P から ppid をたどって pane_pid に着くまで）にあるすべての pid の作業場所も W と一致する。合わなければ断る（理由 `pane_root_not_case`）。Opus の窓の pane_pid は Opus の作業場所で起動した本体（か、それを起動したシェル）なので、ふつうは W にならない。ただし Opus が自分の作業場所のフォルダを W の名前へ移す（mv）と、OS の上では W に見える（4回目の審査 HIGH）。そのため根の作業場所は補助とし、本線は上の起動の形とする（第5版）。
  3. 件の本体 P: F の中で、`CH/sessions/<pid>.json` がある pid がちょうど1つ（CH = `<dataDir>/case-home/<id>`）。その pid の OS 上の作業場所（`lsof -a -p <P> -d cwd -Fn` の n 行）の realpath が W（`<H>/worktrees/discord-cases/<id>`）と一致する。（第3版）P の `ps -o comm= -p <P>` が `claude` と完全一致する（補助。名前は実行ファイルを写せば真似られるので、本線は判定2の根の作業場所）。
  4. 状態: `CH/sessions/<P>.json` を O_NOFOLLOW で開き、通常のファイルで、JSON の pid が P と一致し、status がちょうど `idle` で、名前に `wait` を含むキー（大小文字を区別しない）が無い。それ以外（busy・shell・waiting・読めない・形が違う）は断る。server/agents.ts:76-88 の考え方（idle で待ちが無いときだけ入れる）に合わせるが、読む元は agents の行ではなくこのファイル（件の行は agents で結ばないため。14-2）。
  5. 補助の確認: dataDir/open-sessions.json にその id の項目があり、roleId が `discord-case` と完全一致する（台帳は書き換えられるので補助。本線は判定2〜4）。第2版の環境変数 `TMUX` の確かめは、判定2の祖先の確かめで置き換えたので外した（第3版）。
  6. 手順ファイル: R 自体と `<R>/<手順ファイル名>` がリンクでない（lstat）。手順ファイルを O_NOFOLLOW で開き、fstat で所有者が自分の通常のファイルであることを確かめ、その開いたファイルから sha256 を取る。realpath が R の下。
- 送り方: `tmux -L agent-console send-keys -t =ac-<id> -l <文>` で文字だけを入れる。1秒待ち、Enter の直前に判定2〜4をもう一度行う。外れたら Enter を送らず、`case_say_refused`（理由 `state_changed_before_enter`）を書いて exit 2。このとき入った文字は件の入力欄に残るので、止めの印 `<dataDir>/case-say-blocked/<id>` を作り、以後その件への送信は判定1で断る。Opus は PO に「件の入力欄に残った文を消してください」と知らせ、PO が消したことを確かめてから、PO が `!` で印のファイルを消す（第4版。部品に印を消す口は作らない。3回目の審査 MEDIUM）。Opus も同じファイルを消せるので、作りでは止められない。Opus が手順を破って消した場合に起きるのは、件の入力欄に決まった一文がもう一度足されることだけで、件の窓の中に閉じる（Opus の同意にはならない）。この残る危険を R18 に書く。consent-audit.py `--audit` は、今ある印の数と、`state_changed_before_enter` の件数を出す。通れば `send-keys -t =ac-<id> Enter`。部品は引数の配列で呼び（shell を通さない）、`=` で名前の完全一致にする。
- 記録: 送ったら agent-events.jsonl に `case_say`（ts・件の id・手順ファイル名・文の sha256 先頭16桁・判定6で取った手順ファイルの sha256 先頭16桁・P）を1行書く。本文は書かない。

(b) §4-5 の見張りは変えない。止める条件・止める文・kind・T7 の期待はそのまま。case-say.py を呼ぶコマンドの文字には見張りの語が入らないので、見張りに例外を足す必要がない。

(c) 文書: ADR-1033 の What（いま5項目）に6つ目として「件のセッションへの決まった一文の送信は case-say.py だけで行う（design §14）。§4-5 の見張りの外で端末へ送る、ほかの道を作らない」を足す。§4-5 の末尾に同じ1行を足す。agent-console 側の手順書（便2b-3b のやり直し）は、件の窓への一文を「Opus が case-say.py で送る」に書き換える（agent-console の別 PR）。

(d) 使ってよい場面: PO が承認した手順書に書かれた、件のセッションへの段階の指示だけ。手順ファイルは Opus が R に書き、同じ内容を記録の置き場（~/kb/04-records の該当の回）にも残す。

### 14-4 対象と対象外

- 対象（リポジトリ内）: hooks/case-say.py（新規・試作）、scripts/dev/case-say-tests.py（新規・単体試験）、po-apply-consent.sh（`--update` の写す一覧に case-say.py を足す）、po-rollback-consent.sh（case-say.py を消す1行）、scripts/dev/consent-audit.py（`--audit` に case_say・case_say_refused の件数を1行出す）、本書、ADR-1033、docs/adr/README.md（再生成）。
- 対象（リポジトリ外・PO の `!`）: ~/.claude/scripts/case-say.py。
- 対象外: agent-danger-hook.sh・worktree-only-guard.sh・consent_check.py・settings.json（見張りと許可は変えない）、agent-console のサーバーのコード、件の部屋の設定。

### 14-5 代替案

| 案 | 採否 | 理由 |
|---|---|---|
| A 決まった一文だけを、件の窓だけへ送る部品（本案） | 採用 | 見張りを変えない。送れる文は決まった形の1種類で、文が「1」だけになることはない（数字は決まった前後の文字の中に入る）。宛先が同意を判定しない件の窓だけ |
| B §4-5 の tmux の条件に「宛先が ac-<件>」の例外を足す | 不採用 | 任意の文を送れる。文字照合で宛先を見分けるので、見張りが弱くなる |
| C 予約（ac-reserve）で件を開き、指示を渡す | 不採用 | 件の役割は作りで予約できない（server/config.ts:160-161）。変えるのは部屋の設計の変更になる |
| D 画面のチャットの送信口を使う | 不採用 | 認証の秘密が要り、秘密を読むことは禁止 |
| E 今のまま PO が打つ | 予備 | 案 A が K20 で×のときの戻り先 |

### 14-6 リスクと対処

| # | リスク | 対処 |
|---|---|---|
| R11 | 許可の確認が出ている件の窓に、文字か Enter が入る。文には数字（件の id・ファイル名）が入るので、数字で選ぶ確認なら文字の時点で選択肢が押される恐れがある | 判定2〜4を最後に行い、その直後に文字を入れる（第3版）。Enter の直前にも判定2〜4をやり直し、外れたら Enter を送らない（第2版）。残る隙間: 判定から文字の送信まで、確かめ直しから Enter までの、それぞれ数十ミリ秒の間に確認が出る場合は防げない。その場合も押されるのは件の部屋の中の操作（部屋の G1〜G7 の範囲）で、Opus の同意にはならない |
| R18 | Enter の前に断ったとき、件の入力欄に文が残り、次の送信や件の操作に混ざる | 止めの印で、その件への送信を断る。印は PO が入力欄を消したと確かめた後に、PO が `!` で消す（第4版）。残る危険: Opus も印を消せるので、作りでは止められない。破られた場合も、件の入力欄に決まった一文が足されるだけで、件の窓の中に閉じる。「件の窓の中に閉じる」は、宛先が件の起動の命令の窓に限られる（判定2の本線・R16）ことが前提。--audit に印の数と Enter 前の断りの件数を出す |
| R16 | Opus が台帳・CH の状態ファイル・W を偽り、自分の窓の id を渡して（部品を親から切り離す・偽の本体を W で動かす・自分の作業場所のフォルダを W の名前へ移す場合を含む）、宛先を自分の窓（許可の確認が出ている窓など）へ向ける | 本線は窓の起動の命令（判定2・第5版）。起動の命令はサーバーが窓を作った時に決まり、ファイルや台帳やフォルダを偽っても変わらない。変えるには tmux の命令で窓の中身を入れ替える必要があり、それは §4-5 の見張りが止める。入れ替えれば中の本体（許可の確認を出している側）も止まる。根の作業場所（第4版）と祖先の確かめ（第3版）は補助 |
| R17 | 件が自分の CH の状態ファイルを書き換え、作業中なのに idle と見せる | 影響は件自身の窓だけ（R13 と同じ水準）。Opus の窓には届かない |
| R12 | AI が case-say.py を真似た別の部品を作り、Opus の窓へ「1」を送る | R1 と同じ水準（受け入れ済み）。この改訂で新しく開く道ではない。case-say.py は文も宛先も固定 |
| R13 | 件自身が R の手順ファイルを書き換え、自分への指示を変える | 件が自分でできることの範囲を超えない（件は R に書ける・自分の窓で動く）。送った時の手順ファイルの sha256 を case_say に残すので、kb に残した中身と比べられる |
| R14 | PO が段階ごとの一文を見なくなる | 手順ファイルは PO が承認した手順書から作り、kb の記録に残す。case_say の件数を週次点検に出す |
| R15 | 部屋の中の件が case-say.py を呼ぶ | 部屋の中から tmux のソケットへの接続は失敗する（G7）。宛先は件の起動の命令の窓だけ（判定2の本線）なので、ほかの窓へは向かない。自分の窓へは祖先の確かめ（補助）で断る |

戻し方: `! bash docs/handoff/conversation-consent/po-rollback-consent.sh`（case-say.py を消す）、または case-say.py だけを消す。見張りは変わっていないので、消せば元と同じ。

### 14-7 成功条件

| # | 基準 | 検証方法 |
|---|---|---|
| K20 | 判定2〜4 が本物の件で成り立つ（最初に測る。×なら案 E に戻し、PO に報告） | PO が件を1つ開き、Opus が読むだけの確かめ（pane_pid・子孫・`CH/sessions/<pid>.json` の status とキー・本体の cwd・本体の comm・Opus の Bash の祖先が F に入らないこと・pane_pid の cwd と、pane_pid から P までの道の各 pid の cwd（第4版））を3回行う。あわせて Opus 自身の窓の pane_pid の cwd が W でないことと、件の窓と Opus の窓の `#{pane_start_command}` を1回ずつ読み、件の窓だけが件の起動の命令と一致することを確かめる（第5版）。①入力待ち: 本体がちょうど1つ・pane_pid から P までの cwd がすべて W・comm が `claude`・status が idle・待ちのキーなし・祖先が F の外、なら○。②件に作業を頼んで作業中: status が idle 以外なら○。③件に許可の確認が出る操作を頼み、確認が出ている間: status が idle 以外か、待ちのキーがあれば○（第3版）。1つでも違えば× |
| K21 | 件の窓に、決まった一文が1回だけ入り、件が手順ファイルを読み始める | 本物の件で1回。件の会話の画面にその一文が1回出て、件が手順ファイルを読んだことが件の返事で分かれば○ |
| K22 | 件でない宛先（台帳を書き換えて件の roleId にした件でない窓を含む・自分の窓の id を渡し CH・W・状態ファイル・台帳を偽り `cd W` から呼んだ場合（第3版）・さらに部品を親から切り離し、偽の本体を W で動かした場合（第4版）・さらに自分の作業場所のフォルダを W の名前へ移した場合（第5版。起動の命令が件の形でないので断る）・W がリンクの場合・本体の cwd が W でない・本体の comm が claude でない・CH に状態ファイルが無い・本体が0か2つ以上）、止めの印がある件、形の違う引数、R の外・リンク・R 自体がリンク・無いファイル、状態が idle 以外・待ちのキーあり・読めない、では何も送らず exit 2。Enter の直前に状態が変わったら Enter を送らず exit 2 | case-say-tests.py（偽の tmux・ps・lsof・置き場を差し替え、send-keys の呼び出しが0回。Enter 前の変化の場合は文字の send-keys 1回・Enter 0回・止めの印ができる。自分の窓の偽装は、偽の ps で部品の祖先を F に入れる。切り離しの偽装は、偽の ps で祖先を F の外にし、偽の lsof で P の cwd を W・pane_pid の cwd を W 以外にする。フォルダを移す偽装は、偽の lsof ですべての cwd を W にし、偽の tmux の起動の命令をふつうの窓の形にする）。本物では Opus の窓の id を指定して1回、exit 2 で何も入らないこと |
| K23 | §4-5 の見張りが変わっていない | agent-danger-hook.sh・worktree-only-guard.sh の試作と本物の差分0行、test-agent-hooks.sh の T7 が合格 |
| K24 | 送るたびに case_say が1行、断るたびに case_say_refused が1行書かれ、consent-audit.py --audit がその件数を出す | 単体試験と、K21・K22 の本物の回の後の --audit の出力 |

### 14-8 実装の分け方

- 便CS1（クラウドの Sonnet・PR 1本）: §14-3(a)(c) のリポジトリ側、§14-4 の対象、試験 K22（単体）・K23・K24（単体）。
- PO: マージ後に `! bash docs/handoff/conversation-consent/po-apply-consent.sh --update` を1回。
- Opus: K20（件を PO が開いた後）→ K21・K22 の本物の回 → agent-console の手順書を書き換える。

### 14-9 設計審査

- 1回目（2026-11-05・クラウドの Opus・第1版 19855565d）: REVISE。HIGH 1・MEDIUM 2・LOW 4。
  - HIGH: 宛先と状態を、Opus が書き換えられる台帳の番号で決めていた → 判定2〜4 で、窓の pid の子孫・CH の状態ファイル・OS 上の作業場所で結ぶ形に直した（第2版）。
  - MEDIUM: 「agents.ts と同じ基準」は事実と違う（サーバーは pid で結ぶ）→ 判定4 の書き方を直した。agents の行では件を結ばないことも 14-2 に足した。
  - MEDIUM: 文を入れてから Enter までに状態を確かめ直していない → Enter の直前に判定2〜4をやり直す。K22 に足した。
  - LOW: 環境変数は補助（判定5）・R 自体のリンクと開いた後の sha（判定6）・ADR の What は6つ目・dataDir は既定の場所だけで、無ければ断る。すべて直した。
  - 審査の未確認のうち、環境変数 CLAUDE_CODE_SESSION_ID は判定から外した。
- 2回目（2026-11-05・クラウドの Opus・第2版 a1e062f02）: REVISE。HIGH 1・MEDIUM 2・LOW 2。新しく引いた file:行 はすべて正しいと確認された。
  - HIGH: Opus が自分の窓の id を渡し、CH の状態ファイル・W・R・台帳を偽って `cd W` から部品を呼ぶと、判定2〜5が通り、Enter が自分の窓に入る → 判定2で部品自身と祖先が F に入っていたら断る。判定3で P の comm が claude であることを補助で確かめる。K22 にこの偽装を足した。TMUX の確かめは外した（第3版）。
  - MEDIUM: 文には数字が入るので「「1」は送れない」は不正確 → 14-3 の言い方を直し、R11 に数字と時間の隙間を書いた。判定2〜4を最後に回し、その直後に文字を入れる。
  - MEDIUM: K20 に許可の確認が出ている間の読みが無い → K20 の③を足した。
  - LOW: Enter 前に断ったとき入力欄に文が残る → 止めの印と、PO の `!` の --clear（R18）。
  - LOW: dataDir の既定の行は README.md:314 → 直した。
- 3回目（2026-11-05・クラウドの Opus・第3版 4575a5cc0）: REVISE。HIGH 1・MEDIUM 1・LOW 2。2回目の指摘のうち4件は直ったと確認された。判定の順と Enter 前のやり直しに矛盾なし。
  - HIGH: 部品を親から切り離して呼ぶと祖先の確かめが外れ、偽の本体を W で動かせば判定3・4も通る → 窓の根 pane_pid と、根から P までの道のすべての作業場所が W であることを要る形にした。祖先の確かめは補助（第4版）。K20・K22 に足した。
  - MEDIUM: --clear は Opus も流せ、記録で区別できない → 部品から --clear を外し、PO が `!` で印を消す形にした。Opus も消せることは残る危険として R18 に書いた。--audit に印の数を出す。
  - LOW: 14-5 の案 A の理由と R15 の書き方 → 直した。
- 4回目（2026-11-05・クラウドの Opus・第4版 abeccf96e）: REVISE。HIGH 1・MEDIUM 1・LOW 2。3回目の MEDIUM 1件・LOW 2件の直しは足りていると確認された。件の起動（窓は W で開き、zsh から sandbox-exec、claude と置き換わる）と判定2は矛盾しないと確認された。
  - HIGH: Opus が自分の作業場所のフォルダを W の名前へ移すと、窓の中の作業場所がすべて W に見え、判定2〜5が通る → 本線を、後から変えられない tmux の窓の起動の命令（`#{pane_start_command}` が件の起動の命令と一致）にした。作業場所と祖先は補助（第5版）。K20・K22 に足した。
  - MEDIUM: W の比べ方が無い → W は realpath にせず、lstat でリンクでない自分のフォルダに限り、文字で完全一致と書いた。
  - LOW: R15 の本線の書き方・R18 の前提 → 直した。
- 5回目（2026-11-05・クラウドの Opus・第5版 b61dd3075）: REVISE。HIGH 1・MEDIUM 2・LOW 1。4回目の MEDIUM・LOW 2件の書き直しは入っていると確認された。K20・K22 は○×で決まる形と確認された。
  - HIGH: 起動の命令は `$AC_CASE_SHELL` を展開しない文字のまま比べる形で、中身は newSession の `-e` で渡る（agent-console server/terminal-host/tmux-runner.ts:84-85）。Opus は同じ起動の文字で偽の窓（new-session）を作り、中で自分の窓へつなぐ（attach）ことで判定1〜5を通せる。見張りの語は出ない。直し方の案: 宛先をサーバーがメモリに持つ「件の id → pane_pid」と照合する・P の実行ファイルを確かめる・F に tmux の接続役が無いことを確かめる。
  - MEDIUM: §4-5 の見張りが止めるのは入力の送り込み4語だけで、new-session・new-window・respawn-pane は止まらない。R16 の「入れ替えは見張りが止める」は事実と違う。
  - MEDIUM: R15・R18 の「件の窓の中に閉じる」の前提が HIGH で崩れる。
  - LOW: サーバーは W を os.homedir() から作り realpath にしていない（server/sessions.ts:230）。部品の比べ方と揃える。
- 判断（Opus・2026-11-05）: 1〜5回目の審査で、毎回ちがう HIGH が出た（祖先の外し方→切り離し→フォルダの名前替え→同じ起動の文字の偽の窓）。手元の文字や OS の情報だけで件の窓を確かめる形では、Opus が作れる偽装を閉じきれていない。次の直し方はサーバー（agent-console）側の変更を要し、設計の向きが変わる。ここで止めて、PO に向きを聞く。第5版は採用不可のまま残す。
- 記録の副産物: 5回目の MEDIUM により、§4-5 の見張りは new-session・new-window・respawn-pane を止めないことが分かった（case-say とは別に、今の見張りの穴として残る）。
- 未解決の前提: K20（件の状態ファイルの status が入力待ちで idle・作業中と確認の待ちで idle 以外になるか・本体の cwd が W か・本体の comm が claude か・件の pane_pid から P までの作業場所がすべて W か・件の窓の起動の命令の正確な形）。×なら案 E に戻る。

### 14-10 第6版: 作業画面アプリ（agent-console）のサーバーが宛先を決めて送る

#### 14-10-1 考え方

第5版までは、手元の部品が tmux や OS の情報を読んで「この窓は件か」を判定した。読む情報はすべて Opus が後から作り直せた。第6版では、件の窓を自分で開いたサーバーだけが宛先を決める。サーバーはメモリに「件の id → その窓の本体の pid と開始時刻」を持っている。Opus はそのメモリを書き換えられない。Opus は「件の id と手順ファイル名」だけを渡し、送る文・宛先・送ってよいかの判定はすべてサーバーが行う。

#### 14-10-2 観測事実（agent-console origin/main f503e9b。行番号はこの版）

- 件のセッションは `create` → `createCase`（server/sessions.ts:350・:366-388）で開く。窓は `spawnSession`（:613-675）の中の `openTerminal` で、tmux の `newSession` で新しく作る（:704）。件のとき、その窓の pid（tmux の pane の pid）と開始時刻を `recordCaseMain` で記録する（:631・:292-296。開始時刻が引けなければ記録しない）。
- 記録の写しは `caseMainProcesses()`（:287-289）で取れる。窓が終わると記録を消す（:666-668）。一覧から外したときも消す（:737）。
- 件かどうかは役割の `caseSandbox === true` で決まる（:625）。`caseHomeOf(id)` は、生きている件のセッションのときだけ CH を返す（:270-275）。
- サーバー起動時の復元（server/restore.ts）は、件の項目について `D/cases/<id>/case.json` の worktree が cwd と同じで、写しが作ったままの形のときだけ開く（restore.ts:22-37・:154-158）。開くとき tmux に同じ名前の窓が生きていれば、新しく作らずにつなぎ直す。そのときの pid は tmux が返す今の pane の pid（sessions.ts:691-693、server/terminal-host/tmux-runner.ts:60-69）。つなぎ直したセッションには `reattached: true` が付く（sessions.ts:644）。
- 端末へ書くとき、サーバーは tmux の制御の接続から `send-keys -t =ac-<id>: -H …` を出す（server/terminal-host/tmux-protocol.ts:16・:46）。宛先は「そのセッションの今の窓の今の区画」で、pid では選ばない。
- AI が呼ぶ既存の受け口（予約 /api/agent/reservations）の順序: Origin ヘッダーがあれば 403 → 合言葉（dataDir/reserve-token）を定数時間で比べ、違えば 401 → 本文 → 呼び出し元の照合 `checkCaller`（server/http.ts:459-483・:512-518）。照合は、呼び出し元が名乗る会話の番号を、サーバーのメモリにある生きたセッションの番号と比べ、全部の役割が許可の一覧にあるときだけ通す。名乗りを信じる形で、本人の確かめではない（agent-console docs/handoff/discord-pdca/design.md:250）。監査は `writeAudit` で1行（http.ts:507-510）。
- 予約の命令 `hooks/ac-reserve.mjs` は、合言葉を自分で dataDir/reserve-token から読み、値を画面に出さない（:18-27・:34）。呼び出し元の番号は環境変数 `CLAUDE_CODE_SESSION_ID` だけから取る（:65・:105）。サーバーが dataDir/bin へ写す（server/activity-setup.ts:77-82）。
- 予約・定期実行を使える役割の一覧は config の `reserveRoles`・`routineManagerRoles`（server/config.ts:82-84）。件の役割はどちらにも入れられない（:317-319）。
- 画面のチャットの送り方（server/hub.ts:560-607）: 予約を1件ずつ、`chatVerdict`（server/agents.ts:95-103）が ok のときだけ送る。Claude が動いていると判定したときは括弧付きで貼り、`pasteSubmitDelayMs` 待って Enter。Claude の行が見つからないときは「Claude が動いていないシェル」とみなし、括弧なしで書いて Enter を送る（agents.ts:99、hub.ts:594・:598）。
- 件の本体は `claude agents --json` に出ない（agent-console docs/handoff/discord-pdca/bin2b3d-card.md:51 の記載。設計書の記載で、この版では実測していない → K30 で測る）。出ないなら、画面のチャットから件の窓へ送ると、件に許可の確認が出ていても括弧なしで書いて Enter を送る。このため第6版は画面のチャットの送り方を使わない。
- 件の本体の状態は、部屋の外から `CH/sessions/<pid>.json` を読める。サーバーはこのファイルを、窓の子孫の pid だけについて、リンク・名前付きパイプ・固いリンク・64KiB 超を断って読む部品を持つ（server/case-agents.ts:15-40・:42-71。今は会話の番号だけを取る）。
- 合言葉ファイルの書き手はサーバーだけ（server/reserve-token.ts:6・:28-38）。

#### 14-10-3 変更後の仕組み

(a) 新しい受け口 `POST /api/agent/case-say`（agent-console server/http.ts。予約の受け口と同じく認証の前に分ける）。順に確かめ、外れたら端末へ何も書かずに断る。

1. POST 以外は 405。Origin ヘッダーがあれば 403。合言葉が無い・違うなら 401（予約と同じ）。
2. 本文（4KiB まで）`{ callerSessionId, caseId, stepFile }`。`caseId` は `isSessionId` の形、`stepFile` は `^[A-Za-z0-9._-]{1,64}\.md$` で `..` を含まない。違えば 400。
3. 呼び出し元: `checkCaller(deps, callerSessionId, config.caseSayRoles)`。`caseSayRoles` は config の新しい項目で、既定 `["opus-designer"]`。roles に無い id と件の役割は起動時エラー（config.ts:317-319 と同じ形）。違えば 403。
4. 宛先（すべてサーバーのメモリの記録で決める）:
   - `sessions.get(caseId)` があり、止まっていない。`caseHomeOf(caseId)` が値を返す（件の役割）。
   - `reattached` が付いていない。サーバーがこの起動中に自分で新しく作った窓だけを宛先にする（復元でつなぎ直した窓は、中身をサーバーが作った物か確かめられないため断る。理由 `reattached`）。
   - `caseMainProcesses().get(caseId)` があり、その pid の今の開始時刻が記録と同じ。
   - tmux に、宛先の窓がそのまま残っているかを聞く: `display -p -t =ac-<caseId>: '#{pane_pid} #{session_windows} #{window_panes}'` が「記録の pid・1・1」と一致する（区画の入れ替え・分割・窓の追加で宛先が別の物になっていないこと）。
   違えば 409（理由を本文と監査に書く）。
5. 止めの印: 同じ件に、前に Enter を送らずに終えた記録（メモリ）があれば 409。印はその件の窓が終わったとき・一覧から外したときに消える。消す受け口は作らない。
6. 手順ファイル: `R = casePaths(...).R`。R がリンクでないフォルダ。`<R>/<stepFile>` を O_NOFOLLOW で開き、通常のファイル・固いリンクでない・64KiB まで。sha256 を取る。違えば 409。
7. 件の状態（新しい判定 `caseSayVerdict`。画面のチャットの `chatVerdict` は使わない）: 窓の子孫の pid の中で、`CH/sessions/<pid>.json` を 14-10-2 の安全な読み方で読めるものがちょうど1つ。その JSON の pid が同じ・`status` がちょうど `idle`・名前に `wait` を含むキー（大小文字を区別しない）が無い。あわせて、取り直した `claude agents --json` に子孫の pid の行があれば、その行も idle で `waitingFor` が無い。違えば 409。
8. 書き込みの印 `tryBeginWrite(caseId)`（server/hub.ts:301）が取れなければ 409。
9. 送る文はサーバーが組み立てる1種類だけ: `<R>/<stepFile> を読み、書いてある手順を順に行ってください。`。括弧付きで貼る → `pasteSubmitDelayMs` 待つ → 4・7 をもう一度確かめる → 通れば Enter（`\r`）を送って 200。外れたら Enter を送らず、止めの印を付けて 409（理由 `state_changed_before_enter`）。
10. 監査: 送ったら `caseSay`、断ったら `caseSayRefused`（理由・caseId・stepFile・呼び出し元の番号・文の sha256 の先頭16桁・手順ファイルの sha256 の先頭16桁）。本文と合言葉は書かない。`RoutineAuditAction`（server/routine-audit.ts:11）に2つ足す。

(b) 新しい命令 `hooks/ac-case-say.mjs`（ac-reserve.mjs と同じ作り。サーバーが dataDir/bin へ写す）。使い方は `node "<dataDir>/bin/ac-case-say.mjs" <件の id> <手順ファイル名>` の1つだけ。合言葉は自分で読み、値を出さない。呼び出し元の番号は `CLAUDE_CODE_SESSION_ID` だけから取る。結果（送った／断った理由）を1行出す。

(c) 変えない物: 画面のチャットの送り方・`chatVerdict`・`inputVerdict`、件の部屋、Sales Anchor 側の見張り（§4-5）と許可の設定。Sales Anchor 側の手元の部品 case-say.py は作らない。

(d) 文書: Sales Anchor の ADR-1033 の What に6つ目として「件のセッションへの決まった一文の送信は、agent-console の case-say の受け口だけで行う（design §14-10）。§4-5 の見張りの外で端末へ送るほかの道を作らない」を足す。agent-console の README に「件へ一文を送る」の節を足す。便2b-3b の手順書（agent-console PR #86）は、件の窓への一文を「Opus が ac-case-say.mjs で送る」に書き換える（別 PR）。

(e) 使ってよい場面: PO が承認した手順書に書かれた、件のセッションへの段階の指示だけ（§14-3(d) と同じ）。

#### 14-10-4 対象と対象外

- 対象（agent-console・PR 1本）: server/http.ts（受け口）、server/hub.ts（`caseSayVerdict` と送る手順・止めの印）、server/case-agents.ts（状態ファイルの読み取りの部品を足す。今の番号の読み取りは変えない）、server/config.ts（`caseSayRoles`）、server/routine-audit.ts（2つの action）、server/activity-setup.ts（命令を写す）、hooks/ac-case-say.mjs と型の .d.mts（新規）、試験、README。
- 対象（Sales Anchor）: 本書、ADR-1033、docs/adr/README.md（再生成）。
- 対象外: Sales Anchor の見張り・許可・settings、件の部屋の設定、画面のチャット、予約・定期実行の受け口。§4-5 の見張りが new-session・new-window・respawn-pane を止めない穴（§14-9）は別の件として残す。

#### 14-10-5 代替案

| 案 | 採否 | 理由 |
|---|---|---|
| F サーバーが自分の記録で宛先を決め、決まった一文だけを送る受け口（本案） | 採用 | 宛先の正本がサーバーのメモリで、Opus は書き換えられない。文も固定。見張りを変えない |
| G 画面のチャットの予約（enqueueChat）に一文を積む | 不採用 | 件の本体が agents の行に出ないと、確認の待ちでも括弧なしで書いて Enter を送る（14-10-2） |
| H 定期実行の送信 `submitText`（hub.ts:613-632）を使う | 不採用 | 状態を確かめずに送る |
| A 手元の部品（第1〜5版） | 不採用 | §14-9。手元の情報は Opus が作り直せる |
| E 今のまま PO が打つ | 予備 | K30 が×のときの戻り先 |

#### 14-10-6 リスクと対処

| # | リスク | 対処 |
|---|---|---|
| R20 | Opus が偽の窓（同じ名前・同じ起動の文字）を作り、宛先にする | サーバーのメモリにある、自分で作った窓だけが宛先（4）。偽の窓はメモリに無い。tmux に同じ名前の窓は2つ作れない |
| R21 | Opus がサーバーの再起動の前に偽の件（case.json・写し・tmux の窓）を用意し、復元でつなぎ直させる | つなぎ直した窓は宛先にしない（4 の `reattached`）。残る制約: サーバーを起動し直した後は、開き直した件にしか送れない |
| R22 | Opus が tmux の命令（swap-pane・split-window・new-window・respawn-pane など。§4-5 の見張りは止めない）で、件の名前の窓の中身を別の物にする | 貼る前と Enter の前に、今の区画の pid が記録の pid と同じで、窓1つ・区画1つかを tmux に聞く（4）。中身を入れ替えれば本体の開始時刻か区画の pid が変わる。残る隙間: 確かめてから書くまでの数ミリ秒に入れ替える競争。そのときも送る文は固定で「1」だけにはならない |
| R23 | 許可の確認が出ている件の窓へ文か Enter が入る | 件の状態ファイルで idle・待ちなしのときだけ貼り、Enter の前に確かめ直す（7・9）。状態ファイルが確認の待ちを表すかは K30 で測る。×なら案 E |
| R24 | 件が自分の状態ファイルを書き換え、作業中なのに idle と見せる | 影響は件自身の窓だけ（§14 R17 と同じ水準） |
| R25 | 呼び出し元の照合は名乗りを信じる形で、ほかの役割の AI が Opus の番号を名乗れる | 合言葉と役割の照合は入口の絞りにとどまる。安全の本線は、宛先がサーバーの記録の件だけで、文が固定であること（4・9）。監査に全件残る |
| R26 | Enter の前に断ったとき、件の入力欄に文が残る | 止めの印でその件への送信を断る（5）。印はメモリだけで、件の窓が終わると消える。Opus が消す口は無い。サーバーを起動し直すと消えるが、その後は R21 によりその件には送れない |
| R27 | 部屋の中の件が受け口を呼ぶ | 部屋の読み取りの拒否に `D/reserve-token` が入っている（agent-console docs/handoff/discord-pdca/bin2b3-card.md:26 の `CASE_DENY_READ`。設計書の記載で、この版では件の中から読めないことを実測していない）。読めても、件の会話の番号は件の役割なので `checkCaller` で断る（3。件の役割は `caseSayRoles` に入れられない）。名乗りで Opus の番号を使われた場合は R25 と同じで、宛先は件だけ・文は固定 |

戻し方: agent-console を一つ前の版に戻す（受け口と命令が消える）。Sales Anchor 側は ADR-1033 の1行を戻す。見張りは変えていないので、戻せば元と同じ。

#### 14-10-7 成功条件

| # | 基準 | 検証方法 |
|---|---|---|
| K30 | 件の状態ファイルで、入力待ち・作業中・確認の待ちを見分けられる。件の本体が `claude agents --json` に出るかを確かめる（実装の前に測る。×なら案 E に戻し、PO に報告） | PO が件を1つ開き、Opus が読むだけで3回: ①入力待ちで `CH/sessions/<pid>.json` の status が idle・待ちのキーなし ②件に作業を頼んで作業中に idle 以外 ③件に許可の確認が出る操作を頼み、出ている間に idle 以外か待ちのキーあり。あわせて `claude agents --json` に件の子孫の pid の行があるかを1回記録する。①〜③が全部○なら○ |
| K31 | 14-10-3(a) の1〜9の断りがすべて効き、断ったときは端末へ何も書かない。Enter の前に変わったら Enter を送らず止めの印が付く | agent-console の vitest（偽の tmux・ps・状態ファイル）。断りの各場合で書き込み0回。通る場合は貼り付け1回・Enter 1回。Enter 前の変化は貼り付け1回・Enter 0回・次の呼び出しが 409 |
| K32 | 本物の件に一文が1回だけ入り、件が手順ファイルを読み始める。件でない宛先には何も入らない | 反映後、本物で: 件の id で1回（件の画面に一文が1回出て、件の返事で手順ファイルを読んだと分かれば○）。Opus 自身の窓の id で1回（409・何も入らない） |
| K33 | Sales Anchor の見張りが変わっていない。命令が見張りに止められない | agent-danger-hook.sh・worktree-only-guard.sh の試作と本物の差分0行・test-agent-hooks.sh の T7 合格。K32 の呼び出しが見張りに止められない |
| K34 | 送るたびに caseSay、断るたびに caseSayRefused が監査に1行 | vitest と、K32 の後の監査の行 |

#### 14-10-8 実装の分け方

- 測定（Opus・PO が件を開いた後）: K30。×なら案 E に戻す。
- 便CS1（クラウドの Sonnet・agent-console の PR 1本）: 14-10-3 (a)(b)・README・K31・K34 の単体。
- 便CS2（クラウドの Sonnet・Sales Anchor の docs PR 1本）: ADR-1033 の1行と索引の再生成。
- PO: agent-console の新しい版の反映（いつもの手順）。
- Opus: K32・K33 → 便2b-3b の手順書の書き換え。

#### 14-10-9 外部事例

該当事例なし。理由: 判断の中心は、自作の作業画面アプリの中で「誰が宛先の正本を持つか」で、外部の数値事例では確かめられない。確かめは K30〜K34 の実測で行う。

#### 14-10-10 設計審査（第6版）

- 6回目: 未実施。
