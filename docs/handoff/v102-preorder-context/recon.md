# recon: 試作版 v102 で、予約の案内が「在庫あり（In Stock）」になる（便PO）

基準 origin/main（2026-10-12、d46598323）。本番は読み取りのみ。社外秘：投稿の原文・仕入元の名前はこの文書に書かない。生出力（手元）: /tmp/CC報告ファイル/preorder-status/、/tmp/CC報告ファイル/preorder-release/、/tmp/CC報告ファイル/preorder-design/recon/（r1〜r6・q1〜q3）。
カード: [card-PO.md](./card-PO.md)／設計: [design.md](./design.md)

## 既存 ADR
- `git grep -il "tcg_status_master" docs/adr/` → docs/adr/ADR-154-tcg-parity02-gas-python-migration.md のみ。docs/adr/ADR-154-tcg-parity02-gas-python-migration.md:26 は「マスタ不在時は従来動作を維持」。本変更も規則の行が無ければ従来どおり（design.md §2）。
- docs/adr/FEATURE-INDEX.md にステータス判定の行は無し。ステータスの決め方（予約の扱い）を決める ADR は無し。

## ステータスの決まり方（origin/main）
- backend/app/services/gemini_raw_copy_v101.py:924 `resolve_status_v2(block, ctx.status_entries, raw_memo=block)`。block は backend/app/services/gemini_raw_copy_v101.py:904 で件の lines の行だけ（件の外の見出しは見ない）。
- backend/app/services/tcg_analyzer_svc.py:1162-1200 resolve_status_v2：EXCLUDE → OUTPUT（DEFAULT 以外）→ DEFAULT の順。戻り値からは DEFAULT で決まったかを区別できない。
- backend/app/services/tcg_analyzer_svc.py:1118-1141 load_status_master：public.tcg_status_master の enabled 行を effect, priority 順に読む。
- 本番の規則（2026-10-12）：Pre-order は ST0001 `\(\d{1,2}\/\d{1,2}発\)` と ST0003 `(?:^|[^0-9\/])(\d{1,2}日)(?=BOX|発送|入荷|$)` だけ（ST0002 は無効）。DEFAULT は ST0004 In Stock。「予約」「発売日発送」「発送日要相談」に当たる規則は無い。
- 本番の制約：tcg_status_master は PRIMARY KEY (id) と FOREIGN KEY (tenant_id) だけ（effect・match_type の CHECK 制約なし。pg_constraint で確認、/tmp/CC報告ファイル/preorder-design/test/c1.out）。
- 入力の検証：backend/app/schemas/central_masters.py:549-577（変更前）は effect を {OUTPUT, EXCLUDE}、match_type を {REGEX, LITERAL, DEFAULT} に限る。新しい値の行が入ると管理画面の一覧 API が検証で落ちる。

## 件に届いていない材料
- 投稿日：_extract_one に届いていない（backend/app/tasks/tcg_extraction.py:257 ExtractionContext に無し）。既存の読み方は backend/app/services/line_analysis_v102_svc.py:932 _FOLLOWUP_CURRENT_SQL（line_posted_at）。
- 発売日：ProductEntry に無い。既存の商品マスタの読込は backend/app/services/gemini_raw_copy_v102_product_first.py:290 load_product_first_masters・:105 ProductFirstMasters。
- 件の行番号は raw_text.split('\n') の 1 始まり（q3：1150/1150 一致）。

## 下流（status を見るところ）
- 現行行（is_current）のまとめ方（backend/app/services/tcg_analyzer_svc.py:1855 付近）に status は入らない。
- 配信（backend/app/services/tcg_distribution_svc.py:266, :291-298）は Pre-order を除かず status 列に出す。在庫一覧（GAS）は Pre-order を灰色の札で表示し、status の絞り込みは無い。便BB・便UP は status の文字列を見ない。

## 観測（本番の v102 現行行、2026-10-12 読み取り）
- r1：v102 の現行行を持つ job 110・件 2,664。
- r4：予約見出しの行が、どの件の lines にも入っていない（0件）。
- r6：件の上にあるいちばん近い見出しで分けると、予約の見出しの下 281件のうち In Stock 280・Pre-order 1。在庫の見出しの下は In Stock 1,058。見出しなしは In Stock 1,308・Pre-order 1・Sold out 16。
- 予約の見出しの下で、発売日が投稿日より前の4件は、再販の予約案内（「N月中旬発送予定」「[M/D入荷]」）。商品マスタの発売日は公開情報と一致（/tmp/CC報告ファイル/preorder-release/）。
- Gemini の写しは、価格・数量の食い違い 0/1,169（/tmp/CC報告ファイル/gemini-line-accuracy/）。判定はシステムが行番号から行う方針と合う。

## 未確認
- 「N月入荷分」（同じ投稿で2月・4月・6月が並ぶ）が将来の入荷分の案内かどうか。PO の確認待ち（design.md §7）。
