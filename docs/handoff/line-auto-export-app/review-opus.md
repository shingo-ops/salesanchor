# Opus 審査記録 — 電池最適化で後回しにされたことを検知・記録・復旧できる仕組み

| 項目 | 内容 |
|---|---|
| 対象 | `release/line-export-battery-exempt-guard`（土台 `origin/main` c3834ee5f） |
| 設計 | `docs/handoff/line-auto-export-app/design.md` 追補 2026-11-26 |
| 現在地 | `docs/handoff/line-auto-export-app/recon.md` 追補 2026-11-26 |
| 区分 | A（ADR-1015 の危険パス一覧に `tools/` が含まれるため） |
| PO 承認 | 2026-11-26 Shingo（PO）「3点でgo」 |
| 審査日 | 2026-11-26 |
| 結果 | **APPROVE** |

## 確認した点

1. **当初案の否定が実測で裏付けられている**: `USE_EXACT_ALARM` は `targetSdkVersion 24` では効かず、アラームは既に `window=0 exactAllowReason=compat`＝正確。原因は `standby_quota_rare=1`（1時間に1回）であり、実装はこの事実に沿って「割当を外す（除外）」「外れたことに気づく」に絞られている。新機能の追加や仕様の拡大は無い。
2. **API 境界**: `PowerManager#isIgnoringBatteryOptimizations` は API23 追加で、`minSdkVersion 23` の `android.jar` から直接呼べる。リフレクション不要。取得不可・例外時は `null`（不明）を返し、呼び出し元はいずれも `null` を扱っている。
3. **既存の作法を踏襲**: 除外状態の検知は `notifyIfExactModeChanged` + `SchedulerStore#wasLastScheduleWasExact` と同じ「変化時だけ記録」。発火予定時刻の保存は `getNotificationReservedAt` と**別キー**にしており（意味が違うため）、既存の判定を壊していない。
4. **誤検知の経路を確認した**:
   - 個別の `cancel(...)` 呼び出しは `cancelAll` 以外に1か所（`onAlarmFired` 内の通知引き金）だけで、そこは `onAlarmFired` 冒頭の `clearScheduledFireAt` を通った後。保存値が残らない＝誤検知しない。
   - `cancelAll` は保存値も消す。`disable()` は `cancelAll` の前に `checkStaleScheduledFires` を呼ぶので、本物の空振りだけ記録される。
   - `defer_floor` の経路は `scheduleAt` を通るため保存値が延ばした先に更新される。
5. **既存の集計を壊していない**: 追加は新しい `phase`（`battery_exemption_changed`・`missed_fire`）と、実行開始行への `batteryOptimizationIgnored` の追加のみ。既存項目の名前・意味・タイミング（`FLOOR_INTERVAL_MS` 等）は不変。既存の `jq` 条件はそのまま通る。
6. **ビルドと署名**: `bash build.sh` が終了コード0。`out/app-debug.apk` は `versionCode=23` / `0.20.0-stage3`。証明書 SHA-256 が実機の APK と一致（`c64146dcaca2e2fad8c8b0e37cb0eb0435be52b01f418d02f988d3e213972709`）＝上書き更新で PIN・ユーザー補助・通知の権限が保たれる。
7. **ハードコード**: 画面文字はすべて `res/values/strings.xml` の `battery_*`。レイアウトの寸法・色は既存の直書き値（24dp/16dp/8dp/20sp/16sp/`#33000000`）の再利用のみで、新しい寸法・色は作っていない。

## 指摘（仕様どおりの振る舞い。直しは不要だが読み手が知っておくこと）

- **再起動後に `missed_fire` が1行出ることがある**: 端末の電源が切れていた間は実際に発火していないため記録は誤りではないが、記録を読むときは再起動を考慮すること。
- **不正確モードに落ちた回は、正当な遅れも `missed_fire` になりうる**: ただし発火した引き金は `onAlarmFired` 冒頭で消えるため、記録されるのは「他の引き金の入口を通ったとき」に限られる。これは検知したい症状そのものなので許容する。

## 未実施（この PR の範囲外）

- 実機へのインストールと、除外を外しての実挙動確認（`battery_exemption_changed`・`missed_fire` の記録確認）。インストールは稼働中の自動化に手を入れるため、PO の指示で別途行う。
- `client.py:679` の `termux-job-scheduler` 呼び出しに残る「孫プロセスを殺さない」書き方（今回の範囲外。別作業）。
