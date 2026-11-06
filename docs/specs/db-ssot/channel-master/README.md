# チャネル名簿（全社1つ）— 設計仕様書（表紙）

> この文書は何か（専門用語なしの1行）:
> 連絡手段（Messenger・Instagram・WhatsApp・電話など）の名簿を、会社ごとの写しではなく全社1つの名簿にまとめ、分析とカルテがそこから値を読む形にするテーマの入口。

- あるべき姿（POの言葉）: ./ideal-state.md
- KGI: ./kgi.md
- 現在地の記録: ../../../handoff/channel-master-shared/recon.md
- 親: ../README.md（DB設計のSSOT化）
- 元の要件: ../classification-master/design.md §4-2・§7（2026-07-13 PO決定）

## 境界

- 分類値の台帳化（classification-master）の #12 チャネルを実装するテーマ。他の分類値（流入元・国など）は扱わない。
- 会話ファイルの取り込み（inbox/conversation-import）は本テーマの完了を待つ。

## ステータス

KGI PO承認済み（2026-11-06）。設計作成中。

## 維持の仕組み

- 本テーマのファイル変更はPR＋PO承認のみ。
- ideal-state.md はPOの言葉の正本で、Planner・Generatorは書き換えない。
