# design: PC受信箱のページが縦にはみ出す件を直す

> この文書は何か: PC の受信箱で、ページ全体に縦のスクロールバーが出る（約30pxはみ出す）のを直す設計書。

親（設計仕様書）: [docs/specs/inbox/README.md](../../specs/inbox/README.md) ／ 調査: [recon.md](./recon.md) ／ 審査: [review-opus.md](./review-opus.md) ／ 実装カード: [impl-card.md](./impl-card.md)

- 起案: 2026-11-23 Claude Opus（設計担当）
- 区分: 既存テーマ（受信箱）の延長（STANDARD-WORKFLOW §1.8）。記録は `docs/specs/inbox/track-record.md` に追記する。
- 新しい ADR は作らない: 吹き出しの決めごとは `frontend/src/components.css:437-441` のコメント（「要素は position が必要」）として既にあり、本件はその決めごとを守っていなかった箇所を直すだけ。方針は変わらない。

## 1. 目的と PO の言葉

- 前の件（PC受信箱の3列の幅）の報告で「縦に約30pxはみ出す件が別にある」と伝え、PO が 2026-11-23 に「1」（縦のはみ出しを直す設計を作る・本番まで進める）を選んだ。
- PO の目的（推測ではなく、元の依頼「会話欄を広く取りたい」から）: 受信箱を1画面に収め、余計なスクロールバーを無くす。

## 2. KGI（○×で判定）

| # | 基準 |
|---|---|
| K1 | 本番の PC の受信箱で、ページの高さ（`document.documentElement.scrollHeight`）が窓の高さ（`innerHeight`）と同じ＝はみ出し 0px（今は 34px） |
| K2 | ヘッダー右端の3つのボタン（テンプレート・FAQ・設定）にマウスを乗せると、吹き出しがそのボタンのすぐ下に見える（今は窓の外に出て見えない） |
| K3 | 横のはみ出しも 0px のまま（`scrollWidth` と `innerWidth` が同じ） |
| K4 | 同じ失敗を機械で止める: 新しい画面の自動試験が、直す前のコードでは落ち、直した後は GitHub の CI（画面検査 768px・1280px）で通る |
| K5 | 生の数字・直書きの色を足さない（`npm run check:all` が緑）。受信箱以外の画面の見た目は変わらない |

## 3. 技術の方法

### 3-1. 原因（docs/handoff/inbox-header-tooltip-overflow/recon.md §2・§3）

吹き出しは `[data-tooltip]::after` を `position: absolute; top: calc(100% + 8px)` で置く（`frontend/src/components.css:443-446`）。受信箱のヘッダーの3つのボタン（`frontend/src/pages/inbox/InboxPage.tsx:92`・`:101`・`:110`）は `position` を持たないので、吹き出しはページ全体を基準にして窓の下端の 8px 下に置かれる。見えなくしてあっても場所は取るので、ページが縦に伸びる。

### 3-2. 直し方: ヘッダー右端のボタン群の共通の箱で、吹き出し付きの部品に位置の基準を持たせる

`.page-header-actions`（ADR-144 の共通部品。全ページ共通のヘッダー右端の箱。定義は `components.css` のここだけ＝SSOT）の中の `[data-tooltip]` に `position: relative` を付ける。

- これで吹き出しはボタンを基準にし、ボタンのすぐ下に出る（docs/handoff/inbox-header-tooltip-overflow/recon.md §3-1: 本番の画面で試し、はみ出し 0・吹き出し top 42px・横のはみ出しなしを確認）。
- 共通の箱の CSS 1か所に書くので、今後ほかのページがヘッダーのボタンに吹き出しを付けても同じ失敗が起きない。
- `relative` は数字ではないので、デザイントークンの検査（ADR-067）の対象外。新しいトークンは要らない。

### 3-3. 変更するファイルと前後のコード

**(1) `frontend/src/components.css:510-512` の直後に足す**

変更前（`:507-514`）:
```css
.page-header-actions .icon-btn {
  border: 1px solid var(--border-icon);
}
.page-header-actions .icon-btn:hover {
  border-color: var(--border-icon);
}

/* --- Icon Button --- */
```
変更後:
```css
.page-header-actions .icon-btn {
  border: 1px solid var(--border-icon);
}
.page-header-actions .icon-btn:hover {
  border-color: var(--border-icon);
}
/* 吹き出し（data-tooltip）の位置の基準をボタン自身にする。無いと吹き出しが窓の下に置かれ、ページが縦にはみ出す（docs/handoff/inbox-header-tooltip-overflow/design.md） */
.page-header-actions [data-tooltip] {
  position: relative;
}

/* --- Icon Button --- */
```

**(2) 新しい画面の自動試験 `frontend/tests-e2e/visual-language/inbox-page-no-vertical-overflow.spec.ts`**

- 置き場所の理由: GitHub の CI で今も走る画面の自動試験は `visual-language/` だけ（`.github/workflows/e2e.yml:170-175`。全体の E2E は `:294` で止めてある）。
- 3つの幅（390・768・1280）で流れる。スマホ（390px。`frontend/tests-e2e/visual-language/inbox-helpers.ts` の `MOBILE_MAX_PX` 767 以下）はヘッダーのボタンを出さない（`frontend/src/pages/inbox/InboxPage.tsx:83`）ので `test.skip` にする。
- 中身:

```ts
/**
 * visual-language/inbox-page-no-vertical-overflow.spec.ts — 受信箱のページが縦にはみ出さない
 *
 * ヘッダー右端のボタンの吹き出しが位置の基準を持たないと、窓の下に置かれページが縦に伸びる。
 * 根拠: docs/handoff/inbox-header-tooltip-overflow/design.md
 *
 *   cd frontend && npm run test:e2e:vl
 */
import { expect, test } from "@playwright/test";
import { MOBILE_MAX_PX, openInboxList } from "./inbox-helpers";

test.describe("受信箱のページが縦にはみ出さない", () => {
  test("ヘッダーの吹き出し付きボタンに位置の基準があり、ページの高さが窓と同じ", async ({ page }) => {
    const width = page.viewportSize()?.width ?? 0;
    test.skip(width <= MOBILE_MAX_PX, "スマホ幅ではヘッダーのボタンを出さない（InboxPage.tsx の showHeaderActions）");

    await openInboxList(page);

    const tooltipHosts = page.locator(".page-header-actions [data-tooltip]");
    await expect(tooltipHosts.first()).toBeVisible();
    const positions = await tooltipHosts.evaluateAll((els) =>
      els.map((el) => window.getComputedStyle(el).position),
    );
    expect(positions.length).toBeGreaterThan(0);
    expect(positions.filter((p) => p === "static")).toEqual([]);

    const size = await page.evaluate(() => ({
      scrollHeight: document.documentElement.scrollHeight,
      innerHeight: window.innerHeight,
    }));
    expect(size.scrollHeight).toBeLessThanOrEqual(size.innerHeight);
  });
});
```

### 3-4. 触らない範囲

- `frontend/src/components.css:437-495`（吹き出しの共通の作り）: 変えない。`[data-tooltip]` 全体に `position: relative` を付ける案は採らない（§4 案B）。
- `frontend/src/pages/inbox/InboxPage.tsx`・`frontend/src/components/HeaderButton.tsx`・`Button`: 変えない。
- 絞り込みの開閉（`frontend/src/pages/inbox/InboxConversationList.tsx:82`・`frontend/src/pages/inbox/InboxConversationListMobile.tsx:89`）とカルテを閉じる（`frontend/src/pages/inbox/InboxKartePanel.tsx:174`）の吹き出し: PC でははみ出しを作っていない（docs/handoff/inbox-header-tooltip-overflow/recon.md §3）。スマホ幅は Android 側の担当なので触らない。
- `frontend/playwright.config.ts`（`SELF_WIDTH_SPECS` に入れない。この試験は project の幅で動かすため）・`.github/workflows/`: 変えない。
- backend・migrations・scripts・ADR: 変えない。データと配線は変わらない。

## 4. 代わりの案と選ばなかった理由

| 案 | 内容 | 選ばなかった理由 |
|---|---|---|
| B | `[data-tooltip]` 全体に `position: relative` | `position: fixed`・`absolute` で置いている吹き出し付きの部品（`components.css:439` のコメントの `.inbox-settings-btn` 等）を、書く順番しだいで壊す。影響の範囲が全画面に広がる |
| C | `InboxPage.css` に受信箱だけの指定を足す | 共通の箱の決まりがページごとに散らばる（SSOT に反する）。他のページで同じ失敗が起きる |
| D | `HeaderButton` の部品の中で style を付ける | 受信箱は `HeaderButton` を使わず `Button` と `icon-btn` を直接並べている（`frontend/src/pages/inbox/InboxPage.tsx:87-113`）ので効かない |
| E | 吹き出しの見えないときの場所を消す（`display:none`） | 共通の作り（`:437-495`）を変えることになり、表示の切り替えの動き（`transition`）が無くなる |

## 5. 弊害・トレードオフと対処

| 弊害 | 対処 |
|---|---|
| `relative` にすると、ボタンが新しい重なりの基準になり、吹き出しが会話欄の下に隠れるおそれ | docs/handoff/inbox-header-tooltip-overflow/recon.md §3-1 で本番の画面で試し、設定の吹き出しが会話欄の上に見えることを確認済み。実装後も本番で K2 を目で確かめる |
| 他の5つのページの `.page-header-actions` にも当たる | その5つは `data-tooltip` を渡していない（docs/handoff/inbox-header-tooltip-overflow/recon.md §2-3）。`[data-tooltip]` が無い部品には当たらないので見た目は変わらない |
| カルテの見本写真の検査（1280×900）が変わるか | 写真は `.inbox-right-panel` だけを撮る（`frontend/tests-e2e/karte-visual-gate.spec.ts:395-404`）。ヘッダーは写らないので変わらない見込み。落ちたら実装カードの想定分岐で止める |

## 6. 受け入れ基準と検証方法

| 基準 | 検証方法 |
|---|---|
| K1 はみ出し 0px | Opus が本番反映の後に https://app.salesanchor.jp/lead-chat で `scrollHeight` と `innerHeight` を測り、生の値を記録に貼る |
| K2 吹き出しがボタンのすぐ下 | Opus が本番で3つのボタンにマウスを乗せ、画面写真で確かめる。あわせて各ボタンの `::after` の `top` が窓の高さより小さいことを測る |
| K3 横のはみ出し 0px | K1 と同じときに `scrollWidth` と `innerWidth` を測る |
| K4 機械で止める | 直す前のコードで新しい試験が落ちること・直した後に通ることを、GitHub の CI（画面検査（内部））の記録で示す（実績: 直す前 run 45206027638 で 768・1280 が赤、直した後 run 45209586531 で緑）。PR の CI「画面検査」が緑 |
| K5 生の数字なし・他の画面不変 | `npm run check:all` が緑。差分が §3-3 の2ファイル（と書類）だけであることを審査役が確かめる |

## 7. 外部・過去事例の参照と我々への応用

- CSS の仕様（MDN「position: absolute」）: 位置の基準は「position が static でない一番近い祖先」、無ければ最初の箱（ページ全体）。本件の原因と直し方はこの仕様そのものなので、他社の導入事例は要らない。
- 過去事例: 前の件（docs/handoff/inbox-pc-column-width/recon.md §3-1）で同じはみ出し 31px を観測し、対象外として残していた。本件で直す。

## 8. 維持の仕組み

- 守り手: frontend/tests-e2e/visual-language/inbox-page-no-vertical-overflow.spec.ts
- 対象: 受信箱のヘッダー右端の吹き出し付きボタンが位置の基準を失い、ページが縦にはみ出すこと。PR のたびに GitHub の CI（画面検査 768px・1280px）で確かめる。
- 関所なしの部分: 受信箱以外のページで、ヘッダーの箱の外に吹き出し付きの部品を置いた場合。共通の CSS の注意書き（`frontend/src/components.css:437-441`）と、本件で足すコメントで人手で守る。
