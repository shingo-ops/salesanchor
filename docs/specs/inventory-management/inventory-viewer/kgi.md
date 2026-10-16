# KGI と運用 — 在庫の閲覧専用ページ

親: [README.md](./README.md)

## KGI（○×で判定する）

| # | KGI | ○の条件 | 確かめ方 |
|---|---|---|---|
| 1 | 速い | ログイン済みの閲覧者が /viewer/ を開いてから、在庫表の最初の行が出るまでが 1 秒以内（中央値、5 回計測） | design.md 受入条件（Evaluator・Playwright） |
| 2 | 新しい | 表の「最終更新」が、開いた時刻から 1 分以内 | design.md 受入条件 |
| 3 | 決めた人だけが見られる | 未登録・期限切れ・停止中の email ではログインのリンクが届かず、在庫表が見られない | design.md 受入条件（CI pytest） |
| 4 | 在庫表以外は見えない | 閲覧者のトークンでアプリの API を叩くと、許した 6 本以外はすべて 401 | design.md 受入条件（CI pytest test_viewer_isolation） |
| 5 | トライアルと本契約 | メールの確認から 14 日で trial が見られなくなり、active は期限なく見られる。PO と Claude が切り替え・停止・延長をできる | design.md 受入条件 |
| 6 | 共有と重複に気付ける | PO の画面で、閲覧者ごとのログイン履歴（日時・IP・端末）と、2 つの目印が見られる | design.md 受入条件 |

## 運用方針

- GO は、本テーマの設計どおりの操作であれば、PO の委任に基づき Claude Opus が出す（docs/handoff/go-record-transcription/opus-delegation.md）。設計から外れる操作は PO に聞く。
- 未決：Q4（GAS をいつ止めるか）、Q7（個人情報の保存期間と削除）。design.md の「PO 決定待ち」。
