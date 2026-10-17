# 実装カード 便2: 自動セッション用の口 3 つ・再解析と照合

> 親: [design.md](./design.md) §4-2・§6（O6・O7）／ADR: [ADR-1025](../../adr/ADR-1025-analysis-error-report-autofix.md)／KGI: [kgi.md](../../specs/analysis-error-report/kgi.md)（照合の部分）／前の便: [card-bin1.md](./card-bin1.md)（#4465 本番反映済 2026-10-17）
> 区分: ADR-1015 の A。`.github/workflows/deploy.yml` を含むため、マージ前に ADR-136 の GO 手順が要る（GO は ADR-1003 で Opus に委任）。migration は無い。
> 状態: カード作成済み・PO 実装承認済み（2026-10-17「y」。「設計への補足」1 の v102 限定を含む）。
> 調査: /tmp/CC報告ファイル/bin2-recon/recon.md（origin/main 1e7a68980・担当 Sonnet の読み取り）

## 設計への補足（Opus 判断・設計の意図は変えない）
1. **再解析は v102 の行だけ**。理由: `reanalyze_v102_job`（backend/app/tasks/tcg_extraction.py:734-760）は prompt_version が `v102:` 以外なら skipped を返す。v6 系を 1 ジョブ再解析する経路は super admin ログインの API だけ（routers/tcg_product_master.py:344-389）で、元に戻せない（同 :357-383）。本番の近似集計では在庫表に出る行は v102 だけ（recon §12 (C)＋48 時間条件で v102 996 行・それ以外 0 行）。v102 以外の報告の再解析は 409 で断り、自動セッションは PO 宛てで止まる。
2. **照合は Celery タスクの中で同期で行う**。再解析が同期 Session（tcg_extraction.py:838-854 の型）なので、照合も同期で書く。operator フラグは `set_config('app.is_operator','true', true)`（トランザクション内だけ有効。commit で自動的に戻る）で立てる。tasks/ 配下に operator フラグの前例は無い（recon §2）ため、この書き方をカードで固定する。
3. **「マスタに無い」商品の照合**: 報告後に登録された商品に結び付いたか、または商品が未確定（product_id が NULL）なら一致とする。登録の後で再解析した結果を正しく○にするため。

## 冒頭（必読）
- 実装役は `./scripts/dev/executor-preflight.sh || exit 1` を最初に実行する。作業場所は既存の `~/worktrees/salesanchor/release-analysis-error-report-bin2`（origin/main 1e7a68980 起点）。Bash は毎回この場所へ絶対パスで cd する。
- このカードに書いていないことはしない。迷ったら止まって Opus に `NEEDS_DECISION:` で返す。
- 本番 DB・secrets・GitHub の設定には触らない。commit・push は Opus が行う。

## 実物点検（最初に。推測で進めない）
1. `backend/app/routers/ops.py:76-132`（compare_digest・require_ops_reader・鍵だけを受ける型 :120-132）を読む。
2. `backend/app/tasks/tcg_extraction.py:734-760`（reanalyze_v102_job の戻り値の形）、`:838-854`（タスクの書き方）、`:903-922`（except 側の None 代入と `__all__`）を読む。
3. `public.products` に作成日時の列（`created_at` など）があるかを migrations で確かめる（`git grep -n "CREATE TABLE.*products\b\|ALTER TABLE.*products.*ADD" migrations/`）。無ければ止まる。
4. `backend/app/realtime/topics.py` で、既存の再解析ルート `POST /api/v1/tcg/extraction-jobs/{...}/reanalyze` がどちらの表に、どの値で入っているかを確かめる。
5. `.github/workflows/deploy.yml:309-310`・`:355-356`（OPS_API_TOKEN の受け渡し）、`docker-compose.yml:106`（便1の webhook・backend）、`:137-139`（ops 鍵）、`:213-276`（celery-worker の environment）を確かめる。

## 項目 1: 鍵の検査
### 変更
- 新規 `backend/app/routers/ops_error_reports.py` に依存関数 `require_error_report_agent` を置く。
### 中身
- `Authorization: Bearer <鍵>` を `secrets.compare_digest` で環境変数 `ERROR_REPORT_AGENT_TOKEN` と比べる（ops.py:76-82 と同じ比べ方）。
- 鍵が未設定または空なら、全部 401（全員拒否）。違う鍵も 401。super admin のログインでは通さない（require_ops_reader と違う点）。
### 触らない範囲
- ops.py の既存の関数と OPS_API_TOKEN は変えない。

## 項目 2: 口 3 つ（prefix `/api/v1/ops/error-reports`、main.py に include_router を 1 行）
| 口 | 中身 |
|---|---|
| GET `/{report_code}` | 報告（report_code・extraction_item_id・extraction_job_id・status・reported_at）、fields（field_name・system_value・expected_value・expected_missing_product）、その行の今の 7 項目（便1の `_SYSTEM_VALUES_SQL` と `_SYSTEM_COLUMN` を使い回す。新しい SQL を書かない）、ジョブの prompt_version、events（at・actor・kind・payload を at 順）。無ければ 404 |
| POST `/{report_code}/events` | 本文 `{kind: "cause" or "action", actor: 1〜100 文字, payload: object}`。payload を JSON にして 8192 バイトを超えたら 422（表の CHECK と同じ上限）。status が `open` なら同じトランザクションで `working` にする。resolved・cancelled の報告には 409。201 で event の id を返す |
| POST `/{report_code}/reanalyze` | status が resolved・cancelled なら 409。ジョブの prompt_version が `v102:` で始まらなければ 409（detail `not_v102`）。条件を満たせば events に `reanalyzed`（payload `{"task_id": ...}`）を記録して、項目 3 のタスクを積む。202 で task_id を返す |
- 書き込みは便1と同じく operator フラグを立てた 1 トランザクション（便1 svc:159-184 の型）。
- 新規 `backend/app/schemas/analysis_error_report_ops.py` にこの 3 つの入出力の型を置く。
### 触らない範囲
- 便1の POST `/tcg/items/{id}/error-reports` と、その検査は変えない。

## 項目 3: 再解析と照合のタスク
### 変更
- `backend/app/tasks/tcg_extraction.py` に `@celery_app.task(name="tcg.error_report_reanalyze_and_verify", bind=True, max_retries=0, time_limit=330, soft_time_limit=300)` を足す（:838-854 の型。同じファイルなので celery の include は変えない）。`:903-922` の except 側と `__all__` にも足す。
- 新規 `backend/app/services/analysis_error_report_verify.py`（同期）に照合を置く。
### 流れ
1. `reanalyze_v102_job(extraction_job_id)` を呼ぶ。戻り値が成功でなければ（skipped・失敗・例外）、照合をせず events に `verified`（payload `{"result": "reanalyze_failed", "detail": ...}`）、status を `unresolved` にする。
2. 成功なら、その行の今の値を読み、fields の項目ごとに比べる:
   | 項目 | 一致の条件 |
   |---|---|
   | product_id | 通常は `int(expected_value) == product_id`。expected_missing_product が true なら、product_id が NULL か、その商品の作成日時が報告の reported_at より後 |
   | quantity・price | `Decimal(str(expected_value)) == 値`（NUMERIC(14,2)。100 と 100.00 は一致。値が NULL なら不一致） |
   | unit・condition・status | 文字列の完全一致 |
   | note | note_ja を半角カンマで分け、前後の空白を除いた空でない語の集合と、expected_value の集合が等しい（tcg_analyzer_svc.py:1193-1196 の区切り。順番は問わない。どちらも空なら一致） |
3. events に `verified`（payload `{"result": "resolved" or "unresolved", "fields": [{"field", "expected", "actual", "match"}]}`）を記録し、全部一致で status を `resolved`、1 つでも不一致で `unresolved` にする。operator フラグは設計への補足 2 の書き方。
4. commit の後に、Discord へ照合結果を送る（項目 4）。送れなくても status と events はそのまま。
### 触らない範囲
- `reanalyze_v102_job` と既存の再解析タスクは変えない。

## 項目 4: Discord に照合結果
### 変更
- `backend/app/services/discord_notifier.py` に同期の `notify_analysis_error_report_verified(report_code, result, fields)` を足す（便1の :73-108 と同じ webhook・`?wait=true`。httpx の同期 Client）。
- 本文は「誤り報告 ER-xxxxxx 照合: 正答」または「誤り報告 ER-xxxxxx 照合: 未解決」と、項目ごとの「数量○ 価格×」だけ。値そのものは書かない（便1の本文の方針と同じ）。項目名の日本語は便1の本文で使っている対応をそのまま使う。
- 送れたら events に `notified`、失敗なら `notify_failed`（便1と同じ）。
- `docker-compose.yml` の celery-worker の environment に `ANALYSIS_ERROR_REPORT_DISCORD_WEBHOOK=${ANALYSIS_ERROR_REPORT_DISCORD_WEBHOOK:-}` を足す（backend の :106 と同じ書式）。

## 項目 5: 鍵の受け渡し
- `.github/workflows/deploy.yml`: `:310` の次に `-e '/^ERROR_REPORT_AGENT_TOKEN=/d' \`、`:356` の次に `ERROR_REPORT_AGENT_TOKEN=${{ secrets.ERROR_REPORT_AGENT_TOKEN }}`（OPS_API_TOKEN と同じ書式）。
- `docker-compose.yml`: backend の `:139` の次に `- ERROR_REPORT_AGENT_TOKEN=${ERROR_REPORT_AGENT_TOKEN:-}`。worker には渡さない（タスクは鍵を使わない）。

## 項目 6: 周りの表
- `backend/app/realtime/topics.py`: POST `/api/v1/ops/error-reports/{report_code}/events` は NO_SIGNAL_ROUTES に「誤り報告の記録のみ。画面に出る在庫データは変えない（ADR-1025 便2）」。POST `/api/v1/ops/error-reports/{report_code}/reanalyze` は、実物点検 4 で見た既存の再解析ルートと同じ表・同じ値にする。
- `frontend/api-contract/openapi.json`: CI と同じ Python 3.12・pydantic 2.10.6 で作れる環境が無ければ、生成しないで Opus に返す（便1では CI のログの差分を当てた。ローカルの pydantic 2.13 は無関係の差分を出す）。

## 項目 7: テスト（DB はモック。便1の tests/test_analysis_error_reports.py の型）
- `backend/tests/test_ops_error_reports.py`: 鍵なし 401、違う鍵 401、鍵が未設定の環境で正しそうな鍵でも 401、super admin のログインだけでは 401、無い番号 404、events の kind が cause・action 以外で 422、payload 8192 バイト超で 422、resolved の報告への events と reanalyze が 409、v102 以外の reanalyze が 409（not_v102）、正しい reanalyze で 202 とタスクが積まれる（`.delay` か `.apply_async` を patch）。
- `backend/tests/test_analysis_error_report_verify.py`（照合の関数だけ）: 数量 100 と 100.00 が一致、価格の違いが不一致、値 NULL が不一致、メモの順番違いが一致、メモの語の過不足が不一致、メモがどちらも空で一致、商品の通常一致と不一致、「マスタに無い」で NULL が一致・報告後に作られた商品が一致・報告前からある商品が不一致、再解析失敗で reanalyze_failed と unresolved。

## 止まる条件
- 実物点検の結果がこのカードと違う（特に 3 の作成日時の列が無い、4 の再解析ルートが表に無い）。
- テストが通らず、原因がこのカードの範囲の外にある。
- このカードに無いファイルを触る必要が出た。

## 受け入れ基準
| 基準 | 検証方法 |
|---|---|
| 専用の鍵だけで口 3 つが使え、鍵が未設定なら全員拒否 | API テスト（上の 401 の 4 本） |
| v102 以外の再解析は断る | API テスト（409 not_v102） |
| 照合が項目ごとの一致規則どおり | 照合テスト（上の 11 本） |
| 照合結果が status と events に残る | 照合テスト、本番では便5の試験で ai_ro から読む |
| Discord に正答・未解決と項目ごとの○×だけが届く | 本番反映と PO の secret 登録の後、便5の試験で投稿を目で見る（Opus） |
| 既存の試験が全部緑 | CI の pytest-run-internal |

## 触るファイル（全部）
backend/app/routers/ops_error_reports.py、backend/app/schemas/analysis_error_report_ops.py、backend/app/services/analysis_error_report_verify.py、backend/app/services/discord_notifier.py、backend/app/tasks/tcg_extraction.py、backend/app/main.py、backend/app/realtime/topics.py、.github/workflows/deploy.yml、docker-compose.yml、frontend/api-contract/openapi.json、backend/tests/test_ops_error_reports.py、backend/tests/test_analysis_error_report_verify.py、docs/handoff/analysis-error-report/card-bin2.md

## 戻し方
PR を revert する。表の変更は無い。鍵の secret が未登録なら口は全員拒否のまま。

## カードチェック（Opus・2026-10-17）
- 前例はすべて recon（/tmp/CC報告ファイル/bin2-recon/recon.md）の file:line 付き。正本の重複なし（今の値の読み方は便1の SQL を使い回す。報告の正本は public の表 3 つのまま）。
- 未確認（products の作成日時の列・既存の再解析ルートの表の位置）は実物点検 3・4 に置き、違えば止まる条件にした。
- 判定: APPROVE（実装可）。
