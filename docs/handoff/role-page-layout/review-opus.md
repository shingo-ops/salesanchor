# ロール画面の配置の直し — Opus 審査記録

| 項目 | 内容 |
|------|------|
| 区分 | A（画面だけ。新しい CSS 変数 `--role-color-dot-size` を1つ足すため） |
| 設計審査 | design.md（自己審査 APPROVE・未解決なし） |
| 実装 | クラウド Sonnet、commit `070cbddab`（2026-11-08 push） |
| 実装の確かめ | Opus が手元で差分全文を読んだ（同じ AI による確かめで、独立した審査ではない。マージ前に別の reviewer を通す） |

## 1. 実装役の報告（クラウドで実行・Opus は記録 `impl-checks.txt` を読んだだけ）

- `tsc --noEmit -p .` exit 0（生成物 `generate:api-types` を作ってから。生成物は commit していない）。
- `npm run check:all` exit 0（lint・stylelint・dark-parity 131 変数・css-values・i18n を含む全項目）。
- `npm run test:unit` exit 0。208 ファイル・2410 件すべて通過。

## 2. Opus が差分を読んで確かめたこと

- 変更したファイルは design.md §3 の5つ（`RolesPage.tsx`・`RolesPage.css`・`pages-layout.css`・`responsive.css`・`tokens.css`）と、検査記録 `impl-checks.txt` だけ（`git diff --stat db790e12b 070cbddab`）。
- サーバー・DB・`migrations/`・`deploy.yml`・`scripts/` の変更なし。
- 左の一覧は金型 `SubMenu`（`variant="flat"`）に置き換わった。字下げの計算は消え、色は DB の `roles.color` を丸に塗るだけ。押したときは今までと同じ `selectRole`（未保存の確認つき）を通る。
- `SubMenu` は `className`・`activeKey`・`onChange` を受け付ける（`frontend/src/components/SubMenu.tsx:35-37`）。
- 高さの連鎖: `.roles-page`（100%・縦並び）→ `.roles-layout`（flex 1・min-height 0）→ `.roles-main`（縦並び・overflow hidden）→ `.role-perm-sections`（flex 1・overflow-y auto）。動くのは表だけ。
- 「変更をキャンセル」「変更を保存」は表の下の `.role-perm-footer` へ移った。押せる条件（`disabled` の式）は変えていない。見出しには編集・削除だけが残る。
- 消した `.roles-list`／`.role-item*` の CSS は、ほかで使われていない（`git grep -E "role-item|roles-list" -- frontend/` は `RolesPage.tsx:317` の金型の className だけ）。
- 色・寸法は `var()` だけ。新しい文言なし（`t()` の鍵は既存のまま）。
- スマホ幅（767px 以下）は今の動き（全体で動く）を保つ3行だけ。PO の決定「Android 側が対応・記録のみ」に合う。

## 3. カードとの差

- なし。

## 4. 判定

- APPROVE（PR 作成へ進む）。マージ前に新しく立てた reviewer（Opus）の判定を取る。
