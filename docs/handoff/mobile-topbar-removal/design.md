# 設計: スマホ上部のページ名バーを消す

対象 ADR: ADR-140（モバイルナビ下部タブ）／ADR-137（MobileShell の独立 DOM）／ADR-067（デザイントークン強制）
recon: [recon.md](./recon.md)（`docs/handoff/mobile-topbar-removal/recon.md`）
PO 指定: 2026-10-13「スマホには受信箱というヘッダーを消して欲しい」＋適用範囲は**スマホの全ページ**（同日の選択）

## 1. なぜ消すのか（事実のみ）

- 帯の中身は**ページ名のテキスト1つだけ**で、押せる要素を持たない（recon A1・A2・B3）。
- 現在地は**下部タブバーの点灯**で分かる。実機で 受信箱 / 在庫表 / 受注管理 / メニュー の4つが出ている（recon B2）。
- 受信箱では**同じ名前が二重に出ていた**（上部帯＋ページ内見出し）。ページ内見出しは #4148 で視覚的に隠したため、残っていた見える名前は上部帯だけだった（recon C3・C4）。
- 56px は小さくない。スマホで会話一覧に使える高さは実測で約 1140px（device px）＝5行。56 CSS px（168 device px）を本文へ回すと**1行弱ぶん増える**。

## 2. 変更するファイルと、変更前後

### 2-1. `frontend/src/components/MobileShell.tsx`

**削除（3箇所）**: `:36` の `import { usePageTitle } ...`、`:75` の `const pageTitle = usePageTitle();`、`:190-193` の帯の JSX。

```tsx
// 変更前
<div className="mobile-shell">
  {/* ============ MobileTopBar（タイトルのみ） ============ */}
  <div className="mobile-topbar">
    <span className="mobile-topbar-title">{pageTitle}</span>
  </div>

  {/* ============ Outlet ============ */}
  <main className="mobile-content">

// 変更後
<div className="mobile-shell">
  {/* ============ Outlet ============ */}
  <main className="mobile-content">
```

`pageTitle` は帯の中だけで使われており（recon A6）、`usePageTitle` は副作用を持たない（recon A7）ため、呼び出しと import も消す。先頭の DOM 構造コメントから帯の2行を除き、削除の理由・残す理由を追記する。

### 2-2. `frontend/src/mobile-shell.css`

`:15-37` の `.mobile-topbar` と `.mobile-topbar-title`（25行）を削除し、理由のコメントを残す。**トークン `--topbar-height` と `--z-topbar` は残す**（recon C1・C2）。

### 2-3. `frontend/tests-e2e/visual-language/inbox-single-column.spec.ts`

検査を1件追加し、PC 側の検査に2行足す（§5 の #1〜#4 を機械で守るため）。

## 3. 触らない範囲（明示）

- **PC・タブレット**: MobileShell は 767px 以下でしか描かれない（`frontend/src/App.tsx:137` の `useIsMobile()` 分岐・ADR-137）。768px 以上の DOM は1行も変えない。
- **下部タブバー**（`.mobile-tabbar`）: ADR-140 の所有範囲。触らない。
- **ページ内の見出し**（`PageLayout` の `.text-page-title`）: 残す。受信箱の視覚的な隠し（`slimHeaderOnMobile`）も現状維持。
- **トークン**: `tokens.css` は変更しない。
- **API・DB・migrations**: 一切触らない。

## 4. 守る決まり（CI が検査する）

`check:all`（25項目）／`Lint & Dark Mode Check (ADR-067)`／`UI governance gate`／`guard-hex-increase`／`画面検査（受信箱 3幅 Playwright）`。

## 5. 検証方法（受け入れ基準）

| # | 基準 | 検証方法 |
|---|---|---|
| 1 | 390px で**上部のページ名バーが無い** | `inbox-single-column.spec.ts` で `.mobile-topbar` が `toHaveCount(0)` |
| 2 | 390px で**下部タブバーが残り、押せる大きさがある** | 同検査で `.mobile-tabbar` が表示・タブが2つ以上・最後のタブ（メニュー）の高さが44px以上 |
| 3 | 390px で**現在地が読み上げで分かる**（ページ名が見出しとして存在） | 同検査で `getByRole("heading", { name: "受信箱" })` が `toHaveCount(1)` |
| 4 | **1280px / 768px にモバイル用の殻が出ない**（PC 不変） | 同検査の PC・タブレット側で `.mobile-tabbar` と `.mobile-topbar` が `toHaveCount(0)` |
| 5 | 390px で会話一覧が**縦に長くなる**（56px ぶん） | 実機で会話の行の表示本数を比較（投入前5行・投入後は同じ5行だが下の余白が56px ぶん詰まる。データが5件しかないため行数では増えない） |
| 6 | `npm run check:all` が緑 | 実行して出力を PR に貼る（25/25） |
| 7 | 1画面1ページの往復が壊れていない | 既存の `スマホ: 一覧 → 会話 → 一覧 を切り替える` が緑のまま |

## 6. 戻し方

このPRの revert のみ。削除した JSX と CSS が戻る。トークン・API・DB を変更しないため波及はない。

## 7. 残るリスク（正直に）

1. **受信箱では画面上に名前が1つも出なくなる。** 現在地は下部タブの点灯のみで示される。読み上げ用の見出しは残す（§5 #3）。他のページはページ内見出しが見えたままなので影響しない（recon C3）。
2. **他ページの見た目が 56px 上に詰まる。** 全ページ共通の帯を消すため、ダッシュボード等でも本文が上に寄る。はみ出しや重なりは起きない（帯は in-flow・recon B5）が、スマホの全ページで見た目が変わる点は PO 指定の範囲。
3. **スクロールしても名前が追従する利点は失われる**（帯は `position: sticky` だった）。長い一覧を下まで見たときに現在地の文字が出ない。下部タブは `position: fixed` で常に見えるため、現在地の手がかりは残る。

## 8. 相互参照

- **recon**: [recon.md](./recon.md)（`docs/handoff/mobile-topbar-removal/recon.md`）— A1〜E3 の事実を前提とする。帯の中身・高さ・参照箇所・ADR の決定範囲はすべてここで file:line で確認した。
- **ADR-140**（モバイルナビ下部タブ）: 決定は「ハンバーガー+Drawer → 下部タブバー」。**上部帯の存在は決めていない**（recon E1）ため、本変更は ADR の決定に反しない。下部タブバー自体は触らない。
- **ADR-137**（MobileShell の独立 DOM）: MobileShell と DesktopShell は別 DOM。本変更は MobileShell 側のみで PC に波及しない（recon E2）。
- **ADR-067**（デザイントークン強制）: 削除のみで新しい値を書かない。`--topbar-height` は PC が使うため残す（recon C1・E3）。
- **ADR-144**（UI共通部品のガバナンス）: 新しい部品を作らないため新規金型の登録は不要。
- **関連する直前の作業**: [../app-visual-language/card-stage4b-inbox-mobile.md](../app-visual-language/card-stage4b-inbox-mobile.md) §13（3幅の画面検査の恒久化）。本変更の受け入れ基準はその検査に追記する形で守る。

## 9. 外部・過去事例の参照と我々への応用

| 事例 | 何を参照したか | 我々への応用 |
|---|---|---|
| **WhatsApp（Android）の実測** | チャット一覧の画面は上部に帯を持つが、そこに**検索とメニューの操作が載っている**（入力欄まわりの操作ボタンは48dp・benchmark のメモ） | 「帯を置くなら操作を載せる」。我々の帯は**文字だけ**で操作が無く、お手本の帯とは役割が違う。文字だけの帯は置かない判断にした |
| **Meta Business Suite（Android）の実測** | 受信箱は1列切り替えで、画面の高さを本文に寄せている | 56px を本文へ回す方針の裏付け |
| **ADR-140（社内の先行事例）** | ハンバーガーを下部タブへ移した。その時点で**上部帯から操作が無くなった** | 帯が「文字だけ」になったのは ADR-140 の結果であり、今回の削除はその続き。帯の存在は ADR の決定事項ではない（recon E1） |
| **#4148（社内の直前事例）** | 受信箱のページ内見出しをスマホで視覚的に隠した（読み上げ用には残した） | 同じ作法を踏襲する。**見た目から消しても読み上げからは消さない**（§5 #3） |

**採用しなかったもの**: 「帯を残して高さだけ縮める」案は採らない。文字だけの帯は縮めても情報が増えず、下部タブと二重になる状態が続くため。

## 10. 維持の仕組み

- 守り手: `frontend/tests-e2e/visual-language/inbox-single-column.spec.ts`（390px で帯が無いこと・下部タブが残ること・見出しが残ることを検査）と `.github/workflows/e2e.yml` のジョブ `visual-language`（3幅）、および `frontend/package.json` の `check:all`（25項目）。
- 対象: 帯の復活（`.mobile-topbar` の再出現）、移動手段の消失（`.mobile-tabbar` の消失・44px未満化）、読み上げ用の見出しの消失、PC へのモバイル殻の混入。
- 関所が無い部分: **他ページ（ダッシュボード等）の見た目が 56px 上に詰まること自体は検査していない。** 3幅の検査は受信箱のみを開くため。他ページの崩れは PO の目視で見つける運用とし、崩れが出たらそのページを検査に足す。
