# design: 審査担当を Fable から Opus へ（2026-10-15）

## 目的
PO 決定（2026-10-15）「上限に達した場合の代替え案としてOPUSのに審査させる、FABLEの審査を廃止して標準はOPUSが審査する方法に変更」を、規則の正本に反映する。Fable の利用上限で審査が止まり、便全体が止まった（PR #4300 のコード審査）ことが発端。

## 変更（recon.md の「変更前」8ファイル）
- architect・reviewer の `model: fable` → `model: opus`
- 規則文の「Fable 審査」→「Opus 審査」、記録名 review-fable.md → review-opus.md（今後の記録名。過去のファイルは改名しない）
- ADR-1011・ADR-1015 の備考に「2026-10-15 PO 決定で、審査担当を Fable から Opus へ変更」を追記
- 対象外: recon.md の「残すもの」

## 受入条件
| 基準 | 検証方法 |
|---|---|
| architect.md・reviewer.md の model が opus | `grep -n '^model:' .claude/agents/architect.md .claude/agents/reviewer.md` |
| 規則として Fable を審査担当に定める行が0 | `grep -rn -i fable AGENTS.md docs/STANDARD-WORKFLOW.md docs/ai-agents/design-partner.md .github/PULL_REQUEST_TEMPLATE.md docs/adr/ADR-1011-permission-self-maintenance.md` が0件、ADR-1015 は 51・56 行（経緯）と備考のみ |
| ADR 索引が最新 | `node scripts/generate-adr-index.js` 後に差分なし |

## 外部事例
不要（社内の担当割り当ての変更で、外部の前例が判断材料にならない）。

## 切り戻し
本 PR の merge commit を revert する。

## 維持の仕組み
守り手: .claude/agents/architect.md・reviewer.md の frontmatter（Agent 呼び出し時の既定モデル）と ADR-1015（B 区分の審査担当の正本）。変更は PR と PO 決定のみ。
