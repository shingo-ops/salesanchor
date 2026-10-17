---
mode: handoff
---
<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# recon — celery-unregistered-tasks

> この文書は何か：毎日決まった時刻に動くはずの裏方の作業のうち、一度も動いていないもの（写しシートの書き出し、件数の突き合わせ）、動いているのに成果がないもの（15 分ごとのまとめ翻訳）、そして別の作業を巻き込んで失敗させているもの（買取価格の取得）について、今どうなっているかを実物で確かめた記録です。

**仕事名**: celery-unregistered-tasks
**日付**: 2026-10-15
**対象ADR**: ADR-110（翻訳サブシステム）、ADR-141（受信翻訳の標準入口）、ADR-096（ADR-SA-02 顧客マスタ）、ADR-151、ADR-1001、ADR-157（買取相場ログ）、ADR-1012（AI保守運用24時間化。§7 U11・U13 の出どころ）
**担当**: 設計パートナー（Opus）。読み取りは Sonnet と Fable に委任し、要所の行は Opus が自分で読み直した
**測定基準**: origin/main 5b0486ad0（worktree release/celery-unregistered-tasks-design）。本番の数値は 2026-10-15 に読み取り専用で取得（生出力は /tmp/CC報告ファイル/ai-ops-u11-u13/ と /tmp/CC報告ファイル/ai-ops-u13-dup/ と /tmp/CC報告ファイル/ai-ops-celery-fix/）

凡例: 【事実】出典あり ／ 【未確認】確かめられていない

---

## 既存 ADR の検索

- `git grep -il -e tcg_mirror -e mirror -e translat -e sa02 -- docs/adr/` のヒット: ADR-039, ADR-1001, ADR-1004, ADR-110, ADR-141, ADR-143, ADR-145, ADR-151, ADR-SA-17〜19, README。
- `docs/adr/FEATURE-INDEX.md` には mirror／translat／sa02／翻訳／写し のヒットが 0 行【事実】。
- ADR-110 の本文には、15 分ごとのまとめ翻訳（バッチ）の明記がない【事実：batch／バッチ／15分／900／beat の grep で該当なし】。
- 定期作業を「登録されているか」で検査する ADR・CI は無い【事実：下記 §5】。

---

## file:line 引用表

### §1 写しシート（tcg_mirror）が一度も動いていない

| 引用先 `path:line` | 確認内容 |
|---|---|
| `backend/app/tasks/tcg_mirror.py:295` | `def run_tcg_mirror_write() -> None:` にデコレータが無い。ファイル内に celery／shared_task の import も無い（Opus 再読） |
| `backend/app/celery_app.py:155` | beat に `"tcg-mirror-daily-write"` → task 名 `app.tasks.tcg_mirror.run_tcg_mirror_write`、毎日 02:30 JST |
| `backend/app/celery_app.py:35` | include に `app.tasks.tcg_mirror` がある。モジュールは読まれるが、タスクとしては登録されない |
| `backend/app/tasks/tcg_mirror.py:303` | `TCG_SHEETS_SA_KEY_FILE` が未設定なら、ログを出して何もせず終わる |
| `backend/app/tasks/tcg_mirror.py:262` | 各タブを `clear()` してから A1 へ全件を書く（追記ではなく全上書き） |
| `backend/app/tasks/tcg_mirror.py:270` | 書くタブは「[MIRROR] 商品マスタ／検索キーワード／仕入元／仕入元サマリー／DB構造」と「READ ME」。それ以外のタブには触らない |
| `backend/app/tasks/tcg_mirror.py:30` | 書き込み先は固定の spreadsheetId。シートの新規作成はしない |
| `backend/app/tasks/tcg_mirror.py:249` | DB は共用の `AsyncSessionLocal` を `asyncio.run` の中で使う（後片付けの `engine.dispose()` が無い） |
| `docker-compose.yml:241` | celery-worker にも `TCG_SHEETS_SA_KEY_FILE` を渡している（`docker-compose.yml:258` で鍵ファイルを読み取り専用で載せる） |
| `backend/tests/test_tcg_mirror.py:37` | テストは ID 固定・作成経路なし・未設定時スキップの確認だけ。Celery に登録されているかは見ていない |

- 【事実】git の履歴では、2026-08-31 の追加（e469bca70）から今まで、このファイルに `celery_app.task` や `shared_task` が書かれたことは一度もない（`git log -S`）。
- 【事実】worker のログには、毎日 1 件ずつ「unregistered」が出ている。09-18〜10-15 で 28 件（Fable の生出力 /tmp/CC報告ファイル/ai-ops-u11-u13/fable/）。
- 【事実】書き写しが遅れていた分を取り戻す処理はない。毎回、その時点の DB 全件で上書きする。
- 【事実】2026-10-15、PO が「写しシートはいま見ている」と答えた（y）。
- 【未確認】本番の .env に `TCG_SHEETS_SA_KEY_FILE` が入っているか。DEPLOY_LOG.md の記録しかない。直したあと初めて動いたときのログで確かめる（design の K2）。

### §2 毎朝の件数突き合わせ（sa02_recon）が一度も動いていない

| 引用先 `path:line` | 確認内容 |
|---|---|
| `backend/app/tasks/sa02_recon_monitor.py:136` | `def run_sa02_daily_recon() -> dict:` にデコレータが無い（Opus 再読） |
| `backend/app/celery_app.py:130` | beat に `"sa02-daily-recon"`、毎日 08:00 JST。コメントに「並走終了後にこのエントリを削除すること」とある |
| `backend/app/tasks/sa02_recon_monitor.py:71` | 当日の `meta_messages` の件数と、`conversation_logs`（inbound）の件数を、テナントごとに比べる |
| `backend/app/tasks/sa02_recon_monitor.py:125` | 差がゼロでも差があっても、毎日 1 通を Discord へ送る |
| `backend/app/tasks/sa02_recon_monitor.py:26` | 送り先は環境変数 `ADMIN_NOTIFICATION_DISCORD_WEBHOOK`。未設定なら送らない |
| `backend/app/tasks/sa02_recon_monitor.py:48` | DB は共用の `AsyncSessionLocal` を `asyncio.run` の中で使う（`engine.dispose()` が無い） |
| `docs/plans/sa-progress/SA-02-design.md:90` | §10 並走期間。終了条件は 3 つ（`docs/plans/sa-progress/SA-02-design.md:119`）。段階2 完了日と読み取り切替日は「予定未定」のまま |
| `backend/tests/test_sa02_recon_monitor.py:142` | テストは beat の名前の文字列の一致だけを見ている。登録されているかは見ていない |

- 【事実】worker のログの「unregistered」は 09-18〜10-15 で 28 件。
- 【事実】同じ突き合わせを定期的に行う経路は、ほかに無い（`.github` の sa02 ヒットは 0）。手動用のスクリプト（scripts/verify_sa02_stage2_count_check.py）はある。
- 【事実】2026-10-15、PO が「毎朝の突き合わせも直す」と答えた（y）。

### §3 15 分ごとのまとめ翻訳（translate_pending_messages）

| 引用先 `path:line` | 確認内容 |
|---|---|
| `backend/app/tasks/translation.py:123` | `translate_pending_messages` の登録（name 一致）。本体 `_run_batch` は `backend/app/tasks/translation.py:151`〜257 |
| `backend/app/tasks/translation.py:20` | `_BATCH_SIZE = 20`（まとめ翻訳だけが使う） |
| `backend/app/celery_app.py:117` | beat に `"translate-pending-messages"`、900 秒ごと |
| `backend/app/services/message_translator.py:529` | 予算の判定。HARD_STOP／NO_BUDGET_ROW なら BudgetExceededError。即時翻訳とまとめ翻訳の両方がここを通る |
| `backend/app/services/message_translator.py:154` | `get_required_inbound_targets`。tests を除くと、呼ぶのは `_run_batch` だけ |
| `backend/app/services/message_translator.py:195` | `get_existing_inbound_translation_targets`。tests を除くと、呼ぶのは `_run_batch` だけ |
| `backend/app/services/inbound_translation.py:19` | 即時翻訳は `translate_inbound_message.delay(...)`（`backend/app/tasks/translation.py:24`）で、まとめ翻訳とは別の経路 |
| `backend/app/tasks/translation.py:260` | 翻訳の健全性チェック（毎時）。検知と通知だけで、翻訳はしない。外さない |
| `backend/tests/test_translation_task_context.py:18` | まとめ翻訳を参照するテスト |
| `docs/runbooks/alerts.md:192` | 「毎日 2〜3 回失敗・原因未調査」の記述 |

- 【事実】直近 7 日間で processed=0。「budget exceeded for tenant 1」が 520 回（Fable の生出力）。
- 【事実】まとめ翻訳以外に、翻訳待ちを定期的に拾う経路はない。翻訳が入る経路は、①受信時の即時翻訳、②画面を開いたときの都度翻訳（`backend/app/routers/leads.py:1352` ほか）、③`backend/app/routers/conv_logs.py:136` の 3 つ。
- 【事実】監視ルール（monitoring/）に translate／translation の語は無い。外しても消える警報は無い。
- 【事実】2026-10-15、PO が「この機能は外す」と決めた（原文「→この機能は外す」）。
- 【未確認】tenant 1 の予算の状態が HARD_STOP か NO_BUDGET_ROW か。即時翻訳も同じ判定を通るため、即時翻訳が止まっていないかは、外す前に基準値として件数を取る（design の K4）。

### §4 買取価格の取得のあとに、別の作業が失敗する

| 引用先 `path:line` | 確認内容 |
|---|---|
| `backend/app/tasks/buyback_scraper.py:41` | `buyback.fetch_all_prices`。`asyncio.run` を 3 回呼ぶ（取得・知らせ判定・商品の照合） |
| `backend/app/services/buyback_scraper/alert_checker.py:12` | 知らせ判定は共用の `AsyncSessionLocal`（= `backend/app/database.py:33` の共用 engine）を使う |
| `backend/app/tasks/buyback_scraper.py:28` | 取得と照合は、呼ぶたびに自前の engine を作る |
| `backend/app/tasks/translation.py:144` | 既存の型：`finally: asyncio.run(engine.dispose())`。コメントに「接続の置き場が古いループに紐づいたまま残り、次の作業で "attached to a different loop" を起こすので全部捨てる」とある |
| `backend/app/celery_app.py:167` | 買取価格の取得は 1 日 3 回（UTC 1・4・13 時） |

- 【事実】まとめ翻訳の失敗 18 回（7 日間）は、18 回とも、同じ worker プロセスで買取価格の取得の直後に起きている。例外は「attached to a different loop」（Fable の生出力）。
- 【未確認】因果を再現試験で確かめてはいない。上の既存コメントの説明と、18/18 の並びが一致する、という事実までが分かっている。
- 【事実】写しシートと突き合わせを登録すると、どちらも共用の engine を `asyncio.run` で使う。買取価格の取得と同じ worker プロセスに当たれば、同じ失敗を起こしうる形になっている。

### §5 ほかに登録漏れはないか

- 【事実】`backend/app/celery_app.py:61`〜185 の beat 21 件（task 名は 20 種）を、実際の登録と突き合わせた。未登録は tcg_mirror と sa02 の 2 件だけ（/tmp/CC報告ファイル/ai-ops-celery-fix/E_*.txt）。
- 【事実】beat の名前が登録済みかを確かめるテスト・CI は無い。

### §6 本番の二重保存（U13）の確認結果

- 【事実】2026-10-02 の 16:00Z と 17:00Z に買取価格の取得が 2 回動き、2 店の 465 商品が 2 件ずつ記録されていた（Q2: products_in_both=465）。通常 1 回分は 465 件（Q4）。生出力は /tmp/CC報告ファイル/ai-ops-u13-dup/query_result.txt。
- 【事実】2 回目は約 1 時間後に改めて取りに行った記録で、取得時刻（fetched_at）が違う。同じ行を書き写したものではない。
- 【事実】知らせの条件は 0 件（buyback_alert_rules が 0 行）。Discord の二重送信はない。
- 本設計では、この 465 件の後始末はしない（各行がその時刻の正しい価格のため）。

---

## 不明点リスト

| # | 内容 | 確かめ方 | 期限 |
|---|---|---|---|
| R1 | 本番の .env に `TCG_SHEETS_SA_KEY_FILE` があるか | 直した後、初回 02:30 JST のログ（K2） | 反映の翌朝 |
| R2 | 本番に `ADMIN_NOTIFICATION_DISCORD_WEBHOOK` があるか | 直した後、初回 08:00 JST の Discord（K3） | 反映の翌朝 |
| R3 | tenant 1 の予算の状態（即時翻訳も止まっていないか） | 反映前に、即時翻訳の 7 日件数を基準値として取る（K4） | 実装前 |
| R4 | 買取価格の取得のあとの失敗の因果 | 反映後 3 日間、買取価格の取得の直後の失敗が 0 か（K5） | 反映後 3 日 |
