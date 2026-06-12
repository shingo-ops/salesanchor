# recon — SessionStart 鮮度チェックフック（MTG決定 C）

対象: Claude Code のセッション開始時に **git fetch（非破壊）＋ 開発ルールの遅れ警告** を出すフックを導入。**自動 pull はしない**（作業中変更との衝突回避）。MTG資料 問題1（ルールが自動では伝わらない）への対策。

実コードを **フルパス:行番号** で突合（短縮禁止）。

## 1. 既存 ADR 検索（B の手順を自分で実践）
- `git grep -il "SessionStart" origin/develop` → ヒットは `docs/adr/ADR-042-guardrails-and-release-flow.md` のみ。
- `docs/adr/ADR-042-guardrails-and-release-flow.md:114`「Claude Code 側で自動切替の hook を整備 (settings.json の SessionStart hook 等)」＝**SessionStart hook は ADR-042 で既に想定済み**（文脈は Plan mode 自動切替の構想）。本フックはその hook 基盤の最初の実装。鮮度警告に用途を限定し、Plan mode 自動切替は範囲外（別途）。
- リポジトリに既存の hook 実装・`.claude/hooks/` は **存在しない**（`git log --all -- ".claude/hooks/*"` 空）。＝greenfield。

## 2. 現状ファイル（origin/develop）
- `.claude/settings.json:1-30` … `$schema` + `permissions.allow` のみ。**`hooks` セクションは無い**。ここに `SessionStart` を追記する。
- `.claude/` 配下: `agent-config.sh` / `agents/` / `settings.json`（hooks ディレクトリ無し→新規作成）。
- ルールの正本: `CLAUDE.md`（自動ロード）/ `docs/STANDARD-WORKFLOW.md`（SOP正本）/ `backend/CLAUDE.md` / `frontend/CLAUDE.md`。これらの「origin/develop に対する遅れ」を検知対象とする。

## 3. Claude Code SessionStart フック仕様（公式 docs 確認 2026-06-12）
- 出典: code.claude.com/docs/en/hooks。
- 構造: `hooks.SessionStart = [ { "matcher": "<source>", "hooks": [ { "type":"command", "command":"...", "timeout": <秒> } ] } ]`。
- matcher 値: `startup`（新規）/ `resume`（--resume等）/ `clear`（/clear）/ `compact`（圧縮）。→ 本フックは **startup / resume / clear** を対象（compact は毎回再 fetch になり無駄なので除外）。
- **stdout は SessionStart では Claude のコンテキストに注入される**（UserPromptSubmit / SessionStart の例外）。＝警告文を echo すれば Claude が起動直後に認識できる。
- exit 0: stdout がコンテキスト化。非 0: stderr をユーザーにのみ表示（非ブロッキング）。
- `timeout`（秒）フィールドでフック全体の実行時間を上限化＝**git fetch が固まってもセッションを止めない**（macOS に `timeout` コマンドが無い問題を回避できる）。
- `${CLAUDE_PROJECT_DIR}` がコマンドパスに使える。

## 4. プラットフォーム制約
- 両オペレータは macOS（darwin）。`timeout(1)` は標準で**無い**ため、シェル側で外部 timeout に依存しない。→ フックの `timeout` フィールド＋ `git -c http.lowSpeedLimit/Time` で二重に時間上限。
- worktree からの `git fetch` は可（共有 .git）。リポ外/ネット無しは黙ってスキップ（fail-open）。

## 5. 過去の関連メモ
- 2026-05-25 頃に個人環境で session_start 系 hook を使った形跡（メモリ）だが **リポには未コミット**＝チーム共有されていない。本 PR で初めて repo 共有のフックを入れる。
- `.claude/settings.json` の hooks セクションが過去に pull で消えた件（しんごさん意図未確認）＝**今回 MTG決定 C で hooks 追加が正式承認された**ため再追加は方針に沿う。軽量・fail-open 設計で副作用を最小化する。

## 6. 分類・ゲート
- 変更ファイル: `.claude/hooks/check-freshness.sh`（新規）/ `.claude/settings.json`（hooks 追記）。
- `scripts/check-process-artifacts.js` の DOCS/REAL_CODE 判定では `.claude/` はどのパターンにも該当せず **`unknown`→安全側で real-code 扱い**＝SOP 成果物（recon.md/design.md/PR節）が必要。本ファイル群で充足。
