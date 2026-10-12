# design: 「人が確認済み」列に POルール一括修正分を含める

作成: 2026-10-06／状態: 設計確定（PO決定済み）・設計審査 APPROVE（同一AIの自己審査）
recon: `docs/handoff/condition-manual-po-rules/recon.md`／前便: `docs/handoff/condition-fallback-count/design.md`

## 目的（PO向け1行）
人（PO）のルールで状態を確定した371件が表のどの列にも出ない状態をなくし、「人が確認済み」に数える。

## 変更前 → 変更後
| 列 | 変更前 | 変更後 |
|---|---|---|
| 人が確認済み | basis = `MANUAL_CONDITION_REVIEW` のみ（本番0件） | basis が `MANUAL_CONDITION_REVIEW` または `MANUAL_RAW_REVIEW:PO_RULES` |
| 状態未解決・うち完全お手上げ | 変更なし | 変更なし |

## 実装（SSOT: `analysis_results.condition_basis` の現在値のみ。新テーブル・新カラムなし）
`backend/app/services/tcg_supplier_quality_svc.py`
- :19 `CONDITION_MANUAL_BASIS = "MANUAL_CONDITION_REVIEW"` を次に置換（前便と同じ正規表現方式・完全一致）:
```python
# 人が状態を確定した basis（画面レビュー: tcg_condition_review_svc.py:286 ／ PO許可の一括修正: item_corrections.corrected_by='codex:PO-authorized:20260916-1203'）。
CONDITION_MANUAL_PATTERN = r"^(MANUAL_CONDITION_REVIEW|MANUAL_RAW_REVIEW:PO_RULES)$"
```
- :52 `ar.condition_basis = :manual_basis` → `ar.condition_basis ~ :manual_pattern`
- :66 `"manual_basis": CONDITION_MANUAL_BASIS` → `"manual_pattern": CONDITION_MANUAL_PATTERN`
- docstring の conditionManual 行を新条件に更新
`backend/tests/test_tcg_supplier_quality.py`
- :246 の期待 params を `"manual_pattern": svc.CONDITION_MANUAL_PATTERN` に
- 追加: manual パターン一致 `MANUAL_CONDITION_REVIEW`・`MANUAL_RAW_REVIEW:PO_RULES`、不一致 `MANUAL_RAW_REVIEW:PO_RULES_X`・`X,MANUAL_CONDITION_REVIEW`・`R4:単位既定`・空
- 追加: fallback パターンが `MANUAL_RAW_REVIEW:PO_RULES` に不一致（排他の確認）

## 対象外
FE・i18n・API スキーマ（キー名 `condition_manual_reviewed_count` は不変）・migration・deploy.yml・本番スクリプト・他列の数え方。

## 代替案
| 案 | 不採用理由 |
|---|---|
| `= ANY(:list)` の配列バインド | 前便の正規表現方式と揃えず書式が分散する |
| item_corrections の corrected_by で判定 | 別テーブル JOIN が増え、basis（SSOT）と二重基準になる |
| 列を分けて表示 | PO 決定（y=同じ列に含める）と異なる |

## リスクと対処
| リスク | 対処 |
|---|---|
| 将来別名の一括修正 basis が増える | 定数1か所に集約＋テストで固定。追加時は本定数を更新 |
| 正規表現の部分一致で誤カウント | `^...$` の完全一致、不一致テストで固定 |

## 受入条件
| 基準 | 検証方法 |
|---|---|
| 1. 本番で「人が確認済み」の全行合計 = 照合SQL（`condition_basis IN ('MANUAL_CONDITION_REVIEW','MANUAL_RAW_REVIEW:PO_RULES')`、有効メッセージのみ）の合計 | 反映後に PO 実行の読み取りSQLと画面値を比較 |
| 2. 状態未解決・うち完全お手上げ・既存4列が変更前と同じ | 同上（前便 Q1 と比較） |
| 3. pytest 緑 | `cd backend && python3 -m pytest tests/test_tcg_supplier_quality.py -q --no-cov` |
| 4. 実 PostgreSQL での動作 | ローカル使い捨てDBへの投入は psql-write-guard で拒否（2026-10-06）のため省略。同一方式（`~ :bind` 正規表現）は前便でローカル PG16 実証済み。本変更は反映後に受入条件1の本番読み取り照合で実証する |

## 維持の仕組み
- 守り手: `backend/tests/test_tcg_supplier_quality.py` の manual パターン一致/不一致テスト（CI pytest）
- 所有: `backend/app/services/tcg_supplier_quality_svc.py` の定数 `CONDITION_MANUAL_PATTERN`

## 外部・過去事例の参照と我々への応用
- 外部事例: 不要。社内DBの既存カラムの集計条件を1つ広げるだけで、方式選定を伴わない。
- 過去事例: 前便 #3881 で「画面レビューだけが人の確定」と仮定し、本番実データ照合で一括修正371件が漏れていると判明 → 応用: 集計条件の確定前に本番 basis の全種類分布（読み取りSQL）を必ず取る。

## 設計審査（同一AIの自己審査）
APPROVE（2026-10-06）。変更は1ファイル3行＋テスト、UI/DB/デプロイ影響なし。未解決事項なし。

## 関連
- ADR-154、ADR-100、ADR-027、ADR-067、ADR-144（前便と同じ。UI 変更なし）
