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

## 修正便 R1 の R1-6 測定（2026-11-01 09:00 JST 予約）
- 対象期間: 入れ替え 2026-10-25 00:43 JST（2026-10-24T15:44Z）〜 2026-11-01 09:01 JST。R1 の実装結果表（R1-1〜R1-5）は PR #4711 側にある。
- 抜き出し: ~/.claude/logs/agent-events.jsonl（118,982 行）から hook "mac-vm-guard" の記録は全期間で 8 件。最後は 2026-10-22T06:45:17Z で、対象期間内は **0 件**（hook_blocked 0・hook_permit_consumed 0・hook_internal_error 0）。生出力: /tmp/CC報告ファイル/mac-vm-hook/r1-6/all-mac-vm-guard.jsonl・window-extract.txt
- 見張りが動いていたかの確認（0 件が「止まっていた」でないこと）:
  - settings.json の PreToolUse(Bash) に ~/.claude/scripts/mac-vm-guard.py が登録されたまま。本体の更新時刻 2026-10-25 00:43:53、sha256 先頭 91fc182d
  - 本体へ直接入力を流した試験（記録先は一時ファイルに切替）: profile 付き起動 → exit 2・hook_blocked と matched_part を記録／無指定の起動・echo・list → exit 0／壊れた JSON → exit 0・hook_internal_error を記録。生出力: r1-6/liveness-test.txt
  - 期間内の会話記録（1,317 ファイル）で起動系の命令を探すと、default への起動（無指定の起動）1 種だけが見つかった。§3 では止めない形で、拒否記録も無い＝正しく通した。生出力: r1-6/vm-commands-in-transcripts.txt
- 判定: §3 に当たらない拒否 0 件、hook_internal_error 0 件。

| # | 結果 | 根拠 |
|---|---|---|
| R1-6 | ○ | 期間内の拒否 0 件（誤検知 0）・内部エラー 0 件。見張りは登録済みで動作試験も期待どおり |

- 限界: 期間内に「止めるべき形」の命令が実際に来なかったため、本番の記録で拒否が正しく出ることは今回は観測していない（動作試験でのみ確認）。R2 候補（値を取る旗の誤検知・`&`/`nohup`/`$()` の見逃し）は R1 の記録どおり残っている。
