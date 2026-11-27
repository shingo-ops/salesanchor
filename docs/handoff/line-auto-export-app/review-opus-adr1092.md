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

---

## 続き（2026-11-27・「保守口（無線デバッグ）の強制開け直し」便）

| 項目 | 内容 |
|---|---|
| 対象 | `release/line-export-maintenance-cycle`（土台 `origin/main` 218e4fc7c） |
| 対象ADR | ADR-1092 追補（同日） |
| 設計 | `docs/handoff/line-auto-export-app/design.md` 追補 2026-11-27「保守口（無線デバッグ）の強制開け直し」 |
| 区分 | A（`tools/` のため） |
| 審査日 | 2026-11-27 |
| 結果 | **APPROVE（指摘2点を審査中に修正済み）** |

### 審査で見つけて直した欠陥

1. **記録があふれる**: `checkSignalFile` が `signal_unreadable` を `recordIfChanged` で記録していたが、`recordIfChanged` は `SchedulerStore.getLastMaintenanceChannelResult`（`ensureOpen`/`cycle` と共用の1枠）を見ていた。そのため、ディレクトリが読めず（`signal_unreadable`）かつ Wi-Fi が無い（`ensureOpen` が `blocked`）回に、1回の実行の中で `checkSignalFile` が枠を `signal_unreadable` に上書き→直後の `ensureOpen` が「枠が変わった」と見て `blocked` に上書き、という往復が起き、記録が毎回2行出る（アプリは1日約70回動くため実害）。「変化したときだけ記録する」という作法が崩れていた。
   - **直し**: `SchedulerStore` に合図ファイルの読み取り可否専用の枠（`last_signal_unreadable`、`wasLastSignalUnreadable`/`setLastSignalUnreadable`）を1つ足し、`signal_unreadable` の重複判定をそちらで行うよう `MaintenanceChannel` に `recordSignalUnreadableIfChanged`/`clearSignalUnreadable` を追加した。`ensureOpen`/`cycle` の結果枠とは完全に分離し、ディレクトリが読める状態に戻ったら枠を解除するため、読めない状態が続く間は1行だけになる。
2. **合図を取りこぼす**: 削除が成功した場合も `signalId`（`lastModified`+`length`）を `SchedulerStore` に保存していたため、次に置いた合図が偶然同じ `lastModified` 秒・同じ長さだと「処理済み」と誤判定し、無視してしまう。合図は「保守口が切れて困っている」ときに置かれるものなので、取りこぼすと人手に戻ってしまう。
   - **直し**: 削除に成功したときは `SchedulerStore.clearLastMaintenanceSignalId` で識別子を消す。保存するのは削除に失敗したときだけに変更した。コメント・javadocもこれに合わせて書き直した。

修正後に再ビルドし、終了コード 0・`versionCode=25` / `versionName=0.22.0-stage3`・署名 SHA-256（`c64146dcaca2e2fad8c8b0e37cb0eb0435be52b01f418d02f988d3e213972709`、既存APKと一致）を確認した。

### 残っている不確かさ（実機で未証明）

アプリが合図ファイル（`maintenance-open`）を**読めるかどうかは実機で未証明**である。実測で分かっている前提は以下（推測ではなく実機で測った値）:

- アプリは `targetSdkVersion=24`（旧方式のストレージモデル）。
- `WRITE_EXTERNAL_STORAGE` は `granted=true`、**`READ_EXTERNAL_STORAGE` は `granted=false`**。
- アプリは製品ビルドで `run-as` が使えないため、アプリのプロセス権限で実際にファイルを読めるかを手元（proot環境）から直接確認する手段が無い。

このため、合図ファイルの存在確認（`File#isFile`/`lastModified`/`length`）がアプリのプロセス内で `SecurityException` を投げる可能性があり、投げた場合は `checkSignalFile` の外側の `catch (RuntimeException e)` で吸収され `signal_unreadable` が記録される設計にしてある。**判定材料は実機ログの `signal_unreadable` の記録の有無**: 出れば方式の見直し（`READ_EXTERNAL_STORAGE` の追加権限付与、または別の受け渡し経路への変更）が必要、出なければこの方式で機能している。実機検証手順は `docs/handoff/line-auto-export-app/design.md` 追補に記載した。

---

## 続き（2026-11-27・版名が中身を保証しなかった事象）

PO が実機で重大な事実を測った: 端末のアプリが **2026-11-27 16:48:51 に入れ替えられていた**（実機への `adb install` は本便の作業規約で禁止されている操作）。さらに、入れ替わったAPKは `dumpsys` の申告では `versionName=0.22.0-stage3`／`versionCode=25`（本便が作る版と同じ）だが、**中身（`classes.dex`）は古い**ことが判明した。

### 事実（PO の実機計測・本審査で裏取りした範囲）

- 端末の APK の `classes.dex`（md5 `216bf5c57db4a42f5e392c1c0de7c8d0`）には `ensureOpen` しか無く、`cycle`・`checkSignalFile` は存在しない。文字列 `maintenance-open`・`cycled_opened`・`signal_unreadable` も0件（本審査で同ファイルに対し `grep -a` で再確認し、PO の報告と一致した）。
- 本ブランチのコミット `576269377`（1便目）・`2b8c6b808`（Opus審査の指摘2件を直した便）でビルドした `classes.dex` には、それぞれ該当する文字列が存在する（コミット済みのビルドは健全）。
- **本PRの作業がその直接の原因ではないことを、コミットのタイムスタンプで確認した**: 端末への入れ替えは 16:48:51 JST（=07:48:51 UTC）。本ブランチの worktree 作成は 2026-11-27T08:00:07Z（17:00:07 JST）、最初のコミット `576269377` は 2026-11-27 17:03:31 JST（08:03:31 UTC）、`check-before-submit.sh` の実行記録も 08:04:14Z 以降のみ。いずれも件の入れ替え時刻より**後**であり、この時点で本ブランチのコミットはまだ1つも存在しなかった。本便の実装者（Claude、本審査記録の実装側）は `adb install` 等のadbコマンドを実行していない（本便のBashコマンド履歴に `adb` は一度も現れない。件の事象発覚後に読み取り専用の `adb devices`／`which adb` を事実確認のために実行したのみ）。
- 入れ替わったAPKがどのビルド・どの手順・どのセッションで生まれたかは**未確定**（別のworktreeでの作業や、マニフェストだけ先に上げてビルドした等の心当たりは本便側には無い。「分からない」が正直な答え）。

### 対策（版名が中身を保証しない状態を機械的に防ぐ）

原因の特定を待たず、再発を防ぐ関所を `build.sh` に追加した（詳細: `docs/handoff/line-auto-export-app/design.md` 「版名が中身を保証しない事象への対策」節）:

- `AndroidManifest.xml` の `versionName` を唯一の出所として `BuildStamp.java`（`BuildStamp.VERSION_NAME`）を毎ビルド生成する。
- ビルドの最後（`classes.dex` 生成直後）に、その版名の文字列が `classes.dex` に実在するかを `grep -a -F` で確認し、無ければビルドを失敗させる（0以外の終了コード）。
- **この自己検査をコミット済みのAPK（`2b8c6b808`）で実際に流し、合格することを確認した**: `bash build.sh` の `[3b/8]` ステップが `OK: classes.dex に versionName=0.22.0-stage3 の刻印を確認` と出力し、ビルド全体が終了コード0で完了した。
- **検知能力の確認**: 端末の古い `classes.dex`（md5 `216bf5c5...`）に対して同じ `grep -a -F "0.22.0-stage3"` を実行すると0件（不合格）になることを確認した。この dex には旧版文字列 `0.21.0-stage3` も無く（本対策より前のビルドは版名をコード側に刻印していなかったため）、本対策導入前はどの版でも中身の照合手段が無かったことも分かった。

### 残っている懸念

- 入れ替わったAPKの出自は未確定。別セッションの作業ログの確認が必要（本便の範囲外。PO・設計担当側で継続調査）。
- 端末は現在、古いコード（`ensureOpen` のみ）で稼働中であり、LINEの取込自体は正常（17:11 success 確認済み）。本PRのマージ・実機導入は、原因確認とPOの承認が揃うまで行わない。
