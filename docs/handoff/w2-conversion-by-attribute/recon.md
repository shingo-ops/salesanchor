# recon - W-2① 属性別成約率集計 API

**仕事名**: W-2① 属性別成約率集計 API
**日付**: 2026-06-22
**対象ADR**: ADR-138
**担当**: architect

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/routers/analytics.py:1539-1678` | `/analytics/conversion-by-attribute` の response model, 5軸集計, k=10 shrink, scope team/mine を追加した |
| `backend/tests/test_analytics.py:1138-1213` | SQLite 契約テストで empty / team / mine / shrink / n を検証した |
| `backend/tests/test_analytics_conversion_by_attribute_rls.py:36-318` | tenant_006 の PG/RLS 実走テストで tenant 分離と scope 差を検証する |

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | tenant_006 の解決方法 | information_schema.schemata で schema 存在確認し、tenant_id=6 として扱う | ✅ 解消済み |
| 2 | 収縮係数の初期値 | k=10 の定数で固定 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み / または「該当なし」

## 補足

- read-only endpoint であり migration / データ変更は行わない。
- 既存 `/analytics/channels` と同様に scope=team/mine の集計ロジックを踏襲する。
