# 会話ファイルの取り込み（受信箱 子テーマ）

> この文書は何か（専門用語なしの1行）:
> Facebook・WhatsApp・Instagram などで保存した会話のファイルを、お客さん（リード）を選んで受信箱に入れる機能の仕様書の表紙。

親（あるべき姿＋KGI）へのリンク: [受信箱 親テーマ](../README.md)

配置: docs/specs/inbox/conversation-import/README.md
日付: 2026-11-06
PO: しんご
ステータス: KGI承認済 2026-11-06（段階1）／設計案作成済み・審査前

## 本テーマの範囲（境界）

- 扱う: 保存済みの会話ファイルを、1つの共通の形に変換して、選んだリードの会話として受信箱に入れること。その画面。リードが見つからないときの新規作成。
- 扱わない: 会話の保存の道具そのもの（ブラウザ拡張など）。受信箱からの送信（取り込んだ会話には返信しない）。eBay の API 接続（段階5で別設計）。
- 会話データの正本は「DB設計のSSOT化」の会話の一元化（[conversation-unification](../../db-ssot/conversation-unification/design.md)）に従う。本テーマは新しい保存先を作らない。

## 段階（PO決定）

| 段階 | 中身 | 状態 |
|---|---|---|
| 1 | 共通の形・取り込み画面・Facebook の保存ファイル（fbcap-1） | KGI承認済 2026-11-06・設計案作成済み |
| 2 | WhatsApp の書き出しファイルの変換 | 未着手 |
| 3 | Instagram の変換 | 未着手 |
| 4 | Cardmarket の画面読み取りの道具（API の鍵が無いため。PO「3」） | 未着手 |
| 5 | eBay を API で接続し、受信箱で送受信する（PO「もし出来るのであればAPI繋ぎたい」） | 未着手・別設計 |

## 構成

- [ideal-state.md](ideal-state.md) — あるべき姿（POの言葉のみ。書き換え禁止）
- [kgi.md](kgi.md) — 段階1の合格条件6つ（PO承認 2026-11-06）
- 設計: [docs/handoff/conversation-import/design.md](../../../handoff/conversation-import/design.md)
- 調査: [docs/handoff/conversation-import/recon.md](../../../handoff/conversation-import/recon.md)
- 決定記録案: [ADR-1064](../../../adr/ADR-1064-conversation-file-import.md)

## 維持の仕組み

- 本テーマのファイル変更は PR＋PO承認のみ。process-artifacts gate が通過を管理。
- ideal-state.md の中身はPOの言葉であり、Planner・Generator は書き換えない。
