# 受注管理・未入金（子テーマ）

> この文書は何か（専門用語なしの1行）:
> 「未入金」（請求書は出したがまだ入金されていない注文）を一覧で管理し、内容の修正・再発行・入金確認・リマインドまで行うページの設計一式。

親（あるべき姿＋KGI）へのリンク: [../README.md](../README.md)（受注管理・親テーマ）

配置: docs/specs/order-management/unpaid/
日付: 2026-07-05
PO: しんご
ステータス: To-Be設計（③）完了。recon（④）・差分設計（⑤）は未実施。

---

## 概要

受注管理の7ステータスのうち「未入金」の1面。請求書発行済みで未入金の注文だけが並ぶ。一覧・編集下層ページ・入金確認・リマインドを持つ。

## 境界（このテーマの外）

- 見せ方の器（左サイドメニュー・件数バッジ・共通の骨組み・「次の操作」入口の置き場）＝親テーマが正本。
- データ構造（明細・請求書の版・送料・イベント台帳＝誰が・いつ）＝取引フロー（docs/specs/transaction-flow/）が正本。
- 送料・通貨の計算＝見積・請求書発行機能の仕組みを横展開（既存ロジック再利用）。
- リマインドの実配信・スレッド管理＝受信箱テーマが担当。
- 「顧客ごとの優先チャネル」の置き場＝顧客管理テーマ。
- 設定ページ（各ステータスの設定をまとめる器）＝親へ昇格・予約（全ステータス設計後に定義）。未入金が設定できるべき中身は本設計の design.md に記載。

## 子文書一覧

- [ideal-state.md](ideal-state.md) … あるべき姿（PO自筆・正本）
- [kgi.md](kgi.md) … KGI（○×で測る）
- [design.md](design.md) … To-Be設計（画面・操作・ルール）
- [track-record.md](track-record.md) … 定点観測（PR単位の測定台帳）
- images/unpaid-list.svg … 一覧（2段組み）
- images/unpaid-edit-subpage.svg … 編集下層ページ
- images/payment-confirm-flow.svg … 入金確認フロー＋監査
- images/reminder-channel-ladder.svg … リマインドのチャネル選択
- images/reissue-confirm-dialog.svg … 再発行の確認ダイアログ
