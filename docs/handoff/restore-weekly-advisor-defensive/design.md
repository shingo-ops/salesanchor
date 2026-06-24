# Design: weekly_advisor_defensive 外科的復元

## KGI

`GET /analytics/weekly-advisor-defensive` が develop で 200 を返し、W-1「今やること」が再表示・動作すること。

## 変更内容

| ファイル | 種別 | 変更概要 |
|---------|------|---------|
| `backend/app/routers/analytics.py` | 追加のみ | `datetime` import 追加・WeeklyAdvisor モデル/ヘルパー/EP を末尾に追記 |
| `backend/tests/test_analytics.py` | 追加のみ | `TestWeeklyAdvisorDefensive` クラス（2テスト）を末尾に追記 |
| `docs/handoff/restore-weekly-advisor-defensive/recon.md` | 追加 | 現在地把握 |
| `docs/handoff/restore-weekly-advisor-defensive/design.md` | 追加 | 本ファイル |

**diff は追加のみ・意図外削除ゼロ**（削除は `from datetime import date, timedelta` → `date, datetime, timedelta` への import 行置換 1行のみ）。

## 復元しない（意図的）

`customer_orders_report` / `revenue_segments_report` は全リポジトリで参照ゼロの死蔵と確認済み。PO 決定により削除のまま維持。

## KPI 検証テーブル

| 基準 | 検証方法 |
|------|---------|
| EP が 200 を返す（データなし時） | `test_analytics.py::TestWeeklyAdvisorDefensive::test_weekly_advisor_defensive_empty` — `actions==[]`, `period=="3m"` |
| score 降順ソート | `test_analytics.py::test_weekly_advisor_defensive_ranking_and_scope` — `actions == sorted(..., key=score, reverse=True)` |
| scope=mine が効く | 同上 — `other_co_id not in company_ids` |
| churn_risk が最上位 | 同上 — `actions[0]["type"] == "churn_risk"` |
| 3種 reorder/churn_risk/comm_low が揃う | 同上 — `types` に全3種あり |
| lead_id が正しく紐付く | 同上 — `reorder_co` と `churn_co` に lead_id あり、`comm_co` は None |
| churn_risk と comm_low が排他 | 同上 — `churn_co_id not in comm_ids` |

## ADR 参照

- ADR-072: テナントスキーマ分離・RLS ポリシー（`app.tenant_id` セッション変数）
- recon: `docs/handoff/restore-weekly-advisor-defensive/recon.md`

## 外部・過去事例の参照と我々への応用

**発端が LLM コードジェネレータの意図外削除**という典型的パターン：大規模ファイル（2,400行）への追加タスクで、モデルがファイル全体を「最適化」しながら再生成し、既存エンドポイントを消した。

対策（本PR・今後）：
- Generator へのタスクは「追加のみ」と明示し、diff 確認を CI ゲートではなく実装直後に行う
- analytics.py のような大規模ファイルへの変更は、PR 単位で diff 純増を確認する運用とする

## 触らない範囲

- `priority_prospects`（`backend/app/routers/analytics.py:1779-1893`）
- `_fetch_attribute_conversion_axis` / `/conversion-by-attribute`
- `channels_summary` / `compute_prospect_rank` / `priority_score`
- `migrations/` / `frontend/` / `scripts/`
