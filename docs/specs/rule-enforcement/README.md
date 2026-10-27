# 決まりを機械の検査に変える（rule-enforcement）

> この文書は何か: 誰が作業しても決まりが守られ、決まり違反の変更が本番に出ないように、決まりを1つずつ機械の検査に変える取り組みの表紙。

- あるべき姿: [ideal-state.md](./ideal-state.md)
- KGI: [kgi.md](./kgi.md)
- 子文書:
  - recon（現在地の実測）: [../../handoff/rule-enforcement/recon.md](../../handoff/rule-enforcement/recon.md)
  - design（実現の設計）: [../../handoff/rule-enforcement/design.md](../../handoff/rule-enforcement/design.md)
- 関係する決定・仕様:
  - [ADR-136](../../adr/ADR-136-cc-bot-github-identity.md)（Ruleset の承認数を使わず、記録を検査スクリプトで確かめる）
  - [ADR-135](../../adr/ADR-135-release-stowaway-prevention.md)（必須チェックの登録・bypass_actors）
  - [ADR-1029](../../adr/ADR-1029-review-gate-hook.md)（マージ前の審査役 APPROVE）
  - [ADR-1040](../../adr/ADR-1040-doc-agenda-nav-entry-index.md)（警告で始め、連続 5 回の PR で 0 件なら失敗に上げる）
  - 正本の手順: [docs/STANDARD-WORKFLOW.md](../../STANDARD-WORKFLOW.md)

## 境界

- 対象: kgi.md「決まりの文書」に挙げた文書の決まり、main の必須チェック（ruleset 15777895）、本番の鍵を使う GitHub の自動作業、本番の VPS と PO の Mac にある自前の実行機、提出前に検査を走らせる入口（手元の Claude・クラウドの Claude・Husky）、週次点検の項目。
- 対象外: 既存の必須チェック 16 件の検査内容の変更、ruleset の承認数（ADR-136 で不採用）、deploy.yml の手順の中身（本番の鍵を main だけにするため `environment:` の 1 行は足す）、`.github/workflows/workflow-lint.yml`、製品コード（backend/・frontend/src/）、develop ブランチ。

## 状態

- 2026-10-27: KGI G1〜G5 PO 承認（原文「1」）。recon・design 作成。設計審査1〜4回目 REVISE → 反映済み、5回目 APPROVE。審査で見つかった「本番に触れる別の道」と「決まりの文書の範囲」も、KGI の範囲として PO 承認（原文「1」＝範囲を広げる。kgi.md「範囲の確認」）。
- 2026-10-27: R0 に進む PO 承認（D1、原文「1」）。設計を main に反映（#4815）。R0（読み取り調査）完了、結果は recon §12。R0.5 以降の実装は未着手。D2〜D6 は PO 判断待ち。
- 2026-10-27: R1a（台帳 `rules.yml` と台帳の検査を警告で開始）は main に反映（#4818）。R1b で決まりの語を含む 400 行をすべて仕分けた（未仕分け 0）。決まりの決め方は [ADR-1047](../../adr/ADR-1047-rule-registry.md)（Proposed）。決まりの語の一覧を広げることと、週次点検への「required-checks.txt と ruleset の差」の追加は R1c。
