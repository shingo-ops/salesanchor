# recon: クラウドでも手元と同じ見張りを効かせる（段階1）

状態: 調査済み（2026-10-22〜23、Opus＋Sonnet）

## 1. 既存ADR・仕様の検索
- ADR-1029（マージ前 Opus 審査のフック強制）: review-gate の gate.py は手元のホーム側にあり、リポジトリには無い。
- ADR-136（危険PRのGO手順）、ADR-1003（GO委任）、ADR-1033（会話同意）: いずれも手元の hooks／許可券（permit-danger.sh）を前提にしている。
- クラウド実行（Claude Code on the web / routine）を扱う ADR は無い。

## 2. 公式文書（code.claude.com/docs/en/cloud-environments、2026-10-22 取得）
- ユーザーの ~/.claude/settings.json（手元） の hooks と ~/.claude/CLAUDE.md（手元） はクラウドに入らない。リポジトリの `.claude/settings.json` は入る。
- クラウドでは `CLAUDE_CODE_REMOTE=true`。公式は、手元で動かしたくない hook ではこの変数を見て早く抜ける形を示している。
- GitHub への中継では GraphQL（`gh pr` 等）が 403、REST の `gh api` は通ると書かれている。

## 3. 実地試行
### 試行1（routine trig_01SkyvFEsfURzbJkxeSUE6AM）
- pre-push の `scripts/validate-pr-ownership.sh` が GraphQL で 403 になり、push の手前で止まった。→ PR #4663 で REST 化してマージ済み（本線 13576c09c）。

### 試行2（routine trig_01FtQo88ZtqATGzbmRn7Qucf、session cse_01Jedqsrgy8TgnsCmsK9ELYT）
生出力の要約: /tmp/CC報告ファイル/cloud-trial2-20261022/summary.txt
- 所要 306 秒。npm ci 57秒・lint 10秒・test:unit 113秒、すべて exit=0。
- origin は `https://github.com/shingo-ops/salesanchor`（資格情報なし）。
- リポジトリの husky（`.husky/`）はクラウドでも作動した。worktree 外の commit/push は「🚫 commit を中断しました: worktree 外での作業は禁止されています。」で止まり、`scripts/new-worktree.sh` で作り直すと通った。validate-pr-ownership は「✅ オーナーシップチェック通過」。
- `gh` は「The token in GH_TOKEN is invalid.」で使えなかった（公式の説明と違う。【未確認】原因）。
- クラウドには既定で GitHub MCP（`mcp__github__create_pull_request`、`mcp__github__get_me` など）があり、それで Draft PR #4664 を作れた。名義は `shingo-ops`。
- クラウド既定の ~/.claude/stop-hook-git-check.sh（クラウド既定） が、new-worktree.sh の作る未追跡の台帳ファイル（.claude-pipeline/active-work.d/ 配下の登録ファイル）を理由に、停止のたびに「commit して push せよ」と促した（3回）。

## 4. 手元の見張り48件の仕分け
生出力: /tmp/CC報告ファイル/cloud-parity-hooks-20261022/hooks-analysis.csv
- 移す 14件、移さない 33件（agent-console 19・音声 3・別窓の作業場所争い 6・その他 5）、無効 1件。内訳は design.md §4。

## 5. 分かったこと（設計への影響）
- commit/push 系の見張りはリポジトリの husky にあるので、クラウドでもそのまま効く。移植は Claude の道具呼び出しの前に止める系（PreToolUse）が中心になる。
- PR の作成・マージは `gh` ではなく GitHub MCP を通る。見張りの照合対象に MCP の道具名を含める必要がある。
- クラウドで作る PR は `shingo-ops` 名義になる。CLAUDE.md は、コード変更の PR を shingo-ops 名義で作ることを禁じている（docs のみの PR は除く）。
