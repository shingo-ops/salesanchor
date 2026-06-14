# design: review@salesanchor.jp 新着メール → Discord通知

参照: [recon.md](./recon.md)

---

## KGI（PO承認済み・設計書より転載）

1. `review@salesanchor.jp` に新着メールが届いたら、5分以内に Discord へ通知される。
2. Discord 通知に 件名・差出人・受信時刻・さくらWebメール入口リンク を表示する。
3. メール本文・添付ファイル・Firebase パスワード再設定リンクは Discord に表示しない。
4. 同じメールが短時間に何度も通知されない。
5. 通知失敗・メール取得失敗で Sales Anchor 本体の認証・業務機能を止めない。

---

## 外部・過去事例の参照と我々への応用

既存の類似タスクが本プロジェクト内に複数存在する（ADR-110 翻訳タスク・SA-02 日次突合など）。
これらはすべて「失敗しても本体を止めない」設計で、Discord 通知は best-effort とする。
IMAP ポーリングは Python 標準 `imaplib` で実装可能なため外部依存を追加しない。
新規依存なし・既存パターンを踏襲できるため、外部ライブラリ調査は不要と判断。

---

## 技術 How

### アーキテクチャ

```
Celery Beat (5分) → check_review_mail_inbox Task
                         ↓
              review_mail_notifier.check_and_notify()
                    ↓              ↓
              imaplib (IMAP SSL)   Redis (DB0)
              ヘッダのみ PEEK      通知済み UID 管理
                    ↓
              httpx.post (Discord webhook)
```

### 新規ファイル

| ファイル | 役割 |
|---------|------|
| `backend/app/services/review_mail_notifier.py` | IMAP取得・Redis管理・Discord通知のコアロジック |
| `backend/app/tasks/review_mail_monitor.py` | Celery タスクの薄いラッパー |
| `backend/tests/test_review_mail_notifier.py` | 単体テスト |

### 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `backend/app/celery_app.py` | include に `app.tasks.review_mail_monitor` 追加、beat_schedule に 300秒エントリ追加 |
| `.env.example` | REVIEW_MAIL_IMAP_* 変数のコメント付き例を追加 |
| `docker-compose.yml` | celery-worker に `ADMIN_NOTIFICATION_DISCORD_WEBHOOK` + REVIEW_MAIL_* 変数を追加 |

### 環境変数設計

```env
# VPS .env に手動追加（PO 作業・新 Secret 不要）
REVIEW_MAIL_IMAP_HOST=salesanchor.sakura.ne.jp
REVIEW_MAIL_IMAP_PORT=993
REVIEW_MAIL_IMAP_USER=review@salesanchor.jp
REVIEW_MAIL_IMAP_PASSWORD=<secret>
REVIEW_MAIL_WEBMAIL_URL=https://secure.sakura.ad.jp/rscontrol/rs/webmail2/?mbox=review

# 既存 Secret を流用（追加不要）
ADMIN_NOTIFICATION_DISCORD_WEBHOOK=<existing>
```

**設定不完全時の挙動**: `_is_configured()` が False → ログを出して即 return 0（graceful skip）

### Redis キー設計

```
review_mail:notified:<uid>  → TTL 30日
```

- UID は IMAP の BODY.PEEK[HEADER] 取得時に使う整数値（サーバー側割当・永続的）
- Redis 接続失敗時はログのみ → 再通知リスク許容（本体障害より優先）

### Discord メッセージ仕様

```
📩 **Sales Anchor メール通知**

宛先: review@salesanchor.jp
差出人: <from>（最大300文字）
件名: <subject>（最大200文字）
受信時刻: <date>

さくらWebメールで確認:
<REVIEW_MAIL_WEBMAIL_URL>

※メール本文・再設定リンク・添付ファイルはDiscordには表示しません。
```

**絶対禁止**: `BODY[]`（本文）・`TEXT` パート取得、`oobCode` を含む文字列の投稿

### IMAP 取得戦略

```
BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)]
```

- `PEEK` = 既読フラグを立てない
- `HEADER.FIELDS` = 指定ヘッダのみ（本文・添付は取得しない）
- `UID SEARCH ALL` → 全 UID 走査 → Redis で通知済みをフィルタ

---

## KPI・検証方法

| 受け入れ基準 | 検証方法 |
|------------|---------|
| 5分以内に通知 | beat_schedule = 300.0 秒・手動メール送信後に Discord 確認 |
| 件名/差出人/時刻/URL が出る | pytest: `test_build_discord_content` |
| 本文・oobCode が出ない | pytest: `test_no_body_in_content`, `test_no_oobcode_in_content` |
| 重複通知なし | pytest: `test_already_notified_skip`、Redis TTL 30日 |
| IMAP 失敗で本体停止なし | pytest: `test_imap_connection_failure` |
| webhook 未設定で no-op | pytest: `test_webhook_unset_no_op` |
| Redis 不能で安全 skip | pytest: `test_redis_unavailable_skip` |

---

## 弊害・トレードオフ

| 項目 | 内容 |
|------|------|
| Redis 障害時に重複通知 | Redis 接続失敗 → skip（重複 < 本体障害）と割り切り |
| IMAP `ALL` 走査 | メールが大量にある場合は遅い。TTL で古い UID の Redis キーが消えると再通知リスク。当面メール量は少なく許容範囲 |
| 同期 httpx POST | タスク内で同期 HTTP → 最大10秒ブロック。beat 間隔 300秒に対して問題なし |
| IMAP パスワード管理 | VPS .env 手動設定・GitHub Secrets 外。PO 管理下・scp 等で安全に投入 |

---

## 計画票

| Step | 作業 | 備考 |
|------|------|------|
| 1 | recon.md / design.md 作成 | 本ファイル |
| 2 | `review_mail_notifier.py` 実装 | imaplib + redis + httpx |
| 3 | `review_mail_monitor.py` 実装 | @celery_app.task ラッパー |
| 4 | `test_review_mail_notifier.py` 実装 | 7ケース |
| 5 | `celery_app.py` 更新 | include + beat_schedule |
| 6 | `.env.example` 更新 | コメント付き例 |
| 7 | `docker-compose.yml` 更新 | celery-worker に env 追加 |
| 8 | pytest でグリーン確認 | |
| 9 | PR 作成 | |
