# recon: 状態の価値順（condition value rank）

調査日: 2026-10-17（origin/main 15114e87 基準）。調査: Sonnet（読み取り）／確認: Opus。

## 既存 ADR の検索
- `git grep -i "condition\|状態" docs/adr/` と `docs/adr/FEATURE-INDEX.md` を確認。判定の順番（複数の状態語が当たったときの選び方）を決めた ADR は無い。
- 関連: ADR-1007（共用マスタの値は migration に書かず、記録した SQL で入れる）、ADR-1021（Bulk の状態。様式の前例）。

## 現在地（file:line）
- 状態の判定: `backend/app/services/tcg_analyzer_svc.py:809-909` `resolve_condition_v2`。
  - 主ループ `backend/app/services/tcg_analyzer_svc.py:852-861` は、並び順（priority 昇順 → app_kubun が長い順 → code 昇順）で最初に当たった行を返す。
  - R1 事前検査 :840-850、R4 単位既定 :863-871、R5 パック既定 :873-889、R4c 商品分類既定 :891-906（箱系で再帰呼び出し :902-905）。
- 読み込み: `backend/app/services/tcg_analyzer_svc.py:652-730` `load_condition_entries`。match_type・effect 列が無い DB では fallback の SELECT に切り替える（:682-699）。
- 適用区分: `backend/app/services/tcg_analyzer_svc.py:733-762` `app_kubun_matches`（空欄＝全適用、箱系と箱系大は別）。
- v102 の呼び出し: `backend/app/services/gemini_raw_copy_v102_product_first.py:571-587` `_resolve_condition`（呼び出し 2 か所）。
- 他の呼び出し元（変えない）: tcg_analyzer_svc.py の v6/shadow 経路、v10、tcg_unit_recovery_svc、tools/prompt_ab.py。
- 共通関数の不変を固定するテスト: `backend/tests/test_gemini_raw_copy_v102_product_first.py:423-429`。
- マスタ: `public.line_conditions`。`public.conditions` は列を明示した view で、列を足したら view の再作成が要る（前例 `migrations/20260925_010000_*` :52）。
- 反映の順番: `.github/workflows/deploy.yml` はアプリの入れ替え（backend :397、celery :414-419）が先、migration（:526-543 → `scripts/run_all_migrations.sh`）が後。新しいコードは列が無い DB でも動く必要がある。

## 本番の観測（読み取りのみ）
- v102 の現行行で、同じ群（箱）の状態語が 2 つ以上当たる行は少数（試算で結果が変わるのは 3 行）。群（箱とカートン等）をまたいで当たる行、対象外の状態と同時に当たる行は 0。
- 価値順に入らない状態: Empty box、FLAG_SINGLE、Error、Bulk、空箱 Case。

## 未確認
- なし（カートンの順は PO の明示の y が無い。値の SQL の前に再確認する）。
