# recon — process-artifacts ADR precision fix

**仕事名**: process-artifacts-adr-precision-fix  
**日付**: 2026-06-21  
**対象ADR**: 無し（新規不要）  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|---|---|
| `scripts/check-process-artifacts.js:77-114` | `parseSOPDeclaration()` が PR 本文の `### 標準ワークフロー確認` から `対象ADR:` を抽出する現行実装 |
| `scripts/check-process-artifacts.js:253-317` | `validateDesignDoc()` の ADR 相互参照確認と、ADR ファイル名の境界付き照合ヘルパー |
| `scripts/check-process-artifacts.js:385-400` | `runFullCheck()` が PR 本文の全 ADR をまとめて検証し、1件でも不在なら fail する経路 |
| `scripts/tests/test-process-artifacts.js:161-178` | 単数/複数 ADR の parse テスト |
| `scripts/tests/test-process-artifacts.js:411-418` | 複数 ADR の designDoc 相互参照テスト |
| `scripts/tests/test-process-artifacts.js:575-620` | 実在 ADR 4命名バリエーション、境界、複数 ADR の受け入れテスト |
| `docs/adr/README.md:1-4` | ADR 索引は自動生成で、本体は `docs/adr/*.md` が正本であること |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|---|---|---|
| 1 | ADR-100 など短い番号参照の境界を gate が見逃すか | 境界テスト追加で確認 | ✅ 解消済み |
| 2 | 複数 ADR を PR 本文に書いたとき 1件ずつ検査されるか | parse + runFullCheck + validateDesignDoc を複数対応に修正 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
