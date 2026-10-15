# 設計用 事実集め（読み取りのみ・2026-10-15）
生出力: 同フォルダ 01〜12 の txt。HDD・ClaudeArchive には触っていない。df 空き 25Gi。

## 1. disk-janitor
事実
- 全文 01-janitor-sh.txt。規則 R1(.npm-cache) R2(14日未更新worktreeのnode_modules) R3(agent-console旧版) R4(他リポジトリworktree、reaper呼出)（scripts/disk-janitor.sh:4-8）。
- 既定 dry-run、`--execute` で実削除（:11-12, :349-355）。DJ_ 環境変数で設定上書き（:21-47）。
- 削除ガード dj_guard 1つ（:74-104）、削除本体は dj_act 内（:140-162）。lsof 使用中判定（:106-119）。
- ロック: mkdir /tmp/disk-janitor.lock.d + trap（:33, :360-365）。
- ログ: DJ_LOG_FILE=~/Library/Logs/disk-janitor.log、1MB超で .1 に1世代（:336-345）。plist の StandardOut も同log、StandardError は disk-janitor.err。
- plist ~/Library/LaunchAgents/jp.salesanchor.disk-janitor.plist: 毎日04:00（StartCalendarInterval）、RunAtLoad=false。/bin/bash -lc で ~/.salesanchor-tools を fetch → きれいなら origin/main に detach checkout → `bash scripts/disk-janitor.sh --execute`、失敗なら exit 1。秘密なし（PATH と DJ_LOG_FILE のみ）。
- ~/.salesanchor-tools: salesanchor の worktree（.git は /Users/tanizawashingo/salesanchor/.git/worktrees/-salesanchor-tools を指す）、`HEAD (no branch)` detached、0c7852fd9 (#4280)。ローカルの origin/main に対し 0 ahead / 29 behind（fetch していないローカル参照での値、02-git.txt）。
- salesanchor 内のパス: scripts/disk-janitor.sh、scripts/tests/test-disk-janitor.sh、ops/launchd/jp.salesanchor.disk-janitor.plist、docs/handoff/disk-janitor/{design.md,recon.md,evidence/*}。
- 関連 memory: project_disk_janitor.md（03-memory-janitor.txt）。PR #4183, #4192。ops/launchd は DANGEROUS_PATTERNS（危険PR・PO GO要）。ロック設計 design.md:43。
- janitor の根は worktrees / agent-console-wt / salesanchor / agent-console / versions のみ。~/.claude や /tmp は対象外 → 新規規則の追加が必要。
未確認
- design.md 全文は未精読（grep のみ）。

## 2. 他の LaunchAgent
事実
- com.crm-app.janitor（週1: StartInterval 604800）が呼ぶ /Users/tanizawashingo/crm-app-canonical-20260824/scripts/janitor.sh は存在しない（ls: No such file）。`launchctl list` で状態 `-  0`。同名 janitor.sh は crm-app-canonical-20260830/scripts/janitor.sh にある（06）。内容: 7日以上経ち develop にマージ済みで dirty=0 の worktree を git worktree remove、そうでなければ node_modules/.npm-cache/test-results を ~/.Trash へ mv、最後に npm cache clean --force（:12-31）。ログ ~/janitor.log。
- jp.salesanchor.reaper-onlogin: ログイン時と毎日03:00、`bash scripts/reaper-worktree.sh --execute`、WorkingDirectory=/Users/tanizawashingo/salesanchor（本体）。ログ ~/Library/Logs/reaper-onlogin.log（最終 10/15 03:00、「削除 1 件」「未保存あり43件は保護」）。
未確認
- com.crm-app.janitor の実行履歴（実際に動いているか）。

## 3. 直近ログ（~/Library/Logs/disk-janitor.log、07-log.txt）
事実
- 10/14 15:05:57〜15:06:56 execute 合計 8件 / 826.3MB
- 10/14 21:21:05〜21:24:01 合計 12件 / 1.4GB（R3 5件1.4GB、R4 7件）
- 10/15 04:00:03〜04:00:51 合計 7件 / 835.5MB（R1 0、R2 0・飛ばし35、R3 3件835.5MB、R4 4件）
- .err は10/13 05:45付の1行のまま（汚れ試験の文言）。

## 4. agent-console dataDir 容量
BLOCKED: ac-routine-guard フック（ac-routine-guard.mjs）が「サブエージェントからは使えません」で止めた（Application Support/agent-console への cd+du）。言い換え再実行せず。boards/uploads/routine-audit/diff-comments/activity の件数・大きさは未計測。Opus 本体から実測が必要。

## 5. agent-console の削除処理（git fetch 後 origin/main を grep、09-ac-grep.txt、10-prune-activity.txt）
事実
- activity: server/activity.ts:524 pruneOldFiles が events-YYYYMMDD.jsonl を unlink。keepDays 既定7（server/config.ts:48 DEFAULT_ACTIVITY_KEEP_DAYS=7、activity.ts:246）。起動時と1時間ごと（server/activity-start.ts:81）。→ activity は7日で消える。
- uploads: server/uploads.ts の prune（画像）と pruneFiles（:94〜）が maxKeep 件超を mtime 古い順に unlink/rmdir。DEFAULT_UPLOAD_MAX_KEEP=100（server/config.ts:53、index.ts:98）。
- diff-comments: server/diff-comments.ts:130 prune は「存在しなくなった場所のコメント」を除く処理で、日数削除ではない。
- boards / routine-audit.jsonl: 削除処理は見つからず（検索語 unlink|rmSync|retention|prune|rimraf|rmdir を boards/audit/comment/activity/upload と組合せ）。
- なお server/picks.ts:258 にも maxKeep 超を removeFiles する処理があるが、対象（picks）が今回の対象か未確認。
未確認
- 検索の網羅性（boards の削除が別名の関数にある可能性）。
含意: activity は7日、uploads は100件で消えるため、HDD 写しは毎日が必要。

## 6. plans / cleanupPeriodDays
事実
- ~/.claude/plans: 40件。最古は squishy-yawning-hedgehog.md.backup-20260211-234538（2026-02-11、14559B）。通常 .md の最古は 9/17 00:05（dynamic-finding-cloud-agent-…、4031B）。
- ~/.claude/settings.json に cleanupPeriodDays は無い（grep 0件）。settings.local.json は無い。→ 既定（分類書では30日）。

## 7. rsync と keychain
事実
- /usr/bin/rsync のみ。`rsync --version`: `openrsync: protocol version 29` / `rsync version 2.6.9 compatible`。Homebrew 版なし（/opt/homebrew/bin, /usr/local/bin に無し）。macOS 26.3.1。
- security find-generic-password / hdiutil / keychain を使う LaunchAgent・スクリプトは、このMacの ~/Library/LaunchAgents と ~/.salesanchor-tools/scripts に無い（11-security-grep.txt の1件は local.agent-console.server.plist の AGENT_CONSOLE_AUTH 環境変数キー。キーチェーン呼出ではない。値は出していない）。
未確認
- launchd 下で login keychain が security で読めるか（試していない）。画面ロック中・ログアウト中の挙動も未確認。openrsync(2.6.9互換) が --info=progress2 等の新オプションを持つか未確認。

## 8. HDD 外れ検出の既存例
事実: ~/.salesanchor-tools/scripts と ~/Library/LaunchAgents に /Volumes を確認する箇所は無い（12-volumes.txt は disk-janitor.sh:34 の /System/Volumes/Data のみ）。既存例なし。
参考: 現在 /Volumes に ClaudeArchive, HIGHLIFEJPN HDD, 名称未設定 がある（ls のみ）。

## 9. 増加量
事実
- ~/.claude/projects: 全体 3.1G。直近7日に更新されたファイル 3528件 / 1419.9MB。直近24h 350.4MB。
- /tmp/CC報告ファイル: 全体 1.5G。直近7日の *.md 3354件 / 28.6MB。全種別 直近7日 1299.1MB。
- 「更新」は mtime 基準で、追記された jsonl を丸ごと数える。日次の純増より大きく見える【推測】。rsync の差分転送なら実転送量は変更分。
