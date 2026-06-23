# Design: /analytics/priority-prospects PG/RLS 実走証明

## KGI

`GET /analytics/priority-prospects?scope=mine` が PostgreSQL + RLS 環境下で
全要件を満たすことを CI 上で実証する（PG/RLS テスト GREEN）。

## 変更内容

| ファイル | 種別 | 変更概要 |
|---------|------|---------|
| `backend/tests/test_priority_prospects_pg_rls.py` | 追加 | rls_bootstrap 使用の PG/RLS 実走テスト |
| `docs/handoff/analytics-priority-prospects/recon.md` | 追加 | 現在地把握 |
| `docs/handoff/analytics-priority-prospects/design.md` | 追加 | 本ファイル |

**analytics.py は変更なし**（エンドポイントは #2452/#2455 で既に正しく実装済み）。

## KPI 検証テーブル

| 基準 | 検証方法 |
|------|---------|
| ease_pct = 該当軸 smoothed_rate 平均 / 欠軸除外 | `test_priority_prospects_pg_rls.py:116-122` — 全 item で `sum(b["smoothed_rate"])/len(axes) * 100 ≈ ease_pct` |
| null 金額 → 中央値補完 + "monthly_forecast_unset" フラグ | `test_priority_prospects_pg_rls.py:128-136` — Lead-C の `monthly_forecast == 200.0` かつ flag 確認 |
| rank_score = ease_pct × monthly_forecast | `test_priority_prospects_pg_rls.py:123-127` — 全 item で計算値と一致 |
| rank_score 降順ソート | `test_priority_prospects_pg_rls.py:108-113` — `sorted(..., key=(-rank_score, lead_id))` と一致 |
| low_sample フラグ（n < 10） | `test_priority_prospects_pg_rls.py:138-143` — 全 item で `:low_sample` suffix フラグ存在 |
| テナント分離（RLS） | `test_priority_prospects_pg_rls.py:146-188` — tenant_998 スキーマのリードが tenant_007 セッションから COUNT=0 |
| scope=mine | `test_priority_prospects_pg_rls.py:100-106` — 別ユーザー Lead-D が返らない |

## ADR 参照

- ADR-072: テナントスキーマ分離・RLS ポリシー（`app.tenant_id` セッション変数）
- ADR-027: UI 文字列 i18n（本 PR は backend-only のため対象外）

## 外部事例

Bayesian shrinkage (James-Stein 縮退): 小サンプルの変換率推定で全体平均へ縮退させる手法。
Cohen (1988) の「サンプル n < 30 は信頼区間が広い」に対応。k=10 のパラメータは
`ATTRIBUTE_CONVERSION_SHRINK_K`（`backend/app/routers/analytics.py:959`）で管理。

## 触らない範囲

- `backend/app/routers/analytics.py`（変更なし）
- `frontend/`（Track B 分離方針：frontend は別 PR）
- `migrations/`（スキーマ変更なし）
