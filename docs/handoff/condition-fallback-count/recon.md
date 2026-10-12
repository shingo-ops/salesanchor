# recon: 解析精度管理「状態未解決」列

作成: 2026-09-27（設計セッション）

## 問題
管理画面 > LINE解析 > 解析精度管理の「状態未解決」列が、全仕入先で「集計準備中」と表示される。

## 原因

バックエンドが意図的に `None` を返している。

- `backend/app/services/tcg_supplier_quality_svc.py:60`
  ```python
  "condition_fallback_count": None,  # Q8実測不能 — GAS と同じく null 固定
  ```
- フロントは null を受け取ると「集計準備中」と表示するルール:
  `frontend/src/features/tcg-analysis-review/SupplierQualityList.tsx:63`
  ```ts
  return row.conditionFallbackCount !== null
    ? row.conditionFallbackCount
    : t("superAdmin.supplierQuality.conditionPending");
  ```

「GASと同じくnull固定」というコメントは古い前提。実際はSAアプリ内で条件判定しておりデータが存在する。

## 条件判定の仕組み（resolve_condition_v2）

ファイル: `backend/app/services/tcg_analyzer_svc.py:744-826`

AIが商品の状態を判定する6段階:

| 段階 | condition_basis の値 | 意味 |
|------|---------------------|------|
| 空箱チェック | `EMPTY_BOX:explicit` | 空箱と明示判定 |
| R1 pre-pass | （警告メモのみ、リターンしない） | 箱系で単品語を検出 |
| R2〜R4a メインループ | `R2:{kw}`, `R3:{kw}`, `R4:{kw}` | キーワードマッチで確定 |
| R4 単位既定 | `R4:単位既定` | KWなし・kubunから推測（箱系→Case等） |
| R5 パック既定 | `R5:パック既定` | パック系でKWなし |
| 最終フォールバック | `R4:単位既定:単位不明` | 全分岐非該当 → FLAG_SINGLE |

手動レビュー後: `MANUAL_CONDITION_REVIEW` に上書き
（`backend/app/services/tcg_condition_review_svc.py:219-296`）

### 追記（2026-09-30 設計審査で実物照合）
- 上書きは UPDATE で元の basis を消す: `backend/app/services/tcg_condition_review_svc.py:283-287`
  （`condition_basis='MANUAL_CONDITION_REVIEW'`）。元の値は `item_corrections.system_value` の JSON にのみ残る（:279-282）。
  → 「フォールバック件数から手動済みを除外」は現在値ベースでは常に「フォールバック件数」と同値。
- **basis には接頭辞が付く場合がある**: 箱系で単品語を検出すると `単品語あり・要確認(<kw>),` が前置される
  （`backend/app/services/tcg_analyzer_svc.py:815-825, 847, 852`）。
  例: `単品語あり・要確認(バラ),R4:単位既定`。→ 前方一致 `LIKE 'R4:単位既定%'` では取りこぼす。
- フォールバックの生成箇所（行番号は worktree release/condition-fallback-count 時点、origin/main 8cb3708fb 起点）:
  - `backend/app/services/tcg_analyzer_svc.py:853-859` … `[接頭辞]R4:単位既定`（箱系大→Case／箱系→Sealed box）
  - `backend/app/services/tcg_analyzer_svc.py:877` … `[接頭辞]R5:パック既定`（パック系）
  - `backend/app/services/tcg_analyzer_svc.py:880` … `[接頭辞]R4:単位既定:単位不明`（FLAG_SINGLE）
  - `backend/app/services/tcg_analyzer_svc.py:875` … `R3:MEMO:<kw>` はメモのキーワード一致＝確定扱い（フォールバックではない）
- `R4:単位既定:単位不明` の行は単位復旧処理で再計算され得る: `backend/app/services/tcg_unit_recovery_svc.py:404, 481, 944`。
  集計は現在値ベースなので、復旧後は自動的に件数から外れる。
- 表示側で basis を `MANUAL_CONDITION_REVIEW` とみなす箇所: `backend/app/services/tcg_condition_review_svc.py:175`
- 既存テスト: `backend/tests/test_tcg_supplier_quality.py`、`backend/tests/test_tcg_is_active_filter.py`
- API スキーマ: `backend/app/routers/tcg_supplier_quality.py:35-42`（:42 `condition_fallback_count: int | None`）
- FE: `frontend/src/features/tcg-analysis-review/supplierQuality.ts:8-10, 25, 34, 43`、
  `frontend/src/features/tcg-analysis-review/SupplierQualityList.tsx:14, 29, 62-63`、
  `frontend/src/locales/ja.json:2520`〜（`columns.conditionFallbackCount`="状態未解決（集計準備中）", `conditionPending`="集計準備中"）

## 集計に使えるDBカラム

テーブル: `public.analysis_results`
（定義: `migrations/20260921_110000_pipeline_tables_public.sql:215-283`）

| カラム | 型 | 用途 |
|--------|-----|------|
| `condition_id` | INTEGER NOT NULL | 判定された条件マスタID |
| `condition_canonical` | VARCHAR(100) | 正規化名（FLAG_SINGLE等） |
| `condition_basis` | VARCHAR(100) | 判定根拠（R2:美品, R4:単位既定 等） |

## 既存の集計ロジック（他カラムの参考）

`backend/app/services/tcg_supplier_quality_svc.py:29-63`

既に集計できている指標:
- `analysis_count`: `COUNT(ei.id)`
- `needs_review_count`: `pid_resolved`, `unit_resolved`, `exclusion` を使用
- `product_id_unresolved_count`: `NOT ar.pid_resolved`
- `unit_unresolved_count`: `NOT ar.unit_resolved`

同じパターンで `condition_basis` を使えば `condition_fallback_count` も集計可能。

## フロント側の準備状況

`frontend/src/features/tcg-analysis-review/supplierQuality.ts:18-26`

型定義は `conditionFallbackCount: number | null` で、null でなければ数値表示する仕組みが既にある。
A〜C（1カラム）ならフロント変更不要。D（複数カラム）なら列追加が必要。

## 関連ADR
- ADR-154: GAS→Python完全移植（resolve_condition_v2 の設計根拠）
- ADR-100: インジェスト・解析パイプライン全体方針

## 関連ハンドオフ
- `docs/handoff/parity03-supplier-quality-be/design.md` — 元の設計（null固定の経緯記載）
