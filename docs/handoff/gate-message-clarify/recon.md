# recon: gate-message-clarify

## 目的
process-artifacts gate（scripts/check-process-artifacts.js）が出力する「削除するファイル:」関連メッセージが「ファイルを丸ごと削除」と誤読される。実際は「1行でも削除・変更があったファイル」を対象とする。文言を明確化する前の現在地把握。

## 対象ファイルの実在確認
- 正本: scripts/check-process-artifacts.js（リポジトリルート直下、1ファイルのみ）
- 同名ファイルが worktree/clone 配下に17個存在するが、いずれも作業用コピー。改修対象は正本1つのみ。

## 「削除するファイル」判定ロジックの実コード（file:line）
- scripts/check-process-artifacts.js:148 — PR本文から「削除するファイル:」宣言をパースする正規表現
- scripts/check-process-artifacts.js:664 — git diff --numstat の deletions（削除行数）をパース
- scripts/check-process-artifacts.js:666 — `e.deletions > 0` でフィルタ＝削除行が1行以上あるファイルを対象に含める（丸ごと削除に限らない）
- 誤読の根本: ロジックは「行削除を含むファイル」を見ているが、メッセージ文言は「削除するファイル」とだけ書かれ、ファイル単位の削除と読める

## 誤読を生むメッセージ文字列の実コード（file:line）
- scripts/check-process-artifacts.js:672 — 「PR本文に「削除するファイル:」の宣言がありません」
- scripts/check-process-artifacts.js:673 — 「「削除するファイル:」にリポジトリ相対パスを記入してください」
- scripts/check-process-artifacts.js:674 — 「削除が無い場合は「削除するファイル: なし」と記入してください」
- scripts/check-process-artifacts.js:680 — 「「削除するファイル:」に追記するか、意図しない削除を除去してください」

## 既に正しい表現の箇所（参考・触らない）
- scripts/check-process-artifacts.js:678 — 「宣言外のファイルから行を削除しています:」。既に「行を削除」と明確。改修対象外。

## 触らない範囲（明示）
- 判定ロジック（148, 664, 666 ほか）は一切変更しない。合否判定の挙動は不変。
- 記入欄ラベル「削除するファイル:」（148 のパースキーワード）は変更しない。進行中PRへの影響を避けるため。
- worktree/clone 配下の17個の同名コピーは触らない。
