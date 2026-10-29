/**
 * visual-language/app-update-notice.spec.ts
 * — 「新しい版があります・更新」の知らせの画面検査（受入条件 K6）
 *
 * design: docs/handoff/app-update-notice/design.md §5 K6。
 * 幅 390（vl-mobile-390）と 1280（vl-desktop-1280）で、知らせが出た状態の写真を撮り、
 * 横のはみ出しが無いこと・ボタンの高さが 44px 以上であることを測る。
 *
 * 知らせの出し方（本体に試験専用の抜け道は足さない）:
 *  ・試験は Vite 開発サーバーで動くため、入口の script は /assets/main-*.js の形ではない。
 *    そこで開いたあとに「今の画面が読み込んだ main-<hash>.js」の script 要素を足し（応答は空の JS）、
 *  ・入口 `/` の取り直しの応答だけ route で別の main-<hash>.js の名前に差し替え、
 *  ・Date.now を2分進めて 60 秒の間引きを越え、裏から表に戻す操作（visibilitychange）を起こす。
 */
import { expect, test } from "@playwright/test";
import { openInboxList } from "./inbox-helpers";

const MIN_TAP_PX = 44;
const TARGET_PROJECTS = ["vl-mobile-390", "vl-desktop-1280"];

test.describe("app-update-notice (K6)", () => {
  test("shows the notice at the top without horizontal overflow, with a 44px+ button", async ({ page }, testInfo) => {
    test.skip(!TARGET_PROJECTS.includes(testInfo.project.name), "390 と 1280 のみ");

    await openInboxList(page);
    await expect(page.getByTestId("app-update-notice")).toHaveCount(0);

    await page.route("**/assets/main-OLDOLD01.js", (route) =>
      route.fulfill({ status: 200, contentType: "text/javascript", body: "" }),
    );
    await page.route(
      (url) => url.pathname === "/",
      (route) =>
        route.fulfill({
          status: 200,
          contentType: "text/html",
          body: '<!doctype html><html><head><script type="module" crossorigin src="/assets/main-NEWNEW02.js"></script></head><body></body></html>',
        }),
    );

    await page.evaluate(() => {
      const el = document.createElement("script");
      el.type = "module";
      el.src = "/assets/main-OLDOLD01.js";
      document.head.appendChild(el);
      const orig = Date.now.bind(Date);
      Date.now = () => orig() + 120_000;
      Object.defineProperty(document, "hidden", { configurable: true, value: true });
      document.dispatchEvent(new Event("visibilitychange"));
      Object.defineProperty(document, "hidden", { configurable: true, value: false });
      document.dispatchEvent(new Event("visibilitychange"));
    });

    const notice = page.getByTestId("app-update-notice");
    await expect(notice).toBeVisible({ timeout: 10_000 });

    const box = await notice.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.y).toBeLessThan(40);

    const { scrollWidth, innerWidth } = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth: window.innerWidth,
    }));
    expect(scrollWidth).toBeLessThanOrEqual(innerWidth);

    const btn = notice.getByRole("button");
    await expect(btn).toBeVisible();
    const btnBox = await btn.boundingBox();
    expect(btnBox).not.toBeNull();
    expect(btnBox!.height).toBeGreaterThanOrEqual(MIN_TAP_PX);

    await testInfo.attach("app-update-notice", {
      body: await page.screenshot(),
      contentType: "image/png",
    });
  });
});
