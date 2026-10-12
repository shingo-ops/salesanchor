# 実装カード SU: 状態の言葉で決まった状態の単位を優先する／分類「セット系」（便SU）

設計者: Opus（2026-10-11）。PO 決定（原文・要旨）:
- 「状態が決まっているのであれば自然と単位が決まる」（PO 案）→ 状態が原文の語（basis R1〜R3）で決まったら、その状態の単位を単位語より優先する。
- 「カテゴリに箱系、シングル系、ブックレット系と追加でセット系を足せば…セット系の単位なしの場合は単位をセットにする」「状態は記載がなければ sealed box」「正解が『セット』y」（440301 9種セットはセット系、正解=単位 Set・状態 Sealed box）。
根拠（手元・社外秘）: /tmp/CC報告ファイル/unit-residual5/round6/（e1.out 13件、d1.out 原文、c1.out 候補、a1〜a4 分類表）、round5/（v102pf.py・tas.py の写し・sim.py）。

## 0. 着手前の確認（読み取り。ずれたら NEEDS_DECISION）
0-1. origin/main の backend/app/services/gemini_raw_copy_v102_product_first.py の :47 PRODUCT_KUBUN_BOX、:58-62 定数、:99 product_kubun、:110-115 condition_unit、:496-505 _resolve_condition、:569-573 replace が下記の前提どおりか（行がずれていれば実物の行を報告して続行）。
0-2. resolve_product_first が _resolve_condition の basis（R1〜R3/R4…）を :569 の時点で参照できるか。
0-3. 単位 Set の行を名前でなく code で引けるか（line_units.code=UN0005・canonical Set・kubun 複合 を本番読み取りで確認）。既存コードの code 定数の作法（例 CONDITION_ERROR_CODE="CN0012"）に合わせる。
0-4. public.tcg_product_categories.id が identity/serial か（information_schema.columns の column_default / is_identity）。明示 id を書かない。
0-5. 便BB（backend/app/services/v102_buyback_unit_svc.py）の対象判定が商品の分類を見ているか。

## 1. 変更（v102 経路だけ。tcg_analyzer_svc.py の旧経路の 890/1270 行・tcg_work_comparison_svc.py は触らない）
1-1. 状態の単位を優先（gemini_raw_copy_v102_product_first.py の :569 付近）
  - 条件: 状態の basis が "R1"・"R2"・"R3" で始まる、かつ masters.condition_unit に状態の単位がある、かつ今の単位と違う、かつ 商品の分類がセット系ではない。
  - 動作: 単位を状態の単位にする（既存の from_condition の経路を使い、unit_basis に from_condition と理由 "state_word" を残す）。
  - 例: 6221d9c5「ペリ無し統一箱・パック右上…」→ Opened box（R3）→ Pack を Box に。「プレシャスコレクターボックス 10個@58,000円 検品のため開封済み」→ 個 を Box に。
1-2. 分類「セット系」
  - 定数 PRODUCT_KUBUN_SET = "セット系"（PRODUCT_KUBUN_BOX の隣）。
  - 状態: _resolve_condition の :499 の条件を「商品が箱系 または セット系」かつ単位区分が BOX_RECHECK_UNIT_KUBUNS のとき、に広げる（→ 語が無ければ R4 で Sealed box）。
  - 単位: 単位の語が無い（unit is None）かつ商品がセット系 → 単位 Set（code で引く）。状態の単位（Sealed box→Box）での置き換えより先に入れ、置き換えはしない。unit_basis に {"from_category":"セット系"} を残す。
  - 書かれた単位（BOX 等）があればそのまま。状態の語があれば書かれた状態（1-1 の単位優先はセット系では行わない）。
1-3. 便BB の対象からセット系の商品を外す（セット系は買取の箱の値段で Sealed box/Case に決めない）。0-5 の結果に合わせて最小の変更で。
1-4. 分類の表にセット系の行が無い（本番投入前）ときは何も変わらないこと。

## 2. テスト（合成で。既存の v102 product_first のテストの作法に合わせる）
- 1-1: R3 の Opened box＋単位語 パック → Box。R3＋個 → Box。R4（状態の語なし）＋セット → 変えない。状態の単位と同じ → 変えない。状態の単位が無い状態 → 変えない。
- 1-2: セット系＋単位語なし・状態語なし → Set／Sealed box。セット系＋「200セット」→ Set／Sealed box。セット系＋「50BOX」→ Box。セット系＋状態語（ペリ無し）→ 状態 Opened box・単位 Set のまま。箱系の既存の動き（単位なし→状態の単位）は不変。
- 1-3: セット系の商品は便BB の対象外。箱系は今までどおり。
- 分類の行が無い場合は全て今までどおり。

## 3. 置き換え試験（マージ前の証拠・本番は読み取り）
- 本番の v102 現行行の全件を変更前と変更後で通す（440301 は「セット系」に属したと仮定した場合と、仮定しない場合の2通り）。変わる件を全件列挙（id8・商品・価格・前→後の単位/状態・basis）。
- 期待: 仮定なし → 13件（round6/e1.out の 6221d9c5 と 個の12件）だけが Box に変わる。仮定あり → それに加えて 440301 の 326d28ec（完売〆・単位なし）が Box→Set、他の 440301 は不変（Set 8件は Set/Sealed box、7dded8ef「50BOX」は Box）。
- 期待と違う件が1件でもあれば全件を報告して止まる。便UP・便BB の付き方の変化も全件。

## 4. データ（コードのデプロイ後に Opus が投入。カードでは SQL を作るだけ）
docs/handoff/v102-unit-state-set/data/ に precheck・dryrun・commit・verify・rollback（$ と二重引用符なし、件数違いはゼロ除算で失敗、id を書かない）:
- tcg_product_categories に (code 'PC_SET', display_name 'Set', kubun_type 'セット系', is_active true, tenant_id NULL) を1行。code の重複は precheck で 0 を確認。
- products 440301（code PM0297 で引く）の product_category_id をその行に（前の値 1 を rollback 用に記録）。
- 他の商品は変えない（候補表は PO の y 待ち）。

## 5. 手順
1. `bash scripts/new-worktree.sh release/v102-unit-state-set --claude` → preflight。Bash は単独の `cd <worktree> && …`。
2. 0 → 実装 → テスト → 置き換え試験 → ruff・pytest（v102 関連と PG テスト）・npm run check:all（変わらなければ省略理由を書く）。
3. commit（push しない）。このカードを docs/handoff/v102-unit-state-set/card-SU.md に置く（recon・design は設計者が書く）。

## 停止条件
0 で前提が違う、v102 以外の経路を変えないとできない、置き換え試験で期待外 → NEEDS_DECISION。フックに止められたら言い換えず止まる。最終行 DONE / BLOCKED: / NEEDS_DECISION:。
