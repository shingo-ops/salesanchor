# recon — migration-timestamp-dup-guard

**仕事名**: migration-timestamp-dup-guard
**日付**: 2026-06-24
**対象ADR**: ADR-082
**担当**: shingo-cc

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `.github/workflows/migration-guard.yml:4` | トリガ = `pull_request`（branches: main, develop） |
| `.github/workflows/migration-guard.yml:14` | `fetch-depth: 0`（全履歴あり＝base SHA 照合可） |
| `.github/workflows/migration-guard.yml:22` | `BASE=${{ github.event.pull_request.base.sha }}` |
| `.github/workflows/migration-guard.yml:81` | `git diff "$BASE" "$HEAD" --name-only --diff-filter=A` |
| `.github/workflows/migration-guard.yml:107` | 既存形式チェック `^[0-9]{8}_[0-9]{6}_.*\.sql$` |
| `backend/CLAUDE.md:51` | 命名規約「100番以降は YYYYMMDD_HHMMSS_description.sql」 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | main 既存の重複6組が新ゲートに誤検知されないか | `--diff-filter=A`（新規追加のみ）＝base 側の既存ファイルは対象外。構造的に自動充足 | ✅ 解消済み |
| 2 | `xargs -r` の `-r` フラグが macOS/Linux 両方で動くか | CI は ubuntu-latest のみ実行。Linux で `-r` は標準サポート | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

- 新 step は既存 job の末尾に追記のみ。既存 step は一行も変更しない。
- `fetch-depth: 0` を job-level で既に設定済みのため、`git ls-tree "$BASE"` が使用可能。
- 既存重複6組は base(main) 側に在り「新規追加」ではないため `--diff-filter=A` に出ない。
