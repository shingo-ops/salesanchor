# recon — 柱2 正本ガード（書類スキップの穴）

> この文書は何か（専門用語なしの1行）:
> 「書類だけのPRは検査を飛ばす」抜け穴が、どこに・どう開いていたかを実物で確かめた記録。

**対象ADR**: ADR-121
**設計**: docs/specs/process-hardening/design-pillar2.md
**親（あるべき姿）**: docs/specs/process-hardening/ideal-state.md

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|---|---|
| `scripts/check-process-artifacts.js:42` | DOCS_PATTERNS の定義。`.md` が docs 区分に落ちる |
| `scripts/check-process-artifacts.js:65` | DANGEROUS_PATTERNS。STANDARD-WORKFLOW.md 等は既に自己保護済み |
| `scripts/check-process-artifacts.js:101` | classifyChanges。hasDocsOnly の算出箇所 |
| `scripts/check-process-artifacts.js:104` | hasDocsOnly は危険もコードも無い時に true |
| `scripts/check-process-artifacts.js:54` | 追加した CANONICAL_DOCS_PATTERNS（正本4パターン） |
| `scripts/check-process-artifacts.js:62` | hasCanonicalDoc（正本を含むかの判定） |
| `scripts/check-process-artifacts.js:683` | 正本を含まない書類のみは従来どおり自動スキップ |
| `scripts/check-process-artifacts.js:688` | 正本を含む場合は宣言照合へ進む（本柱の修正点） |
| `scripts/tests/test-process-artifacts.js:613` | 柱2-欠落版（宣言なし → fail） |
| `scripts/tests/test-process-artifacts.js:622` | 柱2-充足版（正本を含むと照合ステージへ進む） |
| `scripts/tests/test-process-artifacts.js:638` | 柱2-中立版（正本を含まない純書類は従来どおりスキップ） |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|---|---|---|
| 1 | 正本を一律 `.md` で判定すると台帳を巻き込まないか | 実測。`.claude-pipeline/active-work.md` は正本4パターンのいずれにも当たらないことを確認 | 解消済み |
| 2 | 正本の実数と網羅範囲 | git ls-files で実測。ideal-state 42・kgi 41・ai-agents 直下 12・CLAUDE/AGENTS 2 = 97件 | 解消済み |
| 3 | PR番号2600の猶予が正本保護を妨げないか | 最新PR番号が3000超のため将来PRに猶予は掛からないと実測 | 解消済み |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

- 過去の書類のみPR5件（#3012 #3005 #3004 #3002 #2991）に本ガードを当てた試算では、5件とも宣言完備で pass 想定・fail 想定 0件。
- 実測は refs/remotes/origin/main を明示参照して行った（ローカルに同名ブランチが存在し `origin/main` が曖昧なため）。
