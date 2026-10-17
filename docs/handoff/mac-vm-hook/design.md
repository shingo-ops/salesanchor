# design: AI が Mac で仮想マシンを作る命令を実行前に止める（mac-vm-hook）

この文書は何か(専門用語なしの1行): Claude が Mac で試験用の仮想マシンを作ろうとしたら、命令が動く前に止めて GitHub の試験場へ案内する見張りの設計。

親テーマ: [docs/specs/vm-test-on-gha/README.md](../../specs/vm-test-on-gha/README.md)（段階2）。段階1の設計: [../vm-test-on-gha/design.md](../vm-test-on-gha/design.md)
状態: 設計案作成済み・Opus 自己審査済み（§9）。KGI H1〜H6 は PO 承認済み（2026-10-17 チャット「y」）。実装は Sonnet に委任。

## 0. PO の願い（2026-10-17 チャット原文）
「hookで強制的に使えないようにしたい、出来る？検査をする場所はhookでgit hubと教えてローカルで通そうとしても技術的に防止させる」→ 設計着手に「y」。

## 1. KGI（○×で判定）
| # | 合格条件 | 測り方 | 合格ライン |
|---|---|---|---|
| H1 | AI が `colima start --profile x` を実行しようとすると止まる | Claude Code の Bash で実行させる | 実行前に拒否。案内文に `sandbox-test` が出る。前後の `colima list` が同じ |（vm-guard-allow: 見張りの説明文。実行する命令ではない）
| H2 | `limactl start foo`／`limactl create foo` も止まる | 同上（試験スクリプト） | 拒否（exit 2） |（vm-guard-allow: 見張りの説明文。実行する命令ではない）
| H3 | 開発用 DB の操作は今までどおり | `colima start`（profile 指定なし・`default`）／`colima stop`／`colima list`／`colima status` | 1件も止まらない。`colima start` 後に `default` が Running |
| H4 | 文章の中の文字列では止まらない | `echo`・`grep`・ヒアドキュメント本文・`git commit -m` に `colima start --profile x` を含める | 試験で 0 件拒否 |（vm-guard-allow: 見張りの説明文。実行する命令ではない）
| H5 | 例外は PO の許可券だけで、AI は自分で通せない | PO が `! bash scripts/permit-danger.sh "mac vm"` → 1回だけ通る。2回目は止まる。AI が券ファイルを作る操作は既存見張りで止まる | 3点とも期待どおり |
| H6 | 誤って止めることが無い | 導入後 7 日間、`~/.claude/logs/agent-events.jsonl` の `mac-vm-guard` 拒否記録を読む | 仮想マシン作成以外での拒否 0 件 |

## 2. 対象と対象外
- 対象（すべてリポジトリ外。py312-guard と同じ置き方）:
  - 新規 ~/.claude/scripts/mac-vm-guard.py（PreToolUse Bash フック、標準ライブラリのみ）
  - 新規 ~/.claude/scripts/tests/test_mac_vm_guard.py（H1〜H5 の試験。券は一時 HOME で作る）
  - 変更 ~/.claude/settings.json の PreToolUse Bash に1件追加（python-version-guard の直後）
- 対象（リポジトリ内・文書のみ）: docs/ops/runner-commands.md §10 に「AI は見張りで止まる・例外は許可券 "mac vm"」を2行追記。docs/specs/vm-test-on-gha/README.md に段階2の行。本 design.md・card.md・results.md。
- 対象外: 人が自分のターミナルで直接打つ命令（フックは AI の命令にだけ効く）／ Codex（Claude Code のフックは効かない。Codex 運用は現在カード実行のみで本件の観測事例なし）／ `default` の CPU・メモリ設定の変更／ 既存の `sa-private-ci` の起動（`--profile sa-private-ci` も止める対象。必要なら許可券）。

## 3. 止める形（判定の正本はこの表）
命令を引用符の外の `; && || |` 改行で分け、各部分の先頭語（`sudo`・`env`・`VAR=` は飛ばす。`/opt/homebrew/bin/colima` のような絶対パスは末尾名で見る）で判定する。
| 先頭語 | 次の語 | 判定 |
|---|---|---|
| `colima` | `start`・`create`・`restart` | profile（`-p`/`--profile`/`--profile=`/位置引数。値を取る旗は段階1の no-mac-vm-guard.sh と同じ一覧で飛ばす）が `default` 以外なら止める。無指定は `default`。環境変数 `COLIMA_PROFILE=` が付き `default` 以外でも止める |
| `limactl` | `start`・`create`・`clone` | 止める |
| `bash`/`sh`/`zsh` | `-c` | 引数の文字列を同じ規則で再判定（1段のみ） |
| その他（`echo`・`grep`・`git`・`cat` 等） | — | 止めない |
ヒアドキュメントの本文は判定前に取り除く（py312-guard の `strip_heredoc_bodies` と同じ）。

## 4. 止めたときの案内文（標準エラー、exit 2）
`🚫 BLOCKED [mac-vm-guard]: この Mac で試験用の仮想マシンは作れません（メモリ 8GB のため）。GitHub の試験場を使ってください: gh workflow run sandbox-test.yml --ref <ブランチ> -f test=<名前>（規則: docs/ops/runner-commands.md §10）。Mac 実機でしか試せない場合は PO に許可券 "mac vm" を依頼してください。`

## 5. 例外（許可券）
許可券置き場（リポジトリ外）の danger-permit-*.json のうち `op == "mac vm"`・`created_by == "manual"`・`expires_at` 未到来のものが1つあれば、それを削除して通す（1回限り）。発行は既存の scripts/permit-danger.sh（変更なし）。AI による券の作成は既存 agent-danger-hook.sh の「permits 自己発行ブロック」で止まる（同ファイル :156-170）。

## 6. 失敗時の扱い
内部エラー（JSON が読めない等）は通す（fail-open、py312-guard と同じ）。理由: 見張りの不具合で全 Bash が止まる被害の方が大きい。拒否・券消費・内部エラーは agent-events.jsonl に1行記録する（H6 の観測源）。

## 7. 代替案と選択理由
- A 採用: Claude Code の PreToolUse フック。原因（AI が作った 4GB の VM）に直接効き、既存の見張りと同じ置き方で保守が1か所。
- B 不採用: `colima` を包む同名スクリプトを PATH の前に置く。人の命令も止められるが、絶対パス `/opt/homebrew/bin/colima` で素通りし、Homebrew 更新・colima-idle-stop と干渉する恐れがある。
- C 不採用: colima 自体を削除。開発用 DB（default）が使えなくなる。

## 8. 外部・過去事例の参照と我々への応用
Claude Code 公式の hooks 仕様（PreToolUse・exit 2 で拒否し標準エラーを AI に返す）に従う。確認は実装時に Context7 か公式資料で行い results.md に出典を残す。同種の運用は本リポジトリ内の py312-guard（K1〜K7 合格、docs/handoff/py312-guard/results.md）が実績。社外の数値事例は本件の成否の根拠にならないため使わない。

## 9. Opus 自己審査（同一 AI による審査）
- 整合: 段階1（no-mac-vm-guard.sh、PR の追加行検査）と止める形を揃えた。規則の正本は runner-commands.md §10 の1か所のまま。
- 検証可能性: H1〜H5 は試験スクリプトと実機で○×、H6 はログで○×。
- リスク: 誤検知 → H4 の試験と H6 の7日観測。作業中の便D（PR #4404）が Mac で VM を作れなくなる → 想定どおり（sandbox-test へ）。
- 判定: APPROVE（KGI の PO 承認後に実装可）。

## 10. 維持の仕組み
- 守り手: PreToolUse フック mac-vm-guard（全 AI セッション・担当に自動適用）と CI の no-mac-vm-guard。点検は Opus（H6・K5）。
- 見張りは ~/.claude/scripts/（他の見張りと同じ場所。リポジトリ外）。試験は `python3 ~/.claude/scripts/tests/test_mac_vm_guard.py` で再実行できる。
- 戻し方: settings.json の1件を消す（または mac-vm-guard.py を退避）。
- K5（2026-10-31 `colima list`）で段階1・2をまとめて効果測定する。
