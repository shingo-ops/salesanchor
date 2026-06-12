# ADR-129: GitHub Actions ランタイムバージョン追従方針

- **Status**: Accepted
- **Date**: 2026-06-12
- **Deciders**: shingo-ops（PO）, Hikky-dev（Dev）

## Context

GitHub Actions の JavaScript actions は内部ランタイムとして特定の Node.js バージョンを使用する。
GitHub はランタイムの EOL に合わせてデフォルトバージョンを切り替えており、
対応していない action バージョンを使い続けると警告が出た後、最終的に強制切換・削除される。

今回の変化:
- Node.js 20 が 2026-04 に EOL を迎えた
- GitHub は 2026-06-16 から GitHub-hosted runner の JavaScript actions デフォルトを Node 24 に変更
- 2026 年秋には Node 20 ランタイムを削除予定

本リポジトリでは以下の 4 アクションを計 48 ワークフロー（85 箇所）で使用しており、全て Node 20 runtime の旧バージョンを参照していた:

| アクション | 旧バージョン | 新バージョン |
|-----------|------------|------------|
| `actions/checkout` | `@v4` | `@v5` |
| `actions/setup-node` | `@v4` | `@v5` |
| `dorny/paths-filter` | `@v3` | `@v4` |
| `webfactory/ssh-agent` | `@v0.9.0` | `@v0.10.0` |

例外: `workflow-lint.yml` は CLAUDE.md §不可逆操作 の対象ファイルのため、
個別の PO 承認を得てから別途対応する。

## Decision

### D1. バージョン更新方針

サードパーティ action のバージョンは、ランタイム EOL の**強制適用日の直前**（1 週間以内）に一括更新する。
更新は機械的な置換のみ（ロジック変更なし）であれば ADR 不要だが、
`deploy.yml` を含む場合は本 ADR を参照し process-artifacts gate を通過させること。

### D2. 今回の更新内容

全 48 ワークフロー・85 箇所を `sed` 一括置換で更新（PR #1983）。
Breaking changes:

- `actions/checkout@v5`: `@v4` と後方互換。credentials 保存方式の変更は `@v6` 以降のため今回は影響なし
- `actions/setup-node@v5`: `@v4` と後方互換
- `dorny/paths-filter@v4`: runtime 更新のみ。filter syntax 変更なし
- `webfactory/ssh-agent@v0.10.0`: minor version bump のみ

### D3. 将来の更新タイミング

- Node 24 EOL（見込み 2027 年後半）時に同様の手順で `@v6`/`@v5` 等へ更新
- `AUTHORIZED_APPROVERS` 制約（process-artifacts gate）により dangerous 変更は必ず PO 確認が必要

## Consequences

- Node 24 強制適用後も CI が正常動作し続ける
- Node 20 deprecation warning が消え、ログが読みやすくなる
- `workflow-lint.yml` のみ `@v4` 残留（warning は出るが hard failure にはならない）
