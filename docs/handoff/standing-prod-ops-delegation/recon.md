# recon：本番サーバー上の作業を Opus に委任する前の現在地（2026-11-02）

## 既存 ADR の検索
- `git grep -n -E '無制限鍵|manual-only' origin/main -- docs/adr AGENTS.md`、`docs/adr/FEATURE-INDEX.md` で確認。
- 該当: docs/adr/ADR-1003-go-delegation-to-opus.md（GO の委任）、docs/adr/ADR-1034-opus-permission-delegation-ledger.md（権限の足し引きと記録帳）、docs/adr/ADR-1033-conversation-consent-ticket.md（会話の同意票）。

## 今の決まり（【事実】）
- `AGENTS.md:26`（変更前）: 無制限鍵での「変更を伴う作業（ファイル作成・コンテナ起動停止・設定変更・再起動・DB 書き込み）は作業ごとに PO の GO が必要」。
- `docs/handoff/go-record-transcription/opus-delegation.md:34`: 10/15 の委任の追加は「無制限鍵での本番の変更は含めない。含めるには ADR と CLAUDE.md の改訂が要るので、別の PR で扱う」。
- `docs/handoff/gas-viewer-fresh-fast/design.md:606`: 2026-10-17 PO「n」（閲覧者の操作の GO は委任しない）。この PR は Q12 を上書きしない（閲覧者のアカウントの操作は ADR-1003 追記の除外に入れた）。
- `scripts/dev/perm-change.py:42`: 自動の安全判定の許可の行（user-automode-allow）は道具では「外す」だけ。足すのは PO の `!` 実行。

## 実測（【事実】・根拠 ~/CC報告ファイル-keep/autonomy-inventory/20261102.md）
- 2026-10-26〜11-02 に自動の安全判定が止めた操作 約50件のうち、本番サーバー上の書き込み・停止は 7 件（Remote Shell Writes 6・Interfere With Workloads 1）。すべて PO の `!` 実行が要った。
- 同じ期間に許可の行を足した2件（shingo-ops 名義の Approve・クラウドの担当の起動）は、足した後の止まりが 0 件。
- 期限付きの同じ形の許可 FNT-1・FNX-1 は、2026-11-02 の週次点検で期限切れのため外した（~/CC報告ファイル-keep/consent-weekly/20261102-changes-analysis.md）。

## ログインの記録（【事実】2026-11-02 16:22 JST、読み取りだけの調査で実測）
- prod1・prod2 とも、ubuntu は adm の組に入っており、`/var/log/auth.log` を sudo なしで読める（`id -nG` の結果に adm）。
- 「Accepted publickey」の行に鍵の指紋が出る。無制限鍵の指紋（`ssh-keygen -lf` の値）での受け入れは、2026-11-01 以降で prod1 64回・prod2 5回。
- 記録は毎週入れ替わり、4週分残る（`/etc/logrotate.d/rsyslog` の `weekly`・`rotate 4`、`auth.log` から `auth.log.4.gz` まで）。
- このため、ログインの数と作業の記録の数は一致しない（読み取りだけの調査でも1回ずつ数えられる）。照合は時刻で並べて行う。

## 今の自動の安全判定の止める行（【事実】2026-11-02、~/.claude/settings.json を読み取り）
- autoMode.soft_deny は3行。そのうち1行（記録用の番号 a2585405）が `Bash(docker compose restart *) — container restarts on prod are forbidden without PO decision; ...` で、本番の容器の再起動を PO の決定なしには止める。
- 足す許可の行は「docker compose の再起動」を含むので、この止める行と重なる。どちらが勝つかは【未確認】。

## 【未確認】
- 7 件のそれぞれが、その時点で審査済みの作業手順に書かれていたか（会話記録を Bash で数えると見張りが止めるため未集計）。委任後は ADR-1003 追記の条件6の記録で毎回確かめる。

## 追補（2026-11-03）: 照合2を道具にする前の現在地

### 今ある道具（【事実】origin/main の scripts/dev/consent-audit.py）
- 会話記録の読み方は既にある: `paths()`（L38-48）、`parse_ts`（L51-60）、`read_jsonl`（L63-74）、`find_transcript`（L99-103）。
- PO の `!` 実行の見つけ方も既にある: `_po_bang_in_records`（L745-776）、`consent_po_bang_at`（L779-796）。ただし探す範囲はメインの会話の記録だけ（`projects/*/*.jsonl`）で、担当（サブエージェント）の記録（`projects/*/<会話>/subagents/*.jsonl`）は見ない。
- 入口は `main`（L1137-1157）の `--probe` / `--audit` / `--permissions` / `--commit-snapshot`。ログインを照らす入口は無い。
- 単体試験は scripts/dev/consent-unit-tests.py。CI では走らず、scripts/dev/permission-delegation-tests.py:1043 から呼ばれる。

### 会話記録の中の形（【事実】2026-11-02〜03 に手元の記録を読み取りで確認）
- 手前で走る Bash: assistant の `tool_use`（name Bash・`input.command`・`id`）→ user の `tool_result`（`tool_use_id` が同じ）。時刻は UTC。
- 裏で走る Bash（`run_in_background`、または途中で「moved to the background」）と Monitor: `tool_result` はすぐ返るが、実行はその後も続く。本当の終わりは、後の記録に出る `<tool-use-id>toolu_…</tool-use-id>` と `<status>completed</status>`（記録の種類は queue-operation・attachment・user のどれか）。終わりの記録が無いものもある。
- PO の `!` 実行: user の記録で、本文が `<bash-input>` で始まる。次の user の記録に `<bash-stdout>` が入る。
- 担当の記録は 1,524 ファイル。メインの記録の中でも `isSidechain` が付く行がある。会話記録は全部で 4.5GB。

### ログインの記録の形（【事実】）
- `/var/log/auth.log` の時刻は `2026-11-02T23:45:10.398968+09:00` の形（日本時間・マイクロ秒つき）。
- 手元の ssh の設定は ControlMaster を使っていない。ssh 1回 = ログイン1回。
- 無制限鍵の指紋は ssh-keygen の値で1つ（名前 shingo-macbook-primary）。

### 手で照らした結果（【事実】記録 ~/CC報告ファイル-keep/consent-weekly/20261102-prod-login-check.md）
- 委任開始（2026-11-02 18:06）以降: prod1 は自分の照合を除いて 16 回、prod2 は 1 回（自分の照合）。16 回のうち 14 回はメインの会話の Bash の文面に無制限鍵があり、2 回は PO の `!` 実行（22:27:12〜22:27:22）。説明できないもの 0 件。
- 委任前の1週間（1,226 回）を時刻の重なりだけで分けると、prod1 は 鍵の文面あり 268・`!` 162・関係の無い実行だけ重なる 595・担当の関係の無い実行 53・担当の鍵の文面あり 1・重なり無し 116、prod2 は 鍵の文面あり 13・関係の無い実行だけ 18。担当の鍵の文面ありの1件は 10-27 01時台で、委任前。
- 重なり無し 116 件の原因: 裏で走る Bash の繰り返し（例: `until ssh -i ~/.ssh/manual-only/... ` が 09:29:16 から 10:12:03 まで続いた）。`tool_result` はすぐ返るので、終わりを `tool_result` で取ると窓から外れる。
- 関係の無い実行だけ重なる 595 件: 中で無制限鍵を使う台本（scripts/accuracy/llm_compare/vps_run_gemini.sh など、repo に「manual-only」を含む台本が7本）と、同じ時刻に別の会話で走った無関係の実行が混ざっている。時刻の重なりだけでは見分けられない。
- 試作は全部の記録を JSON として読むと 8〜15 分かかった。行の生の文字で `toolu_` か `<bash-input>` / `<bash-stdout>` を含む行だけ読むように絞った試作4は、1週間分（入室 1,226 回・呼び出し 51,626 件）を 154 秒で照らした。

### 試作4・5の結果（【事実】2026-11-03、手元で読み取りだけ）
- 裏で走る実行の終わりを `<tool-use-id>` の知らせで取ると、重なり無しは 116 件 → 0 件になった。終わりの知らせが無い呼び出しは 279 件（その会話の最後の記録の時刻を終わりとした）。
- 試作4の分類（prod1）: メインの会話の鍵の文面あり 948・`!` 95・中で鍵を使う台本 67・関係の無い実行だけ重なる 84・担当の鍵の文面あり 1。prod2: メインの会話の鍵の文面あり 31。
- 担当の鍵の文面ありの1件（10-27 01:29:15）は、説明の文章（README）を書く heredoc の中に「manual-only」の文字があっただけで、鍵は使っていない。文字があるだけでは数えてはいけない。
- 手元の `~/.ssh/config` で、別名 `prod1`・`prod2` の鍵が無制限鍵（`IdentityFile ~/.ssh/manual-only/id_ed25519`）になっている。IP で書いたとき（`49.212.137.46` など）は制限付きの鍵（`~/.ssh/salesanchor-claude`）。このため `ssh prod1 "…"` は文面に鍵の名前が無くても無制限鍵で入る。関係の無い実行だけ重なる 84 件の多くは、この `ssh prod1` だった。
- 委任前の 2026-10-30 12:19〜12:20 に、担当（サブエージェント）の記録で `ssh -o BatchMode=yes prod1 '…'` が走り、その中に `docker compose up -d --force-re…`（容器の作り直し）があった。担当が無制限鍵で本番に書き込んだ跡で、委任の前のこと。道具はこれを異常として出せなければならない。
- 台本の中身で判定できないもの: /tmp/CC報告ファイル の下の apply.sh や会話の作業場所（scratchpad）の台本は、もう消えていて中身を読めないものがある（10-29 09:45・10:02、10-30 20:44 など）。
- どの会話の記録とも合わない入室が 22 回あった（10-30 03:06 台 4・10-31 14:35 台 3・10-31 15:10 台 3・11-02 08:10〜08:13 台 12）。接続元はすべて Mac の IP（49.128.148.145）。
- 無制限鍵の入室の接続元は、記録の4週分すべて Mac の IP だけ（prod1 18,696 回・prod2 593 回）。
- Mac の定期実行（~/Library/LaunchAgents）で本番に入るのは、毎日 06:30 の confidential-quote-guard-fetch だけ。22 回の時刻とは合わない。
- 別の AI の道具（Codex）の記録で 10-26 以降に本番の文字があるのは 10-27 の1件だけで、22 回の時刻とは合わない。

### 【未確認】（追補）
- 担当の記録の中の `!` 実行の形（担当は `!` を使えないはずだが、記録で確かめていない）。
- 会話記録が消される時期（Claude Code の設定 cleanupPeriodDays の値と、4週分の auth.log より短いかどうか）。Bash で確かめようとして見張りに止められた（言い換えはしていない）。
- どの会話の記録とも合わない 22 回の出どころ（PO 本人の端末・agent-console の中の処理・消えた会話の記録のどれか）。手元の打ち込み履歴には時刻の付いた行が無く、確かめられなかった。
