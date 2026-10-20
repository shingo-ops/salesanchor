# recon: 区分「サプライ系」（v102・カード用品）

調べた日: 2026-10-20。基準は origin/main 38613d7d7（読み取りだけ）。本番は reader 鍵で ai_ro のビューだけを読んだ。
生出力は社外秘フォルダにある（仕入元の原文・投稿の番号を含むので、リポジトリには入れない）。
ラベル: 【事実】=ファイルか出力で確かめた／【推測】／【未確認】

## 既存 ADR の検索
- ADR-1035（状態ごとの単位・ブックレット系）: 区分を 1 つ足す型の前例。設計は docs/handoff/condition-unit-booklet/design.md。
- ADR-1031（区分ごとの状態の群・既定の状態 R7/R8）、ADR-1021（既定の状態は R4 で始めない）、ADR-1007（値は migration に書かず記録 SQL で入れる）、ADR-1020（共用商品の 9 項目必須）。

## 事実
1. 区分の定数は `backend/app/services/gemini_raw_copy_v102_product_first.py:48-55`、群・既定の状態・basis の定数は `:86-95`、区分→群の表 `_KUBUN_TO_VALUE_GROUP` は `:585-589`。群の行が masters にあるときだけ群で判定する（`:627-629`）。
2. 区分に群が無い商品は、状態の最後の受け皿が FLAG_SINGLE → `_undecided_condition`（`:575-583`）で Error になり、理由 `condition_unknown` が付く。この理由は確認済みにできない（`backend/app/services/review_reason_codes_svc.py:22`）。→ 商品を登録するだけでは要確認から外れない。
3. 単位は `find_unit_product_first`（`:507-533`）が、価格の行→在庫の行→名前の行の順に単位の別名を探す。「100枚入」は別名「枚」（Piece）に当たる。
4. 状態から単位を決め直す `_resolve_unit_from_state`（`:678-704`）は、単位が無いとき（または箱系で「条件つき」のとき）だけ状態の単位で埋める。書かれた単位が Piece なら置き換えない。セット系だけ別の分岐がある（`:688`）。
5. まとめ売りの検出は単位語の直後が「入」なら除く（`backend/app/services/v102_bundle_svc.py:29`, `:95`）→「100枚入」は束の数にならない。
6. 単位表 line_units は 10 行（Case/Box/Pack/Piece/Set/本/点/個/Booklet/MasterCarton）。「袋」「Bag」は無い。別名表 line_unit_aliases にも「袋」「bag」は無い。Booklet の別名は「冊」だけ。
7. line_units.kubun に CHECK は migration に見つからない（表の CREATE 文は【未確認】）。Booklet（kubun 冊子系）を足したとき、コードは変えていない（backend に「冊子系」の文字列は無い）。
8. 単位の表示: 在庫の分布は `unit_canonical` の文字列をそのまま返す（`backend/app/services/tcg_distribution_svc.py:343`）。まとめの表示だけ `COALESCE(name_ja, canonical, unit_canonical)`（`:267`）。単位ごとの i18n キーは ja.json / en.json に無い。→ Booklet は画面に「Booklet」と出ている。
9. 状態の群の CHECK は migration `migrations/20261020_100000_line_conditions_value_group_add_booklet.sql`（冪等ガード付き）。登録は `scripts/run_all_migrations.sh:1030-1031` 付近。
10. 群を足すときに触るコード: `backend/app/services/tcg_analyzer_svc.py:653`（SCOPED_VALUE_GROUPS）、`backend/app/services/line_analysis_v102_svc.py:44`, `:646-649`（_SCOPED_GROUP_OF_KUBUN）、`backend/app/services/tcg_result_order.py:11`（VALUE_GROUP_ORDER）。VALUE_GROUP_ORDER を変えると `backend/tests/test_inventory_distribution_rows.py:107`, `:119`, `:270-284` の SQL の長さとハッシュが変わる。
11. 画面: frontend に booklet を含むファイルは 0 件。区分の kubun_type は自由入力（`frontend/src/pages/product-categories/ProductCategoriesPage.tsx:218-222`）。
12. 区分表 tcg_product_categories の使用中 id は 1, 2, 4, 9, 11, 13（13 = PC_BOOKLET）。
13. 小分類 SUPPLY は product_lines id=9。細分類 product_formats で line_id=9 の行は 0 件（全行の line_id が空）。line_id を参照するのは管理 API の CRUD、`backend/app/routers/super_admin_product_lines.py:137-146` の削除可否、管理画面 `ProductFormatsMasterPanel.tsx` だけで、商品登録の検査（PRODUCT_FORMAT_GAME_MISMATCH）は line_id を見ない。細分類と作品の組は product_format_game_links で決まる。
14. 作品の追加の前例: ハリー・ポッター（9045）・パルワールド（9046）を台本で作った（create_type → update_type(kind_id) → code_only_match/match_by_code の更新）。
15. 既存のサプライ商品は 21 件（product_line_id=9）。20 件はドラゴンボールの公式スリーブ・カードケース＆スリーブセット・プレイマット・エナジーマーカーパック、1 件はヴァイスシュヴァルツのラバーマット付きセット。区分と細分類は空。検索語に「スリーブ」「カードスリーブ」を持つ商品がある。
16. 今回の要確認の対象: 1 つの投稿の用品 4 行（業務用スリーブ／業務用PSAスリーブ／PSA提出用セイバー／サイドローダー）。書き方は「N枚入 価格 在庫N」。4 行とも 商品なし・単位 Piece・状態 Error・理由 product_not_in_master, condition_unknown, gemini_gap_suspect。同じ 4 品は 10/06〜10/20 の 5 つの投稿に出ている。
17. 便2 の影響の数（v102 の現行行・直近60日 4,753 行）:
    - canonical「Bag」の照合（`backend/app/services/gemini_raw_copy_v102_product_first.py:399-443` は NFKC＋小文字で、前後が同じ種類の文字なら不採用）に当たる行は 0 件。同期間の全投稿でも「bag」を含むものは 0 件。
    - 「袋」を含む行は 2 件（どちらも「袋とじ未開封」）。別名「袋」は足さないので影響しない。
    - 「サプライ」を含む行は 1 件（2026-09-28、「サプライのみ」の値段の行）。作品名は 〆の参照で、原文に複数を指す語があるときだけ使われる（`backend/app/services/gemini_raw_copy_v102_soldout_ref.py:300-308`。作品名が原文にあれば、その作品の商品の行だけを〆の候補にする）。
18. 解析の経路: 直近7日に行を作ったのは v102 だけ（688 job）。v6 系は 9/27 が最後。v10/v101 のコードは v102 から呼ばれるので、単位表の変更は v102 にも効く（`backend/app/services/tcg_analyzer_svc.py:99-129` は区分を見ない）。

## 未確認
- 本番の type_master に「サプライ」という作品が既にあるか（便2 の 01_precheck で確かめ、あれば止める）。
- line_units の CREATE 文と kubun の制約（実装カードで実物を確かめる）。
- GAS 在庫一覧での単位の表示。
- プレイマット・アタッシュケースなど、ほかの用品の要確認の件数（行ごとに数えていない）。
