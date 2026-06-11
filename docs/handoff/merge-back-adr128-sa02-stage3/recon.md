# recon — main → develop マージバック（ADR-128 + SA-02 Stage 3 migration 統合）

**仕事名**: merge-back-adr128-sa02-stage3
**日付**: 2026-06-11
**対象ADR**: ADR-114

## コンフリクト箇所の確認

| 確認事項 | 引用 |
|---------|------|
| ADR-128 migration 追加行（develop 側） | `scripts/run_all_migrations.sh:336` |
| SA-02 Stage 3 migration 追加行（main 側） | `scripts/run_all_migrations.sh:339` |
| SA-02 Stage 3 依存 migration | `scripts/run_all_migrations.sh:343` |

## 変更内容

main に直接コミットされた SA-02 Stage 3 マイグレーション（`20260611_120000` / `20260611_130000`）が
develop の `run_all_migrations.sh` に存在せず、release PR がコンフリクト状態になっていた。

コンフリクト解消方針：両方のマイグレーションを timestamp 昇順で保持（`scripts/run_all_migrations.sh:336-343`）。
ファイル内容の変更はなく、develop + main 双方の変更を統合しただけ。

## 不明点リスト

なし。
