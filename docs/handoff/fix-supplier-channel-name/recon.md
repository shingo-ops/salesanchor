# recon — fix-supplier-channel-name

**仕事名**: fix-supplier-channel-name  
**日付**: 2026-09-23  
**対象ADR**: ADR-138  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/services/tcg_analysis_dashboard_svc.py:375` | `sc.name` → `sc.channel` に修正が必要 |
| `backend/app/services/tcg_analysis_dashboard_svc.py:407` | GROUP BY/ORDER BY の `sc.name` → `sc.channel` に修正が必要 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | `supplier_channels` テーブルのカラム名 | 本番DB確認: `information_schema.columns` | ✅ 解消済み（`channel` が正しいカラム名） |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

PR #3711 デプロイ後に `get_supplier_pipeline()` テストで発覚。
本番DBの `public.supplier_channels` に `name` カラムは存在せず、正しいカラムは `channel`。
#3710 で初回導入されたコードに `name` が誤記されていた。
#3711 で先行していた `source_message_id` エラーが修正されたことで `name` エラーが顕在化した。
