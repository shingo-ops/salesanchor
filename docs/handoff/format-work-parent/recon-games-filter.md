# recon 細分類一覧の「使えるゲーム」まとめ表示と作品の絞り込み（画面のみ）

> 親の書類: [recon.md](recon.md)（docs/handoff/format-work-parent/recon.md）。この書類は今回の現在地だけ。
> 基準: origin/main bb0a01c29。worktree release/format-games-filter の実物を読んだ結果。
> PO 依頼（2026-10-23）: 使えるゲームを全部書くと見づらいので「3件＋他N件」にまとめ、上部に作品別の絞り込みを付ける。
> ADR 検索: 対象 ADR-1038（docs/adr/ADR-1038-product-format-child-of-work.md）。

## 1. 今の形（変更前。行番号は bb0a01c29 の実物）
- ゲーム名の引き方: frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx:203-207 の getGameName（tcgTypes から name_ja を探し、無ければ id の文字列）。
- 一覧の文字: 同 :209 の getGameNames。0 件は "-"、それ以外は全件を ", " でつなぐ。
- 一覧の列: 同 :216 の `{ key: "game_ids", ... renderCell: row => getGameNames(row.game_ids) }`（columns は :214 から）。
- ContentToolbar: 同 :230-240。right に追加ボタンだけで、left は無い。
- DataTable: 同 :242-244。`data={items}` で一覧をそのまま渡している。
- 一覧の取得: 同 :91 の `api.get<ProductFormat[]>("/super-admin/product-formats")`。
- ゲームの名前と順の元: 同 :109 の `api.get<TcgType[]>("/super-admin/tcg/types")`。サーバー側の並びは backend/app/routers/super_admin_tcg.py:166-167 の `ORDER BY sort_order, id`（sort_order 順）。
- 今の game_ids の並びは id 順: backend/app/routers/super_admin_product_formats.py:40 の `array_agg(type_master_id ORDER BY type_master_id)`。そのため、画面で作品の並び（sort_order 順）に直す処理が必要。

## 2. 既存の形（0-2）
- SelectControl を ContentToolbar の left に置く前例: frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx:249-283。ContentToolbar は :249、left は :250、SelectControl は :266-280（size="sm"・className="field-h-md"・aria-label・options）。
- SelectControl の props: frontend/src/components/Select.tsx:26-33（options・size）と :34-37（aria-label・className など素の select の props）。型は :58-62、実体は :64。
- ContentToolbar の left: frontend/src/components/ContentToolbar.tsx:4-8（left・right）、:23（関数）、:27（left の描画）。

## 3. 作品数と件数の根拠
- タブでは横に収まらないためプルダウン（SelectControl）にする（Opus 設計判断）。
- 本番を reader 鍵（読み取り専用の鍵）で読んだ日時: 2026-10-23 08:57（日本時間。サーバー記録 2026-10-22T23:57Z）。
- 数え方（読み取り専用の ai_ro スキーマ上の 3 つの表を count(*) で数えた）:
  - 細分類 = public__product_formats: 全体 28 件、うち有効（is_active）28 件。
  - 作品 = public__type_master: 全体 18 件、うち有効 18 件。
  - 細分類と作品の対応 = public__product_format_game_links: 78 件。
- 細分類ごとの使えるゲーム数: product_formats を product_format_game_links に LEFT JOIN し、format_id ごとに数えて、その数ごとの細分類数を出した。
  - 1 件の細分類 13、2 件が 9、4 件が 2、6 件が 1、7 件が 1、10 件が 1、16 件が 1（合計 28）。最大は 16 件。
  - 3 件を超える細分類は 6 件。これらが「他 N 件」の対象になる。
- よって「作品 18 件・細分類 28 件・使えるゲームの最大 16 件」。

## 4. 文言キーの衝突
- productFormatsMaster 配下に gamesMore・filterAllGames・filterByGame は無かった（ja.json・en.json を grep、0 件）。
