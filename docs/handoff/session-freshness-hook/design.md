# design — SessionStart 鮮度チェックフック（MTG決定 C）

参照: recon = `docs/handoff/session-freshness-hook/recon.md` ／ 関連 ADR: **ADR-042**（運用ガードレール・SessionStart hook 構想 L114）／ MTG資料 `docs/meetings/2026-06-11-claude-code-dev-best-practices.html` 問題1・第5章。SOP: `docs/STANDARD-WORKFLOW.md`。

## 0. KGI（PO 承認: しんごさん A〜D 承認済み 2026-06-12）
セッション開始時に**ローカルの開発ルール（CLAUDE.md / STANDARD-WORKFLOW.md 等）が origin/develop より遅れていれば自動で気づける**状態にする。定量: 遅れがある起動で警告がコンテキストに出る＝1（出ない＝0）。自動 pull は**しない**（人が判断）。

## 1. 外部・過去事例の参照と我々への応用
- **公式 Claude Code hooks（recon §3）**: SessionStart の stdout はコンテキストに注入される標準機能。`timeout` フィールドでフック実行を時間上限化できる＝ネット遅延でセッションを止めない安全設計に合致。これをそのまま用いる。
- **過去事例（ADR-042 L114）**: 「settings.json の SessionStart hook を整備」は既に方針化済み。本実装はその hook 基盤の初版で、用途を「鮮度警告」に限定（Plan mode 自動切替は範囲外）。
- **過去事例（auto-release-pr.yml）**: 「自動化で人手の取りこぼしを防ぐ」思想と一致（ただし本件はローカル hook で、CI ではない）。

## 2. 技術 How
### 2.1 `.claude/hooks/check-freshness.sh`（新規）
- `git rev-parse --show-toplevel` でリポルートへ。取得できなければ `exit 0`（リポ外＝何もしない）。
- `git -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=5 fetch origin develop --quiet` を実行（**非破壊**・低速時 5 秒で打ち切り）。失敗（オフライン等）は `exit 0` で黙ってスキップ（fail-open）。
- ルールファイル群 `RULES="CLAUDE.md docs/STANDARD-WORKFLOW.md backend/CLAUDE.md frontend/CLAUDE.md"` について `behind=$(git rev-list --count HEAD..origin/develop -- $RULES)` を算出。
- `behind > 0` のとき、stdout に**日本語＋英語併記の警告**を出す（「ルールが N 件遅れ・最新を取り込んでから着手・自動 pull はしない」）。`behind == 0` は**無出力**（静かに通す＝ノイズを出さない）。
- 常に `exit 0`（非ブロッキング）。
### 2.2 `.claude/settings.json`（hooks 追記）
- 既存 `permissions` を保持しつつ `hooks.SessionStart` を追加。matcher = `startup` / `resume` / `clear` の3エントリ（`compact` は除外）。各 `command = bash "${CLAUDE_PROJECT_DIR}/.claude/hooks/check-freshness.sh"`、`timeout: 12`。

## 3. 受け入れ基準（各基準に検証方法）
| # | 基準 | 検証方法 |
|---|---|---|
| 1 | 遅れ有り（HEAD が origin/develop のルール更新を含まない）で警告文を stdout 出力 | ローカル: ルール更新を含む origin/develop に対し、1つ前の状態を HEAD にして実行→警告が出ることを確認 |
| 2 | 遅れ無し（最新）で**無出力** | 最新 develop チェックアウトで実行→出力空・exit 0 |
| 3 | リポ外で何もしない（exit 0） | `cd /tmp && bash <script>` → 無出力・exit 0 |
| 4 | オフライン/fetch 失敗で固まらず exit 0 | 無効 remote をシミュレート（`http.lowSpeedTime` 効く）／fetch 失敗時 exit 0 をコードレビュー |
| 5 | settings.json が有効な JSON で hooks.SessionStart を持つ | `python -m json.tool .claude/settings.json` ＋ 構造確認 |
| 6 | 自動 pull をしない（fetch のみ） | コードレビュー（`git pull`/`merge`/`reset` を含まないこと） |
| 7 | 非ブロッキング（常に exit 0・timeout で上限） | コードレビュー＋ shellcheck |

## 4. 弊害・トレードオフ
- セッション開始時に最大 ~数秒の fetch 遅延（online は 1-2 秒、offline は lowSpeedTime 5 秒＋timeout 12 秒で上限）。`compact` を除外し頻度を抑制。
- `.claude/settings.json` は repo 共有＝両オペレータの Claude Code で発火（意図通り＝チーム全体の鮮度担保）。過去に hooks セクションが消えた経緯（しんごさん意図未確認）があるが、本 hook 追加は **MTG決定 C で正式承認済み**。軽量・fail-open で副作用最小。
- これは「気づかせる」層であり**強制ではない**。確実性の本命は CI ゲート（process-artifacts 等）。本 hook はそれを補完する“発見”層（MTG資料 守りの三層の「気づかせる」）。

## 5. 計画・継続
- 将来 ADR-042 の Plan mode 自動切替を同 hook 基盤に載せる余地あり（本 PR 範囲外）。
- 警告対象ルールファイルは `RULES` 変数で一元管理（増えたら追記）。
