# results: mac-vm-hook（H1〜H5 の観測）

この文書は何か(専門用語なしの1行): Mac で仮想マシンを作る AI の命令を止める見張りを実装した結果の観測値。

生出力: /tmp/CC報告ファイル/mac-vm-hook/（Mac 内。unittest.txt・h1_before.txt・h1_after.txt・h1_diff.txt・h1_log.txt・h3_list.txt・h3_status.txt・json_check.txt）

## 観測値
| # | 観測 | 生出力 |
|---|---|---|
| H1 | 実機の Bash で `colima start --profile k1probe` はフックに止められ、案内文に `sandbox-test` を含む。前後の `colima list` は同一（diff 差分なし） | h1_before.txt / h1_after.txt / h1_diff.txt / h1_log.txt |
| H2 | 試験で `limactl start/create/clone` が exit 2 | unittest.txt |
| H3 | 試験で default・stop・list・status・delete が exit 0。実機で `colima list`・`colima status` が通った（start/stop は実行せず） | unittest.txt / h3_list.txt / h3_status.txt |
| H4 | echo・grep・git commit -m・ヒアドキュメント本文で拒否 0 件 | unittest.txt |
| H5 | 一時 HOME で、有効な券は1回通って券が消え2回目は exit 2。期限切れ・op 違い・created_by が manual 以外は exit 2。券ファイルは本番の券置き場に作っていない | unittest.txt |
| 内部エラー | 壊れた JSON 等の入力は exit 0 | unittest.txt |
| 試験 | `/usr/local/bin/python3 ~/.claude/scripts/tests/test_mac_vm_guard.py`: 8 テスト（サブケース含む）OK | unittest.txt |

H6（7日観測）は未実施。AI が券ファイルを作る操作の既存見張りでの拒否の試験は未実施（実装中に券置き場を ls した命令が既存の permits-guard に止められたことを1回観測）。

## hooks 仕様の出典
Context7 は月間上限超過（"Monthly quota exceeded"）で使えなかった。公式資料での確認は未実施で、仕様の出典は未確認。代わりの根拠は実機の観測: PreToolUse フックの exit 2 と標準エラー出力でコマンドが実行されず、メッセージが AI に返った（h1_log.txt）。
