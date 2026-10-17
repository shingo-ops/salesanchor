# design: 状態「Bulk」の新設（便1）

recon: docs/handoff/g28-bulk-price/recon.md（§番号で参照）。ADR: docs/adr/ADR-1021-bulk-condition-state.md（Proposed）。関連 ADR: ADR-1007・ADR-1014・ADR-1019・ADR-027・ADR-1015。
PO 承認: 2026-10-16「バルク商品の状態として新しく『バルク』を作り配信に出す」y、KGI と実装開始 y。

## ADR-1015 の区分
**A（PO の判断を待つ区分）**。理由: .sql を含む、ADR を触る、新機能（今は無い状態を作る）。PO 承認は上記のとおり 10/16 に出ている。マージは PO の常時委譲により Opus、危険パス（migrations 等）は触らない。

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

## 外部・過去事例の参照と我々への応用
- 外部事例: 不要。社内の状態マスタに1行足す変更で、外部に比べる対象が無い。
- 過去事例: 状態「Error」(CN0012) の新設（docs/handoff/v102-prod-switch/card-ER.md、data/conditions/）→ 名前を code でマスタから引く流儀、DRY-RUN→COMMIT→verify のデータ SQL、migration でデータを入れない（ADR-1007）を同じ形で踏襲する。
- 過去事例: 箱系・セット系の既定（PRODUCT_KUBUNS_DEFAULTING_TO_BOX、docs/handoff/condition-box-by-product-category/）→ 商品区分で状態の既定を分ける前例。今回は箱扱いにせず（バラのカードを Sealed box にしないため）別の状態を返す。

## 維持の仕組み
- 守り手: .github/workflows/backend-ci.yml（下の単体テスト (a)〜(d) と並び順テストを PR ごとに実行）
- 守り手: Opus（便2 着手前の再測定と、配信の期間条件を変える PR の審査で v9 バルク行を再確認）
- 単体テスト: (a) バルク系で状態語なし → Bulk / R6、(b) バルク系で PSA 等 → 従来どおり、(c) シングル系・箱系・セット系・商品なし → 従来どおり、(d) Bulk のマスタ行が search_kw 空の KEYWORD でどの block にも当たらない。CI で毎回走る。
- 注意（REVIEW_V3）: 配信の48時間条件（max_age_hours）を外す・延ばすときは v9 のバルク行を再確認する（v9 の FLAG_SINGLE 59・Sealed box 35 が候補に戻る）。

## 戻し方
1. コードの PR を revert してデプロイ。2. Bulk で保存された行を reanalyze_v102_job でやり直す（data/rollback.sql の ROWS_STILL_BULK が 0 になること）。3. rollback.sql でマスタ行を is_active=false。この順。

## 実行の分担
本番のマスタ行の投入（DRY-RUN → COMMIT）は Opus。担当は実行しない。SQL の構文の試走は省略（Opus 判断。Opus が本番 DRY-RUN で確かめる）。

---

# design: バルク系の価格を1枚単価に（便2）

recon: docs/handoff/g28-bulk-price/recon.md「便2」。ADR: docs/adr/ADR-1021-bulk-condition-state.md「便2 価格の決まり」。関連 ADR: ADR-1007・ADR-1015・ADR-027・ADR-144。

> 追記（ADR-1027）: set の換算は ADR-1027 で置き換え（piece・review はそのまま）。
PO 承認: 2026-10-16 KGI（価格は1枚の値段・まとめ売りは備考「N枚セット単位（1セットX円）」・決まらない行は配信しない・バルク以外は変えない・2回に分けて反映）と、PRマージ・デプロイまでの完走。

## ADR-1015 の区分
**A**。理由: .sql（理由コード行のデータ変更）を含む・ADR を触る。マージ・反映は Opus（PO 常時委譲）。

## 目的と KGI
|基準|検証方法|
|---|---|
|K1: 反映後の配信バルク行の価格が全件「1枚の値段」で、まとめ売りは備考に「N枚セット単位（1セットX円）」|反映後の配信行 SQL で全件を原文と照合（Opus）。単体テスト backend/tests/test_v102_bulk_price.py が set / piece / 要確認の各形を担保|
|K2: bulk_price_basis_unknown が付いた行の配信 = 0|配信条件 tcg_distribution_svc.py:348 の needs_review。単体テストで理由が付くこと・NON_ACKABLE を確認、反映後に本番 SELECT（Opus）|
|K3: バルク系以外の行の値の変化 = 0、既存試験すべて緑|単体テスト（バルク以外・product_category 無し・商品なしは values と完全一致）、再解析前後の比較（Opus）、backend 全試験|
|規則の移植が検証用の規則と同じ|retest の34行を新モジュールで回し、判定・N・単価・数量・備考が全件一致（リポジトリ外で実行。結果 bin2_impl/port_check.txt）|

## 変更前後
- backend/app/services/v102_bulk_price_svc.py（新規）: 規則の移植と公開関数 `convert(block, price, qty) -> BulkPrice`。前: 無い。後: piece / set / review を返す純関数。
- backend/app/services/line_analysis_v102_svc.py
  - 前: `_write_results` は `_analysis_values` の値をそのまま人の手直し→買取単位→…へ渡す（:952-957）。`_inherit_price(session, job, row, values)`（:966）。
  - 後: :952 の直後に `_apply_bulk_price`（バルク系かつ商品が決まった行だけ換算・要確認）。人の手直しの後で `_without_bulk_reason_if_human_priced`（人が価格か数量を直した行は理由を外す）。`_inherit_price` に `is_bulk`（既定 False）を足し、真なら最初に return。`_write_results` に raw_text（既定 None）、run_v102_analysis の SELECT に line_start・line_end。定数 REASON_BULK_PRICE_BASIS_UNKNOWN。
- backend/app/services/review_reason_codes_svc.py:17: NON_ACKABLE に新理由を追加。
- docs/handoff/v102-prod-switch/data/review_reason_codes/: seed_20261016_bulk_price_basis_unknown.sql と bp_dryrun / bp_commit / bp_verify / bp_rollback.sql、README.md に1節。.sql は .gitignore の対象なので前例どおり git add -f。
- frontend/src/locales/ja.json・en.json の reviewReason に bulk_price_basis_unknown。backend/app/data/review_reason_labels_ja.json は sync_review_reason_labels で再生成。.ts/.tsx は変えない。
- backend/tests/test_review_reason_codes_consistency.py: `_code_side_constants` に新定数。

## 触らない範囲
配信 SQL・frontend の .ts/.tsx・GAS・migrations・v9 以前の行・バルク系以外の値・`_buyback_units` と単価チェックの中身（換算後の値をそのまま見る）・sim の規則の中身（挙動を変えずに移植）。

## 外部・過去事例の参照と我々への応用
- 外部事例: 不要。自社の投稿書式（まとめ売りの書き方）を読む規則で、外部に比べる対象が無い。規則は自社の正解表（検証用の別データ）で検証済み。
- 過去事例: 便UP（単位と価格が相場と合わない）の理由コード追加（docs/handoff/v102-prod-switch/data/review_reason_codes/up_*.sql）→ データ SQL の型・3点セット試験の流儀を踏襲。

## 維持の仕組み
- 守り手: .github/workflows/backend-ci.yml（backend/tests/test_v102_bulk_price.py ほか全試験を PR ごとに実行）。
- 守り手: backend/tests/test_review_reason_codes_consistency.py（コード定数・seed SQL・ja/en.json の3点が揃わないと落ちる）。
- 守り手: Opus（反映後の K1 全件照合と7日間の照合を継続課題として記録）。

## 戻し方
revert PR → 同じ job を reanalyze_v102_job で再解析 → CN0014 を is_active=false（この順）。理由コードの行は残して害がない（bp_rollback.sql は戻すときだけ）。

## 実行の分担
本番の理由コード行の投入（bp_dryrun → bp_commit → bp_verify）・CN0014 の有効化・再解析は Opus。担当は実行しない。
