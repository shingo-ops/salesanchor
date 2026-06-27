# Design: 関所の自己保護（DANGEROUS_PATTERNS 拡張）

日付: 2026-06-24
参照 recon: docs/handoff/sop-gate-self-protect/recon.md
関連 ADR: なし（process-artifacts gate 拡張・ADR-136 GO手順に準拠）

---

## 0. 一行サマリ

関所本体・宣言テンプレ・正本ワークフローの3ファイルを `DANGEROUS_PATTERNS` に追加し、
これらを変更する PR に GO 記録を必須とする（自己保護）。

---

## ① KGI

- `docs/STANDARD-WORKFLOW.md` / `.github/workflows/process-artifacts-gate.yml` / `.github/PULL_REQUEST_TEMPLATE.md` を変更する PR が GO 記録なしでマージされたら process-artifacts gate が赤になる
- GO 記録ありなら緑

---

## ② なぜ必要か

追加前の分類:

| ファイル | 分類 | GO必須 |
|---|---|---|
| `docs/STANDARD-WORKFLOW.md` | `docs` → 早期pass | × |
| `.github/workflows/process-artifacts-gate.yml` | `real-code` | × |
| `.github/PULL_REQUEST_TEMPLATE.md` | `docs` → 早期pass | × |

`classifyFile` の評価順は dangerous(`:74`) → docs(`:75`) → real-code(`:76`)。
`DANGEROUS_PATTERNS` に追加すれば docs/real-code 判定より先に `'dangerous'` を返す。
`hasDocsOnly = !hasDangerous && !hasRealCode`（`:83`）なので、`hasDangerous=true` になれば早期passも回避される。

---

## ③ 変更内容（Generatorは判断ゼロで実装可）

**変更ファイル:** `scripts/check-process-artifacts.js` のみ

**変更箇所:** `DANGEROUS_PATTERNS` 配列の `:51`（pages-layout.cssの行）直後に3行追加

```js
  /^docs\/STANDARD-WORKFLOW\.md$/,                      // 正本（自己保護）
  /^\.github\/workflows\/process-artifacts-gate\.yml$/, // 関所ワークフロー（自己保護）
  /^\.github\/PULL_REQUEST_TEMPLATE\.md$/,              // 宣言テンプレ（自己保護）
```

**触らない範囲:** 他パターン・`classifyFile`・他ファイル

---

## ④ 受け入れ基準（○×実証手順）

| 基準 | 検証方法 | 期待 |
|---|---|---|
| `docs/STANDARD-WORKFLOW.md` 変更 + GO記録なし → 赤 | `CHANGED_FILES=docs/STANDARD-WORKFLOW.md MOCK_PR_BODY=<GO記録なし> node scripts/...` | EXIT=1 |
| `.github/PULL_REQUEST_TEMPLATE.md` 変更 + GO記録なし → 赤 | 同上 | EXIT=1 |
| `.github/workflows/process-artifacts-gate.yml` 変更 + GO記録なし → 赤 | 同上 | EXIT=1 |
| GO記録ありなら → 緑 | GO記録入りMOCK_PR_BODYで実行 | EXIT=0 |
