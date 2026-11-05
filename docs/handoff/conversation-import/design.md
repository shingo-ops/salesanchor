# design: 会話ファイルの取り込み（段階1: Facebook の保存ファイル）

> この文書は何か（専門用語なしの1行）:
> 保存した Facebook の会話ファイルを、選んだリードの会話として受信箱に入れる仕組みの設計。変換の共通の形を決め、後の WhatsApp・Instagram も同じ入口に足せるようにする。

親: [仕様書の表紙](../../specs/inbox/conversation-import/README.md) ／ KGI: [kgi.md](../../specs/inbox/conversation-import/kgi.md) ／ 調査: [recon.md](recon.md) ／ 決定記録案: [ADR-1064](../../adr/ADR-1064-conversation-file-import.md)

状態: 設計案作成済み（Opus）／設計審査前／PO 実装承認前／実装未着手

## 1. 目的

- リードのカルテと返信の速さの分析に使う会話を、API で取れない窓口からも受信箱にそろえる。
- 段階1の合格条件は kgi.md の K1〜K6。

## 2. 対象と対象外

| 対象（段階1） | 対象外 |
|---|---|
| 共通の形（変換後の1件の形）と変換の登録表 | 保存の道具（ブラウザ拡張）そのもの |
| Facebook の保存ファイル fbcap-1 の変換 | WhatsApp・Instagram の変換（段階2・3。登録表に足すだけにする） |
| 下見→取り込みの API 2本 | eBay の API 接続（段階5・別設計） |
| 取り込み画面（ファイル・リードを選ぶ・リードの新規作成） | 取り込んだ会話からの返信（止める・§4-6） |
| 取り込んだ会話への返信を止める見張り | 週次の助言（analytics.py:2255）を meta_messages に向けること（会話の一元化の本体で扱う・§7 R3） |
| 会話画面が新しい方の50件を出さない不具合の直し（K2 の前提） | InboxKartePanel の limit=500（recon §3。別に記録） |

## 3. 変更前と変更後

| | 変更前 | 変更後 |
|---|---|---|
| 保存した会話 | 受信箱に入れる道が無い | 取り込み画面から、選んだリードの会話として meta_messages に入る |
| 受信箱の一覧 | Webhook・送信の会話だけ | 取り込んだ会話も messenger の印で並ぶ。未読は増えない |
| 会話画面 | 古い方の50件だけが出る（recon §3） | 新しい方の50件が出て、「前のメッセージ」で古い方を足して読める |
| 取り込んだ会話への返信 | （該当なし） | サーバーが 400 で止め、理由を返す |

## 4. 設計

### 4-1 共通の形と変換の登録表（後の段階も同じ入口）

- 新しい場所: `backend/app/services/conversation_import/`
  - `common.py`: 変換後の1件の形 `ImportedMessage`（凍結 dataclass）
    - `source_message_id: str`（ファイル内の番号）
    - `occurred_at: datetime`（時間帯つき）
    - `direction: Literal["inbound", "outbound"]`（お客さん→inbound、こちら→outbound）
    - `sender_name: str | None`
    - `text: str | None`
    - `is_attachment: bool`
  - 変換の結果 `ParsedFile`: `source`（例 "fbcap-1"）、`platform`（例 "messenger"）、`messages: list[ImportedMessage]`（ファイルの順）、`saved_at: datetime | None`、`errors: list[str]`
  - `registry.py`: `PARSERS: dict[str, Callable[[bytes], ParsedFile]]`。形の名前（ファイルの format）で選ぶ。段階1は `{"fbcap-1": parse_fbcap1}` だけ。知らない形は 400。
  - `fbcap.py`: `parse_fbcap1(raw: bytes) -> ParsedFile`
- 変換は DB に触らない（純粋な関数）。試験はファイル→結果だけで書ける。

### 4-2 fbcap-1 から meta_messages への写し方（新しい表・列は作らない）

正本は会話の一元化の方針どおり meta_messages（recon §0・§2）。conversation_logs には書かない（同じ会話を2か所に置かない）。

| meta_messages の列 | 入れる値 | 根拠 |
|---|---|---|
| tenant_id / lead_id | ログイン中のテナント／画面で選んだリード | 全会話はリードにひもづく（conversation-unification design.md:20） |
| platform | `ParsedFile.platform`（fbcap-1 は `messenger`） | 一覧の印（icons.tsx:265）と一覧の絞り込み（meta_inbox.py:870）がそのまま使える |
| direction | who=other → `inbound`、who=me → `outbound` | 左右（K3）は direction で決まる |
| sender_id | 固定の文字 `import:fbcap-1` | NOT NULL（012:13）。本当の相手番号は持たない |
| sender_name | ファイルの name | |
| message_id | `fbcap-1:{lead_id}:{id}` | 部分一意の目次（013:48）で2回目は入らない（K4）。id が別の会話で重ならない保証は未確認（recon §1）なので lead_id を挟む |
| message_text | ファイルの text（空なら NULL） | 空の吹き出しは既存の t("inbox.noBody") が出る（InboxMessageThread.tsx の msg-text） |
| created_at / occurred_at | ファイルの at を §4-3 で時間帯つきにした値（両方同じ） | 一覧・会話画面・分析は created_at を読む（recon §3・§7） |
| seen_at / seen_by_staff_id | 取り込んだ時刻／取り込んだ人 | 未読を増やさない（meta_inbox.py:942） |
| is_manual / recorded_by_user_id | TRUE／取り込んだ人 | 取り込みの行の目印。返信の見張り（§4-6）が読む |
| raw_payload | `{"import_source": "fbcap-1", "kind": "<text|attachment>"}` | 会話の中身は重ねて置かない |
| それ以外 | 入れない（NULL・既定値） | |

- 入れる順はファイルの順。同じ分に複数あるときは id（自動の番号）の順で並ぶ（会話画面の `ORDER BY created_at ASC, id ASC`・leads.py:1025）。→ K2 の並び順を守る。
- 1回の取り込みは1つの取引（transaction）。`INSERT ... ON CONFLICT (message_id) WHERE message_id IS NOT NULL DO NOTHING`（webhook.py:723 と同じ書き方）。入った件数と飛ばした件数を返す。
- 取り込みの後に `publish_inbox_update(tenant_id)`（sse_pubsub.py:97）を1回呼び、開いている受信箱が一覧を取り直す。
- 翻訳の依頼（inbound_translation）と Discord の知らせ（send_discord_notification）は呼ばない（K5）。

### 4-3 時刻の時間帯

- fbcap-1 の at は時間帯なし（recon §1）。段階1では **Asia/Tokyo として読む**（保存した Mac が JST・recon §1）。
- 見張り: 最後のメッセージの時刻（Asia/Tokyo）が savedAt（UTC）より2分以上あとなら、下見でエラーにし、取り込ませない（時間帯の読み違いの検出）。
- 下見の画面に最初と最後の時刻を出し、担当者が Facebook の画面と見比べられるようにする。
- 【未確認】Facebook が画面の時刻をどの時間帯で出すかの公式の説明（recon §1）。海外の端末で保存したファイルを扱うときは段階2以降で時間帯を選べるようにする。

### 4-4 ファイルの見張り

- 大きさ 5MB まで、メッセージ 5,000 件まで。超えたら 400。
- format が登録表に無い → 400。
- id が空の行、at が読めない行、who が me/other 以外の行が1つでもあれば、下見でその件数を返し、取り込みは 400（一部だけ入れることはしない）。
- ファイル内で id が重なる → 400。
- エラーの文は日本語の固定文をサーバーで返さず、`code`（例 `unknown_format`, `missing_id`, `time_after_saved`）と件数を返す。画面が t() で文にする（ADR-027）。

### 4-5 API（新しい router: `backend/app/routers/conversation_import.py`）

| 道 | 権限 | 中身 |
|---|---|---|
| `POST /api/v1/leads/{lead_id}/conversation-import/preview`（multipart: file） | messaging.send | 変換だけして返す: `source`, `platform`, `total`, `inbound`, `outbound`, `attachments`, `first_at`, `last_at`, `already_imported`（同じ message_id が既にある件数）, `will_add`, `errors[{code, count}]`。DB に書かない |
| `POST /api/v1/leads/{lead_id}/conversation-import/commit`（multipart: file） | messaging.send | §4-2 で入れる。返す: `added`, `skipped`。errors があれば 400 |

- リードが同じテナントに無い → 404（leads.py:974 と同じ確かめ方）。
- リードの検索と新規作成は既存の `GET /leads?search=` と `POST /leads` を使う（新しい API を作らない・recon §8）。

### 4-6 取り込んだ会話への返信を止める

- `backend/app/routers/leads.py` `send_lead_message`（:1776）の「直近 inbound を読む」SELECT（:1847 付近）に `is_manual` を足す。
- その行の is_manual が TRUE なら、platform の判定より前に 400 を返す。detail は既存の書き方に合わせる。画面は今の送信失敗の表示がそのまま出る。
- 本物の受信（Webhook）が後から来れば、その行が最新になり、普段どおり送れる。

### 4-7 lead_channels は作らない

- 取り込みは lead_channels（Facebook の相手番号とリードの結びつき）を作らない。本当の相手番号を持たないため。
- 後で本物の Facebook 接続から同じお客さんが来ると、Webhook が別のリードを作る（webhook.py:583）。そのときは既存のリードの統合（ADR-1049）で1つにする（§7 R2）。

### 4-8 会話画面で新しい方の50件を出す（K2 の前提・便1）

- `list_lead_messages`（leads.py:974）:
  - `before` が無いとき: 新しい順に limit 件を取り、古い順に並べ直して返す（内側 `ORDER BY created_at DESC, id DESC LIMIT :limit`、外側 `ORDER BY created_at ASC, id ASC`）。
  - `before=<id>` のとき: その行の (created_at, id) より前の行を同じ方法で返す（`(created_at, id) < (:c, :i)`）。id の大小だけで比べると、取り込みのように後から過去の時刻で入った行で順番が崩れるため。
  - 返り値に `has_more: bool` を足す（limit+1 件取って判定）。
- 画面（frontend/src/pages/inbox/InboxMessageThread.tsx・useInboxState.ts）:
  - has_more が true のとき、会話の一番上に「前のメッセージを読む」ボタン（Button 金型・t() の新しい鍵 `inbox.loadOlder`）を出す。押すと先頭の id を before にして取り、上に足す。
  - 新しい部品・色の直書きは作らない。

### 4-9 取り込み画面

- 道: `/lead-chat/import`（frontend/src/App.tsx の `/lead-chat` の近くに足す）。受信箱の上の操作欄（InboxPage.tsx:160 headerAction）に HeaderButton「会話を取り込む」を足す（権限 messaging.send のときだけ）。
- 新しいページ: `frontend/src/pages/inbox/ConversationImportPage.tsx`。型は UnitImportPage.tsx と同じ2段（選ぶ→下見→取り込む）。
  1. ファイル: `<TextField type="file" accept=".json,application/json">`
  2. リード: AsyncCombobox。loadOptions は `GET /leads?search=<文字>&per_page=20`。表示は「名前（LD-00001）」。
  3. リードの新規作成: リード欄の横に Button「新しいリードを作る」（権限 leads.create のときだけ）。押すと LeadsPage.tsx と同じ Modal＋LeadFormFields で `POST /leads`。作ったリードを選んだ状態にする。channel_type の初期値は messenger。
  4. 下見: 件数（全体・お客さん・こちら・添付）、最初と最後の時刻、既にある件数、追加される件数、エラー（t() の文）。
  5. 取り込む: commit を呼び、「追加 N 件・既にあった M 件」を出し、「受信箱で開く」で `/lead-chat` のそのリードへ移る。
- 文字はすべて t()。ja.json と en.json に同じ鍵を足す（ADR-027）。部品は既存の金型だけ（ADR-144）。LeadsPage の新規作成の Modal 部分を共通部品に切り出すかは実装カードで実物を見て決める（同じ中身を2か所に書き写さない）。

## 5. 代替案と選んだ理由

| 案 | 中身 | 判断 |
|---|---|---|
| A（採用） | meta_messages だけに入れる | 会話の正本を meta_messages に寄せる承認済みの方針（recon §0）。一覧・会話画面・成約分析（analytics.py:2489）がそのまま読む |
| B | conversation_logs だけに入れる | 受信箱の一覧（meta_inbox.py）と会話画面が読まない。K1 が × |
| C | 両方に入れる | 同じ会話が2か所になる。PO の「データを分散させることは禁止」に反する |
| platform を新しい値（例 `facebook_import`） | 印が灰色の点になり（icons.tsx:287 以降）、一覧の絞り込みにも出ない | 不採用。取り込みかどうかは is_manual で分かる |
| 返信を止めない | 本当の相手番号が無く、Meta への送信が失敗するか、24時間の窓の判定が狂う（recon §4） | 不採用 |

## 6. 受け入れ条件と検証方法

| 基準 | 検証方法 |
|---|---|
| K1 リードを選んで取り込むと受信箱に出る | Evaluator: tenant_001 で架空ファイル（30件）を取り込み、受信箱の一覧に messenger の印でリードが出て、会話画面に吹き出しが出る画面写し |
| K2 件数と並び順がファイルと同じ | 自動試験: 60件の架空ファイルを取り込み、会話画面の API（before なし＋before で1回）で 60 件・ファイル順。同じ分に3件ある並びも含める。Evaluator: 画面で先頭と末尾の吹き出しの文がファイルと一致 |
| K3 お客さんが左・こちらが右 | 自動試験: who→direction の対応。Evaluator: 画面写しで左右 |
| K4 2回取り込んでも増えない | 自動試験: 同じファイルを2回 commit し、2回目 added=0・skipped=全件、行数が変わらない。Evaluator: 画面の件数が同じ |
| K5 翻訳0回・Discord 0件 | 自動試験: `enqueue_inbound_translation` と `send_discord_notification` を差し替え、呼ばれた回数 0 |
| K6 その画面でリードを作れる | Evaluator: 取り込み画面で新規作成→そのリードに取り込み→受信箱に出る |
| 返信を止める | 自動試験: 取り込みの行が最新 inbound のリードに送信すると 400。Webhook の行が後に来ると送信の判定へ進む |
| 未読が増えない | 自動試験: 取り込み後の一覧の unread_count が 0 |
| 時間帯の見張り | 自動試験: 最後の時刻が savedAt より後になるファイルで下見が `time_after_saved` |
| 画面の決まり | CI: .github/workflows/frontend-check.yml と .github/workflows/ui-governance-gate.yml が緑 |

## 7. リスクと対処

| # | リスク | 対処 |
|---|---|---|
| R1 | Facebook の画面の時刻が JST でない | §4-3 の savedAt との見張り＋下見で最初・最後の時刻を見せる |
| R2 | 後で本物の Facebook 接続が来ると別リードができる | 統合（ADR-1049）で1つにする。取り込みの行は message_id が `fbcap-1:` で始まり、本物の行（m_ で始まる）と重ならない |
| R3 | 週次の助言（analytics.py:2255）は conversation_logs しか読まず、取り込みの会話を数えない | 既存の分散であり、会話の一元化の本体（conversation-unification）で直す。本設計で conversation_logs に写すと分散が増えるため写さない |
| R4 | 会話画面の直し（§4-8）が本物の会話の見え方も変える | 新しい方が出るのが正しい形。自動試験で before の続き読みを確かめる |
| R5 | 保存ファイルの id が長い期間で変わる | lead_id を挟んだ message_id で、同じリードに同じファイルなら重ならない。id が変わった場合は重複が入る。【未確認】のため、段階1の実運用1か月後に重複の有無を数える（§9） |
| R6 | お客さんの会話の中身が git・PR・ログに出る | 試験は架空の文だけ。取り込みのログに本文を出さない（件数と lead_id だけ） |

## 8. 外部・過去事例の参照と我々への応用

- 社内の過去事例: LINE の書き出し取り込み（系統B・public.source_messages）は仕入元専用で、お客さんの会話には流用できない（docs/handoff/whatsapp-intake/README.md:98）。→ 今回は別の入口を作り、変換の登録表で窓口を足せる形にした。
- 社内の過去事例: Webhook の重複防止（webhook.py:723 の ON CONFLICT）を同じ形で使う。
- 外部の数値つき事例: 該当なし。保存ファイルの取り込みは各社固有の作りで、比べられる数値の公表が見つからないため、成功の根拠には使わない。

## 9. 実装の段取り（便）

| 便 | 中身 | 触るファイル |
|---|---|---|
| 便1 | 会話画面で新しい方を出す（§4-8） | backend/app/routers/leads.py、frontend/src/pages/inbox/InboxMessageThread.tsx、frontend/src/pages/inbox/useInboxState.ts、frontend/src/lib/messages.ts、locales、試験 |
| 便2 | 変換と API・返信の見張り（§4-1〜4-7） | backend/app/services/conversation_import/、backend/app/routers/conversation_import.py、backend/app/main.py（router 登録・conv_logs の登録 main.py:716 の近く）、backend/app/routers/leads.py、試験 |
| 便3 | 取り込み画面（§4-9） | frontend/src/pages/inbox/ConversationImportPage.tsx、frontend/src/App.tsx、frontend/src/pages/inbox/InboxPage.tsx、locales、試験 |

- DB の形は変えない（migrations なし）。
- 触らない: webhook.py、conversation_logs、lead_channels、翻訳の処理、analytics.py。
- 1か月後（2026-12-06 ごろ）: 取り込んだ行の数と message_id の重複の疑い（同じリード・同じ時刻・同じ文で message_id が違う）を数える。

## 維持の仕組み

- 守り手: .github/workflows/test.yml（必須の「pytest (SQLite + PostgreSQL RLS)」。便1・便2で backend/tests/ に足す試験が K2・K4・K5・返信の見張りを固定する）
- 守り手: .github/workflows/frontend-check.yml と .github/workflows/ui-governance-gate.yml（画面の文字・金型の決まり）
- 対象: 取り込みが二重に入ること、翻訳・Discord を呼んでしまうこと、取り込んだ会話へ送れてしまうこと、会話画面が新しい方を出さなくなること
- 人手で守る部分: 時間帯の読み（Facebook 側の表示が変わったとき）。理由: 外の仕様で、機械で確かめる手段が無い。下見の最初・最後の時刻を担当者が見比べる
