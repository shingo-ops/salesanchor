# 実装報告: PC の鈴の丸い囲みを外す（card-pc-plain.md）

## 結果

**DONE**（ただし確かめ2の playwright は流せなかった。未確認）

## 変えたファイル

実装 commit 7e7fb7e9f（開始 HEAD は 260a39cf3 と一致を確認）

- frontend/src/components/NoticeBell.css（+6 / -7 付近）
- frontend/src/components/NoticeBell.tsx（1 行: ICON.md → ICON.base）
- frontend/tests-e2e/visual-language/notice-bell.spec.ts（+28）
- 合計 3 files changed, 35 insertions(+), 8 deletions(-)

カードの変更前と実物は一致していた。スマホの形・tokens.css・Badge・i18n・backend は触っていない。

## 確かめ

1. npm ci: 終了コード 0

2. playwright（notice-bell.spec.ts を vl-desktop-1280 と vl-mobile-390）: **流せなかった**（終了コード 1、12 件すべて起動前に失敗）

```
Error: browserType.launch: Executable doesn't exist at /opt/pw-browsers/chromium_headless_shell-1217/chrome-headless-shell-linux64/chrome-headless-shell
  12 failed
```

`npx playwright install chromium` も失敗:

```
Error: Failed to download Chrome for Testing 147.0.7727.15 (playwright chromium v1217), caused by
Error: Download failure, code=1
```

この環境の /opt/pw-browsers にあるのは 1243 版で、プロジェクトの playwright が求める 1217 版とずれている。足した試験が通るかは未確認。

3. npm run lint: 終了コード 0

```
✖ 59 problems (0 errors, 59 warnings)
```

   npx tsc --noEmit: 終了コード 0（出力なし）

4. bash scripts/dev/check-before-submit.sh（commit 後に流した。commit 前は終了コード 2 で止まる）: 終了コード 0

```
合計 9.3 秒 / 必須 16 件を表示 / 流した検査 18 件 / 落ちた検査 0 件
結果: ○ 流した検査は全部通りました（終了コード 0）
```

## 最終 HEAD

この報告書の commit 後に確定（push 後の `git rev-parse HEAD` を参照）。実装 commit は 7e7fb7e9f。
