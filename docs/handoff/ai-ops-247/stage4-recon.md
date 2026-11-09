# 段階4（AI を起こす部分）の前の現在地調べ

- 作成: 2026-11-09 Opus（設計担当）。PO の選択「今の進み具合とアラートの種類を数えてから、AI を起こす部分の設計を始める」に対応する。
- 基準: origin/main（この worktree の土台）と、本番の読み取り専用の道（ADR-1024）で 2026-11-08T16:03Z に読んだ障害記録。
- 状態: 調査のみ。設計・実装は未着手。

## 1. 段階ごとの進み具合（事実）

| 段階・便 | 中身 | 状態 | 根拠 |
|---|---|---|---|
| 段階1〜2 | 障害記録の表・保守 API・Discord 表示 | 済 | `docs/handoff/ai-ops-247/card-stage1-bin1.md`〜`docs/handoff/ai-ops-247/card-stage2-bin-c.md`、`backend/app/routers/ops.py:230`〜`:718` に口 9 つ |
| 段階3 便D・便E・定着 T1 | 健康診断・状態書き係 | 済 | `docs/handoff/ai-ops-247/card-stage3-bin-d.md`・`docs/handoff/ai-ops-247/card-stage3-bin-e.md`・`docs/handoff/ai-ops-247/card-stage3-teichaku-t1.md` |
| 段階3 便F | 保守 API に「auto で未処置」の絞り込みを足す | 未着手 | `docs/handoff/ai-ops-247/stage3-design.md:89`。カードの文書が無い |
| 段階3 便G | 応急処置係（prod1 の cron） | 未着手 | `docs/handoff/ai-ops-247/stage3-design.md:99`。origin/main に処置係のコードが無い（`first_aid` の語は表の列と `backend/app/routers/ops.py:48`・`:356`・`:414` のみ） |
| 段階3 便H | migration 失敗の見張り | 未着手 | `docs/handoff/ai-ops-247/stage3-design.md:115`。`DeployMigrationFailed` の語が origin/main のコード・見張りに無い |
| 段階3 の前提 V6 | 健康診断の 24 時間誤判定 0 | 未確認 | `docs/handoff/ai-ops-247/stage3-design.md:171`。結果の記録が見つからない |
| 段階4 | AI を起こす | 未着手 | `docs/adr/ADR-1012-ai-ops-247.md:28`（決定 4）。`/fire` を呼ぶコードが無い |

段階4 の前に PO 判断が要ると ADR に書いてある点:
- 見張りからの常時起動がサブスクの使い方の範囲に入るか（`docs/adr/ADR-1012-ai-ops-247.md:42`）。
- PO が Web で routine を作り、鍵を本番の secrets に入れる作業（`docs/adr/ADR-1012-ai-ops-247.md:45`）。

## 2. 見張りの通知の種類（42 種）

- 定義: `monitoring/prometheus/alert_rules.yml` 36 種、`monitoring/loki/rules/jarvis/alerts.yml` 6 種。全種に tier と手順書リンクがある。
- tier の内訳: page 14 種、ticket 28 種、auto 0 種。
- 流れ: `monitoring/alertmanager/alertmanager.yml:2`〜`:15`。RecoveryCheckPassed だけは表示用の部屋へ送って止まる（`:10`〜`:12`）。他は Discord の 1 部屋（`:13`〜`:14`）と保守 API（`:15`）の両方へ送る。

## 3. 本番の障害記録の実数（2026-10-16〜2026-11-08）

読み取り: `ai_ro.public__ops_incidents`。AUDIT sha=3ae852c54602 rows=16。

| 通知の名前 | tier | 件数 | 通知回数 | 応急処置 | AI 起動 | 最後 |
|---|---|---|---|---|---|---|
| BruteForceAttempt | page | 400 | 770 | 0 | 0 | 11/08 |
| SustainedAuthFailure | ticket | 162 | 338 | 0 | 0 | 11/08 |
| ContainerUnhealthy | page | 25 | 51 | 0 | 0 | 10/24 |
| HighMemoryUsage | ticket | 20 | 40 | 0 | 0 | 11/08 |
| KumaMonitorDown | page | 9 | 23 | 0 | 0 | 11/08 |
| ServiceDown | page | 8 | 16 | 0 | 0 | 11/08 |
| BackendHighLatency | ticket | 6 | 12 | 0 | 0 | 11/08 |
| ViewerInventoryStale | ticket | 5 | 8 | 0 | 0 | 10/29 |
| RecoveryCheckFailed | page | 5 | 10 | 0 | 0 | 11/08 |
| CeleryHeartbeatStale | page | 4 | 6 | 0 | 0 | 10/29 |
| ContainerStateStale | page | 4 | 9 | 0 | 0 | 11/08 |
| BackendWorkerSaturated | ticket | 4 | 6 | 0 | 0 | 10/29 |
| CeleryQueueBacklog | ticket | 3 | 6 | 0 | 0 | 10/29 |
| BackupTimestampAbsent | ticket | 1 | 9 | 0 | 0 | 10/16 |
| OpsPipelineTest | （なし） | 1 | 2 | 0 | 0 | 10/16 |
| discord-bug-report（人の報告） | （なし） | 1 | 1 | 0 | 0 | 10/24 |

- 合計 658 件。ログインの失敗系 2 種（BruteForceAttempt・SustainedAuthFailure）が 562 件（85%）。
- 鳴ったのは 42 種のうち 14 種。残り 28 種は 0 件。
- 応急処置・AI 起動は全件 0（便G・段階4 が無いことと合う）。

## 4. 障害記録を通らずに Discord へ直接送る送り手

障害記録（唯一の正本）に残らない。段階4 の AI はこれらを見られない。

| 送り先の設定名 | 送り手の数 | 例 |
|---|---|---|
| DISCORD_WEBHOOK_OWNER_PING | 12 | `.github/workflows/deploy.yml`・`.github/workflows/security-scan.yml`・`.github/workflows/prod-ui-check.yml` |
| DISCORD_WEBHOOK_SCHEDULED_REPORT | 10 | `.github/workflows/weekly-stale-pr.yml`・`.github/workflows/zombie-report.yml` |
| DISCORD_WEBHOOK（バックエンドの定期作業） | 12 | `backend/app/tasks/gemini_route_watch.py`・`backend/app/tasks/bundle_bulk_monitor.py`・`backend/app/services/ops_mail_notifier.py` |
| DISCORD_WEBHOOK_PR / _CI | 3 | `.github/workflows/discord-ci-notify.yml`・`.github/workflows/discord-pr-notify.yml` |
| DISCORD_WEBHOOK_PERMISSION / DISCORD_ERR_WEBHOOK_PERMISSION | 1 | `backend/app/routers/leads.py` |
| DISCORD_WEBHOOK_PLAN_REVIEW | 1 | `.github/workflows/hook-permission-check.yml` |
| DISCORD_WEBHOOK_OPS | 1 | `scripts/backup_to_s3.sh` |
| DISCORD_WEBHOOK_URL | 1 | `scripts/sop-health-collector.js` |

（数はテストと設定の見本を除いた送り手のファイル数。重複あり。）

## 5. 分かったこと

1. 段階4 の前に、段階3 の便F・便G・便H と V6 が残っている。ADR-1012 の順番では、AI を起こす前に応急処置係が要る。
2. 記録の 85% はログイン失敗の通知。AI を全件で起こすと、ほぼこの 2 種で枠を使う。起こす種類を絞る表が要る。
3. PO の言う「部屋ごとの通知」の多くは、障害記録を通らない直接送り。AI に渡すなら、まず保守 API へ送る形に寄せる（正本を 1 つに保つため）。
4. サブスクの使い方の範囲は PO 判断が要る（ADR-1012 :42）。

## 6. 未確認

- V6 の結果（prod2 の Prometheus にまだ問い合わせていない）。
- 直接送りの各送り手の 30 日の送信回数（記録が無い）。
