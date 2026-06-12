# Phase 3 設計 — migration-full-dryrun

**対象ADR**: ADR-135  
**recon**: docs/handoff/migration-full-dryrun/recon.md  
**日付**: 2026-06-12  
**担当**: Hikky-dev

---

## 外部・過去事例の参照と我々への応用

- GitHub Actions で PostgreSQL サービスコンテナを使ったマイグレーションテストは一般的なパターン（GitHub公式 PostgreSQL service container ドキュメント参照）。今回は既存の `migration-test-run` ジョブと同一サービス設定を踏襲し、`run_all_migrations.sh` の記載順を SSoT とした。
- 過去事例（#1981）: change_billing migration が deploy.yml 修正のリリースに相乗りし、PO GO 前の migration が本番に出る寸前だった。今回のドライランはこの穴を機械的に塞ぐ。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| migration変更がある場合のみ dryrun ジョブが起動する | CI: `on.pull_request.paths` フィルター（`.github/workflows/migration-test.yml:554`付近） |
| 20260604以降のタイムスタンプSQLが順次実行されエラーなく完了する | CI: `migration-full-dryrun` ジョブ（GitHub Actions ログ） |
| migration-test aggregator が dryrun の結果を統合する | CI: `needs: [detect-changes, migration-test-run, migration-full-dryrun]`（行898） |
| Python依存の番号付きmigrationはスキップされ失敗しない | CI: grepフィルター `20260604以降` で番号付き除外 |

---

## 技術 How・KPI

- KPI: migration変更PRで dryrun PASS率100%（新規migration追加時の早期検知）
- 技術選択: `grep '^run_sql' | awk | grep -E` で run_all_migrations.sh の SSoT 順序を尊重

---

## 弊害・トレードオフ

- 20260602以前の古いタイムスタンプSQLはカバーしない → 対策: これらは Python テーブル依存のため CI 実行不可。本番では deploy.yml で管理
- CI時間が約1〜2分増加 → 許容範囲

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | migration-full-dryrun ジョブを migration-test.yml に追加 | Generator |
| 2 | 20260604以降フィルターで 20260602 依存問題を解消 | Generator |
| 3 | aggregator を更新して dryrun を統合 | Generator |

---

## 継続

- 完了後の監視: 新規migration追加時に CI ログで dryrun 結果を確認
- 次フェーズへの引き継ぎ: Python依存migrationの CI 実行可能化は別タスク
