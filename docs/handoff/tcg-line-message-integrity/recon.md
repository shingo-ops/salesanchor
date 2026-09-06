# LINE メッセージ整合性 recon（2026-09-06）

対象: tenant_004（本番）。調査は読み取りのみ。書き込みなし。
根拠: CARD-RECV-RECON-01〜09 の生出力（/tmp/CC報告ファイル/recv01〜09.txt）。
origin/main = 367ace2b（調査中に不変）。

## 1. 発端

配信先スプレッドシート「在庫集計」の投稿日時列に、値のある行と空欄の行が同一仕入元で混在する。
ビューアの「24時間以内のみ表示」で日時なし行の扱いを決める必要があった。

## 2. 確定した事実

### 2-1. DDL（recv01）
- 経路: analysis_results.extraction_item_id → extraction_items.id → extraction_job_id → extraction_jobs.id → source_message_id → source_messages.id → supplier_channel_id → supplier_channels.id → supplier_id → tcg_suppliers.id
- source_messages.supplier_channel_id は NULL 許容（ON DELETE SET NULL）。received_at は timestamptz・NULL 許容。
- extraction_jobs.source_message_id は NOT NULL・source_messages 参照。

### 2-2. received_at NULL の分布（recv02）
- is_active=TRUE の解析行のうち received_at NULL は 144 行・10 メッセージ・10 仕入元（全 56 仕入元中）。
- NULL 行の created_at（JST）はすべて 2026-08-30。10 件とも 2026-08-30 11:13:22.005976+00 の同一時刻。
- is_active=TRUE のメッセージ総数 70、うち NULL 10、supplier_channel_id NULL 0。
- 引き継ぎ資料の「306 件・09-04」は MIGRATION_LOG.md:252-258（2026-09-02 時点の全件）を指し、母集団が異なる。

### 2-3. 有効メッセージの並存（recv04〜06）
- 同一 supplier_channel に有効メッセージが 2 件以上残る channel は 3 本・9 件: SP0143（4 件）、SP0067（3 件）、SP0136（2 件）。3 仕入元とも channel は 1 本のみ。
- 各 channel とも 2026-08-30 11:13:22 の 1 件（received_at NULL）と、2026-09-04 07:54:11.079532+00 の同一瞬間に挿入された 1〜3 件が並存。
- 09-04 挿入分の extraction_jobs は prompt_version=name-first-v2、5 件中 3 件が pending（抽出未実行）。
- 09-04 挿入分の received_at は +00 で保存されている。

### 2-4. 取込コードの挙動（recv03・06・08）
- backend/app/services/tcg_line_import_svc.py（origin/main）: 1 取込につき仕入元ごとに timestamp 最新の 1 件のみ採用（299-304、ca0c4f98 SQR-05）。その channel の既存有効メッセージは全件 is_active=FALSE にする（361-411）。順序は INSERT が先・UPDATE が後（a87ab9c1）。
- 302: received_at には sorted_msgs[0]["timestamp"]（最古の投稿時刻）を保存している。採用する本文は最新投稿。
- 375-379: received_at の文字列解釈に失敗すると None で挿入する。
- 343-357: 有効な line channel が無い仕入元は挿入も supersede もせず continue する。
- 同ファイルが origin/main に初めて入ったのは 58b6d441（2026-09-05 06:16 JST）。09-04 07:54 UTC の書き込みより後。
- feat/tcg-migration-phase4 上の版（282a65ae、2026-08-30）も supersede を持ち、1 グループ 1 件で書く。received_at は UTC 保存、SQL はスキーマ修飾なし。

### 2-5. 書き込み主体の追跡（recv05・07・09）
- source_messages への INSERT を持つコードは main 上で 2 箇所: tcg_line_import_svc.py:384、tcg_migration/scripts/ingest_to_prod.py:216。
- 09-04 07:54 UTC に同一 channel へ複数件を並存させる挙動は、main のどの版でも phase4 版でも生じない。
- docs/handoff/tcg-received-at-jst/design.md:12 に手動スクリプト tcg_line_ingest.py の記載があるが、全参照の git 履歴にコードとして存在せず（94c5c719 の文言のみ）、本番サーバーの /home/ubuntu・/opt・/srv（深さ 6）と .bash_history にも出現しない。
- DEPLOY_LOG.md に 09-04 の取込サービス配備記録なし。
- 結論: 09-04 の並存を書いた主体は特定不能。追跡は打ち切り（PO 判断、2026-09-06）。

### 2-6. 配信 SQL（recv03・04）
- tcg_distribution_svc.py:229 sm.is_active=TRUE、230-231 supplier_channels を内部結合、238-241 WHERE pid_resolved AND unit_resolved AND price_normalized IS NOT NULL AND cond_filter。
- したがって 2-2 の 144 行は配信に出る日時なし行の上限。

## 3. 決定事項（PO 合意、2026-09-06）

- 原因追跡は打ち切り、掃除と再発防止の設計に移る。
- 掃除で残す 1 件: channel ごとに received_at 最新の 1 件（NULL は最古扱い、同値なら created_at 最新）。残す 1 件が未抽出なら掃除前に抽出を実行する。
- 再発防止: source_messages に「1 channel につき有効な在庫投稿は 1 件」を DB で強制する（部分排他制約 DEFERRABLE INITIALLY DEFERRED を候補）。tenant_006 で実測してから本番。
- 〆（売り切れ）投稿の設計は本テーマに統合する。在庫投稿と〆投稿は同一取込内で両方を保持し、〆は Gemini で抽出後にシステムが商品 ID で除外判定する。在庫投稿より前の〆は無視する。
- 〆投稿の格納先は未決（source_messages に種別列を足す形が有力。別テーブルは extraction_jobs の参照先の問題がある）。

## 4. 未確認・要実測

- SP0136 の 09-04 メッセージの抽出状態と本文長。
- 取込の 24 時間窓（window_start）の判定コード。
- 採用した本文（raw_text）に何を入れているかの行（302 の received_at との対応）。
- 09-04 挿入分の prompt_version が name-first-v2 になっている経緯（挿入時は NULL の設計）。
- 〆セッションの recon.md（未受領）。

## 5. 見なかったもの

- コンテナ内・/tmp・他ユーザーのホームの探索。
- git branch -r の中間部（表示上折りたたまれた範囲）。
- 09-04 以降の取込ファイルに 08-30 残存 7 仕入元が登場したか。
