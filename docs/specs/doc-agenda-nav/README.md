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

- 対象: リポジトリの AI 向け指示文書（CLAUDE.md・AGENTS.md と frontend/backend の同2種、docs/STANDARD-WORKFLOW.md、docs/ai-agents/、docs/specs/README.md、docs/adr/FEATURE-INDEX.md）、商品マスタ登録ルールを差し込むフックの条件1行と免除の置き場1行、目次の到達を検査する CI 1本（新設）と既存の行数検査 CI の対象パス、ユーザー個人の ~/.claude と ~/kb の重複削除・短縮（design §8 段6・段7。段7は PO の実装承認待ち）。
- 対象外: docs/handoff（便ごとの作業記録。索引化しない）、docs/adr（docs/adr/README.md の自動生成で全件たどれる）、自動の覚え書き MEMORY.md、ユーザー個人の ~/.claude と ~/kb のうち段6・段7 以外、画面（触らない）。

## 状態

- 2026-10-22: あるべき姿（PO の言葉）記録・KGI 草案（同日 PO 承認済み・下の行）・recon・design（自己審査 REVISE。PO 判断5件待ち（§10-2・§10-4〜§10-7）。§10-1・§10-3 は解決済み）・ADR 未起案・実装未着手。
- 以後の整備は別セッションが引き継ぐ（PO 2026-10-22）。引き継ぎ書: [handover.md](../../handoff/doc-agenda-nav/handover.md)
- 2026-10-22（引き継ぎ後）: KGI K1〜K7 **PO 承認済み**。KGI の測り方修正（K1・K5・K7）と K8〜K10 の追加も PO 承認済み（原文「1」）。design §10-3 PO 回答済み（Codex 使用中）。本文の正本を AGENTS.md に置き CLAUDE.md が取り込む構造も PO 承認済み（原文「1」）。PO 判断の残りは design §10 を正とする。
- 2026-10-22: design 審査7回目 APPROVE（HEAD 084764bf3）。§10-2 入口の上限は PO 原文「1」で 90行（AGENTS.md 80・CLAUDE.md 10）。
- 2026-10-22: 残りの判断（design §10-4〜§10-7・§11 の安全寄りの3文）は PO 原文「fableにまかせてくれ」で Fable が決め、design に反映。PO 向けの全体図は design §20。上の行の「PO 判断5件待ち」は解消。
- 2026-10-22: design 審査8回目・9回目（いずれも REVISE）の指摘を反映（design §21・§22）。
