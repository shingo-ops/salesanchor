# design — dist01 ar.created_at バグ修正

参照: `docs/handoff/dist01-ar-created-at/recon.md`
ADR: ADR-154

## KGI / 検証基準

| 基準 | 検証方法 |
|------|---------|
| `GET /api/v1/tcg/distribution/preview` が 200 を返す | デプロイ後に Python スクリプトで直接呼び出し確認 |
| `ar.updated_at >= NOW() - INTERVAL '30 days'` で正常クエリ実行 | エラーログなし |

## 修正方針

`analysis_results.created_at` は存在しないカラム。
`updated_at`（実在・DIST-01 マイグレーション時に確認）に変更する。

変更は 1 行のみ（`tcg_distribution_svc.py:349`）。他カラム・他テーブルへの影響なし。

## 外部・過去事例

DIST-01（#3250）は migration で `tcg_distribution_targets` に `created_at`・`updated_at` 両方を定義。
`analysis_results` は別テーブルであり `created_at` を持たない（`updated_at` のみ）。
カラム名混同によるバグ。デプロイ後に初めて発覚（Phase 5-1 で検出）。

## 戻し方

`ar.updated_at` → `ar.created_at` に戻す（失敗する）のでなく、
`analysis_results` テーブルに `created_at` を追加する migration を起案（additive-only 原則）。
ただし本修正が正しい対応であり、revert 不要。
