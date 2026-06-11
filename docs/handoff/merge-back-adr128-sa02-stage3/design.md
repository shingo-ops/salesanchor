# design — main → develop マージバック（ADR-128 + SA-02 Stage 3 migration 統合）

## 参照

- ADR: `docs/adr/ADR-114-develop-auto-done-stamp.md`
- Recon: `docs/handoff/merge-back-adr128-sa02-stage3/recon.md`

## How

main に直接コミットされた migration エントリを develop の `run_all_migrations.sh` に追加する。
timestamp 昇順を維持し、依存関係を壊さない順序で統合。

## KPI / 検証基準

| 基準 | 検証方法 |
|------|---------|
| `run_all_migrations.sh` に3行とも含まれる | `grep -c "20260611_1[123]0000" scripts/run_all_migrations.sh` が 3 |
| release PR #1948 のコンフリクトが解消される | PR マージ可能状態になることを確認 |

## 外部・過去事例の参照と我々への応用

- **Git merge-back パターン**: main に hotfix/直接コミットが入った場合、develop にマージバックして divergence を解消するのは標準的な Git Flow の操作。
- 本プロジェクトでは同様のマージバック（PR #1939）を 2026-06-11 に実施済み。同じ手順で対応。

## 弊害・トレードオフ

なし（ファイル内容に実質的な変更なし・migration の追加のみ）。
