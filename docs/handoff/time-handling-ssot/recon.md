# 時刻の扱いのSSOT化（time-handling-ssot）— recon

> この文書は何か（専門用語なしの1行）:
> 日本時間とUTCの取り違えがなぜ3度も起きたのかを、実測した事実だけで記録したもの。

- 対象ADR: ADR-151（バックエンド全域で「今日」の基準を JST に統一）
- 関連ADR: ADR-021（J2 fix: 月次集計の JST 化）
- 実測日: 2026-09-08
- 実測時の origin/main SHA: 65b13bb8c63d66a96238957cafbd18b68c616c39
- 対象テナント: tenant_004（本番実データ）

## 1. 発端となった実害

顧客向けの在庫配信で、2026-09-08 に投稿された商品がシートに出ないという申告があった。

追跡の結果、取り込み処理の時刻の扱いに誤りがあることが判明した。詳細は §4 に記す。

## 2. 同型の誤りは3度目である

| 回 | 日付 | 出典 | 内容 |
|---|---|---|---|
| 1回目 | 2026-05-13 | ADR-021 J2 fix | 月次集計の境界がUTC基準だった。`backend/app/services/time.py` を新設して対処 |
| 2回目 | 2026-09-01 | ADR-151 | `date.today()` がUTCで「今日」を取っていた。5ファイルを名指しで置換 |
| 3回目 | 2026-09-08 | 本recon | 取り込み処理。詳細は §4 |

過去2回はいずれも該当箇所を名指しで個別修正しており、再発を止める機械的な仕組みは置かれていない。

ADR-151 の「対象」欄（`docs/adr/ADR-151-jst-date-basis.md`）には、`backend/app/routers/analytics.py`（10箇所）、`backend/app/routers/goals.py`（2箇所）、`backend/app/routers/quotes.py`、`backend/app/services/fedex_rates.py`、`backend/app/tasks/sa02_recon_monitor.py` が名指しで列挙されている。

## 3. 既存の正本と、その普及状況

### 3-1. 正本

- `docs/adr/ADR-151-jst-date-basis.md`（34行・Accepted・2026-09-01）
- `backend/app/services/time.py`（55行）— `JST = ZoneInfo("Asia/Tokyo")` と `_jst_month_range_utc()` を持つ

### 3-2. 普及していない実測

`services.time` を import しているファイルは3件のみ。いずれも `_jst_month_range_utc` 目的。

- `backend/app/routers/order_financials.py:51`
- `backend/app/routers/order_commissions.py:63`
- `backend/app/routers/analytics.py:30`

`backend/app/services/time.py` の `JST` 定数を参照しているファイルは0件。

代わりに同一定義が3箇所に重複している。

- `backend/app/routers/goals.py:41` — `_JST = ZoneInfo("Asia/Tokyo")`
- `backend/app/routers/analytics.py:34` — 同上
- `backend/app/routers/quotes.py:20` — 同上

## 4. 今回の誤り（3か所・file:line）

### 4-1. 入口: 日本時間にUTCのラベルを貼っている

`backend/app/services/tcg_line_import_svc.py:433-435`

LINEエクスポートファイル内の時刻文字列（日本時間で記録されている）を `strptime` で解釈し、`.replace(tzinfo=timezone.utc)` でUTCとして扱っている。日本時間の値にUTCの印を付けているため、保存される値が9時間ずれる。

### 4-2. 窓の計算: UTC基準の起点と日本時間の文字列を文字列比較している

`backend/app/services/tcg_line_import_svc.py:367`

`cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)` で起点を計算し、`:368` で文字列に整形。`:372` でファイル内の日本時間文字列と `>=` で比較している。

結果として、画面の「取り込み幅」が24と表示されていても、実際の窓は実行時刻マイナス15時間になる（24 - 9 = 15）。

### 4-3. 出口: タイムゾーンの印を剥がして返している

`backend/app/routers/tcg_line_import.py:156`

`created_at AT TIME ZONE 'UTC' AS created_at` により、`timestamptz` からタイムゾーン情報が失われる。`:169` の `isoformat()` でオフセットなしの文字列となり、ブラウザがローカル時刻と解釈するため、画面表示が9時間ずれる。

## 5. 実測した証跡（DB）

### 5-1. 窓が15時間である証拠

`tenant_004.import_jobs` の直近3件。

| created_at | window_start | 差 |
|---|---|---|
| 2026-09-08 02:01:26 | 2026-09-07 11:01:27 | 15時間 |
| 2026-09-08 01:01:52 | 2026-09-07 10:01:52 | 15時間 |
| 2026-09-07 14:05:04 | 2026-09-06 23:05:05 | 15時間 |

画面の入力欄は 24 と表示されていた。

### 5-2. 実行環境の時刻設定

| 対象 | 値 |
|---|---|
| DB（`current_setting('TimeZone')`） | `Etc/UTC` |
| DBの時刻列の型 | `timestamp with time zone` |
| VPS（prod1）の `date` | JST |
| 手元の `date` | JST |

DBの保存形式そのものは正しい。誤りはアプリケーション側の変換にある。

### 5-3. `source_messages` の構造（誤解の訂正記録）

`source_messages` は「メッセージ1件=1行」ではなく「仕入元1社=1行」である。取り込みのたびに、その仕入元の既存行を `is_active=FALSE` にして差し替える（`backend/app/services/tcg_line_import_svc.py:416-421` および `:462-469`）。

2026-09-08 02:01 の取り込みでは48行（仕入元48社ぶん）が作成され、01:01 の回の48行のうち46行が無効化された。

`received_at` はその仕入元の最後のメッセージ時刻を表す。日付で件数を数えると、その日に投稿した仕入元の数になる。取り込み件数ではない。

## 6. 同型候補の分類（実測・全件）

### 6-1. `replace(tzinfo=` — 16箇所

判定基準: **直前に `tzinfo is None` の確認があるか。**

安全（15箇所）: 元がUTCの値に対し、印が欠落していた場合のみ補う形。

- `backend/app/routers/meta_inbox.py:860, 877`
- `backend/app/routers/leads.py:879, 893`
- `backend/app/services/registration_token.py:140`
- `backend/app/services/messaging_window.py:63`
- `backend/app/services/google_calendar.py:203, 239, 270`
- `backend/app/services/translation_monitor.py:188`
- `backend/app/services/google_drive_oauth.py:235, 273, 304`
- `backend/app/discord_gateway/ticket_channel_writer.py:175`
- `backend/app/discord_gateway/dm_writer.py:99`

誤り（1箇所）: 確認なしに、解釈直後に決めつけている形。

- `backend/app/services/tcg_line_import_svc.py:435`

### 6-2. `utcnow()` — 4箇所

Python 3.12 で非推奨。タイムゾーン情報を持たない値を返す。

- `backend/app/routers/customer_priority.py:126, 243`
- `backend/app/routers/inventory_offers.py:162`
- `backend/app/services/priority_scoring.py:407`

### 6-3. `AT TIME ZONE` — 3箇所

- `backend/app/routers/tcg_line_import.py:156` — `'UTC'`。印を剥がしている（誤り）
- `backend/app/services/tcg_distribution_svc.py:210` — `'Asia/Tokyo'`。正しく変換している
- `backend/app/services/time.py:16` — コメント。SQLite テストで動かないため Python 側で変換する方針の記述

### 6-4. `strptime` — 4箇所

- `backend/app/services/inventory_aggregation.py:140, 162`
- `backend/app/services/fedex_rates.py:479`
- `backend/app/services/tcg_line_import_svc.py:433`（誤り。6-1と同一箇所）

### 6-5. `datetime.now(` — 40箇所

うち `ZoneInfo("Asia/Tokyo")` または `_JST` を使うもの: `backend/app/routers/goals.py:45`、`backend/app/routers/analytics.py:39`、`backend/app/routers/quotes.py:191`、`backend/app/tasks/sa02_recon_monitor.py:50`、`backend/app/services/fedex_rates.py:417`。

残りは `timezone.utc` を指定しており、単独では誤りと断定できない。誤りとなるのは §4-2 のように日本時間と比較する場合のみ。

## 7. 静的検査の見本

`backend/tests/test_tcg_schema_qualification.py`（148行）が、同じ型の静的検査として既に稼働している。

方式: ソースを正規表現で読み、`text(...)` の引数文字列を抽出して、テーブル名にスキーマ修飾があるかを確認する。DB接続を要さず、既存の `pytest` 環境でそのまま動く。

時刻の検査も同じ骨組みで書ける。

## 8. 未解明の事項（本reconの時点で確定していない）

- 2026-09-08 02:01 以降の投稿が `source_messages` に反映されなかった理由。窓の起点は 09-07 11:01 であり、文字列比較でも通るはずだが、実測では 01:37 が最新だった。9時間のずれだけでは説明がつかない。
- 2026-09-08 10:00 に実施された取り込み操作が `import_jobs` に記録されていない理由。同時刻に同一内容のファイルがアップロードされ、`raw_sha256` による冪等化で `already_imported` として弾かれた可能性があるが、アップロードされたファイルの実体を確認していないため確定していない。

## 9. 別テーマとして予約したもの

- **抽出結果の履歴保持**: 過去のメッセージから抽出した価格と在庫データをログとして蓄積する。`source_messages` の1社1行・上書き方式は維持する。PO決定 2026-09-08。
- **crm-app 構造への移植検討**: 営業CRM側のDB構造を別リポジトリ（GEN-RYU-System/crm-app）の構造へ移植する検討。TCG解析パイプラインは crm-app にパーサーが無いため salesanchor 側で構造化する、とPOが決定（2026-09-08）。

## 10. guards.md への記載について

並行セッション（design-partner-card-ops）と協議のうえ、**記載しない**と決定した（2026-09-08）。

理由: guards.md の対象は「カードを出すときにどこで止まるか」であり、収録済みの事例はすべてガード・フック・関所・実行役の挙動である。アプリケーションコードの規約を入れると、作業の種類で引く §0 の対応表の構造が崩れる。

同種の規範は `docs/handoff/design-partner-card-ops/guards/00-common.md` に一般形（実行環境の値を実測せずにカードへ書かない）として既に存在する。
