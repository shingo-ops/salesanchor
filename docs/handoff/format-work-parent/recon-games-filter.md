# recon 細分類一覧の「使えるゲーム」まとめ表示と作品の絞り込み（画面のみ）

> 親の書類: [recon.md](recon.md)（docs/handoff/format-work-parent/recon.md）。この書類は今回の現在地だけ。
> 基準: origin/main bb0a01c29。worktree release/format-games-filter の実物を読んだ結果。
> PO 依頼（2026-10-23）: 使えるゲームを全部書くと見づらいので「3件＋他N件」にまとめ、上部に作品別の絞り込みを付ける。
> ADR 検索: 対象 ADR-1038（docs/adr/ADR-1038-product-format-child-of-work.md）。

## 1. 今の形（変更前）
- 一覧の列は getGameNames が全件を ", " でつなぐ。実物 frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx（変更前の getGameName / getGameNames）。
- ContentToolbar は right に追加ボタンだけ。DataTable は items をそのまま渡す。
- ゲームの名前と順は tcgTypes（GET /super-admin/tcg/types。sort_order 順）から取る。

## 2. 既存の形（0-2）
- SelectControl を ContentToolbar の left に置く前例: frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx の ContentToolbar left 内（size="sm" className="field-h-md" aria-label options）。
- SelectControl の props: frontend/src/components/Select.tsx（options・size・aria-label は素の props）。
- ContentToolbar の left: frontend/src/components/ContentToolbar.tsx。

## 3. 作品数
- 本番の作品は 18 件。タブでは横に収まらないためプルダウン（SelectControl）にする（Opus 設計判断）。

## 4. 文言キーの衝突
- productFormatsMaster 配下に gamesMore・filterAllGames・filterByGame は無かった（ja.json・en.json を grep、0 件）。
