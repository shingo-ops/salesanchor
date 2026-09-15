# 完売ルール管理 — 本番DBとコード接続の照合記録

> 今あるデータのつながりと処理の順番を実物で確認し、安全に接続する位置を特定した記録。

親: [提供元フィード翻訳](../../specs/inventory-management/feed-translation/README.md)。設計: [詳細設計案](sold-out-rules-design.md)。業務合意: [引き継ぎ正本](sold-out-rules-handoff.md)。
観測日: 2026-09-15、記録時刻06:13:02Z。コード基点 `origin/main=189cd3386caf37bf66233d48bc481a2420ef95da`。製品変更/DB書込/新しいGemini要求0回。

## 1. 調査方法と範囲

SSHの既存prod1接続で稼働コンテナ名を確認し、backendとcelery-worker内からアプリが実際に使う接続設定でDBカタログをSELECTした。接続時に `default_transaction_read_only=on`、`statement_timeout=5000` を設定し、transaction_read_only=onを実確認。URL/パスワード/APIキーは出力せず、原文/個人情報も取得・掲載しない。DB権限を変更したのではなく、今回の接続を読み取り専用にした。

DB照会はpg_namespace/pg_class/pg_roles/information_schema.columns/pg_constraint/role_table_grants/pg_triggerと、既存状態ルール・実行記録の集計に限定。件数は観測時点であり、今後の固定値/seed条件にしない。これは実DB上の読取調査であり、移行や新機能の動作試験ではない。

## 2. 本番実物の観測

| 項目 | 結果 | 意味/制限 |
|---|---|---|
| DB | jarvis_db、PostgreSQL16.13 | 実接続先を確認 |
| アプリ接続role | backend/workerともsalesanchor_app | superuser=false、bypassrls=false、createrole=false |
| 対象schema | 両コンテナTCG_SCHEMA=tenant_004 | リクエストから任意schemaを渡す設計にしない |
| 自動解析設定 | backend未設定、workerはTCG_AUTO_ANALYZE=1 | backend側だけ見て自動解析停止と判断してはいけない |
| schema所有者 | tenant_001/003/004/005/006はいずれもjarvis | アプリroleではなくmigration側の所有者 |
| 既存対象表の所有者 | 確認したtenant_004の7表すべてjarvis | 新版の表も既存のDDL実行経路から作る |
| 既存対象表の権限 | salesanchor_appへSELECT/INSERT/UPDATE/DELETE、grant不可 | 既存権限の流用だけでは履歴不変を保証しない |
| schema CREATE権限 | public/tenant_001/tenant_004ともsalesanchor_appはfalse、USAGEはtrue | 管理画面の保存処理で表を自動生成しない |
| 対象7表のRLS/独自trigger | RLS=false、独自trigger0 | 新履歴の改変拒否は新しい契約・試験が必要。現状で保護済みとしない |
| 新版用sold_out_%表 | カタログで0 | 既存新版テーブルがあるという前提を置けない |
| 状態マスタ | tenant_004は9行、全enabled、除外語欄は全空 | 完売5・予約3・既定1。tenant_001には同名表なし |
| 原文/抽出job/明細/解析 | 1527 / 1528 / 31676 / 31676行 | jobは原文1件につき複数を許す。数だけで一対一としない |
| 関連切れ | job→原文0、明細→job0、解析→明細0 | LEFT JOIN/IS NULLによる観測。今後はFKで維持 |
| 既存モデル実行記録 | 64件、requested_model=gemini-3.6-flash、prompt_version=raw-extraction-v4-work-id-p2 | 既存記録。今回モデル呼出しは0 |
| 既存抽出所要時間 | completed63件平均37.28秒、failed1件44.97秒 | finished_at-started_at。モデルだけの時間でも、新完売判断の予測時間でもない |
| SDK | backend/workerともgoogle-genai2.8.0 | workerでGenerateContentConfigのresponse_mime_type/response_json_schema/response_schema/temperature欄を実物確認。モデルの対応/意味精度は未試験 |

対象7表: source_messages、extraction_jobs、extraction_items、extraction_attempts、analysis_results、tcg_status_master、audit_log。

### 稼働ファイルの同一性

backendとworker内の下記5ファイルをSHA256で読み、origin/mainの同ファイルと全5件一致した。10比較=10一致。稼働コンテナのファイルの照合であり、プロセス内部メモリを取得して照合したものではない。

| ファイル（backend/配下） | SHA256 |
|---|---|
| app/tasks/tcg_extraction.py | 6aa489551600a3693d98ce3c1289c98aff92f320940981fc65464e5db18d3404 |
| app/services/tcg_analyzer_svc.py | 5be6c9ac3aaa42813c98dfd8cd46c2ba5c14b101aa1c7d2ef8f0feaeb2afb452 |
| app/services/gemini_extraction_svc.py | 6bdf1da975f1231853c6652e71ac7d3504a697c4b36e7b3fc1d483f425ba7cd7 |
| app/services/tcg_extraction_record_svc.py | 4d255b7ce95bd87b4a4f7accd4dd88a40371cc667bd3b61395ad861a394cc669 |
| app/services/tcg_line_import_svc.py | 58072ed34f26ddd2a5504e2aa5e05d0017dc3611a93112d415f8a7fffa53f0b7 |

## 3. 既存DBの接続契約

- source_messages.id UUID → extraction_jobs.source_message_id（FK、ON DELETE CASCADE）。原文はraw_text、投稿日はline_posted_at。仕入元はsupplier_channel_id FK。仕入元削除時はSET NULL。
- extraction_jobs.id UUID → extraction_items.extraction_job_id（FK、CASCADE）。明細はid UUID、line_start/end、raw_*の抽出値とresolved_work_id。
- extraction_items.id → analysis_results.extraction_item_id（FK、CASCADE、UNIQUE）。商品参照はpublic.products.tcg_uuidへのFK。商品テーブルを複製しない。
- extraction_attempts.extraction_job_idもjobへのFK/CASCADE。完了phaseにはinput_payload/response_text/parsed_items/item_count等のCHECKがある。
- audit_logのold_values/new_valuesはTEXT、record_idはUUID、changed_byはVARCHAR。既存にルール版へのFKはない。

新しい通常完売runは既存job/source/itemのIDを参照する。テスト原文/正解は別目的のテスト集合として持ち、実原文表や実jobをテスト用に複製しない。元原文の物理削除が既存jobへ連鎖するため、新記録のFKをRESTRICTにして既存削除を突然止めるかCASCADE/保持するかは、記録保管要件と一緒に確定が必要。未確定で勝手にON DELETEを選ばない。

## 4. 実コードの順番と接続位置

| 順 | 実装位置（固定基点） | 実際の処理 |
|---|---|---|
| 1 | tcg_line_import_svc.py:370-445,693-704 | 原文重複を確認し原文/jobを作り、Celeryへsource IDを送る |
| 2 | tcg_extraction.py:117-155 | pending jobとraw_textを読取、作品/商品参照をDBから作る |
| 3 | gemini_extraction_svc.py:198-216; tcg_extraction_record_svc.py:57-91 | コードの抽出指示+DB参照+原文で送信内容を組立、実送信前にattemptを保存 |
| 4 | tcg_extraction.py:170-197 | Gemini抽出の原文根拠/作品参照の変更を検証 |
| 5 | tcg_extraction_record_svc.py:143-161; tcg_extraction.py:199-270 | 明細UUIDを割当、items/job/attemptを同一commitで確定 |
| 6 | tcg_extraction.py:273-284 | workerのTCG_AUTO_ANALYZE=1ならanalyze_extraction_jobを呼ぶ |
| 7 | tcg_analyzer_svc.py:1195-1220,1240-1257 | 原文/job/itemをFOR SHARE、既存解析行をFOR UPDATE。商品手動訂正があれば通常の自動上書きをskip |
| 8 | tcg_analyzer_svc.py:1328-1357,1364-1430 | ステータス決定、確認理由の統合、解析結果UPSERT |
| 別入口 | tcg_product_master_svc.py:616-644,694-708 | 手動再解析。退避履歴を保存して同じanalyzerを呼ぶ。workerだけ直すとこの入口が旧判定のままになる |

### 根拠から導いた接続案

1. 新しい完売runの準備/モデル通信は、抽出明細をcommitした**後**、analyzerを呼ぶ**前**に置く。analyzerのDBロック中にネットワーク通信を置かない。
2. 完売runはpolicy版・job・source hash・明細ID集合を先に保存して通信し、返答を検証してから完了にする。判定欠落/未確定では通常解析へ進めず、抽出完了と完売判断未完了を別の状態として記録する。
3. analyzerへ検証済みsold_out_run_idを明示して渡す。ロック取得後にjob/source hash/明細集合を再照合。旧resolve_status_v2のEXCLUDEを新しい判断に重ねない。既存の予約/既定OUTPUTとは責任を分ける。
4. 手動再解析は有効な完売runを照合して利用し、未準備なら明示エラーとする案。既存手動操作へ無断でモデル呼出しを追加しない。通常/手動の2入口と、analyzerへのrunなし直接呼出しを試験する。
5. 商品手動訂正のskip分岐を保持するだけでは、その明細の新しい完売判断も反映されないことが分かった。商品/数量等の手動値を維持しつつstatus/確認理由だけを扱う接続契約が必要。独断でcontinueを削除して全項目を再解析しない。
6. tcg_condition_review_svc.py:133-161は既存review_reasonsを統合する。新しい完売確認理由をここへ正しく渡し、tcg_analysis_review_svc.py:75-94の既存確認待ち条件に残るかを検証する。新しい人間確認ページは今回作らない。

原文が0明細でemptyになる経路では、既存はanalyzerを呼ばない。完売だけの原文が抽出されない場合も自動で成功とせず、未割当原文として検知する契約が必要。価格/数量欠落だけで原文を捨てないが、商品IDを作って補完もしない。

## 5. 現行判定の限定再現（Geminiなし）

本番ファイルからASTでload_status_master/_match_status_pattern/resolve_status_v2だけ取り出し、本番DBの9ルールを読み取り専用で取得して実行した。モデルもDB書込も行わない。抽出/フィールド正規化/原文全体の精度試験ではない。

| 入力欄・人工例 | 現行結果 |
|---|---|
| 状態: 完売 | Sold out / excluded |
| 状態: 完売ではありません | Sold out / excluded |
| 状態: 予告なく完売となる場合があります | Sold out / excluded |
| 備考: 予告なく完売となる場合があります | In Stock / null |
| 状態: 〆 | In Stock / null |
| 状態: 一旦ストップ | In Stock / null |

loaderの返却にexclude_patternなしを実確認。これだけで「原文全体の正答率」を計算しない。DBに除外列があるだけでは効果がなく、旧判定と新しい完売判断を重ねる設計は誤判定を残す。

## 6. 現在の設計から必要な修正・残る条件

- T01の所有者/権限/表/キーは実確認済み。アプリroleでCREATE不可のためmigration必須。既存表にRLS/改変拒否がないので新版/監査の不変性を新たにDBで保証する。
- QAのtenant_001にはtcg_status_masterがない。新実行設定から旧マスタへ無条件FKを張る前案はこのschemaで成立しない。前提整備または旧参照をなくす設計変更が必要。初期値のハードコードで解消しない。
- T02の呼出位置は具体化できたが、原文削除の参照保全、手動訂正明細、empty原文、失敗後の再実行まで未確定。新しい完売run失敗を完了済み抽出jobのerrorへ戻すと再抽出を重ねるため流用しない。
- T03はSDK2.8.0のフィールド実在とモデルの既存64要求を確認。ただし新しいJSON契約での実モデル対応・追加コスト/遅延は未試験。37.28秒を追加時間の見積りには使わない。
- tenant.py:1629以降の新tenant作成はadmin_dbによるDDL、scripts/db/sync_tenant_schema.pyはtenant_004を基準にする。新表/不変制約/権限が新tenantでも同じになることは新migration試験で確認する。既存同期のコメントだけで保証しない。
- 今回の完売管理ページはsource_messages.is_activeの採用方式を変えない。現行import:388-395,427-437は同仕入元の旧有効原文を非アクティブ化する。ページ完成だけで「他商品在庫の維持」全体を達成したと報告しない。

自己審査: REVISE継続。基礎のDB整合と接続箇所は観測事実で示せた。残る契約を閉じる前に実装/本番GOへ進めない。削除時のテスト条件Q24はPO未回答のまま保持する。

## 7. 調査中の保護チェック

権限を確認するSELECTの別名と、コード検索文字列に削除操作の語が含まれ、保護チェックが不可逆操作として拒否した。SQLは実行されていない。許可解除は使わず、information_schema.role_table_grantsの読取と必要箇所のgit showへ変更して確認できた。保護設定/権限の変更0。
