# recon: qa-smoke 自動実行の停止

現在地の調査は design.md §2（file:line 付き）。設計: docs/handoff/qa-smoke-rebuild/design.md

主な根拠（詳細は design.md §2）:
- 動かす機械は監視サーバーの self-hosted runner: `.github/workflows/qa-smoke.yml:58`
- 起動条件（毎週・PR・手動）: `.github/workflows/qa-smoke.yml:37-48`（この PR で毎週と PR を削除）
- 本番 DB の tenant_006 の表を消して入れ直す: `scripts/qa/seed-tenant.sql:76-94`
- 試験の途中でも DB を直接数える: `tests/qa-smoke/utils/db-assert.ts:49`
- 動作確認の会社の決まり（tenant_001 は QA、tenant_006 は QA 禁止）: `docs/STANDARD-WORKFLOW.md:98`
既存 ADR 検索: ADR-038・ADR-078・ADR-080・ADR-1013・ADR-1017・ADR-1048・ADR-1024 を確認（design.md §2 と §9）。

生出力の置き場（design.md 6 行目）:
- /tmp/CC報告ファイル/qa-smoke-recon/
- /tmp/CC報告ファイル/qa-smoke-recon2/
- /tmp/CC報告ファイル/qa-smoke-design/raw/
- /tmp/CC報告ファイル/auth-status-1030/
