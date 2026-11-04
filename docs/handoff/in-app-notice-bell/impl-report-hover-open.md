# 実装報告: PC の鈴はマウスを乗せると一覧が開く（card-hover-open.md）

結果: **DONE**（ただし確かめ 3 の e2e は流せなかった。下記）

- 開始 HEAD: d6c63ebab（一致を確認）
- 実装 commit: 17ef42640
- 変えたファイル（5 つ、合計 +182 / -4）:
  - frontend/src/components/Popover.tsx（+60 / -3 前後）
  - frontend/src/components/NoticeBell.tsx（2 か所、+2 / -2）
  - frontend/src/components/Popover.test.tsx（+89、describe 1 つ・it 6 つ）
  - frontend/src/components/Popover.stories.tsx（+14）
  - frontend/tests-e2e/visual-language/notice-bell.spec.ts（+16）
- 変更前の行はカードの記述と一致（行番号のずれのみ）。直値の色・寸法は無し。

## 確かめ

1. `npm ci` → 終了 0（最後: `npm notice ... To update run: npm install -g npm@12.2.1`）
2. vitest Popover.test.tsx + MultiSelect.test.tsx → 終了 0
   ```
   Test Files  2 passed (2)
        Tests  35 passed (35)
   ```
3. playwright notice-bell.spec.ts（vl-desktop-1280 / vl-mobile-390）→ **流せなかった**
   - 全 14 件が起動前に落ちた: `browserType.launch: Executable doesn't exist at /opt/pw-browsers/chromium_headless_shell-1217/...`
   - `npx playwright install chromium` も `Failed to download Chrome for Testing 147.0.7727.15 ... Download failure, code=1` で失敗。
   - 変更を退避した元のコードでも同じく落ちた（原因はブラウザ無しで、今回の変更ではない）。
   - 環境には chromium-1243 のみあり、版が合わない。executablePath の差し替えはカードに無いので行わなかった。
   - 追加の e2e（座標 `page.mouse.move(10, 700)`）は未検証。手元かブラウザのある環境で要確認。
4. `npm run lint` → 終了 0（`✖ 59 problems (0 errors, 59 warnings)`、既存の警告）／`npx tsc --noEmit` → 終了 0（出力なし）
5. `bash scripts/dev/check-before-submit.sh`（commit 後に再実行）→ 終了 0
   ```
   合計 10.6 秒 / 必須 16 件を表示 / 流した検査 18 件 / 落ちた検査 0 件
   結果: ○ 流した検査は全部通りました（終了コード 0）
   ```
   （commit 前に流したときは「commit していない変更があります」で終了 2。commit 後に通った）

## 最終 HEAD

実装 commit 17ef42640 の上に、この報告書の commit が 1 つ載る（push 後の HEAD は `git log` を参照）。
