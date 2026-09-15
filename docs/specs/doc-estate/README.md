# 文書体系（ナレッジベース）— 表紙

> この文書は何か（専門用語なしの1行）:
> このリポジトリの全文書（正本・仕様書・判断記録・失敗記録）が、長期的に増え続けても正しく整理され、誰でも（AIエージェント含む）迷わず読める・収められる状態を定義し、測り続けるテーマの入口。

- あるべき姿（POの言葉のみ・正本）: [ideal-state.md](./ideal-state.md)
- KGIと運用: [kgi.md](./kgi.md)
- 親: 索引 [docs/specs/README.md](../README.md)
- ステータス: KGI承認済（2026-07-03・チャットGO。実装は子便に分解済み→kgi.md §設計送り）

## 索引確認の記録（蛇口・3点）
1. 索引を確認した（2026-07-03・origin/main b4a1ced 時点の実物）。
2. 既存で足りない理由: 置き場（§1.5）・親子（§1.6）・維持欄（§1.7）・門番（§1.8）・索引・FEATURE-INDEX・§6失敗記録という部品は各所に実在するが、書庫全体の理想と測定を束ねる親テーマが索引に存在しないため。
3. 本PRで索引に登録した。

## 境界（接点）
- 内容の重複防止（同じ領域に理想が2つできない）: 循環テーマ design-partner-loop §1.8 門番判定と蛇口ルールの管轄。本テーマは形式の秩序（場所・語彙・量・導線・維持）を担当する。
- テーマ進捗の時間軸把握（経過・放置・効果測定）: 別テーマ「進捗観測」（起票待ち）の管轄。共通の上位の願い＝「プロジェクトの全知識と全状態が、誰でも（AIエージェント含む）正しく把握・維持できる」。
- 文書の中身の質（設計として良いか）: 機械では測れないためPO目視の管轄（循環テーマ§6と同じ原理的線引き）。

## 維持の仕組み（守り手の名指し）
- 本テーマの各KGIの守り手は kgi.md の表に列挙（原則PRごとの関所、例外は定期再測定）。
- 既に稼働中の守り手（実在パス）: [.github/workflows/process-artifacts-gate.yml](../../../.github/workflows/process-artifacts-gate.yml)／[scripts/check-doc-heading-duplicates.sh](../../../scripts/check-doc-heading-duplicates.sh)／索引の凡例（[docs/specs/README.md](../README.md)）。
- 本表紙・ideal-state.md・kgi.md の変更はPR＋PO承認のみ。ideal-state.md はPOの言葉のみで構成し、Planner・Generatorは書き換えない（§1.5）。
