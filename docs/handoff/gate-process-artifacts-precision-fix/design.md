# design — process-artifacts gate precision fix

## 目的

バッククォート内の拡張子なし語を file citation と誤認しないようにする。

## 方針

- `extractFileCitations()` は `.md/.js/.ts/.tsx/.py/.yml/.yaml/.json` を持つパスのみ存在チェックする。
- `parseSOPDeclaration()` の recon/design 実在チェックは変更しない。
- テストで次を保証する。
  - `scope=mine`、`FunnelSection`、`/analytics/weekly-advisor-defensive`、`tenant_006` は無視される。
  - 実在しない `docs/.../recon.md` や `backend/.../file.py:1` のような本物の file citation は fail する。

## 参照

- `scripts/check-process-artifacts.js:77-88`
- `scripts/check-process-artifacts.js:196-230`
- `scripts/tests/test-process-artifacts.js:274-339`
