# recon — process-artifacts gate precision fix

測定日: 2026-06-19

## 事実

- gate 本体は `scripts/check-process-artifacts.js` で、実行入口は `.github/workflows/process-artifacts-gate.yml:13-30`。
- 誤検知の起点は `extractFileCitations()` のバッククォート抽出と実在チェック。
- `parseSOPDeclaration()` の recon/design 実在確認は別系統で、今回の精度改善では維持する。
- 受け入れテストは `scripts/tests/test-process-artifacts.js` にある。

## 参照

- `scripts/check-process-artifacts.js:77-88`
- `scripts/check-process-artifacts.js:196-230`
- `scripts/tests/test-process-artifacts.js:274-339`
- `.github/workflows/process-artifacts-gate.yml:13-30`
