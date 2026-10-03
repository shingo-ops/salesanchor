branch: release/stop-products-column-churn

| ブランチ名 | 担当機能エリア | 開始日時 | 状態 | PR# | main | 備考 |
|-----------|--------------|---------|------|-----|------|------|
| release/stop-products-column-churn | public.products 列 churn 停止（1600列上限インシデント対応） | 2026-10-04 00:00 | IN_PROGRESS | | | worktree ディレクトリ名は `release-llm-usage-charts`（元ブランチ `release/fx-rate-history-table`, PR #3957 マージ済み・worktree 上限100件のため再利用。`git switch -c release/stop-products-column-churn origin/main` で作成）。インシデント: 2026-10-03 deploy run 37130920016 失敗（1600列上限）。詳細: docs/handoff/products-column-churn/ |
