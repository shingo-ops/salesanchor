# ADR-1064: 保存した会話ファイルは、変換して meta_messages に入れ、受信箱に出す

| 項目 | 内容 |
|------|------|
| ステータス | Proposed（段階1の K1〜K6 が tenant_001 で ○ になったら採用に上げる） |
| 備考 | PO 2026-11-06「1」：段階1（共通の形・取り込み画面・Facebook）の合格条件6つを承認 |
| 起案日 | 2026-11-06 |
| 方針の決定者 | Shingo（PO） |
| 関連 | ADR-095（多チャネルの取り込みは別途設計）、ADR-119（lead_channels）、ADR-1049（リードの統合）、ADR-110（受信の翻訳）、ADR-144（画面の金型）、ADR-027（画面の文字） |
| 設計・根拠 | [design.md](../handoff/conversation-import/design.md)、[recon.md](../handoff/conversation-import/recon.md)、[仕様書](../specs/inbox/conversation-import/README.md) |

---

## What（何を決めたか）

1. 保存した会話ファイルは、窓口ごとの変換で1つの共通の形にしてから入れる。変換は形の名前（例 fbcap-1）で選ぶ登録表に足していく。
2. 入れ先は meta_messages だけ。conversation_logs には書かない。新しい表・列は作らない。
3. 取り込みの行は is_manual = TRUE と recorded_by_user_id で見分ける。message_id は `<形の名前>:<lead_id>:<ファイル内の番号>` にし、同じファイルの2回目は入らない。
4. 取り込みは翻訳の依頼と Discord の知らせを呼ばない。未読も増やさない（seen_at を入れる）。
5. 最新の受信が取り込みの行のリードには、受信箱から送信できない（サーバーが 400 で止める）。
6. 会話画面は新しい方から取り、古い方は「前のメッセージを読む」で足す。続き読みは (created_at, id) で比べる。

## Why（なぜ）

- 会話の正本は meta_messages を土台に1つにする方針が既存の設計にある（docs/specs/db-ssot/conversation-unification/design.md:14-20。PO 承認の記録はその文書内に無い）。両方に書くと同じ会話が2か所になる。
- 受信箱の一覧と会話画面は meta_messages だけを読む（recon §3）。成約しやすさの分析も messenger のリードは meta_messages を読む（recon §7）。
- 取り込みの行は本当の相手番号を持たない。送ると Meta への送信が失敗するか、24時間の窓の判定が狂う（recon §4）。
- 会話画面は古い方の50件しか出さず、50件を超える会話の新しい方が見えない（recon §3）。K2 の前提として直す。
- 過去の時刻で後から入る行があるため、id の大小だけの続き読みでは順番が崩れる。

## 受け入れるリスク

- 週次の助言（analytics.py:2255）は conversation_logs しか読まないため、取り込みの会話を数えない。会話の一元化の本体で直す。
- 後で本物の Facebook 接続が来ると別のリードができる。ADR-1049 の統合で1つにする。
- 段階1は保存ファイルの時刻を Asia/Tokyo として読む。保存時刻（savedAt）との見張りと下見の表示で読み違いを見つける。

## 対象外

- 保存の道具（ブラウザ拡張）。WhatsApp・Instagram の変換（段階2・3）。Cardmarket の画面読み取り（段階4）。eBay の API 接続（段階5）。
