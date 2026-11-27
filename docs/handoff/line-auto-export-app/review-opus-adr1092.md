# Opus 審査記録 — 保守口（無線デバッグ）が切れたらアプリが開き直す

| 項目 | 内容 |
|---|---|
| 対象 | `release/line-export-maintenance-channel`（土台 `origin/main` 65934286b） |
| 対象ADR | ADR-1092 |
| 設計 | `docs/handoff/line-auto-export-app/design.md` 追補 2026-11-27 |
| 現在地 | `docs/handoff/line-auto-export-app/recon.md` 追補 2026-11-27 |
| 区分 | A（ADR-1015 の危険パス一覧に `tools/` が含まれるため） |
| PO 承認 | 2026-11-27 Shingo（PO）「1よい2よい3よい4方法が決まり不要になったら消す」 |
| 審査日 | 2026-11-27 |
| 結果 | **APPROVE（指摘2点を審査中に修正済み）** |

## 審査で見つけて直した欠陥

1. **キーが未設定のときに何もしなかった**: `adb_wifi_enabled` が読めない（`-1`）場合に早期 return していたため、保守口が閉じていても永久に開かない経路が残っていた。目的は「閉じていたら開く」なので、**`1` 以外（`0` と `-1`）はすべて書きにいく**ように直した。`1` を書くこと自体は無害である。
2. **2回目以降の復旧が記録に残らなかった**: `opened` を「前回結果と変化したときだけ記録」にしていたため、1度 `opened` を記録すると、その後に再発した復旧が同じ値として捨てられていた。ADR-1092「維持の仕組み」が求める「復旧の実績が残る」が成り立たないため、**`opened` は毎回記録する**ように直した（復旧はまれな事象なので記録量は増えない）。`blocked`・`no_permission` は毎回の実行で繰り返し得るため、変化時だけの記録を維持した。

修正後に再ビルドし、終了コード 0・`versionCode=24` / `versionName=0.21.0-stage3` を確認した。

## 確認した点

1. **書き換えるキーが1つに限定されている**: `KEY_ADB_WIFI_ENABLED = "adb_wifi_enabled"` のみ。`adb_enabled`（USB デバッグ）を触るコードは無い（ADR-1092 What-4 を満たす）。
2. **止められる**: `SELF_RECOVERY_ENABLED` 1つで全体が無効化され、無効時は読み取りすら行わない（ADR-1092 What-6）。
3. **落ちない**: 権限未付与の `SecurityException` を捕まえて `no_permission` として記録し、その他の `RuntimeException` も吸収する。診断・復旧の仕組みがアプリ本体を壊さない既存の方針に沿う。
4. **呼び出し場所が2か所に限定されている**: `RunScheduler#scheduleAt` の末尾（全予約の共通出口）と `AlarmReceiver` の `BOOT_COMPLETED` 経路。後者は在アプリのタイマーが OFF でも通るため、再起動直後も効く。
5. **Wi-Fi が無い回の扱いが実測に沿っている**: 書いた後に読み直して定着を確かめ、定着しなければ `blocked` として次回に持ち越す。実測（Wi-Fi 無しでは 1 が定着しない／有りなら定着する）と一致する。
6. **既存の集計を壊していない**: 追加は新しい `phase=maintenance_channel` の行だけ。既存のログ項目・名前・タイミング（`FLOOR_INTERVAL_MS` 等）は不変。
7. **署名**: `apksigner verify --print-certs` の SHA-256 が実機の APK と一致（`c64146dcaca2e2fad8c8b0e37cb0eb0435be52b01f418d02f988d3e213972709`）。上書き更新で暗証番号・ユーザー補助・通知の権限が保たれる。既存の `build/debug.keystore` が再利用されたことをビルド出力で確認した。
8. **権限が APK に入っている**: `aapt dump badging` に `uses-permission: name='android.permission.WRITE_SECURE_SETTINGS'`。

## 指摘（直しは不要。運用で知っておくこと）

- **予期しない `RuntimeException` は記録に残らない**（ログにのみ出る）。結果が確定しないため記録しない判断は妥当だが、万一この経路が常態化すると記録からは見えない。現実的に起きるのは権限未付与（記録される）である。
- **`pm grant` はアプリを削除して入れ直すと消える**。入れ替え手順に付与を含めること（README と ADR に記載済み）。
- **権限が未付与のままだとこの仕組みは働かない**。付与は本 PR のマージ後、実機適用時に行う。

## 未実施（この PR の範囲外）

- 実機へのインストールと `pm grant`、および自動復旧の実挙動確認（`adb_wifi_enabled` を 0 にして復旧と記録を確認）。PO の承認を得てから行う。
- 調査で開いた固定ポート 5555 を閉じ、`adb_enabled` を 0 に戻す作業（本方式の確認後に実施）。
- 調査で Termux に付与した `WRITE_SECURE_SETTINGS` の削除（PO 決定: 方法が決まり不要になったら消す）。
- Wi-Fi 自体の安定化（画面操作・PO 実施）。
