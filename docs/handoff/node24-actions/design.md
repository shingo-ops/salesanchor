# design: GitHub Actions Node 24 対応（ADR-129）

> recon: `docs/handoff/node24-actions/recon.md`
> 対象ADR: ADR-129

## 1. 変更理由

GitHub は Node.js 20 の EOL（2026-04）を受け、2026-06-16 から GitHub-hosted runner の JavaScript actions デフォルトランタイムを **Node.js 24 に強制変更**する。
これ以降、Node 20 runtime に依存する旧バージョンの actions は deprecation warning を出し続け、2026 年秋には削除予定。

本リポジトリで使用中の 4 アクションを Node 24 対応版へ更新する（詳細: `docs/handoff/node24-actions/recon.md`、ADR-129）。

## 2. 変更内容

| アクション | 変更前 | 変更後 | 箇所数 |
|-----------|--------|--------|--------|
| `actions/checkout` | `@v4` | `@v5` | 64 |
| `actions/setup-node` | `@v4` | `@v5` | 15 |
| `dorny/paths-filter` | `@v3` | `@v4` | 5 |
| `webfactory/ssh-agent` | `@v0.9.0` | `@v0.10.0` | 1 |
| **合計** | | | **85 箇所・48 ファイル** |

機械的な置換のみ（ロジック変更なし）。

## 3. 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| Node 24 対応版 actions のバージョン文字列が全ワークフローに反映されている | `grep -r "checkout@v4\|setup-node@v4\|paths-filter@v3\|ssh-agent@v0.9" .github/workflows/` が 0 件（workflow-lint.yml 除く） |
| CI 全ジョブ（ubuntu-latest）が Node 24 環境で正常動作する | PR #1983 の全 CI チェックが green |
| 本番デプロイが正常完了する | デプロイ検証: Bootstrap / migrations / smoke (SA-19) / Stamp の全ステップ ✓ |
| `workflow-lint.yml` の変更禁止ゲートが通過する | `CI設定整合性チェック` が pass |
| Node 20 deprecation warning が消える | 2026-06-16 以降のデプロイログに `Node.js 20 actions are deprecated` が出ないこと |

## 4. 外部・過去事例の参照と我々への応用

### 外部事例

**GitHub 公式アナウンス（2025-09-19）**:
「Deprecation of Node 20 on GitHub Actions runners」
- 内容: 2026-06-16 から Node 24 をデフォルトに変更、2026 年秋に Node 20 削除
- 対応方法: `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` の環境変数（一時回避）または actions を Node 24 対応版に更新
- 参照: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/

### 各アクションの Node 24 対応バージョン

| アクション | Node 24 対応リリース | リリース日 |
|-----------|-------------------|-----------|
| `actions/checkout@v5` | v5.0.0 | 2024-08-11 |
| `actions/setup-node@v5` | v5.0.0 | 2024-09-04 |
| `dorny/paths-filter@v4` | v4.0.0 | 2026-03-12 |
| `webfactory/ssh-agent@v0.10.0` | v0.10.0 | 2025-03-11 |

### 我々への応用

- `@v6`（checkout/setup-node）は credentials 保存方式に破壊的変更あり → 今回は `@v5` に留める
- 次の更新タイミング（Node 24 EOL 見込み 2027 年後半）でも同手順を踏む
- `workflow-lint.yml` の Node 20 残留は deprecation warning のみで hard failure にはならないため、別途 PO 承認を経て対応する

## 5. リスクと対処

| リスク | 対処 |
|--------|------|
| self-hosted runner（shingo-mac）が runner v2.327.1 未満の場合 checkout@v5 が失敗 | shingo-mac は 2024年以降に設定済みのため v2.327.1 以上を満たすと推定。デプロイ検証で確認 |
| `actions/checkout@v5` の挙動変化でワークフローが壊れる | 全 CI チェック green で確認後にマージ |
