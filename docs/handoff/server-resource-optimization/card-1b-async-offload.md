# 実装カード ①b：LINE 取込のパースとログイン確認を、イベントループから逃がす

- 設計：設計 PR #3909 の design-20261001.md（server-resource-optimization フォルダ）§4 便①の追加分。前の便 ① は PR #3912（本番反映済み、2026-10-02）。
- このカードは recon（現在地の確認）を兼ねる：`docs/handoff/server-resource-optimization/card-1b-async-offload.md`
- 対象の ADR：`docs/adr/ADR-081-monitoring-vps-final-operational-design.md`（ADR-081-monitoring-vps-final-operational-design。backend は workers=1 を標準とする）
- PO の決定（2026-10-02、AskUserQuestion の回答）：「先に直す（推奨）」。backend を 1 ワーカーにする前に、LINE 取込の、他を止める処理を直す。
- 調査の根拠（origin/main、Sonnet の静的調査と本番の Prometheus）
  - `/api/v1/tcg/line-devices/import` は 7日で 36,565 件、平均 0.99 秒。
  - パースは、async の関数の中で同期のまま呼ばれている（下の表）。
  - `firebase_admin.auth.verify_id_token` は、公開証明書をネットワークで取得することがある。Context7 `/firebase/firebase-admin-python` の errors.md に `CertificateFetchError`（「Failed to fetch certificates」）の記述があることで確認した。
- 重なりの確認：作業中の LINE 解析の PR（open の release/line-* 9件、#3894・#3901・#3903 は merged）は、どれも下の3ファイルを変更していない。#3874 が変更するのは `backend/app/services/tcg_line_system_events.py` で、このカードではそのファイルに触らない。

## 書き方の規則
- `asyncio.to_thread(...)` を使う（前の便 ① と同じ書き方。既存の例は `backend/app/routers/contact.py:92`）。`import asyncio` が無いファイルには追加する。
- 呼び出される側の関数（`parse_android_export`、`parse_line_export`、`match_system_event`、`verify_id_token`）の中身は変えない。呼び出す側だけを変える。
- 例外の種類、ログ、戻り値は変えない。

## 変更の一覧（変更前 → 変更後）
| # | 箇所 | 変更前 | 変更後 |
|---|---|---|---|
| p1 | `backend/app/services/tcg_line_import_svc.py:539` | `android_messages = parse_android_export(export_text) if source_format == "android" else None` | `android_messages = (await asyncio.to_thread(parse_android_export, export_text)) if source_format == "android" else None` |
| p2 | 同 `:576` | `all_messages = android_messages if android_messages is not None else parse_line_export(export_text, supplier_names)` | `all_messages = android_messages if android_messages is not None else await asyncio.to_thread(parse_line_export, export_text, supplier_names)` |
| p3 | 同 `:579-588`（`match_system_event` を全メッセージに当てる内包表記） | async の関数の中の内包表記 | 内包表記を**一字も変えずに**、同じファイルのモジュール関数 `_mark_system_events(all_messages)`（同期の def。戻り値は今の内包表記の結果と同じ list）に移す。呼び出し側は `<元の代入先> = await asyncio.to_thread(_mark_system_events, all_messages)` にする。内包表記が all_messages 以外の局所変数を参照している場合は、それも引数で渡す |
| a1 | `backend/app/auth/dependencies.py:142` | `firebase_auth.verify_id_token(token)`（代入先は今のまま） | `await asyncio.to_thread(firebase_auth.verify_id_token, token)` |

## 触らない範囲（明示）
- `_enqueue_extraction` の `.delay()` のループ（`backend/app/services/tcg_line_import_svc.py:702-703`、`backend/app/routers/tcg_line_import.py:642-643`）と、`backend/app/routers/buyback_prices.py:147` の `.delay()`。
  - 理由：Celery の公式ドキュメント（Context7 `/websites/celeryq_dev_en_stable`）で、複数のスレッドから同時に publish してよいかを確認できなかったため。1件あたりの時間も、まだ測っていない。便②の後の計測項目として残す。
- `backend/app/services/tcg_line_import_svc.py:646-655` の二重ループ：仕入元が未解決のときだけ動く。規模を測っていないため、今回は対象外。
- `backend/app/auth/dependencies.py:88` の `_init_firebase`：プロセスごとに1回だけ。
- `backend/app/services/tcg_line_android_parser.py` と `backend/app/services/tcg_line_system_events.py`：中身は変えない（LINE 解析の担当範囲。#3874 と重なる）。
- super_admin_status_master の preview_match の正規表現と、product_matcher の二重ループ：スーパー管理者だけが使い、頻度が低い。今回は対象外。
- `backend/Dockerfile` の workers の数：便②で扱う。

## テスト（TDD：先に赤を確認する）
- 既存の `backend/tests/test_event_loop_nonblocking.py` に追加する（同じ方式：重い処理を `time.sleep(0.3)` に差し替え、ティックの数が 10 以上なら合格）。
- 必須
  - p1：`import_line_export(..., source_format="android")`。`parse_android_export` を sleep に差し替える。db のモックは `backend/tests/test_tcg_line_import.py:657-667` の書き方に合わせる。sleep の後は処理が続かなくてよい（例外で抜けてもよい）。判定するのはティックの数だけ。
  - a1：`get_current_user`。Redis のキャッシュミスの経路で、`firebase_auth.verify_id_token` を sleep に差し替える。モックが30行を超える場合は除外し、報告で「未テスト」と明記する。
- p2 と p3 は、既存の `backend/tests/test_tcg_line_import.py` と `backend/tests/test_tcg_line_android_api.py` が緑であることで確認する（p3 は動きが変わらないことの確認）。

## 受入条件（○×）
| 基準 | 検証方法 |
|---|---|
| p1、p2、p3、a1 が表のとおりに変わっている | `git diff origin/main...HEAD -- backend/app` を見て、行ごとに○×をつける |
| 新しいテストが、修正前に赤、修正後に緑 | 前の便と同じく、prod2 の使い捨てのコンテナで、コミット1とHEADの両方を実行する |
| backend の既存テストが全件緑 | CI の Backend Tests が success |
| 範囲外のファイルを触っていない | `git diff --name-only origin/main...HEAD` が、3つの対象ファイル、テスト、カード、台帳だけ |

## 外部・過去事例の参照と我々への応用
- 過去事例（社内）：便 ①（PR #3912）。同じ書き方で9か所を直し、本番反映の前後で 5xx は 0 件、新しい種類のエラーも無かった（2026-10-02 の確認）。
- 公式の仕様：Firebase Admin の `verify_id_token` は、証明書の取得に失敗したときに `CertificateFetchError` を出す。つまり、ネットワークの I/O を含みうる。
- 外部の一般事例は使わない。効果は、新しいテストで直接確かめる。

## 維持の仕組み
- 守り手: CI の Backend Tests（`backend/tests/test_event_loop_nonblocking.py`）。

## 戻し方
- PR を revert する（コードだけの変更）。

## 本番での確認（デプロイの後）
- `/api/health` が 200 を返す。
- Loki で、デプロイの前後1時間の backend の ERROR/Traceback の件数を比べる。
- Prometheus で、`/api/v1/tcg/line-devices/import` の 5xx と件数（取込が止まっていないこと）をデプロイの前後で比べる。
- ログインできる（`/api/v1/me/permissions` の 200 の件数が、デプロイの後も続いている）。
