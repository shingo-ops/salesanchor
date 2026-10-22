# design: クラウドでも手元と同じ見張りを効かせる（段階1）

状態: 設計案作成済み／設計審査済み（同一AIの自己審査）／方針は Opus 決定（PO 委任に基づく）／実装未着手
根拠: recon.md（同じフォルダ）

## 1. 目的
PO 2026-10-22「クラウドでもいまと変わらない環境を構築したい、本番への読み取りも、hookも」。
段階1は hook（見張り）。クラウドで動く AI が、手元と同じ禁止事項で止まるようにする。
段階2（本番を HTTPS で読む窓口）、段階3（社外秘・試算材料の置き場所）、段階4（結果の持ち帰り）は対象外。

## 2. 方針（Opus 決定・2026-10-23）
PO 2026-10-23「今まで通りopusには権限委譲するので決まったことは自律的に行ってほしい」を受け、次のように決めた。
- クラウドの役割は「調べる・作る・push する」まで。マージ、危険操作、本番DBへの書込は、クラウドでは例外なく止める。
- 理由: GO とマージの委任先は手元の Opus（ADR-1003）。手元には、Opus 審査の記録と PR 番号・HEAD を照らし合わせる仕組み（ADR-1029 gate.py）がある。クラウドには、この照合の記録も許可券（permit-danger.sh）も無い。クラウドでマージを許すと、委任の外で取り込まれる道ができる。
- PR の作成: docs だけの PR はクラウドで作ってよい。コード変更を含む枝はクラウドでは push までとし、PR は手元で `shingo-cc` 名義で作る。理由: クラウドの PR は `shingo-ops` 名義になる（recon §3）。CLAUDE.md は、コード変更の PR を shingo-ops 名義で作ることを禁じている。

## 3. 成功条件
| No | 基準 | 検証方法 |
|---|---|---|
| K1 | クラウドで、危険操作（DROP TABLE・`rm -rf`・`git push --force`・`git reset --hard` など。CLAUDE.md の一覧と同じ）を Bash で実行しようとすると止まる | クラウド試行で `echo` で包まず命令そのものを試させ（実害のない対象で）、止めた文言を記録する。手元のテスト台本で、各命令を入れて exit 2 になることを確かめる |
| K2 | クラウドで、PR のマージ（`mcp__github__merge_pull_request`、`gh api …/merge`、`gh pr merge`）が止まる | 同上 |
| K3 | クラウドで、コード変更を含む枝の PR 作成（`mcp__github__create_pull_request`、`gh api … /pulls` の POST、`gh pr create`）が止まる。docs だけなら通る | テスト台本で、変更ファイル一覧が docs のみ／コードを含む の2通りを試す |
| K4 | クラウドで作る PR 本文に「### 標準ワークフロー確認」が無いと止まる | テスト台本 |
| K5 | クラウドで、英語だけの最終返事が止まる。会話の始まりに、手元の個人用 CLAUDE.md（ホーム側） に相当する決まり（報告の型・秘密を出さない等）が入る | クラウド試行の記録（get_run_log）で確認 |
| K6 | 手元（Mac）では新しい見張りが一切動かない | 手元で `CLAUDE_CODE_REMOTE` 未設定のまま dispatch.sh に各入力を流し、すべて exit 0・出力なしになること |
| K7 | Python 以外の新しい依存を足さない。各見張りは 1 回 1 秒以内に終わる | テスト台本で時間を測る |

## 4. 何を移すか（48件の仕分け）
生出力: /tmp/CC報告ファイル/cloud-parity-hooks-20261022/hooks-analysis.csv
移す:
- agent-danger-hook（#21）→ K1。許可券・会話同意の例外は持ち込まない。
- review-gate gate.py（#45）のマージ止め部分 → K2。クラウドでは「常に止める」に簡略化する。
- pr-body-guard（#24）→ K4。照合対象に MCP の道具と `gh api` の POST を加える。
- 新規: PR 作成時の名義・範囲の止め → K3。
- japanese-reply-guard（#14）→ K5。
- 決まりの注入（SessionStart）→ K5。
- master-register-rules-guard（#6, #40）: すでにリポジトリ版がある。直書きのパスを `$CLAUDE_PROJECT_DIR` に置き換えて配線する。
- python-version-guard（#43）、subagent-bash-wait-guard（#47）、card-lint-hook（#4）。
移さない:
- worktree-only-guard（#20, 26, 28, 46）: commit/push の止めは、リポジトリの husky がクラウドでも効く（recon §3）。重ねない。
- agent-console 関連 19件、音声 3件、別窓の作業場所争い 6件、mac-vm-guard（#44）、本店の写しの古さ警告（#48）、メモリ点検（#9）、許可拒否ログ（#17）、審査記録（#12）。
- launch_guard_for_sim（#39）は段階3で扱う。
無効: gh-scope-guard（#23）。

## 5. 作り方
- `scripts/agent-hooks/cloud/` を新設する。入口は `scripts/agent-hooks/cloud/dispatch.sh` 1本で、先頭に `[ "$CLAUDE_CODE_REMOTE" = "true" ] || exit 0` を置く（K6）。
- 個々の見張りは同じフォルダに置く。各ファイルの先頭に「元: ~/.claude/hooks/<名>」を書く。Mac の絶対パスは使わない。
- `.claude/settings.json` の hooks に、dispatch.sh を PreToolUse（Bash と `mcp__github__.*`）、Stop、SessionStart で配線する。既存の hooks は消さない。
- 決まりの本文は `scripts/agent-hooks/cloud/rules.md` に置き、SessionStart で会話に渡す。秘密・社外秘（仕入元名など）は入れない（リポジトリは公開）。
- 手元のテスト台本 `scripts/agent-hooks/cloud/test.sh` で、K1〜K4・K6・K7 を確かめる。

## 6. 代替案
- A: 手元の `~/.claude` をそのままクラウドへ写す → 33件が Mac 専用で誤作動する。不採用。
- B: 見張りを GitHub の CI に寄せる → 命令の前に止められない。不採用。
- C（採用）: リポジトリに「クラウドでだけ動く」写しを置く。公式が示す形。
- マージ方針の代替（許可券をクラウドへ／マージだけ許す）: 委任の照合をクラウドに作り直す必要がある。2 で述べた理由で不採用。

## 7. リスクと対処
- リポジトリは公開なので、止める言葉の一覧が外から読める → 秘密・社外秘は書かない。
- 手元の見張りを直したときに、クラウド側が古くなる → 写しに出どころを書く。週次の点検で差分を見る（別カード）。
- 止めすぎてクラウドの作業が進まない → 試行で止まった命令を記録し、1件ずつ直す。
- クラウド既定の stop-hook-git-check.sh が、未追跡の台帳ファイルで促しを繰り返す → クラウドへの依頼文の型に「active-work.d の登録ファイルは commit しない。促しは無視してよい」と書く（rules.md に含める）。

## 8. 戻し方
`.claude/settings.json` から、足した hooks を消す（1 commit の Revert）。手元は CLAUDE_CODE_REMOTE で最初から素通しなので、影響はない。

## 9. 外部・過去事例の参照と我々への応用
Anthropic 公式文書の推奨形（CLAUDE_CODE_REMOTE で切り分ける）に従う。数値つきの導入事例は見つけていないので、成功の証明には使わない。効果は K1〜K7 の実地試行で測る。

## 10. 維持の仕組み
- 守り手: Opus（設計統括）。手元の見張りを直したときに、クラウド側の写しの更新要否を判断する。
- 写しの出どころを各ファイルの先頭に書く。
- test.sh を CI に載せるかは、段階1の結果を見て別カードで決める（今回は CI 設定を変えない）。

## 11. 審査（Architect・同一AIの自己審査）
判定: APPROVE。
- 根拠: 二重発火を避ける方法は公式文書で、husky と GitHub MCP の挙動は試行2の実地で確かめた。
- 未解決: `gh` の GH_TOKEN が無効になる理由は【未確認】。ただ、MCP の道を止めの対象に含めるので、設計は成り立つ。SessionStart で渡した決まりが CLAUDE.md と同じだけ効くかは、K5 の試行で確かめる。
