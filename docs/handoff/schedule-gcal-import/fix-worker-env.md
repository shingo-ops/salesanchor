# ADR-1059 便2 の直し: 取り込み係（celery-worker）に合鍵と Google の名札を渡す

状態: 設計案（Opus 作成・自己審査 APPROVE・2026-11-04）。実装は Sonnet に委任する。
親設計: `docs/handoff/schedule-gcal-import/design.md`（ADR-1059 便2・PR #5083 で本番反映済み）

## 1. 目的と成功条件（KGI）

PO が予定の画面を開くと、PO 本人の Google カレンダーの予定が出る（便2 の K1 と同じ）。

| 基準 | 検証方法 |
|---|---|
| G1 本番の celery-worker の中で `METADATA_FERNET_KEY`・`GOOGLE_CALENDAR_CLIENT_ID`・`GOOGLE_CALENDAR_CLIENT_SECRET`・`GOOGLE_CALENDAR_REDIRECT_URI` が 4 つとも「入っている」 | 反映後、PO の `!` で読むだけの台本（値は出さず set/EMPTY だけ）。期待 4/4 set |
| G2 反映後最初の 15 分おきの実行で、記録に「未接続のため…スキップ」が 0 行 | 同じ台本で celery-worker のログを読む |
| G3 本番の `google_webhook_subscriptions` が 1 行（tenant 4・channel_token_hash あり） | reader 鍵の道 `ai_ro.public__google_webhook_subscriptions` |
| G4 tenant_004 の `calendar_events` に `source='google'` の行が 1 行以上 | reader 鍵の道（件数のみ） |
| G5 PO が予定の画面で Google の予定を見られる | PO 目視（○×） |
| G6 同じ種類の漏れ（取り込み係が読む設定が compose で渡っていない）を CI で止める | 追加する試験が、4 行のどれかを消すと落ちることを担当が実際に確かめる |

## 2. 現在地（観測事実。推測なし）

本番の事実は PO の `!` で読むだけの台本を 2 回実行して取った（値は出していない）。生出力:
`/private/tmp/claude-501/-Users-tanizawashingo-salesanchor/a31998c3-b50b-4f1f-9119-370c58e82a8b/scratchpad/gcal-logs.txt`（1 回目・68 行）、同 `gcal-facts2.txt`（2 回目・73 行・末尾 `== END ==` まで動いた）。

- F1 celery-worker のログ（UTC。2026-11-03 19:51Z〜22:51Z の 13 回すべて）: `Google Calendar 未接続のため Webhook 登録スキップ (tenant=4): 環境変数 METADATA_FERNET_KEY が設定されていません。` と `… 取り込みスキップ (tenant=4): …` が毎回出て、作業は `succeeded … {'synced': 1}` で終わっている。ERROR／Traceback は 0 行（gcal-facts2.txt §8。ただし 00:42Z の入れ替え後の分のみ）。
- F2 本番の celery-worker・celery-beat の中では 4 つとも EMPTY（gcal-facts2.txt §6）。
- F3 本番の backend（`astro-webapp-backend-1`）の中では 4 つとも set（同 §6b）。`API_BASE_URL` は backend も worker も EMPTY で、コードの既定 `https://api.salesanchor.jp` が使われる（`backend/app/services/google_webhook.py:54`）。
- F4 本番の `.env` には 4 つの名前がある（同 §5。名前だけ確認・値は見ていない）。値は `.github/workflows/deploy.yml:348,352-354` が GitHub Secrets から書く。
- F5 backend だけ渡っている理由: backend は `scripts/blue-green-cutover.sh:84-85` が `.env` の全部の名前を `--env` で渡して `docker run` する。celery-worker は `docker-compose.yml:234-` の `environment:` に並べた名前だけを受け取り、そこに 4 つが無い（`docker-compose.yml` を `GOOGLE|CALENDAR` で検索して該当 0・`git log -S GOOGLE_CALENDAR_CLIENT_ID -- docker-compose.yml` も 0 件）。
- F6 取り込みの経路で 4 つが要る場所: 復号は `backend/app/services/encryption.py:57`（`METADATA_FERNET_KEY`）。Google の資格情報は `backend/app/services/google_calendar.py:234-235`（`_build_credentials` が毎回 `_get_client_id()`・`_get_client_secret()` を呼ぶ）。`GOOGLE_CALENDAR_REDIRECT_URI` は接続の手順（`google_calendar.py:135,139,190,194`）だけで使うが、同じモジュールの設定として揃えて渡す。
- F7 本番の DB（reader 鍵の道・AUDIT 記録あり・2026-11-03 12:43Z〜13:00Z）: `tenant_google_calendar_config` は 1 行（tenant 4・bidirectional・持ち主あり）。`google_webhook_subscriptions` は 0 行。tenant_004 の `calendar_events` は `source='app'` 9 行だけで `google` は 0 行。
- F8 失敗が「成功」と記録された理由: `backend/app/tasks/google_calendar_sync.py:62-64` は `register_webhook` が None、`sync_tenant_from_google` が `{"skipped": "not_connected"}` を返しても `synced += 1` する。ログは INFO。

原因: 便2 の設計で、取り込みを celery-worker で動かすのに、worker へ渡す設定を確かめるのを入れ忘れた。

## 3. 変更（この便は 1 つだけ）

`docker-compose.yml` の `celery-worker:` の `environment:` の末尾（`- MAIL_FROM=${MAIL_FROM:-}` の次、現 288 行の次）に足す:

```yaml
      # ADR-1059 便2 の直し: Google の予定の取り込み（app.tasks.google_calendar_sync）が
      # 接続の鍵の復号と Google の資格情報に使う。backend は blue-green-cutover.sh が
      # .env の全部の名前を渡すが、worker はここに並べた名前しか受け取らない。
      # この 4 行が無いと「未接続のため取り込みスキップ」で毎回何もしない（2026-11-04 本番で確認）。
      - METADATA_FERNET_KEY=${METADATA_FERNET_KEY:-}
      - GOOGLE_CALENDAR_CLIENT_ID=${GOOGLE_CALENDAR_CLIENT_ID:-}
      - GOOGLE_CALENDAR_CLIENT_SECRET=${GOOGLE_CALENDAR_CLIENT_SECRET:-}
      - GOOGLE_CALENDAR_REDIRECT_URI=${GOOGLE_CALENDAR_REDIRECT_URI:-}
```

- celery-beat には足さない（beat は時刻に合図を出すだけで、取り込みの処理は worker で動く）。
- 秘密の値は変えない。新しい鍵も作らない。既に `.env` にある値を worker にも渡すだけ。

### 3-1. 同じ漏れを止める試験（G6）

`backend/tests/test_compose_worker_env.py` を新しく作る:
- リポジトリ直下の `docker-compose.yml` を読み（`yaml.safe_load`。PyYAML が backend の依存に無ければ、行を読んで `services.celery-worker.environment` の `- NAME=` を拾う素朴な読み方でよい。どちらにしたか報告に書く）、`celery-worker` の environment の名前の集合を作る。
- `REQUIRED = {"METADATA_FERNET_KEY", "GOOGLE_CALENDAR_CLIENT_ID", "GOOGLE_CALENDAR_CLIENT_SECRET", "GOOGLE_CALENDAR_REDIRECT_URI"}` がすべて含まれることを確かめる。
- 加えて、`backend/app/services/google_calendar.py` の本文から `os.getenv("NAME"` の NAME を正規表現で全部拾い、それらがすべて worker の environment にあることを確かめる（将来ここに設定が増えたときの漏れを止める）。
- 試験で `docker-compose.yml` が見つからない環境（CI の作業場所の位置）では、`pathlib.Path(__file__).resolve().parents[2] / "docker-compose.yml"` を使う。見つからなければ skip ではなく fail にする。

### 触らない範囲

- `backend/app/tasks/google_calendar_sync.py` の「スキップも成功と数える」（F8）は**この便では直さない**（変更は一度に 1 つ）。次の便で、スキップを数えて WARNING を出すように直す（§6）。
- `scripts/blue-green-cutover.sh`・`.github/workflows/deploy.yml`・secrets・backend の設定は変えない。

## 4. 弊害と対処

- worker が暗号の鍵を持つ範囲が広がる。worker は既に DB の接続情報・Gemini・メールのパスワードを持つ同じ信頼の入れ物で、backend と同じ鍵を持つだけ。新しい外部の入口は増えない。
- 反映後、最初の実行で token の期限切れ（`token_expiry` 2026-11-03 03:32Z）を refresh_token で更新する。更新に失敗した場合（refresh_token が無効）は G2 が「未接続」以外の理由で落ちる。その時は止めて PO に「Google のつなぎ直し」を頼む。

## 5. 戻し方と測り方

- 戻し方: この PR を revert する PR をマージして反映する（worker が 4 つを受け取らない元の状態に戻る。DB は変えていない）。
- 測り方: 反映の終わりから 15 分以上たってから G1〜G4 を確かめる。基準値は §2 F2・F7（4 つとも EMPTY、webhook 0 行、google 0 行）。

## 6. 次の便（この便が本番で G1〜G5 を満たした後）

- `_run_all` が `{"skipped": …}` を数え、モードが取り込みなのに not_connected のときは WARNING を出し、作業の戻り値に会社ごとの結果を入れる（F8 の直し。今回、失敗に気づけなかった原因）。

## 7. 外部事例

不要。Docker Compose の `environment:` に書いた名前だけがコンテナに渡る、という仕組みの範囲の不具合で、本番の実測（§2）で原因が特定できているため。

## 8. Architect 自己審査（同一 AI による。独立した第二者の審査ではない）

- 既存仕様との整合: ADR-1059 便2 の設計（design.md）の動きは変えない。渡し忘れを足すだけ。
- 根拠の十分さ: 本番の set/EMPTY・ログの文面・コードの行で、原因が 1 つに特定できている。
- 受入条件: G1〜G4 は数で、G5 は ○×、G6 は試験の結果で判定できる。
- 実装範囲: `docker-compose.yml` の 1 か所と試験 1 つ。
- 判定: APPROVE。未解決: refresh_token が有効かは反映後にしか分からない（§4 で止まる条件を決めた）。
