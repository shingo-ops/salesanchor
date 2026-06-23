# design — trackb-order-based-conversion

**仕事名**: trackb-order-based-conversion  
**日付**: 2026-06-23  
**対象ADR**: ADR-142  
**recon**: docs/handoff/trackb-order-based-conversion/recon.md  
**担当**: planner

## 外部・過去事例の参照と我々への応用

- ADR-094 / ADR-107 / ADR-138 / ADR-139 の「成約=商談」系表現は、ADR-142 で受注ベースに上書き済み。今回の変更もその正典に従う。
- `docs/handoff/deal-removal-track-a/recon.md` と `docs/handoff/deal-removal-track-a/design.md` は、商談ボードの可視参照外しを別トラックで扱う前例として参照する。

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| conversion_rate が order ベースで算出される | `pytest -q backend/tests/test_analytics_conversion_by_attribute_rls.py --no-cov` |
| 1 lead 複数 company でも成約が二重計上されない | `pytest -q backend/tests/test_analytics_conversion_by_attribute_rls.py --no-cov` |
| company 無し lead は成約なし | `pytest -q backend/tests/test_analytics_conversion_by_attribute_rls.py --no-cov` |
| `pytest-run-internal` が green | GitHub Actions |
| `pytest (SQLite + PostgreSQL RLS)` が green | GitHub Actions |
| process-artifacts gate が green | GitHub Actions |

## 技術 How・KPI

- KPI: 受注ベースの成約率が dashboard / analytics / goals で同じ意味になる。
- 技術選択: 既存列 join と `EXISTS` / `DISTINCT` で重複を抑え、migration を不要にする。

## 弊害・トレードオフ

- `converted_deal_id` は温存するため、商談化と成約を混同しないよう命名とテストで分離する。
- order/invoice に分解したことで、KPI の再ポイント箇所が複数ファイルにまたがる。

## 計画票

| ステップ | 内容 | 担当 |
|---|---|---|
| 1 | `backend/app/routers/dashboard.py`, `analytics.py`, `goals.py`, `priority_scoring.py` を受注ベースに固定 | Generator |
| 2 | tenant_006 の PG/RLS 実走テストで実値を確認 | Generator |
| 3 | PR 本文の `### 標準ワークフロー確認` と `### GO記録` を更新 | Reviewer |

## 継続

- 完了後の監視: process-artifacts gate と pytest RLS 実走結果を確認する。
- 次フェーズへの引き継ぎ: 商談ボード去就や deal 撤去は別トラックで扱う。
