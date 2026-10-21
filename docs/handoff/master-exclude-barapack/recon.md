# recon: 商品 440406 の除外語「バラパック」を外す

実測日 2026-10-21。実測時の origin/main: d7c5dc2e41870095588842c3fd0d57ada7f3e838。事実のみ。投稿本文・仕入元名は含まない。

## §1 既存 ADR の検索
実行: `git grep -il -e "exclude_keywords" -e "除外語" -e "除外キーワード" -- docs/adr`、`grep -n -i 除外 docs/adr/FEATURE-INDEX.md`

- 該当 ADR: ADR-093 / ADR-100 / ADR-1001 / ADR-1002 / ADR-154 / ADR-155。FEATURE-INDEX.md に「除外」の行はなし（0 件）。
- docs/adr/ADR-155-product-master-ssot-csv-app.md:25-26: 商品マスタの値の正規の更新手段は CSV 取り込みとアプリ画面。値の操作をマイグレーションで行うことは禁止。今回はマイグレーションではなく、PO 合意（2026-10-21）に基づく直接 SQL（PO の ! 実行のみ）。前例: docs/handoff/master-keyword-fix/README.md（PR #4616・#4617）、docs/handoff/deckbuild-master-fix/README.md。
- 除外語を外す専用の ADR はなし。

## §2 表の制約と position の扱い（事実）
- migrations/20260919_020000_master_ssot_public_tables.sql:317-326: public.product_exclude_keywords の定義は id（IDENTITY・主キー）・keyword・position・product_id（public.products への参照）・updated_at。索引は product_id と (product_id, position) の 2 本で、どちらも一意ではない。
- 本番（reader 鍵で pg_indexes を照会）: 主キー索引（id）のみが一意。information_schema.table_constraints は reader 鍵では 0 行（権限による）。一意制約は索引の面では (product_id, position) に無い。
- 本番の全行（1340 行）で (product_id, position) の組は 1340 通り、重複なし。
- アプリの保存の並べ方: backend/app/services/tcg_product_detail_svc.py:298 で商品の語を全部消し、:302-305 で `enumerate(words, 1)` により position を 1..n の連番で入れ直す。backend/app/services/tcg_product_master_svc.py:791 `next_pos = len(existing_kws) + 1`（末尾追加は件数 + 1）、:721 も同様。どちらも連番前提。
- 判断: 一意制約はないので、行を消しても詰めなくてもエラーにはならない。ただしアプリの保存と末尾追加は連番（1..n）を前提にしているため、消したあとに position を 1 つ詰めて 1..51 に保つ。詰めないと、末尾追加（件数 + 1 = 52）が既存の position 52 と重なる。
- 本番には position が 0 始まりの古い商品が残る（reader 鍵で確認、例: 商品 10・14・15）。440406 は 10/17 の書き直しで 1..52 の連番（本番で確認）。

## §3 440406 の今の値と試算（reader 鍵・2026-10-21）
- products 440406: product_code PM0263、mark M6a、name 30th CELEBRATION、is_active 真。products.exclude_keywords（旧テキスト列）は空。product_blank_confirmations は 0 行。
- 除外語 52 行、position 1〜52 の連番。「バラパック」は 1 行だけ、id 2000、position 46、updated_at 2026-10-17 06:50:02.770819+00。直前 position 45 は「コンプ」、直後 47 は「シングルカード」。
- 「バラパック」を含む商品は、reader 鍵で見た限り 440406 の 1 行のみ（`where product_id=440406 and keyword='バラパック'` が 1 件）。
- 使う表の列（reader 鍵・information_schema で確認）: product_exclude_keywords = id, keyword, position, product_id, updated_at / products = id, product_code, mark, name, is_active, updated_at ほか / audit_log = id, table_name, record_id, action, changed_by, changed_at, old_values(text), new_values(text) / product_blank_confirmations = product_id, field_code, confirmed_by, confirmed_at, note。
- audit_log の前例の形: id 497（440406 の 10/19 の追加）は old_values / new_values に `{"product_id": …, "exclude_keywords": [語の一覧]}` を文字列で入れている。今回も同じ形。
- 試算（社外秘の本文は載せない・数のみ。調査記録は a5_a7_check.md §A7）: 直近 30 日の現行行 + 未登録グループ 1498 文のうち、検索語と「バラパック」を両方含むのは 1 文面。外すと unmatched → matched 440406。ほかの文の変化は 0、悪くなった文は 0。
- 入れた日・人・理由は見つからなかった（audit_log id 442 の変更前の 47 語に既に入っていた）[未確認]。

## §4 再解析の対象（reader 鍵・2026-10-21 12:34Z 時点）
- 試算の 1 文は job ef13fd86（10/21 07:02 受信）にあるが、同じ仕入元の新しい投稿（10/21 10:09 受信の job 4f3a13ed）が出て ef13fd86 の投稿は有効でなくなった（is_active が偽）。同じ行は 4f3a13ed にある。
- 有効（is_active 真）な v102 の job で「バラパック」と 30th 系の語を両方含む投稿は 2 本: job 4f3a13ed（10:09 受信）と job c4c59612（12:03 受信）。どちらも現行行に「product_not_in_master」で未一致の行が残る（4f3a13ed は gemini_index 3 の 1 行、c4c59612 は gemini_index 0 と 11 の 2 行）。どの行がバラパックの行かは行の対応を確かめていない [未確認]。
- audit-out.txt:883 の別の投稿（#70、job cb42de20、10/06 受信）: v102・done・現行行は未一致で、除外語「バラパック」だけで外れていた。ただし投稿は有効でなく（is_active が偽）、画面に出ない。
- 判断: 再解析の対象は有効な 2 本（4f3a13ed、c4c59612）。ef13fd86 と cb42de20 は有効でない投稿のため対象外（画面に出ず、直しても見た目が変わらない）。
- 未確認: c4c59612 の gemini_index 11 の行がどの商品か、再解析後に 440406 に当たるかは試算していない（試算は 10/21 朝のコーパス。この 2 本はその後に届いた投稿）。再解析の dryrun 後に再解析結果を見て確認する。
