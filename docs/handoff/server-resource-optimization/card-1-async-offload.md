# 実装カード ①：async の処理の中で、同期処理がイベントループを塞いでいる箇所を、スレッドに逃がす

- 設計：`docs/handoff/server-resource-optimization/design-20261001.md` §2・§4 便①（PR #3909）
- 調査の根拠：Sonnet の静的調査（origin/main、2026-10-01）。すべて file:line で確認済み。
- 目的：backend を workers=1（ADR-081）に戻す前提として、1つの要求の待ちが、ほかの全要求と SSE を止めないようにする。
- 変更の種類：backend のコードとテストのみ。migrations、compose、Dockerfile、deploy.yml、フロントエンドは変更しない。

## 書き方の規則（周りのコードに合わせる）
- `backend/app/routers/invoices.py` の中：既に import されている `run_in_threadpool` を使う（お手本は同じファイルの `:880`）。
- `backend/app/services/tcg_distribution_svc.py` の中：同じファイルの書き方（`loop.run_in_executor(None, ...)`。お手本は `:163-165`）に合わせる。
- それ以外のファイル：`asyncio.to_thread(...)` を使う（既存の使用例は `backend/app/routers/shipping.py:340`）。`import asyncio` が無いファイルには追加する。
- Google API の `.execute()`：リクエストの組み立て（`service.events().list(...)`）は今のまま同期で行い、`.execute` だけをスレッドに渡す。
  例：`result = await asyncio.to_thread(service.events().list(...).execute)`
- 例外の処理（try/except とメッセージ）は、今の形をそのまま保つ。ログの文言も変えない。

## 変更の一覧（変更前 → 変更後）
| # | 箇所 | 変更前 | 変更後 |
|---|---|---|---|
| a | `backend/app/routers/contact.py:91` | `_send_notification(data)` | `await asyncio.to_thread(_send_notification, data)` |
| b | `backend/app/routers/purchase_orders.py:421-428` | `result = send_po_email_sync(to_addr=..., ...)` | `result = await asyncio.to_thread(send_po_email_sync, to_addr=..., ...)`（キーワード引数はそのまま） |
| c | `backend/app/services/po_renderer.py:479` | `pdf = render_po_pdf(data)` | `pdf = await asyncio.to_thread(render_po_pdf, data)` |
| d | `backend/app/routers/invoices.py:835` | `pdf_bytes = render_invoice_pdf(invoice_data, tenant_profile)` | `pdf_bytes = await run_in_threadpool(render_invoice_pdf, invoice_data, tenant_profile)` |
| e1 | `backend/app/services/google_calendar.py:351-361`（get_events） | `(service.events().list(...).execute())` | `await asyncio.to_thread(service.events().list(...).execute)` |
| e2 | 同 `:375-378`（create_event） | `.insert(...).execute()` | `await asyncio.to_thread(service.events().insert(...).execute)` |
| e3 | 同 `:390-393`（update_event） | `.patch(...).execute()` | 同様 |
| e4 | 同 `:405`（delete_event） | `.delete(...).execute()` | 同様 |
| e5 | 同 `:191`（exchange_code） | `flow.fetch_token(code=code)` | `await asyncio.to_thread(flow.fetch_token, code=code)` |
| e6 | 同 `:263`（_refresh_if_needed） | `creds.refresh(Request())` | `await asyncio.to_thread(creds.refresh, Request())` |
| f1 | `backend/app/services/google_drive_oauth.py:386-395`（upload_pdf） | `service.files().create(...).execute()` | `await asyncio.to_thread(service.files().create(...).execute)` |
| f2 | 同 `:223`（exchange_code） | `flow.fetch_token(code=code)` | `await asyncio.to_thread(flow.fetch_token, code=code)` |
| f3 | 同 `:243` | `"account_email": _fetch_account_email(creds),` | dict を作る前に `account_email = await asyncio.to_thread(_fetch_account_email, creds)` とし、dict では `"account_email": account_email` にする |
| f4 | 同 `:296`（_refresh_if_needed） | `creds.refresh(Request())` | `await asyncio.to_thread(creds.refresh, Request())` |
| g1 | `backend/app/services/google_webhook.py:75-83`（register_webhook） | `service.events().watch(...).execute()` | `await asyncio.to_thread(service.events().watch(...).execute)` |
| g2 | 同 `:141-143`（stop_webhook） | `service.channels().stop(...).execute()` | 同様 |
| g3 | 同 `:227-232`（handle_webhook_notification） | `service.events().list(...).execute()` | 同様 |
| h | `backend/app/services/tcg_distribution_svc.py:791-792`（run_distribution） | `creds = Credentials.from_service_account_file(key_file, scopes=_SCOPES)` と `gc = _build_gspread_client()` | `loop = asyncio.get_event_loop()` を try の中に置き、`creds = await loop.run_in_executor(None, lambda: Credentials.from_service_account_file(key_file, scopes=_SCOPES))` と `gc = await loop.run_in_executor(None, _build_gspread_client)` にする。`:808` の `loop = ...` は、そのまま残してよい |
| i | `backend/app/routers/leads.py:2415-2416` | `_abs_path.parent.mkdir(parents=True, exist_ok=True)` と `_abs_path.write_bytes(file_bytes)` | `await asyncio.to_thread(_abs_path.parent.mkdir, parents=True, exist_ok=True)` と `await asyncio.to_thread(_abs_path.write_bytes, file_bytes)` |

## 触らない範囲（明示）
- `backend/app/services/email_sender.py:70`：呼び出し元は Celery の同期タスク（`backend/app/tasks/email_tasks.py:46`）だけ。async の経路ではない。
- `build("calendar"|"drive", ...)`（`backend/app/services/google_calendar.py:322`、`backend/app/services/google_drive_oauth.py:201,360`）：通信が発生するかを確認できていないため、このカードでは触らない。
- `backend/app/services/tcg_line_import_svc.py:539,576` のパース処理：CPU の処理時間をまだ測っていないため、対象外。
- `backend/Dockerfile`（workers の数）、`docker-compose.yml`（上限）：便②と③で扱う。
- 関数の引数と戻り値、例外の種類とメッセージ、ログは変えない。

## テスト（TDD：先に赤を確認する）
- 新しいファイル：`backend/tests/test_event_loop_nonblocking.py`
- 方式：重い処理を `time.sleep(0.3)` をする関数に差し替える。対象のコルーチンと「0.01秒ごとに数を数えるコルーチン」を `asyncio.gather` で同時に走らせる。数えた回数が 10 以上なら合格（ループが塞がれていない）。
  - 修正前は 0〜1 回になり、赤になることを確認する。
- 必須（関数単位でモックしやすいもの）
  - a：`submit_contact`（`_send_notification` を差し替える）
  - c：`render_po_pdf_for`（`gather_po_render_data` を AsyncMock に、`render_po_pdf` を sleep に差し替える）
  - e1：`get_events`（`_get_service` を AsyncMock にし、`get_calendar_id` も差し替える。`execute` を sleep に差し替える）
  - f1：`upload_pdf`（`_get_drive_service` を差し替え、`execute` を sleep に差し替える）
  - g3：`handle_webhook_notification`。DB のモックが30行を超える場合は除外し、報告で「未テスト」と明記する。
- 残りの b、d、e2〜e6、f2〜f4、g1〜g2、h、i：既存のテスト（`backend/tests/test_google_calendar.py`、`test_google_drive_oauth.py`、`test_tcg_distribution.py`、`test_message_image_send.py`、`test_invoices.py`、`test_po_mailer.py`、`test_po_renderer.py`、`test_paypal_invoicing.py`、`test_integrations.py`）がすべて緑であることで確認する。
  - 新しい非ブロッキングのテストを、モック30行以内で書けるものは追加してよい。

## 受入条件（○×）
| 基準 | 検証方法 |
|---|---|
| 上の表の全箇所が、スレッドに逃がす書き方になっている | `git diff origin/main...HEAD -- backend/app` を目で確認し、表の行ごとに○×をつける |
| 新しいテストが、修正前に赤、修正後に緑になる | 修正前のテストの実行結果（失敗）と、修正後の実行結果（成功）の生出力 |
| backend の既存テストが全件緑 | CI の Backend Tests が success |
| lint | CI の ruff と bandit が success |
| 範囲外のファイルを触っていない | `git diff --name-only origin/main...HEAD` が、上の対象ファイル、新しいテスト、このカードのファイルだけ |

## 戻し方
- PR を revert する（コードだけの変更で、データには触れない）。

## 本番での確認（デプロイの後）
- `/api/health` が 200 を返す。
- backend のログに、新しい例外（`RuntimeError` の増加）が出ていない。デプロイの前後1時間を Loki で比べる。
- 該当機能（カレンダー同期、PDF のダウンロード、問い合わせ）でエラーが増えていない。prod2 の Prometheus で、`http_requests_total{status=~"5.."}` をデプロイの前後で比べる。
