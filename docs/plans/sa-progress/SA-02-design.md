# 設計doc — SA-02 会話ログ＋会社集計ビュー（contact粒度）

| 項目 | 内容 |
|------|------|
| 発行日 | 2026-06-11（Planner: Web Claude） |
| 状態 | 設計確定（KGI承認 2026-06-11／J1〜J4判断 2026-06-11 すべてShingo決定済み） |
| 相互参照 | ADR-096（対象）・ADR-095（原則）・**recon**: `docs/handoff/sa-02-stage1/recon.md`（file:line差分表＝`docs/plans/sa-progress/SA-02-plan.md` §3）・ADR-088/110/ADR-SA-17（翻訳）・ADR-119（lead_channels） |

---

## 1. 目的（Why）

全チャネルのやり取りを1本の会話ログ（conversation_logs）に集約し、顧客カルテと会社集計ビューで「会話数・最終会話日時」が自動で正しく出る状態を作る。reconの結論：**テーブル・集計VIEW・翻訳基盤・監査ログは既存流用可、不足は「配線」と「画面」**。

## 2. 確定済み判断（この設計の前提。変更はShingo承認が必要）

| # | 判断 | 決定 |
|---|------|------|
| KGI | G1a/G1b/G2/G3/G4 | 承認済み（SA-02-plan.md §2） |
| 手動記録 | 1メッセージずつ／スレッド欄チャット風入力／編集可＋履歴＋再翻訳／翻訳・解析必ず適用／1チャネル＝1入口の排他 | 確定 |
| J1 | エコー受信（アプリ外送信の自動記録） | **ON**。メッセージIDで重複排除 |
| J2 | meta_messages の過去メッセージ | **全件移行**。既存翻訳の紐づけを維持。移行の本番実行は**Shingo明示GO必須** |
| J3 | 手動記録の削除 | **論理削除**（ゴミ箱方式）。誰がいつ消したか残す。集計から除外。物理削除なし |
| J4 | 会話要約 | **v1見送り→v2**。v1のG2対象は会話数・最終会話日時 |
| v2送り | AI分割（まとめ貼り付け）／スクショ読み取り／会話要約 | 確定 |

## 3. v1スコープ（What）— recon「不足6項目」に判断を反映

1. **webhook→conversation_logs配線**：全連携チャネルの受信＋エコー受信（送信分）を保存。メッセージIDによる冪等・重複排除。
2. **過去メッセージ移行**：meta_messages→conversation_logs全件。message_translationsの紐づけ維持。再翻訳しない。移行はmigration＋検証スクリプトで、**本番適用は別途GO**。
3. **手動記録**：保存・編集（record_audit_log流用で履歴）・論理削除のAPI＋スレッド欄常設のチャット風入力UI。保存時にtranslate_inbound（即時翻訳・解析）を発火。編集時は再翻訳。
4. **チャネルマスタ**：「電話」「対面」等の手動チャネルをテナント単位で追加可能に。連携状態（自動/手動）を持ち、**入力ボックス表示の判定はチャネル単位**（1チャネル＝1入口）。
5. **会社→contact集約ページ**：v_company_stats流用。会社を開く→所属contactの会話が1画面に集約→3クリック以内で原文＋訳文。
6. **InboxMessageThread改修**：手動／自動の時系列混在表示、手動バッジ＋記録者名、重複ガード（同一チャネル・近接日時・同一本文の保存前警告）。

## 4. 弊害対策（ポカヨケ）

- **二重記録**：入口排他（連携チャネルに手動入力ボックスを出さない）＋メッセージID冪等＋保存前重複警告の三重。
- **派生値の汚染**：会話数・最終会話日時はVIEW/集計のみ。書き込み可能な手入力経路を作らない（K2で監視）。
- **誤テナント**：既存RLS境界内で完結。テナント横断の参照を追加しない。
- **移行事故**：移行は件数突合（旧＝新）と無作為抽出の照合を伴う検証スクリプト必須。失敗時ロールバック手順を先に用意。

## 5. KPI（確定）

| # | KPI | 目標 | 測り方 |
|---|-----|------|--------|
| K1 | 受信→会話ログ保存率 | 100% | webhook受信数と保存数の突合（sweeperの回収発生を計測） |
| K2 | 派生値への手入力経路 | 0箇所 | コードレビュー＋DB権限で担保（SA-01チェック#2） |
| K3 | 会社→原文＋訳文の到達 | 3クリック以内 | UIレビュー（検証ゲート） |
| K4 | 取りこぼしの自動回収 | sweeper周期内に回収 | 既存sweeperの周期・ログを流用（周期値は実装時に既存設定へ合わせる） |
| K5 | 手動記録の所要 | 1メッセージ1分以内 | 検証ゲートでの実測 |

## 5b. 受け入れ基準（process-artifacts gate 用）

| 基準 | 検証方法 |
|------|---------|
| Meta Messenger/Instagram の受信が conversation_logs に保存される | `pytest backend/tests/test_conv_log_writer.py` + CI pytest-run-internal |
| Discord DM の受信が conversation_logs に保存される | `pytest backend/tests/test_discord_inbox.py::test_dm_writer_creates_new_lead` |
| external_message_id 重複で ON CONFLICT DO NOTHING が動作する | `pytest backend/tests/test_conv_log_writer.py::test_write_conversation_log_duplicate_returns_none` |
| エコー受信（is_echo=True）が direction='outbound' で conv_logs に保存される | webhook.py `_iter_inbound_messages` のエコー分岐確認 + CI |
| channel_masters テーブルが作成され RLS が適用される | `マイグレーションSQL 実行テスト（実DB）` CI ジョブ |
| 失敗時にチャネル・ext_id 付きエラーログが出力される | `pytest backend/tests/test_conv_log_writer.py::test_direction_values_in_callers` |

## 6. 実装の段階分け（提案。PR分割はGenerator裁量、ゲートは各PRで通す）

| 段階 | 内容 | 本番適用条件 |
|------|------|------------|
| 段階1（土台） | チャネルマスタ＋webhook配線＋エコーON＋冪等 | CI緑で進行可 |
| 段階2（移行） | 移行スクリプト＋検証 | **本番適用はShingo明示GO必須** |
| 段階3（手動記録） | API＋スレッドUI＋翻訳発火＋論理削除 | CI緑で進行可 |
| 段階4（集約ビュー） | 会社→contact集約ページ＋スレッド混在表示 | CI緑で進行可 |

## 7. 外部・過去事例

- **HubSpot/Salesforce**：未連携チャネルは「アクティビティを記録」で同一タイムラインに手動記録（本設計と同型）。
- **Meta message_echoes**：エコー＋message id（mid）冪等は外部実装の標準手法。
- **社内過去事例**：翻訳sweeper（ADR-SA-17）の「取りこぼし後追い回収」を受信全般に流用。FedEx Stage 1で確立したsmoke監視の型をK1計測に流用。

## 8. 継続（リリース後）

- K1/K4をsmoke・ログで常時計測。回収発生が続くチャネルはアラート（既存Discord通知の型）。
- 手動チャネルの記録漏れは機械検知不可＝運用ルール（v2でN日無記録のうながし表示を検討）。

## 9. ゲート・GO条件

- 通常のUI・ロジックPR：CI緑→マージ→本番デプロイまで進行可（2026-06-10合意の線引き）。
- **migrations（段階2の本番適用）のみShingo明示GO必須**。
- 全段階完了後：KGI実測＋SA-01横断チェック→進捗100%。

## 10. 並走期間の定義（meta_messages と conversation_logs の二重書き）

段階1デプロイ〜段階2移行完了・読み取り切替までの間、両テーブルに同じ受信データが書かれる。
この「並走期間」の管理基準を以下に定める。

### 日程表

| マイルストーン | 日付 | 備考 |
|--------------|------|------|
| **並走開始** = 段階1本番デプロイ日 | _(デプロイ後記入)_ | PR #1932 本番反映日 |
| 段階2引っ越し完了（全件移行＋検証一致） | _(予定未定)_ | Shingo 明示 GO 後に実行 |
| 読み取り切替完了（inbox/API が conv_logs を参照） | _(予定未定)_ | 段階4完了時 |
| **廃止判断日** = 読み取り切替日 ＋ 14日 | _(自動算出)_ | 14日連続で不一致0を確認後 |
| 廃止実行（meta_messages DROP / 旧パス削除） | _(予定未定)_ | PR起案→Shingo GO で実行 |

### 日次自動突合

- **内容**: meta_messages と conversation_logs の当日新規件数を毎日突合し、差異があれば Discord 通知する。
- **実装**: 既存の `translation_monitor.py` sweeper 型の軽量 Celery beat タスク（または cron ジョブ）。本 PR への同梱または別 PR は Generator 裁量。
- **通知フォーマット（例）**:
  ```
  [SA-02 並走監視] 2026-06-12
  meta_messages 当日新規: 42件
  conversation_logs 当日新規: 42件
  差異: 0件 ✅
  ```
- **差異検知時**: WARNING ログ + Discord 通知（`send_discord_notification` 既存パターン流用）。差異件数・チャネル別内訳を含める。

### 終了条件（3つすべてを満たすと並走終了）

1. 段階2（meta_messages→conversation_logs 全件移行）完了 + 件数突合一致
2. 読み取り切替完了（受信箱・API が conv_logs のみを参照）
3. 切替後14日連続で日次突合の差異が0件

### 廃止手順

1. 終了条件3つが揃ったら廃止判断日を記録
2. PR 起案: `meta_messages` DROP migration + webhook/dm_writer からの二重書きコード削除
3. Shingo GO → マージ → 本番デプロイ
4. 物理削除後は本ファイルの日程表に「廃止実行」日を記入してクローズ
