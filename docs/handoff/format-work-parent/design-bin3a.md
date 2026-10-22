# design 便3a: 旧列 product_formats.type_master_id を読む・書くコードを外す

> 設計の正本: [design.md](design.md) §4 便3a・§8 K5。この書類に新しい設計判断はない。
> 現在地: [recon-bin3a.md](recon-bin3a.md)（docs/handoff/format-work-parent/recon-bin3a.md）／対象 ADR: ADR-1038（docs/adr/ADR-1038-product-format-child-of-work.md）

守り手: backend/tests/test_product_format_game_links_pg.py

## 変更前後の要約
- 変更前: 細分類の API・画面・契約・翻訳が、親子の正本 links と別に、旧列 type_master_id を持っていた。
- 変更後: API は旧列を読まず・書かず・返さない。画面から単独欄と一覧の列を外す。契約と翻訳のキーも外す。
- 変えないもの: DB の列と値（便3b で落とす）、links の編集と使用中の 409、extra の扱い（既定の無視のまま）。migration は無い。

## 受入条件と検証方法
|基準|検証方法|
|---|---|
|作成・更新に type_master_id を付けて送っても保存でき、旧列の値は変わらない|test_create_ignores_legacy_type_master_id_and_does_not_return_it、test_update_ignores_legacy_type_master_id_and_list_does_not_return_it|
|一覧・詳細の応答に type_master_id が無い|同上の model_dump の確認と、openapi.json の ProductFormat 系スキーマに type_master_id が無いこと|
|links の編集と使用中の 409 は変わらない|既存の test_replace_games_adds_and_removes_links、test_replace_games_blocks_removal_in_use|
|パネルに単独欄が出ず、「使えるゲーム」は今までどおり|ProductFormatsMasterPanel.test.tsx|
|K5 の読み手の条件の前半|git grep -n "typeMasterId" frontend/src が何も出さない（exit 1）。router・schema・panel の git grep -n "type_master_id" の残りが links 由来の行だけ|
|契約が最新|CI の API contract is up to date（再生成の差分は細分類の 3 か所だけ）|

## 外部・過去事例の参照と我々への応用
この便は design.md §10 の判断のとおり。数値つきの外部事例はない。過去事例は ADR-1026（products.type_master_id の取り外し）で、読み手を先に外し、列は後の便で落とす順番を踏襲する。

## 維持の仕組み
- 守り手: backend/tests/test_product_format_game_links_pg.py（旧列を受け取っても無視し、返さない試験）
- 親子の正本は links だけ。旧列の代わりの置き場は作らない。

## 解析の正答率への影響（2026-10-22 調べ）
影響する経路は無い。
- v102 の解析、backend/app/tasks、scripts/accuracy、gas/ に type_master_id・typeMasterId を含む行は 0 件（git grep の出力 0 行。recon-bin3a.md 参照）。
- 解析側で product_formats を読むのは backend/app/services/tcg_product_import_svc.py:267（code と id）と tcg_product_roundtrip_svc.py:240-241（to_jsonb で取るが使うのは code と id、:294）。旧列の値は使わない。
- 正答率の採点（scripts/accuracy/score_v102.py）は TSV の突き合わせだけで DB に接続しない（便2 の調べ: design-bin2.md）。
