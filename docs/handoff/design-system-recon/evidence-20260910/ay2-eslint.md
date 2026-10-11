# ay2-eslint

base HEAD 08f59418c772fab0bed6137e818d5e87de5c91f2。pre-commit の lint-staged（frontend/package.json:53-58、`src/**/*.{ts,tsx}` → `eslint --max-warnings=0` / `node scripts/check-jsx-emoji.js` / `node scripts/check-css-var-fallbacks.js`）と同じ3コマンドを、text-like input を含む .tsx 83 ファイル（ay2-target-files.txt）に実行した結果。

コマンドと結果（生出力は ay2-eslint-raw.json / ay2-eslint-maxwarn.txt / ay2-emoji-check.txt / ay2-fallback-check.txt）:

| コマンド | 終了コード | 要約行 |
|---|---|---|
| `npx eslint --max-warnings=0 <83 files>` | 1 | `✖ 74 problems (0 errors, 74 warnings)` / `ESLint found too many warnings (maximum: 0).` |
| `node scripts/check-jsx-emoji.js <83 files>` | 0 | `✅ JSX絵文字チェック PASSED` |
| `node scripts/check-css-var-fallbacks.js <83 files>` | 0 | `✅ CSS var フォールバックチェック PASSED` |

## 警告があるファイル（pre-commit を止める。warnings >= 1）

| ファイル | 該当 input 数 | 警告数 | ruleId 内訳 | 備考 |
|---|---|---|---|---|
| frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx | 7（行 68,201,205,209,213,338,470。:470 は ref+onKeyDown 付きで G07 に含まれる） | 63 | `local/no-japanese-literal` 62、ruleId なし 1（行247: `Unused eslint-disable directive (no problems were reported from 'local/no-japanese-literal').`） | 日本語リテラル警告: 行 71,175,180-182,189,191,195-199,203,207,211,215,219,225-232,247,252,259,266,309,312,324-326,333-336,341,347,351,361,367,368,373,387-391,526,528,529 |
| frontend/src/features/tcg-analysis-review/SourceRawPane.tsx | 1（G34） | 11 | `local/no-japanese-literal` 10、`react-hooks/exhaustive-deps` 1 | 行 15,28,30(x9) |

警告数の合計 74（63 + 11）、エラー 0。上記 2 ファイル以外の 81 ファイルは警告 0。

注: ProductMasterDrawer.tsx:470 の input は ref/onKeyDown を持つ（ay2-handlers.md）。実際にこの2ファイルの input を TextFieldControl へ移す場合、同コミットで警告を解消しない限り lint-staged（`--max-warnings=0`）がコミットを止める（事実: 上表の終了コード 1）。他の 81 ファイルは現状この点で止まらない。

警告が 0 のファイル 81 本の一覧は ay2-target-files.txt から上記 2 本を除いたもの。
