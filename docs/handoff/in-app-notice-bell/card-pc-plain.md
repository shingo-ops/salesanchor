# 実装カード: PC の鈴の丸い囲みを外す（design.md §7-3-改訂5）

- 設計: docs/handoff/in-app-notice-bell/design.md §7-3-改訂5（Architect 自己審査 APPROVE）
- PO 承認: 「PCの鈴マークは丸いアイコンで囲わなくて良い」（2026-11-04）／マウスを乗せたときは「3」（鈴の色だけ濃くなる、2026-11-04）
- ブランチ: release/notice-bell-pc-plain（origin の先頭 968e1e695 から）
- 触ってよいファイル（この 3 つと報告書 docs/handoff/in-app-notice-bell/impl-report-pc-plain.md だけ）:
  - frontend/src/components/NoticeBell.css
  - frontend/src/components/NoticeBell.tsx
  - frontend/tests-e2e/visual-language/notice-bell.spec.ts
- 触らない: tokens.css・Badge の金型（Badge.tsx / Badge.css）・DesktopShell・MobileShell・topbar.css・i18n（ja.json / en.json）・backend・openapi.json。スマホの形（`variant="tab"` の分岐、NoticeBell.tsx:118-136 付近）は 1 文字も変えない

## §1 frontend/src/components/NoticeBell.css（変更前は :32-56）

変更前:

```css
.notice-bell-btn {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--notice-bell-size);
  height: var(--notice-bell-size);
  border: 1px solid var(--border);
  border-radius: var(--radius-full);
  background: var(--bg-surface);
  color: var(--text-secondary);
  box-shadow: var(--shadow-md);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.notice-bell-btn:hover {
  background: var(--bg-hover);
}

.notice-bell-badge {
  position: absolute;
  top: calc(var(--space-1) * -1);
  right: calc(var(--space-1) * -1);
}
```

変更後:

```css
.notice-bell-btn {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--notice-bell-size);
  height: var(--notice-bell-size);
  border: none;
  border-radius: var(--radius-full);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: color var(--transition-fast);
}

.notice-bell-btn:hover {
  color: var(--text-primary);
}

.notice-bell-badge {
  position: absolute;
  top: var(--space-1);
  right: var(--space-1);
}
```

## §2 frontend/src/components/NoticeBell.tsx（PC の形だけ。変更前は :143）

- 変更前: `<BellOutline size={ICON.md} aria-hidden="true" />`（`className="notice-bell-btn"` のボタンの中）
- 変更後: `<BellOutline size={ICON.base} aria-hidden="true" />`
- この 1 行以外は変えない。`ICON.base` は既に import 済みの `ICON` の値（frontend/src/constants/iconSizes.ts）

## §3 frontend/tests-e2e/visual-language/notice-bell.spec.ts（末尾の `test.describe` の中、最後の test の後に 1 つ足す）

```ts
  test("PC: 鈴に丸い囲み・枠・影が無く、赤い数字は鈴の箱の内側。乗せると色だけ変わる", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "vl-desktop-1280", "1280 のみ");
    await setup(page, 3);
    const btn = page.locator(".notice-bell-btn");
    await expect(btn).toBeVisible({ timeout: 10_000 });
    const style = () =>
      btn.evaluate((el) => {
        const s = getComputedStyle(el);
        return { border: s.borderTopWidth, shadow: s.boxShadow, bg: s.backgroundColor, color: s.color };
      });
    const before = await style();
    expect(before.border).toBe("0px");
    expect(before.shadow).toBe("none");
    expect(before.bg).toBe("rgba(0, 0, 0, 0)");
    await expect(badge(page)).toHaveText("3");
    const b = await btn.boundingBox();
    const g = await badge(page).boundingBox();
    expect(b).not.toBeNull();
    expect(g).not.toBeNull();
    expect(g!.x).toBeGreaterThanOrEqual(b!.x);
    expect(g!.y).toBeGreaterThanOrEqual(b!.y);
    expect(g!.x + g!.width).toBeLessThanOrEqual(b!.x + b!.width);
    expect(g!.y + g!.height).toBeLessThanOrEqual(b!.y + b!.height);
    await btn.hover();
    await expect.poll(async () => (await style()).color).not.toBe(before.color);
    expect((await style()).bg).toBe("rgba(0, 0, 0, 0)");
  });
```

## 想定される分岐（推測で埋めず止まる）

- 変更前の CSS / TSX の行が上と一致しない（行番号のずれ以上の違い）→ NEEDS_DECISION:
- 足した試験で、数字の箱がボタンの外にはみ出して落ちる → `top/right` の値を自分で変えず NEEDS_DECISION:（実測の座標を報告書に書く）
- `color` が乗せる前後で同じで落ちる → `--text-secondary` と `--text-primary` の実値を報告書に書いて NEEDS_DECISION:
- 色・寸法の直値（#xxx・px）を書きたくなった → 書かずに NEEDS_DECISION:

## 確かめ（Mac では流さない。クラウドで流す）

1. `cd frontend && npm ci`
2. `npx playwright test tests-e2e/visual-language/notice-bell.spec.ts --project=vl-desktop-1280 --project=vl-mobile-390`（ブラウザが無ければ `npx playwright install chromium` を先に。入れられなければ流せなかったと書く）
3. `npm run lint` → `npx tsc --noEmit`
4. リポジトリ直下で `bash scripts/dev/check-before-submit.sh`

報告書 docs/handoff/in-app-notice-bell/impl-report-pc-plain.md に、各確かめの最後の数行の生出力・変えたファイルと行数・最終 HEAD・DONE / BLOCKED: / NEEDS_DECISION: のどれかを書く。
