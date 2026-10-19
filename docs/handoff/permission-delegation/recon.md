<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ。リポジトリ外のパスはバッククォートを付けない -->
# Phase 2 現在地 — Opus の権限の自律管理（台帳と週次点検）

**日付**: 2026-10-19
**担当**: Planner（Opus）。事実の採取は Sonnet の読み取り調査（2026-10-19）と Opus の Bash 実測。
**凡例**: 【事実】=コマンド・ファイルで確認／【推測】／【未確認】。秘密の値は書かない。

## 0. 既存 ADR の検索

- `git grep -il "permit\|権限\|autoMode" docs/adr/` で関連を確認。直接関係するのは次の3本。
  - `docs/adr/ADR-1011-permission-self-maintenance.md`（許可の自律保守。autoMode.allow の `SM-` の文だけを週次で足し引きする）。台帳は `docs/handoff/design-approval-ticket/permission-ledger.md`（30行、2026-10-13〜）。
  - `docs/adr/ADR-1033-conversation-consent-ticket.md`（会話の同意票。§維持の仕組みに「同意と権限の週次点検」）。
  - `docs/adr/ADR-1003-go-delegation-to-opus.md`（GO 発行の委譲）。
- 【事実】ADR の最大番号は ADR-1033（`git ls-tree --name-only origin/main docs/adr/`、2026-10-19）。本件は ADR-1034 とする。

## 1. 権限にあたるものと置き場所

| # | もの | 置き場所 | 件数（2026-10-19 実測） | 変更の記録 |
|---|---|---|---|---|
| 1 | permissions.allow | ~/.claude/settings.json | 7 | 無し |
| 2 | autoMode.allow / soft_deny / environment | 同上 | 28 / 3 / 26 | ADR-1011 の台帳（`SM-` の文と PO の変更のみ） |
| 3 | hooks の登録 | 同上 | 39（`python3 scripts/dev/consent-audit.py --audit --permissions` の初回の写し） | 無し |
| 4 | リポジトリの .claude/settings.json の allow | ~/salesanchor/.claude/settings.json（git 追跡） | 27 | git の履歴のみ |
| 5 | リポジトリの .claude/settings.local.json の allow | 同じ場所の settings.local.json（追跡外、.gitignore の `.claude/*`） | 45 | 無し |
| 6 | 危険語リスト danger_ops | ~/.claude/agent-tokens.json | 17 | 無し（古い写しが3本、最後は 9/1） |
| 7 | フック本体 | ~/.claude/scripts/ | - | 反映スクリプトの控え（.backup）のみ |
| 8 | 許可券 | `scripts/permit-danger.sh` が ~/.claude/permits/ に作る（30分・1回） | 0（10/19 の写し） | 消費（danger_permit_consumed ほか）のみ。**発行の記録は無い** |

## 2. 今の週次点検が見ている範囲

- 【事実】`scripts/dev/consent-audit.py:319-343`（collect_permissions）は ~/.claude/settings.json と ~/.claude/settings.local.json の permissions.allow・hooks と、~/.claude/permits のファイル名だけを写す。allow の各文は `sha8(json.dumps(a, sort_keys=True, ensure_ascii=False))`（:329）、hooks は `event|matcher|sha8(...)`（:336）、permits はファイル名の sha8。
- 【事実】`scripts/dev/consent-audit.py:378-383` は `--permissions` を付けて走らせるたびに写し（permission-snapshot.json）を上書きする。週の途中で手で走らせると、週次の差分がそこで消える。
- 【事実】`scripts/dev/consent-audit.py:5` は「引数でパスは受けない」。main は `--audit` で常に rc 0 を返す（:428-430）。
- 【事実】写しに入っていない権限の項目: permissions.deny / ask / defaultMode、skipDangerousModePermissionPrompt などの確認省略の設定、autoMode の全体、リポジトリ側 settings の allow と hooks、危険語リスト、フック本体。
- 【事実】権限不足で止まった記録は ~/.claude/logs/permission-denied.jsonl にある。
- 【事実】`scripts/dev/consent-audit.py:355-385`（run_permissions）は前回の写しと比べて増減の件数とハッシュを出すが、**増減が正しいか（誰が・なぜ）を判定しない**。`:412` の ABNORMAL は同意の不一致と見張りの停止しか見ない。
- 【事実】~/.claude/settings.local.json は存在しない（2026-10-19 の初回出力で 0 件）。
- 【事実】ADR-1011 の「範囲外（AI が自分では変えない）」（`docs/adr/ADR-1011-permission-self-maintenance.md:29-39`）は、`SM-` 以外の allow・permissions・hooks・~/.claude/scripts を AI が変えないと定めている。今回の PO 決定はこのうち allow の部分を改める。
- 【事実】~/.salesanchor-tools（origin/main を切り離しで取り出した場所、2026-10-19 に HEAD d743ed9ab・変更 0）は、Mac の自動作業4つ（LaunchAgent の disk-janitor・claude-archive・mac-jobs-watch・colima-idle-stop）と agent-console の定期実行が使っている。disk-janitor と claude-archive は「変更が無ければ `git fetch` して origin/main を切り離しで取り出す」、ほかの2つは「変更が無く HEAD が origin/main の祖先か」を確かめてから読むだけ。変更（追跡外のファイルを含む）があると止まる。
- 【事実】自動作業の時刻（`plutil -extract StartCalendarInterval json` の結果、2026-10-19）: claude-archive は毎日 03:30、disk-janitor は毎日 04:00。便1（#4544）マージ直後の ~/.salesanchor-tools は HEAD d743ed9ab で、scripts/dev/perm-change.py はまだ無い（`ls` で確認、2026-10-19）。
- 【未確認】claude-archive が ~/.claude/projects の会話の記録を移すか・いつ移すか。移された場合、design §4-3 改7 の確かめは通らず B になる（止めすぎ側）。
- 【事実】定期実行「同意と権限の週次点検」（agent-console id bb581a6f、月曜 09:30）は 2026-10-19 に登録済み。基準値は /tmp/CC報告ファイル/consent-weekly/baseline-20261019.txt。

## 3. AI が権限を変えられる道

- 【事実】(a) `scripts/permit-danger.sh` を実行すると券を作れる。フックはこの実行を止めない。券の中身の created_by は常に "manual"（`scripts/permit-danger.sh:35`）。
- 【事実】(b) 設定ファイル・危険語リスト・フック本体を AI が書き換えることは、Claude Code 本体の自動判定（Self-Modification、ADR-1011 の Why）が止める。2026-10-13 に AI のフック書き換えが止まった実績がある（`docs/handoff/design-approval-ticket/self-maintenance-design.md`）。止まらなかった場合に後から気づく記録は無い。
- 【事実】(c) autoMode.allow の `SM-` の文は ADR-1011 の例外で、週次の保守だけが足し引きできる。
- 【事実】Claude Code の Bash には環境変数 `CLAUDECODE=1` が入っている（このセッションで `env | grep -c ^CLAUDECODE=` が 1）。PO が `!` で打つコマンドも同じプロセスの子なので、【推測】この目印だけでは AI と PO を区別できない。

## 4. PO の決定（2026-10-19）

- 委任の原文: 「日々の業務中にopusが必要と感じたら権限を追加しても良い権限委譲する、代わりに定期実行で追加した許可や削除した許可、意図や理由を確認していまの権限が適切かどうかを確認する仕組みを設けて管理しながらPDCAを回して最適なマネジメント能力を構築するために育てたい」
- 範囲: 選択肢「1.【おすすめ】本番データの削除、本番の元の枝（main）への直接の書き込み、合言葉や鍵などの秘密情報、見張りを弱める変更、の4つだけはあなたの確認を残し、ほかは私が権限を足し引きします。足し引きした理由は毎週の点検で確かめます。」に「1」。

## 5. 未確認

- 【未確認】Opus が ~/.claude/settings.json の permissions.allow を Edit したとき、自動判定が通すか。止まった場合は言い換えず、PO の `!` で反映する台本に切り替える（設計 §6）。
