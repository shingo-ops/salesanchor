# recon: 単位も状態も書かれていない件を買取価格で Sealed box / Case に決める（便BB）

基準 origin/main（2026-10-11）。本番は読み取りのみ。生出力（手元・社外秘）: /tmp/CC報告ファイル/buyback-ref/、unit-cascade/、unit-autofix/、unit-truth/、v102-buyback-unit/。

## 既存 ADR
- ADR-157（買取価格の取得。docs/adr/ADR-157-buyback-price-logger.md:30-33 取得元シンソク・ホムラ）、ADR-1007（値は data SQL）。docs/adr で 単位・買取・buyback を git grep → 買取価格で単位を決める ADR は無し。

## 単位・状態の決まり方（v102）
- 件の行の単位の別名: backend/app/services/gemini_raw_copy_v102_product_first.py:422-454 find_unit_product_first（見つからなければ alias None）。
- 状態: resolve_condition_v2 の R4 既定 backend/app/services/tcg_analyzer_svc.py:860-863（箱系→Sealed box、箱系大→Case）、最終フォールバック backend/app/services/tcg_analyzer_svc.py:903-904（R4:単位既定:単位不明）、R4c backend/app/services/tcg_analyzer_svc.py:886-901。
- 語で決まったかの判定は backend/app/services/gemini_raw_copy_v102_soldout_ref.py:44-51 condition_decided_by_word。
- 単位 Case・basis R4:単位既定 の現行行126件は、全件が価格行の位置照合で別名「カートン」「CASE」を持つ（語あり）。

## 買取価格
- 表: public.buyback_shop_products（product_id・product_type・match_status・last_seen_at）、public.buyback_price_logs（price_s・fetched_at）。migrations/20260922_000000_create_buyback_tables.sql:6-34。取得は1日3回（backend/app/celery_app.py:164-167）。
- 結び付き済み 338/477行。種別 BOX 140・BOX_SHRINK 83・CARTON 23・PACK 40 等。つなぎ間違い 7行（2.1%、BOX 系は3行）→ 別セッションへ依頼（~/CC報告ファイル-keep/request-to-buyback-session-20261011-linkage.md）。
- 比（仕入価格÷買取 BOX 中央値）: 人の目で箱 130件 0.82〜1.38、カートン 50件 11.94〜27.32（重なりなし）。買取のカートン÷BOX は 10.49〜13.00。
- 3段（買取→他社→同じ仕入元）の評価: 正解241件で買取段が180件決めて外れ0、他社段6件、同じ仕入元段0件（緩めると同じ仕入元の誤りを引き継いで外れ3）。

## 読み手への影響
- condition_basis "BUYBACK:…" は condition_decided_by_word で False（語で決まっていない側）。品質集計 backend/app/services/tcg_supplier_quality_svc.py:17-18 のパターンには当たらない。backend/app/services/tcg_unit_recovery_svc.py:404 の対象外。
