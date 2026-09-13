# 添付ファイルの保管（attachment-storage）— 表紙

> この文書は何か（専門用語なしの1行）:
> 顧客がDiscordなどで送ってきた画像やファイルを、あとから見返せるように自分たちのサーバーへ保管しておくための決まりを書いた設計仕様書の表紙。

配置: docs/specs/attachment-storage/README.md
日付: 2026-09-01
PO: しんご
ステータス: あるべき姿・KGI確定 2026-09-01

## なぜ新規テーマか（KGI⑪）

着手前に索引 docs/specs/README.md と docs/specs/ 配下を走査したが、
ファイル保管・添付・ストレージに該当するあるべき姿は0件だった（2026-09-01 実測）。
既存テーマにぶら下げられないため新規作成する。

## 本テーマの範囲（境界）

- 対象: Discord で受信した添付ファイルの保管・配信・削除。将来 LINE 等が増えたら同じ扱いにする。
- 対象外: Meta（Messenger / Instagram）。規約上の理由から自社保存せず、
  既存方式（CDN URL を保存し期限切れ時に再取得）を維持する（PO決定 2026-09-01）。
- 対象外: 受信箱の見せ方。受信箱（inbox）テーマが担当する。
- 対象外: prod1 のディスク清掃。server-resource-optimization テーマが担当する。

## 構成

- README.md（本ファイル・表紙）
- [ideal-state.md](./ideal-state.md) — あるべき姿（PO自筆のみの正本。Planner・Generatorは書き換えない）
- [kgi.md](./kgi.md) — KGI（○×条件・上限値・前提）

## 背景となる実測（2026-09-01）

- Discord の添付URLは署名付きで約24時間で失効する（Discord公式仕様）。
- LINE も送信コンテンツを一定期間後に自動削除する（LINE公式ドキュメント）。
- Meta（IG）は直近20件/スレッド制限があり古いメッセージは取得できない場合がある。
- prod1 の空き容量 28GB、prod2 の空き容量 166GB。
- 既存の添付は全テナント合計3件（tenant_006 のみ）。
- 既存の自社保存の仕組みは存在しない（StaticFiles / mount が0件）。

## 維持の仕組み

- 本表紙の変更はPR＋PO承認のみ。process-artifacts gate が通過を管理する。
