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

## 続き（2026-11-27・版番号の衝突。当初「版名が中身を保証しなかった事象」として記録した件の訂正）

### 訂正（記録の正確さのため残す）

当初、Opus は「端末のアプリが2026-11-27 16:48:51に入れ替えられ、版名（`versionName=0.22.0-stage3`／`versionCode=25`）は新しいのに中身は古い＝版名が偽りのAPKが入った」と記録し、本便（実装担当）がその入れ替えを行ったのではないかと疑って指摘した。**その後 Opus 自身が実機とハッシュで裏取りし、この疑いは誤りだったことが確定した。** 本便（実装担当）は `adb install` 等の adb コマンドを一度も実行していない（Bashコマンド履歴に `adb` は一度も現れない。事象発覚後に読み取り専用の `adb devices`／`which adb` を事実確認のために実行したのみ）。コミットのタイムスタンプ（worktree作成 2026-11-27T08:00:07Z・最初のコミット08:03:31Z）も、端末への入れ替え時刻（16:48:51 JST＝07:48:51 UTC）より後であり、物理的に本便の作業が原因になり得ないことを裏付けていた。

### 確定した事実（ハッシュ一致による特定）

- 端末のAPK（md5 `cc6bbb97f81dc10570c7b738f598e255`）は、**別ブランチ `release/line-export-click-retry`（`/root/worktrees/release-line-export-click-retry/tools/line-auto-export-app/out/app-debug.apk`）のビルドと1バイト単位で同一**であることがハッシュ一致で確定した。そのツリーのビルド時刻は 15:46:49、マニフェスト更新は 15:46:46（本便のworktree作成・最初のコミットより前）。
- そのツリーのコードに `cycle`・`checkSignalFile` は0件（＝PR #5803 のままのコード）。
- そのブランチは **PR #5808（OPEN）** で、`versionCode=25`／`versionName=0.22.0-stage3` を**先に**コミット済みだった（`origin/main` は 24／0.21.0-stage3）。
- つまり「版名が偽りのAPK」ではなく、**PR #5808 の正当な自己整合ビルド**だった。本便（本PR）も独立に同じ値（25／0.22.0-stage3）を次の版として選んでいたため、**2つのPRが同じ版番号を取り合っていた**。版番号だけでは、端末に入っているのがどちらのPRのコードかを識別できない状態になっていた。

### 対応（版番号を上げて衝突を解消）

- 本PRの `versionCode` を 25→**26**、`versionName` を 0.22.0-stage3→**0.23.0-stage3** に上げ、PR #5808 の値と重複しないようにした。
- 既存の `build/debug.keystore` で再ビルドし、署名 SHA-256（`c64146dcaca2e2fad8c8b0e37cb0eb0435be52b01f418d02f988d3e213972709`）が変わらないことを確認した。
- **自己検査（`build.sh [3b/8]`）を再実行し、`OK: classes.dex に versionName=0.23.0-stage3 の刻印を確認` を得た**（新しい版番号での刻印・検査が機能することを確認）。

### 対策（版名が中身を保証しない事象そのものへの対策。引き続き有効）

- `AndroidManifest.xml` の `versionName` を唯一の出所として `BuildStamp.java`（`BuildStamp.VERSION_NAME`）を毎ビルド生成し、ビルドの最後に `classes.dex` へその文字列が実在するかを `grep -a -F` で確認する自己検査は、引き続き有効（詳細: `docs/handoff/line-auto-export-app/design.md`）。
- **この自己検査の限界（過信しないこと）**: 今回確定した真因は「版名そのものが偽り」ではなく「**異なる2つのPRが同じ版番号を使っていた**」ことだった。PR #5808 のビルドは自己整合（版名と中身が一致）しているため、**本自己検査はこの種の衝突を検出できない**。自己検査が守れるのは「1つのビルドの中で版名とコードがずれていないか」だけであり、「複数のPR・ブランチ間で版番号が重複していないか」は別の問題として運用で防ぐ必要がある（下記「運用上の注意」参照）。

### 運用上の注意（今回の教訓）

- 同じアプリ（`tools/line-auto-export-app/`）を複数のブランチが同時に触るため、**版番号（`versionCode`／`versionName`）は、他に在庫中（オープン）のPRが既に使っている値とぶつからない値を取る**。ブランチを作る時点で `gh pr list --search "tools/line-auto-export-app"` 等で他のオープンPRの版番号を確認するか、統合直前に最新の `origin/main` の値から改めて採番し直すのが安全。
- **実機で実際に動いているコードの識別は、版名（`dumpsys`の申告）を信じず、`classes.dex` の内容を直接確認する**。手順:
  ```bash
  adb pull /data/app/~~<ランダム文字列>/jp.salesanchor.lineexport-<ランダム文字列>/base.apk /tmp/device.apk
  # もしくは: adb shell pm path jp.salesanchor.lineexport でAPKの実際のパスを確認してから pull する
  unzip -o /tmp/device.apk classes.dex -d /tmp/device_extract
  strings -a /tmp/device_extract/classes.dex | grep -x "checkSignalFile\|cycle\|maintenance-open\|cycled_opened"
  ```
  目印の文字列（例: 本PRなら `checkSignalFile`・`cycle`・`maintenance-open`・`cycled_opened`）が出れば、そのPRのコードが実際に動いている証拠になる。

### 残っている懸念

- 端末は現在、PR #5808（`ensureOpen` のみ）のビルドで稼働中であり、本PR（保守口の強制開け直し）の機能は端末に未導入。LINEの取込自体は正常（17:11 success 確認済み）。
- 本PRのマージ・実機への正しいビルドの導入は、PO の承認が揃うまで行わない（実機への `adb install`・再起動・`adb_wifi_enabled`/`adb_enabled` の書き換えは禁止のまま）。

---

## 続き（2026-11-27・合図ファイルの検知方式を作り直し。実機導入で `canRead()` の前提が崩れたことを受けて）

| 項目 | 内容 |
|---|---|
| 対象 | `release/line-export-maintenance-cycle`（PR #5811・OPEN継続） |
| 対象ADR | ADR-1092 追補3 |
| 設計 | `docs/handoff/line-auto-export-app/design.md` 追補「合図検知の作り直し（`canRead()` 門番の撤去）」 |
| PO 決定 | 2026-11-27 Shingo（PO）「読み取り権限は増やさない」 |
| 区分 | A（`tools/` のため） |
| 審査日 | 2026-11-27 |

### 経緯（実機で前提が崩れたことの確定）

上記「残っている不確かさ（実機で未証明）」節は「合図ファイルを読めるかどうかは実機で未証明」としていたが、PR #5811 の成果物（`versionCode=26`／`versionName=0.23.0-stage3`）を実機へ導入した結果、**未証明ではなく「機能していない」ことが確定した**。実機の `run-20261127.jsonl` に `result=signal_unreadable` が記録され、旧 `checkSignalFile` の `!dir.canRead()` が true になっていた。一方、同じディレクトリへの書き込み（この記録自体）は成功している。つまり**「書けるのに `canRead()` が false になる」**（`READ_EXTERNAL_STORAGE` 未付与・`targetSdkVersion=24`）という、design.md が懸念していた最悪のケースが実際に起きていた。

### 設計変更

PO は「読み取り権限を増やす」ではなく「読み取りに依存しない検知方式に変える」を選んだ。これに伴い `MaintenanceChannel.checkSignalFile` を次のように作り直した。

1. `canRead()`／`isDirectory()` による事前の門番を撤去（`dir == null` のときだけ早期return）。
2. 検知器を `new File(dir, "maintenance-open").delete()` の戻り値に変更。`true` なら合図を確定し、**削除してから** `cycle` を呼ぶ（順序を逆にすると削除失敗時に毎回 cycle してしまう、前回審査と同種の穴になるため、順序を審査観点として確認した＝OK）。
3. 旧方式の `lastModified`＋`length` による識別子の重複判定（`SchedulerStore.getLastMaintenanceSignalId` 系）を削除。削除が成功した回だけ cycle するため、二重消費が原理的に起きない構造になり、該当の複雑さごと不要になった。
4. 自己試験（`.maintenance-probe` の作成→削除の往復）を追加。成功したら `signal_channel_ok` を1回記録して以後は試験しない旗（`SchedulerStore.isSignalChannelConfirmed`）を立てる。失敗したら `signal_probe_failed` を専用の重複判定枠（`SchedulerStore.wasSignalProbeFailureRecorded`）で1回だけ記録する（旗は立てず次回また試す）。
5. `signal_unreadable` という結果名・関連する `SchedulerStore` のキー（`last_signal_unreadable`）は撤去し、意味の異なる新しい結果名・枠に置き換えた。

### 審査で見つけて直した欠陥

**試験ファイルの残骸で「経路が壊れている」と誤報する**: `probeSignalChannel` の成功判定に使う `createNewFile()` は、ファイルが既に在るときもfalseを返す（異常ではない）。試験ファイル（`.maintenance-probe`）を作った直後〜削除する前にアプリの処理が落ちる（省電力による停止・プロセス終了等）と残骸が残り、次回の試験で `createNewFile()`=false・`delete()`=trueとなって、**経路は正常なのに `signal_probe_failed` を誤記録してしまう**（次の回には確認済みで自己回復するが、その1行を見て「経路が使えない」と誤判断する恐れがある。記録に騙されないことが本作業の主題のため、潰す必要がある指摘として扱った）。

**直し**: 試験の最初に残骸の掃除としての `delete()` を1回入れ（結果は判定に使わない）、`createNewFile()` → 後始末の `delete()` の順で行うように変更した。成功判定は後ろ2つ（作成・後始末のdelete）だけで行う。`exists()`・`canRead()` 等の読み取り系の判定はここでも使っていない（この端末では読み取りが拒否されるため）。再現筋をコメントに残した。

修正後に再ビルドし、終了コード0・`[3b/8]` で `OK: classes.dex に versionName=0.24.0-stage3 の刻印を確認`、署名SHA-256（`c64146dcaca2e2fad8c8b0e37cb0eb0435be52b01f418d02f988d3e213972709`、実機と一致）を再確認した。

### 確認した点

1. **権限が増えていない**: `AndroidManifest.xml` の `<uses-permission>` に差分なし（`READ_EXTERNAL_STORAGE` 等の追加なし）。PO方針「読み取り権限は増やさない」を満たす。
2. **削除してから cycle の順序**: `checkSignalFile` で `consumed = ... .delete()` の次に `if (consumed) { cycle(...); }` という順になっており、削除成功が確定した後にだけ cycle する。
3. **重複判定の枠が分離されている**: `signal_probe_failed` の重複判定は `SchedulerStore.wasSignalProbeFailureRecorded`（専用キー `signal_probe_failure_recorded`）を使い、`ensureOpen`/`cycle` が使う `last_maintenance_channel_result` とは別枠。記録があふれる旧欠陥と同種の穴を作っていない。
4. **試験ファイルの残骸対策**: `probeSignalChannel` は掃除delete→`createNewFile()`→後始末deleteの順に行い、成功判定を後ろ2つに限定している（上記「審査で見つけて直した欠陥」参照）。読み取り系の判定（`exists()`・`canRead()`）は使っていない。
5. **版番号**: `versionCode` 26→27、`versionName` 0.23.0-stage3→0.24.0-stage3。`origin/main`（PR #5808 マージ後 25／0.22.0-stage3）および他のオープンPRと衝突しないことを確認した。
6. **ビルド自己検査が通る**: `build.sh` 終了コード0、`[3b/8]` で `OK: classes.dex に versionName=0.24.0-stage3 の刻印を確認`。`strings -a` で `checkSignalFile`・`probeSignalChannel`・`signal_channel_ok`・`signal_probe_failed`・`.maintenance-probe` の存在、および旧 `signal_unreadable`・`last_maintenance_signal_id`・`last_signal_unreadable` の不在を確認した。
7. **署名**: `apksigner verify --print-certs` の SHA-256 が実機の APK と一致（`c64146dcaca2e2fad8c8b0e37cb0eb0435be52b01f418d02f988d3e213972709`、既存の `build/debug.keystore` を再利用）。

### 未実施（この便の範囲外）

- 実機への導入（`adb install`）と実機検証（`docs/handoff/line-auto-export-app/design.md` 追補「合図検知の作り直し」の実機検証手順(a)(b)(c)）。PO の承認後に Opus が実施する。
