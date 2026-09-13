# recon — B+C便（agent設定整合＋鮮度フック修理）

- 実施日: 2026-07-05 / 対象SHA: origin/main 302f33a4（実測時）
- 参照: docs/handoff/agent-guardrails/handoff-20260703.md §3-1

## file:line 引用表
| path:line | 確認内容 |
|---|---|
| `.claude/agents/generator.md:52` | `remove your row from active-work.md and commit the deletion`（B-2 矛盾箇所） |
| `.claude/agents/generator.md:179` | `# Critical rules`（B-1追加・B-3挿入のアンカー） |
| `docs/PARALLEL_TERMINAL_GUIDE.md:100` | `行は DONE で残す（active-work.md の行は削除しない）`（B-2一致先の正文） |
| `docs/ai-agents/design-partner.md:135` | `## 6. 実務の教訓`（§6開始） |
| `docs/ai-agents/design-partner.md:181` | `## 7. 変更・継続`（B-4挿入アンカー） |
| `.claude/hooks/check-freshness.sh:16,19,27,32` | `origin/develop` 参照（C・見張り先／比較基準） |
| `.claude/hooks/check-freshness.sh:41-45` | develop 前提の警告文（C・利用者向け文面） |
| `.claude/settings.json:35,39,45,51` | SessionStart で check-freshness.sh を起動（フック健在確認） |

## 確認事実
- generator.md 188行・二重掲載なし（CC transcript表示の重複と判別）。
- check-freshness.sh 47行・比較ロジック（merge-base起点blob直比較）は正常。develop参照のみ陳腐化。
- develop は凍結存続（handoff §4・SHA 1b9a93b7）＝永久に前進しない＝警告が永久沈黙。

## 不明点
- なし（B-1〜B-4・C の全アンカーを実測確定）。
