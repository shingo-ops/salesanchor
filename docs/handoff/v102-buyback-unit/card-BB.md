# 実装カード BB: 単位も状態も書かれていない件を、買取価格で Sealed box / Case に決める（便BB）

設計者: Opus（2026-10-11）。PO 決定（原文）:
- 買取価格を最優先の物差しにする案に「y」
- 「単位も状態もない場合は sealed box,case,unsearched pack,searched pack のどれかである まず sealed boxとcaseの自動判定機能を作ってほしい、その後にpackを実装計画する」
根拠（手元・社外秘）: /tmp/CC報告ファイル/buyback-ref/（買取の表・比の分布）、unit-cascade/（3段の評価）、unit-autofix/（自動で直る件の原文判定: 14件中 当たり10・外れ0・分からない4、パックの比）。人の正解表 unit-truth/judged_all.csv。

## 0. 着手前の確認（読み取り。ずれたら NEEDS_DECISION）
0-1. v102 で「単位も状態も原文に書かれていない」を判定できる地点: backend/app/services/gemini_raw_copy_v102_product_first.py の find_unit_product_first（件の行に単位の別名が無いと None）と _resolve_condition / resolve_condition_v2 の basis（語で決まると R1〜R3:<語>、語が無いと R4:単位既定 / R4:単位既定:単位不明 / R4c / R5:パック既定）。file:line と、「単位の語も状態の語も無い」を確実に判定する条件（コード上の事実）を報告。
0-2. 買取の表: public.buyback_shop_products（product_id・product_type・last_seen_at・match_status）、public.buyback_price_logs（price_s・fetched_at）。種別 BOX・BOX_SHRINK の最新価格の商品別中央値の取り方（/tmp/CC報告ファイル/unit-autofix/rule.py の取り方に合わせる）。
0-3. 状態 Sealed box（CN0003）・Case（CN0001）の行と line_conditions.unit_id（Box・Case）を本番読み取りで確認。コードは code で引く（名前・id を直書きしない）。
0-4. 便UP（backend/app/services/v102_unit_price_check_svc.py）との順序: 本便で決めた単位・状態のあとに便UP の確認が走るか。

## 1. 変更（v102 経路だけ）
1-1. 対象: 件の行に単位の語も状態の語も無い件（0-1 の条件）で、商品が特定済み（product_id あり）、価格あり。
1-2. 物差し: 同じ商品の買取の BOX・BOX_SHRINK の最新価格（店ごとの最新）の中央値 m_bb。買取の行は「結び付き済み」かつ last_seen_at が設定の日数（例 unit_buyback_max_age_days=7）以内。m_bb が無ければ何もしない（今までどおり）。
1-3. 判定: r = 価格 ÷ m_bb。
  - 設定 unit_buyback_box_min（0.5）≤ r < 設定 unit_buyback_box_max（2）→ 状態 Sealed box・単位 Box
  - r ≥ 設定 unit_buyback_case_min（6）→ 状態 Case・単位 Case
  - それ以外 → 何もしない
  - 決めたら condition_basis に根拠（例 "BUYBACK:Sealed box r=1.07"）を残す。condition_unknown・unit_unknown の理由は、この件では外す（状態と単位が決まったため）。他の理由は残す。
1-4. 設定 4 key は public.tcg_distribution_settings（便UP と同じ表）。値はコードに書かない。1つでも無い・不正なら本便の判定はしない（何もしない・logger.warning）。投入 SQL は docs/handoff/v102-buyback-unit/data/（precheck・dryrun・commit・verify・rollback、$ と二重引用符なし、件数違いはゼロ除算で失敗）。
1-5. 相場の SQL は1ジョブ1回。失敗したら SAVEPOINT で確認だけ飛ばす（便UP と同じ形）。
1-6. パック（Unsearched pack・Searched pack）は本便では決めない（次の便で計画）。

## 2. テスト（合成で）
- 単位・状態の語が無い件で r=1.0 → Sealed box/Box、r=12 → Case/Case、r=3 → 変えない、r=0.1 → 変えない。
- 単位の語がある件・状態の語がある件 → 変えない。
- 買取が無い・古い → 変えない。設定が無い → 変えない。
- condition_unknown・unit_unknown が外れ、他の理由は残る。
- v102 以外の経路は変わらない。

## 3. 置き換え試験（マージ前の証拠・本番は読み取り）
- 本番の v102 現行行の全件を変更前と変更後で通し、変わる件の全件（job8・商品・価格・m_bb・r・前の単位/状態→後）。
- その全件を原文（件の行・前後・見出し）で読み、人として単位・状態を判定（判定を書いてから突き合わせ）。当たり・外れ・分からない。
- 変わる件以外の値の変化が0であること。便UP の付き方への影響（付く件が減る・増える）も全件。
- 停止条件: 外れが1件でもあれば全件を報告して止まる。

## 4. 手順
1. `bash scripts/new-worktree.sh release/v102-buyback-unit --claude` → preflight。Bash は単独の `cd <worktree> && …`。
2. 0 → 実装 → テスト → 置き換え試験 → ruff・pytest・npm run check:all。
3. commit（push しない）。このカードを docs/handoff/v102-buyback-unit/card-BB.md に置く（recon・design は設計者）。

## 停止条件
- 0 で前提が違う、v102 以外の経路を変えないとできない、外れが出た → NEEDS_DECISION。フックに止められたら言い換えず止まる。最終行 DONE / BLOCKED: / NEEDS_DECISION:。
