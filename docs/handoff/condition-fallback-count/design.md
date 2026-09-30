# design: 解析精度管理「状態未解決」列の実数値化

作成: 2026-09-27（設計セッション）／確定: 2026-09-30
状態: **設計確定（PO定義選択済み）・設計審査 APPROVE（同一AIの自己審査）・実装未着手（PO実装承認待ち）**
起点: origin/main `8cb3708fb`／ブランチ `release/condition-fallback-count`

## 目的（PO向け1行）
解析精度管理の表で、仕入先ごとに「AIが状態を決めきれず人の確認が要る件数」と、その内訳を数字で見えるようにする。

## PO決定事項
- 2026-09-30 PO選択「3列で確定」: 状態未解決／うち完全お手上げ／人が確認済み（案D'）
- 旧案 A〜D のうち C・D は審査で不成立と判明（下記「設計審査」）。

## 変更前 → 変更後（利用者に見える変化）
| 列 | 変更前 | 変更後 |
|---|---|---|
| 状態未解決（既存） | 全行「集計準備中」 | 件数（推測＋完全お手上げ、人が未確認のもの） |
| うち完全お手上げ（新） | なし | 件数（状態語も単位区分もなく FLAG_SINGLE を仮置きしたもの） |
| 人が確認済み（新） | なし | 件数（手動の状態レビューで確定・修正されたもの） |

## 数え方（SSOT: `analysis_results.condition_basis` の現在値）
basis には `単品語あり・要確認(<kw>),` の接頭辞が付く場合があるため、末尾一致の正規表現で数える（recon 追記参照）。

| 出力キー | PostgreSQL 条件 |
|---|---|
| `condition_fallback_count` | `ar.condition_basis ~ '(^|,)(R4:単位既定(:単位不明)?|R5:パック既定)$'` |
| `condition_give_up_count` | `ar.condition_basis ~ '(^|,)R4:単位既定:単位不明$'` |
| `condition_manual_reviewed_count` | `ar.condition_basis = 'MANUAL_CONDITION_REVIEW'` |

不変条件: `condition_give_up_count ≤ condition_fallback_count`。`condition_fallback_count` と `condition_manual_reviewed_count` は排他（同じ行は両方に入らない）。

## 対象外（触らない）
- 判定ロジック（`tcg_analyzer_svc.py`）・手動レビュー（`tcg_condition_review_svc.py`）・単位復旧（`tcg_unit_recovery_svc.py`）
- DB スキーマ（migration なし）・deploy.yml・本番スクリプト
- 他の既存列（解析／要確認／商品ID未解決／単位未解決）の数え方
- `fetch_supplier_source`（`tcg_supplier_quality_svc.py:66-104`）

## 影響範囲（呼び出し元走査済み・recon 追記参照）
- BE: `backend/app/services/tcg_supplier_quality_svc.py:29-63`、`backend/app/routers/tcg_supplier_quality.py:35-42`
- FE: `frontend/src/features/tcg-analysis-review/supplierQuality.ts`、`SupplierQualityList.tsx`、
  `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:45, 428-451`（同じ型を使うため追随が必要）
- i18n: `frontend/src/locales/ja.json` / `en.json` の `superAdmin.supplierQuality`（:2520〜）
- テスト: `backend/tests/test_tcg_supplier_quality.py`

## 代替案と選択理由
| 案 | 不採用理由 |
|---|---|
| 前方一致 `LIKE 'R4:単位既定%'` | 接頭辞付き basis を取りこぼす（`tcg_analyzer_svc.py:852`） |
| 旧案C（A − 手動済み） | 手動レビューで basis が上書きされるため A と常に同値（`tcg_condition_review_svc.py:286`） |
| 手動前の元 basis を `item_corrections` から復元 | JSON 解析が必要で重く、PO の目的（今の残件と内訳）に不要 |

## リスクと対処
| リスク | 対処 |
|---|---|
| basis の書式が将来変わり件数が0に落ちる | 正規表現を定数化し、書式の生成元（`tcg_analyzer_svc.py:853,877,880`）を定数コメントで指す。pytest で代表 basis の一致/不一致を固定 |
| SQLite テストでは正規表現 SQL が動かない | SQL 実行はモック。正規表現の意味は Python `re` で同一パターンを検証＋本番値との手動照合（受入条件4） |
| `AnalysisDashboardPanel.tsx` は本店（~/salesanchor）で別作業の未保存変更あり | worktree は origin/main 起点で独立。変更は :428-451 のマッピング2行追加のみに限定し、衝突時は停止報告 |

## 受入条件
| 基準 | 検証方法 |
|---|---|
| 1. 「状態未解決」列に「集計準備中」が出ず数値が出る | 本番画面（管理画面 > LINE解析 > 解析精度管理）で全行目視 |
| 2. 「うち完全お手上げ」「人が確認済み」列が表示される（ja/en とも） | 本番画面目視＋ `node` による ja/en キー一致チェック（既存CI） |
| 3. 全行で お手上げ ≤ 状態未解決 | 本番画面または API 応答で全行確認 |
| 4. 1仕入先以上で画面の3値 = SQL 直叩きの3値 | 本節末の照合SQLを本番 DB（読み取りのみ）で実行し画面と比較 |
| 5. 既存4列の値が変更前と同じ | デプロイ前後で API 応答の既存4キーを同一仕入先で比較 |
| 6. pytest 緑（代表 basis の分類テスト含む） | `cd backend && pytest tests/test_tcg_supplier_quality.py` |

照合SQL（読み取りのみ）:
```sql
SELECT ps.supplier_code,
  COUNT(*) FILTER (WHERE ar.condition_basis ~ '(^|,)(R4:単位既定(:単位不明)?|R5:パック既定)$') AS fallback,
  COUNT(*) FILTER (WHERE ar.condition_basis ~ '(^|,)R4:単位既定:単位不明$') AS give_up,
  COUNT(*) FILTER (WHERE ar.condition_basis = 'MANUAL_CONDITION_REVIEW') AS manual
FROM public.source_messages sm
JOIN public.supplier_channels sc ON sc.id = sm.supplier_channel_id
LEFT JOIN public.suppliers ps ON ps.id = sc.supplier_id
JOIN public.extraction_jobs ej ON ej.source_message_id = sm.id
JOIN public.extraction_items ei ON ei.extraction_job_id = ej.id
JOIN public.analysis_results ar ON ar.extraction_item_id = ei.id
WHERE sm.is_active = TRUE
GROUP BY ps.supplier_code ORDER BY ps.supplier_code;
```

## 維持の仕組み
- 書式の変更検知: pytest の basis 分類テスト（代表値: 接頭辞あり/なし、R3:MEMO、R4:<kw>、MANUAL）
- 所有: 解析精度管理の BE サービス（`tcg_supplier_quality_svc.py`）に正規表現定数を集約

## 外部事例
不要: 社内DBの既存カラムを数えるだけの集計置換で、外部の方式選定を伴わないため。

## 設計審査（Architect・同一AIの自己審査）
判定: **APPROVE**（2026-09-30）
- 根拠: 変更箇所は file:line で特定済み、migration/deploy 変更なし、受入条件は全て○×判定可能。
- 修正済みの指摘: 旧案C/Dの不成立、前方一致の取りこぼし。
- 未解決事項: なし（実装承認のみ PO 待ち）。

## 関連
- recon: `docs/handoff/condition-fallback-count/recon.md`
- 実装カード: `docs/handoff/condition-fallback-count/card.md`
- 元の設計: `docs/handoff/parity03-supplier-quality-be/design.md`
- 台帳: `.claude-pipeline/active-work.d/release-condition-fallback-count.md`
- ADR-154（条件判定ロジック）、ADR-100（パイプライン全体）、ADR-027（i18n）
