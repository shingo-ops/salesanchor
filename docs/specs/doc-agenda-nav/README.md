# AI向け指示文書の「入口→目次→章→末端ページ」化（doc-agenda-nav）

> この文書は何か: AI が会話のたびに読む文書を短い入口だけにし、手順書は目次をたどって必要なときだけ読む形に組み替える取り組みの表紙。

- あるべき姿: [ideal-state.md](./ideal-state.md)
- KGI: [kgi.md](./kgi.md)
- 子文書:
  - recon（現在地の実測）: [../../handoff/doc-agenda-nav/recon.md](../../handoff/doc-agenda-nav/recon.md)
  - design（実現の設計）: [../../handoff/doc-agenda-nav/design.md](../../handoff/doc-agenda-nav/design.md)
  - 引き継ぎ書（別セッション向け）: [../../handoff/doc-agenda-nav/handover.md](../../handoff/doc-agenda-nav/handover.md)
- 関係する決定・仕様:
  - [ADR-076](../../adr/ADR-076-claude-md-hierarchy.md)（CLAUDE.md の階層化・行数上限）
  - [ADR-113](../../adr/ADR-113-two-mode-dev-flow.md)（設計文書の書式 mode: handoff）
  - [文書の親子構造 標準ルール化](../doc-parent-child/README.md)（人が文書のつながりをたどれる形。本テーマは「AI が読む順番と量」を扱う兄弟テーマ）
  - 正本の手順: [docs/STANDARD-WORKFLOW.md](../../STANDARD-WORKFLOW.md) §1.5〜§1.8・§7

## 境界

- 対象: リポジトリの AI 向け指示文書（CLAUDE.md・AGENTS.md と frontend/backend の同2種、docs/STANDARD-WORKFLOW.md、docs/ai-agents/、docs/specs/README.md、docs/adr/FEATURE-INDEX.md）、商品マスタ登録ルールを差し込むフックの条件1行、目次の到達を検査する CI 1本（新設）。
- 対象外: docs/handoff（便ごとの作業記録。索引化しない）、docs/adr（docs/adr/README.md の自動生成で全件たどれる）、自動の覚え書き MEMORY.md、ユーザー個人の ~/.claude と ~/kb（別便）、画面（触らない）。

## 状態

- 2026-10-22: あるべき姿（PO の言葉）記録・KGI 草案（PO 未承認）・recon・design（自己審査 REVISE。PO 判断6件待ち。§10-1 は解決済み）・ADR 未起案・実装未着手。
- 以後の整備は別セッションが引き継ぐ（PO 2026-10-22）。引き継ぎ書: [handover.md](../../handoff/doc-agenda-nav/handover.md)
- 2026-10-22（引き継ぎ後）: KGI K1〜K7 **PO 承認済み**。design §10-3 解決（Codex 使用中 → 本文の正本を AGENTS.md に置き CLAUDE.md が取り込む向きへ変更）。PO 判断の残りは design §10 を正とする。
