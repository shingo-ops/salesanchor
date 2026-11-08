# ロール画面の表の区切りがつぶれる不具合 — 現在地（recon）

| 項目 | 内容 |
|------|------|
| 基準 | `origin/main` d2f6a824c2cffad4e859317087aa7d272131e48b |
| 作成 | Opus（2026-11-08） |
| 前の仕事 | `docs/handoff/role-page-layout/`（表だけ動かす直し。本番反映済み 2026-11-08 11:01 JST） |

## 0. 何が起きたか（本番で観測した事実）

- 本番 `https://app.salesanchor.jp/management-center/roles`（オーナーを選んだ状態・窓の高さ 898px）で、権限の表の区切り（メニューの組ごとの枠）が低く押しつぶされ、中の行が切れて見えた。
- DOM の実測（2026-11-08 本番・ブラウザで計測）:
  - 表の入れ物 `.role-perm-sections`: 見える高さ 508px、中身の高さ 508px、`overflow-y: auto`。中身と見える高さが同じなので動かない。
  - 区切り `.role-perm-section` 5つ: 見えている高さ 94／68／60／74／149px、本来の高さ 476／341／302／373／765px。`flex-shrink` はすべて `1`。
  - `.hub-content` の scrollTop は 0（画面全体は動いていない＝この点は設計どおり）。
- PO の求め「権限の表だけがスクロールするように」が満たされていない。

## 1. 原因（事実）

- `.role-perm-sections` は縦の flex（`frontend/src/pages/roles/RolesPage.css:38-46`、`display:flex; flex-direction:column; flex:1; min-height:0; overflow-y:auto`）。
- 子の `.role-perm-section`（`frontend/src/pages/roles/RolesPage.css:48-52`）は `overflow: hidden` で、`flex-shrink` の指定が無い（既定値 1）。
- flex の子は既定では中身より小さく縮まないが、`overflow` が `visible` 以外だと縮める下限が 0 になる（CSS Flexbox の「自動の最小の大きさ」の決まり）。そのため区切りが入れ物の高さに合わせて縮み、入れ物の中身があふれず、スクロールが起きない。
- 前の設計 `docs/handoff/role-page-layout/design.md` §3-3 で、子の区切りに `flex-shrink: 0` を入れ忘れた。

## 2. 直し方を本番の画面で試した結果（事実）

- ブラウザで `.role-perm-section { flex-shrink: 0 }` だけを一時的に足して測った（保存はしていない・再読み込みで消える）:
  - `.role-perm-sections`: 見える高さ 508px、中身の高さ 2331px。いちばん下までスクロールすると scrollTop 1823。
  - 最後の行「配送」が表の見える範囲に入った。
  - `.hub-content` の scrollTop は 0 のまま。保存の段 `.role-perm-footer` は表の下（上端 805px・下端 858px、窓の高さ 898px の中）。

## 3. 既存 ADR

- `git grep -i -l 'role-perm-section' docs/adr/` → 該当なし。関係する決まりは前の仕事と同じ（ADR-067・ADR-144）。新しい変数は使わない。
