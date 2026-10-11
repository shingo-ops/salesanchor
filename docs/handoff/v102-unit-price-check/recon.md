# recon: 単位と価格が相場と合わない件（便UP）

基準 origin/main（2026-10-11）。本番は読み取りのみ。生出力（手元・社外秘）: /tmp/CC報告ファイル/price-unit-backtest/、price-unit-gap/、unit-truth/、box-median-check/、pack-products/、unit-heading/、v102-unit-price-check/。

## 既存 ADR
- docs/adr を 単位・価格・相場・unit_price で git grep → 価格で単位を確かめる ADR は無し。関係: ADR-1007（値は data SQL）、ADR-158（is_current）。

## 単位の決まり方（v102）
- backend/app/services/gemini_raw_copy_v102_product_first.py find_unit_product_first（件の source_lines の行の中だけで単位の別名を探す）→ 無ければ resolve_product_first で状態から単位（line_conditions.unit_id）。箱系の商品は R4 で Sealed box → Box。
- 単位の根拠列（analysis_results.unit_basis）は v102 では空。

## 単位の誤りの実態
- 人の目の正解表（無作為300件＋8件、/tmp/CC報告ファイル/unit-truth/judged_all.csv）: v102 の単位の正答率 97.6%（239/245）。誤り6件は全て「Case なのに Box」。原因: 見出し「下記はカートン」が件の行の外（2）、Gemini が「カートン」の行を件から飛ばした（4・完売で価格なし）。
- 見出しの単位を引き継ぐ規則の調査（unit-heading/）: 本物の見出しは60日で2投稿4件だけ。広げると商品名・注意書きの下の約125件を誤らせる → 不採用。
- 単位間の価格の開き（price-unit-gap/）: Case÷Box の中央値 約14倍、Box÷Pack 約50倍。例外10商品は原文確認で全て単位の付け間違い（主に旧エンジン v9 の raw_unit "BOX"）。
- Box 相場の原文確認（box-median-check/）: v102 の Box 3件以上 70商品・207行で箱でない行 0。旧エンジンは約1割が箱以外 → 相場は v102 の行だけ。
- 置き換え試験（v102-unit-price-check/）: 規則A（相場の3倍超かつ別単位が近い）で2件、規則B（別単位の相場が無い時、相場の5倍以上の高い側）で4件。原文で全て当たり。規則Bを安い側にも使うと、汚れた相場で空振り3件 → 高い側だけ。

## 人の判断
- v102 の人の判断（backend/app/services/v102_human_decisions_svc.py:29-45）に単位の直しは無い。review_ack（このままで良い）で理由を外せる。

## 設定の置き場所
- 解析用の key/value 設定表は無い。public.tcg_distribution_settings（key, value, note）に key を足す（配信設定の画面にも並ぶ）。
