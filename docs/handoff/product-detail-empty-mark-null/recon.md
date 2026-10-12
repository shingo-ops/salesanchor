# recon: 商品詳細の保存で空の mark・english_title が '' になる件

実測時の origin/main: 85115283e

## 事実

| 引用先 | 確認内容 |
|-------|---------|
| backend/app/routers/tcg_product_import.py:280-281 | ProductDetailUpdate の english_title・mark は str（null 不可）。型は変えない |
| backend/app/services/tcg_product_detail_svc.py:175 | UPDATE は name_en=:english_title, mark=:mark をリクエストの値のまま書く（空なら ''） |
| backend/app/services/tcg_product_master_svc.py:418-419 | 新規作成は mark.strip() or None / english_title.strip() or None（空は NULL） |
| backend/app/services/tcg_product_detail_svc.py:121-124 | before はスナップショット（row_to_json）で NULL は null のまま。revision もスナップショットから計算 |
| backend/app/services/tcg_product_detail_svc.py:196-201 | audit_log の old/new は before/after のスナップショット |

## 変更前後の比較（audit_log）

- before が NULL の商品を空欄のまま保存: 変更前は NULL→'' の差が audit に出ていた。変更後は NULL→NULL で差が出ない
- before が '' の旧データを保存: '' → NULL の差が1回だけ出る（以後は出ない）。これは仕様として許容するかを設計者が判断
- 外部事例: 該当なし（既存の保存経路の値の正規化のみ）
