# visual-check-dedup 設計（画面検査の重複をなくす）

## 1. 目的（PO の言葉）

PO 2026-11-03 チャット「2」: 画面検査（内部）が長くかかる理由のうち、同じ確かめを2回流している分を先になくす。PR #5040 はそのあとに入れる。

成功条件（○×で判定）:

| 基準 | 検証方法 |
|---|---|
| K1 収集件数が 816 → 594 になる | `cd frontend && E2E_NO_WEBSERVER=1 npx playwright test --list --project=vl-mobile-390 --project=vl-tablet-768 --project=vl-desktop-1280` の末尾の件数 |
| K2 CI の画面検査（内部）で 511 件 passed・83 件 skipped・failed 0 | 本 PR の CI ジョブのログ末尾 |
| K3 画面検査（内部）が 15 分の上限内で終わる（実測の分数を PR に記録） | 本 PR の CI ジョブの所要時間 |
| K4 幅を自分で決めない spec（受信箱系・app-update-notice）の収集件数は 3 project とも変わらない | K1 の list を project ごとに数える（vl-mobile-390 272・vl-tablet-768 50・vl-desktop-1280 272） |
| K5 一覧に載せた spec が project の幅・触る扱いを読み始めたら、設定の読み込みで止まる | 一覧の spec に `testInfo.project` を1行足して `--list` を流すと失敗する（手元で確かめて戻す） |

## 2. 現在地（recon.md より）

- 3 project は frontend/playwright.config.ts:62-76。vl-mobile-390 だけ isMobile・hasTouch（:65）。
- 16 spec（recon.md 7節の表で C の spec）は最初の goto の前に幅を自分で決める（gotoViewer: frontend/tests-e2e/visual-language/viewer-helpers.ts:137-140、gotoInventory: frontend/tests-e2e/visual-language/inventory-helpers.ts:110-112、または spec 内の setViewportSize）。project・触る扱いを読む test は 0 件（recon.md 5節）。
- 222 test × 3 = 666 回がこの 16 spec。
- recon.md は「3幅とも同じ（C）」と分類したが、Opus が公式資料で確かめた結果、スマホの回は別の確かめである:
  - Playwright 公式: isMobile は「meta viewport を考慮し touch events を有効にする」（docs/src/api/params.md context-option-ismobile、Context7 /microsoft/playwright で 2026-11-03 確認）。
  - hasTouch:true は Chromium に `Emulation.setTouchEmulationEnabled` を送り、`(hover: hover)` が false になる（packages/playwright-core/src/server/chromium/crPage.ts、tests/library/browsercontext-viewport-mobile.spec.ts。同日 Context7 で確認）。
  - アプリには `@media (hover: hover)` が4か所ある（frontend/src/components/MultiSelect.css:46、frontend/src/pages/viewer/viewer.css:111、frontend/src/pages/inventory/InventoryToolbar.css:61、frontend/src/pages/inbox/InboxPage.css:1873）。frontend/viewer/index.html:6 の meta viewport も isMobile のときだけ効く。
  - よって 16 spec は正しくは B（タブレットとパソコンが同じ・スマホは別）。vl-tablet-768 と vl-desktop-1280 はどちらも Desktop Chrome で isMobile・hasTouch なし（:70,:75）、幅は spec が上書きするので、この2回は同じ確かめになる。
- 既存 ADR: 3 幅の扱いを決めた ADR は無い（recon.md 6節）。docs/specs/design-system/visual-language/design.md:53 は「3幅の画面検査を作る」目標で、各 test を3回流せとは書いていない。

## 3. 変えること

frontend/playwright.config.ts だけ（e2e.yml はコメント1行の更新のみ）。

変更前（:67-71）:

```ts
    {
      name: "vl-tablet-768",
      testMatch: /visual-language\/.*\.spec\.ts/,
      use: { ...devices["Desktop Chrome"], viewport: { width: 768, height: 1024 } },
    },
```

変更後:

- config の上部に、幅を自分で決める spec の一覧 `SELF_WIDTH_SPECS`（ファイル名16個の配列）を1か所だけ置く。中身は recon.md 7節の表で C の16 spec。
- vl-tablet-768 に `testIgnore` を足し、この一覧の spec を外す。vl-mobile-390 と vl-desktop-1280 は変えない。
- 見張り（K5）: config の読み込み時に一覧の各 spec を読み（node:fs）、次のどれかを含めば `throw new Error(...)` で止める。一覧の spec が存在しないときも止める。
  - `.project`（testInfo.project・test.info().project）・`projectWidth`・`hasTouch`・`touchscreen`・`.tap(`
  - test の引数で Playwright の isMobile を受け取る形（正規表現 `async \(\{[^)]*\bisMobile\b`）
  - 単語 `isMobile` そのものは止めない。いまの 16 spec はアプリ側の幅の判定（frontend/src/hooks/useIsMobile.ts）の説明としてコメントに書いている（drawer-inert-closed.spec.ts:31、popover-mold.spec.ts:8、viewer-focus-trap.spec.ts:29,50）。
  - `page.viewportSize()` も止めない。inventory-mobile-baseline.spec.ts:153・inventory-raw-text-mobile.spec.ts:59 は spec が自分で決めた幅を読み直すだけで、2つの project で同じ値になる。
  - 実装後、いまの 16 spec で見張りが止めないこと（K1 の `--list` が通る）を確かめる。
- コメントに理由（vl-desktop-1280 と同じ確かめになるため・スマホは hover と meta viewport が違うので残す・根拠は本 design.md）を書く。
- .github/workflows/e2e.yml:150 の古いコメント「現状 2 本・テスト 8 件」を「20 本。幅を自分で決める spec は vl-tablet-768 で流さない（frontend/playwright.config.ts）」に直す。timeout-minutes は変えない。

外すのを vl-tablet-768 にした理由: vl-desktop-1280 と同じ確かめなのでどちらを外しても失う確かめは無い。app-update-notice が 390 と 1280 を対象にしており（recon.md 3節）、パソコン幅の回を基準に揃える。

触らない範囲: spec・helper・アプリのコード・スナップショット画像・vl-mobile-390・vl-desktop-1280・受信箱系 spec（幅を自分で決めないので 768 の回は別の確かめ）・timeout-minutes・workers。

## 4. 代替案

| 案 | 採らない理由 |
|---|---|
| 16 spec をスマホの回だけで流す | スマホの回は hover:none・meta viewport が効く。パソコン相当の扱いの確かめが消える |
| 15分の上限を25分に延ばす | 同じ確かめを流す無駄が残る。PO が「2」で先に重複をなくすと決めた |
| spec ごとに test.skip を書く | 16 か所に散る。一覧が1か所に無いと抜け・二重が起きる |

## 5. リスクと対処

- 一覧に載せた spec が後で project の幅を読み始めると、タブレット幅の確かめが黙って抜ける → K5 の見張りで config 読み込み時に止める。
- 新しい spec を一覧に足し忘れる → 3回流れるだけで確かめは失わない（遅くなるだけ）。
- 時間がどこまで縮むかは未確認 → K3 で実測し PR に記録する。

## 6. 戻し方・測り方

- 戻し方: 本 PR の revert（config とコメントだけ）。
- 測り方: 基準値は変更前の CI 実測（816 件・733 passed・83 skipped・13.6分、PR #5040 の run 41562593512 / 41564866990 は15分で打ち切り）。変更後は K1〜K3。

## 7. 維持の仕組み

- 守り手: frontend/playwright.config.ts の見張り（K5）。CI の画面検査（内部）と手元の `npx playwright test` で毎回読み込まれる。

## 8. 外部・過去事例の参照と我々への応用

- 外部事例は使わない。理由: 判断の根拠は Playwright 公式資料（isMobile・hasTouch の働き）と本リポジトリの実測（recon.md）で足り、他社の数値はこの重複の有無の証明にならない。
- 過去事例: PR #5040 の run 41562593512 / 41564866990 が15分で打ち切られた（本リポジトリの実測）。我々への応用: 上限を延ばす前に、同じ確かめの重複を先に除く（4節の代替案）。

## 9. 審査（Opus 自己審査・独立した第二者レビューではない）

- 判定: APPROVE（設計合格）
- 根拠: 変更は config 1か所で、失う確かめが無いことを公式資料と recon.md 5節（project・触る扱いを読む test 0件）で確かめた。受入条件は件数と CI ログで○×が付く。
- 未解決: 所要時間の縮み幅（K3 で実測）。
