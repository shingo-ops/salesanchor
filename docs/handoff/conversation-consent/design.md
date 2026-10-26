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
- 対象（リポジトリ外・PO の `!` で反映）: ~/.claude/scripts/agent-danger-hook.sh・worktree-only-guard.sh（po-apply-consent.sh で写す。po-apply-consent.sh の中身は変えない）。agent-console の定期実行の指示文は Opus が公式手順で書き換える（§9 と同じ。サブエージェントは触らない）。
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

- 便R1: §13-3(a)(b)(d) と routine.json:12（(c) のリポジトリ側）、試験 K14・K15。PR 1本。フックのパスを含むため、マージ後に PO が `! bash docs/handoff/conversation-consent/po-apply-consent.sh` を1回打つ（試験が不合格なら自動で戻る）。
- 反映後に Opus: agent-console の定期実行の指示文を routine.json と同じに書き換える（ac-routine の公式手順）。K16・K17 は次の月曜の点検で測る。

### 13-9 設計審査（Opus の自己審査。独立した第二者の審査ではない）

判定: APPROVE（HIGH 0・MEDIUM 0・LOW 2）。
- 整合: 止める条件（§4-5・K7）を変えないので T1〜T9 の既存の期待は変わらない（T7 は件数の期待 7・6 を保ち、項目の確認を足すだけ）。ABNORMAL 系の行の形を変えない（permission-delegation/design.md:207）。R1 の受容の範囲を広げない（判定の文字列照合は R1 と同じ水準・R8）。
- 根拠: 56件の内訳と条件は保存した生データ、行番号は origin/main 900afee29 の worktree で確認。
- 検証可能性: K14・K15 は試験で○×、K16・K17 は保存ファイルで○×。
- LOW-1: 書き込みの形 3 の語の一覧は網羅でない（R8・R9 で受け入れ、K16 で測る）。
- LOW-2: agent-console の定期実行の指示文は agent-console 側にも写しがあり、二重管理になっている（今回は routine.json を正にして写すだけ。二重管理の解消は対象外）。
- 未解決の前提: なし。PO の判断が要るのは実装の承認と、反映（po-apply-consent.sh）の実行の2点。
