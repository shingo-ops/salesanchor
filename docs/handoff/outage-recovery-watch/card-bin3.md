# 実装カード 便3 — さくらの点検・障害のメールを Discord の運用チャンネルへ

> この文書は何か：outage-recovery-watch 便3 の作業指示書です。
> - さくらインターネットから届く点検・障害のメールを、件名と作業日時つきで Discord の運用チャンネルへ知らせます。
> - 流れ: PO の業務用メール（Gmail）が、さくらの差出人のメールを新しい受け箱へ自動転送 → 本番の裏方の処理（celery）が 5 分ごとに受け箱を読む → Discord へ 1 件送る。
> - 2026-10-22 のさくら緊急メンテでは、予告のメールが 10/21 に届いていたのに、誰も気づかないまま prod1 が 12:02〜12:54 JST に止まりました。そのための便です。
> - 転送が切れたこと・受け箱を読めなくなったことも、見張り 2 本で知らせます。
> - 本番への配置は §8 で行います。PO の画面の作業（受け箱・webhook・secret・転送）と、マージの後の Opus の配置（同意票つき）からなります。

- 設計: docs/handoff/outage-recovery-watch/design.md §1 G1・§3-1・§3-1-1・受け入れ基準・維持の仕組み
- recon: docs/handoff/outage-recovery-watch/recon.md
- 事実確認の生出力（2026-10-23。repo は origin/main だけを読み、本番は読んでいない。Gmail は Opus が読み取りだけ）:
  - /tmp/CC報告ファイル/outage-bin3/recon/（Sonnet）
  - /tmp/CC報告ファイル/outage-bin3/recon2/a.txt・b.txt・c.txt（Opus）
  - /tmp/CC報告ファイル/outage-bin3/recon3/a.txt・b.txt・c.txt（Opus）
- 対象ADR:
  - ADR-1012（AI保守運用24時間化。決定1「経路の正本は Alertmanager 1 本。全アラートルールに札と手順書リンク」:31）
  - ADR-136（危険 PR の GO 手順）
- 状態: 設計は PO 承認済み（2026-10-22 PO 返信「1」。KGI G1〜G3 と案M）。2026-10-23 PO が「2. 先にさくらのメールの転送（便3）の作り方も決めてから、まとめて作り始める」を選択。このカードはその「作り方」。実装の開始は、このカードを添えた PO への報告の後、PO の返事を受けてから
- 前提:
  - このカードの PR（文書だけ）が main にマージされていること（§10 で確かめる）
  - 便2（card-bin2.md）の実装が main にマージされ、本番に配置されていること（§10 で確かめる。ルールと手順書の本数がずれるため。design.md §3-1-1「順番」）
- 危険便（ADR-136 の危険パス）: はい
  - `.github/workflows/deploy.yml` を触る（secret 3 つを本番の .env に書く行を足す）。
  - マージの前に Opus が GO 記録を PR 本文に書く（PO の委任に基づく Claude Opus 発行。§8）。担当はマージしない。
  - `migrations/`・本番の `scripts/` は触らない。
- §10 の手順で作業場所を作った直後に `cd /Users/tanizawashingo/worktrees/salesanchor/release-ops-mail-notifier && ./scripts/dev/executor-preflight.sh` を実行し、exit 0 を確かめる（0 でなければ BLOCKED:。AGENTS.md:99）
- 担当:
  - Sonnet: 実装と配置台本の下書き
  - Opus（reviewer）: コード審査
  - Opus: GO 記録・マージ・本番配置・反映確認
  - PO: 受け箱・webhook・secret・Gmail の転送の画面の作業（§8-1・§8-6）と Discord の目視

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は ready で作る（Draft にしない）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（さくらのメールの中継と、その見張りだけ） |
| 5 | 既存ブランチへの追記ではない（新規ブランチ） | ○ |
| 6 | 書式は実例で示した | ○（§4 に完成形） |
| 7 | 合格基準を出力まで縛った | ○（§5・§8） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-2・§5-6。件数とルール名・見出しを対で出す） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実測から | ○（§2。便2 の後でルール 32 本・手順書 38 節の見込み。§10 で実測してから始める） |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§12） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない | ○（§5・§10・§12） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○ |
| guards/04-worktree.md | new-worktree.sh の出力をパイプに通さず、実在は `ls -1d` と `git worktree list` で確かめる | ○（§10） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh` で作る。触るファイル・削除するファイルは同一行カンマ区切り | ○（§10） |
| guards/08-vps.md | どの機体・どの鍵かをカードに書く | ○（§8。prod1 は deploy.yml の通常のデプロイと、試験メール 1 通だけ。prod2 はルールの配置だけ。担当は本番に接続しない。配置は Opus が同意票を受けて行う） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード outage-recovery-watch 便3 の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. 新しい部品 `backend/app/services/ops_mail_notifier.py`（運用の受け箱を読み、さくらの点検・障害のメールだけを Discord へ送る）
2. 新しいタスク `backend/app/tasks/ops_mail_monitor.py`
3. `backend/app/celery_app.py` に include 1 行と beat の 1 項目（5 分ごと）
4. `backend/app/metrics.py` に指標 2 つ
5. 単体試験: 新規 `backend/tests/test_ops_mail_notifier.py`、`backend/tests/test_metrics.py` に 1 件
6. `docker-compose.yml` の celery-worker に環境変数 3 つ
7. `.github/workflows/deploy.yml` に secret 3 つ（消す行 3・足す行 3）
8. `.env.example` に 3 つ（値は空）
9. `monitoring/prometheus/alert_rules.yml` に新しいグループ `ops_mail_alerts`（2 本）と、その試験 4 件
10. `docs/runbooks/alerts.md` に 2 節
11. `monitoring/tokens.yml` に閾値 2 行と for 2 行
12. 本番配置の台本 3 本（リポジトリの外 `/tmp/CC報告ファイル/outage-bin3/deploy/`。commit しない。§4-12）

入れない:
- `backend/app/services/review_mail_notifier.py` と `backend/app/tasks/review_mail_monitor.py`（1 行も変えない。review@ の通知は今のまま。design.md §3-1-1）
- `backend/tests/test_review_mail_notifier.py`（変えない。39 件がそのまま通ること）
- review@ の検索範囲・重複防止の鍵の性質（直さない。design.md §3-1-1）
- 受け箱のアドレス・パスワード・webhook の値（どのファイルにも書かない。secret だけ）
- 既存のルールの式・for・札、`monitoring/alertmanager/alertmanager.yml`（変えない。新しい 2 本は既定の道で Discord と保守 API に届く。時計ずれの抑止にも足さない。design.md §3-1-1）
- `monitoring/scripts/check_alert_rules.py`（変えない。新ルール 2 本は既存の検査に乗る）
- 本番への接続（担当は prod1・prod2 に接続しない）
- PO の画面の作業（§8-1・§8-6。担当は手順を書かない。手順はこのカードにある）

## 2. 前提の事実

| # | 事実 | 出典 |
|---|---|---|
| F1 | review@ の部品（backend/app/services/review_mail_notifier.py、249 行）: 環境変数は :36-43（`REVIEW_MAIL_IMAP_HOST`・`_PORT`（既定 993）・`_USER`・`_PASSWORD`・`_WEBMAIL_URL`・`REDIS_URL`・`_DISCORD_WEBHOOK`・`_DISCORD_MENTION`）。`_decode_mime_header(value)`（:77）・`_get_redis()`（:89。同期の Redis、ping、失敗で None）・`_post_discord`（:135。webhook は review@ の固定）・`check_and_notify()`（:161。`uid search ALL`、`BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)]`、送れたときだけ鍵を付ける、Redis が無ければ 0 を返す）。重複防止の鍵は `review_mail:notified:<uid>`・30 日 | recon3/b.txt・recon3/a.txt |
| F2 | タスク: `backend/app/tasks/review_mail_monitor.py` の `check_review_mail_inbox`（max_retries=0、`{"notified": n}` を返す）。celery_app.py の include :33・beat の項目 `review-mail-discord-notifier`（300 秒） | recon3/b.txt |
| F3 | `backend/tests/test_celery_beat_registered.py` は beat の全項目の task 名が登録済みかを試す（新しい項目もこれに乗る） | recon3/c.txt |
| F4 | 環境変数は celery-worker だけに渡している（docker-compose.yml:240-247 の 8 行。コメント :240「review@salesanchor.jp メール監視（GitHub Secrets → deploy.yml → VPS .env）」） | recon3/b.txt |
| F5 | deploy.yml は secret を本番の .env に「sed で消してから足す」形で書く。消す行 :295-300（REVIEW_MAIL の 6 行）、足す行 :341-346（`KEY='${{ secrets.KEY }}'`）。deploy.yml は main への push で動く（:3-6） | recon3/b.txt・recon3/c.txt |
| F6 | `.env.example` の review@ の段は :104-116 | recon3/b.txt |
| F7 | 指標: `backend/app/metrics.py` の `_read_ts(redis_client, key)`（:62。非同期の Redis を 1 秒で打ち切り、無い・数でない・例外は 0）と `_update_viewer_inventory_gauges()`（:71-80。中で鍵の名前を import）。`/metrics`（:111-125）が try/except で呼ぶ | recon3/a.txt・b.txt |
| F8 | Prometheus は backend の `/metrics` を job `backend`・instance `app-vps` で読む。ルールの型は CeleryHeartbeatStale（alert_rules.yml:183-192） | recon2/b.txt・c.txt |
| F9 | 今の main（便2 の前）でルール 29 本・Loki 6 本・手順書 35 節。最後のグループは `clock_alerts`（:349）。便2 で 32 本・38 節・最後のグループ `recovery_check_alerts` になる見込み（card-bin2.md §5-2） | recon3/a.txt |
| F10 | `check_alert_rules.py`: TIERS は page・auto・ticket（:19）、runbook_url は `https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#` ＋ 名前の小文字（:18・:89） | recon2/b.txt |
| F11 | tokens.yml: 時計ずれの段 :97-98（`clock_skew_sec: 60`）・for の最後 :130（`clock_sync_stopped`）。便2 でその後ろに 1 行ずつ足される | recon3/a.txt・card-bin2.md §4-12 |
| F12 | さくらの差出人: `support@sakura.ad.jp`（ほかに `domain@sakura.ad.jp`）。10/21 の件名「［緊急］さくらのVPS東京・大阪・石狩リージョンのソフトウェアメンテナンスについて」。本文に「■作業日程 : 2026年10月21日15時00分 - 2026年10月22日18時00分」「■影響範囲 :　さくらのVPS 東京・大阪・石狩リージョン」（全角の空白を含む）。本文の頭に会員 ID と契約者名の行がある | 2026-10-23 Opus が Gmail で読み取りだけ |
| F13 | 業務用メールでの約 2 年の検索で、件名に「メンテナンス・障害・緊急・停止」を含むさくらのメールは 10/21 の 1 通。決済の案内「クレジットカード決済のお知らせ」は毎月 10〜11 日の 8 時ごろ（2026-05〜10 は毎月 1 通） | 同上 |
| F14 | Python の `imaplib.IMAP4.response(code)` は、受け取った応答コード（`select` の後の `UIDVALIDITY` など）のデータを返す。無ければ `(code, [None])` | https://docs.python.org/3.12/library/imaplib.html（Context7 は月の上限で使えず、公式文書を直接確かめる。担当は §4-1 の前に WebFetch で確かめ、違えば BLOCKED:） |

決めたこと（design.md §3-1-1 の具体化）:
- review@ の部品は変えない。新しい部品は `_decode_mime_header` と `_get_redis` だけを review@ の部品から import して使う（同じ処理を 2 か所に書かない）。
- 送るのは「差出人のドメインが `sakura.ad.jp` と完全に一致」かつ「件名に 8 つの言葉のどれかを含む」メールだけ。
  - `@sakura.ad.jp` で終わることで判定し、`@xxsakura.ad.jp` や `@sakura.ad.jp.example.com` を通さない（ドメインの部分が `sakura.ad.jp` と一致すること）。
- 本文は、送るメールに限り先頭 64KB だけ読む。取り出すのは「作業日時」の行と「影響範囲」の行の 2 つだけ。ほかの行は Discord にもログにも出さない（会員 ID・契約者名を出さないため。F12）。
  - 「影響範囲」の言葉は `影響範囲` と `対象サービス` だけにする。言葉の直後に `:`・`：` が来る行だけを取る（「会員ID :」「ご契約者名 :」の行を取り出しの言葉にしないため。言葉を増やすときは、この 2 つに当たらないことを試験 6 で確かめる）。
- 鍵は 3 種類:
  - `ops_mail:notified:<UIDVALIDITY>:<uid>`（30 日で消える。扱い終えたメール）
  - `ops_mail:last_sakura_mail_ts`（消えない。さくらの差出人のメールを最後に見た時刻）
  - `ops_mail:last_poll_ok_ts`（消えない。受け箱を最後に読めた時刻）
- 「扱い終えた」の印は、送るメールは Discord に送れたときだけ付ける（送れなければ次の回にもう一度）。送らないメール（さくら以外・件名で外れたさくら）はその場で付ける（毎回読み直さないため）。
- 検索は `SINCE`（7 日前の日付）。月の名前は英語の 3 文字を表で持つ（`strftime` の `%b` は地域の設定で日本語になりうるため）。
- 時刻は Mac や本文の日付ではなく、読んだときの `time.time()` を書く（本文の Date は書き手が決めるため）。

## 3. 触るファイル（これ以外は触らない）

- 新規: `backend/app/services/ops_mail_notifier.py`
- 新規: `backend/app/tasks/ops_mail_monitor.py`
- 新規: `backend/tests/test_ops_mail_notifier.py`
- 変更: `backend/app/celery_app.py`
- 変更: `backend/app/metrics.py`
- 変更: `backend/tests/test_metrics.py`
- 変更: `docker-compose.yml`
- 変更: `.github/workflows/deploy.yml`
- 変更: `.env.example`
- 変更: `monitoring/prometheus/alert_rules.yml`
- 変更: `monitoring/prometheus/tests/alert_rules_test.yml`
- 変更: `monitoring/tokens.yml`
- 変更: `docs/runbooks/alerts.md`
- 変更: `docs/handoff/outage-recovery-watch/card-bin3.md`（このカード。担当は §13 報告欄の追記のみ）
- リポジトリの外（commit しない）:
  - `/tmp/CC報告ファイル/outage-bin3/deploy/deploy-bin3.sh`（prod2 のルール）
  - `/tmp/CC報告ファイル/outage-bin3/deploy/rollback-bin3.sh`（prod2 のルール）
  - `/tmp/CC報告ファイル/outage-bin3/deploy/verify-bin3.sh`（prod1 の試験メール）

## 4. 作り方

4-1. `backend/app/services/ops_mail_notifier.py`（完成形の骨組み。関数の名前・定数の名前・鍵の名前はこのとおり）

- 頭の説明文（docstring）: 運用の受け箱を読み、さくらの点検・障害のメールの件名・作業日時・影響範囲だけを運用の Discord に送ること。本文はその 2 行以外を投稿もログもしないこと。設計 docs/handoff/outage-recovery-watch/design.md §3-1-1。
- import: `email`・`email.utils`・`imaplib`・`logging`・`os`・`re`・`time`・`httpx`、`from app.services.review_mail_notifier import _decode_mime_header, _get_redis`。
- 定数:

```python
_IMAP_HOST = os.getenv("REVIEW_MAIL_IMAP_HOST", "")
_IMAP_PORT = int(os.getenv("REVIEW_MAIL_IMAP_PORT", "993"))
_IMAP_USER = os.getenv("OPS_MAIL_IMAP_USER", "")
_IMAP_PASSWORD = os.getenv("OPS_MAIL_IMAP_PASSWORD", "")
_DISCORD_WEBHOOK = os.getenv("OPS_MAIL_DISCORD_WEBHOOK", "")

NOTIFIED_KEY_PREFIX = "ops_mail:notified:"
LAST_SAKURA_MAIL_TS_KEY = "ops_mail:last_sakura_mail_ts"
LAST_POLL_OK_TS_KEY = "ops_mail:last_poll_ok_ts"
_NOTIFIED_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 日
_SEARCH_DAYS = 7  # 7 日前から後だけ探す（30 日で鍵が消えた後に同じメールを送り直さないため）

_SENDER_DOMAIN = "sakura.ad.jp"
_SUBJECT_KEYWORDS = ("メンテナンス", "障害", "緊急", "停止", "工事", "再起動", "復旧", "作業")
_BODY_FETCH = "(BODY.PEEK[]<0.65536>)"  # 先頭 64KB だけ。既読にしない
_SCHEDULE_RE = re.compile(r"^[■●◆・\s]*(?:作業日程|作業日時|実施日時|メンテナンス日時|作業期間|日時)\s*[:：]\s*(.+?)\s*$", re.MULTILINE)
_SCOPE_RE = re.compile(r"^[■●◆・\s]*(?:影響範囲|対象サービス)\s*[:：]\s*(.+?)\s*$", re.MULTILINE)
_MAX_LINE_CHARS = 200
_MAX_SUBJECT_CHARS = 200
_MAX_DISCORD_CHARS = 1800
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
```

- `_SCHEDULE_RE`・`_SCOPE_RE` の `\s` は全角の空白（U+3000）にも当たる（Python の str の正規表現の既定）。§4-3 の試験 5 で確かめる。
- 関数（この 9 つ。ほかに足すときは報告に書く）:
  - `_is_configured() -> bool`: `_IMAP_HOST`・`_IMAP_USER`・`_IMAP_PASSWORD`・`_DISCORD_WEBHOOK` がすべて空でない。
  - `_is_sakura(from_header: str) -> bool`: `email.utils.parseaddr(from_header)[1].lower()` の `@` より後ろが `sakura.ad.jp` と一致。`@` が無ければ False。
  - `_is_ops_subject(subject: str) -> bool`: `_SUBJECT_KEYWORDS` のどれかを含む。
  - `_since_date(now: float) -> str`: `time.gmtime(now - _SEARCH_DAYS * 86400)` から `DD-Mon-YYYY`（例 `16-Oct-2026`。日は 2 桁、月は `_MONTHS`）。
  - `_body_text(raw: bytes) -> str`: `email.message_from_bytes(raw)` を `walk()` し、最初の `text/plain` の部分の `get_payload(decode=True)` を `get_content_charset() or "iso-2022-jp"` で `errors="replace"` で文字にする。読めない文字コード名（`LookupError`）は `utf-8` でやり直す。`text/plain` が無ければ空文字。例外は外に出さず空文字。
  - `_extract_lines(text: str) -> tuple[str | None, str | None]`: `_SCHEDULE_RE`・`_SCOPE_RE` の最初の一致の中身を `_MAX_LINE_CHARS` で切って返す。無ければ None。
  - `_build_content(subject: str, schedule: str | None, scope: str | None, date_str: str) -> str`: 下の完成形。
  - `_post_discord(content: str) -> bool`: review@ の `_post_discord`（F1）と同じ作り。webhook は `_DISCORD_WEBHOOK`、`username` は `"Sales Anchor 運用メール"`、`allowed_mentions` は常に `{"parse": []}`、`content[:_MAX_DISCORD_CHARS]`、timeout 10 秒。失敗は False（例外を外に出さない）。ログに webhook の値を出さない。
  - `check_and_notify() -> int`: 下の手順。

- Discord に送る文（完成形。行は `"\n"` でつなぎ、最後に改行を付けない。`schedule` が None なら作業日時の行の全文を `作業日時: 本文から読み取れませんでした（業務用メールで確かめてください）` にする。`scope` が None なら影響範囲の行を出さない。`date_str` が空なら `受信: 不明`）:

```
📢 さくらからの点検・障害のお知らせ
件名: ［緊急］さくらのVPS東京・大阪・石狩リージョンのソフトウェアメンテナンスについて
作業日時: 2026年10月21日15時00分 - 2026年10月22日18時00分
影響範囲: さくらのVPS 東京・大阪・石狩リージョン
受信: Wed, 21 Oct 2026 16:05:00 +0900
本文は業務用メールで確かめてください
```

- `check_and_notify()` の手順（上から順。例外は外に出さず、ログに 1 行書いて 0 を返す）:
  1. `_is_configured()` が False → info のログ 1 行で 0。
  2. `redis_client = _get_redis()`。None → warning のログ 1 行で 0（重複を防げないので送らない。review@ と同じ）。
  3. `imaplib.IMAP4_SSL(_IMAP_HOST, _IMAP_PORT)` → `login` → `select("INBOX")`。`uidvalidity = conn.response("UIDVALIDITY")[1][0]`（bytes なら decode。None なら `"0"`）。
  4. `conn.uid("search", None, "SINCE", _since_date(now))`（`now = time.time()`）。応答が OK でなければ 0（読めた時刻は書かない）。
  5. 読めた時刻を書く: `redis_client.set(LAST_POLL_OK_TS_KEY, now)`。続けて `redis_client.set(LAST_SAKURA_MAIL_TS_KEY, now, nx=True)`（鍵が無いときだけ。40 日の数え始め。design.md §3-1-1）。
  6. 見つかった uid ごとに:
     - 鍵 `NOTIFIED_KEY_PREFIX + uidvalidity + ":" + uid` があれば飛ばす。
     - `BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)]` でヘッダーを読み、`email.message_from_bytes` で `msg` にする。
     - `_is_sakura` には文字にする前の生の From（`msg.get("From", "")`）を渡す（文字にした後の表示名に「,」があると `parseaddr` が空を返し、本物のさくらのメールを取りこぼすため。2026-10-23 審査で実測）。
     - 件名は `_decode_mime_header(msg.get("Subject", ""))` で文字にし、`_MAX_SUBJECT_CHARS` で切る。受信の日時は `msg.get("Date", "")`（空なら `不明`）。
     - `_is_sakura` が False → 印を付けて次へ（送らない）。
     - さくら: `redis_client.set(LAST_SAKURA_MAIL_TS_KEY, now)`。
     - `_is_ops_subject` が False → 印を付けて次へ（送らない）。
     - 送る: `_BODY_FETCH` で本文の先頭を読み、`_body_text` → `_extract_lines` → `_build_content` → `_post_discord`。True なら印を付けて数を 1 足す。False なら印を付けない。
     - 印: `redis_client.set(鍵, "1", ex=_NOTIFIED_TTL_SECONDS)`。
     - 1 通の中の例外は warning のログ 1 行（uid だけ）で次へ。
  7. 送った数を返す。`finally` で `logout()`（例外は無視）。
- ログに書いてよいのは: uid・送った/送らなかった・送らなかった理由（`not_sakura`・`subject_filtered`・`post_failed`）・数。件名・差出人・本文・パスワード・webhook は書かない。
- ログの行の形（このとおり。§4-13 の verify-bin3.sh が文字で探す）: 送った `[ops_mail] notified uid=123`、送らなかった `[ops_mail] skipped uid=123 reason=not_sakura`、1 回の終わり `[ops_mail] done notified=1`。この 3 つは info で書く（celery-worker は `--loglevel=info` で動く。docker-compose.yml:217。debug では verify-bin3.sh が行を見つけられない）。

4-2. `backend/app/tasks/ops_mail_monitor.py`: `backend/app/tasks/review_mail_monitor.py` と同じ形（担当は最初に全文を読む）。task 名 `app.tasks.ops_mail_monitor.check_ops_mail_inbox`、`max_retries=0`、`ops_mail_notifier.check_and_notify()` を呼んで `{"notified": n}` を返す。

4-3. `backend/tests/test_ops_mail_notifier.py`（pytest。IMAP・Redis・httpx はすべて MagicMock と patch。`backend/tests/test_review_mail_notifier.py` の書き方に揃える。担当は最初に全文を読む）。最低限この 16 件:
1. `_is_sakura`: `"さくら <support@sakura.ad.jp>"`・`"domain@SAKURA.AD.JP"` は True。`"x@xsakura.ad.jp"`・`"x@sakura.ad.jp.example.com"`・`"support@sakura.ad.jp.evil"`・`"not-an-address"` は False。表示名「さくらインターネット株式会社, サポート」を RFC 2047 で符号化した生の From（`email.header.Header("さくらインターネット株式会社, サポート", "utf-8").encode() + " <support@sakura.ad.jp>"`）は True。
2. `_is_ops_subject`: 10/21 の件名（F12）は True。「クレジットカード決済のお知らせ」は False。
3. `_since_date`: 2026-10-23 00:00 UTC の秒で `"16-Oct-2026"`。2026-01-03 で `"27-Dec-2025"`。
4. `_extract_lines`: F12 の 2 行を含む本文から `("2026年10月21日15時00分 - 2026年10月22日18時00分", "さくらのVPS 東京・大阪・石狩リージョン")`。
5. `_extract_lines`: 全角の空白とコロン（`■作業日時　：　…`）でも取れる。行が無ければ `(None, None)`。300 文字の行は 200 文字に切られる。
6. `_extract_lines`: 「会員ID : XX000000」「ご契約者名 : 試験 太郎」「対象会員ID : XX000000」の行は、どちらにも当たらない。
7. `_body_text`: iso-2022-jp の text/plain、utf-8 の multipart（text/plain と text/html）、文字コードの無い本文、64KB で途中まで切れた本文、のそれぞれで例外を出さず文字が返る。
8. `_build_content`: 完成形（§4-1）と一字一句同じ。`schedule` None で「本文から読み取れませんでした」の行、`scope` None で影響範囲の行が無い。
9. `check_and_notify`: 未設定（webhook が空）なら IMAP に接続しない・0。
10. `check_and_notify`: Redis が None なら IMAP に接続しない・Discord に送らない・0。
11. `check_and_notify`: さくら・件名あり 1 通 → Discord に 1 回送る。送った本文に会員 ID と契約者名の文字が含まれない。鍵 `ops_mail:notified:<UIDVALIDITY>:<uid>` に ex 30 日で印。`LAST_SAKURA_MAIL_TS_KEY` と `LAST_POLL_OK_TS_KEY` に時刻。戻り値 1。`allowed_mentions` が `{"parse": []}`。
12. `check_and_notify`: さくら・件名なし（決済の案内）1 通 → Discord に送らない。本文を読まない（`_BODY_FETCH` の fetch が呼ばれない）。印が付く。`LAST_SAKURA_MAIL_TS_KEY` に時刻。戻り値 0。
13. `check_and_notify`: さくら以外 1 通 → Discord に送らない・本文を読まない・印が付く・`LAST_SAKURA_MAIL_TS_KEY` は `nx=True` の 1 回だけ（さくらとしての更新は無い）。
14. `check_and_notify`: Discord が 500 → 印が付かない・戻り値 0。次の回に同じ uid でもう一度送る。
15. `check_and_notify`: 印が既にある uid は fetch しない。search が `SINCE` と `_since_date` の値で呼ばれる（`ALL` ではない）。
16. `check_and_notify`: ログ（`caplog`）に件名・差出人・会員 ID・パスワード・webhook の文字が出ない。
- 試験の本文に本物の会員 ID・契約者名・メールアドレスを書かない（「XX000000」「試験 太郎」「support@sakura.ad.jp」だけを使う）。

4-4. `backend/app/celery_app.py`（足すだけ）:
- include の `"app.tasks.review_mail_monitor",` の行（:33）の次に: `"app.tasks.ops_mail_monitor",  # さくらの点検・障害のメール → 運用 Discord（outage-recovery-watch 便3）`
- beat の `"review-mail-discord-notifier"` の項目の次に:

```python
    # 運用の受け箱を 5 分ごとに確認し、さくらの点検・障害のメールを運用 Discord へ（outage-recovery-watch 便3）
    # 未設定（OPS_MAIL_IMAP_USER 等）の場合は no-op で安全スキップ
    "ops-mail-discord-notifier": {
        "task": "app.tasks.ops_mail_monitor.check_ops_mail_inbox",
        "schedule": 300.0,  # 5分
    },
```

4-5. `backend/app/metrics.py`（足すだけ）:
- `VIEWER_INVENTORY_LAST_HOLD_TS` の定義の後に:

```python
OPS_MAIL_LAST_SAKURA_MAIL_TS = Gauge(
    "salesanchor_ops_mail_last_sakura_mail_timestamp_seconds",
    "運用の受け箱で、さくらの差出人のメールを最後に見た時刻（UNIX 秒。0 は未設定）",
)

OPS_MAIL_LAST_POLL_OK_TS = Gauge(
    "salesanchor_ops_mail_last_poll_success_timestamp_seconds",
    "運用の受け箱を最後に読めた時刻（UNIX 秒。0 は未設定）",
)
```

- `_update_viewer_inventory_gauges` の後に、同じ形の `_update_ops_mail_gauges()`（中で `from app.services.ops_mail_notifier import LAST_POLL_OK_TS_KEY, LAST_SAKURA_MAIL_TS_KEY  # noqa: PLC0415`。Redis が None なら 2 つとも 0）。
- `/metrics` の中、viewer の try/except の後に、同じ形の try/except（例外なら 2 つとも 0）。
- `backend/tests/test_metrics.py` に 1 件足す（既存の :14 の試験の書き方に揃える）: Redis の偽物が 2 つの鍵に `"1761200000.0"` を返すと、`/metrics` の本文に 2 つの指標の名前と値が出る。

4-6. `docker-compose.yml` の celery-worker（足すだけ）: `REVIEW_MAIL_DISCORD_MENTION` の行（:247）の次に:

```yaml
      # 運用の受け箱（さくらの点検・障害のメール → 運用 Discord。outage-recovery-watch 便3）。接続先は REVIEW_MAIL_IMAP_HOST/PORT を使う
      - OPS_MAIL_IMAP_USER=${OPS_MAIL_IMAP_USER:-}
      - OPS_MAIL_IMAP_PASSWORD=${OPS_MAIL_IMAP_PASSWORD:-}
      - OPS_MAIL_DISCORD_WEBHOOK=${OPS_MAIL_DISCORD_WEBHOOK:-}
```

- celery-worker 以外のサービスには足さない（`/metrics` は Redis の鍵だけを読み、この 3 つを使わない）。
- 作業の前に `sed -n '236,250p' docker-compose.yml` で、:240-247 が celery-worker の段であることを確かめる（service の名前を報告に書く）。違えば BLOCKED:。

4-7. `.github/workflows/deploy.yml`（足すだけ。既存の行は変えない）:
- 消す行: `-e '/^REVIEW_MAIL_DISCORD_WEBHOOK=/d' \`（:300）の次に 3 行:

```
              -e '/^OPS_MAIL_IMAP_USER=/d' \
              -e '/^OPS_MAIL_IMAP_PASSWORD=/d' \
              -e '/^OPS_MAIL_DISCORD_WEBHOOK=/d' \
```

- 足す行: `REVIEW_MAIL_DISCORD_WEBHOOK='${{ secrets.REVIEW_MAIL_DISCORD_WEBHOOK }}'`（:346）の次に 3 行:

```
            OPS_MAIL_IMAP_USER='${{ secrets.OPS_MAIL_IMAP_USER }}'
            OPS_MAIL_IMAP_PASSWORD='${{ secrets.OPS_MAIL_IMAP_PASSWORD }}'
            OPS_MAIL_DISCORD_WEBHOOK='${{ secrets.OPS_MAIL_DISCORD_WEBHOOK }}'
```

- 字下げは前後の実物の行に揃える。行番号がずれていれば、REVIEW_MAIL_DISCORD_WEBHOOK の 2 か所を手がかりに合わせる（報告に書く）。
- このファイルの編集が見張り（フック）に止められたら、言い換えずに BLOCKED:（止まった原文を報告）。

4-8. `.env.example`（足すだけ）: review@ の段（:104-116）の次に、空行と次の段:

```
# --- 運用の受け箱（さくらの点検・障害のメール → 運用 Discord。outage-recovery-watch 便3） ---
# GitHub Secrets → deploy.yml → VPS .env に自動同期。接続先は REVIEW_MAIL_IMAP_HOST / REVIEW_MAIL_IMAP_PORT を使う。
# 未設定の場合は Celery タスクが no-op で安全スキップする。
# アドレス・パスワード・webhook はこのファイルにも書かない（公開リポジトリ）。
OPS_MAIL_IMAP_USER=
OPS_MAIL_IMAP_PASSWORD=
OPS_MAIL_DISCORD_WEBHOOK=
```

4-9. `monitoring/prometheus/alert_rules.yml` の最後（`recovery_check_alerts` の後）に足す（完成形。他の行は変えない）:

```yaml
  - name: ops_mail_alerts
    rules:
      # 運用の受け箱に、さくらの差出人のメールが 40 日届いていない（Gmail の転送切れの兆し。tokens.yml: ops_mail_silent_sec=3456000）
      # backend/app/metrics.py が Redis から読んで出す。0（未設定）のときは鳴らない
      - alert: OpsMailSilent
        expr: (time() - salesanchor_ops_mail_last_sakura_mail_timestamp_seconds{job="backend"}) > 3456000 and salesanchor_ops_mail_last_sakura_mail_timestamp_seconds{job="backend"} > 0
        for: 1h
        labels:
          severity: warning
          tier: ticket
        annotations:
          summary: "さくらからのメールが 40 日届いていません"
          description: "運用の受け箱に、さくらの差出人のメールが {{ $value | humanizeDuration }} 届いていません（閾値: 40 日。決済の案内は毎月届きます）。業務用メールの自動転送が切れている見込みがあります。"
          runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#opsmailsilent"

      # 運用の受け箱を 3 時間読めていない（パスワードの誤り・受け箱の削除・celery の停止。tokens.yml: ops_mail_poll_stale_sec=10800）
      - alert: OpsMailPollStale
        expr: (time() - salesanchor_ops_mail_last_poll_success_timestamp_seconds{job="backend"}) > 10800 and salesanchor_ops_mail_last_poll_success_timestamp_seconds{job="backend"} > 0
        for: 10m
        labels:
          severity: warning
          tier: ticket
        annotations:
          summary: "運用の受け箱を 3 時間読めていません"
          description: "さくらの点検・障害のメールを読む処理が {{ $value | humanizeDuration }} の間、受け箱を読めていません（閾値: 3 時間）。この間、さくらのお知らせは Discord に届きません。"
          runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#opsmailpollstale"
```

- 作業の前に `grep -n "^  - name:" monitoring/prometheus/alert_rules.yml` で最後のグループが `recovery_check_alerts` であることを確かめる（違えば BLOCKED:。便2 が入っていない）。

4-10. `monitoring/prometheus/tests/alert_rules_test.yml`（:4 の「全 32 本」を「全 34 本」に直す。他の試験は変えない）。最後に足す。入力ごとに test group を分ける。系列の札は `job="backend", instance="app-vps"`。
1. OpsMailSilent 鳴る: `interval: 1m`、`salesanchor_ops_mail_last_sakura_mail_timestamp_seconds` を `'1x58000'`（`interval: 1h` にすると、各時刻の 5 分後から次の時刻まで系列が見えず for 1h が毎時途切れて鳴らない。2026-10-23 審査の指摘。既存の試験 50 組も 1m か 15s）。`eval_time` 962h（経過 3463199 秒 > 3456000 が 1 時間以上）で 1 件。`exp_labels` は job・instance・severity・tier。`exp_annotations` は 3 つとも書く（humanizeDuration の展開は CI の got に合わせる。便1・便2 と同じ）。
2. OpsMailSilent 鳴らない（40 日たたない）: 同じ入力で `eval_time` 900h に 0 件。
3. OpsMailPollStale 鳴る: `interval: 1m`、`salesanchor_ops_mail_last_poll_success_timestamp_seconds` を `'1x300'`。`eval_time` 4h（経過 14399 秒 > 10800 が 10 分以上）で 1 件。`exp_annotations` は 3 つとも。
4. 鳴らない（未設定）: 2 つの指標を `'0x300'`（`interval: 1m`）で `eval_time` 4h に、OpsMailSilent も OpsMailPollStale も 0 件。
- 【未確認】試験 1・2 は 1 分おきに 962 時間分（約 58000 点）を評価するため、promtool の所要が延びる見込みがある。CI の monitoring-check の所要を便2 の後の実測と比べて報告に書く（担当は CI を待たない。Opus が確かめる。§6）。

4-11. `docs/runbooks/alerts.md`（:3 の「Prometheus 32 本」を「34 本」に直す）。最後に `## OpsMailSilent`・`## OpsMailPollStale` の 2 節を足す。形は既存の節（`- 札：`・`- 何が起きているか：`・`- 影響：`・`- 最初に見るもの：`・`- 直し方：`・`- 止め方：`）。書くこと:
- OpsMailSilent:
  - 札：ticket
  - 何が起きているか：運用の受け箱に、さくらの差出人のメールが 40 日届いていない。さくらは決済の案内を毎月送るので、業務用メールの自動転送（さくらの差出人だけを転送する設定）が切れている見込みがある。
  - 影響：さくらの点検・障害の予告が Discord に届かない。
  - 最初に見るもの：PO の業務用メールに、この 40 日の間にさくらからのメールがあるか（PO に聞く）。あれば転送の設定（Gmail の設定 → 転送とフィルタ）。無ければ、さくらが送っていないだけなので、次の決済の案内まで待つ。
  - 直し方：転送の設定を PO が直す（card-bin3.md §8-6 の手順）。直った後、次にさくらからメールが届けば自動で解決する。
  - 止め方：`amtool silence add alertname=OpsMailSilent --duration=PERIOD --comment=REASON`
- OpsMailPollStale:
  - 札：ticket
  - 何が起きているか：裏方の処理（celery）が運用の受け箱を 3 時間読めていない。
  - 影響：さくらの点検・障害のメールが Discord に届かない。
  - 最初に見るもの：同じ時間に CeleryHeartbeatStale が鳴っているか（鳴っていればその節）。prod1 の celery-worker のログの `[ops_mail]` の行（接続の失敗・ログインの失敗）。
  - 直し方：パスワードを変えた・受け箱を消したなら、PO が受け箱と GitHub の secret を直し、Opus が通常のデプロイで本番の設定に入れる。直れば自動で解決する。
  - 止め方：`amtool silence add alertname=OpsMailPollStale --duration=PERIOD --comment=REASON`
- 受け箱のアドレス・IP・鍵のパス・webhook を書かない（公開リポジトリ）。

4-12. `monitoring/tokens.yml`:
- `thresholds:` の中、便2 で足した `recovery_check_stale_sec` の段の後に、空行と次の段:

```yaml
  # 運用の受け箱（alert_rules.yml: ops_mail_alerts）
  ops_mail_silent_sec:     3456000  # OpsMailSilent: time() - salesanchor_ops_mail_last_sakura_mail_timestamp_seconds > 3456000（40 日）
  ops_mail_poll_stale_sec:   10800  # OpsMailPollStale: time() - salesanchor_ops_mail_last_poll_success_timestamp_seconds > 10800（3 時間）
```

- `for_durations:` の最後（便2 の `recovery_check_stale` の後）に:

```yaml
  ops_mail_silent:      "1h"   # OpsMailSilent
  ops_mail_poll_stale:  "10m"  # OpsMailPollStale
```

- 作業の前に `grep -n "recovery_check_stale" monitoring/tokens.yml` で 2 行あることを確かめる（無ければ BLOCKED:）。

4-13. 本番配置の台本 3 本（リポジトリの外。commit しない）を Write で作る。担当は実行しない（実行は Opus が PO の同意票を受けて行う）。置き場は `/tmp/CC報告ファイル/outage-bin3/deploy/`。
- 共通:
  - 形は便2 の台本 `/tmp/CC報告ファイル/outage-bin2/deploy/deploy-bin2.sh` と便1 の `/tmp/CC報告ファイル/outage-bin1/deploy/deploy-bin1.sh` に揃える（担当は最初に両方の全文を読む。無ければ BLOCKED:）。
    - 接続先（機体・利用者 `ubuntu`・鍵 `~/.ssh/manual-only/id_ed25519`・IP の決め方）は台本の実物から写す。推測で利用者名を書かない（fail2ban に当たる）。sudo は使わない。
    - `set -euo pipefail`、`tee` で生出力を残す。秘密（パスワード・webhook・受け箱のアドレス）の値は出さない。
- `deploy-bin3.sh`（prod2。引数 1 つ＝実装 PR のマージ commit の sha）。手順は deploy-bin2.sh の 1〜4・6・7・10・11 の型で、対象は `monitoring/prometheus/alert_rules.yml` の 1 本だけ:
  1. 書き込みの確かめ（`/opt/salesanchor-monitoring/monitoring/prometheus` と `backups` に `test -w`）。
  2. 本番の alert_rules.yml の sha256 が `"${MC}^1:monitoring/prometheus/alert_rules.yml"` と一致（違えば止まる）。
  3. `backups/outage-bin3/` に日付つきの控え。
  4. silence の数（1 以上なら止まる）・鳴っている警報の alertname の一覧。
  5. マージ commit の版を一時ディレクトリへ送り、`promtool check rules`（期待 `SUCCESS: 34 rules found`）。
  6. `install -m 644` で置き、sha256 の一致を出す。Prometheus を `/-/reload`。
  7. 読み取りで確かめて出す（期待外れがあっても全部出してから exit 1）:
     - `/api/v1/rules` のルール数（期待 34）、`ops_mail_alerts` の 2 本の名前と `health`（期待 ok）、`health` が ok でないルールの数（期待 0）。
     - `/api/v1/query` で `salesanchor_ops_mail_last_poll_success_timestamp_seconds{job="backend"}` の値と `time() - …`（期待: 値が 0 より大きく、差が 900 未満。prod1 のデプロイが済み、secret が入っていれば 5 分ごとに進む）、`salesanchor_ops_mail_last_sakura_mail_timestamp_seconds{job="backend"}` の値（期待: 0 より大きい）。
     - `ALERTS{alertname=~"OpsMail.*"}` の件数（期待 0）。
     - 受け箱の時刻が期待外れ（0 か、差が 900 以上）のときは、台本の中で 330 秒待ってから 1 回だけ読み直し、2 回目の値で判断する（デプロイで celery-beat が作り直され、1 回目の読みは起動の約 300 秒後のため。deploy.yml:446-453）。
- `rollback-bin3.sh`（prod2。引数 1 つ＝控えの日付の文字列）: 控えを `install -m 644` で戻し、`/-/reload`、sha256 の一致とルール数（期待 32）を出す。
- `verify-bin3.sh`（prod1。引数なし。G1 の本番での確かめ）:
  - prod1 の作業ツリーは `/home/ubuntu/salesanchor`（docs/handoff/ai-ops-247/card-stage1-bin6.md の F4）。コマンドはその `cd` の後に `docker compose exec -T celery-worker ...` で実行する。担当は作る前に、便の記録（card-stage1-bin6.md §8-5 など）で prod1 の `docker compose` の呼び方を確かめ、報告に出典を書く。確かめられなければ BLOCKED:。
  1. 実行した時刻（日本時間）を出す。celery-worker の中で `OPS_MAIL_IMAP_USER`・`OPS_MAIL_IMAP_PASSWORD`・`OPS_MAIL_DISCORD_WEBHOOK`・`REVIEW_MAIL_IMAP_HOST` が空でない数を出す（期待 4。値は出さない）。4 でなければ exit 1。
  2. celery-worker の中の python で、運用の受け箱に試験のメールを 1 通だけ入れる（`imaplib` の `append("INBOX", None, imaplib.Time2Internaldate(time.time()), msg_bytes)`。送信ではなく受け箱への書き込み）。メールの中身（完成形。日付は実行時の値）:
     - `From: さくらインターネット（試験） <support@sakura.ad.jp>`（RFC 2047 で符号化）
     - `Subject: ［試験］さくらのVPS メンテナンスのお知らせ（Sales Anchor の転送の確かめ）`（同上）
     - 本文（utf-8 の text/plain）: `会員ID : XX000000` / `ご契約者名 : 試験 太郎` / `■作業日程 : 2026年10月24日10時00分 - 2026年10月24日11時00分（試験）` / `■影響範囲 :　試験（実際の作業はありません）`
     - append の応答（OK か）と、入れた時刻を出す。
  3. celery-worker のログを、`[ops_mail] notified uid=` を含む行が出るまで、最大 54 回・10 秒おき（最大 9 分。Opus のコマンドの上限 10 分に収めるため）に `docker compose logs --since "${APPENDED_AT}" celery-worker` で読む（`APPENDED_AT` は手順 2 の時刻を RFC 3339 で入れた変数）。出た時刻と、手順 2 からの経過秒を出す（期待 600 未満）。9 分で出なければ、`[ops_mail]` の行を全部出して exit 1。
  4. Redis の 2 つの時刻の鍵の値と、今との差を出す（celery-worker の中の python で `_get_redis()` を使う）。
  - 試験のメールは受け箱に残してよい（印が付いているので二度と送らない）。

## 5. 確かめ方（担当が実行し、出力を報告に貼る）

5-1. `cd backend && python -m pytest tests/test_ops_mail_notifier.py tests/test_review_mail_notifier.py tests/test_metrics.py tests/test_celery_beat_registered.py -q` の最後の 5 行（期待: 失敗 0。test_review_mail_notifier の 39 件が通る）。backend の試験の実行の仕方は backend/AGENTS.md・backend/CLAUDE.md に従う（別の書き方なら、その出典を報告に書く）。
5-2. `python3 monitoring/scripts/check_alert_rules.py` が exit 0 で `OK: Prometheus 34 rules, Loki 6 rules, runbook 40 sections`。あわせて `grep -n "alert: OpsMail" monitoring/prometheus/alert_rules.yml`（期待 2 行）。
5-3. `git diff --numstat "$(git merge-base origin/main HEAD)" -- backend/app/celery_app.py backend/app/metrics.py docker-compose.yml .github/workflows/deploy.yml .env.example monitoring/prometheus/alert_rules.yml monitoring/tokens.yml` の出力。期待: 7 本とも 2 列目（削除行数）が 0。
5-4. `git diff --stat "$(git merge-base origin/main HEAD)" -- backend/app/services/review_mail_notifier.py backend/app/tasks/review_mail_monitor.py backend/tests/test_review_mail_notifier.py` が空（review@ を変えていない）。
5-5. わざと壊して落ちることを確かめる: `_is_sakura` を一時的に「`sakura.ad.jp` を含めば True」に書き換えると試験 1 が落ちる。`_extract_lines` で `_SCOPE_RE` の言葉に `会員ID` を足すと試験 6 が落ちる（`対象` を足しても落ちない。言葉の直後にコロンを求めるため）。確かめたら Edit で戻す（`git checkout` は使わない）。戻した後に 5-1 がもう一度通る最後の 5 行を出す。
5-6. 手順書の見出し: `grep -c '^## ' docs/runbooks/alerts.md`（期待 40）と `grep -n '^## OpsMail' docs/runbooks/alerts.md`（期待 2 行）。
5-7. promtool は Mac では実行しない（Mac に無く、Docker も起動しない）。PR の CI `monitoring-check` で動く。担当は PR を作った後に `gh pr checks` の行のうち monitoring-check と backend の試験の行を貼る（待たない。合否は Opus が確かめる）。
5-8. `python3 monitoring/scripts/validate_tokens.py` の終了コードと「閾値ズレ」の行（期待: exit 0・閾値ズレ 0 行）。
5-9. `bash -n` を台本 3 本に実行した終了コード（期待 0）。3 本の全文を報告に貼る（鍵のパスと利用者名は伏せずに貼ってよい。秘密の値は台本に書かない）。
5-10. 公開してはいけない文字が無いこと: `git diff "$(git merge-base origin/main HEAD)" | grep -nE "[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+|@salesanchor\.jp|discord\.com/api/webhooks"` の該当（期待: 足した行（`+` で始まる行）には 0 行）。
5-11. `git diff "$(git merge-base origin/main HEAD)" --stat` が §3 のリポジトリ内の 14 ファイルであること。
5-12. `grep -n "_SUBJECT_KEYWORDS\|_SENDER_DOMAIN\|NOTIFIED_KEY_PREFIX\|LAST_SAKURA_MAIL_TS_KEY\|LAST_POLL_OK_TS_KEY" backend/app/services/ops_mail_notifier.py backend/app/metrics.py`（言葉と鍵の名前が §4-1 のとおり 1 か所で定義され、metrics.py は import していること）。

## 6. 分岐ごとの対処

- 5-1〜5-6・5-8〜5-12 の出力が違う → 直してやり直す（記録のみで続行）。
- F14 の公式文書の確かめで、`response("UIDVALIDITY")` の形が違う → BLOCKED:（文書の該当の文を貼る）。
- 最後のグループが `recovery_check_alerts` でない・`recovery_check_stale` が tokens.yml に無い（便2 が入っていない）→ BLOCKED:。
- docker-compose.yml の :240-247 が celery-worker でない → BLOCKED:。
- `.github/workflows/deploy.yml` の編集がフックに止められた → BLOCKED:（言い換えない）。
- CI の結果は担当は待たない。落ちていたら Opus が担当に出力を渡して直させる。
  - promtool の test の落ちは試験の期待値（展開後の文字列）を直す。§4-9 の式・閾値・札を変えて合わせることはしない。
  - monitoring-check の所要が便2 の後より 3 分以上延びたら、Opus が試験 1 の作り（`interval` と `eval_time`）を見直す。
- この Mac で `colima`・`docker`・`limactl` を打たない（docs/ops/runner-commands.md:351）。

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| さくらの差出人で件名に 8 つの言葉のどれかがあるメールだけが Discord に 1 件届き、件名・作業日時（取れなければ「読み取れませんでした」）・影響範囲・受信の日時が載る。会員 ID・契約者名・ほかの本文は載らない | 単体試験 1〜8・11・16（§5-1）・壊すと落ちる（§5-5） |
| さくら以外・件名で外れたさくらのメールは送られず、本文も読まれない | 単体試験 12・13 |
| 送れなかったメールは次の回に送り直し、送ったメールは二度と送らない。7 日より前のメールは探さない | 単体試験 14・15 |
| review@ の通知は変わらない | §5-4 が空・test_review_mail_notifier の 39 件が通る（§5-1） |
| 見張り 2 本が §4-9 の完成形で入り、既存の 32 本は変わらない。札・手順書リンク・見出しの検査が通る（34 本・40 節）。未設定のときは鳴らない | §5-2・§5-3・§5-6・CI の promtool（試験 1〜4） |
| 本番で受け箱を 5 分ごとに読めていて、ルールに評価の失敗が無い | §8-4（deploy-bin3.sh の手順 7） |
| G1: さくらの形の試験メールが受け箱に入ってから 10 分以内に、件名と作業日時つきで Discord の運用チャンネルに 1 件届く | §8-5（verify-bin3.sh の経過秒）＋ PO が Discord で目で確かめる |
| G1（転送）: PO の業務用メールに届いたさくらのメールが、転送で受け箱に入る | §8-7（次の決済の案内 2026-11-11 ごろで「さくらのメールを見た時刻」が進む。件名で外れるので Discord には届かないのが正しい） |

- 時間の見込み: 受け箱に入ってから Discord まで、beat の 5 分の間隔＋1 回分の処理で最悪約 5 分強。Gmail の転送の遅れは【未確認】（§8-7 で実測し、次にさくらの点検のメールが届いたときに記録する）。

## 8. 本番への配置（マージの前後。PO の画面の作業と、Opus の配置）

- 機体: prod1 は main へのマージで動く通常のデプロイ（deploy.yml）で入る。試験メールの 1 通（verify-bin3.sh）だけ、prod1 に無制限鍵で入って行う。prod2 はルールの配置だけで、無制限鍵を使う。無制限鍵は、PO の同意票（ADR-1033）を受けた Opus だけが使う。担当は使わない。

8-1. マージの前に PO が行う画面の作業（Opus が PO にこの手順を日常語で渡す。パスワード・webhook はチャットに貼らない）:
- P1. さくらのレンタルサーバーのコントロールパネルで、メールアドレスを 1 つ作る（review@ と同じサーバー）。名前は推測されにくいものにする。パスワードは英字と数字だけで作る（記号の `'`・`"`・`$` は使わない。本番の設定ファイルに `'…'` で囲んで書くため、入ると値が壊れる）。迷惑メールの仕分けの設定を開き、「受信箱以外へ移す・捨てる」になっていれば「何もしない」にする（転送されたメールが受信箱の外へ移ると届かないため。画面の名前は【未確認】で、見当たらなければ Opus に画面の写真を送る）。
- P2. Discord の運用チャンネル（警報が届くチャンネル）の設定 → 連携サービス → ウェブフックで、新しいウェブフックを 1 つ作り、URL を写す。
- P3. GitHub の画面（リポジトリの Settings → Secrets and variables → Actions → New repository secret）で 3 つ登録する: `OPS_MAIL_IMAP_USER`（P1 のアドレス）・`OPS_MAIL_IMAP_PASSWORD`（P1 のパスワード）・`OPS_MAIL_DISCORD_WEBHOOK`（P2 の URL）。
- Opus が `gh secret list` で 3 つの名前があることだけを確かめる（値は見えない・見ない）。

8-2. GO 記録とマージ（Opus）:
- 危険 PR（deploy.yml）なので、PR 本文に `### GO記録` を書く（発行者: PO の委任に基づく Claude Opus 発行。委任 ID・PR 番号・HEAD・変更の 3 行・審査と CI の根拠・日時。直前のバックアップの確かめ: 当日の本番 DB のバックアップの成功時刻を Prometheus の `backup_local_last_success_timestamp` で確かめて書く）。PO の GO の原文は書かない（創作しない）。
- 新しく立てた Opus の reviewer の APPROVE（その HEAD）と CI 緑の後に、`bash scripts/gh-pr-merge-safe.sh --merge` でマージする。
- マージで deploy.yml が動く。Opus はその実行の成否を `gh run list --workflow deploy.yml --limit 1` で確かめる（待つときは Opus の側で。担当は待たない）。

8-3. Opus が台本 3 本を読み、§4-13 と合うか確かめる。

8-4. Opus が PO に同意票を出す（1 枚にまとめる）:
- 操作1: `bash /tmp/CC報告ファイル/outage-bin3/deploy/deploy-bin3.sh マージcommitのsha`（prod2 に見張り 2 本を置く）
- 操作2: `bash /tmp/CC報告ファイル/outage-bin3/deploy/verify-bin3.sh`（prod1 の運用の受け箱に試験メールを 1 通入れ、Discord に届くまでを測る）
- 実行は、§8-2 の deploy.yml の実行が終わってから 10 分たった後に限る。
- PO の「1」を受けて Opus が実行し、生出力を `/tmp/CC報告ファイル/outage-bin3/deploy/` に残す。自動の許可判定に止められたら、言い換えずに PO に `!` での実行を頼む（便1・便2 と同じ）。

8-5. 結果を PR にコメントで追記する。PO に Discord の運用チャンネルで、試験のお知らせが 1 件・件名と作業日時つきで届いたことを目で確かめてもらう。

8-6. PO が行う転送の設定（8-5 の後）:
- P4. 業務用メール（Gmail）の設定 → 転送と POP/IMAP → 「転送先アドレスを追加」に P1 のアドレスを入れる。確認のメールが P1 の受け箱に届くので、さくらのウェブメールで開いて確認のコードを Gmail に入れる（このメールはさくらの差出人ではないので Discord には届かない）。
- P5. Gmail の検索で差出人に `sakura.ad.jp` と入れ →「フィルタを作成」→「次のアドレスに転送する」に P1 のアドレスを選ぶ。全体の自動転送はオンにしない（さくら以外のメールを転送しない）。
- 転送先の追加が「管理者が許可していない」と出たら止めて Opus に知らせる（U4。Opus が別の案を PO に出し直す）。

8-7. 転送の確かめ（後日。Opus）:
- 次にさくらからメールが届いた日（毎月の決済の案内。2026-11-11 ごろ）の後に、Prometheus の `salesanchor_ops_mail_last_sakura_mail_timestamp_seconds{job="backend"}` が届いた時刻の後に進んだことを確かめ、PR にコメントで書く。進んでいなければ PO と転送の設定を見直す。
- 次にさくらの点検・障害のメールが届いたときに、業務用メールの受信時刻と Discord の時刻の差を記録する（設計「継続」）。

§8 の分岐:
- 8-1 の P1〜P3 が終わらない → マージしない（secret が空でも害は無い（未設定なら何もしない）が、後から入れるとデプロイをもう 1 回要するため）。
- 8-2 で deploy.yml の実行が落ちる → Opus が原因を見て、本番障害なら PO に報告し、PR の revert をマージする（§9）。
- deploy-bin3.sh の手順 1〜5 で止まる → 置かずに止まる（Opus が PO に報告）。手順 6 の後に落ちる → `rollback-bin3.sh` を同意票で出し直して戻す。
- 手順 7 で受け箱を読めていない（値が 0 か、差が 900 以上）→ 戻さずに verify を行わない。celery-worker のログの `[ops_mail]` の行で、接続・ログインの失敗か、secret の空かを見て、Opus が PO に報告する（P1・P3 のやり直し）。
- verify で 9 分以内に送らない → `[ops_mail]` の行の理由（`not_sakura`・`subject_filtered`・`post_failed`）を見る。`post_failed` なら P2 の webhook を PO と見直す。理由が分からなければ PO に報告する。
- verify で届いた文に会員 ID か契約者名の文字があった → 直ちに Opus が PR の revert をマージし（§9）、PO に報告する（試験の文字は架空の値なので害は無いが、取り出しの作りが壊れている）。

## 9. 戻し方

- repo: この PR の revert を main にマージする（deploy.yml が動き、タスクと指標が外れる。secret の 3 つと .env の 3 行は残っても使われない）。
- prod2: `rollback-bin3.sh`（控えのルールを戻す）。無制限鍵を使うので、同意票を受けて Opus が実行する。
- Gmail の転送のフィルタは PO が消す（残しても受け箱に溜まるだけ）。
- 戻すと、さくらのメールが Discord に届かない状態に戻る（10/22 以前と同じ）。便1・便2 は残る。

## 10. PR

- 作業場所:
  - このカードの PR が main にマージされたことを確かめる: `gh pr list --state merged --head release/outage-bin3-card --limit 1 --json number,state`。合格は 1 件で state が MERGED。`[]` なら作業を始めずに BLOCKED:。
  - 便2 の実装が入っていることを確かめる: `gh pr list --state merged --head release/outage-recovery-check --limit 1 --json number,state` が 1 件で MERGED。`[]` なら BLOCKED:。
  - その後 `cd /Users/tanizawashingo/salesanchor && git fetch origin && bash scripts/new-worktree.sh release/ops-mail-notifier --claude`（origin/main 起点）を実行する。
  - 出力はパイプに通さない。最後に「Input must be provided」と出て exit 1 になることがあるが、作業場所の作成とは無関係（2026-10-22 実測）。`cannot lock ref` で失敗したら、同じコマンドを 1 回だけやり直す。
  - 作成後に `ls -1d /Users/tanizawashingo/worktrees/salesanchor/release-ops-mail-notifier` と `git worktree list` の両方で実在を確かめる。`ls docs/handoff/outage-recovery-watch/card-bin3.md` でこのカードの実在を確かめる。
  - 変更の前に `python3 monitoring/scripts/check_alert_rules.py` を実行し、`OK: Prometheus 32 rules, Loki 6 rules, runbook 38 sections` であることを確かめる（違えば BLOCKED:。§7 の期待値の前提）。
  - 以後の作業はすべてその作業場所に `cd` してから行う。
- push は `git push -u origin release/ops-mail-notifier`。commit の後に `git log -1 --oneline`、push の後に `git log origin/release/ops-mail-notifier -1 --oneline` で実在を確かめる。
- PR は `scripts/gh-pr-create-safe.sh` で作る。
  - 先に Write ツールで本文ファイル `/tmp/CC報告ファイル/outage-bin3/pr-body.md` を作り、`--body-file` で渡す（executor-checklist.md §0）。
  - 作成後に `gh pr list --head release/ops-mail-notifier --limit 1 --json number,isDraft` で 1 件・isDraft が false を確かめる。
- 作成前に `gh auth status` で `shingo-cc` 名義であることを確かめる。
- PR は ready で作る（`--draft` を付けない）。base は main。マージは Opus の審査と GO 記録の後に限る（担当はマージしない）。
- 本文は PR テンプレートに沿う。`### 標準ワークフロー確認` には次を書く:
  - recon・設計・このカード（docs/handoff/outage-recovery-watch/ の 3 本）
  - `対象ADR:` は ADR-1012, ADR-136
  - `設計仕様書（あるべき姿）:` は docs/specs/ai-ops-247/README.md
  - `区分:` は A（新機能。PO 承認は設計の PO 承認 2026-10-22「1」）
  - `Opus 審査記録:` は「コード審査はこれから」
  - `触るファイル:` と `削除するファイル:` は 1 行・カンマ区切り・バッククォートなし。`削除するファイル:` には、行を書き換えた既存ファイルを全部書く（`validate-pr-body.sh` の規則）
- 本文に「危険 PR（deploy.yml）。GO 記録はマージの前に Opus が書く」「§8 の本番配置はマージの後に Opus が同意票を受けて行う。台本はリポジトリの外にあり commit しない」を書く。
- 本文に IP・受け箱のアドレス・webhook・鍵のパス・利用者名・認証ファイルの中身・メールアドレスを書かない。実在しないパスをバッククォートで書かない。
- 作成前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し、exit 0 を確かめる（2 分以上かかる。Bash の timeout は 240000 以下にする）。

## 11. 報告

- 完了報告の本文に: 冒頭の受領文／§5-1〜5-12 の出力／PR の URL／生出力のパス／判断を要した点（事実のみ）
- 停止したときは: 停止した手順番号／最後に実行したコマンド／停止した理由の原文
- 1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか

## 12. 委任の定型

- sleep しない（待ちは Opus が行う。例外は §4-13 の台本の中の待ちだけ。台本は担当が実行せず、Opus が同意票を受けて実行する。担当のコマンドでは sleep しない）
- ファイルの作成と編集は Write/Edit ツールで行う（ヒアドキュメントで書かない）
- PR を作る前に `scripts/dev/validate-pr-body.sh` で exit 0 を確かめる
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える

## 13. 報告欄（担当が追記）

（未記入）

END OF CARD
