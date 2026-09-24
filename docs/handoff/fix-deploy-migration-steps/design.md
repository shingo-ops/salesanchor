# design: fix-deploy-migration-steps

## recon 参照
- docs/handoff/fix-deploy-migration-steps/recon.md
- 対象ADR: ADR-082（migration は run_all_migrations.sh に統合）

## KGI/KPI
- KGI: 次回デプロイ時に migration ステップが /tmp/migrations/ 参照エラーなく完了する
- KPI: deploy.yml の `Run database migrations` ステップが success になる

## 変更方針
deploy.yml の誤った個別ステップ2件を削除する。
`scripts/run_all_migrations.sh` が `migrations/20260924_040000_seed_knowledge_extraction_vocab.sql` と
`migrations/20260924_050000_create_supplier_knowledge_links.sql` を正しく実行する。

## 影響範囲
- .github/workflows/deploy.yml のみ（行削除）
- 弊害なし（冪等マイグレーションが1回呼ばれるだけになる）

## 戻し方
git revert で元に戻せる（ただし戻すとデプロイが再度失敗する）

## 外部・過去事例の参照と我々への応用
`scripts/run_all_migrations.sh` の run_sql パターンは既存の全マイグレーションで採用済み（ADR-082）。
今回の失敗は deploy.yml に個別ステップを直書きした際の典型的なパスミスであり、run_all_migrations.sh 経由に一本化するルールを守ることで再発防止できる。

## 維持の仕組み
- deploy.yml のコメント「新マイグレーション追加時は run_all_migrations.sh に追記する」が守り手
- CI の deploy.yml lint（workflow-lint.yml）でステップ構造を確認

## 守り手
- `scripts/run_all_migrations.sh` を変更する場合は必ず `.github/workflows/deploy.yml` と整合性を確認すること
