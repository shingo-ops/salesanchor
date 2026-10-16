# AY-5d 設計: UIガバナンス検出種別の説明を5種に揃える

**対象ADR**: ADR-144
**recon**: docs/handoff/ay5d-ui-guard-kinds-docs/recon.md

## 1. 目的
検出は5種（select / text系input / checkbox / radio / 自作タブ）なのに、説明が3種のまま残っている。このため読んだ人・AI が、checkbox と radio も止まることを知らない。この状態を無くす（2026-10-16 PO「y」）。

## 2. 対象と対象外
- 対象: 3行の文字置換。
  - .github/workflows/ui-governance-gate.yml:3 のコメント
  - docs/BRANCH_PROTECTION_SETUP.md:314
  - CLAUDE.md:119
- 対象外: docs/handoff/ 配下（経緯記録）、scripts/check-ui-governance.js 本体。

## 3. 変更前後
- yml:3 「生select / 生input text+search+省略 / 自作タブ」→「生select / 生input text+search+省略 / 生checkbox / 生radio / 自作タブ」
- BRANCH_PROTECTION_SETUP.md:314 「生 `<select>`/`<input>`/タブ増加」→「生 `<select>`/`<input>`/checkbox/radio/タブ増加」
- CLAUDE.md:119 「生select/生input/自作タブ/色直値禁止」→「生select/生input/生checkbox/生radio/自作タブ/色直値禁止」

## 4. 影響範囲
文字だけの変更。CI の判定・画面・API・DB は変わらない。yml はコメント行のみを変える。

## 5. 代替案
- 列挙を消して、docs/CC_UI_GOVERNANCE.md への参照だけにする案もある。CLAUDE.md は常に読み込まれるので、列挙を残す方が誤りにくい。そのため不採用。

## 6. リスクと対処
- CLAUDE.md は行数が上限にある。同じ行の中で置換し、120行を保つ（check-claude-size.js は PASSED）。

## 7. 受け入れ基準
| 基準 | 検証方法 |
|---|---|
| 3か所すべてに checkbox と radio が入る | git diff で各1行置換 |
| 旧列挙「生select/生input/自作タブ」が対象3ファイルで0件 | git grep |
| CLAUDE.md が120行のまま | wc -l |
| CI 必須チェックが全て緑 | gh pr checks |

## 維持の仕組み
- 種別の正本は docs/CC_UI_GOVERNANCE.md の表とする。
- 種別を増やすときは、本3か所も同時に直す（ADR-144 追記節）。

## 外部・過去事例の参照と我々への応用
該当なし：文書の文言修正のみのため、外部事例は不要。過去事例として、AY-5b（#4375）で CC_UI_GOVERNANCE.md の表に radio 行を足した。今回はそれに合わせて残り3か所を揃える。

## 設計審査（Opus 自己審査）
APPROVE。変更は文字のみで、根拠は recon の行番号で確認済み。
