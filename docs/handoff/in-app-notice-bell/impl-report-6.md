# impl-report-6（設計 7-3-改訂4）

1. 変えたファイルと行（frontend/）:
   - src/components/MobileShell.tsx: 右上の入れ物を削除（旧 :214-217）、メニューの直前に `<NoticeBell variant="tab" />`（:331-333）
   - src/components/NoticeBell.tsx: `variant?: "floating" | "tab"` 追加（:21-48）、tab の描画（:118-139）
   - src/components/NoticeBell.css: `.top-right-cluster--mobile` を消し `.notice-bell-tab-slot` 2 規則を追加（:21-32 付近）
   - src/components/MobileShell.test.tsx: :201 試験名、:208 の数 4→5
   - tests-e2e/visual-language/notice-bell.spec.ts: :83 数字の見つけ方、:122-137 スマホ幅の試験を 1 つ追加
2. 確かめの結果（生）:
   - npm ci: 終了 0
   - vitest run src/components: Test Files 62 passed (128) / Tests 833 passed (833) / Errors 1（Storybook 用ブラウザ chromium_headless_shell-1223 が入っておらず起動失敗。環境の問題。MobileShell・NoticeBell の試験は通過）
   - npm run check:all: 終了 0（lint 0 errors, 59 warnings）
   - npx tsc --noEmit: 4 errors、すべて触っていないファイル（api/generated/schema が無い: soldOutApi.ts・OwnInventoryPage.tsx・SoldOutResultsPanel.tsx）。触った 5 ファイルは 0 件
   - e2e（Playwright）: 流していない。CI で確かめる
3. 設計との違い: 無し。
4. 補足: executor-preflight.sh は gh が使えない（クラウド）ため FAIL。git fetch/push は通る。main の取り込みは衝突なし。

DONE
