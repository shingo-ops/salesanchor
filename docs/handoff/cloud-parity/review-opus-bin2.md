# review-opus（便2）: release/cloud-parity-bin2 マージ前審査

審査役: Claude Opus（新規起動・reviewer）／対象 head: 4ca6c91049baa29b01298de44ce48a1765d77084／日時: 2026-10-23 JST
生出力: /tmp/CC報告ファイル/cloud-parity-bin2-review-20261023/（手元）

## 設計者（Opus）の扱い
- 任意1（design.md:38 がカード §4 の一覧外）: 設計者が実装担当に指示した変更（参照1つの追加）。次のカードから §4 に含める。
- 任意2（timeout 10 秒と git show 最大20秒の差）: 未確認のため、クラウド試行4で #40 の所要時間を記録して確かめる。10 秒を超えるなら別カードで timeout を手元と同じ 30 にする。
- 任意3（使われない引数 cwd）: カードどおり。直さない。

## 審査役の報告（原文）

マージ前審査の結果：release/cloud-parity-bin2（HEAD 4ca6c9104）は承認です。マージを止める指摘はありません。

生出力の置き場所（/tmp/CC報告ファイル/cloud-parity-bin2-review-20261023/）
- diffstat.txt、diff.txt（origin/main...HEAD の差分。全650行）
- copies-diff.txt（写し3本と元の差分）
- test-cloud.txt、test-mrr.txt（試験の生出力）
- secret-scan.txt（秘密語の検索結果）

１：カードどおりか（§4-1〜§4-7）

【事実】変更は9ファイルでした（diffstat.txt）。カード §4 の7件に加えて、カード本体 `docs/handoff/cloud-parity/card-2.md`（新規）と `docs/handoff/cloud-parity/design.md` の1行が入っています。
- §4-1：`scripts/agent-hooks/master-register-rules-guard.py:14` はカードの変更後の行と一字一句同じです。変わったのはこの1行だけです。
- §4-2：`python_version_guard.py` と元（194行）の差分は次の4点だけでした（copies-diff.txt）。
  - 先頭への「元:」行の追加
  - LOG の既定を `/tmp/agent-events.jsonl` に変更
  - MSG をカードの文言に変更
  - ROOT・WT・`in_scope_path`・`in_scope` の削除と、`decide` の条件を `if not isinstance(command, str):` に変更（`python_version_guard.py:123`）
  - これ以外に違いはありません。
- §4-3：`subagent_bash_wait_guard.py` の違いは、:1 の「元:」行と :17 のログ既定の2点だけです。
- §4-4：`card_lint_hook.sh` は5点ともカードどおりです。
  - 「元:」行を追加
  - /tmp への書込を削除
  - `python3` に変更
  - 検査本体の場所を :42-43 の1か所に変更
  - warn モードを削除し、rc=1 なら常に exit 2（:52-58）
  - 「END OF CARD を含まなければ素通し」「プロンプトが取れなければ素通し」「rc≠1 なら素通し」は元のままです。
- §4-5：`dispatch.sh:19-48` はカードのコード片と一致しています。:2 の `CLAUDE_CODE_REMOTE` の行は変わっていません。
- §4-6：`.claude/settings.json` は「8行追加・0行削除」です。追加は PreToolUse の `Write|Edit` 項目と UserPromptSubmit の新設だけでした。既存の hooks と permissions に削除・変更の行はありません。JSON として読めることも確かめました（hooks のキー：PreToolUse/SessionStart/Stop/SubagentStop/TeammateIdle/UserPromptSubmit）。
- §4-7：test.sh に B1〜B8 が追加され、既存のケースはそのまま残っています。商品作成の命令名は `TARGETS` を import して組み立てており、台本に直接は書いていません（test.sh 追加部の冒頭）。

２：正しさ

【事実】
- PreToolUse の終了コードの扱い
  - guard_pre_tool.py が 0・2 以外を返すと、dispatch が止めます（exit 2）。
  - 写し2本は、0 なら次へ進み、2 ならそのまま止め、それ以外は内部エラーの文言を出して止めます（`dispatch.sh:27-33`）。
  - master-register の判定（JSON の deny）は標準出力にそのまま流れ、0 以外なら止めます（:35-40）。
  - カード §3 の「0・2 以外は止める」に合っています。
- UserPromptSubmit の順序
  - card-lint を先に動かし、2 なら止めます。それ以外の値は素通しで、これは元の動きと同じです。
  - その後に master-register の知らせ（additionalContext）を出します（:43-47）。
- 新しい `Write|Edit` 配線で既存の見張りも呼ばれるようになりますが、`guard_pre_tool.py:243` が Bash と mcp__github__ 以外を対象外にしているため、止めすぎは起きません。`python_version_guard.py` も command が無ければ素通しです。
- K6（手元では何も動かない）：B7 は「17件中 逸脱 0件」、既存の K6 も「54件中 逸脱 0件」でした（test-cloud.txt）。

３：止め漏れ・止めすぎ／カード §6 との対応

【事実】
- origin/main が無い場合：`master-register-rules-guard.py:75-77` で deny（止める側）になります。§6 のとおりです。
- python3.12 が無い場合：写しは場所の条件を持たず、venv の作成と pip install を止めます。§6 のとおりです。

【推測】確かめていない懸念が1つあります（任意の2件目で詳しく書きます）。

４：秘密・社外秘

【事実】追加された行を秘密語で検索した結果は13件で、すべて次のどれかでした（secret-scan.txt）。秘密の値・Webhook URL・社外秘の分析記録はありませんでした。
- 秘密を伏せるための正規表現
- 関数名 `tokens`
- 設計書のパス
- Mac のパス `/Users/tanizawashingo/...`（main にすでにある行と同じ種類で、`master-register-rules-guard.py` の変更前の :14 にもあります）

５：試験（自分で実行）

【事実】
- `bash scripts/agent-hooks/cloud/test.sh`：rc=0、「結果: 全件OK」。B1〜B6b の17件はすべて OK です。B8 の最大は 0.270 秒で、既存の K7 は「1秒以上 0件（負荷 13.8）」でした。今回の実行では、実装担当が報告した K3 の 1.359 秒は再現しませんでした（既存ケースの最大は 0.282 秒）。
- `bash scripts/agent-hooks/test_master_register_rules_guard.sh`：rc=0、18件すべて PASS です。

指摘

必須（マージを止める）：ありません。

任意：
1. `docs/handoff/cloud-parity/design.md:38` は、カード §4 の「これ以外は触らない」の一覧に入っていないファイルの変更です。中身は「→ 便2（card-2.md）」という参照を1つ足しただけで、動作には影響しません。次のカードからは §4 に書いておくとよいです。
2. `.claude/settings.json` の新しい配線は timeout 10 秒（カード §4-6 の指定どおり）です。一方、`master-register-rules-guard.py:36` の `git show` は最大20秒待ちます。【推測・確かめていません】クラウドで git が10秒を超えて止まった場合、Claude Code はフックの時間切れを「止めない側」として扱うと理解しています。そうだとすると、#40 が止めずに通してしまいます。手元の元の配線は timeout 30 です。クラウド試行4で、時間を記録して確かめることを勧めます。
3. `python_version_guard.py:121` の `decide(command, cwd)` に、使われなくなった引数 `cwd` が残っています。カードが「それ以外は1字も変えない」としているので、そのままで正しい扱いです。指摘というより記録として残します。

VERDICT: APPROVE
