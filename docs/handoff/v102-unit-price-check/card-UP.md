# 実装カード UP: 単位と価格が相場と合わない件を要確認にする（確認役・便UP）

設計者: Opus（2026-10-11）。PO 決定（原文）:
- 「ケースとシュリンク付きの価格は少なく見積もっても5倍以上開きが出る、パックに関しても同様にシュリンク付きより5割は安くなる」
- 最終案（相場は v102 の行だけ・別々の投稿3つ以上・相場の3倍以上ずれて別単位の相場の方が近い時だけ要確認・単位は書き換えない）に「y」
- 「推測は禁止…確立したなら進める」
根拠（手元・社外秘）: /tmp/CC報告ファイル/price-unit-backtest/、price-unit-gap/（exceptions 含む）、unit-truth/（人の正解308件）、box-median-check/（v102 70商品・207行）、pack-products/。

## 0. 着手前の確認（読み取り。ずれたら NEEDS_DECISION）
0-1. v102 の保存の流れ: backend/app/services/line_analysis_v102_svc.py の _write_results・_analysis_values（v102 の行の値と review_reasons・needs_review を作る所）を origin/main で file:line。1ジョブの件をまとめて DB を1回読む形で相場を引ける場所はどこか。
0-2. 設定の置き場所: 解析（v102）用の key/value の設定表が既にあるか（git grep で settings・_settings の表。tcg_distribution_settings 以外）。無ければ public.tcg_distribution_settings（key TEXT PK, value TEXT）に key を足す（ADR-1007: 値は data SQL で投入）。どちらにしたかと理由を報告。
0-3. 人の確認: 要確認の画面（ReviewItemDrawer / ConditionReviewPanel 等）で、v102 の件の単位を人が直す仕組みがあるか（item_corrections の field_name・v102_human_decisions_svc が読む判断の種類 file:line）。無ければ「無い」と報告（本便では作らない。「このままで良い」= ack で通せることだけ確かめる）。
0-4. 同じ投稿の重複: クリムゾンヘイズ（product 82）の 203,000 の2行は、同じ source_message の2件か、別の source_message で raw_text が同じものか（本番読み取り）。

## 1. 変更（v102 経路だけ）
1-1. 相場: 件の product_id ごとに、本番の analysis_results から「engine_version LIKE 'v102%' かつ is_current かつ needs_review が false かつ price_normalized あり かつ unit_canonical あり かつ 今の投稿（source_message）とは別の投稿」の行を、product_id×unit_canonical ごとにまとめ、価格の中央値（percentile_cont 0.5）と「別々の投稿の数」を出す。別々の投稿の数は source_messages の raw_text が同じものを1つと数える（md5(raw_text) で重複を除く。0-4 の結果を見て、必要なら設計者に確認）。1ジョブ分を1回の SQL で引く。
1-2. 判定: 件の単位 U・価格 p について、相場 m(U) と、U 以外の単位の相場 m(V) のうち、別々の投稿の数が設定の最小（既定案 3）以上のものだけを使う。r(U) = max(p, m(U)) / min(p, m(U))。r(U) が設定の倍率（既定案 3）を超え、かつ m(V) のどれかで r(V) が r(U) より小さいとき、理由 unit_price_mismatch を付けて needs_review。p が無い・m(U) が無い・比べる m(V) が無い時は何もしない。単位・価格は変えない。
1-3. 設定: 倍率と最小の投稿数は設定の表の key（例 unit_price_check_ratio=3、unit_price_check_min_posts=3）。値をコードに書かない。key が無い・不正なら確認をしない（何もしない・logger.warning）。
1-4. 理由コード unit_price_mismatch: コード定数・tests/test_review_reason_codes_consistency.py・frontend ja.json/en.json reviewReason（「単位と価格が相場と合わない」／"Unit and price do not match the market"）・data/review_reason_codes/ に seed と up_* SQL（gt_* と同じ型）。「このままで良い」で外せる（NON_ACKABLE に入れない）。
1-5. 設定値の投入 SQL（data/ に key 2つ、precheck/dryrun/commit/verify/rollback）。

## 2. テスト（合成で）
- 相場より3倍以上ずれ、別単位の方が近い → unit_price_mismatch。3倍未満 → 付かない。別単位の相場が無い → 付かない。別々の投稿が最小未満 → 付かない。同じ投稿・同じ raw_text の行は数えない。価格なし → 付かない。設定 key なし → 付かない。
- v102 以外の経路は変わらない。理由コード整合テスト。

## 3. 置き換え試験（マージ前の証拠・本番は読み取り）
- 本番の v102 の現行行（直近の全ジョブ）を、変更前と変更後で通し、unit_price_mismatch が付く件の全件（job8・商品・単位・価格・相場 m(U)・最も近い m(V)・別々の投稿の数）。
- その全件について、原文（件の行・前後・見出し）を読んで人として単位を判定（箱／カートン／パック／分からない）。判定を書いてから突き合わせ、「当たり（本当に単位の誤り）」「空振り（単位は正しい）」「分からない」を数える。
- 件以外の値（商品・単位・状態・価格・数量・他の理由）の変化が0であること。
- 停止条件: 空振りが1件でもあれば、全件を報告して止まる（設計者が判断）。

## 4. 手順
1. `bash scripts/new-worktree.sh release/v102-unit-price-check --claude` → preflight。Bash は単独の `cd <worktree> && …`。
2. 0 → 実装 → テスト → 置き換え試験 → ruff・pytest・npm run check:all。
3. commit（feat:、末尾 Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>）。push しない。このカードを docs/handoff/v102-unit-price-check/card-UP.md に置く（recon・design は設計者）。

## 停止条件
- 0 で前提が違う、v102 以外の経路を変えないとできない、空振りが出た → NEEDS_DECISION。フックに止められたら言い換えず止まる（読み取り専用の SELECT が誤検知された時は、書き方の違い（例 -F）を報告）。最終行 DONE / BLOCKED: / NEEDS_DECISION:。
