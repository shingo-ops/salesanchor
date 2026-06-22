# design.md - W-2① 属性別成約率集計 API

**対象ADR**: ADR-138
**recon**: docs/handoff/w2-conversion-by-attribute/recon.md
**日付**: 2026-06-22
**担当**: Planner

## 外部・過去事例の参照と我々への応用

- 既存の `/analytics/channels` にある team/mine 集計パターンを踏襲し、read-only のまま属性別成約率を返す。
- 今回は新しいフロント実装、スコア化、順位付け、マイグレーションは入れない。
- 該当なし: 外部ライブラリ追加や、既存のユーザー操作フローを変える過去事例は不要。

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| /analytics/conversion-by-attribute が返る | `pytest -q backend/tests/test_analytics.py -k conversion_by_attribute --no-cov` |
| team/mine の scope 差が返る | `pytest -q backend/tests/test_analytics.py -k conversion_by_attribute --no-cov` |
| n / conversions / raw_rate / smoothed_rate / overall_rate が返る | `pytest -q backend/tests/test_analytics.py -k conversion_by_attribute --no-cov` |
| tenant_006 の RLS 実走で tenant 分離を確認する | `pytest -q backend/tests/test_analytics_conversion_by_attribute_rls.py --no-cov` |
| process-artifacts gate が通る | GitHub Actions の process-artifacts gate |

## 技術 How・KPI

- KPI: 成約率の属性別分布を 1 endpoint で read-only に返す。
- 技術選択: overall_rate をベースに `k=10` の shrink をかけて、n が小さい bucket の暴れを抑える。

## 弊害・トレードオフ

- 0-1 スケールで返すため、フロント表示で必要なら百分率変換が別途必要。
- 収縮は overall_rate への単純縮退なので、他軸の掛け合わせは行わない。

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | backend/app/routers/analytics.py に read-only 集計 endpoint を追加 | Generator |
| 2 | SQLite 契約テストと PG/RLS 実走テストを追加 | Generator |
| 3 | PR 本文に GO 記録と標準ワークフロー確認を記入 | Reviewer |

## 継続

- 完了後の監視: CI の process-artifacts gate と pytest 実行結果を確認する。
- 次フェーズへの引き継ぎ: W-2② 以降の順位付け / スコア化 / フロント表示に接続する。
