# design: 状態「Bulk」の新設（便1）

recon: docs/handoff/g28-bulk-price/recon.md（§番号で参照）。ADR: docs/adr/ADR-1021-bulk-condition-state.md（Proposed）。関連 ADR: ADR-1007・ADR-1014・ADR-1019・ADR-027・ADR-1015。
PO 承認: 2026-10-16「バルク商品の状態として新しく『バルク』を作り配信に出す」y、KGI と実装開始 y。

## ADR-1015 の区分
**A（PO の判断を待つ区分）**。理由: .sql を含む、ADR を触る、新機能（今は無い状態を作る）。PO 承認は上記のとおり 10/16 に出ている。マージは PO、危険パス（migrations 等）は触らない。

## 目的と KGI
|基準|検証方法|
|---|---|
|B1: 反映後に v102 で解析されたバルク系の行のうち、状態語が無いのに Error になる件数 = 0|反映後に本番 SELECT（Opus）。単体テスト (a) が分岐の正しさを担保|
|B2: バルク系以外の行で状態が変わる件数 = 0|単体テスト (b)(c)（バルク系の状態語あり・シングル系・箱系・セット系・商品なしが従来と同じ）＋反映前後の比較（Opus）|
|B3: バルク系で状態語が無く Bulk になった行が、配信の状態条件を通る|配信 SQL（tcg_distribution_svc.py:236-239 の条件）で確認（Opus）。単体テスト (d) はマスタ行が他の block に当たらないことを担保|

## 変更前後
- gemini_raw_copy_v102_product_first.py
  - 前: `_resolve_condition` の最後（recon §2 :571-573）は resolve_condition_v2 の後、無条件に `_undecided_condition`。
  - 後: その直前に分岐を1つ。`product_kubun == PRODUCT_KUBUN_BULK` かつ Bulk 行がマスタにあり、かつ `cond == FLAG_SINGLE` かつ `BASIS_UNIT_UNKNOWN in basis` なら `(Bulk の canonical, "R6:バルク既定", [])` を返す。定数 `PRODUCT_KUBUN_BULK = "バルク系"`（:47-48 付近）、`CONDITION_BULK_CODE = "CN0014"`、`BASIS_BULK_DEFAULT = "R6:バルク既定"` を追加。Bulk の名前は code で masters から引く（Error と同じ流儀）。
  - マスタに CN0014 が無ければ分岐に入らず、従来どおり Error（安全策。Opus 2026-10-16 採用）。
- tcg_result_order.py: RESULT_CONDITION_ORDER の末尾に "Bulk"。
  - **カードの文言との違い**: カードは「FLAG_SINGLE と同じ並び」だが、FLAG_SINGLE は表に載っておらず ELSE（recon §2 :25）で最後尾になる。Bulk は配信できる状態なので表に載せ、表に無い値（FLAG_SINGLE・Error）より前に並べる。Opus 2026-10-16 判断どおり。
- マスタ行: data/dry_run.sql → commit.sql → verify.sql（戻し rollback.sql）。値は ADR-1021 §What 2。priority=10 の根拠は、既存 OUTPUT 行の最大値が10（recon §3）で、search_kw が空のため判定順に影響せず末尾に置くのが最も安全なため。.sql は .gitignore の対象なので前例どおり git add -f で追跡する。

## 触らない範囲
価格・数量・note・price_basis（便2）／配信 SQL／frontend／GAS／migrations（マスタはデータ SQL）／v9 の行。

## 外部事例
不要。社内の状態マスタに1行足す変更で、外部に比べる対象が無い（前例は社内の CN0012 Error、docs/handoff/v102-prod-switch/data/conditions/）。

## 維持の仕組み
- 単体テスト: (a) バルク系で状態語なし → Bulk / R6、(b) バルク系で PSA 等 → 従来どおり、(c) シングル系・箱系・セット系・商品なし → 従来どおり、(d) Bulk のマスタ行が search_kw 空の KEYWORD でどの block にも当たらない。CI で毎回走る。
- 注意（REVIEW_V3）: 配信の48時間条件（max_age_hours）を外す・延ばすときは v9 のバルク行を再確認する（v9 の FLAG_SINGLE 59・Sealed box 35 が候補に戻る）。

## 戻し方
1. コードの PR を revert してデプロイ。2. Bulk で保存された行を reanalyze_v102_job でやり直す（data/rollback.sql の ROWS_STILL_BULK が 0 になること）。3. rollback.sql でマスタ行を is_active=false。この順。

## 実行の分担
本番のマスタ行の投入（DRY-RUN → COMMIT）は Opus。担当は実行しない。SQL の構文の試走は省略（Opus 判断。Opus が本番 DRY-RUN で確かめる）。
