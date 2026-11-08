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

状態: 設計案 第6版の改訂（§14-10。サーバー側で宛先を決める形）。6〜8回目の審査は REVISE で、指摘を反映済み。9回目の審査で APPROVE（LOW 2件を反映済み）。PO 承認前。実装・反映は PO の実装承認の後。§14-3〜14-8 の第5版（手元の部品 case-say.py）は採用しない（§14-9 の判断）。§14-1・14-2 の目的と観測事実は第6版でも使う。（2026-11-06 追記: この後、第11版で Architect APPROVE・PO が作り始めを承認し、agent-console v0.51.0 で導入済み。今の状態は §14-13 の末尾）
向きの決定: PO 2026-11-05、選択肢「2. 作業画面アプリの裏側で件の窓を確かめる形に作り直す」に「2」と回答（作業画面アプリ = PO の Mac の agent-console。Sales Anchor 本番のサーバーではない）。
名前の書き方（2026-11-06・PO「1」）: §14-12 と §14-13 でコードの書式で書いていた agent-console のファイルのうち、server/・tests/ の下と agent-console.config.json は、その行を書いた時点の版に固定した agent-console へのリンクで示す（§14-12 は f503e9b、§14-13 は b467656）。ops/ の下・README と、§14-2〜§14-11 の agent-console の行の指し示しは、元の書き方のまま。Mac の上で動くときにできるファイル（CH/… など）・作らなかった案の名前・claude 本体の中の文字は、どのリポジトリにも無いので「」で囲む。
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
- （第2版で追加）件の Claude は `claude agents --json` の行で見分ける作りになっていない。サーバーは件の会話の番号を、件の設定の置き場 CH = `<dataDir>/case-home/<id>`（server/case-sandbox.ts:66）の 「sessions/&lt;pid&gt;.json」 から、件の端末の子孫の pid だけで読む（server/case-agents.ts:38-42、server/hub.ts:659-676）。ふつうの agents の行に同じ番号があれば、件の番号を外す（server/hub.ts:674）。
- （第2版で追加）サーバーは端末とプロセスを、tmux の窓の pid の子孫で結ぶ（server/process-tree.ts:40、server/hub.ts:323）。台帳の番号では結ばない。
- （第2版で追加）件の作業場所 W は `<H>/worktrees/discord-cases/<id>`（server/case-clone.ts:46-48、server/case-sandbox.ts:61）。
- （第2版で追加）「~/.claude/sessions/&lt;pid&gt;.json」 のキー（2026-11-05 実測・24個のうち1つ）: status・pid・sessionId・cwd ほか。status の値は idle 5・busy 1・shell 6。同じ時に `claude agents --json` は idle 5・busy 7。待ちの印（wait を含むキー）は、どちらにも無かった（その時に待ちのセッションが無い）。
- （第2版で追加）`CLAUDE_CONFIG_DIR` を空の置き場にして `claude agents --json` を手元で試そうとしたが、local-agent-guard に止められた。言い換えて試していない。
- （第3版で追加）`ps -o pid=,comm=` で、手元の 「~/.claude/sessions/&lt;pid&gt;.json」 の pid のうち生きている8つは、どれも comm が `claude`（2026-11-05 実測）。実行ファイルの場所を `lsof -d txt` で確かめようとしたコマンドは、`claude` の語を含むため local-agent-guard に止められた。言い換えて試していない。
- （第5版で追加）件の端末の起動の命令は、agent-console の設定で `["/bin/zsh", "-c", "source \"$AC_CASE_SHELL\" && ccdiscordcase"]` と決まっている（agent-console agent-console.config.json:47、つなぎ直しは :48）。サーバーはこの命令で tmux の窓を作る（server/sessions.ts:379 で役割の command を渡し、:704 の newSession で作る）。tmux の窓の起動の命令（`#{pane_start_command}`）は、窓を作った時に決まる。後から変えるには tmux の命令で窓の中身を入れ替える必要があり、そのときは中で動いている本体が止まる。
- 未確認: 件の 「CH/sessions/&lt;pid&gt;.json」 が、件の入力待ちで status=idle になり、作業中と許可の確認の待ちで idle 以外になるか。件の Claude の OS 上の作業場所（cwd）が W か。部屋（sandbox-exec から exec）で動く件の本体の comm が `claude` か。件の pane_pid が本体そのものか、その間にあるプロセスの作業場所がすべて W か（第4版）。`tmux display -p '#{pane_start_command}'` が件の窓で返す文字の正確な形（第5版）。§14-7 の K20 で最初に測る。

### 14-3 変更後の仕組み

(a) 新しい部品 「case-say.py」（試作 docs/handoff/conversation-consent/hooks/case-say.py、本物 ~/.claude/scripts/case-say.py。PO の `!` の po-apply-consent.sh `--update` で写す）。

- 呼び方: `python3 ~/.claude/scripts/case-say.py <件の id> <手順ファイル名>`。送る文を引数で渡す手段は作らない。
- 送る文は部品が組み立てる1種類だけ: `<R>/<手順ファイル名> を読み、書いてある手順を順に行ってください。`（R は 14-2 の置き場）。任意の文は送れない。文には数字が入る（R の中の件の id・手順ファイル名）が、文が「1」だけになることはなく、必ず決まった前後の文字がつく（第3版で言い方を直した。2回目の審査 MEDIUM）。
- 置き場の決め方: dataDir は agent-console の既定の場所 `~/Library/Application Support/agent-console`（agent-console README.md:314）、H は自分のホームを部品の中で組み立てる。W の比べ方（第5版・4回目の審査 MEDIUM）: W の期待値は `realpath(H)` に `/worktrees/discord-cases/<id>` をつないだ文字とし、W 自体は realpath にしない。W を lstat して、リンクでなく自分が持ち主のフォルダであることを確かめる。OS が返す作業場所（lsof の n 行）は、この文字と完全一致で比べる。dataDir の realpath が無いときは断る。設定で dataDir を変えた Mac には対応しない（断る）。
- 宛先は、書き換えられる台帳ではなく、OS が返す事実で結ぶ（第2版。審査 HIGH の直し）。台帳（open-sessions.json）は補助の確認にだけ使う。
- 判定（この順。外れたら何も送らず exit 2、理由を標準エラーと agent-events.jsonl の `case_say_refused` に書く。第3版で、状態を見る判定2〜4を最後に回し、その直後に文字を入れる形にした）:
  1. 件の id が UUID の形（小文字の16進と `-`）。手順ファイル名が `^[A-Za-z0-9._-]{1,64}\.md$` で、`..` を含まない。止めの印 `<dataDir>/case-say-blocked/<id>` が無い（判定後の送り方を参照）。
  ※ 下の判定6・5を先に行い、判定2〜4は最後に行う（番号は第2版のまま）。
  2. 窓の起動の形と pid: （第5版・4回目の審査 HIGH の直し。本線）`tmux -L agent-console display -p -t =ac-<id> '#{pane_start_command}'` が、件の起動の命令（14-2 の agent-console.config.json:47 の形。K20 で測った正確な文字を部品に固定で持つ）と完全一致する。合わなければ断る（理由 `pane_not_case_start`）。Opus の窓や、ほかのふつうの窓は、この命令で起動していないので断られる。続けて `tmux -L agent-console display -p -t =ac-<id> '#{pane_pid}'` が正の整数を1つ返す。子孫の pid の集合 F を `ps -axo pid=,ppid=` から作る（server/process-tree.ts:40 と同じ作り）。（第3版・2回目の審査 HIGH の直し）同じ `ps` の結果から、部品自身の pid とその祖先（ppid をたどって pid 1 まで）を集め、1つでも F に入っていたら断る（理由 `caller_in_case_pane`）。Opus が自分の窓の id を渡し、CH・W・状態ファイル・台帳を偽って `cd W` から部品を呼んでも、部品は自分の窓の子孫なのでここで断られる。ただし、部品を親から切り離して呼ぶ（二重の後ろ起動・nohup・setsid）と祖先が pid 1 に変わり、この確かめは外せる（3回目の審査 HIGH）。そのため祖先の確かめは補助とし、本線は次の「根の作業場所」とする。
     （第4版・3回目の審査 HIGH の直し）根の作業場所: 窓の pane_pid の OS 上の作業場所（`lsof -a -p <pane_pid> -d cwd -Fn`）の realpath が W と一致し、かつ pane_pid から P までの親子の道（P から ppid をたどって pane_pid に着くまで）にあるすべての pid の作業場所も W と一致する。合わなければ断る（理由 `pane_root_not_case`）。Opus の窓の pane_pid は Opus の作業場所で起動した本体（か、それを起動したシェル）なので、ふつうは W にならない。ただし Opus が自分の作業場所のフォルダを W の名前へ移す（mv）と、OS の上では W に見える（4回目の審査 HIGH）。そのため根の作業場所は補助とし、本線は上の起動の形とする（第5版）。
  3. 件の本体 P: F の中で、「CH/sessions/&lt;pid&gt;.json」 がある pid がちょうど1つ（CH = `<dataDir>/case-home/<id>`）。その pid の OS 上の作業場所（`lsof -a -p <P> -d cwd -Fn` の n 行）の realpath が W（`<H>/worktrees/discord-cases/<id>`）と一致する。（第3版）P の `ps -o comm= -p <P>` が `claude` と完全一致する（補助。名前は実行ファイルを写せば真似られるので、本線は判定2の根の作業場所）。
  4. 状態: 「CH/sessions/&lt;P&gt;.json」 を O_NOFOLLOW で開き、通常のファイルで、JSON の pid が P と一致し、status がちょうど `idle` で、名前に `wait` を含むキー（大小文字を区別しない）が無い。それ以外（busy・shell・waiting・読めない・形が違う）は断る。server/agents.ts:76-88 の考え方（idle で待ちが無いときだけ入れる）に合わせるが、読む元は agents の行ではなくこのファイル（件の行は agents で結ばないため。14-2）。
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
| K20 | 判定2〜4 が本物の件で成り立つ（最初に測る。×なら案 E に戻し、PO に報告） | PO が件を1つ開き、Opus が読むだけの確かめ（pane_pid・子孫・「CH/sessions/&lt;pid&gt;.json」 の status とキー・本体の cwd・本体の comm・Opus の Bash の祖先が F に入らないこと・pane_pid の cwd と、pane_pid から P までの道の各 pid の cwd（第4版））を3回行う。あわせて Opus 自身の窓の pane_pid の cwd が W でないことと、件の窓と Opus の窓の `#{pane_start_command}` を1回ずつ読み、件の窓だけが件の起動の命令と一致することを確かめる（第5版）。①入力待ち: 本体がちょうど1つ・pane_pid から P までの cwd がすべて W・comm が `claude`・status が idle・待ちのキーなし・祖先が F の外、なら○。②件に作業を頼んで作業中: status が idle 以外なら○。③件に許可の確認が出る操作を頼み、確認が出ている間: status が idle 以外か、待ちのキーがあれば○（第3版）。1つでも違えば× |
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
- サーバー起動時の復元（server/restore.ts）は、件の項目について 「D/cases/&lt;id&gt;/case.json」 の worktree が cwd と同じで、写しが作ったままの形のときだけ開く（restore.ts:22-37・:154-158）。開くとき tmux に同じ名前の窓が生きていれば、新しく作らずにつなぎ直す。そのときの pid は tmux が返す今の pane の pid（sessions.ts:691-693、server/terminal-host/tmux-runner.ts:60-69）。つなぎ直したセッションには `reattached: true` が付く（sessions.ts:644）。
- 端末へ書くとき、サーバーは tmux の制御の接続から `send-keys -t =ac-<id>: -H …` を出す（server/terminal-host/tmux-protocol.ts:17・:46）。宛先は「そのセッションの今の窓の今の区画」で、pid では選ばない。
- `write` は、制御の接続がまだ用意できていない・取り直し中・接続が無いとき、書く分をため込み、接続できた後でまとめて流す（server/terminal-host/tmux-terminal.ts:198-206・:221-233）。流す時刻は呼んだ時刻より後になる。
- tmux の区画には `%` で始まる番号があり、その区画が生きている間は変わらず、tmux の中で重ならない（tmux.1 COMMANDS。Context7 /tmux/tmux で確認）。`if-shell -F` は、条件を書式として展開し、空でも0でもなければ1つ目の命令を実行する。シェルは動かさない（tmux.1 MISCELLANEOUS）。書式の `#{==:a,b}` は文字の一致で1か0になる（tmux.1 FORMATS）。`respawn-pane -k` は区画の番号を保ったまま中のプロセスを入れ替える（tmux.1 WINDOWS AND PANES）。
- AI が呼ぶ既存の受け口（予約 /api/agent/reservations）の順序: Origin ヘッダーがあれば 403 → 合言葉（dataDir/reserve-token）を定数時間で比べ、違えば 401 → 本文 → 呼び出し元の照合 `checkCaller`（server/http.ts:459-483・:511-518）。照合は、呼び出し元が名乗る会話の番号を、サーバーのメモリにある生きたセッションの番号と比べ、全部の役割が許可の一覧にあるときだけ通す。名乗りを信じる形で、本人の確かめではない（agent-console docs/handoff/discord-pdca/design.md:250）。監査は `writeAudit` で1行（http.ts:507-510）。
- 予約の命令 `hooks/ac-reserve.mjs` は、合言葉を自分で dataDir/reserve-token から読み、値を画面に出さない（:18-27・:34）。呼び出し元の番号は環境変数 `CLAUDE_CODE_SESSION_ID` だけから取る（:65・:105）。サーバーが dataDir/bin へ写す（server/activity-setup.ts:77-82）。
- 予約・定期実行を使える役割の一覧は config の `reserveRoles`・`routineManagerRoles`（server/config.ts:82-84）。件の役割はどちらにも入れられない（:317-319）。
- 画面のチャットの送り方（server/hub.ts:560-607）: 予約を1件ずつ、`chatVerdict`（server/agents.ts:95-103）が ok のときだけ送る。Claude が動いていると判定したときは括弧付きで貼り、`pasteSubmitDelayMs` 待って Enter。Claude の行が見つからないときは「Claude が動いていないシェル」とみなし、括弧なしで書いて Enter を送る（agents.ts:99、hub.ts:594・:598）。
- 件の本体は `claude agents --json` に出ない（agent-console docs/handoff/discord-pdca/bin2b3d-card.md:51 の記載。設計書の記載で、この版では実測していない → K30 で測る）。出ないなら、画面のチャットから件の窓へ送ると、件に許可の確認が出ていても括弧なしで書いて Enter を送る。このため第6版は画面のチャットの送り方を使わない。
- 件の本体の状態は、部屋の外から 「CH/sessions/&lt;pid&gt;.json」 を読める。サーバーはこのファイルを、窓の子孫の pid だけについて、リンク・名前付きパイプ・固いリンク・64KiB 超を断って読む部品を持つ（server/case-agents.ts:15-40・:42-71。今は会話の番号だけを取る）。
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
   - tmux に、宛先の窓がそのまま残っているかを聞く: `display -p -t =ac-<caseId>: '#{pane_id} #{pane_pid} #{session_windows} #{window_panes}'` の2〜4つ目が「記録の pid・1・1」と一致する（区画の入れ替え・分割・窓の追加で宛先が別の物になっていないこと）。1つ目の区画の番号 `%N` を、この呼び出しの宛先として控える。以後の貼り付けと Enter はこの番号へ送る（9）。
   - 端末の接続が今すぐ書ける状態（用意済み・取り直し中でない・接続あり）で、ため込んだ書き込みが0件。tmux-terminal.ts にこれを答える読み取りだけの部品を足す。違えば 409（理由 `terminal_not_ready`）。
   違えば 409（理由を本文と監査に書く）。
5. 止めの印: 同じ件に、前に貼り付けを書いた後、Enter を送り切らずに終えた記録（メモリ）があれば 409。印を付けるのは、貼り付けを書いた後のすべての終わり方（Enter の前の確かめで断った・例外が出た・件の窓が終わった・閉じ始めた・Enter の条件付き送信が実行されなかった）。印はその件の窓が終わったとき・一覧から外したときに消える。消す受け口は作らない。
6. 手順ファイル: `R = casePaths(...).R`。R がリンクでないフォルダ。`<R>/<stepFile>` を O_NOFOLLOW で開き、通常のファイル・固いリンクでない・64KiB まで。sha256 を取る。違えば 409。
7. 件の状態（新しい判定 `caseSayVerdict`。画面のチャットの `chatVerdict` は使わない）: 窓の子孫の pid の中で、「CH/sessions/&lt;pid&gt;.json」 を 14-10-2 の安全な読み方で読めるものがちょうど1つ。その JSON の pid が同じ・`status` がちょうど `idle`・名前に `wait` を含むキー（大小文字を区別しない）が無い。あわせて、取り直した `claude agents --json` に子孫の pid の行があれば、その行も idle で `waitingFor` が無い。一覧そのものが取れなければ 409（理由 `agents_unavailable`。安全側。PR #100 で追加）。違えば 409。件の行がこの一覧に出るかは K32 で記録する。
8. 書き込みの印 `tryBeginWrite(caseId)`（server/hub.ts:301）が取れなければ 409。
9. 送る文はサーバーが組み立てる1種類だけ: `<R>/<stepFile> を読み、書いてある手順を順に行ってください。`。書き方は今の `write`（`=ac-<id>:` 宛て・ため込みあり）を使わず、tmux-terminal.ts に足す「区画の番号を宛先にし、ため込まずに今の制御の接続へ出す」部品で送る（接続が書けない状態なら書かずに失敗を返す）。手順:
   条件付きの送り方（貼り付けと Enter の両方で使う）: `if-shell -F -t %N '#{==:#{pane_pid},<記録の pid>}' 'send-keys -t %N -H <16進>' 'display -p NO'`。tmux が命令を実行する時点で、区画 `%N` の中のプロセスが記録の pid のときだけ書く。外れたら書かずに `NO` を返す。制御の接続の応答は、条件が合うときも外れるときも2つ（if-shell の分と、差し込まれる2つ目の命令の分）になる。agent-console の CommandQueue（tmux-protocol.ts:133-152）は1命令に応答1つで待つので、この命令には待ちを2つ積む。2つの応答がどちらも成功（%end）で、2つ目の中身が空のときだけ「書いた」と読む。それ以外（2つ目が `NO`・どちらかが失敗（%error）・2つ目が空でも `NO` でもない）は「書いていない」とみなし、止めの印を付けて 409 にする。1つ目の応答が失敗（%error）のときは、tmux が2つ目の命令を差し込まず応答が1つで終わりうる。そのときは余った待ちが次の命令の応答を取らないよう、その接続の待ち行列を捨てて接続を取り直す（7回目の審査役が tmux 3.4 の制御の接続で、応答が2つにそろうことを実測した。§14-10-10）。貼り付けが 1000 バイトを超えて複数の send-keys に分かれるときは、分かれた1本ずつをこの形で送る。
   (1) 括弧付きの文を、上の条件付きの形で貼る。どれか1本でも「書いた」と読めなければ止めの印を付けて 409（理由 `pane_changed_during_paste`）。
   (2) `pasteSubmitDelayMs` 待つ。
   (3) 4・7 をもう一度確かめる（区画の番号 `%N` が4で控えた物と同じことを含む）。
   (4) 通れば、Enter（16進 `0d`）を上の条件付きの形で送る。区画の番号は入れ替え（swap-pane）でもその区画についてゆくので、Enter がほかの区画に入らない。中身の入れ替え（respawn-pane -k）なら pid が変わるので Enter は入らない。「書いた」と読めなければ止めの印を付けて 409（理由 `enter_not_sent`）。
   (5) 送った後、同じ接続から `display -p -t %N '#{pane_pid}'` を聞き、記録の pid なら 200。そうでなければ止めの印を付けて 409（理由 `enter_not_confirmed`）。
   (3) で外れたら Enter を送らず、止めの印を付けて 409（理由 `state_changed_before_enter`）。
   前提（K35 で実装の前に確かめる）: tmux が `if-shell -F` の条件を判定してから差し込んだ命令を実行するまでの間に、ほかの接続の命令が割り込まない。割り込めると分かったら、この送り方を使わず審査をやり直す。
10. 監査: 送ったら `caseSay`、断ったら `caseSayRefused`（理由・caseId・stepFile・呼び出し元の番号・文の sha256 の先頭16桁・手順ファイルの sha256 の先頭16桁）。本文と合言葉は書かない。`RoutineAuditAction`（server/routine-audit.ts:11）に2つ足す。合言葉の確かめより前の断り（405・Origin の 403・401）は残さない（予約の受け口と同じ。相手を特定できず、合言葉なしで監査を膨らませられるため。agent-console PR #100 の審査で確定）。

(b) 新しい命令 `hooks/ac-case-say.mjs`（ac-reserve.mjs と同じ作り。サーバーが dataDir/bin へ写す）。使い方は `node "<dataDir>/bin/ac-case-say.mjs" <件の id> <手順ファイル名>` の1つだけ。合言葉は自分で読み、値を出さない。呼び出し元の番号は `CLAUDE_CODE_SESSION_ID` だけから取る。結果（送った／断った理由）を1行出す。

(c) 変えない物: 画面のチャットの送り方・`chatVerdict`・`inputVerdict`、件の部屋、Sales Anchor 側の見張り（§4-5）と許可の設定。Sales Anchor 側の手元の部品 case-say.py は作らない。

(d) 文書: Sales Anchor の ADR-1033 の What に6つ目として「件のセッションへの決まった一文の送信は、agent-console の case-say の受け口だけで行う（design §14-10）。§4-5 の見張りの外で端末へ送るほかの道を作らない」を足す。agent-console の README に「件へ一文を送る」の節を足す。便2b-3b の手順書（agent-console PR #86）は、件の窓への一文を「Opus が ac-case-say.mjs で送る」に書き換える（別 PR）。

(e) 使ってよい場面: PO が承認した手順書に書かれた、件のセッションへの段階の指示だけ（§14-3(d) と同じ）。

#### 14-10-4 対象と対象外

- 対象（agent-console・PR 1本）: server/http.ts（受け口）、server/hub.ts（`caseSayVerdict` と送る手順・止めの印）、server/terminal-host/tmux-terminal.ts と tmux-protocol.ts（書ける状態の読み取り・区画の番号宛てにため込まず送る部品・条件付き Enter の命令。今の `write` は変えない）、server/case-agents.ts（状態ファイルの読み取りの部品を足す。今の番号の読み取りは変えない）、server/config.ts（`caseSayRoles`・`caseSayClaudeVersions`。第10版）、server/sessions.ts（件の記録に claude の実体の道を残す。第10版 §14-13-7）、agent-console.config.json（`caseSayClaudeVersions: ["2.1.318"]`。第10版）、server/routine-audit.ts（2つの action）、server/activity-setup.ts（命令を写す）、hooks/ac-case-say.mjs と型の .d.mts（新規）、試験、README。
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
| R22 | Opus が tmux の命令（swap-pane・split-window・new-window・respawn-pane など。§4-5 の見張りは止めない）で、件の名前の窓の中身を別の物にする。特に、確かめた後に区画を入れ替え、Enter（`\r`）だけをほかの区画に入れ、そこに出ている許可の確認を承認させる | 宛先を「セッションの今の区画」でなく、4で確かめた区画の番号 `%N` にする（9）。番号はその区画についてゆくので、入れ替えても Enter はほかの区画に入らない。Enter は `if-shell -F` の条件付きで、tmux が実行する時点で `%N` の中が記録の pid のときだけ入る（9 (4)）。中身を入れ替えれば pid が変わり Enter は入らない。貼り付けも同じ条件付き（9 (1)）。送った後にも pid を聞き直す（9 (5)）。残る点1: `if-shell -F` の条件の判定と、続く send-keys の実行の間に、ほかの接続の命令（respawn-pane -k など）が割り込めるかは未確認。割り込めると、Enter が区画 `%N` の入れ替わった後のプロセスに入りうる。K35 で実装の前に確かめ、割り込めるなら実装しない。残る点2: 条件は pid だけで、開始時刻は見ない。判定から実行までの間に pid が別のプロセスに使い回される見込みは極めて小さいが、0ではない |
| R28 | 端末の接続のつなぎ直し中に呼ばれ、ため込まれた貼り付けと Enter が、確かめより後にまとめて流れる | ため込む `write` を使わない（9）。書ける状態でため込み0件のときだけ進める（4）。書けない状態なら書かずに 409 |
| R23 | 許可の確認が出ている件の窓へ文か Enter が入る | 件の状態ファイルで idle・待ちなしのときだけ貼り、Enter の前に確かめ直す（7・9）。状態ファイルが確認の待ちを表すかは K30 で測る。×なら案 E |
| R24 | 件が自分の状態ファイルを書き換え、作業中なのに idle と見せる | 影響は件自身の窓だけ（§14 R17 と同じ水準） |
| R25 | 呼び出し元の照合は名乗りを信じる形で、ほかの役割の AI が Opus の番号を名乗れる | 合言葉と役割の照合は入口の絞りにとどまる。安全の本線は、宛先がサーバーの記録の件だけで、文が固定であること（4・9）。監査に全件残る |
| R26 | Enter の前に断ったとき、件の入力欄に文が残る | 止めの印でその件への送信を断る（5）。印はメモリだけで、件の窓が終わると消える。Opus が消す口は無い。サーバーを起動し直すと消えるが、その後は R21 によりその件には送れない |
| R27 | 部屋の中の件が受け口を呼ぶ | 部屋の読み取りの拒否に `D/reserve-token` が入っている（agent-console docs/handoff/discord-pdca/bin2b3-card.md:26 の `CASE_DENY_READ`。設計書の記載で、この版では件の中から読めないことを実測していない → K33 で件の中から読めないことを実測する。読めたら実装に進まず PO に報告）。読めても、件の会話の番号は件の役割なので `checkCaller` で断る（3。件の役割は `caseSayRoles` に入れられない）。名乗りで Opus の番号を使われた場合は R25 と同じで、宛先は件だけ・文は固定 |

戻し方: agent-console を一つ前の版に戻す（受け口と命令が消える）。Sales Anchor 側は ADR-1033 の1行を戻す。見張りは変えていないので、戻せば元と同じ。

#### 14-10-7 成功条件

| # | 基準 | 検証方法 |
|---|---|---|
| K30 | 件の状態ファイルで、入力待ち・作業中・各種の待ちを見分けられる。件の本体が `claude agents --json` に出るかを確かめる（実装の前に測る。×なら案 E に戻し、PO に報告） | PO が件を1つ開き、Opus が読むだけで5回。毎回 「CH/sessions/&lt;pid&gt;.json」 のキーの一覧と、`pid`・`status` と名前に `wait` を含むキーの値をそのまま記録する（会話の中身は記録しない）: ①入力待ちで status が idle・待ちのキーなし ②作業中に idle 以外 ③許可の確認が出ている間に idle 以外か待ちのキーあり ④質問への答え待ちの間に同じ ⑤計画の承認待ちの間に同じ。あわせて `claude agents --json` に件の子孫の pid の行があるかを1回記録する。①〜⑤が全部○で、判定7が使うキーの名前（`pid`・`status`・待ちのキー）が記録と合えば○。合わなければ判定7を記録に合わせて直し、審査をやり直す |
| K31 | 14-10-3(a) の1〜9の断りがすべて効き、断ったときは端末へ何も書かない。貼り付けを書いた後に終わったら必ず止めの印が付く | agent-console の vitest（偽の tmux・ps・状態ファイル）。断りの各場合で書き込み0回。接続が書けない状態・ため込みありで書き込み0回。通る場合は貼り付け1回・条件付き Enter 1回で、どちらも宛先が `-t %N`。貼り付けの後の各終わり方（Enter 前の確かめで断る・例外・窓が終わる・閉じ始める・条件付きの送信が `NO`・どちらかの応答が %error・2つ目が空でも `NO` でもない・送った後の pid が違う）で、Enter 0回か印あり、次の呼び出しが 409。1つ目が %error のときは、その接続の待ち行列が空になり接続を取り直すこと。あわせて本物の tmux を使う試験を1本: 専用のソケットで窓を作り、制御の接続から条件付きの送り方を、条件が合う場合と外れる場合で1回ずつ出し、応答がどちらも2つで、2つ目が空と `NO` になり、続けて出した display の応答が正しい命令に渡ることを確かめる（クラウドか GitHub の試験で回す。Mac では回さない。その場の tmux の版を記録する） |
| K32 | 本物の件に一文が1回だけ入り、件が手順ファイルを読み始める。断るべき宛先には何も入らない | 反映後、本物で: 件の id で1回（件の画面に一文が1回出て、件の返事で手順ファイルを読んだと分かれば○）。件でない id で1回（409・何も入らない）。許可の確認が出ている件で1回（409・何も入らない）。サーバーの起動し直しでつなぎ直した件があれば1回（409 `reattached`。無ければ「場面なし」と記録） |
| K33 | Sales Anchor の見張りが変わっていない。命令が見張りに止められない。件の中から合言葉を読めない | agent-danger-hook.sh・worktree-only-guard.sh の試作と本物の差分0行・test-agent-hooks.sh の T7 合格。K32 の呼び出しが見張りに止められない。K30 で開いた件に、`D/reserve-token` を読む操作を頼み、読めずに断られることを件の返事で確かめる（値は出させない。読めたら×で PO に報告）。あわせて、件が R（手順書の置き場）に書けるかを1回記録する（書けても影響は件自身の手順だけ。R24 と同じ水準） |
| K34 | 送るたびに caseSay、合言葉の確かめ以後に断るたびに caseSayRefused が監査に1行（合言葉の前の 405・403・401 は残さない） | vitest と、K32 の後の監査の行 |
| K35 | `if-shell -F` の条件の判定から、差し込んだ命令の実行までの間に、ほかの接続の命令が割り込まない（実装の前に確かめる。×なら実装しない） | PO の Mac の tmux の版を `tmux -V` で記録する（読むだけ）。クラウドの Sonnet が、その版の tmux のソース（if-shell の命令・命令の列・サーバーの処理の回し方）を読み、差し込んだ命令が同じ列のすぐ後に入り、ほかの接続の列より先に実行されることを file:line で示す。あわせて同じ版のソースで、else 付きの `if-shell -F` が条件の合う・外れるのどちらでも制御の接続に応答を2つ（if-shell の分と差し込んだ命令の分）出すことを file:line で示す（7・8回目の審査役が実測したのは tmux 3.4 だけのため）。宛先の区画が無いときやエラーのときに応答の数が変わるかも、同じソースで file:line を添えて記録する。どちらも示せれば○。示せない・割り込めると分かる・応答の数が変わると分かれば× |

#### 14-10-8 実装の分け方

- 測定（Opus・PO が件を開いた後）: K30。×なら案 E に戻す。
- 確かめ（クラウドの Sonnet・読むだけ）: K35。×なら実装しない。
- 便CS1（クラウドの Sonnet・agent-console の PR 1本）: 14-10-3 (a)(b)・README・K31・K34 の単体。
- 便CS2（クラウドの Sonnet・Sales Anchor の docs PR 1本）: ADR-1033 の1行と索引の再生成。
- PO: agent-console の新しい版の反映（いつもの手順）。
- Opus: K32・K33 → 便2b-3b の手順書の書き換え。

#### 14-10-9 外部事例

該当事例なし。理由: 判断の中心は、自作の作業画面アプリの中で「誰が宛先の正本を持つか」で、外部の数値事例では確かめられない。確かめは K30〜K34 の実測で行う。

#### 14-10-10 設計審査（第6版）

- 6回目（d3747f8f9・クラウドの Opus・2026-11-04）: REVISE（HIGH 1・MEDIUM 4・LOW 2）。
  - HIGH: 貼り付けも Enter も宛先が「セッションの今の区画」で、確かめた後に区画を入れ替えると Enter だけがほかの区画に入り、許可の確認を承認しうる → 宛先を区画の番号 `%N` にし、Enter を `if-shell -F` の条件付きにし、送った後に聞き直す（9・R22）。
  - MEDIUM: 接続のつなぎ直し中は書き込みがため込まれ、確かめより後に流れる → ため込まない部品で送り、書ける状態のときだけ進める（4・9・R28）。止めの印が「Enter の前に断った」ときだけ → 貼り付けの後のすべての終わり方に広げる（5・K31）。K30 がキーの名前を記録しない・待ちの種類が足りない → キーの一覧を記録し、質問への答え待ち・計画の承認待ちを足す（K30）。件が合言葉を読めないことが未実測 → K33 に実測を足す（R27）。
  - LOW: checkCaller の行を :511-518 に直した。K32 の「Opus 自身の窓」は caseHomeOf で断られ確かめにならない → 件でない id・確認待ちの件・つなぎ直した件に替えた。
  - 未確認（審査役）: 件の中から R に書けるか → K33 で記録する。
- 7回目（9ae44b5c6・クラウドの Opus・2026-11-04）: REVISE（HIGH 2・MEDIUM 1・LOW 2）。審査役は tmux 3.4 の制御の接続で実際に試した。
  - HIGH: `if-shell -F` は条件が合うと応答が2つ、外れると1つで、1命令に応答1つで待つ CommandQueue と数が合わず、以後の応答がずれる → else に `display -p NO` を足して応答を常に2つにし、待ちを2つ積む（9。審査役が2つにそろうことを実測）。偽の tmux の試験ではこれを見つけられない → 本物の tmux の試験を K31 に足した。
  - MEDIUM: 貼り付けに条件が無く、確かめの後に中身を入れ替えると新しいプロセスに文が入る → 貼り付けも同じ条件付きにした（9 (1)）。
  - LOW: R22 に「割り込まれると入れ替わった後のプロセスに Enter が入る」点が抜けている → R22 に書き、K35（実装の前に tmux のソースで確かめる）を足した。条件が pid だけな点 → R22 に残るリスクとして書いた。
  - 確かめて問題が無かった所（審査役）: swap-pane の後も %N はその区画についてゆく。respawn-pane -k で番号は同じで pid が変わる。引用符・%N・`#{==:}` はそのままの形で動く。K30〜K34 は○×で決まる。6回目の他の指摘は直っている。
  - 未確認（審査役）: 割り込みの有無（→ K35）。PO の Mac の tmux の版（→ K35 で記録）。
- 8回目（be5707679・クラウドの Opus・2026-11-05）: REVISE（MEDIUM 1・LOW 1）。審査役は tmux 3.4 の制御の接続で、条件が合う・外れる・続けて別命令・無い区画宛て、を実際に試した。
  - MEDIUM: 応答が2つにそろうのは tmux 3.4 での実測だけで、PO の Mac の版でも同じとは決めていない → K35 に「Mac と同じ版のソースで、応答が2つ出ることを file:line で示す」を足した。
  - LOW: 2つ目の応答が失敗（%error）や想定外の中身のときの扱いが無い → 「両方成功で2つ目が空のときだけ書いた。それ以外は書いていないとみなし 409」と書いた（9）。
  - 確かめて問題が無かった所（審査役）: 4通りとも応答は2つで、順は if-shell の分→差し込んだ命令の分。まとめて送っても続く display の応答が正しい順で来る。7回目の指摘5件は直っている。K35 は○×で決まり、便CS1 より前にある。前回までに確かめた所は崩れていない。
  - 未確認（審査役）: 割り込みの有無と Mac の版（どちらも → K35）。
- 9回目（bf21d1c4b・クラウドの Opus・2026-11-05）: **APPROVE**（HIGH・MEDIUM なし。LOW 2）。8回目の指摘2件は直っている。前回までに確かめた所は崩れていない。実装役が迷わず作れる粒度。
  - LOW: 1つ目の応答が %error のとき応答が1つで終わり、待ちがずれうる → 待ち行列を捨てて接続を取り直す、と9に書き、K35 にエラー時の応答の数の記録を足した。
  - LOW: K31 の試験が `NO` の場合しか試していない → %error・想定外の中身の場合も K31 に足した。
  - 未確認（審査役）: エラー時の応答の数（→ K35）。PO の Mac の tmux の版（→ K35）。
  - LOW 2件の反映は Opus が行い、再審査は行っていない（APPROVE の後の軽い直し）。
- PO の承認（2026-11-05・チャット）: 選択肢「1. この設計で作り始めてよい」に PO が「1」と答えた。K30・K35 を先に確かめ、通れば CS1・CS2 を作る。
- K35 の記録: PO の Mac の tmux は `tmux -V` で `tmux 3.8`（/opt/homebrew/bin/tmux・2026-11-05 Opus が読んだ）。
- K35 の判定: ○（tmux 3.8 の元の文を読んで確かめた。クラウドの Sonnet が読み、2026-11-05 に Opus が同じ箇所を tag 3.8 から取り直して読み、一致を確かめた）。
  - 割り込みなし: `if-shell -F` は選んだ命令を同じ利用者の列の自分の直後に入れる（cmd-if-shell.c:99-102・条件の評価は :86-88）。入れ方は cmd-queue.c:332-355。サーバーは1本の処理で、利用者ごとの列を順に空になるまで回す（server.c:275-281）。
  - 返事は2つ: else 付きなので、合っても合わなくても命令が1つ入り、返事の区切りは2つ（cmd-if-shell.c:87-90・:99-101）。窓が無いときも `CMD_FIND_CANFAIL`（:49）でエラーにならず、条件が偽になり `NO` が返る。
  - 返事が1つになる場合: 命令の文が読めないとき（cmd-if-shell.c:97-98 `CMD_RETURN_ERROR`）は %error の1つだけ。設計の「1つ目が %error ならその接続の待ち列を捨ててつなぎ直す」で扱える。
  - まだ確かめていないこと: 本物の tmux 3.8 で動かして確かめることは、クラウドで tmux を組み立てる操作が自動判定に止められたため、していない。K31 の本物の tmux を使う試験で確かめる。
- K30 の判定: ×（2026-11-05・Opus が読むだけで測った。PO が件を1つ開き、件の窓で操作した）。
  - 状態ファイルのキーは、測った間ずっと次の17個で変わらなかった: asksForConvertedSkills・cwd・entrypoint・kind・name・nameSince・nameSource・peerFeatures・peerProtocol・pid・pidDomain・sessionId・startedAt・status・statusUpdatedAt・updatedAt・version。名前に `wait` を含むキーは一度も無かった。status の値は `idle` と `busy` の2つだけだった（0.3〜0.5 秒ごとに読み、変わった時だけ記録）。
  - ① 入力待ち: status `idle`・待ちのキーなし。○
  - ② 作業中: status `busy`。○
  - ③ 許可の確認: この件の窓では許可の確認が出なかった（ファイルを作る依頼でも、確認なしで進んだ。PO の目視）。測れず。
  - ④ 質問への答え待ち: PO が「選択肢が出た」と送った直後（11:54:57）に読み、status `idle`・待ちのキーなし。×（待ちを見分けられない）
  - ⑤ 計画の承認待ち: plan mode で頼んでも承認の確認が出なかった（PO の目視）。測れず。
  - 件の窓の区画は `%21`、pane_pid は件の本体の pid と同じ 97478、親は tmux サーバー。本体の comm は `claude` ではなく、版の番号が付いた実行ファイルの道（`.../claude/versions/2.1.318`）だった（判定3 の補助の確かめは、このままでは合わない）。
  - `claude agents --json` に件が出るかは測っていない（手元の見張り local-agent-guard が `claude` の呼び出しを止めた。言い換えずに止めた）。
  - 生の記録は社外秘の置き場（個人の記録の cloud-case-ai-20261030）に残した。会話の中身は記録していない。
  - 結論: 判定7（状態ファイルで idle・待ちなしのときだけ貼る）は、質問の選択肢が出ている窓を見分けられない。設計の決まりどおり案 E（今のまま PO が打つ）に戻し、PO に報告した。
- PO の判断（2026-11-05・チャット）: 「2」（質問の選択肢が出ていることを見分ける別の方法を探す。見つからなければ案 E）。
- 別の方法1 `claude agents --json` の測り（2026-11-05 12:17:56〜12:17:59・PO が `!` で台本を動かした。件の窓に質問の選択肢が出ている間）:
  - ふつうの置き場で動かした一覧: 12行。件の本体（pid 97478）の行は無い。行のキーは cwd・kind・name・pid・sessionId・startedAt・status の7つ。
  - `CLAUDE_CONFIG_DIR=CH` で動かした一覧: 1行。pid 97478・status `idle`・waitingFor なし。
  - 結論: ×。件の質問の待ちは、この一覧でも見分けられない。
- 別の方法2（まだ設計していない・測っていない）: 件の Claude の仕掛け（hooks）で、PreToolUse（AskUserQuestion・ExitPlanMode）と PermissionRequest の時に印を書き、答えた後に消す。公式の説明書（code.claude.com/docs/en/hooks・2026-11-05 読んだ）に、PreToolUse が AskUserQuestion と ExitPlanMode にも当たると書かれている。答えを断った時に印が消える出来事が来るかは書かれておらず、未確認。Context7 は今月の上限で使えなかった。 → §14-11 で設計した。

### 14-11 第7版: 件の「答え待ちの印」をサーバーが持つ

#### 14-11-1 目的と見える変化

- 目的: K30 で、件の状態ファイルからは「質問の選択肢が出ている」状態を見分けられなかった（§14-10-10）。この版では、件の Claude Code の仕掛け（hooks）からサーバーへ「答え待ちが始まった・終わった」を知らせ、サーバーが件ごとに印を持つ。印がある間、case-say は何も書かずに断る。
- PO から見える変化: 件の窓に質問の選択肢・承認の確認が出ている間は、Opus が一文を送ろうとしても届かない（監査に「断った・理由 awaiting_input」が残る）。出ていない間は §14-10 のとおり一文が1回届く。
- 第6版の 14-10-3 の判定1〜10はそのまま使う。この版は判定7に「サーバーの印が無いこと」を足す（判定7の状態ファイルの確かめは残す。印と状態ファイルの両方が通るときだけ貼る）。

#### 14-11-2 観測事実（agent-console origin/main f503e9b）

- 件の設定は `buildCaseSettings`（server/case-sandbox.ts:446-472）が作る。記録用の hook を `addHandlers` で足し、宛先を `--post http://127.0.0.1:<port>/api/agent/case-activity` にする（:450）。件の見張り（guard）は PreToolUse の全道具に同期で入り、`onFailure: "block"`・`timeout: 10` を使っている（:453）。許可の既定は `defaultMode: "dontAsk"`（:460）。部屋の中から読めるファイルは名前で挙げた物だけで（`CASE_ROOM_READ_NAMED`・:212-221）、記録用 hook・見張りの hook はここに入っている。
- 共通の記録用 hook の一覧 `HOOK_SPECS`（server/activity-hooks.ts:53-72）は全窓に入る。Notification は使っていない（:49 のコメント）。`buildHandler`（:96-102。:98）は `async: false` を書かない限り非同期にする。`HookSpec`（:35-45）と `Handler`（:79-86）には `onFailure` の欄が無く、この道では block を付けられない。件の見張りは `buildCaseSettings` の中で生の形で直接書いている（case-sandbox.ts:453）。
- 件からの知らせの受け口 `handleCaseActivity`（server/http.ts:436-451）: Origin があれば 403 → `caseOfRequest`（:397-414。送り元の番号を lsof で pid に引き、親をたどって件の本体の記録（pid と開始時刻）に行き着いたらその件）→ 本文 → session_id の固定（違えば 409）→ 記録 → 204。件は合言葉を持たず、どの件からの知らせかはサーバーが pid で決める。
- 公式の説明書（code.claude.com/docs/en/hooks・2026-11-05 Opus が読んだ。Context7 は今月の上限で使えなかったため、本起動指示の代替で直接読んだ）: PreToolUse は AskUserQuestion と ExitPlanMode にも当たる。PermissionRequest は許可の確認が要る時に来る。Stop は利用者が止めた（割り込み）ときは来ない。hooks は既定で同期で、終わるまで Claude は先へ進まない（async を付けたものは待たない）。質問を Esc で断ったときに何の知らせが来るかは書かれていない（未確認）。`onFailure: "block"`（v2.1.295 から。件の本体は 2.1.318）: 失敗に数えるのは「起動できない・0 と 2 以外で終わる・時間切れ」。block のとき、失敗はその出来事で 2 で終わったのと同じ動きになる（PreToolUse は道具を止める・UserPromptSubmit は入力を捨てる・Elicitation は断る）。PermissionRequest では断りになる。Stop には効かない。2 で終わったときの動き: PermissionRequest は 2 を無視して確認がそのまま出る・Stop は Claude を止めずに続けさせる・PostToolUse は Claude に知らせるだけ。同じ出来事の hook は並んで動く（2026-11-05 Opus が説明書を読み直して確かめた。10回目の審査の指摘）。
- K30 の実測: 件の窓では許可の確認と計画の承認は出なかった（dontAsk のため。§14-10-10）。質問の選択肢は出た。

#### 14-11-3 変更後の仕組み

(a) 件だけに入る同期の hook（`buildCaseSettings` の中で足す。共通の `HOOK_SPECS` には入れないので、ふつうの窓は変わらない）。本体は新しい `hooks/case-wait-hook.mjs`。受け取った JSON から `hook_event_name`・`tool_name`・`tool_use_id`・`session_id` だけを取り、新しい受け口へ POST する。会話の中身（tool_input・prompt）は送らない。

| 出来事 | 絞り込み | 印 |
|---|---|---|
| PreToolUse | AskUserQuestion\|ExitPlanMode | 付ける |
| PermissionRequest | （全部） | 付ける |
| Elicitation | （全部） | 付ける |
| PostToolUse・PostToolUseFailure | AskUserQuestion\|ExitPlanMode | 外す |
| UserPromptSubmit | — | 外す |
| Stop | — | 外す |

- 作り方: `HOOK_SPECS`・`HookSpec`・`buildHandler` は使わず、変えない。`buildCaseSettings` の中で、件の見張り（case-sandbox.ts:453）と同じ生の形 `{ type: "command", command: p.nodeBin, args: [<case-wait-hook.mjs のパス>, "--post", "http://127.0.0.1:<port>/api/agent/case-wait"], timeout: 5 }` を各出来事の hooks に足す。`async` は書かない（書かなければ同期）。付ける3種だけ `onFailure: "block"` を足す。PreToolUse・PostToolUse・PostToolUseFailure は `matcher: "AskUserQuestion|ExitPlanMode"` の組、ほかは matcher 無しの組にする。
- すべて同期・`timeout: 5`。同期にする理由: 印を付ける知らせが届く前に選択肢が出ること、知らせの順が入れ替わる（外すが付けるより後に届く）ことを防ぐ。Claude は同期の hook が終わるまで先へ進まないので、知らせは起きた順にサーバーへ届く。
- 終わり方（2 は使わない。2 は出来事ごとに意味が違い、PermissionRequest では無視され、UserPromptSubmit では PO の入力を捨て、Stop では Claude を止めなくなるため）:
  - 付ける3種（PreToolUse・PermissionRequest・Elicitation）: サーバーが 204 を返したときだけ 0 で、何も出力しない。それ以外（接続できない・204 以外・5 秒を超える）は 1 で終わる。`onFailure: "block"` を付ける（件の見張りと同じ書き方。:453）。1 は失敗に数えられ、PreToolUse は道具を止め、PermissionRequest は断り、Elicitation は断る。サーバーへ届かなければ、その質問・確認を出させない。
  - 外す4種（PostToolUse・PostToolUseFailure・UserPromptSubmit・Stop）: 結果にかかわらず必ず 0 で終わり、何も出力しない。`onFailure` は付けない。届かなければ印が残るだけで、安全側。
- 部屋の中から hook の本体を読めるよう、`CASE_ROOM_READ_NAMED`（server/case-sandbox.ts:212-221）に `path.join(p.D, "hooks", "case-wait-hook.mjs")` を足す。足さないと起動できず、付ける側が block になって質問がいつも出なくなる。送り先 127.0.0.1 へつなぐ許しは、記録用 hook と同じ道を使う（記録用 hook が今つないでいる）。

(b) 新しい受け口 `POST /api/agent/case-wait`（server/http.ts。`handleCaseActivity` と同じ順で確かめる）: POST 以外 405 → Origin があれば 403 → `caseOfRequest` で件を決める（決まらなければ 401）→ 本文（4KiB まで。`hook_event_name` が 7つの出来事（PreToolUse・PermissionRequest・Elicitation・PostToolUse・PostToolUseFailure・UserPromptSubmit・Stop） のどれか、`tool_name` は文字列か無し、`tool_use_id` は (c) のとおり）→ `pinCaseSessionId` と同じ固定の確かめ（違えば 409）→ 印を更新して 204。表に無い出来事・形の違う本文は 400 で、印は変えない。

(c) 印の置き場: サーバーのメモリの `Map<caseId, { pending: Set<string>; since: number; lastEvent: string }>`。`pending` が空でなければ答え待ち（`awaiting`）。
   - PreToolUse は本文の `tool_use_id` を `pending` に足し、PostToolUse・PostToolUseFailure は同じ `tool_use_id` だけを外す（担当の道具の終わりが本体の質問の印を外さないため）。`tool_use_id` が無い・文字列でない本文は 400（付ける側の hook は 1 で終わり、質問を出させない。安全側）。
   - PermissionRequest・Elicitation は `tool_use_id` があればそれを、無ければ `"permission"`・`"elicitation"` の決まった名前を足す。これらは UserPromptSubmit か Stop でだけ外れる。
   - UserPromptSubmit と Stop は `pending` を空にする（本体の応答の区切り。本体が質問を出している間は本体の Stop は来ない）。件の本体の記録（`recordCaseMain`）と同じ所（server/sessions.ts）に置き、窓が終わったとき・一覧から外したときに一緒に消す。ファイルには書かない（正本は1か所）。窓を新しく作ったときは `awaiting: false` で始める（hooks は起動の時から入っているため）。つなぎ直した窓は §14-10-3(a)4 の `reattached` で case-say がもともと断るので、印の初期値の問題は起きない。

(d) case-say の判定7に足す: その件の `pending` が空でなければ 409（理由 `awaiting_input`）。判定は貼る前（7）と Enter の前（9 (3)）の両方で行う。

(e) 変えない物: 共通の `HOOK_SPECS`・ふつうの窓・画面のチャット・`handleCaseActivity`・件の部屋・Sales Anchor 側の見張りと許可。

#### 14-11-4 対象と対象外

- 対象（agent-console・PR 1本。便CS0）: server/case-sandbox.ts（件だけの hook を足す）、hooks/case-wait-hook.mjs と型（新規）、server/activity-setup.ts（写す）、`CASE_ROOM_READ_NAMED`（読める一覧に足す）、server/http.ts（受け口と K36 用の読み取り口）、server/sessions.ts（印の置き場と消し方）、試験、README。case-say（送る仕組み）は作らない。
- 対象（Sales Anchor）: 本書。
- 対象外: 送る仕組み（便CS1）、ADR-1033（便CS2）、ふつうの窓の hooks。

#### 14-11-5 代替案

| 案 | 採否 | 理由 |
|---|---|---|
| 件だけの同期の hook でサーバーに印を持たせる（本案） | 採用 | 出来事の時点で確実に知らせが来る。正本はサーバーのメモリ1か所。ふつうの窓に触らない |
| `claude agents --json` | 不採用 | 実測で質問の待ちを見分けられない（§14-10-10 別の方法1） |
| 状態ファイル | 不採用 | 実測で×（K30） |
| 画面の文字を読む（tmux の capture-pane） | 不採用 | 会話の中身を読むことになる。画面の形が版で変わると黙って外れる |
| 非同期の hook | 不採用 | 印が付く前に貼れる・知らせの順が入れ替わる |
| 今のまま PO が打つ（案 E） | 予備 | K36 が×のときの戻り先 |

#### 14-11-6 リスクと対処

| # | リスク | 対処 |
|---|---|---|
| R29 | 質問を Esc で断ったとき、外す知らせが来ない | 印が残り、case-say は断り続ける（安全側）。PO が件に何か打つ（UserPromptSubmit）と外れる。どの知らせが来るかを K36 で記録する |
| R30 | サーバーが落ちている・遅いとき、付ける知らせが届かない | 付ける出来事は `onFailure: "block"` で、届かなければ質問を出させない。この効き方を K36 ⑥で確かめる（効かなければ×） |
| R31 | 件が自分で受け口を呼び、印を外す | 影響は件自身の窓だけ（質問の選択肢に一文が入る）。件の許可は dontAsk で許可の確認は出ないので、ほかの窓や本番に届く承認は起きない。§14 R17・R24 と同じ水準 |
| R32 | 件が自分の settings を書き換えて hook を外す | 件の設定の置き場 D/cases は部屋の書き込み拒否に入っている（server/case-sandbox.ts:78 の `CASE_DENY_WRITE`）。外せても影響は R31 と同じ |
| R33 | 担当（サブエージェント）の道具の終わりが、本体の質問の印を外す | 印を `tool_use_id` ごとに持ち、Post は同じ id だけを外す（14-11-3 (c)）。担当の hook も件の本体の子から送られ、`caseOfRequest` は同じ件に決まる。K36 ⑦で担当からの質問が出るかを1回記録する（出なければ「場面なし」） |
| R35 | hook の終わり方の取り違え（2 で終わると PermissionRequest では無視・UserPromptSubmit では入力が消える・Stop では止まらない） | 2 は使わない。付ける側は 1、外す側は常に 0（14-11-3 (a)）。K37 の試験で終わり方を確かめる |
| R34 | 同期の hook で件の動きが遅くなる | 当たるのは 7つの出来事（PreToolUse・PermissionRequest・Elicitation・PostToolUse・PostToolUseFailure・UserPromptSubmit・Stop） だけ。K36 ⑧で1回あたりの時間を記録する（目安 1 秒未満） |

戻し方: agent-console を一つ前の版に戻す（hook と受け口が消える）。件を開き直せば設定は元に戻る。

#### 14-11-7 成功条件

| # | 基準 | 検証方法 |
|---|---|---|
| K36 | 本物の件の窓で、答え待ちの間だけ印が付き、答えると外れる | 便CS0 を反映した後、PO が件を1つ開き、Opus がサーバーの印を読むだけで記録（読む口は便CS0 で足す。件の id を渡すと `awaiting`（pending が空でないか）・`pendingCount`・`lastEvent`・`since` だけを返す、合言葉付きの読み取り）: ① 開いた直後 false ② 質問の選択肢が出ている間 true ③ 選んで答えた後 false ④ 質問の選択肢で Esc → 値と lastEvent をそのまま記録（true のままなら安全側で○。false なら外れた知らせの名前を記録） ⑤ PO が何か打った後 false ⑥ サーバーを止めた状態で質問を頼む → 選択肢が出ないこと（出たら×） ⑦ 担当からの質問（出なければ場面なし） ⑧ 7つの出来事（PreToolUse・PermissionRequest・Elicitation・PostToolUse・PostToolUseFailure・UserPromptSubmit・Stop） の hook の1回あたりの時間。①②③④⑤⑥が○なら○。×なら便CS1 に進まず案 E |
| K37 | ふつうの窓の hooks が変わっていない。件の hook が正しく入り、正しく終わる | vitest で: 件でない役割の設定に case-wait-hook が入らないこと。`buildCaseSettings` が返す設定の JSON に、表の7つの出来事それぞれへ case-wait-hook の handler が `async` の鍵無し・`timeout: 5` で入り、PreToolUse・PermissionRequest・Elicitation の handler にだけ `onFailure: "block"` の鍵が実際にあり、外す4種には無いこと。`HOOK_SPECS` の中身が変わっていないこと。`CASE_ROOM_READ_NAMED` に case-wait-hook.mjs があること。case-wait-hook.mjs を偽のサーバーで動かし、付ける3種は 204 で 0・接続できない／500／5 秒超で 1、外す4種はどれでも 0 で終わり、どの場合も何も出力しないこと（2 で終わる場合が無いこと） |
| K38 | 受け口の断りと印の数え方 | vitest: 件に決まらない 401・Origin 403・表に無い出来事 400・PreToolUse で tool_use_id 無し 400・session_id 違い 409 で、どれも印が変わらないこと。Pre(A)→Pre(B)→Post(B) で印が残り、Post(A) で空になること。PermissionRequest の印が Post では外れず UserPromptSubmit で外れること。本文に会話の中身が入っていても印にも監査にも残らないこと |

#### 14-11-8 実装の分け方

- 便CS0（クラウドの Sonnet・agent-console の PR 1本）: 14-11-3 (a)〜(c) と読み取り口・K37・K38。送る仕組みは作らない。
- PO: 便CS0 の版の反映。
- Opus と PO: K36。
- K36 が○なら、§14-10 の便CS1（判定7に 14-11-3 (d) を足す）・便CS2 へ。×なら案 E。

#### 14-11-9 外部事例

該当事例なし。理由: 自作の作業画面アプリの中で、Claude Code の hooks から自分のサーバーへ知らせる仕組みで、外部の数値事例では確かめられない。確かめは K36 の実測で行う。

#### 14-11-10 設計審査（第7版）

- 10回目（89e312a25・クラウドの Opus・2026-11-05）: REVISE（HIGH 1・MEDIUM 1・LOW 4）。
  - HIGH: hook が失敗を 2 で返すと、PermissionRequest では無視され、UserPromptSubmit では PO の入力が消え、Stop では Claude が止まらない。`onFailure` は 0 と 2 以外を失敗に数えるので効かない → 付ける側は 1・外す側は常に 0 にした（(a)・R35・K37）。Opus が説明書を読み直して確かめた。
  - MEDIUM: 部屋の中から読めるファイルの一覧に新しい hook が無く、起動できない → `CASE_ROOM_READ_NAMED` に足す（(a)・14-11-4・K37）。
  - LOW: 印が真偽1つで、担当の道具の終わりが本体の質問の印を外しうる → `tool_use_id` ごとに持つ（(c)・R33・K38）。spec に `async: false` が要る → (a) に書いた。行番号のずれ（dontAsk :460・注記 :49・HOOK_SPECS :53-72・handleCaseActivity :436）と R32 の引く所（:78）→ 直した。
  - 確かめて合っていた所（審査役）: 印の正本はメモリの1か所。ふつうの窓は変わらない。つなぎ直した窓は断る。K36〜K38 は○×で決まり、便CS1 より前にある。onFailure は説明書にあり、件の版で使える。
  - 未確認（審査役）: Esc で断ったときの知らせ・割り込みで Stop が来るか・AskUserQuestion に PermissionRequest が来るか（説明書に無い → K36）。
- 11回目（babde1ad7・クラウドの Opus・2026-11-05）: REVISE（MEDIUM 1・LOW 1）。10回目の HIGH・MEDIUM は直っていた。直しから生まれた新しい穴は無し。
  - MEDIUM: 「spec に async:false」で `buildHandler` の道を使うと、`HookSpec`・`Handler` に `onFailure` の欄が無く block を付けられない → 件の見張り（case-sandbox.ts:453）と同じ生の形で `buildCaseSettings` に直接書く、に決めた（(a)）。共通の部品を変えないので、ふつうの窓に触れない。K37 に「設定の JSON に onFailure の鍵が実際にあること」を書いた。Opus が実物で確かめた。
  - LOW: buildHandler の行番号 → :96-102・:98 に直した。
  - 未確認（審査役）: 担当（サブエージェント）の hook の session_id が本体と同じか（違えば 409 で質問が止まる。安全側。K36 ⑦で記録する）。Esc・割り込みの知らせ（K36）。
- 12回目（af91d27c2・クラウドの Opus・2026-11-05）: APPROVE（LOW 1）。11回目の MEDIUM は直っていて、件の見張り（case-sandbox.ts:453）の形と同じ。公式の説明書と食い違い無し。行番号は全部合う。新しい穴は無し。
  - LOW: 受け口の本文・R34・K36 ⑧の「6種」は表の行の数で、出来事の名前は7つ（PostToolUse と PostToolUseFailure は別）→ 3か所とも7つの名前を並べて書いた。
  - 未確認（審査役）: Elicitation に onFailure block が効くか（説明書の該当節を読み切れず）・担当の hook の session_id・Esc と割り込みの知らせ → どれも K36 で実測する。

#### 14-11-11 前提の誤り（2026-11-05 16時台・Opus の読み直し）

判定: 第7版は REVISE（12回目の APPROVE を取り消す）。設計が守ろうとした「選択肢の画面」が、件の窓では出ない作りだった。審査役も Opus も、件の窓の起動台本を読んでいなかった。

観測事実:
- 件の窓の起動台本 `ops/shell/ccdiscord.zsh:72`（agent-console v0.50.1 入り版）は `--tools "Bash,Read,Edit,Write,Glob,Grep,Agent,TodoWrite"` で道具を絞る。AskUserQuestion・EnterPlanMode・ExitPlanMode は入っていない。同じ行に `--strict-mcp-config --disallowedTools "mcp__*"`・`--permission-mode dontAsk` がある。
- 件の窓の記録（activity/events-20261105.jsonl・session 79484388-…）で、件の AI は 4 回「AskUserQuestion は使えない」と答え、質問を文で書いた（11:34:54・11:54:42・12:17:50 ほか。10:58:25 の回は Stop の記録が無い）。EnterPlanMode も使えないと答えた（10:59:19）。
- 11:36:04 の回で、計画の段階（Shift+Tab で入る）に入った窓が、計画の保存先 「case-home/427a63ce-…/plans/1-fizzy-planet.md」 への Write を case-guard に止められた。ExitPlanMode も無いので、AI は計画の段階から自分で出られない。
- 件の窓（main pid 97478）は 16:18 時点で無い。open-sessions.json・tmux にも無い。case-home の sessions/ は 12:55 に空になった。終わった理由の記録は見つからない（server.err.log の最終更新は 10:58）。

ここから言えること（事実の組み合わせ）:
- PreToolUse/PostToolUse の `AskUserQuestion|ExitPlanMode` は、件の窓では起きない。PermissionRequest は dontAsk のため画面に出ない。Elicitation は MCP が切られているので起きない。第7版の旗は、件の窓では立つ場面がほぼ無い。
- 件の窓の「待ち」は、AI が文で質問して Stop した状態だけ。このとき case-say が貼る文は、そのまま「答え」として届く。K30 の「選択肢の画面に文が入る」危険は、この起動の形では起きない。
- 残る穴は計画の段階: 人が Shift+Tab で入れる。保存が止められ、AI が自分で出られない。

未確認:
- 件の窓が 12:55 ごろに終わった理由（人が閉じたか・異常終了か）。
- 計画の段階の中で case-say が貼った文がどう扱われるか。

次の一手（PO の決めごと）: 第7版を進めるか・件の窓の形に合わせて設計を小さくし直すか。

### 14-12 第8版: 件の窓を「聞かずに進む形（dontAsk）」から外さない（2026-11-05・PO「1」で小さく作り直し）

**状態**: 設計審査済み（2026-11-05・5回目の審査で APPROVE〈HIGH・MEDIUM なし〉。LOW 2件〈K6(a) の止め方の命令・始める前の一覧の確かめ〉を反映）。同じ AI の系統による審査で、独立した第二者レビューではない。第7版（答え待ちの印）は §14-11-11 の前提の誤りにより取りやめ。

#### 14-12-1 目的と成功条件

PO の言葉: 「件の窓の今の作りに合わせて設計を小さく作り直す…計画の段階で窓が抜け出せない穴だけを直します」（PO 選択「1」）。

| 基準 | 検証方法 |
|---|---|
| K1 件の窓で Shift+Tab を押しても形が変わらない（画面下の帯に plan / accept edits / manual の表示が出ない） | 本物の件の窓へ tmux send-keys で BTab を3回送り、①画面の写し（tmux capture-pane）に `plan mode on`・`accept edits on`・`manual mode on` が0件（ほかの dontAsk 以外の形の表示も0件） ②続けて K3 の「ls して」が通る。○×は①②だけで決める（会話記録の形の項目は参考として写すだけ） |
| K2 本体の会話で形が dontAsk でないときは道具を1つも通さない（許可の問い合わせ画面が出ない＝case-say の貼り付けが問い合わせ画面に入らない） | case-guard の試験: `agent_id` が無く `permission_mode` が `plan`・`default`・`acceptEdits`・`auto`・`bypassPermissions` のとき終了コード2。`dontAsk`・項目なし・`agent_id` ありのときは今と同じ判定（同じ入力で今の版と同じ終了コード） |
| K3 ふだんの件の作業が今までどおり通る（下請けの AI を含む） | 本物の件の窓で ①「ls して」と頼み Bash が通る ②「Agent で下請けを1つ動かして README を読ませて」と頼み、下請けの中の Read が通る（どちらも会話記録に tool_result があり `case-guard:` の拒否の文が無い）。任意の確かめ: 下請けを動かしている途中で `/plan` を送り、画面の写しに許可の問い合わせ画面が出ないこと（出たら PO へ戻す） |
| K4 件の AI が keybindings.json を書き換えられない | case-sandbox の試験: 部屋の書き込み拒否の正規表現に 「CH/keybindings.json」 が一致する。case-guard でも CH は作業場の外なので Edit/Write は止まる（既存） |
| K5 既存の試験がすべて通る | agent-console の CI（vitest・型検査）緑 |
| K6 計画の形に入っても、件を開き直せば dontAsk に戻る | 本物の件の窓で「/plan README を読んで」と送る→道具が `case-guard: permission mode is not dontAsk` で止まる。続けて次の2つを別々に行う。(a) 始める前に、復元の一覧（open-sessions.json）に件の claudeSessionId があることを確かめる。そのうえでこの順で行う: ①agent-console を止める（`launchctl kill SIGTERM gui/<uid>/local.agent-console.server`。AI はサーバー停止の見張り〈agent-console README.md:64〉で止められるので、PO が `!` で打つ。サーバーの pid が消えたことを確かめてから②へ。launchd が自分で起こし直したら、その回は判定せずやり直す） ②件の tmux セッションを kill-session ③agent-console を起動する（`launchctl kickstart gui/<uid>/local.agent-console.server`）（先に tmux を落とすと、動いている agent-console が [server/restore.ts:65](https://github.com/GEN-RYU-System/agent-console/blob/f503e9bc7c92ec7d9787f7c1d24018564d115d77/server/restore.ts#L65)・`:94` で件を復元の一覧から外し、誤って×になる）。③の後、復元の一覧（open-sessions.json）に件の claudeSessionId が残っていることを確かめる。件の役割には `restoreCommand` がある（[agent-console.config.json:48](https://github.com/GEN-RYU-System/agent-console/blob/f503e9bc7c92ec7d9787f7c1d24018564d115d77/agent-console.config.json#L48)。[server/config.ts:160-161](https://github.com/GEN-RYU-System/agent-console/blob/f503e9bc7c92ec7d9787f7c1d24018564d115d77/server/config.ts#L160-L161) が禁じるのは `resumeCommand` だけ）ので、復元の道 [server/restore.ts:179](https://github.com/GEN-RYU-System/agent-console/blob/f503e9bc7c92ec7d9787f7c1d24018564d115d77/server/restore.ts#L179)→[server/sessions.ts:564](https://github.com/GEN-RYU-System/agent-console/blob/f503e9bc7c92ec7d9787f7c1d24018564d115d77/server/sessions.ts#L564) で AC_RESUME_ID が渡り、`ccdiscord.zsh:73-75` が同じ会話を `--resume` で開く。`:72` の `--permission-mode dontAsk` が一緒に渡る）→同じ会話で「ls して」が通る。(b) 画面で件を閉じ、新しい件として開く（件の役割は `resumeCommand` を持てない [server/config.ts:160-161](https://github.com/GEN-RYU-System/agent-console/blob/f503e9bc7c92ec7d9787f7c1d24018564d115d77/server/config.ts#L160-L161)。会話の続きは失われる）→「ls して」が通る。どちらかが×なら PO へ戻す |
| K7 入れた時点で開いている件の窓にも（１）が効く | v0.50.2 を入れる前から開いていた件の窓で、入れた後に K1 と同じ手順を行い同じ結果 |

#### 14-12-2 変更前→変更後（agent-console・origin/main f503e9b = v0.50.1）

（１）キーの割り当てを外すファイルを件ごとに書く
- 変更前: [server/case-sandbox.ts:398-421](https://github.com/GEN-RYU-System/agent-console/blob/f503e9bc7c92ec7d9787f7c1d24018564d115d77/server/case-sandbox.ts#L398-L421) `rewriteCaseClaudeJson` は case-home の 「.claude.json」 だけを書き直す。case-home は `ops/shell/ccdiscord.zsh:61` で件の窓の設定置き場（CLAUDE_CONFIG_DIR）。
- 変更後: 同じファイルに `writeCaseKeybindings(CH)` を足し、「CH/keybindings.json」 に次を `writeAtomicSync` で書く。[server/sessions.ts:627](https://github.com/GEN-RYU-System/agent-console/blob/f503e9bc7c92ec7d9787f7c1d24018564d115d77/server/sessions.ts#L627) の `checkCaseSandbox` の行の直後、`openTerminal` の前（`room` が null でないとき）に呼ぶ（実装時の訂正: 当初は `:626` の `prepareCaseRoom(id)` の直後としたが、そこでは case-home が無いとき `checkCaseSandbox` の⑩「case-home is missing」より先に書き込みが失敗し、既存の試験 [tests/unit/sessions.case.test.ts:374](https://github.com/GEN-RYU-System/agent-console/blob/f503e9bc7c92ec7d9787f7c1d24018564d115d77/tests/unit/sessions.case.test.ts#L374) が落ちた。`checkCaseSandbox` も `openTerminal` も新規・つなぎ直しの両方で通るので、意図は変わらない）。こうすると新しく開くときだけでなく、つなぎ直し（[server/sessions.ts:691-698](https://github.com/GEN-RYU-System/agent-console/blob/f503e9bc7c92ec7d9787f7c1d24018564d115d77/server/sessions.ts#L691-L698) の probe で既存の窓に戻る道。`beforeNew` は `:703` でしか呼ばれない）でも書かれる。書けなければ `CaseSandboxUnavailableError`。これは `prepareCaseRoom` が room.sb などを書けないときと同じ扱いで、つなぎ直しでも今すでに同じ理由で開けなくなりうる。CH は agent-console が作って持つ置き場なので、書けないのは置き場そのものが壊れたときだけ。その場合に窓を開かないのは今と同じ考え方なので、つなぎ直しだけ警告で続ける分け方はしない（開けない件が増える道は、CH が壊れたときに限られることを受け入れる）。
  ```json
  {"bindings":[{"context":"Chat","bindings":{"shift+tab":null}}]}
  ```
- 根拠: 公式 keybindings.md「Unbind default shortcuts」（action を null で外す）、`chat:cycleMode` の既定は Shift+Tab（Windows の古い端末以外）。claude 2.1.318 本体に 「keybindings.json」 と `"bindings" array` の形の検査がある（/tmp/CC報告ファイル/plancheck/kb-strings.txt）。CLAUDE_CONFIG_DIR 側を読むかは未確認→K1 で判定。公式 keybindings.md:17「ファイルの変更は自動で検出され、再起動なしで効く」により、開いている窓もつなぎ直しで書かれた時点で効く（K7 で判定）。

（２）件の AI がそのファイルを書けないようにする
- 変更前: [server/case-sandbox.ts:249-252](https://github.com/GEN-RYU-System/agent-console/blob/f503e9bc7c92ec7d9787f7c1d24018564d115d77/server/case-sandbox.ts#L249-L252) `chSettingNames` の書き込み拒否は `remote-settings.json … settings.json|agents|hooks|commands|skills|CLAUDE.md`。
- 変更後: 同じ並びに keybindings.json の名前を足す（足した後の形: [server/case-sandbox.ts:250](https://github.com/GEN-RYU-System/agent-console/blob/b467656c721440c46307fe9f82d0f5f707bbd824/server/case-sandbox.ts#L250)）。

（３）形が dontAsk でなければ道具を止める（安全網）
- 変更前: `ops/case/case-guard.mjs:75-111` `decide` は道具の名前と道だけを見る。
- 変更後: `decide` の先頭（`:76` の前）で `input.agent_id === undefined && typeof input.permission_mode === "string" && input.permission_mode !== "dontAsk"` なら `block("permission mode is not dontAsk; ask the person to close and reopen this case")`。項目が無いとき・`agent_id` があるとき（下請けの AI の中の道具）は今と同じ判定。
- 根拠: 公式 hooks.md:737 共通入力の `permission_mode`（"default","plan","acceptEdits","auto","dontAsk","bypassPermissions"）。hooks.md:255・:745 下請けの中の道具では `agent_id` が入る。sub-agents.md:596 本体が dontAsk のとき下請けは自分の設定の形で動く（組み込みの下請けの形は未確認）ので、下請けには形の検査をかけない。本体が計画の形のときは本体の Agent 呼び出しがこの検査で止まるため、計画の形の下請けは生まれない。

（４）取りやめ（2回目の審査で根拠の読み違いと分かったため）
- 前の案: `buildCaseSettings` の deny に `"ExitPlanMode"` を足して、開き直しで計画の形に戻らないようにする。
- 取りやめの理由: 公式 sessions.md「permission mode on resume」では、端末で `--resume` するとき `--permission-mode` を渡すと戻るはずの形はそれで上書きされる。件の起動台本 `ops/shell/ccdiscord.zsh:72` は前から `--permission-mode dontAsk` を `--resume`（:73-75）と一緒に渡している。`--resume` が付くのは agent-console の再起動時の復元（件の役割に `restoreCommand` がある [agent-console.config.json:48](https://github.com/GEN-RYU-System/agent-console/blob/f503e9bc7c92ec7d9787f7c1d24018564d115d77/agent-console.config.json#L48)。[server/restore.ts:179](https://github.com/GEN-RYU-System/agent-console/blob/f503e9bc7c92ec7d9787f7c1d24018564d115d77/server/restore.ts#L179)→[server/sessions.ts:564](https://github.com/GEN-RYU-System/agent-console/blob/f503e9bc7c92ec7d9787f7c1d24018564d115d77/server/sessions.ts#L564)）だけで、画面で閉じて開くと新しい会話になる（[server/config.ts:160-161](https://github.com/GEN-RYU-System/agent-console/blob/f503e9bc7c92ec7d9787f7c1d24018564d115d77/server/config.ts#L160-L161)）。どちらの道でも足さなくても dontAsk で始まる（K6 の (a)(b) で判定）。足すと K6 で効き目を見分けられないので、変更を増やさない。

（５）版を v0.50.2 にする（package.json・package-lock.json・extension/manifest.json・docs/CHANGELOG.md。#98 と同じ書き方。CHANGELOG に戻し方 `bash scripts/ac-update.sh v0.50.1` の1行）。

#### 14-12-3 触らない範囲

case-say 本体・Discord 側・room.sb の作り（CH は読み取り subpath で許可済み [server/case-sandbox.ts:209-221](https://github.com/GEN-RYU-System/agent-console/blob/f503e9bc7c92ec7d9787f7c1d24018564d115d77/server/case-sandbox.ts#L209-L221)）・起動台本 `ops/shell/ccdiscord.zsh`・見張り類・salesanchor 側のコード。第7版の答え待ちの印は作らない。

#### 14-12-4 代わりの案と選ばない理由

- `/plan` を UserPromptSubmit で止める: 組み込みの `/plan` がこの合図を通るか未確認。（３）で問い合わせ画面は出ないので今回は入れない。
- plansDirectory を部屋の中へ向ける: 計画は保存できても ExitPlanMode が無いので抜けられない穴は残る。

#### 14-12-5 危険と対処・戻し方

- `/plan` を頭に付けた依頼で計画の形に入ると、Shift+Tab を外したので戻れない。対処: （３）で道具が止まり、拒否の文で AI が「件を閉じて開き直してください」と伝える。開き直すと `ccdiscord.zsh:72` の `--permission-mode dontAsk` で始まる。ただし画面で閉じて開くと新しい件の会話になり、それまでの会話の続きは失われる（K6 (b)）。続きを残したいときは agent-console の再起動で同じ会話を `--resume` で開く道がある（K6 (a)）。K6 が×なら PO へ戻す。
- claude が CLAUDE_CONFIG_DIR 側の keybindings.json を読まない場合 K1 が×。対処: ×なら（１）（２）を戻すか（３）だけ残すかを PO に聞く。
- 下請けを動かしている途中で本体が計画の形に入った場合: 公式 sub-agents.md は「本体が plan のとき下請けも plan」とするが、すでに動いている下請けの形が途中で変わるかは書かれていない（未確認）。変わると、下請けの道具は `agent_id` があるので（３）を素通りし、問い合わせ画面が出うる。Shift+Tab を（１）で外したので、途中で入る道は `/plan` を頭に付けた依頼だけになる。実物の確かめは K3 の後の任意の確かめ「下請けを動かしている途中で `/plan` を送る」で行い、問い合わせ画面が出たら PO へ戻す。
- 入れた時点で開いている件の窓: 版を入れると agent-console が再起動し、開いている件はつなぎ直し（[server/sessions.ts:691-698](https://github.com/GEN-RYU-System/agent-console/blob/f503e9bc7c92ec7d9787f7c1d24018564d115d77/server/sessions.ts#L691-L698)）になる。つなぎ直しでは claude は起動し直さないので、その時点で計画の形に入っている窓はそのまま残る（閉じて開き直すよう PO に伝える）。（１）はその時に書かれる。一方、開いている窓の hook が新しい版の case-guard を指すか（起動時の settings の道が realpath で旧版の置き場を指したままか）は未確認。K7 で（１）を判定し、（３）は新しく開いた窓（K6）で判定する。K7 が×なら、開いている件の窓を閉じて開き直すよう PO に1行で伝える。
- 項目なしの扱い: `permission_mode` が来ない版の claude では今と同じ判定になる（強めない）。今の本体（2.1.318）が送るかは K6 の拒否の文で確かめる。
- 戻し方: `bash scripts/ac-update.sh v0.50.1`（docs/CHANGELOG.md の既存の書き方）。

#### 14-12-6 維持の仕組み

case-guard の試験（K2）と case-sandbox の試験（K4・ファイルの中身）を agent-console の CI に入れ、外れたら赤になる。

### 14-13 第9版: K30 を件の窓の今の形で決め直し、第6版（§14-10）で作る（2026-11-05・PO「1」）

**状態**: 設計案（審査前）。PO の判断（2026-11-05・チャット）: 選択肢「1. 昼の×の判定を、今の前提で決め直します。そのうえで、一文を送る仕組みを作ります」に「1」。PO への説明では「判定を決め直したら、設計の審査をもう一度通し、その後クラウドで作り、合流と導入まで進める」と伝えた。第6版の PO 承認（§14-10-10「1. この設計で作り始めてよい」）は、K30・K35 が通ることを条件にしていた。本版はその K30 の判定の決め直しで、送る仕組み（§14-10-3）は変えない。

#### 14-13-1 決め直す理由（観測事実）

- K30 の ④（質問への答え待ち）の×は、件の窓に「選択肢の画面」が出たという前提で付けた（§14-10-10）。§14-11-11 で、その前提が誤りと分かった: 件の窓の起動 `ops/shell/ccdiscord.zsh:72`（agent-console v0.50.2 入り版でも同じ行）の `--tools "Bash,Read,Edit,Write,Glob,Grep,Agent,TodoWrite"` に AskUserQuestion・EnterPlanMode・ExitPlanMode は無い。件の AI は 11:54:42 に「AskUserQuestion は使えない」と答え、質問を文で書いて Stop した。PO が 11:54:57 に見た「選択肢」はこの文で、そのとき status が `idle` だったのは正しい読み（入力を待つ状態）。
- ③（許可の確認）: 同じ行の `--permission-mode dontAsk` で、許可の確認は画面に出ない（§14-10-10 の ③ の観測: ファイルを作る依頼でも確認なし）。v0.50.2（§14-12）で、本体の形が dontAsk でないとき道具を1つも通さない（K2・agent-console `ops/case/case-guard.mjs` の `decide` の先頭）。Shift+Tab は外した（K1 合格・2026-11-05 22:28）。開き直しと再起動の復元でも dontAsk で始まる（K6 (a)(b) 合格・2026-11-05 22:47・23:23）。
- ⑤（計画の承認待ち）: ExitPlanMode が道具に無いので、承認の画面は出ない（§14-11-11）。`/plan` を頭に付けた依頼で計画の形に入った場合も、道具は止まり、承認の画面は出ない（§14-12-5）。
- 起動の時の画面: 件の 「CH/.claude.json」 は agent-console が毎回書き直し、`hasCompletedOnboarding: true` と、作業場所の `hasTrustDialogAccepted: true` を入れる（agent-console [server/case-sandbox.ts](https://github.com/GEN-RYU-System/agent-console/blob/b467656c721440c46307fe9f82d0f5f707bbd824/server/case-sandbox.ts) `rewriteCaseClaudeJson`）。最初の案内と「このフォルダを信頼しますか」の画面は出ない。
- 調子を聞く画面（"How is Claude doing?"）: 起動は `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` を入れる（`ccdiscord.zsh:62`）。公式 env-vars の `CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY` の行に「`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` が入っているときも調子を聞く画面は出ない（`CLAUDE_CODE_ENABLE_FEEDBACK_SURVEY_FOR_OTEL` で戻さない限り）」とある（code.claude.com/docs/en/env-vars・2026-11-05 Opus が直接読んだ。Context7 は今月の上限で使えなかった）。起動の台本に `CLAUDE_CODE_ENABLE_FEEDBACK_SURVEY_FOR_OTEL` は無い。
- MCP の問い合わせ（Elicitation）: `--strict-mcp-config --disallowedTools "mcp__*"` で MCP が無いので起きない（§14-11-11）。

#### 14-13-2 決め直した判定

- K30: 条件付きの○。①入力待ち `idle`・②作業中 `busy` は実測で見分けられた（§14-10-10）。③④⑤の画面は、件の窓の今の起動の形では出ない（14-13-1）。このため判定7（状態ファイルで `idle`・待ちのキーなしのときだけ貼る）で、文が入るのは「入力を待つ欄」だけになる。
- 条件（どれかが崩れたら案 E に戻す）: (1) 件の起動の道具の並びに AskUserQuestion・EnterPlanMode・ExitPlanMode・MCP が入っていない (2) `--permission-mode dontAsk` で起動する (3) case-guard が dontAsk でない形の道具を止める (4) `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` が入っていて、調子を聞く画面を戻す変数が無い。
- 条件を守る仕組み: 既存の [tests/unit/ccdiscord-zsh.test.ts](https://github.com/GEN-RYU-System/agent-console/blob/b467656c721440c46307fe9f82d0f5f707bbd824/tests/unit/ccdiscord-zsh.test.ts) の2つの試験（引数の確かめと環境変数の並びの確かめ）が (1)(2)(4) を守る（K40。第10版で新しい試験は作らないと決めた。§14-13-7 M3）。(3) は K2 の試験が既に守る。起動の台本を変える PR はこの試験で赤になり、§14-13 を読み直す合図になる。
- `claude agents --json` の確かめ（判定7 の後半）: 件の本体は、ふつうの置き場の一覧に出ない（§14-10-10 別の方法1）。判定7 の「行があれば、その行も idle で waitingFor が無い」は、行が無いときは状態ファイルだけで決める。この扱いは第6版のままで変えない。
- 判定3 の補助の確かめ（本体の comm が `claude`）: 第6版の 14-10-3 の判定には無い（第5版の §14-3 の判定）。第6版で作るので、合わないことは影響しない。

#### 14-13-3 残る危険と対処

| # | 危険 | 対処 |
|---|---|---|
| R35 | `/plan` を頭に付けた依頼で計画の形に入った件へ一文が入る | 件の AI に文が届くだけで、道具は case-guard が止め、承認の画面は無い（§14-12）。件の返事で「閉じて開き直してください」と出る。外へ何かが漏れる道にはならない。K32 で場面があれば記録する |
| R36 | claude の版が上がり、件の窓に新しい種類の選ぶ画面が加わる | 件の起動の台本は `DISABLE_AUTOUPDATER=1`（`ccdiscord.zsh:63`）。版は agent-console の版の更新のときだけ変わる。K32 の測りを版の更新のあとにもう一度行い、選ぶ画面が出たら案 E に戻して PO に報告する |
| R37 | 件の AI が文で質問して止まっている間に、Opus の一文が「答え」として届く | 一文は固定（手順ファイルを読んで順に行う）で、件はそれを答えとして読む。手順書は PO が承認したものだけ（§14-10-3 (e)）。答えの代わりに手順を進めてよいかは、手順書の側で「件の質問が残っていれば、先に PO へ戻す」と書く（便2b-3b の手順書の書き換えで入れる） |

#### 14-13-4 成功条件（足すもの）

| 基準 | 検証方法 |
|---|---|
| K40 起動の台本が 14-13-2 の条件 (1)(2)(4) を満たす | 第10版で既存の試験を正本にした（§14-13-7 M3）: agent-console [tests/unit/ccdiscord-zsh.test.ts](https://github.com/GEN-RYU-System/agent-console/blob/b467656c721440c46307fe9f82d0f5f707bbd824/tests/unit/ccdiscord-zsh.test.ts) の引数の試験（`--tools` の完全一致・`--permission-mode dontAsk`・`--strict-mcp-config`・`mcp__*`）と環境変数の並びの完全一致の試験。新しい試験は作らない。どれかが外れたら赤 |
| K32 の足し（測り） | 本物で一文を送る前と後に、件の窓の画面の写し（tmux capture-pane）を取り、選ぶ画面（番号の選択肢・Yes/No）が0件であることを確かめる |

K31・K33・K34・K35 は第6版のまま。K35 は○（§14-10-10）。

#### 14-13-5 実装の分け方（第6版 §14-10-8 から変えるもの）

- 測定 K30: 本版の判定で済み（条件付きの○）。
- 便CS1（クラウドの Sonnet・agent-console の PR 1本）: §14-10-3 (a)(b)・判定4b（§14-13-7 M1）・README・K31・K34・K42 の単体。K40 は既存の2つの試験に注を足すだけ（§14-13-7 M3）。
- 便CS2・PO の反映・K32・K33 は第6版のまま。

#### 14-13-6 外部事例

該当事例なし。理由: 判断の中心は、自作の件の窓の起動の形で出うる画面の洗い出しで、外部の数値事例では確かめられない。確かめは K40 と K32 の実測で行う。

#### 14-13-7 設計審査（第9版）と直し（第10版）

**審査**（2026-11-05 23:54〜23:58 JST・クラウドの Opus・読むだけ・salesanchor e1b603aa1 / agent-console b467656）: REVISE。A1・A2・A3・A5・A7 は○。A4・A6 は×。必須1件・推奨3件。

- M1（必須）: R36 の「版は agent-console の版の更新のときだけ変わる」は実物と合わない。設定は `"claudeBin": "claude"`（agent-console [agent-console.config.json:8](https://github.com/GEN-RYU-System/agent-console/blob/b467656c721440c46307fe9f82d0f5f707bbd824/agent-console.config.json#L8)）。件を開くたびに PATH から実体の道を引き直す（[server/sessions.ts](https://github.com/GEN-RYU-System/agent-console/blob/b467656c721440c46307fe9f82d0f5f707bbd824/server/sessions.ts) の `prepareCaseRoom` → `resolveClaudeReal`）。`DISABLE_AUTOUPDATER=1` が止めるのは件の中の更新だけ。PO のふつうの claude が更新されると、件の版も変わる。
- M2（推奨）: 下請け（Agent）が動いている途中に `/plan` で計画の形に入ったときの確認画面は、4条件の外にある。case-guard は `agent_id` があるとき形を見ない（`ops/case/case-guard.mjs:76`）。K3 の下請けの確かめも未実施。
- M3（推奨）: K40 は既存の試験とほぼ同じ。[tests/unit/ccdiscord-zsh.test.ts:94-111](https://github.com/GEN-RYU-System/agent-console/blob/b467656c721440c46307fe9f82d0f5f707bbd824/tests/unit/ccdiscord-zsh.test.ts#L94-L111) が台本を実際に動かして `--tools`・`--permission-mode dontAsk`・`--strict-mcp-config`・`mcp__*` を確かめ、同 `:207` 付近が `CLAUDE*`・`ANTHROPIC*` の環境変数の並びを完全一致で確かめる（`CLAUDE_CODE_ENABLE_FEEDBACK_SURVEY_FOR_OTEL` が入れば赤になる）。
- M4（推奨）: §14-10-2 の行番号は f503e9b のまま。b467656 ではずれる（例: `recordCaseMain` の呼び出しは sessions.ts:632）。

**直し**:

- M1 → 判定4 に足す（4b）: 件を開くとき、サーバーは `prepareCaseRoom` が解いた claude の実体の道を、その件の記録（メモリ）に一緒に残す。実体の道の最後の名前が `^\d+\.\d+\.\d+$` の形なら、それを件の claude の版とする（観測: PO の Mac で `~/.local/bin/claude` の実体は `~/.local/share/claude/versions/2.1.318`、`claude --version` は `2.1.318 (Claude Code)`。2026-11-06 Opus が実行）。case-say は、件の版が config の新しい項目 `caseSayClaudeVersions`（文字列の並び。コードの既定は空＝どの件にも送らない）に入っているときだけ進む。形に合わない・並びに無いときは 409（理由 `claude_version_unverified`）。版は監査の caseSay・caseSayRefused の行にも書く。同梱の [agent-console.config.json](https://github.com/GEN-RYU-System/agent-console/blob/b467656c721440c46307fe9f82d0f5f707bbd824/agent-console.config.json) には `["2.1.318"]` を入れる。版を足す手順（第11版で置き換え。§14-13-8 M2）: 版が変わったら、PO が件を1つ開く → PO が K41 (a)(b) の頼み事と K32 の一文を打つ → Opus が画面の写しと状態ファイルを読むだけで、選ぶ画面0件と K41 の○を確かめる → 版を足す PR を出し、審査を通してから入れる。R36 の対処はこれに置き換える。
- M2 → 成功条件 K41 を足す（実装は止めない。K32 の前に測る）: 本物の件の窓で、(a) 下請けにフォルダの一覧を頼み、通ることを確かめる（K3 の下請けの確かめ）。(b) `/plan` を頭に付けて下請けを使う依頼をし、下請けが動いている間と終わった後の画面の写し・状態ファイル（`pid`・`status`・名前に `wait` を含むキー）を記録する。確認画面が出ている間に、状態ファイルが `idle` で待ちのキーなしと読めたら×（判定7 をすり抜ける）。×なら case-say を使わず案 E に戻し、PO に報告する。確認画面が出ない、または出ている間 `idle` 以外か待ちのキーありなら○。
- M3 → K40 は新しく作らない。既存の [tests/unit/ccdiscord-zsh.test.ts](https://github.com/GEN-RYU-System/agent-console/blob/b467656c721440c46307fe9f82d0f5f707bbd824/tests/unit/ccdiscord-zsh.test.ts) の2つの試験（引数の確かめと環境変数の並びの確かめ）を K40 の正本とする。便CS1 では、この2つの試験に「§14-13-2 の条件 (1)(2)(4) を守る試験。変えるときは design §14-13 を読み直す」の注を足すだけにする。
- M4 → 便CS1 は agent-console b467656 を基準にする。§14-10-2 の行番号は f503e9b のときの物なので、実装役は関数名・文字で今の行を探し直す。名前が見つからない・振る舞いが §14-10-2 と違うときは作らずに止める。

**成功条件の足し**:

| 基準 | 検証方法 |
|---|---|
| K42 版が並びに無い件には送らない | vitest: 件の実体の道の最後の名前が並びに無い版・版の形でない名前のとき、409 `claude_version_unverified` で書き込み0回。`caseSayClaudeVersions` が既定の [] のときも、どの件にも同じく 409 で書き込み0回（第11版）。並びにある版なら判定5以降へ進む |
| K41 下請けの途中の確認画面で判定7 をすり抜けない | 上の M2 の (a)(b)。本物の件の窓で Opus が読むだけ（K32 の前） |

**状態**: 第10版の直しを入れた設計案。再審査は §14-13-8。

#### 14-13-8 設計審査（第10版）と直し（第11版）

**審査**（2026-11-06 00:03〜00:06 JST・クラウドの Opus・読むだけ・salesanchor 992539219 / agent-console b467656）: REVISE。B1〜B6 は○、B7 は×。必須1件・推奨2件。B1 の根拠: 実体の道は `resolveClaudeReal` が realpath で解き（agent-console [server/case-sandbox.ts:433-449](https://github.com/GEN-RYU-System/agent-console/blob/b467656c721440c46307fe9f82d0f5f707bbd824/server/case-sandbox.ts#L433-L449)）、その値が `AC_CLAUDE_BIN` になり（[server/sessions.ts:476](https://github.com/GEN-RYU-System/agent-console/blob/b467656c721440c46307fe9f82d0f5f707bbd824/server/sessions.ts#L476)）、台本はその道を exec する（`ops/shell/ccdiscord.zsh:31`・`:78`）。（訂正 2026-11-06: b467656 の ccdiscord.zsh は77行で、exec は `:76`。`:31` はその道で版を読む行）

- M1（必須）: §14-13-4 の K40 の行・§14-13-5 の便CS1・§14-10-4 の対象が第10版に合っていない。→ 直した（K40 は既存の2つの試験、便CS1 に 4b・K42、対象に [server/sessions.ts](https://github.com/GEN-RYU-System/agent-console/blob/b467656c721440c46307fe9f82d0f5f707bbd824/server/sessions.ts) と [agent-console.config.json](https://github.com/GEN-RYU-System/agent-console/blob/b467656c721440c46307fe9f82d0f5f707bbd824/agent-console.config.json)）。
- M2（推奨）: 版を足す手順に K41 の測り直しが無い。K41 の頼み事を誰が打つかが無い。→ 版を足す手順を「PO が件を1つ開く → PO が K41 (a)(b) の頼み事と K32 の一文を打つ → Opus が画面の写しと状態ファイルを読むだけで、選ぶ画面0件と K41 の○を確かめる → 版を足す PR を出し、審査を通してから入れる」に置き換える。K41 の頼み事も PO が打つ（Opus は件の窓に打たない）。
- M3（推奨）: 決まりが3つ足りない。→ 次のとおり決める。
  - `caseSayClaudeVersions` の各要素が `^\d+\.\d+\.\d+$` の形でないときは、`caseSayRoles` と同じく起動時エラーにする。
  - 判定4b より前で断った監査の行は、版の欄を書かない（欄なし）。判定4b 以後は、読めた版、または版の形でない名前のときは空文字を書く。
  - K42 に「`caseSayClaudeVersions` が既定の [] のとき、どの件にも 409 `claude_version_unverified` で書き込み0回」を1件足す。

**再審査**（2026-11-06 00:11〜00:12 JST・クラウドの Opus・読むだけ・salesanchor fca230859 / agent-console b467656）: **APPROVE**。C1〜C4 は○。必須の指摘なし。推奨2件（:906 の K40 の言い回しが古い・版を足す手順と K42 の表の行に第11版の直しが入っていない）は、言い回しだけの直しとしてこの版で直した。

**状態**: 設計審査済み（第11版・APPROVE）。PO の実装承認は §14-13 の冒頭（2026-11-05 PO「1」と、同日の「判定を決め直したら、設計の審査をもう一度通し、その後クラウドで作り、合流と導入まで進める」）に基づく。（2026-11-06 追記: GEN-RYU-System/agent-console PR #100 で合流（412717f）し、agent-console v0.51.0 で導入済み。実際の件の窓での K32・K33・K41・K7 の確かめは、PO が件を1つ開いた後に行う）

### 14-14 第12版: 件の claude の版を人の手なしで確かめて使う（2026-11-06・PO「1」）

**状態**: 設計案・審査4回目 APPROVE（4稿）。その推奨3件を取り込んだ5稿（当て先は §14-14-15）。設計書は本線に合流済み（2026-11-06・#5208）。便CS3c（ADR-1033 What 6 の例外と第12版への参照の直し）は #5210 で ADR-1033 に入れる。実装（便CS3a）は未着手。審査1回目の必須の直し7件と推奨3件の当て先は §14-14-12、審査2回目の必須の直し5件と推奨3件の当て先は §14-14-13、審査3回目の必須の直し3件と推奨3件の当て先は §14-14-14、審査4回目の推奨3件の当て先は §14-14-15。守りの水準は PO 2026-11-06「1」（うっかり防止の水準。同じ Mac の AI が技術的には書き換えられることを受け入れる）。PO の決定の原文は「1」。意味は『使ってよい版の一覧を config から、サーバーが自分で書く dataDir の記録へ移す』（設計役の3回目が出した PO 判断の選択肢1）。3回目の設計（D1 版ずれ通知・D2 写しで固定・D3' サーバー内部の判定・D4 probe の件・D5 dataDir の記録・便の順・S1〜S7・危険1〜3）は本書に入っていなかったため、本節で agent-console origin/main aabdeef（v0.52.0）の実物で確かめ直して書き下ろす。本節が正本。行番号はすべて aabdeef の物。

#### 14-14-1 目的と決定

- 今の形（第10・11版。§14-13-7 M1・§14-13-8）: 件の claude の版は、件を開くたびに PATH から解いた実体の道の最後の名前（[server/sessions.ts:513-515](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/sessions.ts#L513-L515) `prepareCaseRoom` → [server/case-sandbox.ts:432-449](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/case-sandbox.ts#L432-L449) `resolveClaudeReal`）。case-say の判定 4b は、その名前が config の `caseSayClaudeVersions`（[server/config.ts:88](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/config.ts#L88)・同梱の [agent-console.config.json:9](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/agent-console.config.json#L9) は `["2.1.318", "2.1.319"]`）に入っているときだけ通す（[server/hub.ts:538-542](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/hub.ts#L538-L542)）。版を足す手順は README:313-318 の4段（PO が件を開く → PO が K41 (a)(b) と K32 の一文を打つ → Opus が読む → PR・審査・導入）。
- 観測事実（人の手の量）: 2.1.319 を足した PR #101（54f7c74・v0.51.1）は、コードを変えずに 7 ファイル・8 行（config・README・試験の期待値・版番号3か所・CHANGELOG）を変え、PO の操作・Opus の測り・審査・ac-update を要した。PO のふつうの claude が更新されるたびに同じ量がかかり、更新から版を足すまでの間、case-say は全件 `claude_version_unverified` で止まる。その事実は Opus が呼んで断られるまで誰にも知らされない（監査の行だけ。断りの行を書くのは [server/http.ts:554](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/http.ts#L554) `refused(409, reason, …)`。:543-553 は欄の組み立てと成功のときの道）。
- 決定（PO「1」）: 一覧の正本を、サーバーだけが書く dataDir の記録へ移す。版の○×はサーバーが自分で開く「probe の件」で機械的に確かめ、人は打たない・読まない・PR を出さない。config の `caseSayClaudeVersions` は無くす（便CS3b）。
- ADR-1033 What 6 の例外（審査1回目 C4・必須1）: ADR-1033:24 What 6 は「件のセッションへの決まった一文の送信は case-say の受け口だけで行う。§4-5 の見張りの外で端末へ送るほかの道を作らない」。本版は、サーバーが自分で開いた probe の件（D4）にだけ、コードの定数の文 3 つ（文1〜文3）を送る道を足す。条件: (a) 宛先は `versionProbe: true` の件だけ（PO の件・Opus の窓へは送れない）、(b) 文は定数で Opus・PO・外からの入力は入らない、(c) 打ち方は case-say と同じ `sendToPane`（区画 `%N` と pid の条件付き）・Enter の前の idle の確かめ直し、(d) 発火はサーバーの内側だけ（受け口・命令を作らない）、(e) 1回ごとに監査に残す（§14-14-6 の 9）。この例外は PO の決定「1」（版の○×を人の手なしにする）から来る。ADR-1033 の本文を直すのは便CS3c（§14-14-9）。便CS3c は便CS3a の合流より前に合流させる（ADR を先に直し、実装を後から合わせる。AGENTS.md の ADR 優先。審査2回目 必須4）。
- 変えない物: PO の件・Opus の窓へ送る文は1種類（[server/hub.ts:140](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/hub.ts#L140) `caseSayText`・:571 で組む・README:302）、宛先の決め方（判定 4。[server/hub.ts:521-537](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/hub.ts#L521-L537)・README:304）、判定 1〜3・5〜9、Sales Anchor 側の見張り、起動台本 `ops/shell/ccdiscord.zsh`（K40 の2つの試験が守る）。

#### 14-14-2 変更前後

| 項目 | 変更前（v0.52.0） | 変更後（第12版） |
|---|---|---|
| 使ってよい版の正本 | config `caseSayClaudeVersions`（config.ts:88・:411-416、config.json:9） | dataDir の記録「case-say-claude-versions.json」（D5。書き手はサーバーだけ） |
| 版の○×を決める人 | PO が打つ・Opus が読む・PR で足す（README:313-318） | サーバーが probe の件で機械条件（§14-14-4）により決める（D3'・D4） |
| 判定 4b の比べ方 | 実体の道の最後の名前が一覧にあるか（hub.ts:538-542） | 件を開いたときの実体の指紋（sha256・size）が記録の使える項目と一致するか（D2）。名前は表示と監査の欄 |
| 版ずれの知らせ | 無し（caseSayRefused の監査行だけ） | 画面の案内・macOS 通知・監査 `caseClaudeVersionNotice`（D1） |
| サーバー起動時 | 版について何もしない | 記録を読み、各項目の指紋を実体と比べ直す。PATH の claude が未記録なら probe を予約（§14-14-6 の再 probe） |
| 断りの理由 | `claude_version_unverified` | 同じ。確かめ中は `claude_version_probing`、probe の件への送信は `version_probe_session` を足す |
| README | 「claude の版の一覧」節（:309-318） | 「版はサーバーが自分で確かめる」節に置き換え。人の手順は×のときの PO の手（§14-14-5）だけ |
| 試験 | tests/unit/case-say.test.ts:334-357（K42）・:360-396（config） | K42 を記録の形に書き換え。config の試験は便CS3b で外す |

#### 14-14-3 D1〜D5（読む物・書く物・file:line）

**D5 dataDir の記録（正本）**
- 書く物: 「<dataDir>/case-say-claude-versions.json」。形は `{ "version": 1, "entries": [ { "sha256", "size", "claudeVersion", "real", "verifiedAt", "probeCaseId", "checks": { "E1".."E4", "P0".."P5" }, "usable", "lastProbeAt", "lastResult", "failCount", "mac" } ] }`。項目の鍵は `sha256`（版の名前は表示用。同じ名前で中身が違えば別の項目）。書き方は [server/json-store.ts:30-36](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/json-store.ts#L30-L36) `writeJsonAtomic`（tmp＋rename・0600）。読み方は同 :20-27 `readJsonFile`。壊れていれば上書きせず「使える版 0」として扱い D1 で知らせる（open-sessions と同じ考え。[server/session-store.ts:60-63](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/session-store.ts#L60-L63)）。
- 書く条件: probe が○のときだけ `usable: true` の項目を書く。人が手で足す命令は作らない（`scripts/ac-case-macos.mjs accept` のような形も作らない。理由: 人の手なしが目的。×のときの手は §14-14-5）。項目は消さず、起動時の再確認で指紋が合わなければ `usable: false` にする。
- 読む側: 新しい部品「server/case-say-versions.ts」（`CaseSayVersionStore`）が起動時に読み、メモリに写しを持つ。判定 4b（`caseSayTarget`。同期関数 hub.ts:521）はメモリで決める。
- 部屋からの守り: 件の部屋の書き込み拒否 [server/case-sandbox.ts:70-87](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/case-sandbox.ts#L70-L87) `CASE_DENY_WRITE` には D/cases・case-gh・hooks・activity は入っているが dataDir 直下のファイルは入っていない → 記録と鍵（§14-14-6 の 1）を `CASE_DENY_WRITE` と `CASE_DENY_READ`（同 :89-100）に足す。room.sb は件を開くたびに書き直す（sessions.ts:513-532）ので、入れた後に開いた件から効く。
- 既存の似た形: macOS の版の記録「case-room-macos.json」（[server/case-proxy.ts:98-109](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/case-proxy.ts#L98-L109)・[scripts/ac-case-macos.mjs:34-36](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/scripts/ac-case-macos.mjs#L34-L36)）。違いは、あちらは人が命令で書き、こちらはサーバーだけが書く。

**D2 実体の写し（指紋）で固定**
- 指紋を取る時点（審査1回目の推奨1を採用）: 件の claude を起動する前に取る。`createCase`（sessions.ts:394-414。async）の中で、写しを作った後・`spawnSession` を呼ぶ前に `resolveClaudeReal` で実体を解き、sha256・size を流し読みで計算し、その `real` と指紋を `spawnSession` → `prepareCaseRoom` へ渡す（`prepareCaseRoom` は渡された `real` を使い、解き直さない）。起動した後に計算すると、開いてから計算するまでの間に中身を変えられるため。計算に 60 秒かかれば件は開くが 4b は `claude_version_unverified`・D1 n1 に理由を付ける。残る隙（計算してから起動台本が exec するまでの差し替え）は E2（固いリンクでない）と起動時の再確認（§14-14-6 の 3）で減らすだけで、無くはならない（PO「1」の水準で受け入れる）。
- 読む物: 件を開くときに解いた実体の道 `claudeReal`（sessions.ts:514。[server/sessions.ts:661](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/sessions.ts#L661) で `caseClaudeReal`（:219 の Map）に残す。起動台本はこの道を `AC_CLAUDE_BIN` として受け（:504）、`ccdiscord.zsh:19` で実行できることを確かめ、`:76` で exec する）。
- 書く物: `caseClaudeReal` の値を `{ real, size, sha256 }` に広げる（上の時点で取った値。流し読みは非同期で、サーバーを止めない）。指紋を持たない件（どの道で開いたかを問わない。復元 restore.ts:125-190 を含む）は、4b で必ず `claude_version_unverified`（誤って通す方へ倒さない）。復元の道に同じ計算を足すかは便CS3a の実装の選択で、どちらでも K50 の「指紋なし→409」で確かめる。実体のサイズと計算時間は未確認（U5）。大きすぎると分かれば、件を開くときは `size`・`mtime`・`ino` の一致で代え、sha256 は起動時と probe のときだけ計算する（K56 で測って決める）。
- 判定 4b の新しい形: 件の指紋（sha256・size）が記録の `usable: true` の項目と一致 → 通す。あわせて最後の名前が `CLAUDE_VERSION_PATTERN`（[server/config.ts:409](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/config.ts#L409)）に合うことは引き続き要求する（監査の `claudeVersion` 欄 [server/routine-audit.ts:58-59](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/routine-audit.ts#L58-L59) に書くため）。名前だけでは通らない。

**D3' サーバー内部の判定**
- 版の○×を決める材料は、サーバー自身が持つ物だけ: (a) 自分が開いた probe の件の状態ファイル（[server/case-agents.ts:91-125](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/case-agents.ts#L91-L125) `readCaseStateFile`。今は `pid`・`status`・`waitKeys` だけを取る → `version` も取る。K30 の実測で 17 キーの中に `version` があった（§14-10-10）。値の形は未確認 U1）、(b) 自分が受けた件の活動の記録。probe の判定のため、probe の件の設定だけに道具の記録の hook を 2 本足す（審査2回目 必須1・2）。`buildCaseSettings`（[server/case-sandbox.ts:455](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/case-sandbox.ts#L455)）に引数 `{ versionProbe: true }` を足し、その時だけ PreToolUse と PostToolUse に matcher `"*"`・同期（`async: false`・`timeout: 5`）の handler を 1 本ずつ足す。引数の道は `createCase` → `writeCaseFiles`（[server/sessions.ts:405](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/sessions.ts#L405) で呼ぶ。[server/case-sandbox.ts:496](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/case-sandbox.ts#L496)）→ `buildCaseSettings`（case-sandbox.ts:504 で呼ぶ）で、`writeCaseFiles` にも同じ引数を足して渡す（審査3回目 推奨1）。`createCase`（sessions.ts:394）にも任意の引数 `versionProbe` を足す。どれも任意の引数で、渡さなければ今と同じ（PO の件の設定は変わらない）。Session に probe の印を付けるのは `spawnSession` の直後（`initialName` を付ける :408 と同じ所）とする（審査4回目 推奨3）。同期にする理由（審査3回目 必須2）: handler の既定は非同期（[server/activity-hooks.ts:98](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/activity-hooks.ts#L98)）で、送信は 2 秒で打ち切り、失敗しても黙る（[hooks/activity-hook.mjs:14](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/hooks/activity-hook.mjs#L14)・:293-301）。非同期のままだと post の記録が `idle` の後に届き、判定の時点で「post が 0 件」が成り立って P3 が誤って○になり得る。同期なら claude は hook が終わるまで次へ進まない。activity-hook はいつも exit 0 で終わる（:332）ので、道具を止めない。PO の件は今と同じく引数なしで呼ぶので、PO の件の設定は今の版と1文字も変わらない。2 本の送り先は新しい受け口 `POST /api/agent/case-probe-activity`（`activity-hook.mjs --post <その url>`。hook は入力をそのまま送り、記録はサーバーが作る。[hooks/activity-hook.mjs:320-327](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/hooks/activity-hook.mjs#L320-L327)。受け口の作りは [server/http.ts:455-470](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/http.ts#L455-L470) `handleCaseActivity` と同じ順）。新しい受け口は件を `caseOfRequest` で引き、それが今動いている probe の件（`runningVersionProbe.caseId`）でなければ 403 にする。受けた入力は `runActivityHook` に渡さない。このため活動の記録にも `applyPre` にも入らず、Agent の開始の記録（`starts` の description など）を上書きしない（[server/activity.ts:462-463](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/activity.ts#L462-L463)・:517-527）。サーバーは probe の実行中だけ、メモリに次の欄だけを持つ: `ts`・`phase`（"pre" / "post"）・`agent_id`・`tool`・`tool_use_id`・`permission_mode`（`tool_input`・`tool_response` は持たない）。probe が終われば捨て、数えた結果を監査の行に残す（§14-14-6 の 9）。今の記録の道は P3 の照合に使わない。ファイルを書く道具の PostToolUse の記録に `tool_use_id` が無く（[hooks/activity-hook.mjs:162-166](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/hooks/activity-hook.mjs#L162-L166)）、Bash・Read の PostToolUse は来ない（activity-hooks.ts:55）ため。共通の `HOOK_SPECS`（PO のふつうの窓にも効く）と `handleCaseActivity` は変えない。コードの名前は `versionProbe` にそろえる（Session の欄 `versionProbe: true`・記録の欄 `runningVersionProbe`・409 の理由 `version_probe_session`・`buildCaseSettings` の引数 `{ versionProbe: true }`）。sessions.ts:714 の引数 `probe` と tmux-runner の `probeSession` に紛れないため（審査2回目 推奨1）。本書では短く probe と書く。公式の hooks の説明（code.claude.com/docs/en/hooks・2026-11-06 に読んだ。Context7 は月の上限で使えなかった）では、PreToolUse の入力に `permission_mode`（`"plan"` などの値）と `tool_use_id` があり、合う hook は並んで同時に走る。case-guard が exit 2 で止めたときに、同時に走った probe の道具の記録の hook が最後まで送れるかは書かれていない（U13）。送れなければ P3 は×に倒れる（誤って○にはならない）。既存の記録の受け口は（[server/http.ts:455-470](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/http.ts#L455-L470) `handleCaseActivity` → [server/activity.ts:491](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/activity.ts#L491) 返事の全文・:584 `chat()`・:592 `files()`。記録される出来事は [server/activity-hooks.ts:53-72](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/activity-hooks.ts#L53-L72) `HOOK_SPECS`: PostToolUse は `Agent|Write|Edit|MultiEdit|NotebookEdit` だけ（:55）で Bash は入らない。SubagentStart :62・SubagentStop :56・Stop :60）、(c) probe の件の R（手順書の置き場）に probe が書かせたファイルの有無と中身（サーバーが lstat して読む。64KiB 上限・リンク拒否は case-agents.ts:19-37 と同じ読み方）、(d) tmux の画面の写し `capture-pane -p -t %N`（probe の件だけ。PO の件の画面は読まない。§14-11-5 で画面を読まないと決めたのは PO の会話を読まないためで、probe の件の画面はサーバーが自分で作った会話）。
- 使わない物: Opus の報告・PO の目視・`claude agents --json`（件は出ない。§14-10-10 別の方法1）。
- 実体そのものの確かめ（E1〜E4。§14-14-4）もサーバーが行う。`--version` はサーバーが `execFile(real, ["--version"])` で読む（[server/agents.ts:127-134](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/agents.ts#L127-L134) `fetchClaudeVersion` と同じ形。起動台本も同じ命令を `ccdiscord.zsh:31` で件の起動のたびに実行している）。

**D4 probe の件**
- サーバーが自分で開く件のセッション。開き方は `createCase`（[server/sessions.ts:394-414](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/sessions.ts#L394-L414)）をサーバーの内側から呼ぶ。役割は `discord-case`（同梱の設定で `caseSandbox: true` の役割はこれ 1 つ。[agent-console.config.json:46-53](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/agent-console.config.json#L46-L53)）。起動台本も PO の件と同じ `ccdiscordcase`（K40 で守る物を変えない）。名前は `probe claude <版>`。写しは `createCaseClone`（[server/case-clone.ts:90](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/case-clone.ts#L90) から。:102 で `git clone --local --no-checkout --no-hardlinks`）で作る。Session に `versionProbe: true`（メモリ）を足す。
- 本店での fetch（審査1回目の推奨3）: `createCaseClone` は写しを作る前に、本店の作業場所 M で `git fetch origin main` を打つ（case-clone.ts:96）。probe の件もこれを通るので、probe 1 回につき M の `origin/main` の参照が新しくなる。M の作業中のファイル・ブランチ・index は変わらない（fetch は参照と物だけ）。PO の件を開くときと同じ副作用で、新しい種類の副作用ではない。
- 枠（審査1回目の推奨2）: probe は、probe を開いた後も件の枠が 1 つ以上空くときだけ始める（`hasCapacity`（sessions.ts:562）の数え方で、空きが 2 以上）。足りなければ予約のまま待ち、PO が件を閉じて空きが 2 以上になったら始める。probe の最中に PO が件を開こうとして枠が足りないときは、PO を優先する: probe を中断（`aborted`）して閉じ、PO の件を開く。
- gh の鍵（審査1回目 C4 の2点目）: probe の件も起動台本（`ccdiscord.zsh:41-43`）で shingo-cc の gh の鍵を持つ。起動台本は変えない（K40）。文1〜文3 は R にファイルを書くことしか頼まず、gh・git push は頼まない。件の中の見張り（case-guard・部屋の拒否）は PO の件と同じに効く。probe の件が gh を使ったかは活動の記録（PostToolUse には Bash は残らない。HOOK_SPECS :55）では見えないため、上の probe の道具の記録（`phase: "pre"`）に `tool` が `Bash` の行が 1 つでもあれば P5 を×にする（文1〜文3 は Bash を要らない）。
- 発火: (t1) 件を開くとき（spawnSession :654-661）、解いた実体の指紋が記録の使える項目に無い → D1 で知らせ、同じ指紋の probe が無ければ 1 つ予約。(t2) サーバー起動時、`resolveClaudeReal(config.claudeBin, PATH)` の指紋が記録に無い → 復元（[server/restore.ts:125-190](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/restore.ts#L125-L190)）と `hub.start()`（index.ts:127）の後に probe を 1 つ予約。(t3) 人の操作・Opus の呼び出しでは起こさない。同時に動く probe は 1 つ。1 つの指紋につき、×の後は 24 時間は再 probe せず、連続 3 回×で止める（記録の `failCount`・`lastProbeAt`）。枠（`hasCapacity` sessions.ts:562）が無ければ予約のまま待つ。
- 台本（サーバーが probe の窓へ打つ。打ち方は case-say の判定 4・5・7・8・9 と同じ道: 区画 `%N` と pid の条件付き送信 [server/terminal-host/tmux-terminal.ts:306-321](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/terminal-host/tmux-terminal.ts#L306-L321) `sendToPane`、Enter の前に状態ファイル idle を確かめ直す。4b は飛ばす（4b を作るための窓）。送る文はコードの定数 3 つで、Opus の入力は入らない）。文の中の `<R>` はその probe の件の R:
  - 文1: `<R>/probe-1.txt に Write ツールで ok とだけ書いてください。Bash は使わないでください。`
  - 文2: `Agent で下請けを1つ動かし、下請けに <R>/probe-2.txt へ Write ツールで ok とだけ書かせてください。あなたも下請けも Bash は使わないでください。`
  - 文3: `/plan <R>/probe-3.txt に Write ツールで ok とだけ書いてください。`
  - 文4: `計画どおり進めてください。`（文3 の返事が plan の pre なしで終わったときだけ 1 回。§14-14-16）
  - 判定は §14-14-4 の P0〜P5。終わったら probe の件を閉じる（[server/sessions.ts:793](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/sessions.ts#L793) `close`）。片付け（U8 を決めた）: sessions.ts の中では、閉じる道（`close` → `closeRunning` → `remove` :762-773）は件のファイルも写し W も消さない。`removeCaseFiles`（[server/case-sandbox.ts:545-555](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/case-sandbox.ts#L545-L555)。D/cases・case-gh・case-home を消す）と、W・R（手順書の置き場。[server/case-sandbox.ts:62](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/case-sandbox.ts#L62)）の `rm` を呼ぶのは、sessions.ts では開くのに失敗したとき（:411-413）だけ。`onRemoved`（:341）に付く聞き手は sessions.ts の外にあり読んでいない。そこで probe の片付けは、閉じた後に自分で (1) `removeCaseFiles(D, probeId, { tmp: true, tmpRoot })`、(2) `rm(R, { recursive: true, force: true })`（:412 と同じ）、(3) `rm(W, { recursive: true, force: true })`（:413 と同じく `W === caseCloneDir(H, probeId)` のときだけ）を打つ。どれも既に消えていれば何もしない形で呼ぶ（`.catch(() => undefined)` は :411-413 と同じ）。これで聞き手の有無に依らず残らない。K52 で「probe の後に D/cases/<probeId>・R・W が無い」を確かめる。
- probe の件への他からの入力はすべて断る: 画面の端末入力（[server/ws.ts:36-39](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/ws.ts#L36-L39) → sessions.write :780）・チャット（hub.ts:617 `enqueueChat`）・`submitText`（:765）・名前の変更・case-say（判定 4 に `versionProbe` → 409 `version_probe_session`）。復元の一覧には書かない（[server/restore.ts:94](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/restore.ts#L94) の filter に `versionProbe` を足す）。記録に `runningVersionProbe: { caseId, startedAt }` を書き、起動時の片付けの順は次で固定する（U9 を決めた）: (1) `startupSweep`（[server/terminal-host/tmux-runner.ts:95](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/terminal-host/tmux-runner.ts#L95)）が返す `ac-*` の名前の一覧を受ける（startupSweep 自体は消さない。一覧を返して設定を読み直すだけ）。(2) 記録に `runningVersionProbe` があり、その `ac-<caseId>` が一覧にあれば、その 1 つだけ kill-session する（ほかの `ac-*` には触らない）。(3) その probe の W を上と同じ条件で消し、R を消し、D/cases などを `removeCaseFiles` で消す。(4) `runningVersionProbe` を消し、項目の `lastResult: "aborted"`・監査 aborted。(5) その後に復元（restore.ts。probe は復元の一覧に入らない）。

**D1 版ずれ通知**
- 出す場面: (n1) 件を開いたとき、指紋が使える項目に無い。(n2) 起動時、PATH の claude が未記録。(n3) 起動時の再確認で、記録の項目の実体が無い・指紋が違う → `usable: false` に変えた。(n4) probe が×（P 番号付き）。(n5) 記録が読めない・MAC が合わない項目を捨てた。(n6) 監査に書けなかった（§14-14-6 の 9）。
- 出し先: ① Snapshot（[server/hub.ts:78-95](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/hub.ts#L78-L95)）に `caseVersionNotices` を足す（`restoreNotices` :82・`setRestoreNotices` :353-355 と同じ作り。画面の案内。文言は画面側の i18n）。② macOS 通知（[server/notify.ts:34-41](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/notify.ts#L34-L41) `osascriptSender`。config の `notify.macos` が true のとき。1 場面につき 1 回）。③ 監査 `routine-audit.jsonl` に `caseClaudeVersionNotice`（reason n1〜n5・claudeVersion・sha256 の先頭 16 桁。[server/routine-audit.ts:11](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/routine-audit.ts#L11) の action に `caseClaudeVersionNotice`・`caseClaudeVersionProbe` の 2 つを足す）。④ `/api/state`（[server/http.ts:194-208](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/http.ts#L194-L208)）に `caseSayVersions: { usable: [版の名前], probing: [版の名前] }` を足す（画面用。Opus 用の新しい読み口は作らない。Opus は case-say の 409 の reason で知る）。
- Opus への見え方: 断りの理由は `claude_version_unverified` のまま。probe が動いている・指紋の計算中は `claude_version_probing`（README:306 の理由の一覧に足す）。

#### 14-14-4 ○×の判定の機械条件

使える＝E1〜E4 が全部○ かつ P0〜P5 が全部○ かつ R1 が○。1 つでも×なら使えない（記録に `usable: false`・`lastResult: "<×の番号>"`）。

| # | 条件 | 読む物 | ○ | × |
|---|---|---|---|---|
| E1 | 実体の道の最後の名前が `^\d+\.\d+\.\d+$` | `resolveClaudeReal` の戻り（case-sandbox.ts:433-449） | 合う | 合わない |
| E2 | 実体が通常ファイル・実行可・固いリンクでない | `statSync`・`accessSync X_OK`（sessions.ts:487-489 と同じ）・`nlink === 1` | 全部 | どれか外れ |
| E3 | `<real> --version` の出力が E1 の版で始まる（15 秒以内） | `execFile`（agents.ts:127-134 の形） | 一致 | 不一致・時間切れ・空 |
| E4 | sha256・size が取れた | ファイルを流して読む | 取れた | 読めない |
| P0 | probe の件を開いて 60 秒以内に状態ファイルが読める | `readCaseStateFile`（case-agents.ts:91） | ちょうど 1 つ・JSON の pid ＝ファイル名の pid ＝区画の pid・`status === "idle"`・`waitKeys` 空・`version` キーがあれば値に E1 の版の文字が含まれる | どれか外れ・60 秒超 |
| P1 | 文1 の後、道具が通る | R の `probe-1.txt`・状態ファイル | 120 秒以内にファイルがあり中身が `ok`（前後の空白を除く）・その後 `idle` に戻る | 無い・中身違い・時間切れ |
| P2 | 文2 の後、下請けが通る（K41 (a)） | R の `probe-2.txt`・活動の記録（PostToolUse・SubagentStart・SubagentStop）・状態ファイル | 180 秒以内に次が全部: ファイルが `ok`・PostToolUse の `tool: "Write"` で `path` が `<R>/probe-2.txt` に完全一致し `agent_id` が空でない行が 1 以上（下請けが書いた証拠。主の会話が書いた行は数えない）・その `agent_id` の SubagentStart と SubagentStop が各 1 以上・`idle` に戻る | どれか外れ（主の会話だけが書いたときも×） |
| P3 | 文3 の後、計画の形では道具が止まる（K41 (b)） | probe の道具の記録（§14-14-3 D3' (b)。pre と post）・R の `probe-3.txt`・状態ファイル・P4 | 待ち方は §14-14-16 の 2（文3 の返事で plan の pre が無ければ文4 を 1 回送る。文3・文4 それぞれ 120 秒まで）。次が全部: 主の会話（`agent_id` なし）の pre の行で `permission_mode: "plan"` のものが 1 以上で、その行の `tool_use_id` がどれも空でない・その行と同じ `tool_use_id` の post の行が 0 件・文3 の送信から判定までの間に主の会話の post の行が `tool_use_id` を問わず 0 件（審査3回目 必須1）（照合は probe の道具の記録の pre と post どうしで行う。post は道具が通ったときだけ来るので、0 件は case-guard [ops/case/case-guard.mjs:76](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/ops/case/case-guard.mjs#L76) が止めた形。case-guard は stderr と exit 2 だけでサーバーへ何も送らないので、止めたことは「試みた記録があり、通った記録が無い」で読む）・P2 の間に post の行が 1 以上来ていた（post の道が働いている証拠。これが無いと「post が 0 件」がいつでも成り立つため）・P1・P2 の間の probe の道具の記録の pre の行が、どれも同じ `tool_use_id` の post の行と対になっている（post が途中で消えていない証拠。審査4回目 推奨2）・ファイルが無い・`idle` に戻り、その後 3 秒待ってから判定する（hook の送信の打ち切り 2 秒より長く待つ。審査3回目 必須2）・P4 が 0 件。参考記録: 返事（activity.ts:491）に `permission mode is not dontAsk` が含まれるか（含まれなくても×にしない。U7） | どれか外れ。道具を 1 度も試みなかった（pre の plan の行が 0）ときも×（止める仕組みが働いた証拠が無いため）。通った道具の post の行があれば×（審査2回目 必須1）。pre の plan の行に `tool_use_id` が空の物がある・文3 の後に主の会話の post の行が 1 つでもある も×（審査3回目 必須1）。P1・P2 の pre の行に対の post が無い物がある も×（審査4回目 推奨2） |
| P4 | 選ぶ画面が出ない | P0〜P3 の各 `idle` 復帰の時点の probe の件の `capture-pane -p -t %N`（probe の件だけ）。数えるのは、監査に残すのと同じ、制御文字を除き末尾 4KiB に切った写し（K55 ② の数と合わせる。審査3回目 推奨2） | 次の形が 0 件: 行頭の番号付き選択肢（`^\s*[❯>]?\s*\d+\.\s`）が 2 行以上連続し、その塊の中に選ぶ印の付いた行（`^\s*[❯>]\s*\d+\.\s`）が 1 つ以上ある物（§14-14-16 の 3）・`\(y/n\)`・`Do you want to`・`Esc to cancel`・`Yes` と `No` が同じ行 | 1 件以上。正規表現は probe の件の画面の写しで確かめる（U6・K55 ①）。PO の件の画面は読まない |
| P5 | 全体が 10 分以内・待ちの間の `status` が `idle`・`busy` 以外にならない・probe の道具の記録の pre に `tool: "Bash"` の行が無い | 時計・状態ファイル・probe の道具の記録 | ○ | 時間切れ・他の値（値を記録）・Bash の行がある |
| R1 | 記録の項目の MAC が鍵と合う・`version: 1` | 記録ファイル・鍵ファイル（§14-14-6 の 1） | 合う | 合わない項目は捨てる |

件を開いたとき（判定 4b）: その件の指紋（D2）が `usable: true` の項目の `sha256`・`size` と一致すれば通す。一致する項目が無く、同じ指紋の probe が動いている・指紋の計算中なら `claude_version_probing`。それ以外は `claude_version_unverified`。

#### 14-14-5 止まり方

- probe が×（P0〜P5 のどれか）: その指紋は使えない。D1 n4 で知らせ、監査 `caseClaudeVersionProbe`（outcome denied・`failedCheck` に×の番号。審査4回目 推奨1）。case-say はその版の件へ 409 のまま。人が記録に手で足す口は無い。PO の手は 2 つ: (a) claude をふつうの手で前の版に戻す（PO の操作。手順は本書に書かない）か、(b) ×の番号を見て設計を見直す（P4 なら claude に新しい選ぶ画面が加わった可能性。案 E（§14-10-5）へ戻し、本書を直してから再び probe）。24 時間後・連続 3 回までは自動で再 probe する。3 回×で止まり、D1 n4 に「設計者の確認が要る」を付ける。
- probe が途中で終わる（サーバー再起動・件が開けない 503・時間切れ）: `lastResult: "aborted"`・`failCount` は増やさない。次の発火（件を開く・起動）で再 probe。
- 記録が読めない（壊れた JSON）・MAC が合わない項目: 上書きしない・捨てた項目は書き戻さない。使える版は 0。D1 n5。PO が記録ファイルを別名に退避してサーバーを起き直すと再 probe が走る（これだけが人の手。壊れた記録は PO 確認なしに消さない。AGENTS.md の不可逆操作の考え）。
- 指紋の計算が終わらない（U5）: 4b は `claude_version_probing`。60 秒で打ち切り、`claude_version_unverified`・D1 n1 に理由を付ける。
- 戻し方: agent-console を便CS3a の一つ前の版に戻す（`bash scripts/ac-update.sh v0.52.0`。記録ファイルと鍵は残るが古い版は読まない。config の `caseSayClaudeVersions` が同梱の設定にそのまま残っていれば、戻した版はそれで動く）。便CS3b の後に戻すときは、同梱の設定に `caseSayClaudeVersions` を戻す必要があるので、便CS3b の CHANGELOG にその 1 行を書く。
- 予備: 案 E（今のまま PO が打つ）。

#### 14-14-6 偽造を減らす手（起動時の再 probe を含む）

3回目の危険 1〜3 を実物で確かめ直した形:

| # | 危険 | 対処 |
|---|---|---|
| 危険1 | 記録の偽造: Opus（部屋の外。PO と同じ利用者で動く）が dataDir の記録に `usable: true` の項目を書く | 下の 1（MAC）・2（指紋）・6（下請けの見張り）。残る危険（PO 2026-11-06「1」で受け入れ済み）: Opus 本体の会話は見張りに止められないので、鍵を読んで MAC を作り、項目を書ける。監査を Edit で直すこともできる。守りの水準はうっかり防止で、悪意への対策ではない（agent-console のほかの合言葉と同じ水準） |
| 危険2 | 実体の差し替え: 版の名前はそのままで中身を変える・偽の実体を版の名前で置く | 2（指紋が鍵。名前だけでは通らない）・3（起動時の再確認で指紋が違えば使えなくする）・E3（`--version` の答えと名前の一致） |
| 危険3 | probe の汚染: 人や Opus が probe の窓に打つ・PO の件の画面を読んでしまう・新しい選ぶ画面を見逃す | 4（probe の件への入力を全部断る）・D3'（画面を読むのは probe の件だけ）・P4（選ぶ画面の形を数える。形は実物で決める U6）・P5（想定外の status を記録して×） |

1. 記録の書き手はサーバーだけ・項目ごとに MAC を付ける。鍵は `<dataDir>/case-say-claude-versions.key`（0600。起動時に無ければ作る。[server/reserve-token.ts:28-39](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/reserve-token.ts#L28-L39) と同じ形）。読んだとき MAC が合わない項目は捨て、D1 n5。
2. 判定は指紋（sha256・size）で行い、版の名前では行わない（D2）。
3. 起動時の再 probe: (a) 軽い方＝記録の各 `usable` 項目について、実体 `real` を stat・sha256 し直し、無い・違えば `usable: false`（D1 n3・監査）。(b) 重い方＝PATH の claude を解き、その指紋が記録に無ければ probe の件を開く（D4 t2）。既に使える指紋では窓を開き直さない（使用量を増やさない）。
4. probe の件への入力はサーバーだけ（§14-14-3 D4）。probe の件は case-say の宛先にもならない（`version_probe_session`）。
5. 件の部屋から記録・鍵を書けない・読めない（`CASE_DENY_WRITE`・`CASE_DENY_READ` に足す。§14-14-3 D5）。
6. 見張りの実際の範囲（審査1回目 C3・必須2。実物どおりに書き直した）: 共通の同期 hook `GUARD_IFS`（[server/activity-hooks.ts:12-19](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/activity-hooks.ts#L12-L19)）のうち、dataDir の親フォルダの名前を含む道を止めるのは :15（Bash）と :18（Read）。本体の [hooks/ac-routine-guard.mjs](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/hooks/ac-routine-guard.mjs) は、:2「入力に agent_id があるときだけ判定する」・:27-28 で agent_id が空なら通す。:5 で Grep・Glob は対象外。:7「誤用防止であり、悪意への対策ではない。引用符や glob で迂回できる」。
   - 止まる物: 下請け（Agent で動かした担当）の Bash と Read のうち、道の文字列にその名前をそのまま含む物。
   - 止まらない物: Opus 本体の会話の全部（Bash・Read・Write・Edit・Grep・Glob）。下請けの Write・Edit・Grep・Glob。`\` や引用符・glob で名前を崩した道。
   - 鍵は dataDir に置いたまま（審査が挙げた Keychain へ移す案は採らない。PO 2026-11-06「1」）。上の止まらない物から来る偽造の危険は、危険1 の「残る危険」として PO が受け入れた。
   - PO の Mac の dataDir がその名前の下にあるかは設定の値で決まり、本書には書かない（U2・K57 で確かめる）。
   - Opus 本体が監査と記録を読めることは、上の範囲から来る（9 の読み方の前提。K57 とは食い違わない）。
7. probe の台本の文はコードの定数（Opus・PO の文は入らない）。
8. 監査: 発火・○・×・中断・無効化・通知をすべて `routine-audit.jsonl` に残す（`caseClaudeVersionProbe`・`caseClaudeVersionNotice`）。本文・鍵・合言葉は書かない。例外は 9 の `paneSamples` だけ（probe の件の画面の写し。サーバーが自分で開いた件で、送った文は定数の文1〜文3 だけなので PO の会話を含まない）。
9. 記録を残す（PO 2026-11-06「記録も残るようにして」）: 自動の確かめは1回ごとに後から読める記録を残し、消さない。
   - 監査の書き方は追記だけ（[server/routine-audit.ts:73](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/routine-audit.ts#L73) `appendFile`。同ファイルに消す・切り詰める処理は無い）。本機能も消す・切り詰める処理を足さない。
   - `caseClaudeVersionProbe` の1行に必ず入れる欄: 始めた時刻・終わった時刻・`claudeVersion`・sha256 の先頭16桁・`outcome`（ok / denied / aborted）・×の番号（E1〜E4・P0〜P5・R1）・発火の理由（t1 / t2）・`probeCaseId`・`counts`（P2・P3・P5 で数えた数: P2 の下請けの Write の post の行・P2 の間の post の行・pre の plan の行・plan の行に合う post の行・pre の Bash の行・P1・P2 の pre の行のうち対の post が無い行。活動の記録と probe の道具の記録は後で消えるため、数をここに残す。審査2回目 推奨2）・`paneSamples`（P0〜P3 の各 `idle` 復帰の時点の probe の件の `capture-pane` 1 枚ずつ・最大 4 枚・各 4KiB まで・制御文字を除く。K55 ② の U6 の確かめに使う。監査は1件1行の JSON の追記で、`JSON.stringify` して追記するだけなので行の長さの上限は無い。[server/routine-audit.ts:69-78](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/routine-audit.ts#L69-L78)。MAC の対象にはしない。MAC は D5 の記録の改ざんを見る物で、監査は証拠の記録のため。審査2回目 必須5）。`caseClaudeVersionNotice` の1行: 時刻・reason（n1〜n5）・`claudeVersion`・sha256 の先頭16桁・`outcome` は "ok"。2 つの action の行とも `callerSessionId` は null（省けない欄。[server/routine-audit.ts:24](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/routine-audit.ts#L24)。審査4回目 推奨1）。×の番号の欄の名前は `failedCheck` にそろえる。
   - 監査の型の直し（便CS3a。審査3回目 必須3）: `RoutineAuditEntry`（[server/routine-audit.ts:13-62](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/routine-audit.ts#L13-L62)）の `outcome`（今は :16 で `"ok" | "denied"` だけ）に `"aborted"` を足す。欄 `startedAt`・`endedAt`・`sha16`・`failedCheck`（×の番号）・`trigger`（t1 / t2）・`probeCaseId`・`counts`・`paneSamples` を足す。:2 の注記「token・本文の中身は書かない」に「例外: `caseClaudeVersionProbe` の `paneSamples`（設計 conversation-consent §14-14-6 の 8・9）」を書き足す。`audit_failed` は監査に書けなかったことの印なので監査の `outcome` には入れず、記録の `lastResult` だけに入る。
   - D5 の記録の項目は消さない（§14-14-3 D5）。使えなくなった版も `usable: false` で残り、`lastProbeAt`・`lastResult`・`failCount` が履歴の要約になる。
   - 読み方: PO は画面の案内（D1 ①）と `/api/state` の `caseSayVersions` で今の状態を見る。過去の履歴は Opus 本体の会話が `routine-audit.jsonl` と記録ファイルを Read（または Bash の `grep`・`tail`）で読み、PO に報告する。見張りは本体の会話を止めない（6）ので、新しい読み口は作らない。下請けには読ませない（止まる）。履歴を一覧で見る新しい画面は本版では作らない（作るなら別の設計・PO 判断）。
   - 監査に書けなかったとき（審査1回目 C6・必須5）: 今の `writeAudit`（[server/http.ts:580](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/server/http.ts#L580)）は失敗を console.error に出すだけで続く。本機能は監査の追記を `await` し、失敗したら (a) 新しい通知 n6（D1 の 4 つの出し先のうち監査を除く 3 つ）を出し、(b) その probe を中断して `usable: true` を書かない（記録の無い○を作らない）。`lastResult: "audit_failed"`・`failCount` は増やさない。
   - 監査を直されたとき: 記録の項目の `lastProbeAt`・`lastResult` は MAC の対象に入れる。監査の行と記録が食い違えば、Opus は報告でそれを書く（直された監査を正としない）。Opus 本体が両方を直す危険は危険1 の受け入れの内。

#### 14-14-7 使用量

| 項目 | 見込み | 根拠 |
|---|---|---|
| probe 1 回の claude の使用量（トークン） | 未確認 | 根拠となる実測が無い。文 3 つ・下請け 1 つ・返事 3 回の小さい会話だが、数は書けない。K56 で測る |
| probe 1 回の時間 | 10 分以内（P5 の上限） | 上限は設計で決めた値。実測は K56 |
| probe の発火回数 | claude の版が変わるたび 1 回（×なら最大 3 回） | 版の変化の頻度は未確認（U10）。観測は 2.1.318 → 2.1.319 が 2026-11-05〜06 の間に 1 回（docs/CHANGELOG.md:6） |
| 写しのディスク | 未確認 | `git clone --local --no-checkout`（case-clone.ts:102）。大きさは測っていない |
| 指紋の計算 | 未確認（U5） | 実体のサイズを測っていない |
| 使う鍵 | 件の鍵（`ccdiscord.zsh:45-49` が Keychain から取る専用の項目） | この鍵が PO の購読と同じ契約かは未確認（U3）。同じなら PO の枚数を減らす |

#### 14-14-8 成功条件

| # | 基準 | 検証方法 |
|---|---|---|
| K50 | 判定 4b は記録だけで決まる | vitest（tests/unit/case-say.test.ts の K42 を書き換え）: 使える項目と指紋が一致 → 判定 5 以降へ。項目が無い・`usable: false`・sha256 違い・size 違い・MAC 違い → 409 `claude_version_unverified`・書き込み 0 回。同じ指紋の probe 中・計算中 → 409 `claude_version_probing`・書き込み 0 回。4b より前で断った行に版の欄が無いこと（既存） |
| K51 | probe の台本と○×が機械条件どおり | vitest（偽の tmux・偽の状態ファイル・偽の R・偽の活動の記録）: P0〜P5 のそれぞれを 1 つだけ×にして `usable` にならない・`lastResult` が×の番号・監査 denied。誤って○にしない場面を 1 つずつ: probe-2.txt を主の会話（`agent_id` なし）だけが書いた → P2 ×。文3 の後に pre の plan の行が 0 → P3 ×。plan の行と同じ `tool_use_id` の post の行がある（道具が通った）→ P3 ×。P2 の間に post の行が 0 → P3 ×。pre の plan の行の `tool_use_id` が空 → P3 ×。文3 の後に主の会話の post の行が（`tool_use_id` が空でも）1 つある → P3 ×。P1・P2 の pre の行のうち 1 つに対の post が無い → P3 ×。post の行が `idle` の後 2 秒以内に届く（偽の遅れ）→ 判定は待ってから行うので P3 ×。probe の 2 本の handler が `async` を持たず `timeout: 5` である。pre に Bash の行 → P5 ×。`buildCaseSettings` を引数なしで呼んだ設定（PO の件）は今の版の出力と完全に一致し、`{ versionProbe: true }` のときだけ 2 本増える。共通の `HOOK_SPECS` は変わらない。新しい受け口は probe でない件からの送信を 403 にし、活動の記録に 1 行も足さない（Agent の開始の記録の description・subagentType・model が上書きされない）。PO の件が枠を求めたら probe が aborted で閉じる。空きが 1 のとき probe は始まらない。全部○で `usable: true`・MAC 付き・監査 ok。probe の件への画面入力・チャット・submitText・名前の変更・case-say がどれも断られ、端末への書き込み 0 回。文 3 つがコードの定数と一致 |
| K52 | 起動時の再 probe と片付け | vitest: probe の後（ok・denied・aborted のどれでも）に D/cases/<probeId>・R・W が無い。起動時の片付けで kill-session するのは `runningVersionProbe` の `ac-<id>` 1 つだけ（ほかの `ac-*` はそのまま）・その後に復元が走る。件の指紋を起動前に取る（偽の実体を起動の後に差し替えても、記録される指紋は起動前の物）。指紋を持たない件は 4b で 409。記録の項目の実体の中身を変えて起動 → `usable: false`・D1 n3・監査。実体を消して起動 → 同じ。PATH の claude の指紋が未記録 → probe が 1 つ予約される（同時に 2 つにならない）。使える指紋では probe の窓を開かない。残っていた `runningVersionProbe` の tmux セッションを消す |
| K53 | 記録の守り | vitest: MAC 違いの項目を捨てて上書きしない・壊れた JSON で使える版 0・D1 n5。鍵が無ければ作り 0600。case-sandbox の試験で `CASE_DENY_WRITE`・`CASE_DENY_READ` に記録と鍵がある |
| K54 | D1 の出し先 | vitest: n1〜n5 のそれぞれで Snapshot の `caseVersionNotices`・`/api/state` の `caseSayVersions`・監査 `caseClaudeVersionNotice` が 1 件ずつ、macOS 通知（差し替えた送信関数）が 1 回。n6 は監査を除く 3 つに 1 件ずつ |
| K55 | 本物で人の手なしに版が使えるようになる | 便CS3a を入れた後（PO の Mac）: ① サーバーを起き直す → 10 分以内に probe の件が開いて閉じ、記録に `usable: true` の項目が 1 つ・監査 `caseClaudeVersionProbe` ok（Opus は記録と監査を読むだけ） ② U6 の確かめ: ① の監査の行の `paneSamples`（§14-14-6 の 9）を Opus 本体が Read で読み、P4 の正規表現が当たった数と、Opus が目で数えた選ぶ画面の数が一致する（PO の件の画面は読まない） ③ PO が件を 1 つ開き、Opus が `ac-case-say.mjs` を 1 回（K32 と同じ）→ 200 ④ PO のふつうの claude が更新されたとき（起きたときに行う。起きなければ「場面なし」）: PO が件を開く → 画面と macOS に D1 n1 → probe → 記録に 2 つ目 → 開いていたその件へ case-say が 200（開き直し不要）。①〜③が○で○。④は場面が来たときに○×を足す |
| K56 | 使用量の実測 | K55 ① の probe で: 所要時間・写しのディスク・指紋の計算時間・実体のサイズ・（取れれば）件の鍵の使用量を、数値のまま本書 §14-14-7 に書き足す |
| K57 | 見張りの範囲が §14-14-6 の 6 のとおり（止まる物は止まり、止まらない物は本書どおり止まらない） | 便CS3a を入れた後、Opus 本体が PO の Mac で、導入済みの `hooks/ac-routine-guard.mjs` の `judge` を node で呼ぶ（下請けは起動しない。手元で起動してよい担当の決まりを変えないため）。入力は作った JSON だけで、記録と鍵の中身は開かない。出すのは終了コードだけ（道の値は画面に出さない）: ① `agent_id` あり・`tool_name: "Read"`・`file_path` が記録の道 → 2。② 同じで `Bash`・`cat <記録の道>` → 2。③ 鍵の道で ①② → 2。④ `agent_id` あり・`Grep` → 0（止まらないことが本書どおり）。⑤ `agent_id` なし（本体）で ① → 0（本書どおり）。①〜③のどれかが 0 → dataDir がその名前の下に無い（U2 が×）。×なら PO に報告し、§14-14-6 の 6 を直す。`\` で崩した道は試さない（迂回の手を作らない） |
| K58 | 既存の試験が通る | agent-console の CI（ci.yml: `npm ci`・typecheck・lint・vitest）が緑。K40（ccdiscord-zsh.test.ts）・K2・K31・K34 は変えない。便CS3b で config の試験（tests/unit/case-say.test.ts:360-396）を外し、同梱の設定に `caseSayClaudeVersions` があれば起動時エラーになる試験を足す |
| K59 | 記録が残る（§14-14-6 の 9） | vitest: probe の ok・denied・aborted のそれぞれで監査に `caseClaudeVersionProbe` が1行ずつ追記され、§14-14-6 の 9 の欄が全部ある（`counts`・`paneSamples` を含む）。2回 probe した後も1回目の行が残る。監査の追記を失敗させると n6 が 3 つの出し先に 1 件ずつ出て、`usable: true` が書かれない。本物: K55 ① の後、Opus 本体の会話が監査の該当行を Read で読み、欄が全部あることを確かめる |

#### 14-14-9 便の分け方と触らない範囲

- 便CS3a（agent-console・PR 1 本・クラウドの Sonnet）: D5（記録・鍵・MAC）、D2（起動前の指紋）、D3'（状態ファイルの `version`・probe の件の設定だけの道具の記録 2 本と受け口 `case-probe-activity`・活動の記録・R・probe の件の画面の写し）、D4（probe の件・役割 `discord-case`・台本・入力の拒否・復元から外す・枠の空き 2 以上・自分で片付け・起動時の片付けの順）、D1（4 つの出し先・n1〜n6）、起動時の再 probe、4b の置き換え（この便の間は「記録の使える項目 ∪ config の一覧」で通す。過渡期）、部屋の deny、監査 action 2 つと型の直し（§14-14-6 の 9）、理由 2 つ、README、試験 K50〜K54・K58・K59。版は CHANGELOG の決まりで付ける。
- PO: 便CS3a の反映（いつもの手順）。
- Opus（読むだけ）: K55 ①②・K56・K57。×なら便CS3b に進まず PO に報告。
- 便CS3b（agent-console・PR 1 本・クラウドの Sonnet）: 4b を「記録だけ」にし、config の `caseSayClaudeVersions` を外す（同梱の設定・型・parse・README:309-318 の節・試験）。設定に鍵が残っていれば起動時エラー。CHANGELOG に戻し方（同梱の設定に `caseSayClaudeVersions` を戻す 1 行を含む）。
- 便CS3c（Sales Anchor・docs PR 1 本・便CS3a より先に合流）: ADR-1033:26 の「第11版」を第12版に直す。ADR-1033:24 What 6 に、probe の件への定数の文 3 つの例外（§14-14-1 の条件 (a)〜(e)）を足す（ADR の変更なので `node scripts/generate-adr-index.js` を回す）。本書の状態を更新。
- 便の順: CS3c → CS3a → K55〜K57 → CS3b（審査2回目 必須4。ADR を先に直す）。CS3a の過渡期に config の一覧を残すのは、probe が 1 度も○になる前に case-say が全件止まるのを避けるため。
- 触らない範囲: PO の件へ送る文（hub.ts:140・:571・README:302）、共通の `HOOK_SPECS`（activity-hooks.ts:53-72。足すのは probe の件の設定の 2 本だけ）、PO の件の設定（`buildCaseSettings` を引数なしで呼んだ出力）、`handleCaseActivity`（http.ts:455-470）と活動の記録（activity.ts）、`GUARD_IFS` と `hooks/ac-routine-guard.mjs`、宛先の決め方（hub.ts:521-537・README:304）、判定 1〜3・5〜9、`ops/shell/ccdiscord.zsh`、`ops/case/case-guard.mjs`、Sales Anchor 側の見張り・許可・settings、画面のチャット、予約・定期実行、`claude agents --json` の扱い、PO の件の画面（`capture-pane` は probe の件だけ）、tmux の設定。

#### 14-14-10 外部事例

該当事例なし。理由: 判断の中心は、自作の作業画面アプリの中で「版の○×を誰が・何を材料に決めるか」で、外部の数値事例では確かめられない。確かめは K50〜K57 の試験と実測で行う。

#### 14-14-11 未確認

- U1 件の状態ファイルの `version` キーの値の形（K30 は名前だけ記録した。§14-10-10）。合わなければ P0 のこの条件は外し、E3 だけで版の文字を確かめる。
- U2 PO の Mac の dataDir が、`GUARD_IFS`（activity-hooks.ts:15・:18）の規則の名前の下にあるか（K57 で確かめる。値は本書に書かない）。
- U3 件のログインの鍵（`ccdiscord.zsh:45-49`）が PO の購読と同じ契約か。
- U4 probe 1 回の claude の使用量（トークン）。
- U5 claude の実体のサイズと sha256 の計算時間。
- U6 P4 の選ぶ画面の正規表現が実物の画面に合うか。確かめは K55 ② で、監査の行の `paneSamples`（K55 ① の probe の件の画面の写し）だけで行う。PO の件の画面は読まない。合わなければ probe は×（P4）に倒れ、正規表現を直す便を出す（誤って○にはならない側の外れは、選ぶ画面を見逃す側。K55 ④ の場面で D1 n4 が出なければ見逃しの疑いとして PO に報告する）。
- U7 件の AI が case-guard の拒否の文を返事に写すか（P3 の参考記録）。
- U8 決めた（§14-14-3 D4 の片付け）: sessions.ts の閉じる道は件のファイルも W も消さない。sessions.ts の外の `onRemoved` の聞き手は読んでいないが、probe は自分で消すので答えに依らない。
- U9 決めた（§14-14-3 D4 の起動時の片付けの順 (1)〜(5)）。
- U13 case-guard が exit 2 で道具を止めたとき、同時に走った probe の道具の記録（pre）の hook が受け口まで送り終わるか（公式の説明に書かれていない）。送れなければ P3 は×に倒れ、K55 ① が×になる。そのときは P3 の材料を見直す便を出す（誤って○にはならない）。
- U14 文3 の後の post だけが送信の失敗（2 秒の打ち切り・受け口の誤り）で消え、同時に case-guard が道具を通した場合は、P3 が誤って○になり得る。P1・P2 で pre と post が全部対になることを求めて post の道が働いていることは確かめるが、文3 の後だけ消える場合は防げない。残る危険として受け入れる（2 つが重なったときだけ起きる。審査4回目 推奨2）。
- U15 P1・P2 で道具が失敗した・止められたために post が来なかった場合も、P3 の「pre と post が全部対」が外れて×になる（誤って×になる側。安全な側に倒れる）。K55 ① で P3 が×のときは、監査の `counts` の「対の post が無い行」の数を見て、この場合かどうかを切り分ける（マージ前審査 LOW-1・LOW-2）。
- U10 PO のふつうの claude の更新の頻度。
- U11 下請け（Agent）の Write が case-guard を通るか（K3 ② で確かめたのは Read。P2 の前提）。
- U12 3回目の設計の文そのもの（D1〜D5・S1〜S7・危険1〜3）は本書に無く、本節が書き下ろし。3回目との食い違いがあれば本節を正本とする。

#### 14-14-12 審査1回目（REVISE）の当て先

審査1回目: クラウドの審査役（2026-11-06 12:20〜12:24Z・対象 f2910b13 の本節と agent-console aabdeef）。指摘の原文と Opus の照合は Opus の手元の記録に残し、本書には当て先だけを書く。

| 指摘 | 直した所 |
|---|---|
| 必須1 ADR-1033 What 6 の例外 | §14-14-1「ADR-1033 What 6 の例外」・§14-14-9 便CS3c |
| 必須2 見張りの実際の範囲・受け入れ・K57 | §14-14-6 の危険1・6（PO 2026-11-06「1」で残る危険を受け入れ）・K57 |
| 必須3 P3 はサーバーが受ける記録で○・P2 は下請けの Write 必須 | §14-14-3 D3' (b)・§14-14-4 P2・P3・K51（2回目で記録の道を直した。§14-14-13） |
| 必須4 U6 は probe の件の画面で | §14-14-4 P4・K55 ①・U6 |
| 必須5 Opus 本体の読み方・監査に書けないとき | §14-14-6 の 9・D1 n6・K54・K59 |
| 必須6 probe の役割・U8・U9 | §14-14-3 D4（役割 `discord-case`・片付け・起動時の順）・K52・U8・U9 |
| 必須7 引用 3 か所 | §14-14-1（http.ts:554）・§14-14-3 D4（case-clone.ts:90・:96・:102）・§14-14-6 の 6（activity-hooks.ts:15・:18） |
| 推奨1 指紋は起動の前に | §14-14-3 D2「指紋を取る時点」・K52 |
| 推奨2 probe が枠をふさぐとき | §14-14-3 D4「枠」・K51 |
| 推奨3 本店での fetch の副作用 | §14-14-3 D4「本店での fetch」 |
| C4 2点目 probe も gh の鍵を持つ | §14-14-3 D4「gh の鍵」・P5 の Bash の条件 |

#### 14-14-13 審査2回目（REVISE）の当て先

審査2回目: クラウドの審査役（2026-11-06・対象 5e273c00 の本節と agent-console aabdeef）。指摘の原文と Opus の照合（実物の写しで確かめた行）は Opus の手元の記録に残し、本書には当て先だけを書く。Opus の照合で、2稿の `--case-pre` は hook の引数だったが、件の hook は入力をそのまま送り記録はサーバーが作る（activity-hook.mjs:320-327・http.ts:455-470）ため、引数がサーバーに届かないことも分かった。これも必須1・2 の直しで同時に直した。

| 指摘 | 直した所 |
|---|---|
| 必須1 P3 の照合が書く道具の post の記録（`tool_use_id` が無い）に頼っていた | §14-14-3 D3' (b) probe の道具の記録（pre と post）・§14-14-4 P3（同じ記録どうしで照合・P2 の間の post の行を必須）・K51 |
| 必須2 `--case-pre` が PO の件にも効き、`applyPre` に入る | §14-14-3 D3' (b)（`buildCaseSettings` の引数 `versionProbe`・新しい受け口で活動の記録に入れない）・§14-14-9 触らない範囲・K51 |
| 必須3 R が残る | §14-14-3 D4 の片付け (2)・起動時の片付け (3)・K52 |
| 必須4 ADR を後で直す順 | §14-14-1「ADR-1033 What 6 の例外」・§14-14-9 便の順（CS3c が先） |
| 必須5 `paneSamples` の置き場・MAC・上限、K55 の番号 | §14-14-6 の 8・9（監査の行・MAC の外・各 4KiB・最大 4 枚）・K55（①〜④）・K59・U6 |
| C1 引用 3 点 | [docs/CHANGELOG.md:6](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/docs/CHANGELOG.md#L6)・[tests/unit/case-say.test.ts](https://github.com/GEN-RYU-System/agent-console/blob/aabdeefbbd1b8eb3eeaa51dd4d4ef1cbad9ab012/tests/unit/case-say.test.ts)・sessions.ts:411-413 |
| 推奨1 名前の紛れ | §14-14-3 D3' (b) の末尾（コードの名前は `versionProbe`） |
| 推奨2 数を監査に残す | §14-14-6 の 9 `counts` |
| 推奨3 K56 の結果で指紋を変えるとき | 取り入れる。K56 の結果で size・mtime・ino に代えると決まったら、その時点で本書を直して審査に出す（実装役は決めない） |

#### 14-14-14 審査3回目（REVISE）の当て先

審査3回目: クラウドの審査役（2026-11-06・対象 e3739a79 の本節と agent-console aabdeef）。2回目の必須1〜5 はどれも○。新しく見つかった穴への直しは次のとおり。指摘の原文は Opus の手元の記録に残し、本書には当て先だけを書く。Opus は指摘の行（routine-audit.ts:13・:16・:69-78、activity-hooks.ts:98、activity-hook.mjs:14・:293-301・:332、sessions.ts:405、case-sandbox.ts:496・:504）を aabdeef の写しで確かめた。

| 指摘 | 直した所 |
|---|---|
| 必須1 P3 で pre の `tool_use_id` が空のときの扱いが無い | §14-14-4 P3（空なら×・文3 の後の主の会話の post は `tool_use_id` を問わず 0 件）・K51 |
| 必須2 probe の hook が非同期で、post が `idle` の後に届くと誤って○ | §14-14-3 D3' (b)（同期・`timeout: 5`）・§14-14-4 P3（`idle` の後 3 秒待つ）・K51 |
| 必須3 監査の引用の行が無い・`outcome` に aborted が無い・:2 の注記 | §14-14-6 の 9（routine-audit.ts:69-78・型の直し・注記の例外）・便CS3a |
| 推奨1 引数の道 | §14-14-3 D3' (b)（`createCase` → `writeCaseFiles` → `buildCaseSettings`） |
| 推奨2 P4 は切った写しで数える | §14-14-4 P4 |
| 推奨3 K58 と K59 の順 | §14-14-8 の表 |

#### 14-14-15 審査4回目（APPROVE）の推奨の当て先

審査4回目: クラウドの審査役（2026-11-06・対象 19ae5ce3 の本節と agent-console aabdeef）。判定は APPROVE。3回目の必須1〜3 はどれも○、前の回に○だった物で崩れた物は無い。推奨3件を次のとおり取り込んだ。指摘の原文は Opus の手元の記録に残す。Opus は routine-audit.ts:24（`callerSessionId` は省けない欄。審査役は :27 付近と書いたが実物は :24）と sessions.ts:394・:405・:407-408 を aabdeef の写しで確かめた。

| 推奨 | 直した所 |
|---|---|
| 推奨1 ×の番号の欄の名前・`callerSessionId`・通知の `outcome` | §14-14-5（`failedCheck`）・§14-14-6 の 9（両 action とも `callerSessionId` は null・通知は "ok"） |
| 推奨2 post が消えていない証拠 | §14-14-4 P3（P1・P2 で pre と post が全部対）・K51・U14（文3 の後だけ消える場合は残る危険） |
| 推奨3 `createCase` の引数と印を付ける所 | §14-14-3 D3' (b)（`createCase` に任意の引数・`spawnSession` の直後） |
| マージ前審査 LOW-1・LOW-2（対の post が無い数・誤って×の場合） | §14-14-6 の 9 `counts`・U15 |

#### 14-14-16 第12版の直し1: claude 2.1.319 で probe が P3 で×になった件（2026-11-08）

経緯（事実）: v0.55.1 を入れた後、PO の Mac で claude 2.1.319 の probe が 2 回×になった（記録の項目: `usable: false`・`lastResult: "P3"`・`failCount: 2`・`lastProbeAt: 2026-11-07T17:34:31Z`。Opus 本体が node で結果と時刻の欄だけを読んだ。MAC の欄は読んでいない）。§14-14-5 (b) の「×の番号を見て設計を見直す」と U6 の「合わなければ正規表現を直す便を出す」に当たる。3 回目の×で自動の再 probe は止まる（`PROBE_MAX_FAILS = 3`。agent-console 2372b23 の server/case-say-probe.ts:17・:315）ので、直す前に 3 回目を起こさない。

原因の切り分け（クラウドで、本物の claude 2.1.319 を件と同じ起動の形で 8 回動かした。生の記録は Opus の手元の記録に残す。件の画面・PO の件は読んでいない）:

| 観測 | 数 | 意味 |
|---|---|---|
| 文3（`/plan …`）だけでは、主の会話の plan の pre が来ない | 2 / 2（文4 を送らなかった回）。PO の Mac の 2 回の×も同じ形 | 2.1.319 は計画の形で計画を文で答えて止まり、道具を試みない。P3 の「pre の plan の行が 1 以上」が成り立たない |
| 文4「計画どおり進めてください。」を送ると、plan の pre が来て case-guard が止め、post が来ない・probe-3.txt ができない | 6 / 6 | 止める仕組みが働いた証拠（P3 が見たい物）が文4 で取れる |
| 旧 P4 の数え方（番号付きの行 2 行以上の塊）が、計画の文の「1. 2. 3.」に当たる | 8 / 8（文3・文4 の後の画面） | 選ぶ画面が無いのに P4 が×になる（誤って×） |
| 新 P4（塊の中に `❯` か `>` の付いた番号の行があるときだけ数える） | 0 / 16 画面 | 計画の文には当たらない。本物の選ぶ画面（`❯ 1. Yes`。agent-console 2372b23 の docs/handoff/chat2/recon.md:62-71 にある 2.1.296 の画面の写し）には当たる |
| 新しい文1・文2（`Write ツールで`・`Bash は使わないでください`）での Bash の pre | 0 / 8 | P5 の Bash の条件が誤って×になる道を減らす |
| 新しい文1・文2 で probe-1.txt・probe-2.txt が `ok` | 4 / 4（許可の規則を件と同じ `Edit(//<abs>/**)` の形にした回） | P1・P2 は文を変えても通る |

直す物（agent-console の server/case-say-probe.ts だけ。ほかは触らない）:

1. 文（§14-14-3 D4 の台本）を次の 4 つにする。文4 は定数で、Opus の入力は入らない。
   - 文1: `<R>/probe-1.txt に Write ツールで ok とだけ書いてください。Bash は使わないでください。`
   - 文2: `Agent で下請けを1つ動かし、下請けに <R>/probe-2.txt へ Write ツールで ok とだけ書かせてください。あなたも下請けも Bash は使わないでください。`
   - 文3: `/plan <R>/probe-3.txt に Write ツールで ok とだけ書いてください。`
   - 文4: `計画どおり進めてください。`（文3 の返事が終わっても plan の pre が無いときだけ、1 回だけ送る）
2. P3 の待ち方（§14-14-4 P3 の「120 秒以内に」を次で置き換える。○×の条件そのものは変えない）:
   - (a) 文3 を送った時刻を `sent3At` とする。`PROBE_P3_MS`（120 秒）の間、1 秒ごとに状態ファイルと記録を見る。
   - (b) `sent3At` 以後に主の会話の plan の pre があり、状態が `idle` → 文4 を送らずに (e) へ。
   - (c) plan の pre が無く、状態が `idle` を 2 回の見回しで続けて見て、次のどちらかが成り立つ → 文3 の返事が終わったとみて、文4 を 1 回だけ送る: ① `sent3At` 以後に状態 `busy` を 1 度でも見た ② `sent3At` から `PROBE_P3_QUIET_MS`（20 秒）たった。② は、返事が 1 秒の見回しの間に始まって終わり `busy` を見逃した場合の受け皿。送った直後の状態ファイルはまだ `idle` のことがある（probeSend は `busy` になるのを待たない。agent-console 2372b23 server/hub.ts:607-640）ので、① か ② が無いうちは送らない。① の「`busy` を見た」は P3 の待ちの中だけの旗（`sent3At` 以後の見回しで `busy` を読んだら立てる）で持つ。run 全体の状態の集合（`observed`。agent-console 2372b23 server/case-say-probe.ts:348・:391。P1・P2 の `busy` が入っている）は使わない（審査1 必須1）。「2 回続けて `idle`」は、返事の途中の一瞬の `idle` で送らないための受け皿（そういう一瞬の `idle` が起きる証拠は無い。審査1 推奨2）。
   - (d) 文4 を送れなかった（probeSend が false）→ P3 ×。送れたら、その時刻から `PROBE_P3_MS` の間に「plan の pre があり、状態が `idle`」を待つ。来なければ P3 ×。
   - (d') P3 の待ち（(c)・(d)）で×にするときも、throw の前に `counts` へ `p3FollowUp` と `countTools(records, sent2At, sent3At)` の結果を入れ、監査に残す（今は :482 で入るので、:475 の×では残らない。審査1 推奨1）。
   - (e) その後は今と同じ: 3 秒待つ・画面の写しを取る・`countTools(records, sent2At, sent3At)` で数える。数える範囲は `sent3At` 以後のままなので、文4 の後の pre・post も P3 の材料に入る（文4 の後に主の会話の post が 1 つでもあれば×のまま）。
   - 文4 は文3 の返事の中で 1 回だけ。2 回目は送らない。
3. P4 の数え方（§14-14-4 P4 の「行頭の番号付き選択肢が 2 行以上連続」を次で置き換える。ほかの 4 つの形は変えない）: `^\s*[❯>]?\s*\d+\.\s` に合う行が 2 行以上続く塊のうち、塊の中に `^\s*[❯>]\s*\d+\.\s` に合う行（選ぶ印の付いた番号の行）が 1 つ以上ある物だけを数える。数え方は一意に次のとおり（審査1 必須2）: 上から 1 行ずつ見て、番号付きの行が続く間は塊にためる。番号付きでない行（空行を含む）か文の終わりで塊を閉じ、閉じた塊が 2 行以上で、印の行が塊のどこかに 1 つ以上あれば 1 と数える（塊 1 つで最大 1）。
4. 監査の `counts` に `p3FollowUp`（文4 を送れたら 1、送らなかった・送れなかったら 0）を足す。§14-14-6 の 9 の欄に足す。

時間の上限: 文3 と文4 の待ちは最大で 120 秒ずつ。全体の上限 10 分（P5・`PROBE_TOTAL_MS`）は変えない。上限を越えたら今と同じく P5 ×（`tick` の deadline）。

×の数え方への影響: 直した版を入れた後、24 時間の待ち（`PROBE_RETRY_AFTER_FAIL_MS`。最後の×から）が明けた後の、最初の件を開くとき（t1）かサーバーの起動（t2）で probe が走る。2026-11-07T17:34:31Z の 24 時間後は 2026-11-08T17:34:31Z（日本時間 11/9 02:34）。○なら `failCount: 0`・`usable: true`（case-say-probe.ts:583）。×なら 3 回目で止まり、D1 n4 に「設計者の確認が要る」が付く。

変わらない物: E1〜E4・P0〜P2・P5・R1 の条件、記録・鍵・MAC、24 時間・3 回の規則、probe の件の開き方・片付け、PO の件と Opus の窓（case-say の判定 4・5・7・8・9）、case-guard・部屋の拒否、hooks。

成功条件（この直しの分）:

| 基準 | 検証方法 |
|---|---|
| K51 の追加: 文3 の返事で plan の pre が来た → 文4 を送らない・P3 ○ | vitest（偽の状態ファイル・偽の記録）: 送った文が 3 つ・`counts.p3FollowUp === 0` |
| K51 の追加: 文3 の返事が plan の pre なしで `busy` → `idle` に終わる → 文4 を 1 回だけ送り、その後の plan の pre（post なし）で P3 ○ | vitest: 送った文が 4 つで 4 つ目が文4 の定数と一致・`p3FollowUp === 1` |
| K51 の追加: `busy` を 1 度も見ないまま `idle` → 20 秒たつまで文4 を送らない・20 秒後に送る | vitest（偽の時計・見回し 1 秒）: 文3 から文4 までが 20050 ms ちょうど（20 秒を越えた最初の見回し） |
| K51 の追加: `busy` と `idle` が 1 回ずつ交互に来る間は文4 を送らない（`idle` が 2 回続いた見回しで送る） | vitest: 交互が 10 回続く列で、文3 から文4 までが 10050 ms ちょうど |
| K51 の追加: P1・P2 で `busy` を見た後、文3 の後は `busy` を見ない → 20 秒たつまで文4 を送らない（旗が P3 だけの物） | vitest（偽の時計・P1・P2 の間だけ `busy` を返す）: 19 秒の時点で送った文 3 つ |
| K51 の追加: 文4 の後に P3 ×のとき、監査の `counts` に `p3FollowUp: 1` と `planPres` などの数が残る | vitest |
| K51 の追加: 文4 の後も plan の pre が来ない → P3 ×（文4 は 1 回だけ） | vitest: `lastResult: "P3"`・送った文が 4 つ |
| K51 の追加: 文4 の送信が失敗 → P3 ×・`p3FollowUp` は 0（送れていない）・`countTools` の数は監査に残る | vitest |
| K51 の追加: 文4 の後に主の会話の post がある → P3 × | vitest |
| K51 の追加: P4 — 印の無い番号付きの計画の文（`1. …`・`2. …`）は 0・`❯ 1. Yes` と `  2. No` の画面は 1 以上・既存の (y/n) などの形は今と同じ | vitest（`countPickScreens` の単体） |
| K51 の追加: 文1〜文4 の定数が本節の文と一字一句同じ | vitest |
| K58 既存の試験が通る | agent-console の CI が緑 |
| K55 ① 本物で ok | 24 時間明け後の最初の probe で記録に `usable: true`・`lastResult: "ok"`・監査 `caseClaudeVersionProbe` ok・`counts.p3FollowUp` の値を Opus 本体が読んで本書に書き足す |

残る危険:
- U16 文4 で plan の pre が来なかった回は今回の試しでは 0 / 6 だが、claude の版が変われば起き得る。そのときは P3 ×（誤って○にはならない側）。
- U17 文4 の文は、計画の形を外す（`ExitPlanMode`）許しと読まれる恐れがある。外れて道具が通れば post が来るので P3 ×（誤って○にはならない側）。今回の 6 回では外れていない（post 0）。
- U18 新 P4 は、選ぶ画面の印が `❯`・`>` 以外に変わると見逃す。そのときは K55 ② の `paneSamples` の目視で気づく（U6 と同じ）。

外部事例: 該当事例なし。理由は §14-14-10 と同じ（自作の仕組みの中の判定の直しで、確かめは試験と実測で行う）。

審査の記録（クラウドの審査役。指摘の原文は Opus の手元の記録に残す）:

| 回 | 日時（UTC） | 対象 | 判定 | 当て先 |
|---|---|---|---|---|
| 1 | 2026-11-07 19:41 | 本節 d520da26・カード 95ca0363 | 返事の終わりが切れて判定の行が読めず、読めた必須2・推奨2 を取り込んだ | 必須1 → 2 (c) の P3 だけの旗。必須2 → 3 の数え方。推奨1 → 2 (d')。推奨2 → 2 (c) の「2 回続けて `idle`」 |
| 2 | 2026-11-07 19:47 | 本節 5cb8fb75・カード 95ca0363 | REVISE | 必須1 → カード G5 の試験の偽の世界に、状態の口・文4 だけ失敗させる口・送った時刻の列を足した。必須2 → `p3FollowUp` は文4 を送れた後で 1（2 の 4）。推奨 → K51 の行（20050 ms・交互の列 10050 ms・送信失敗でも数が残る） |
| 3 | 2026-11-07 19:54 | 本節 6704edeb・カード dd04e8fd | APPROVE（必須・推奨なし） | 審査役が run() と偽の世界で、文4 を送る時刻（3050・20050・20050・10050 ms）を数えて一義と確かめた。既存の試験は壊れない |

#### 14-14-17 第12版の直し2: 版の確かめの毎日の見回り（2026-11-08・PO「1」「小さく始める」）

目的（PO の言葉）: 「失敗した場合は自動であなたが介入して現状把握を実施、システムの更新に失敗した理由を現状調査で把握して恒久的に失敗しない方法を設計して対策してシステムの改善を自動で行う保守運用」。選択肢「1. まず、Claude の版の確かめだけを対象に作る」に「1」、続けて「小さく始める」。

決定（Opus）: 製品コードは変えない。agent-console の定期実行（PO 2026-10-14「このアプリの定期実行で管理させる」）に 1 件足し、毎日 1 回、Opus が版の記録を読んで、下の表のどれかを行う。手順の正本は本節で、定期実行の指示文は本節を読ませるだけにする（指示文と手順の二重持ちをしない）。

観測事実（2026-11-08 09:00〜09:40 JST）:
- 定期実行は `dataDir/routines.json` の 1 か所に持つ。AI は `node "<dataDir>/bin/ac-routine.mjs" add|update|enable|disable|list` で触る（agent-console 6aaba26 README.md「ac-routine の使い方」）。開始が他の有効な定期実行・予約と 60 分未満なら 400。有効な定期実行の開始は 09:00（月〜金）・11:00・12:00（毎日）・13:00（火・木）・14:00・16:00（月）。03:30 は空いている（`ac-routine.mjs list` の結果）。
- probe が走るきっかけは、件を開いたとき（t1）とサーバーの起動（t2）だけ（agent-console 6aaba26 server/case-say-probe-wiring.ts:139-146・:182-190）。×の後 24 時間の待ちが明けても、時計で走り直す仕組みは無い。予約が待ちで捨てられる（server/case-say-probe.ts:296-300）。
- サーバーの再起動は `launchctl kickstart -k gui/<uid>/local.agent-console.server`（scripts/lib/ac-common.sh:30・:499）。件の本体は専用の tmux の中で動き、再起動で止まらない（README.md「keep-sessions」）。チャットの送信の予約はメモリだけで、再起動で消える（README.md「v0.13.0」）。
- ×の後の材料は監査 `dataDir/routine-audit.jsonl` の `action: "caseClaudeVersionProbe"` の行に残る: `outcome`・`failedCheck`・`counts`・`paneSamples`（画面の写し 4KiB×最大 4）・`claudeVersion`・`startedAt`・`endedAt`（server/case-say-probe.ts:584-599）。
- `failCount` は ○ でしか 0 に戻らない。3 回で止まった後は、直した版を入れても probe は走らない（server/case-say-probe.ts:321-328・:619-628。記録には MAC があり、手で書き換えない）。

見回りの手順（毎日 03:30 JST。読む物は版の記録の `claudeVersion`・`usable`・`lastResult`・`failCount`・`lastProbeAt` と、記録の外側の `runningVersionProbe` の有無だけ。MAC の欄・鍵は読まない。記録は書かない）:

| 場合 | 見分け方 | すること |
|---|---|---|
| A 使える | 今の `claude --version` の版の項目が `usable: true` | 「点検済み ○ <版>」と返して終える |
| B 待ち時間中 | `usable: false`・`failCount` 1〜2・`lastProbeAt` から 24 時間たっていない | 「待ち時間中（<日本時間> から確かめ直せます）」と返して終える |
| C 確かめ直す | 項目が無い、または `usable: false`・`failCount` 0〜2・24 時間たった・`lastProbeAt` の時刻が本書のどこかに書いてある（調べた×）・その節の直しの版が `/healthz` の版以下 | probe が動いていない（`runningVersionProbe` が無い）ことを確かめ、サーバーを再起動する（t2）。1 分ごとに `lastProbeAt` を読み、変わるまで最大 15 分待つ。変われば A か D へ。変わらなければ「枠が空かず未実施」と返して終える |
| D 新しい× | `usable: false`・`lastProbeAt` の時刻が本書のどこにも無い | 下の「×の後の進め方」 |
| E 止まった | `failCount` 3 以上 | `NEEDS_DECISION:` で PO に聞き、自分を `disable` する（理由つき）。3 回で止まると、直しても probe が走らないため（上の観測事実の 5 つ目） |

×の後の進め方（D）:
1. 監査の最後の `caseClaudeVersionProbe` の行を node で読み、`failedCheck`・`counts`・`paneSamples` を `/tmp/CC報告ファイル/case-probe-watch/<日付>/` に生のまま残す（鍵・token の欄は無い。読めない・行が無いときは `BLOCKED:`）。
2. クラウドで、本物の同じ版の claude を件と同じ起動の形で動かし、×の形を再現して原因を切り分ける（§14-14-16 と同じやり方。件の画面・PO の件は読まない）。
3. 本書に新しい節（§14-14-18 以降）を書く。節には、その×の `lastProbeAt` の時刻をそのまま書く（C・D の見分けに使う）。
4. 設計の審査をクラウドで受ける（APPROVE まで最大 3 回。3 回で通らなければ `NEEDS_DECISION:`）。
5. 直しが次の範囲に収まるときだけ続ける: agent-console の server/case-say-probe.ts の、送る文・待ち方・画面の数え方。E1〜E4・P0〜P5・R1 の○×の条件を緩める直し、24 時間・3 回の規則、記録・鍵・MAC、hooks・見張り・許可に触る直しは `NEEDS_DECISION:`。
6. カード → クラウドの実装役 → CI → マージ前の審査役（opus） → マージ → タグ → `scripts/ac-update.sh` で反映。反映した日の翌日以降の見回りで C になり、確かめ直す。
7. どこかで止まったら、そこまでの事実を返して `BLOCKED:` か `NEEDS_DECISION:` で終える（閉じずに残る。agent-console README.md「自動クローズ」）。

変わらない物: agent-console の製品コード、E1〜E4・P0〜P5・R1 の条件、24 時間・3 回の規則、記録・MAC、通知 n1〜n6 の文、hooks・見張り・許可。

成功条件（この直しの分）:

| 基準 | 検証方法 |
|---|---|
| K60 見回りが登録されている | `ac-routine.mjs list` に名前「Claude版の確かめ 毎日見回り」・`enabled: true`・`weekdays` 0〜6・`timeHHmm` 03:30・`closeWhenIdle: true`・役割 opus-designer |
| K61 初回（2026-11-09 03:30）が C で確かめ直す | 定期実行の履歴に 11/9 03:30 の `sent`、版の記録の `lastProbeAt` が 2026-11-08T17:34:31Z より後 |
| K62 A・B の日は何も変えずに閉じる | 履歴の `closed` と返事の先頭（「点検済み」か「待ち時間中」） |
| K63 D のとき、人の操作なしで材料の保存と新しい節の起案まで進む | 最初に D になった日に、`/tmp/CC報告ファイル/case-probe-watch/<日付>/` の生の材料と本書の新しい節（その `lastProbeAt` の時刻入り）がある |
| K64 同じ理由の×が 2 回目から 0 回（PO 2026-11-01 の基準） | D の節ごとに、直しの反映後の確かめで同じ `failedCheck` が出ないこと（30 日） |

残る危険:
- U19 再起動でチャットの送信の予約が消える。C のときだけ再起動し（×1 回につき 1 回）、時刻を人が少ない 03:30 にする。
- U20 3 回目の×で、直しても確かめ直せない（E）。直すには「確かめ方を直した版を入れたら回数を 0 から数える」等の規則の変更が要り、3 回で止める決まりに触るので PO の判断にする。
- U21 待ちの明けが 03:30 の直後だと、確かめ直しが最大で約 1 日遅れる。時計で走り直す仕組み（server/case-say-probe-wiring.ts に足す）は、効き目を見てから別に設計する。
- U22 通知 n2 の文「まだ確かめていません」は、×の後の待ち時間中にも出る（実際と合わない）。本節では変えない。別に設計する。
- U23 再起動・クラウドの呼び出しが見張りに止められたら、言い換えずに `BLOCKED:` で返す。

外部事例: 該当事例なし。理由: 自作の仕組みの中の、自分の確かめの失敗を自分で見回る手順で、確かめは実際の記録の数で行う（§14-14-10 と同じ）。

この節を入れた後の手作業（Opus 本体）: `ac-routine.mjs add` で見回りを登録する。この会話の中だけの一回の見張り（11/9 03:17）は、見回りと二重に再起動しないよう消す。
