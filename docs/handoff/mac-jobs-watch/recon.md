# recon: Mac の自動お手入れの見張り（mac-jobs-watch）

この文書は何か(専門用語なしの1行): 見張り役を作る前に、今の Mac と既存の仕組みがどうなっているかを実物で確かめた記録。

- 調査日: 2026-10-15（基準: origin/main e1cdbc468）
- 生出力: /tmp/CC報告ファイル/ac-heavy/notify-recon/R1.txt〜R7.txt、/tmp/CC報告ファイル/ac-heavy/governance/G1.txt〜G9.txt・SUMMARY.md
- 調査役: Sonnet（読み取りのみ）。本書は Opus が生出力を読んで書いた。

## 0. 既存 ADR の検索

`git grep -n -i "launchd\|LaunchAgents\|disk-janitor\|colima" origin/main -- docs/ai-ops docs/handoff/ai-ops* docs/adr`（R7.txt）と、`git grep -n -i -E "通知|discord|チャンネル|alert|監視" origin/main -- docs/adr docs/ops`（R4.txt）の結果:

| ADR | 該当 | 本テーマとの関係 |
|---|---|---|
| docs/adr/ADR-1009-discord-ops-intake.md:36 | 「停止は番人（launchd）が別の webhook で PO に通知し」 | Mac 上で launchd から Discord に知らせる前例。通知先ファイルを共用する（§2） |
| docs/adr/ADR-029-self-hosted-runner-fleet.md:232 | 「svc.sh (LaunchAgent) を採用。macOS 個人機（ログイン時起動）に適合」 | LaunchAgent はログイン時に動くという既存判断 |
| docs/adr/ADR-035-external-state-verification.md:160 | `scripts/notify/discord-owner-ping.sh`（L5） | GitHub Actions の秘密情報 `DISCORD_WEBHOOK_OWNER_PING` 前提。Mac には無い（§2） |
| docs/adr/ADR-1015（開発フロー） | 区分 A/B の判定 | 本 PR は scripts/・ops/ を含むので区分 A |

ai-ops（docs/handoff/ai-ops-247/）で Mac の launchd 常駐を見張る計画は無い（R7.txt。ai-ops-247/recon.md:122 は「番人は Mac の launchd で動く（Mac が眠ると止まる）」の記述だけ）。

## 1. 見張る対象の今

| 事実 | 根拠 |
|---|---|
| Docker 自動停止は 15 分ごと（StartInterval 900）、ログ1行の形は `ISO時刻 result=<…> reason=<a|b|c|d|-> elapsed= detail=` | ops/launchd/jp.salesanchor.colima-idle-stop.plist（StartInterval 900）、scripts/colima-idle-stop.sh:41 |
| Docker 自動停止が失敗で終わるのは「停止に失敗（stop-fail）」のときだけ（終了コード 1） | scripts/colima-idle-stop.sh:205-206 |
| 判定に失敗すると reason=d を書く（止めない） | scripts/colima-idle-stop.sh 冒頭コメント:6、docs/handoff/colima-idle-stop/design.md |
| 毎回ログに1行書く（停止中でも `result=stopped`） | R5.txt「colima-idle-stop.log (all)」12:17:32 の行 |
| 毎日の自動片付けは毎日 04:00（StartCalendarInterval Hour 4 Minute 0） | ops/launchd/jp.salesanchor.disk-janitor.plist:49-54 |
| 自動片付けのログは「===== disk-janitor 開始 YYYY-MM-DD HH:MM:SS …」「===== disk-janitor 終了 …」 | scripts/disk-janitor.sh:368、:398 |
| 自動片付けの本体は常に 0 で終わる。道具のコピーの更新に失敗したときだけ plist の `|| { echo … >&2; exit 1; }` が ~/Library/Logs/disk-janitor.err に書く | scripts/disk-janitor.sh:399、ops/launchd/jp.salesanchor.disk-janitor.plist:34、:66 |
| disk-janitor.err は 2026-10-13 05:45:43 に 87 バイト書かれた（1回） | R5.txt「logs mtime」 |
| 自動片付けは手動でも動く（10/14 15:05・21:21 の開始行） | R5.txt「disk-janitor start lines」 |
| どちらも、止まったり失敗したりしても人に知らせる仕組みが無い | /tmp/CC報告ファイル/ac-heavy/governance/G6.txt |

## 2. 通知の手段

| 事実 | 根拠 |
|---|---|
| Mac から Discord に送る既存の仕組みは「受付の番人」1つ。通知先 URL はファイル `~/.config/sa-ops-intake/watchdog-webhook`（権限 600、122 バイト、2026-10-13 05:17） | R3.txt、tools/claude-channels/README.md:30、tools/claude-channels/bin/sa-ops-intake-watchdog:10-11 |
| 番人は URL を引数に出さず、curl の設定を標準入力で渡す | tools/claude-channels/bin/sa-ops-intake-watchdog:70-72 |
| 番人は同じ異常を 1 時間に 1 回まで知らせる | tools/claude-channels/bin/sa-ops-intake-watchdog:13、:57-64 |
| キーチェーンにも、シェルの設定にも Discord の通知先は無い | R3.txt「keychain existence」「env var names」 |
| `scripts/notify/discord-owner-ping.sh` が使う `DISCORD_WEBHOOK_OWNER_PING` は GitHub Actions の秘密情報で、Mac には無い | R4.txt（.github/workflows/*.yml の env）、R3.txt |
| **受付の番人 jp.salesanchor.ops-intake-watchdog は launchd に読み込まれていない**（`Could not find service`）。最後のログは 2026-10-13 09:17:37 | R2.txt、R5.txt「logs mtime」 |
| 朝の停止要約 jp.salesanchor.stop-log-digest-daily も launchd に読み込まれていない | 2026-10-15 `launchctl print` 実測（Bad request / Could not find service） |

## 3. 再起動と眠り

| 事実 | 根拠 |
|---|---|
| 最後の起動は 2026-10-09 18:02:31（kern.boottime sec=1791536551）。設置（10/15）後の再起動は 0 回 | R5.txt `sysctl kern.boottime`、`last reboot` |
| ~/Library/LaunchAgents は「Per-user agents provided by the user」 | R5.txt man launchd:54 |
| Apple 公式「Creating Launchd Jobs」: ユーザーがログインすると per-user launchd が始まり、~/Library/LaunchAgents を読み込む | 前回調査（summary 記載の BPSystemStartup の引用） |
| StartInterval は眠っている間の回は飛ばされる | man launchd.plist:350（前回調査） |
| StartCalendarInterval は眠っている間の回を、起きたときにまとめて1回動かす | man launchd.plist:363-366（前回調査） |
| `sysctl kern.waketime` は 0 を返し、起きた時刻は取れない | 前回調査 |

## 4. 似た作りの手本

- scripts/colima-idle-stop.sh:16-28 設定を1か所（`CIS_` 環境変数で上書き可）、:33-42 ログ（1MB 超で .1 へ1世代）、:48-70 mkdir ロック。
- scripts/tests/test-colima-idle-stop.sh:1-12 一時フォルダと偽コマンドだけで試す。
- ops/launchd/jp.salesanchor.colima-idle-stop.plist: 道具のコピー（~/.salesanchor-tools）を読むだけで動かす1行（自動片付け実行中は見送り）。
- 手順書は docs/ops/runner-commands.md §9 の小節（:202 起動時 reaper、:220 disk-janitor、:268 colima-idle-stop）。

## 5. 未確認

- 再起動後に LaunchAgent が自動で動くことの、この Mac での実測（設置後に再起動していないため）。→ design.md K6 で次の再起動時に自動で証拠を取る。
