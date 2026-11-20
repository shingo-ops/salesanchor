# results: mac-vm-hook（H1〜H5 の観測）

この文書は何か(専門用語なしの1行): Mac で仮想マシンを作る AI の命令を止める見張りを実装した結果の観測値。

生出力: /tmp/CC報告ファイル/mac-vm-hook/（Mac 内。unittest.txt・h1_before.txt・h1_after.txt・h1_diff.txt・h1_log.txt・h3_list.txt・h3_status.txt・json_check.txt）

## 観測値
| # | 観測 | 生出力 |
|---|---|---|
| H1 | 実機の Bash で `colima start --profile k1probe` はフックに止められ、案内文に `sandbox-test` を含む。前後の `colima list` は同一（diff 差分なし） | h1_before.txt / h1_after.txt / h1_diff.txt / h1_log.txt |（vm-guard-allow: 見張りの説明文。実行する命令ではない）
| H2 | 試験で `limactl start/create/clone` が exit 2 | unittest.txt |（vm-guard-allow: 見張りの説明文。実行する命令ではない）
| H3 | 試験で default・stop・list・status・delete が exit 0。実機で `colima list`・`colima status` が通った（start/stop は実行せず） | unittest.txt / h3_list.txt / h3_status.txt |
| H4 | echo・grep・git commit -m・ヒアドキュメント本文で拒否 0 件 | unittest.txt |
| H5 | 一時 HOME で、有効な券は1回通って券が消え2回目は exit 2。期限切れ・op 違い・created_by が manual 以外は exit 2。券ファイルは本番の券置き場に作っていない | unittest.txt |
| 内部エラー | 壊れた JSON 等の入力は exit 0 | unittest.txt |
| 試験 | `/usr/local/bin/python3 ~/.claude/scripts/tests/test_mac_vm_guard.py`: 8 テスト（サブケース含む）OK | unittest.txt |

H5 実地（Opus 2026-10-17 00:43 JST）: PO が `! bash scripts/permit-danger.sh "mac vm"` で券を発行 → `colima start -p h5probe --help` 1回目は通り（rc=0、使い方の表示のみ）、ログ `hook_permit_consumed`。2回目は `hook_blocked` で拒否。前後の `colima list` は default・sa-private-ci のみ（h5_first.txt / h5_list_after.txt / h5_log.txt）。→ H1〜H5 ○。（vm-guard-allow: 見張りの説明文。実行する命令ではない）

H6（7日観測）は agent-console 予約（2026-10-24 09:00）で確認する。AI が券ファイルを作る操作の既存見張りでの拒否の試験は未実施（実装中に券置き場を ls した命令が既存の permits-guard に止められたことを1回観測）。

## hooks 仕様の出典
Context7 は月間上限超過（"Monthly quota exceeded"）で使えなかった。代替として Opus が公式資料を直接確認した（2026-10-17、https://code.claude.com/docs/en/hooks）:
- 「Exit with code 2 to block the action. … a `PreToolUse` hook blocks the tool call」「The message that comes with the block is your hook's stderr.」
- 「Hooks from settings files … also run inside subagents. When a subagent calls a tool, tool events such as `PreToolUse` … fire the same configured hooks」→ Sonnet 等の担当にも効く。
- exit 0 以外・2 以外は非ブロッキング（本見張りの fail-open は exit 0 で意図どおり）。

既知の限界（Opus コード審査）: `$( … )`・バッククォート内、`nohup`/`exec`/`command` 前置、別行の `export COLIMA_PROFILE=x` は判定しない。AI の通常の書き方では起きにくく、H6 の観測と K5（10/31 `colima list`）で取りこぼしを検出する。

補足の根拠として実機も観測した: PreToolUse フックの exit 2 と標準エラー出力でコマンドが実行されず、メッセージが AI に返った（h1_log.txt）。

## H6 7日観測（2026-10-17〜2026-10-24 09:10 JST）— ×

- 観測源: `~/.claude/logs/agent-events.jsonl` の `hook: "mac-vm-guard"` 行（ローテーション無し）。生データ: `/tmp/CC報告ファイル/mac-vm-hook/h6/events-raw.jsonl`、一覧: `denials.txt`
- 件数: 拒否 `hook_blocked` 5件 / 券消費 `hook_permit_consumed` 0件 / 内部エラー 計測不能（後述）
- 判定基準: §3 の「止める形」に当たらない拒否が0件なら○

| # | 日時(JST) | 止まった部分 | §3 判定 |
|---|---|---|---|
| 1 | 10/17 20:04 | `colima start 2>&1` | 当たらない（profile 無指定＝default）→ 誤検知 |
| 2 | 10/20 21:54 | `(colima start --cpu 2 --memory 4 --disk 20 > …` | 記録が120文字で切れ全文不明。見えている範囲に profile 指定なし。再現試験で同形が `>` により止まる → 誤検知の疑い |
| 3 | 10/22 15:22 | `colima start > /tmp/…/colima_start.txt 2>&1` | 当たらない → 誤検知 |
| 4 | 10/22 15:22 | 3と同じ（再実行） | 当たらない → 誤検知 |
| 5 | 10/22 15:45 | `colima start 2>&1` | 当たらない → 誤検知 |

- 結論: 誤検知 4件確定（＋1件疑い）。H6 は ×。
- 原因（コード読み取り＋再現）: `~/.claude/scripts/mac-vm-guard.py:81-103` の `colima_profile()` が `-` で始まらない最初の語を位置引数の profile とみなすため、`2>&1`・`>`・リダイレクト先が profile 名扱いになり default 以外と判定される。再現: `/tmp/CC報告ファイル/mac-vm-hook/h6/fp-repro.txt`（`colima start 2>&1 | tail -5` rc=2、`colima start` 単独 rc=0、`colima start -p foo` rc=2）
- 設計との食い違い2点: (a) 上記リダイレクトの扱い（§3 は無指定＝default） (b) §6「内部エラーも1行記録」に対し実装 `mac-vm-guard.py:180-181` は記録せず return 0 のため、内部エラー件数を観測できない。`cmd_head` が120文字切り詰め（`:142`）で全文検証もできない。
- 対応: 見張りは直していない。修正方針は PO 判断待ち。

## 修正便 R1 実装結果（2026-10-25）
- PO 実装承認: 2026-10-25 チャット「1」（design.md §11 の設計どおり直す）。実装は Sonnet、審査は Opus（別起動の reviewer）。
- 入れ替え: 2026-10-25 00:43 JST。対象は ~/.claude/scripts/mac-vm-guard.py と ~/.claude/scripts/tests/test_mac_vm_guard.py の2つだけ（repo・settings.json は不変）。退避は同じ場所の `.bak-r1`。差分: /tmp/CC報告ファイル/mac-vm-hook/h6/r1/guard.diff（130行）・test.diff（72行）
- 試験: 実装前 12件中 10件 FAIL（R1-1 の8形・R1-4・R1-5）→ 実装後 12件 OK（既存8件を含む）。生出力: r1/test-before.txt・r1/test-after.txt

| # | 結果 | 根拠 |
|---|---|---|
| R1-1 | ○ | 8形すべて exit 0（test-after.txt、fp-after.txt） |
| R1-2 | ○ | 5形すべて exit 2 |
| R1-3 | ○ | 既存8件を含む12件 OK |
| R1-4 | ○ | 壊れた JSON で exit 0、hook_internal_error 1行 |
| R1-5 | ○ | matched_part = `colima start -p foo 2>&1` |
| R1-6 | 未測定 | agent-console 予約（2026-11-01 09:00 JST）で測る |

- 審査（Opus reviewer）: APPROVE。修正前後に51命令＋壊れた入力7種を流して比べ、止めるべき命令の新たな見逃しは0件。設計 §11-3 との照合は Opus が差分で実施。
- 既知の残り（修正前からあり、R1 では変えていない。R2 候補）:
  - 誤検知: `colima start --port-forwarder grpc`・`colima start --disk-image /x.img` が止まる（値を取る旗の一覧に無いため）
  - 見逃し: 単独の `&` で続けた命令・`nohup`・`$(...)` の中は見ない（§3 の表どおり）
  - 段階1 CI 側 scripts/ci/no-mac-vm-guard.sh の同じ読み違い（§11-4）
