# recon: LINE解析 取りこぼし調査（2026-09-28 18:00〜23:15 JST）

- 状態: 調査記録（事実の確定のみ）。修正の設計・実装は未着手
- 起点: PO報告「9/28 20:11〜22:03 はかなり投稿があるのに拾えていない（クレームあり）」
- 調査日: 2026-09-29（JST）
- 調査方法: 本番DBは読み取り専用で照会した（PO許可の鍵を使用、`SET default_transaction_read_only=on` → `SHOW transaction_read_only` = `on` を毎回確認、SELECTのみ）。コードは origin/main（HEAD `638cc6f91`）基準
- 既存ADR・設計の検索: `docs/handoff/tcg-import-latest-only/`（SQR-05／〆の商品単位反映、Draft）、`docs/handoff/line-import-missing-channel/design.md`、`docs/handoff/line-import-schema-rewire/recon.md`

## 1. 取り込み経路（事実）

| 段階 | 実装 | 根拠 |
|---|---|---|
| 書き出し | スマホ（Termux）が、LINE「WeGo売ります・BOX…」グループの「トーク履歴を送信」を約15分ごとに自動実行する（1つのトークに固定） | `tools/line-auto-export/flow.sh:52` |
| 送信 | `android-talk.txt` を `POST /api/v1/tcg/line-devices/import` へ送る。`window_hours=0`（期間で絞り込まない） | `tools/termux-line-import/client.py:429-437`、`backend/app/routers/line_import_devices.py:70-84` |
| 件数 | `import_jobs.message_count` ＝ファイル全体の件数からシステムイベント（送信取り消し等）を除いた件数 | `backend/app/services/tcg_line_import_svc.py`（`import_line_export`）、`backend/app/services/tcg_line_android_parser.py:33-38` |
| 保存 | **1回のアップロードの中で、同じ送信者は最新の1通だけ** `source_messages` に保存する（SQR-05） | `backend/app/services/tcg_line_import_svc.py:275-321` |
| 置き換え | 新しい行を保存すると、同じ `supplier_channel_id` の有効な行を**すべて**無効化する（`is_active=FALSE`）。商品ごとの判定はしない | `backend/app/services/tcg_line_import_svc.py:452-463` |
| 表示 | ダッシュボードは `sm.is_active = TRUE` の行だけを表示する | `backend/app/services/tcg_analysis_review_svc.py:35-39` |
| 原文 | アップロードされたファイル本体はサーバーに保存しない（端末側 `~/line-import/state/originals/` のみ） | `backend/app/routers/tcg_line_import.py`（`upload_android_line_export` のコメント） |

## 2. 照合の方法

- 突き合わせの基準: POがPCから書き出した同じグループのファイル（`[LINE]WeGo売ります掲示板グループ.txt`、4,874,208 bytes、193,975行、2026-09-28 23:15の投稿まで収録）
- 送信者名は、本番 `suppliers.line_name`（217件）との最長一致で判定した（スペースを含む名前に対応するため）
- 注意: PCファイル（照合の基準）と、DBの取り込み元（スマホの自動書き出し）は、同じグループを**別の経路で書き出したもの**

## 3. 結果（事実）

### 3-1. 時間帯ごとの件数

| 時間帯 | PCファイルの実投稿 | DBに保存 | 有効（画面に出る対象） | 有効かつ解析で商品が1件以上 |
|---|---|---|---|---|
| 18:00–20:10 | 12 | 12 | 9 | 8 |
| 20:11–22:03 | 7 | 6 | 5 | 3 |
| 22:04–23:15 | 3 | 2 | 2 | 1 |
| **合計** | **22** | **20** | **16** | **12** |

注: 20:11–22:03のDB行数も7行だが、そのうち1行はPCファイルでは送信取り消しになっている「もと 22:03」（3-4 C参照）。**件数が一致しているだけで、中身は一致していない**。

### 3-2. 1件ずつの照合（18:00–23:15）

| 投稿 | 送信者 | 冒頭 | DB | 状態 | 解析 |
|---|---|---|---|---|---|
| 18:04 | カンジン | 明日29日発送商品のご案内 | 保存（18:11:06） | 有効 | done 7 |
| 18:04 | Ren | 遊戯王 LIMIT OVER COLLECTION | 保存（18:11:06） | 有効 | done 1 |
| 18:10 | SAMURAI-T | ST01完売〆 | 保存（18:11:06） | 有効 | done 1 |
| 18:10 | 大知 | 在庫品 30… | 保存（18:11:06） | 無効（18:11で置き換え） | done 4 |
| 18:11 | 大知 | 30th 両方〆 | 保存（18:29:29） | 有効 | done 1 |
| 18:30 | しらいたつや | @kyosuke 個別しました | 保存 | 無効（20:15で置き換え） | filtered 0 |
| 18:57 | かあ | AR19… | 保存 | 有効 | done 2 |
| 19:19 | 倉田 和博 | ワンピースDAY 26… | 保存 | 無効（20:46で置き換え） | done 1 |
| 19:38 | 斉藤 | ご案内いたします | 保存 | 有効 | done 91 |
| 19:42 | N.Takashi | @斉藤 個別しました | 保存 | 有効 | filtered 0 |
| 20:04 | 伊石侑生 | LeGacyWorks株式会社 | 保存 | 有効 | done 13 |
| 20:07 | 星野 良介 | 17時まで当日発送可能です | 保存 | 有効 | done 23 |
| 20:11 | 矢ヶ嵜裕史 | ◆30th CELEBRA… | 保存（20:30:43） | 有効 | done 5 |
| **20:15** | **Nexus** | **Nexus Trading合同会社です（商品案内）** | **保存されず** | — | — |
| 20:15 | しらいたつや | @Nexus 個別しました | 保存（20:30:43） | 有効 | filtered 0 |
| 20:16 | Nexus | 30th 〆 | 保存（20:30:43） | 有効 | done 1 |
| 20:46 | 倉田 和博 | 4周年 四皇トレジャーゲット…完売 | 保存 | 有効 | **empty 0** |
| 21:03 | oyama | 株式会社NGAです | 保存 | 有効 | done 7 |
| 21:36 | 平田光希 | 遊戯王 ORIGINAL ARTWORK COLLECTION… | 保存 | **無効（23:15 EB03〆で置き換え）** | done 8 |
| （22:03） | もと | PCでは「送信取り消し」 | 取り消し前の本文が保存（22:12:40） | **有効のまま** | done 1 |
| **22:23** | **やまざきけんと** | **30th CELEBRATION（商品案内）** | **保存されず** | — | — |
| 22:24 | やまざきけんと | 〆 | 保存（22:26:40） | 有効 | empty 0 |
| 23:15 | 平田光希 | EB03〆 | 保存（23:27:23） | 有効 | done 1 |

- 仕入元として登録されていない送信者: 0件
- 取り込みエラー・処理待ち: 0件
- 自動アップロードの間隔: 25分を超える空きが2回（19:27:53→19:55:52、23:27:23→23:52:43）。どちらの時間帯の投稿も保存されている
- 21:49〜21:50にbackend/celery-workerが再起動（`docker inspect` の起動時刻 2026-09-28T12:49:41Z／12:50:06Z）。前後の取り込みはすべて `status=ok`

### 3-3. アップロードの記録（import_jobs、抜粋、生出力）

```
     created_jst     | message_count | provider_count | status |     filename
---------------------+---------------+----------------+--------+------------------
 2026-09-28 17:42:41 |          2582 |            168 | ok     | android-talk.txt
 2026-09-28 17:57:11 |          2582 |            168 | ok     | android-talk.txt
 2026-09-28 18:11:06 |          2585 |            168 | ok     | android-talk.txt
 2026-09-28 18:29:29 |          2586 |            168 | ok     | android-talk.txt
 2026-09-28 18:43:23 |          2587 |            168 | ok     | android-talk.txt
 2026-09-28 19:06:11 |          2588 |            168 | ok     | android-talk.txt
 2026-09-28 19:11:39 |          2588 |            168 | ok     | android-talk.txt
 2026-09-28 19:27:53 |          2589 |            168 | ok     | android-talk.txt
 2026-09-28 19:55:52 |          2591 |            168 | ok     | android-talk.txt
 2026-09-28 20:10:53 |          2593 |            168 | ok     | android-talk.txt
 2026-09-28 20:30:43 |          2597 |            168 | ok     | android-talk.txt
 2026-09-28 20:41:48 |          2597 |            168 | ok     | android-talk.txt
 2026-09-28 20:58:01 |          2598 |            168 | ok     | android-talk.txt
 2026-09-28 21:16:27 |          2599 |            168 | ok     | android-talk.txt
 2026-09-28 21:28:42 |          2599 |            168 | ok     | android-talk.txt
 2026-09-28 21:45:25 |          2599 |            168 | ok     | android-talk.txt
 2026-09-28 21:58:07 |          2599 |            168 | ok     | android-talk.txt
 2026-09-28 22:12:40 |          2600 |            168 | ok     | android-talk.txt
 2026-09-28 22:26:40 |          2602 |            168 | ok     | android-talk.txt
 2026-09-28 22:41:02 |          2602 |            168 | ok     | android-talk.txt
 2026-09-28 23:02:29 |          2602 |            168 | ok     | android-talk.txt
 2026-09-28 23:12:34 |          2602 |            168 | ok     | android-talk.txt
 2026-09-28 23:27:23 |          2602 |            168 | ok     | android-talk.txt
 2026-09-28 23:52:43 |          2602 |            168 | ok     | android-talk.txt
 2026-09-28 23:56:51 |          2602 |            168 | ok     | android-talk.txt
 2026-09-29 00:12:39 |          2602 |            168 | ok     | android-talk.txt
 2026-09-29 00:26:54 |          2602 |            168 | ok     | android-talk.txt
 2026-09-29 00:42:43 |          2602 |            168 | ok     | android-talk.txt
```

### 3-4. 原因の切り分け

**A. 1回のアップロードに入った同じ人の投稿は、最新1通だけが残る（保存されなかった2件の原因）**
- Nexus 20:15（商品案内）と 20:16（30th 〆）は、同じアップロード（20:30:43）に入っていた → 20:16だけが保存された
- やまざきけんと 22:23（商品案内）と 22:24（〆）は、同じアップロード（22:26:40）に入っていた → 22:24だけが保存された
- 比較: 大知 18:10 と 18:11 は別々のアップロード（18:11:06／18:29:29）に入り、両方保存された
- コード: `backend/app/services/tcg_line_import_svc.py:275-321`

**A'. 〆の投稿が、その人の有効な投稿を商品に関係なくすべて無効化する（画面から消える原因）**
- 平田光希 21:36（9品目。product_code 621／18／440406／125079／125081 ほか）は、23:15「EB03〆」（product_code 18 だけ）によって、投稿全体が `is_active=FALSE` になった
- コード: `backend/app/services/tcg_line_import_svc.py:452-463`（同じ `supplier_channel_id` の有効な行をすべて置き換える）。`backend/app/services/` の中に、商品単位で判定するロジックはない
- 既存設計との関係: `docs/handoff/tcg-import-latest-only/design.md` では、PO合意として「商品を指定した〆は、その商品だけを在庫から外し、他の商品は維持する」と記録されている。ただし同文書は Draft で、実装・本番反映は未実施と明記している → **設計済み・未実装のずれ**

**B. 倉田 和博 20:46 が empty になった理由**
- 本文（50文字）は「4周年 四皇トレジャーゲット キャンペーンパック 10パックセット/¥5,000 **完売**」
- `extraction_attempts`: model `gemini-3.1-flash-lite`、phase=completed、item_count=0、error_code 空。応答はヘッダー行だけで、データ行は0件
- `backend/app/services/gemini_extraction_svc.py:602-611`: items も parse_errors もないときは `status="empty"`
- 事実として言えるのは、Geminiが0件と返したこと。本文は「完売」の告知だった。どのプロンプト指示で0件になったかは未確認

**C. 送信取り消しがDBに反映されない**
- もと 22:03（`b27bdf58…`）: 22:12〜23:12の5回のアップロードでは `created`／`reused` として紐付いている。23:27以降の8回のアップロードでは紐付きがない（＝書き出しファイルから本文が消えた）。それでもDBの行は `is_active=TRUE`、`superseded_by=NULL` のまま
- コード: 取り消し行は、送信者のないシステムイベントとして解析される（`backend/app/services/tcg_line_android_parser.py:33-38`）。書き出しファイルから消えたことをきっかけに行を無効化する処理は存在しない
- 同じ行の `received_at` が 2026-08-29 23:26 になっている（投稿時刻と約1か月ずれている）。原因は未確認

## 4. 結論（証拠が示す範囲）

1. 18:00〜23:15のLINE実投稿22件のうち、DBに入らなかったのは **2件**（Nexus 20:15、やまざきけんと 22:23）。2件とも原因は A（直後の同じ人の〆と同じ回のアップロードに入った）。
2. 保存された20件のうち、画面に出る対象は16件。商品が1件以上取れているのは **12件**。差の内訳は、置き換え（A'を含む）4件、返信で対象外（filtered）2件、empty 2件（倉田 20:46「完売」告知、やまざき 22:24「〆」）。
3. 取り消された投稿（もと 22:03）が、有効なまま残っている（C）。
4. アップロードの停止、サーバー再起動による欠落、仕入元の未登録による欠落は、この時間帯では確認されなかった。

## 5. 未確認

- 画像だけの投稿: PCファイルの9/28分には `[写真]`／`[スタンプ]` の行が1件もない。画像だけの投稿が書き出しに含まれていない可能性は、確認していない
- POのクレームの対象になった具体的な投稿（時刻・送信者）: 未特定（PO回答「分からない」）
- `message_count` が 22:26:40 以降 2602 のまま変わらず、23:15の投稿が23:27:23に保存されている理由（取り消し1件と相殺した可能性があるが、確認していない）
- もと 22:03 の `received_at` のずれの原因

## 6. 付随事項

- 調査中に、本番の環境変数を読んだ際、DB接続文字列（パスワードを含む）が作業記録に1回表示された。外部への送信はなし。パスワードを変更するかはPOが判断する
- `docs/handoff/go-record-transcription/opus-delegation.md` は origin/main に存在しない（`git ls-tree -r --name-only origin/main | grep -i opus-delegation` → 0件）

## 7. 次の判断（PO）

A／A'／B／C を直すかどうかと、その順番。A'は既存の Draft 設計（`docs/handoff/tcg-import-latest-only/`）の実装に当たる。
