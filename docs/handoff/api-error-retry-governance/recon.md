<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。 -->
# Phase 2 recon — api-error-retry-governance（自動の送り直しを続ける仕組み）

親: docs/handoff/api-error-auto-retry/design.md
この文書は何か: PR #4854 の自動の送り直しについて、「続ける仕組み」で何が揃い何が欠けているかを実物で確かめた記録。

**基準**: origin/main 47e0954f7（2026-10-29 fetch 後）。根拠は `git show origin/main:<path>` で読んだ。
**生出力**: /tmp/CC報告ファイル/api-error-auto-retry-governance/（8項目の点検）、/tmp/CC報告ファイル/api-error-auto-retry-gov-recon/（埋め方の調べ）

## 1. 点検の結果（8項目、4項目が ×）

| # | 項目 | 判定 | 根拠 |
|---|------|------|------|
| 1 | 試験が必須の検査で毎回走る | ○ | `.github/workflows/test.yml:242`（pytest 全件）、`.github/workflows/test.yml:251` のジョブ名が main の必須チェック（ruleset 15777895） |
| 2 | 10分ごとの見回りが予定に入っている | ○ | `backend/app/celery_app.py:186`（600秒）、`backend/app/tasks/tcg_extraction_recovery.py:370`、登録漏れの検査 `backend/tests/test_celery_beat_registered.py:14` |
| 3 | 設計判断が ADR にある | × | docs/adr にこの件の ADR が無い。`docs/adr/FEATURE-INDEX.md:20` は ADR-100 だけを指す |
| 4 | 諦めたとき人に知らせる | × | `backend/app/tasks/tcg_extraction_recovery.py:318` の `< :max_attempts` で対象から外れるだけ。通知の処理は 0 件 |
| 5 | 回数を測る指標 | × | ログの行だけ（`backend/app/tasks/tcg_extraction_recovery.py:379`、`backend/app/services/line_analysis_v102_svc.py:510`） |
| 6 | 上限が変わらないよう守る | ○ | `backend/tests/test_api_error_auto_retry.py:186`（SQL の値を完全一致）、`backend/tests/test_api_error_auto_retry.py:76`（待ち [2, 8]） |
| 7 | 担当と見直しの予定 | × | `.claude-pipeline/active-work.d/release-api-error-auto-retry-design.md:5` の担当欄が空。tasks/todo.md と週次の点検に載っていない |
| 8 | ほかの経路は対象外と明記 | ○ | `docs/handoff/api-error-auto-retry/design.md:81` |

補足: `docs/handoff/api-error-auto-retry/design.md:141` の守り手は「人手で守る」のまま。実装 PR で試験に差し替える予告が反映されていない。

## 2. 埋めるのに使える既存の型

- Discord への送信: `backend/app/services/discord_notifier.py:45` の `_post_discord_webhook`（送り先は環境変数 ADMIN_NOTIFICATION_DISCORD_WEBHOOK、`backend/app/services/discord_notifier.py:40`）。失敗は握りつぶして bool を返す。
- 同じ件を二度送らない型: `backend/app/tasks/viewer_share_flag_monitor.py:72`（Redis キーがあれば飛ばす。送れたらキーを置く。キーの期限は30日、`backend/app/tasks/viewer_share_flag_monitor.py:21`）。
- 週1回の件数の知らせ: `backend/app/tasks/bundle_bulk_monitor.py:93`（beat は `backend/app/celery_app.py:207`、月曜 09:05）。`backend/app/tasks/master_required_fields_monitor.py:87`（月曜 09:00、`backend/app/celery_app.py:202`）。
- 諦めた job の拾い方: `backend/app/tasks/tcg_extraction_recovery.py:297` の条件のうち、試行の数を `>= 3` にすると拾える。通知済みを記録する列は extraction_jobs・extraction_attempts に無い（migrations/20260921_110000_pipeline_tables_public.sql:80 と :112）。
- 指標の仕組み: prometheus-client あり（`backend/requirements.txt:42`、`backend/app/metrics.py:133`）。ただし worker の値は Redis を経由して backend が出す（`backend/app/celery_health.py:48`）。Grafana は自動配置あり（`monitoring/grafana/provisioning/dashboards/dashboards.yml:10`）。
- ADR: 最大の番号は ADR-1049。ADR-1050 は空いている。昇格の例は `docs/adr/ADR-1047-rule-registry.md:10`。

## 3. 既存 ADR の検索

- `git grep -i "api-error\|retry_transient\|API_ERROR" docs/adr`: 該当する ADR なし。
- `docs/adr/FEATURE-INDEX.md:20`「取り込み / 解析」→ ADR-100・ADR-014。送り直しの記述なし。
- 関連: ADR-154（試行記録で失敗回数を数える）、ADR-1003（GO委任）。

## 4. 未確認

- 定期処理そのものが止まったときの警告（beat の停止）が今ある規則で拾えるか。今回は、週1回の知らせが来ないことで人が気づく形にとどめる（design.md の弊害欄）。
- Loki の規則が本番の Loki に読み込まれているか。今回の設計は Loki の規則を使わない。
