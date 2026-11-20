# 製品の要件の書類を「作業の場面で目に入る」形にする（requirement-library）

> この文書は何か: AI が機能を直す・作る前に、その機能で決まっている要件（ADR・設計仕様書）を必ず目にして読むようにする取り組みの表紙。

- あるべき姿: [ideal-state.md](./ideal-state.md)
- KGI: [kgi.md](./kgi.md)
- 子文書:
  - recon（現在地の実測）: [../../handoff/requirement-library/recon.md](../../handoff/requirement-library/recon.md)
  - design（実現の設計）: [../../handoff/requirement-library/design.md](../../handoff/requirement-library/design.md)
- 関係する決定・仕様:
  - [ADR-1040](../../adr/ADR-1040-doc-agenda-nav-entry-index.md)（作業の決まりの入口→目次。本テーマは「製品の要件」を扱う兄弟テーマ）
  - [doc-agenda-nav](../doc-agenda-nav/README.md)（作業の決まりの本。練習問題で開いた割合を測る方法 K12 を本テーマも使う）
  - [機能 → ADR 索引](../../adr/FEATURE-INDEX.md)（本テーマで作り直す目録の正本）
  - 正本の手順: [docs/STANDARD-WORKFLOW.md](../../STANDARD-WORKFLOW.md) Phase 2（ADR 検索の義務）

## 境界

- 対象: 機能 → ADR 索引（docs/adr/FEATURE-INDEX.md）の中身と形、目録の抜けを数える CI、作業の場面で目録の行を差し出すリポジトリの見張り（.claude/settings.json と .claude/hooks/）、練習問題での測定。
- 対象外: 製品のコード・DB・画面。ADR・設計仕様書の本文の書き換え（指す先を足すだけ）。作業の決まり（doc-agenda-nav の範囲）。

## 状態

- 2026-11-21: あるべき姿（PO の言葉）・KGI R1〜R4 PO 承認済み（原文は kgi.md）。recon・design 作成中。実装未着手。
