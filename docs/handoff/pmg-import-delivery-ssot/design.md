---
mode: handoff
---
# インポート・解析・配信の統合設計と第1段階

この文書は、取込から配信までを一画面で確認するための設計と、最初の実装範囲を記録する。
親: [商品マスタ](../../specs/product-master/README.md)
recon: docs/handoff/pmg-import-delivery-ssot/recon.md
対象ADR: ADR-113, ADR-154, ADR-072
日付: 2026-09-10


> 現在地: 切替中の配布保留方針と、根拠確立後のページ作成はPO承認済み。末尾の既存API接続ページをTerraが実装済み、rootがコード差分・模擬API試験・PC/狭幅画像を確認済み。新解析実行記録・永続配信履歴・本番切替の設計はREVISEを継続。ページ接続PR #3416はマージ・本番反映済み（末尾の完了記録）。

## PO合意と範囲

POは「同じ仕入元・実際の投稿日時・本文が完全一致した場合だけ、同じ投稿として再利用する方針でよいですか？」への回答として「合意」と発言した（2026-09-10 本セッション）。
この合意は投稿同一性の条件に対するもの。マージ・本番適用のGOではない。
最初のPRは仕様登録・追加migration・取込関連・共通進捗とページ付き明細API・テスト。
解析attempt記録、配信履歴、UI、NOTE_JA変換・全件再解析は後続。

## 第1段階の実装契約

- source_messages.line_posted_at TIMESTAMPTZ nullable を追加。新規取込の採用本文に対応する実際のLINE投稿日時をJSTで保存。既存received_atと旧データは変更しない。
- 同一supplier_channel_id・line_posted_at・SHA256で候補を引き、本文の完全一致も確認。本文ハッシュ単独で同一としない。旧行のNULL日時を推測で補わない。
- 再利用は本文・商品・抽出ジョブを新設せず、旧版のis_activeやsuperseded_byを変更しない。failedジョブの再実行にも転用しない。
- 複合一意索引とsupplier_channelsの行ロックで投稿作成を直列化。仕入元コード順でロック取得。取込ファイルはschemaとSHAを含むトランザクション単位のロックで同時重複を防ぐ。
- import_jobsを先にINSERTし、投稿・import_job_messages・messages_linked_atを同一トランザクションで確定。queueはcommit後。保留確定はimport_jobs行をFOR UPDATE。再度の確定は従来どおり409、増殖なし。
- import_job_messagesは(import_job_id,source_message_id)主キー、同一schema内の2外部キー、created/reused CHECK、逆向き索引。初回の区分を再試行で上書きしない。
- 有効LINEチャンネル欠落時は確定させない。関連が欠けた状態をcompleteにしない。
- GET /tcg/line-import/{id}/progress および /items は既存require_super_adminと設定済みTCG_SCHEMAを継承。利用者指定schemaは受け付けない。TCGは既存の中央管理対象であり、一般テナントユーザーには403。
- progress/itemsとも単一SQLのCTEで取得し、レスポンス内で同一snapshotを使う。scope・as_of・coverageを返す。別リクエストの時点が違えば件数が変わり得る。
- coverage=completeはmessages_linked_at非NULL。それ以外はpending_review/discarded/legacy_unknownを区別し、工程件数はnull。completeかつ0件のみ対象なし。
- extractionはジョブ単位のstatus別集計。errorと残存商品・結果を併記。analysisは商品単位の現在結果・needs_reviewを表示し、実行状態や成功数は未記録としてnull。
- itemsはoffset>=0、limit=1..100、filter=all/needs_review/extraction_error、安定したcreated_at/id順。空ページでも総数を返す。NOTE_JAは現行値。

## 適用と戻し方

追加migrationはTCGのimport_jobs/source_messagesが存在する全tenant_NNN schemaを走査する。既存の対象はtenant_001/004。TCGのない一般CRMテナントにTCG表を新設しない。
新規テナントの汎用作成関数はTCGを作らない。将来TCGを有効化する場合、既存のTCG初期DDL適用後に本migrationを再実行する。これをローカルPostgreSQLの後発schemaで検証する。
本番SQLは実行しない。戻す場合はアプリを前版に戻し、新規表・列・履歴は保持する。

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 同じ投稿の別ファイル再取込は投稿1、関連2。別日時・別本文は別投稿 | 実PostgreSQLテスト |
| 同時取込・同時保留確定・再試行で増殖しない | 独立DB接続による競合テスト |
| 保存途中失敗で取込・投稿・関連を残さずqueue起動なし | ロールバックとqueue spy |
| 旧取込不明とcompleteの0件を区別 | progress/itemsテスト |
| error57ジョブ・残存結果166件を成功扱いしない | 同型の合成データで集計テスト |
| 複数理由でも要確認商品は1件、NOTE_JAを返す | 明細と集計の突合 |
| 一般ユーザー・別schemaのIDを参照できない | 認証とschema分離テスト |
| 既存・後発TCG schemaに同じ制約が存在 | information_schema/pg_constraintと再適用テスト |

## 外部・過去事例の参照と我々への応用

外部導入事例は該当なし。既存DB関連の追加であり、成功率を外部事例から推定しない。
Context7は本セッションで利用不可。代替として[PostgreSQL 16 snapshot仕様](https://www.postgresql.org/docs/16/transaction-iso.html)と[ロック仕様](https://www.postgresql.org/docs/16/explicit-locking.html)を確認。
既存tcg-import-fk-order-fix PR #3296のINSERT後supersede順を維持する。

## 弊害・トレードオフ

旧データは同一性が証明できないため、新ファイル取込時に旧行を再利用できない。同一チャンネルの同時取込はロック待ちになる。本文ハッシュ衝突は一意制約エラーとなり、誤再利用しない。
LINEエクスポートの時刻精度は分。同じ仕入元が同じ分に完全同文を2回投稿した場合は、この合意条件では区別できない。

## 設計審査

APPROVE（第1段階の設計）。同一AIによる自己審査であり独立した第二者レビューではない。
根拠: 現行の保存日時の不一致を追加列で分離し、PO合意条件・既存本文SSOT・非後付けの境界を満たす。APIの不明状態と工程単位を明記し、受入条件を実DBテストへ対応付けた。
実装・テストの合格や本番GOを意味しない。第3〜5便の配信外部結果照合等は未解決のまま後続に残す。

## 維持の仕組み

- 守り手: .github/workflows/migration-guard.yml
- 対象: migration登録漏れ。動作は追加PostgreSQLテストで守る。
- 人手で守る: TCG新規有効化時の適用手順と、独立レビュー・本番GO。

---
## 引き継いだ総合仕様v1（以下は原文）

# インポート・解析・配信 総合画面 — 実装仕様 v1

状態: 設計成果物。コード・DB変更、PR作成、本番適用は未実施。
目的: 取込後の進捗・失敗・配信候補を一画面で確認し、同じ画面から既存の配信を実行する。
対象: SalesAnchor TCG。既存テナント境界・権限・配信条件を継承する。

## 1. 根拠と限界

コード調査SHA: 8206ba2844921c1efb3ca4fd647230e76bb0c5c6。
以下はMac側の読み取り専用調査報告をレビューした結果。

- `/tmp/reports/pmg-import-delivery-ssot-recon-01d.txt`: 固定コミットのコード・migration調査。
- `/tmp/reports/pmg-import-delivery-ssot-prod-recon-01.txt`: 本番checkout SHA一致、worker自動解析有効、列定義。
- `/tmp/reports/pmg-import-delivery-ssot-prod-recon-01b.txt`: 21制約と工程別件数。
- `/tmp/reports/pmg-import-delivery-ssot-prod-recon-01c.txt`: 関連整合性・充填率・配信先結果。

| 本番観測 | 値 | 設計への影響 |
|---|---:|---|
| 取込履歴 | 28、確認待ち1 | 確認待ちは技術失敗と分離 |
| 抽出ジョブ | done 966 / empty 72 / error 57 | 状態値を保持して表示 |
| 抽出商品・解析結果 | 各23,456 | 既存結果を正本として再利用 |
| errorジョブに属する商品・結果 | 各166 | 結果があるだけで成功扱いしない |
| 要確認商品 | 4,255 | 複数理由があっても商品を重複計上しない |
| 関連欠損・解析結果重複・未完了解析ラン | 調査対象はいずれも0 | 現在の整合性。将来の不具合不存在の証明ではない |
| raw_memo非空のNOTE_JA充填 | 1,234 / 2,855 = 43.22% | 1,621件空欄。新仕様未適用か辞書未一致かは未確定 |
| 有効配信先 | 3、最新結果は各ok | 全履歴の成功件数には換算しない |

本番で取込から元投稿への恒久関連と、専用の配信実行・明細保存先は確認できなかった。
APIコンテナの実コード比較、外部シート上の実データ、過去データの取込所属復元は未確認。
全件name-first-v2であることは、全件がNOTE_JA新仕様で再解析済みという証明ではない。

## 2. 画面仕様

既存インポートページを総合画面へ拡張する。既存入力方法は維持し、ファイル入力だけへの変更をしない。

1. 上部: 既存インポート入力、取込履歴選択、対象取込日時・状態。
2. 工程表示: インポート、Gemini抽出、システム解析。各工程の単位・分母・完了数・待機・実行中・失敗を表示。
3. 詳細: 要対応、解析結果、全体の配信候補、処理履歴。NOTE_JA・理由を確認できる。
4. 配信領域: 「配信対象：現在の全体データ」を常時明示。配信先、候補数、除外数、実行条件、配信ボタン。
5. 実行後: 同じ領域に実行ID、配信先別結果、開始・終了時刻、履歴を表示。

取込の選択は進捗・解析結果の表示範囲だけに適用する。配信候補と配信実行は既存の全体範囲を維持する。
画面上の第四工程には「全体配信」と表示し、選択取込の配信完了と誤認させない。
モックで仮置きした「今回の取込だけの配信」「要確認が1件でもあれば配信停止」は実装しない。
既存配信条件による未完了ジョブ・ランの停止判定、除外条件を継承する。

ページ離脱・再読込でもDBから状況を復元する。初期案は表示中5秒間隔の読取更新、非表示タブでは停止。
取得失敗はエラーと最終取得時刻を表示し、最後の値を古い値と明示する。0件へ置換しない。
集計が未対応・関連不明の場合はnullと理由を表示し、進捗率を作り上げない。
PageLayout、ja/en翻訳、既存アイコン、デザイントークンを使用する。時刻はオフセット付きで通信し、UIでJST表記を明示する。
詳細のページ送り・フィルタ・対象行数はサーバー側で処理し、全商品をブラウザへ一括取得しない。

## 3. SSOTとデータの責務

以下の新規名・フィールドは提案する実装契約であり、既存テーブル名ではない。
実装開始時に最新mainとの衝突を確認し、同じ責務の実装が追加されていたら再利用する。

| 情報 | 正本 | 追加・維持する内容 |
|---|---|---|
| 取込・確認待ち | import_jobs | 既存情報を維持。関連記録の完全性を示すnullableな印を追加 |
| 元投稿 | source_messages | 本文の唯一の現在保存先を維持 |
| 取込と投稿の関連 | import_job_messages（新規） | import_job_id / source_message_id、取込時のcreatedまたはreused区分、created_at |
| 抽出状態 | extraction_jobs | 既存statusを状態の正本として維持。必要な開始・終了・更新時刻を追加 |
| 抽出商品 | extraction_items | 正本を維持、画面用コピーを作らない |
| 現在の解析結果 | analysis_results | extraction_item_id UNIQUEを維持 |
| 解析の各実行 | analysis_runs | 自動・手動実行の状態、attempt識別、失敗コード・時刻を追加 |
| 再解析前の履歴 | analysis_run_snapshots | 既存の役割を維持 |
| 配信実行 | distribution_runs（新規） | 実行ID・request key・scope・actor・時刻・snapshot識別 |
| 配信先別の試行 | distribution_run_targets（新規） | run_id / target_id / attempt、状態、エラー分類、送信行数、時刻 |
| 配信対象の固定内容 | distribution_run_rows（新規） | run_id / row ordinal、元解析結果IDとの対応、実際に送信する行データ |

取込関連の複合キー(import_job_id, source_message_id)を一意にし、両方向検索用インデックスを設ける。
同じ投稿が複数の取込に現れても本文を複製せず、それぞれの取込への関連を保持する。
重複ファイルとして同じimport_jobを返す既存動作は維持する。再試行で関連行を増殖させない。
取込commitの投稿作成・既存投稿参照・関連作成・取込確定は一貫したトランザクションにする。
保留中は既存pending_messagesを継承し、確定時に関連を作成する。
関連記録が完了しているという印により、「0投稿」と「過去の関連未記録」を区別する。
既存取込を日時・本文類似で後付け紐付けしない。過去分は関連不明として表示する。
取込対象外・無効・旧版の判定は既存の判定を使い、状態を画面用テーブルに複写しない。

最新の解析状態はanalysis_runsの実行記録から決定し、extraction_jobsへ同じ解析状態を二重保存しない。
既存analysis_runsのtotal等は実行時点の履歴値。現在件数はanalysis_resultsから算出する。
新規自動解析も実行開始・完了・例外を記録し、既存手動再解析も同じ記録処理を使用する。
記録導入前の解析は「結果あり・実行状態未記録」とし、結果の存在から成功状態を捏造しない。
同一タスクの再配達は同じattemptを再利用し、明示的な再試行は新attemptとして履歴を残す。
worker消失時は期限と実行所有権を確認して状態不明を記録する。時間だけで失敗や成功を断定して再実行しない。
新たな未完了runを既存配信停止判定がどう扱うかを、実装便で必ず統合検証する。

配信スナップショットは過去に送った事実の保存であり、商品の現在値を編集する保存先にはしない。
同一出力内容を複数配信先へ送る場合、run共通の行データを1回保存し、配信先別結果から参照する。
配信先ごとに内容が異なる既存仕様が見つかった場合は、出力セット単位で保存し共有する。
JSON行のハッシュだけでは内容を復元できないため、実送信する列・値・順序も保持する。
複数解析行から出力1行が生成される場合は、単一のanalysis_result_idを無理に割り当てず対応表を用いる。
現在結果が後で更新されても過去配信内容は変えない。現在結果の削除に配信履歴を連鎖削除させない。
tcg_distribution_targets.last_*は既存互換用の最新サマリと位置付け、履歴の正本は新規実行記録とする。
新規画面とAPIは履歴から最新結果を取得する。互換サマリは同じ完了処理で更新し独立編集しない。
移行前のlast_*は「導入前の最新記録」として表示し、存在しない過去runを生成しない。

## 4. 集計契約

- レスポンスはscope、as_of、coverage、単位、件数、理由を持つ。coverageはcomplete/legacy_unknown等を区別。
- 取込進捗は中間表経由のDISTINCT投稿・ジョブ・商品を工程別に数える。
- 投稿と商品を合算した「失敗総数」を表示しない。
- 処理完了割合は終端数/対象総数。成功率と別表示し、errorも処理終了として明示する。
- 0対象の進捗は「対象なし」。不明の分母を0と扱わない。
- 解析結果の要確認は商品単位のdistinct集計。理由別内訳には重複し得る旨を示す。
- 抽出errorのまま商品や結果が残る場合、error表示と残存結果件数を併記する。
- 全体候補と除外は既存配信判定の共通関数から生成する。UIで別の判定を実装しない。
- 集計API内の複数照会は同じ読取スナップショットを使い、処理中の更新で分子分母が食い違うことを防ぐ。
- 全テーブルを横断JOINして行数を膨張させず、工程別集計後に統合する。

提案API（既存経路との衝突・権限を確認して確定する）:
- GET /tcg/line-import/{id}/progress: 取込進捗、関連完全性、要対応内訳。
- GET /tcg/line-import/{id}/items: ページ付き解析結果と工程状態。
- GET /tcg/distribution/preview: 既存互換を保ち、共通選定による全体候補を返す。
- GET /tcg/distribution/runs と /runs/{id}: ページ付き履歴・配信先別結果。
- 既存run操作: request keyと確認した内容のrevisionを受け取り、履歴IDを返す契約へ拡張。

## 5. 配信操作・競合・部分成功

1. プレビューは現在の全体データを共通関数で生成し、候補の安定した順序と内容・設定からrevisionを返す。
2. 利用者は配信範囲、対象配信先、候補数、NOTE_JAを確認する。
3. 実行時にサーバーが権限・既存停止条件・revisionを再確認する。変化があれば再確認を求め、勝手に違う内容を送らない。
4. tenant内の配信実行権をDB上で排他的に取得する。request keyをtenant内一意にし、同じ要求は同じrunを返す。
5. 送信内容と対象設定を固定してDBに保存・commitした後、その保存内容から外部出力する。
6. 配信先ごとにqueued/running/succeeded/failed/unknownを記録する。全体の状態は配信先別状態から導出する。
7. 一部成功はそのまま保持する。成功済み配信先は同じrunの再試行対象から除く。
8. タイムアウト・接続断等で外部結果が不明ならunknownとし、失敗扱いの自動再送をしない。

外部出力とDB更新を1つの原子的処理にはできない。外部成功後・DB記録前の停止に対して、照合可能な手段を実装前に確認する。
外部側の冪等性・結果照合手段がない場合は「重複なし」を保証しない。unknownの手動確認導線を設ける。
ロックは画面ボタン無効化だけに依存しない。クラッシュで期限切れとなった実行も、unknown確認前に再送させない。
配信候補の確認は読取操作とし、DBへの大量snapshot保存は実行時だけ行う。

## 6. 最小実装便と権限境界

| 便 | 内容 | 主な検証 |
|---|---|---|
| 1 | この設計を既存正本文書体系へ登録。最新mainとの重複・競合を確認 | 対象ファイル宣言・既存仕様との照合 |
| 2 | 取込関連の追加、commit経路対応、共通進捗API | 再取込・重複・rollback・過去関連不明 |
| 3 | 自動/手動解析の実行記録を統一 | 再配達・例外・worker停止・配信停止条件 |
| 4 | 配信履歴、共通選定、実行固定、排他・冪等性 | 二重実行・部分成功・unknown・再試行 |
| 5 | 採用レイアウトを既存インポート画面へ実装、配信操作を共用 | 進捗更新・エラー表示・JST・ja/en・モバイル |

UIを並行試作しても、取得不能値を推測で実データ表示しない。
この仕様書は本番SQL実行・配信・マージの許可ではない。各変更は既存のPR・GO経路に従う。
報告は/tmp/reportsに保存する。生の本番報告はリポジトリへコミットしない。
schema追加はadditive-only。既存全対象テナントと新規テナントの適用経路を記載する。
移行は既存結果を書き換えない。戻す場合はアプリを前版へ戻し、新規表・履歴は保持する。
NOTE_JAの全件再解析、辞書改善、取込単位配信はこの画面統合の便に混ぜない。

## 7. 受入条件

1. 取込の新規作成・保留から確定・既存投稿再利用の各経路で関連が一度だけ記録される。
2. 再試行しても投稿・商品・関連・解析実行が意図せず増殖しない。
3. 過去取込の関連不明を0件や100%完了と表示しない。
4. 57 errorジョブに結果166件が残る型のデータで、成功と誤表示しない。
5. 同じ商品に複数確認理由があっても、要確認商品数は1件。
6. 同じscopeと読取時点について各ページの集計値が一致する。
7. API失敗・権限エラー・通信断を0件表示へ変換しない。
8. ページ移動なしで配信候補確認・実行・結果確認ができる。
9. 取込選択を変更しても全体配信の範囲は変わらず、UIに明示される。
10. プレビュー後のデータ変更を検知し、確認していない内容を送らない。
11. 二重クリック・別画面同時実行で同一配信が二重開始されない。
12. 部分成功時に成功済み配信先を再送しない。結果不明時は照合前に再送しない。
13. 後から解析結果を更新しても配信履歴の列・値・順序が再現できる。
14. テナントを越える取込・進捗・配信履歴を参照できない。
15. 実PostgreSQLで関連制約・競合・トランザクション検証を行い、外部出力はテスト用に置換する。

## 8. 実装前に解消する限定事項

- 最新mainに同じ機能が追加されていないか、変更対象ファイルの所有・競合を確認する。
- 稼働APIサービス名と配布経路を確認する。存在しないbackendサービス名を固定しない。
- 外部配信の実体が置換・追記のどちらか、照合・冪等性が可能かを現行送信関数で確認する。
- analysis_runsの既存停止判定・失敗runの終端化と、新規自動解析記録を整合させる。
- 本番データや権限への追加操作が必要なら、その対象を明示した別便にする。

調査の繰り返しではなく、上記の変更に直結する差分確認だけを実施する。

## 第1段階の実装・ローカル検証（2026-09-10）

- 実装済み: 関連表・2つのnullable日時列・一意索引・取込/保留確定・progress/items。UIと配信履歴と解析attemptは未実装。
- ローカルPostgreSQL 16.15、独立DB pmg_import_ssot_test、Python 3.12の一時venvで68件通過（実DB14件・既存ユニット54件）。外部抽出queueはモック。Gemini・実配信なし。
- コマンド: PMG_TEST_PG_URLでローカル専用DBを指定し、backendから pytest -o addopts='' -o cache_dir=/tmp/pmg-pytest-cache -q --tb=short tests/test_tcg_import_progress_pg.py tests/test_tcg_line_import.py。
- この対象テスト実行では全体カバレッジ判定を行っていない。全体スイートはGitHub CIで確認する。
- make lint-ci: exit 0。ruff成功、bandit High 0。mypyは既存の非ブロック運用で全体にエラーあり（今回の3変更Pythonモジュールに指摘なし）。
- ADR-072 strict lint: 88ファイルOK。check-task-state.sh、git diff --check成功。
- Mac arm64の一時venvではSQLAlchemyのasyncio extra（greenlet）を追加導入した。製品requirements変更なし。
- 実DBテストは既存CIのRLS_ADMIN_DATABASE_URLでも稼働し、ローカル限定・テストDB名の検査をして隔離schemaを使う。CI設定変更なし。
- 本番の既存全テナントへの適用検証は未実施。ローカルの既存相当2schemaと後発1schemaで追加列・FK・再適用を検証した。
- マージ・本番適用・人による画面確認は未実施。本番GOは記録していない。

## PR提出・テスト定義の是正
+
+PR: https://github.com/shingo-ops/salesanchor/pull/3386 （OPEN、main向け）。実装commit aa74625c8283cf159d0dd620949995bfe6acc1c1。
+CIのtest-schema-dup gateがテスト内の独自テーブル定義を検出したため、既存TCG初期migrationとreview-stage migrationをテストschemaに適用する形に変更。ガードの変更・例外追加なし。
+正式migrationから作る実DBでも68件通過（2.08秒）。新規テスト内の複製テーブル定義は0。確認範囲・外部通信禁止・本番未適用は維持。
+

## 2026-09-10 後続便: 解析実行記録の設計草案

この節は、解析の成功・失敗・結果不明を画面で見分けられるようにする設計案。
親: [商品マスタ](../../specs/product-master/README.md)。根拠: [recon.md](recon.md)の同日後続便節。
対象ADR: ADR-113、ADR-154、ADR-072。mode: handoffで引き渡すための草案。第1段階のAPPROVE・GO #3386・GO #3390は本便の実装承認ではない。

### 目的と境界

自動と手動を同じanalysis_runsへ記録し、結果と成功記録を同じ保存処理で確定する。記録済み実行について二重適用0回、途中失敗時の部分更新0件、旧記録からの成功推定0件を受入目標とする。
今回扱うのは実行記録、進捗/明細APIへの接続、既存配信停止判定との整合。配信履歴・内容固定・全画面統合は後続。商品判定v3・辞書改善・NOTE_JA全件再解析・本番データ修復は含めない。

### 正本と追加データ（提案名・未実装）

analysis_resultsは現在結果、analysis_runsは実行履歴、analysis_run_snapshotsは再解析前の履歴として維持する。
analysis_runsへ以下をnullableで追加。旧行を推測で埋めない。

| 項目 | 契約 |
|---|---|
| execution_state | queued / running / succeeded / failed / unknown。旧行NULLはlegacy_unrecorded |
| request_key | schema内UNIQUEの文字列。自動はauto:<extraction_job_uuid>。手動はクライアントUUID。旧行NULL可 |
| request_fingerprint | job_id・run_type・retry_ofの一致確認。同じkeyの別要求は409 |
| attempt_no | ジョブ行ロック内で採番。新規同一job内UNIQUE。旧行NULL |
| retry_of | 明示再試行元run。同一schema・同一jobだけ。成功runを再試行しない |
| execution_started_at / finished_at | 実行開始・結果確定/不明化の時刻。既存started_atは受付日時として維持 |
| owner_token / heartbeat_at | 実行所有者とDB時刻による生存記録 |
| error_code | 固定コードのみ。例外本文、DSN、元投稿を保存しない |
| result_summary | 成功時のbefore/afterをJSONBで保持し、同一keyへの応答を現在結果から再計算しない |
| resolved_by_run_id | 未解決の失敗/unknownが後続の同一job成功で解消された参照。古い失敗状態は書き換えない |

completed_atは新規では成功時だけ設定。失敗を成功したように見せるためには設定しない。旧列・旧値は維持する。
analysis_resultsへlast_successful_run_idをnullable追加。同じトランザクションで結果の出どころを保存。旧結果はNULLのまま。
同一schemaにtcg_pipeline_guard（id=1だけの行）を新設する案。状態の正本ではなく、解析と配信準備の同時実行を調整するためだけに使う。全ての新FKは同一schema。新規参照を理由に既存履歴を連鎖削除しない。

### 保存と実行の順序

1. 抽出ジョブの取得はpending条件付きUPDATE RETURNINGで所有を確保し、更新0件の再配達は新たなGemini抽出を開始しない。抽出中の復旧自体は本便で自動化しない。
2. 自動解析ONかつ抽出doneの場合、抽出結果・done・queuedのanalysis_runを同じトランザクションで保存する。抽出doneなのに解析予定が未記録となる隙間をなくす。OFF/empty/errorはrunを作らず、それぞれ未実行理由を表示する。過去行は設定値から理由を推定しない。
3. 自動・手動は共通のexecute_analysis_runを呼ぶ。queuedのclaimだけを許可し、同一jobで別runが実行中なら新規実行を始めない。終端runの同一key再送はその履歴を返し、処理を繰り返さない。
4. runningとowner_token・開始時刻を短い取引で保存。その後、guardの共有ロック→extraction_jobs行の排他ロックの順で取得し、run状態・ownerを再確認する。確認不一致なら結果を書かない。
5. 再解析前snapshot、商品解析、E3a/E5→E3b→E4、最終値からの統計再集計、last_successful_run_id、succeeded/completed_atを1トランザクションで保存する。解析関数内の3か所のcommitを共通実行処理へ移す。通常アプリの自動・手動2呼出しを同時に移行する。
6. 任意マスタ欠落の互換は維持する。3ローダーのsession全体rollbackを局所的なSAVEPOINTへ置き換える。空への代替を認めるのは該当任意テーブル欠落（SQLSTATE 42P01）のみ。接続断・権限不備・列欠落は失敗へ伝え、成功にしない。
7. 例外では結果取引をrollback後、別取引で同じownerかつrunningのrunだけfailedへ変更する。接続不能等で失敗記録も保存できなければrunningが残り、後述の照合でunknownになる。新接続で結果処理だけを勝手に続行しない。

### 再配達・明示再試行・停止時

- queuedはDBを再開点とし、queueへ送る前にcommitする。enqueueに失敗してもrunは消さない。新規の定期処理がqueuedを再送するが、実行側claimで二重適用を防ぐ。配送回数と解析attemptを分ける。
- Celeryのtask IDだけをrequest keyにしない。公式仕様上、retryは同じtask IDを使用するため、明示再試行の区別にはDBのrequest keyとretry_ofを使う。
- failed/unknownは自動再試行しない。明示要求の新keyで新runを作り、retry_ofに元runを残す。unknownからの再試行もjobロックと元所有者の無効化を確認してから実行する。
- 生存更新15秒、期限180秒、照合周期60秒を草案値とする。これらは成功率の実測値ではない。周期遅延があるため検出時間の上限は保証しない。
- runningの期限切れだけでは書き換えない。照合処理がguard共有→job行をNOWAITで取得し、期限と状態を再確認できた場合だけunknownへ遷移させ、ownerを無効化する。jobを実行者が保持中なら状態確認中と表示して停止判定を維持する。
- 結果取引の最後にownerとrunning条件を再確認して成功を確定する。照合で所有権を失った処理は成功記録も結果もcommitできない。
- queuedの長期待機はqueued_delayedとして表示し、成功・失敗にしない。

### 実行管理の配置とDB接続（草案の具体化）

共通処理はbackend/app/services/tcg_analysis_run_svc.py。新規taskモジュールtcg_analysis_runs.pyにrun_id指定の実行タスクとtickを定義し、celery_app.pyのinclude/beatへ登録する。tickは60秒ごと、queuedのenqueueとrunning期限切れの照合だけを行い、failed/unknownを実行しない。配送前のqueued選択は安定したstarted_at/id順・上限100件とし、反復処理する。queue停止時もDBのqueuedを維持する。
heartbeatは実行中だけ別スレッド・別Sessionで15秒ごとに実施する。解析結果のSessionを別スレッドと共有しない。UPDATE条件はid/owner_token/running、時計はDB。処理終了時は停止イベントを設定しスレッドを終了する。heartbeat接続の障害は成功の根拠にせず、結果取引のowner条件とDBロックを最終的な排他条件とする。
同期DB用のsession factoryを共通サービスに集約し、自動・手動・tickで同じTCG_SCHEMAと接続設定を使う。既存TCG_DB_URL優先の接続契約は勝手に削除しない。実際の接続先とAPIの接続先の一致を稼働環境で確認してから有効化する。異なる場合は本設計を合格にせず接続設定の設計へ戻す。接続情報そのものを履歴・画面に出力しない。

### 配信との整合（停止方針は今回PO合意、詳細設計は草案）

従来の未完了抽出pending/running/extractedによる停止と既存商品除外条件を維持する。要確認商品が1件あるだけで全体を止める条件は追加しない。
配信準備はguard排他ロック取得後に未完了判定と現行候補取得を行い、メモリ上の出力を組み立ててからロックを解放する。run受付/解析更新は共有ロックを使う。外部送信中にDBロックを持ち続ける設計にはしない。実行時の恒久snapshot・二重配信排他は後続配信便で扱う。
未完了run条件案: 旧行はcompleted_at NULLかつresolved_byなし、新行はqueued/running/unknown、または未解消failed。同じjobの後続成功時だけ過去failed/unknownを解消済みにする。過去の失敗自体は表示に残す。
自動解析のfailedも全体配信を止めると、従来は未記録だった失敗で配信が止まる。これは現行の完全同一動作ではない。POへ「自動解析が失敗した場合、その解析をやり直して成功するまで、全体配信を止める方針でよいですか？」と確認し、1件の失敗でも全体配信が待機する影響を説明した。PO原文「進める」を、この方針への合意として受け取った（2026-09-10）。実装・実配信・本番変更のGOではない。

### 画面へ渡すAPI契約案

既存progressのanalysis.unit=extraction_itemと商品件数を維持。新たにanalysis.executions（unit=extraction_job、latest_states、recorded_jobs、unrecorded_jobs）を追加し、商品数とrun数を混ぜない。各jobの最大attempt_noの状態を最新状態とし、履歴件数は別欄。旧行しかなければunrecorded、成功に読み替えない。
itemsにはlatest_analysis_run_id / analysis_execution_state / result_run_idを追加。失敗runと直前の保存済み結果を併記できるようにする。既存のscope/as_of/coverageと単一読取時点の契約を維持。
既存手動reanalyze APIはbefore/afterを維持してrun_idを追加。任意のIdempotency-Key（UUID形式）を受け、同じkeyは同じrun。未指定の旧クライアントはサーバーでUUIDを作るため通信断後の同一要求再送保証は対象外。新画面は必ずkeyを生成・保持する。
履歴参照はGET /tcg/extraction-jobs/{job_id}/analysis-runs（offset>=0、limit=1..100、attempt_no DESC NULLS LAST、started_at/idで安定順）を提案。require_super_admin・設定TCG_SCHEMAを継承し、404で別schemaを推測させない。
再試行は同じPOSTに任意query retry_of（UUID）を追加する。新画面は履歴のfailed/unknownを選び、「この解析だけを再試行する。配信はしない」を確認して新しいIdempotency-Keyで送る。retry_ofは同じjobのfailed/unknownだけ有効。未解決失敗があるのにretry_ofなしなら409 recovery_required。同時実行中のjobへの別key要求は409 analysis_busyとし、新runを作らない。
同一keyのsucceededは保存済result_summaryとrun_idを200で返す。queued/runningは409 analysis_in_progress（run_id、state、Retry-After: 5）を返し、GETで確認する。failed/unknownは409 analysis_retry_requiredと元run_idを返す。新規の実処理で捕捉した失敗は500 analysis_failedとrun_idを返し、生の例外は返さない。keyのfingerprint不一致は409 idempotency_conflict。UUID形式不正は422、権限は既存403、job不在/別schemaは404。DB接続不成立時は503とし成功の空レスポンスを返さない。
GET履歴にはscope/as_of、最新状態、result_summary、error_code、retry_of、resolved_byと時刻を含め、owner_tokenと生の例外は返さない。新画面で通信断時は同じkeyを保持し再送する。UI実装は後続便でこの契約を利用する。

### 移行・影響ファイル・戻し方

追加migrationは既存のTCG表を持つtenant_NNNのみ対象。tenant_001/004と後発TCG有効化に適用する。CRM一般テナントにTCG表を新設しない。migration登録は既存公式経路を使用し、本セッションでscripts/deploy/CIを変更しない。
候補: backend/app/services/tcg_analysis_run_svc.py（新規）、backend/app/tasks/tcg_analysis_runs.py（新規）、tcg_analyzer_svc.py、tcg_product_master_svc.py、tcg_import_progress.py、tcg_distribution_svc.py、tasks/tcg_extraction.py、routers/tcg_product_master.py、celery_app.py、追加migrationと対応試験。
旧workerが残ると新ロック・履歴を無視して書けるため、API/worker全経路の切替と旧実行の排出を確認してから記録を有効化する。稼働サービス名と配布順序は下記の追加確認を参照。旧実行の排出と停止時間は未確認。新旧混在でも安全と宣言しない。
APIとworkerのDB接続先一致も有効化の前提。TCG_DB_URLとDATABASE_URLが別DBを向く状態では履歴正本が分裂するため有効化しない。旧データの成功backfillは行わない。
戻す場合は新規受付を止め、実行中runを確認してからアプリを戻し、追加列・履歴を保持する。実行中のまま旧workerへ戻す手順は許可しない。実運用手順は実機確認後に確定する。

### 受入条件と検証方法（未実施）

| 基準 | 検証方法 |
|---|---|
| 自動・手動の成功が同じrun構造で記録される | 両入口を実PostgreSQLで実行しrunと結果参照を突合 |
| 同一keyを2接続で送ってrun1件・結果適用1回 | 独立接続の同時実行試験 |
| 同じkeyの別job要求は409、更新0件 | APIとDBを突合 |
| 明示再試行は新run、元failed/unknownは履歴に残る | retry_ofと解消参照を検査 |
| 3つの旧commit境界で失敗しても部分更新0件 | 各処理段階に故障を注入し全結果の前後一致 |
| 3任意マスタ欠落で実行履歴が消えない | 実DBのSAVEPOINT・履歴保存を確認 |
| 接続・権限・列欠落を成功にしない | 故障別のfailed/unknownと結果rollbackを確認 |
| worker停止は成功にならずunknown、再送で再解析しない | 別プロセス停止、期限とjobロックを制御 |
| 生存中の処理を期限だけで奪わない | ロック保持中の照合と遅延worker試験 |
| 成功commit直後の停止・再配達で適用1回 | 成功DB記録と再配達を突合 |
| 配信と受付/解析の競合で途中結果を選ばない | 2接続の実行順を固定し候補取得・停止を検証。外部送信はstub |
| 旧run・旧結果を成功と誤表示しない | NULL、旧未完了、完全記録0件の3型でAPI確認 |
| 商品数と実行数を混ぜず最新runと結果来歴を返す | 1job複数商品・複数attemptを用いた集計試験 |
| DB/schema境界・既存/後発migration一致 | 正式migrationを適用する既存の実DB試験基盤を拡張 |

### Why・代替案・根拠の適用限界

途中保存3か所、自動履歴保存なし、手動だけの履歴、任意マスタ照会rollback3か所という実コードが、結果と成功を同時保存する変更の直接根拠。履歴だけ追加する案では途中結果が残るため採らない。全解析を再実行する案は旧データを変えるため対象外。
PostgreSQLの行ロックは取引終了まで保持される。SQLAlchemy2のSAVEPOINTは外側の取引を保ちながら局所rollbackする仕組み。Celery retryは同じtask IDを使う。これらは仕様の根拠であり、この製品の実装が動いた証明ではない。
- https://www.postgresql.org/docs/16/explicit-locking.html
- https://docs.sqlalchemy.org/en/20/orm/session_transaction.html
- https://docs.celeryq.dev/en/stable/userguide/tasks.html
確認日2026-09-10。Context7利用不可のため公式資料で代替。外部導入事例は不要。今回必要な数値は再配達/部分更新の件数であり、他社の改善率から成功を推定しない。
弊害: 1job分の結果をまとめて保存するためロック保持時間が増える。失敗/不明の未解決中は全体配信が止まり得る。処理時間と混雑時の実測は実装試験で記録する。

### 設計自己審査

REVISE（修正必要、実装カード発行不可）。同一AIによる自己審査であり独立レビューではない。
解消した点: 途中commit、任意マスタrollback、同一要求と再試行の識別、停止workerの所有権確認、旧データの非推定、配信準備とのロック順序を草案へ明記。
未解決: 旧worker排出・切替手順の実機確認。API/workerの接続設定による実DB一致は下記の読取診断で確認した。自動解析failedで全体配信を止める方針と成功時の解除は今回PO合意として追記した。
再試行APIと実行中応答、heartbeatのSession分離、tickの配置は本節に具体化済み。残件は読み取り調査で確認し、停止・本番変更は別承認。文書上の接続設定だけを実機の一致と扱わない。

### 維持の仕組み（後続便）

守り手: backend/tests/test_tcg_gemini_extraction.py、backend/tests/test_tcg_distribution.py、backend/tests/test_tcg_import_progress_pg.pyと実装時に追加する実行記録試験。実装役が故障・競合試験を維持し、PO指定Reviewerが結果を確認する。既存CIは .github/workflows/test.yml と .github/workflows/migration-guard.yml。未追加の試験が現在のCIで強制済みとは扱わない。


### 配布順序の追加確認と分割案（2026-09-10）

.github/workflows/deploy.yml:149-158 はコード配布→migration→最終確認の順。:319-335 はAPIをblue-greenで切り替えた後、worker/beatを再作成する。scripts/blue-green-cutover.sh:147-150 は旧APIを最大40秒で停止する。これらは現在のコード順序であり、本セッションでは実行していない。
したがって追加テーブルを無条件に読む新コードとmigrationを同じ便で出すだけでは、テーブル未作成・新旧worker混在の時間帯を安全に扱えない。配布スクリプトを独断変更せず、次の分割で設計する。

1. 追加migrationのみ先行。既存コードが使わない表・列を追加し、影響・schema適用を検証する。マージ/本番はそのPRの別GO。
2. 実行管理コードを未有効の状態で配布する。guardにtracking_mode（legacy/paused/tracked、初期legacy）を提案追加。全新入口はlegacy時に既存処理を維持し、trackedだけで新履歴を使用する。設定表が未作成でも新履歴を使用しない。
3. 新版API・worker・beatの実体とDB接続一致を確認後、pausedにして新規の取込確定・再解析・配信とworkerの新規claimを一時停止する。状態参照は継続する。処理中の排出を確認し、追跡不能な旧実行があれば有効化しない。
4. 同じ確認済み環境でtrackedへ切り替え、旧pendingは新しい実行管理で処理する。停止と有効化は本番操作のため別の明示GOが必要。

pausedへの遷移と受付の競合はguard排他/共有ロックで直列化する。新APIの停止時応答は503 pipeline_paused。workerはpendingを保持し後で再配達する。旧版はこの制御を知らないため、旧版が残る状態で本機構による停止を保証しない。
具体的な稼働サービス・バージョン・旧実行の検査方法は、許可された読取ができてから確定する。現時点の設計審査はREVISEを維持する。


### DB接続先の実測確認（2026-09-10、読取のみ）

人間用SSH鍵の使用を「今回のDB接続先確認に限る」と説明して許可を求め、PO原文「進める」を受領。その範囲で診断を実行しexit0。
API・worker・beatの各稼働コンテナ内に作った診断用接続で、transaction_read_only=onが3/3、DB識別値のSHA256一致が3/3、TCG_SCHEMA=tenant_004が3/3、対象4表の存在が各4/4だった。生の接続情報は出力していない。コマンド・出力と限界はrecon.md同日節に保存。

これはコンテナの環境設定から開いた診断用接続の一致であり、稼働中プロセスが既に保持する接続・全worker個体・配布版・処理中件数の確認ではない。beatにDB利用処理が存在することの証明にも使わない。PR #3386の全migration適用・本番反映完了も本診断の対象外。
設計自己審査はREVISEを維持。接続設定の相違という未確認事項は解消したが、旧実行の排出を判断する検査と切替手順は未確定。設計全体のPO承認、実装カード発行、実装着手、本番切替は未実施。


### 切替前確認の具体化と先行案の修正（2026-09-10）

先行分割案の「新版を配布した後にpausedとして旧実行を排出」だけでは、最初の新版配布時の強制終了を防げない。.github/workflows/deploy.yml:331-335はworker/beatをdocker rm -fで削除する。したがって、この案単独で初回移行の途中中断0件を保証することは撤回する。コード変更や本番操作は行っていない。

docker-compose.yml:190-192のworkerはconcurrency=2で、backend/app/celery_app.py:20-36に翻訳・メール・保守等とTCGタスクが同居する。worker全体の停止を「TCGだけ止まる」と説明してはいけない。TCG解析だけのactive=0も、この配布処理が消す全実行の安全確認にはならない。

#### 実装役に渡す切替確認表（未実装・未実測）

| 段階 | 必要な観測と合格条件 | 不成立時 |
|---|---|---|
| 対象の固定 | 配布対象のcommit、サービス、全コンテナID、イメージID、起動時刻を記録。旧greenや別名workerも一覧から分類し、未分類0件 | 有効化しない。名前3件だけの検査を流用しない |
| コード実体 | API/全worker/beatの対象コードを配布対象commitのファイルハッシュと比較し、対象ごと一致。イメージ名やホストgit HEADだけでは合格にしない | 不一致・読取不可を未確認として停止 |
| DB/schema | 全書込経路の接続設定で同じDB/schemaと必要な列・制約・guard1行を確認。既存の3接続診断はDB一致だけの証拠 | 4表の存在だけでmigration完了にしない |
| 新規受付の停止 | 実際のAPI各入口で新規取込確定・再解析・配信が拒否され、DB更新/外部送信0件となることを試験。停止の開始時刻と対象を保存 | POへの作業自粛依頼だけを機械的な排他の証拠にしない |
| workerの排出 | 全workerから応答があり、実行中・予約済み・遅延予約の各タスクを分類。新規投入/取得の抑止が成立した状態で実行中0件を確認する | 無応答を0件にしない。待機時間満了を強制終了の許可にしない |
| DBとの突合 | extraction_jobsのrunning/extracted、旧analysis_runsのcompleted_at NULLをID単位で分類。残存結果から成功へ補正しない | 孤立した旧実行は個別調査。自動成功backfill・一括状態書換えをしない |
| 送信中の排出 | 同期配信要求と外部送信が終わっている証拠を確認する。現行last_*だけでは送信中0件と判定しない | 完了を観測できない送信があれば切替停止 |
| 再開 | 配布/必要検査成功後の別承認でtrackedへ変更。旧queued/pendingはIDを保持して再開し、新旧要求を混ぜない | queue purgeや全件再解析で整合を取り直さない |

各欄は将来実行する検査契約であり、現在通過済みではない。取得方法の実機確認・停止制御の実装試験が必要。Dockerの環境値全文、task引数/本文、SQL本文、認証情報は根拠へ出力しない。必要な件数・ID・状態・コード版だけを残す。

#### 次の設計判断

推奨候補は、初回切替に受付の一時停止と実行中処理の完了待ちを設けること。ただし現行の共有workerを止めると翻訳等にも待ちが生じ得る。停止対象・時間は未確定であり、短時間/TCG限定と約束しない。無停止を必須とする案は、共有workerの配布/タスク分離まで別途設計が必要となる。
この一時停止を許容する方針は未合意。本番停止を実行する承認とは分けてPOに確認する。方針が合意されても、停止制御の初回導入手順と再開条件が未確認のまま実装カードは発行しない。

#### 自己審査の更新

REVISEを維持。接続設定の一致は確認済み。追加で「初回配布が排出確認より先になる穴」と「共有workerの他業務への影響」を明確化した。受入条件に、全worker無応答時の停止、新規投入と排出の競合、送信中の切替拒否、旧版混在時の有効化拒否を追加する。これらの試験は未実施。


### 初回一時停止方針のPO合意と具体化（2026-09-10）

確認した質問: 「初回切替で一時停止を許容する方針で、設計を進めてよいですか？ 実際の本番停止の承認とは分けます。」
説明した影響: 新規受付を止めて実行中の完了を待つ。共有する翻訳等にも待ちが生じ得る。停止時間は未確認。
PO返答原文: 「GO」。承認対象はこの設計方針だけ。PR #3396のマージ、実装開始、人間用SSH鍵の追加利用、本番停止・再起動・変更には流用しない。前節の「一時停止方針は未合意」はこの記録により更新する。具体的な操作・所要時間は引き続き草案。

#### 停止の漏れを防ぐ対象範囲

APIの登録はbackend/app/main.py:569-604（/api/v1）、商品分類の管理入口は:456。対象候補は /api/v1/tcg/ と /api/v1/super-admin/tcg/ 配下。入口ごとの副作用を確認し、少なくとも次を停止する。

| 入口 | 必要な理由・根拠 |
|---|---|
| LINE upload/resolve/commit | 取込記録・仕入元・投稿を変更。tcg_line_import.py:125,387,550 |
| 商品CSV commit・商品作成・キーワード追加 | 解析が読む商品情報が変わる。tcg_product_import.py:153、tcg_product_master.py:208,246 |
| 単一job再解析・抽出再試行 | 解析実行や再投入を始める。tcg_product_master.py:287、tcg_diagnostics.py:88 |
| 配信run（全体/単一）・配信先/設定変更 | 外部送信と対象条件を変更。tcg_distribution.py:94,120,135,163,172,197 |
| series/types作成・変更・削除 | TCG参照マスタ変更。super_admin_tcg.py:72,103,133,171,203,233 |

HTTPメソッドだけで無副作用と判定せず、読取入口・previewはサービスまで確認してから通す。既存の状態参照を残す方針は維持するが、初回の旧版用受付遮断では読取も止める案を比較対象として残す。読取停止まで今回GOで承認済みとは扱わない。
定期側では抽出だけでなく、保留破棄（tcg_import_discard.py:57）と外部ミラー書出し（tcg_mirror.py）も照合対象。未知の書込経路があれば停止範囲の確定前に調べる。

#### 既存版にも効く受付遮断の候補と条件

新版のtracking_modeだけでは旧版の初回停止を制御できない。候補はAPIより手前でTCG書込入口を遮断する方式。nginx/nginx.conf:71,259にはapp/api両ホストがあり、両方を対象にする。legacyホストは:44でappへ転送する現行ファイルを確認したが、本番の設定一致は未確認。
既存nginxは設定ファイル単体のbind mount（docker-compose.yml:11）。ADR-137ではinodeの相違によりreloadだけでは新内容を読めない事例がある。従って「ホストファイル編集→reload」だけを手順として採択しない。コンテナが読む設定・構文検査・実際の拒否応答・復旧手段まで設計・試験してから採否を決める。nginxや運用スクリプトをこのセッションで変更しない。
遮断は配布中も維持する必要があり、deployによる設定置換や再作成で解除される方式は不採択。既存の内部直接呼出し・手作業・別workerはHTTP遮断だけでは止まらないため、全writer調査と合わせる。

#### 処理完了待ちの順序案（操作未承認・未実行）

1. 対象HEAD・全writer・必要な退避/復旧手段・停止期間の担当を確定し、その操作カードに対する本番GOを受領してから開始する。
2. 初回用の受付遮断を適用し、両公開ホストの対象入口で新規副作用0件を確認する。既に受付済みのAPI処理は別に完了を待つ。
3. 定期投入を停止し、共有workerの新規取得を止め、実行中を完了まで待つ。queue内の待機要求は削除しない。翻訳等の共有業務の待機を記録する。
4. 自然終了を確認してから配布処理を許可する。時間切れ・無応答・孤立したDB状態を強制終了や成功への書換えで解消しない。移行を中断し、受付遮断を維持するか解除するかは事前の復旧条件で決める。
5. 旧APIの完了・外部送信の完了を確認し、コード/DDL/接続/新規実行管理を検査する。新workerが起動直後にlegacy処理を始めないよう、起動前からpausedが有効な構成を必要条件とする。初期値legacyのまま起動して後からpausedにする順は採らない。
6. 記録済み対象に対する別の再開承認と検査を経てtrackedにし、受付遮断を解除する。再開後の待機要求・実行履歴・外部送信0件の確認方法を操作カードへ明記する。確認目的の実配信はしない。

Celery公式Workers GuideはTERMで実行中完了待ちを行う仕様を記載する。ただしREMAP_SIGTERM=SIGQUITなら即時停止側となり、5.6では完了待ち中のheartbeat動作変更も記載される。依存宣言>=5.4.0から稼働版の挙動を決めない。Docker stopは期限後にSIGKILLへ進むため、既定タイムアウト付き停止を完了待ち保証として使わない。稼働版・設定・PID1へのシグナル伝達・予約タスクの扱いを模擬環境で確かめるまで、停止コマンドを正式カードにしない。

仕様の出典（2026-09-10、Context7検索0件のため公式資料で代替）:
- https://docs.celeryq.dev/en/stable/userguide/workers.html （仕様確認時5.6.3。稼働版とは区別）
- https://docs.docker.com/reference/cli/docker/container/stop/
- https://nginx.org/en/docs/http/ngx_http_rewrite_module.html#return

追加の受入条件: 両公開入口の遮断漏れ0件、配布中の遮断解除0件、旧worker残存時の有効化0件、停止待ち期限切れ時の強制終了0件、新worker起動直後のlegacy実行0件。全て未実施。

自己審査: REVISE。一時停止の事業判断は解消。残件は初回受付遮断の採用方式、全writer/稼働版の実機照合、既存API/送信中処理の完了観測、停止・復旧の模擬試験。今回GOを技術方式全体の合格とは扱わない。


### 受付遮断方式の絞り込みと次の読取（2026-09-10）

deploy.yml:182-184はホストをorigin/mainへresetし、:360-374はnginx設定変更時にコンテナを再作成する。従って作業中だけ追跡済みnginx.confを書き換える案は、配布中も遮断維持という条件を満たせないため不採択。単にreloadを追加しても解決しない。
採用候補は、配布・rollbackが消さない停止状態と、それを読む入口制御を先に設ける方式。停止状態が読めない場合は対象書込を拒否する。停止状態の保存先/権限/初回導入/両ホストの制御を確定し、再作成・rollback中の遮断維持を試験してから採択する。既存本番の設定を未確認のまま、新しいnginx設定や運用コードを実装役へ渡さない。

処理完了について、tcg_product_master_svc.py:520以降は同期解析を別スレッドで実行し、tcg_distribution_svc.py:410以降も外部書込をthread executorで実行する。HTTP応答・切断・DBの非activeだけで処理完了とは判定しない。API処理が使う実行方式と稼働版を照合し、必要な完了観測を決める。

本番確認案は /tmp/pmg-cutover-runtime-readonly.py。Docker版、全稼働コンテナ名、対象projectのコンテナID/イメージID/状態/開始時刻/サービス名、API/worker/beatのCelery・Uvicorn・SQLAlchemy版、PID1の実行名、TERM置換の有無、対象コード7ファイルとnginx設定のSHA256だけを取得する。環境変数全文・認証情報・task引数・ログ・DB内容は出力せず、データ更新・再起動・signal送信・Celery制御を行わない。
対象project以外の稼働名も確認し、未分類のworker候補を残さないための入口にする。名前一覧だけで外部ホストを含む全writerを網羅したとは判定しない。これは稼働版/設定の照合用であり、排出実行や処理中0件の証拠ではない。
診断のAST構文チェック成功、SHA256=8e355d21acc44058e43febf28532d64ddfbd9d7935c670857c939d904ac8e3fa。未実行。本環境にはdockerコマンドがなく（exit127）、コンテナ模擬試験は未実施。人間用SSH鍵の前回許可はDB接続先診断だけなので、今回の読取には対象を明示した別許可を求める。設計自己審査REVISEを維持する。


### 稼働版照合を受けた設計自己審査（2026-09-10）

許可された読取診断exit0。API/worker/beatのインストール済みCelery5.6.3、Uvicorn0.34.0、SQLAlchemy2.0.38を確認。対象コード7ファイルは3コンテナで手元と21/21一致、nginx設定ファイルも一致した。worker/beatのPID1実行名celery、診断環境のREMAP_SIGTERM未設定を確認。詳細のID・起動時刻・hashと限界はrecon.md「稼働版・構成の読取結果」。

解消した未確認: コンテナに入っている対象コード、インストール済み版、nginxのマウント先ファイルとの一致。Celery停止案の参照を5.6.3へ合わせられるが、実際の停止試験成功とは扱わない。nginxファイルの一致だけで受付遮断機構が存在するとは扱わない。
残件を次の3項目に整理する。
1. 配布/rollback中にも維持される初回受付遮断の具体的な保存先・導入・復旧方法。
2. HTTP切断後も動き得る別スレッド処理と外部配信の完了を、旧版で確認する方法。
3. 全writerの境界確認と、停止/予約要求保持/再開の模擬試験。ローカルDocker不在のため試験環境は未確保。
これらが未解決なのでREVISEを維持する。実装カードを発行せず、本番停止も行わない。稼働版/対象コードの確認は繰り返さず、次の調査は上記残件へ限定する。


### 初回切替方式の改訂案と検証仕様（2026-09-10）

これまでの候補を、以下の段階方式へ絞る。これは審査中の技術案であり、実装/本番操作カードではない。

**受付制御の案**: 停止状態は配布checkout外の専用ディレクトリで保持し、nginxへディレクトリ単位で読取専用mountする。具体候補はホスト/var/lib/salesanchor/pmg-cutover、コンテナ/etc/salesanchor/pmg-cutover。プロジェクト管理の通常設定はその状態を参照するだけとし、deployで停止状態を初期化しない。所有者は本番操作を承認された運用担当、アプリ/nginxからの書込不可。製品DBの解析状態とこの運用上の受付制御を混同しない。
拒否を既定とし、明示的な受付許可状態が確認できる場合だけ対象書込を通す。読取不能・状態欠落時も通してしまう単なる「停止ファイルが存在したら拒否」方式は採らない。状態のキャッシュやnginx設定再読込との競合を模擬試験で確認する。状態表現とnginx判定式は試験前に確定し、未検証のコード断片を実装例として渡さない。

**戻し先の制約**: 停止機構の先行導入と、その機構を含む戻し先の確保を必須にする。解析実行管理を導入する便は、戻し先commitにも受付制御が含まれることを事前に照合する。追加mountだけを残しても戻したnginx設定が参照しなければ遮断されないため、状態保存先をcheckout外に置くだけでは合格にしない。受付制御がない版へ自動rollbackする経路は、この切替の運用に使用しない。現行自動rollbackを無効化して押し通す意味ではなく、専用切替の設計・承認・検証が整うまで現行経路での切替を禁止する。

**初回導入の境界**: 受付制御の導入便自体にも旧版の排出問題がある。従って解析コードの通常deployに受付制御の初回導入を相乗りさせない。先行導入の変更対象はnginx設定・mount・操作/復旧手順に限定した別の設計審査対象とする。現行deployはnginxだけの変更でもworkerを再作成するため、現行経路で先行導入すれば安全という説明はしない。この運用準備が確定するまでは、解析実行管理の本番切替は未準備とする。本セッションでCI・nginx・compose・運用scriptは変更しない。

**入口の網羅性**: backend/app/routers/tcg_*.pyとsuper_admin_tcg.pyをASTで抽出した結果、HTTP定義43件（GET21、非GET22）。対象はmain.pyの/api/v1配下登録と照合。非GET22件には読取用preview/重複確認も含まれ、22件全てが更新処理という意味ではない。初回遮断試験では22件全てを入口一覧に含め、公開2ホストで44組を試す。読取を通す例外は、サービスの副作用確認後に名前付きで限定する。HEAD/OPTIONSの扱い・末尾slash・URL正規化・認証済/未認証も別ケースで扱う。

**古い処理の完了観測**: Uvicorn0.34.0のServer.runはasyncio.runを使用し、shutdownは受付を閉じた後で接続とtasksの完了を待つ。一方、graceful timeout時にはtaskをcancelする実装である。よってshutdownログ1行やHTTP切断を解析/配信完了の証拠にしない。旧コンテナと子プロセスの終了に加え、解析runの終端状態と外部送信の照合が必要。プロセスが終了しても送信成否が確定しない場合はunknownとして切替を止め、同じ外部送信を自動再試行しない。
既存のAuditMiddlewareは応答後の監査記録であり、別スレッドや外部送信完了を保証する管理簿ではない。これを排出判定に転用しない。初回旧版で観測できない処理が残る場合は、自動で完了扱いにせず個別の確認対象にする。

#### 模擬試験の実行条件と合格表

既存ADR-115の本番相当Docker環境で、架空データ・隔離DB/Redis・外部送信stubだけを使用する。本番のenv/認証鍵/volumeを持ち込まず、本番へ接続しない。ローカルでdocker/nginx/podmanのコマンドを確認できず、このターンでは試験を実行していない。既存rehearsal-env/recon.mdは過去の調査であり、現在の試験環境として使える証拠にはしない。

| 試験 | 合格条件 | 記録 |
|---|---|---|
| 入口44組の遮断 | 通すと定義した読取例外以外は503、upstream副作用0回 | host/method/path/HTTP/upstream回数 |
| 停止状態の欠落・権限不備 | 対象更新が通る件数0 | 状態とHTTP、エラー種別 |
| 設定再読込・nginx再作成・配布の間 | 停止中の連続要求で成功更新0 | 時刻付き要求結果とコンテナID |
| rollback | 機構を含む戻し先でも遮断維持、機構なしの戻し先は開始前に拒否 | 戻し先SHAと状態/拒否根拠 |
| API応答切断後の別スレッド継続 | HTTP終了を完了と誤判定0回 | stubの開始/完了と実行状態 |
| SIGTERM完了待ち | API/worker処理完了前の強制終了0、対象処理を照合 | 親/子PID、終端状態、stub回数 |
| 完了しない処理・無応答worker | 再開/成功判定0回、追加KILL送信0 | 待機中断理由と停止状態 |
| 予約要求と再開 | queue purge0、同一runの二重適用0、起動時legacy実行0 | request/run/task IDの対応 |
| 外部送信の応答喪失 | unknownを維持、確認目的の再送0 | stub受信とDB状態の相違 |

これは実装前の検証仕様。模擬試験コードを作成したり、正式な実装カードを発行したりしたものではない。

公式根拠: https://raw.githubusercontent.com/encode/uvicorn/0.34.0/uvicorn/server.py （run/shutdown）、https://docs.python.org/3.12/library/asyncio-runner.html （asyncio.runの終了処理）。確認日2026-09-10。Context7利用不可のため公式の版固定ソースと資料を使用。ローカルPython3.14.3と本番Dockerfileの3.12を同じ試験環境と扱わない。

**自己審査REVISE**: 受付制御の保存先・戻し先の制約・44組の入口試験・9つの模擬試験を具体化。未解決は受付制御の初回導入経路と状態判定式、旧版の送信成否の観測、隔離試験環境での実証。解析実装の範囲へ運用変更を暗黙に追加しない。既に合意された一時停止方針の再承認は求めない。


### 初回導入経路の具体案（2026-09-10、審査中）

現行deploy.ymlはmain pushで起動し、nginx変更の判定は通常のAPI/worker配布を止める条件になっていない。これを前提に、停止機構の初回導入は**入口だけを更新する専用経路**として設計する。通常deployを先に走らせてから入口だけを更新する案は採らない。

1. **入口専用便を識別する**: 変更一覧の名前だけでなく内容を検査する。許可する製品設定差分はnginxのTCG受付制御、nginxサービスへの専用directory mount、これを配送/検証/復旧する手順だけ。composeの他サービス差分、backend/frontend/migration/secret差分、分類不能な差分が1件でも混ざれば入口専用便として拒否し、通常deployへ自動フォールバックしない。workflow自体の変更はPO指定Reviewerが事前に確認する。
2. **通常配布と排他的に選ぶ**: 初回便から通常deployのbuild/API切替/worker再作成/全体rollback/failure cleanupを実行しない経路とする。既存workflowと同じdeploy-productionの排他単位を使う。並行する通常配布・手動操作を許可しない。単なるpaths-filter追加ではなく、副作用を持つ全段階の条件と異常終了処理を確認する。
3. **対象を固定する**: 配送するnginx設定・composeの必要部分・手順を承認されたcommitから取り出す。稼働checkoutを更新して通常コードまで新しくした状態に放置しない。API/worker/beat/DB/RedisのコンテナID・起動時刻・イメージIDを前後比較し、変化0件を合格条件にする。前回のコード7ファイル診断はこの将来便の前後証拠には流用しない。
4. **状態と復旧材料を先に用意する**: checkout外の専用directory、所有/読取権限、初回の明示的受付許可、旧nginx設定・mount・イメージ・復旧手順を準備して検算する。初回は機構を装着する段階であり、ここで解析実行管理を有効化しない。以後の停止状態の変更は別の承認された操作とする。
5. **入口だけを切り替える**: nginxの構文/参照先/権限を事前検査し、nginxだけにmountと設定を反映する。通常deployのworker再作成や全体rollbackを呼ばない。既存nginxの接続をどう完了待ちして再作成するかは下記未解決事項であり、force-recreateだけを完成手順として渡さない。
6. **失敗時は入口だけを戻す**: 装着前の旧設定・mount・イメージへ戻して疎通を確認。解析機能は旧版のままなので、この装着便の失敗を理由にbackend/worker/DBへ手を加えない。停止機構が未装着へ戻った場合は後続の解析切替を禁止する。装着成功後の解析切替では、戻し先は機構付きの版に限定する。
7. **成功判定を分ける**: 全44組の入口契約と通常読取、API/worker等の不変、失敗注入からの復旧を確認して「停止機構装着」を判定する。これは「解析実行管理完成」「本番切替済み」と別の状態。追跡有効化へ自動で進めない。

必要な将来実装の責任範囲は、配布担当によるCI分岐・nginx/mount・検証/復旧手順、実装役による解析実行管理、PO指定Reviewerによる経路/GO範囲照合に分ける。担当者は未指定。今回の設計セッションは文書だけを更新し、別AIを起動しない。

**未解決を限定**: nginx再作成に伴う既存接続の扱い、受付許可状態の確定した判定式、入口専用経路の実コードを使う隔離試験が残る。入口は他APIも共用するため、装着時の瞬間的な接続影響を「TCGだけ」とは約束しない。具体的影響/停止時間が分かった時点で操作承認へ示す。一時停止方針へのGOを、未提示の全API停止承認に広げない。

### 模擬試験環境の所在を更新

本ローカルにDockerはないが、.github/workflows/test-rollback.ymlはubuntu-latestでDockerを確認してscripts/test_rollback_simulation.shを実行する経路を持つ。架空データで隔離コンテナを使う既存パターンがあるので、「試験場所が全くない」とは扱わない。ただし本件9試験を実行するコード/設定は未作成であり、既存試験のdispatchで代用しない。
別のtest-phase2-rehearsal.ymlはSALESANCHOR_APP_PASSWORDを受け取り、scripts/rehearsal_phase2.shは本番と同じコンテナ名を使う。今回の隔離検証へそのまま流用しない。既存資料のbackend/scripts/rehearsal_phase2.shと現行scripts/rehearsal_phase2.shを混同しない。
将来の試験は本番資格を渡さない一時runnerを推奨し、対象設計のコードを実際に抽出・実行する方式とする。配布手順の手書き再現だけでは、その手順自体の誤りを検出した証拠にしない。CI変更・試験コード作成は本セッションでは未実施。

最新main確認: origin/main=760532a9（PR #3398）。base以降のdeploy.yml、blue-green-cutover.sh、対象解析コードに変更なし。#3398は別テーマのmigration2件と登録script変更であり、この停止機構を導入した証拠ではない。読み取りで照合し、他者の差分は変更していない。
自己審査はREVISE。初回導入の経路と失敗時の責任範囲、既存Docker試験経路を特定したが、上記未解決を補う前に実装可能とは判定しない。

外部根拠: GitHub Actionsのpushイベントとworkflow concurrencyの公式資料を2026-09-10に確認。イベント/排他の仕様を本設計へ適用する案であり、このrepoの新しい専用経路が動作済みという証拠ではない。
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#push
- https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency


### 受付判定の確定案とローカル実物試験（2026-09-10）

これまで未確定だった受付許可の判定を、次の契約に具体化した。nginx1.31.1を公式ソースから一時領域でビルドし、架空のHTTP処理先で確認した。製品設定/コードは変更していない。

- 専用directory内の `allow-writes` が通常ファイルとして存在するときだけ、対象書込を許可する。内容は読まず、存在そのものを許可状態と定義する。directory不存在・探索権限なし・ファイルなし・同名directoryは拒否する。ファイル本文の読取権限を検査する契約ではない。
- 判定は要求の受付時に行い、`open_file_cache off`を明示して、許可取消後の新規要求で古いファイル状態を使わない。停止とは許可ファイルを外すこと、再開とは承認された担当が再作成すること。部署/利用者の認証・アクセス権を置き換えるものではない。
- 対象の正規化済みURIは `/api/v1/tcg` と `/api/v1/super-admin/tcg` の境界付き配下。GET/HEAD/OPTIONSはこの停止判定の対象外、それ以外を判定する。既存の認証とルーティングは維持する。今回試験はPOSTのpreview/重複確認も含めて一時停止する契約であり、POST読取例外を追加する場合は別途照合する。
- 許可がなければ対象要求を503で終え、処理先に転送しない。許可ありは既存処理へ渡すだけで、要求自体の成功を保証しない。
- 取消前に通った要求は取り消さない。その処理の完了待ちが別途必要。「ファイルを外した瞬間に全処理が止まる」という表示/判断は禁止する。

試験した判定式（設計上の抜粋、製品設定へ未反映）:

```nginx
# http context
map $uri $pmg_target {
    default 0;
    ~^/api/v1/(tcg|super-admin/tcg)(/|$) 1;
}
map "$request_method:$pmg_target" $pmg_needs_allow {
    default 0;
    ~^(GET|HEAD|OPTIONS):1$ 0;
    ~:1$ 1;
}
map "$pmg_needs_allow:$pmg_allowed" $pmg_deny {
    default 0;
    "1:0" 1;
}
# 対象の各server context
open_file_cache off;
set $pmg_allowed 0;
if (-f /etc/salesanchor/pmg-cutover/allow-writes) { set $pmg_allowed 1; }
if ($pmg_deny) { return 503; }
```

本実験では状態パスを一時directoryへ、listenと転送先を127.0.0.1へ変更している。両hostは同じ試験serverにHostヘッダーで渡したため、本番の独立した2つのTLS server blockへの組込み試験ではない。外部通信、DB、実際のSales Anchor handlerは使っていない。

#### 実測結果

| 検証 | 結果 |
|---|---|
| 非GET22入口×2host、許可なし | 44/44が503、処理先到達0 |
| 同44組、許可あり | 44/44が試験処理先の200、到達44 |
| 同44組、許可取消後 | 44/44が503、処理先到達0 |
| 同名directory・状態directoryの探索権限なし | 2/2が503 |
| 末尾slash・重複slash・URLエンコード・dot segment | 4/4が503 |
| GET参照と対象外POST（2host） | 4/4が試験処理先の200 |
| 長い処理の受付後に取消 | 新規POSTは503、先行処理は200で終了 |
| reload | 新worker PIDの出現を確認、取消後POSTは503、先行処理は完了 |
| nginxの終了と再起動 | 新master PIDを確認、許可なしを維持して503 |
| 全assertion | **151/151成功、exit0**（転送件数・PID確認を含む） |

初回試行はconfigureの未対応optionで失敗し、取り除いてビルド成功。初期nginx起動はsandbox内のOS情報参照拒否で未実行だったため、承認レビューを通したローカル試験として実行し成功した。初回148件からreloadの実体確認/再起動を追加して最終151件。失敗を本番障害や受付判定の失敗と混同しない。

根拠保存: `/tmp/reports/pmg-nginx-admission-probe-3396/`（probe.py、実行結果、実際のnginx.conf、ルート一覧、build/errorログ、環境情報）。ZIPは同名.zip、SHA256=e7537c80a7a1b91159ab624e734a493ee992b2f2555aac4d8345fd0bf484fb76。probe.py SHA256=3d8ad783e4b9b063e08e774622a14790e79402b538368ba0bed03736455704c4。成果の要点は本節を正本とし、一時ファイル消失後も試験範囲/限界を残す。

#### 入口更新時の接続の扱い

nginx公式仕様ではreload後の旧workerが既存接続を処理し続ける。今回の試験でも、受付済み要求が取消/reload後に完了することを確認した。従って停止機構導入前の旧workerが残る期間を「遮断完了」としない。既存接続/旧workerの消失確認と、対象要求の処理完了照合を必要条件とする。
追加mountが必要な初回のDockerコンテナ再作成は、このローカルreload試験とは別。既存接続を打ち切らずに再作成できると断定しない。SSEを含む長時間接続が残り、所定の作業枠で自然に終わらない場合は、強制終了に切り替えず導入を保留する。作業枠の長さ/瞬間的な全API接続影響は運用準備で確定し、今回GOから推定しない。

設計自己審査: **REVISE**。受付判定式と許可取消/reloadの挙動には151件の実物根拠が得られた。残る本番前提は、初回mount導入時の接続/失敗復旧、Linux/Docker上の実組込み、旧版解析/配信の完了照合。ローカルnginx試験を本番相当の9試験完了とはしない。

公式仕様: https://nginx.org/en/docs/control.html 、https://nginx.org/en/docs/http/ngx_http_rewrite_module.html 、https://nginx.org/en/docs/http/ngx_http_core_module.html#open_file_cache 。2026-09-10確認、Context7利用不可のため公式資料で代替。PCRE2は公式release10.46を実験ビルドに使用。本番PCRE版との一致は未確認。


### 復旧・完了待ち試験の追加結果（2026-09-10）

同じローカルnginx1.31.1の試験に9項目を追加し、**160/160成功、exit0**。
追加の実測は、不正な設定でreload失敗した際にmaster/旧workerが存続すること、拒否が維持されること、正しい設定へ戻して新workerが立ち上がること、QUIT時に新規接続が停止する一方で受付済み要求を待ち、その要求が200で完了した後に正常終了すること、再起動後も拒否が続くこと。
「QUITなら新規接続も使える」とはしない。この方式を入口全体へ適用するとTCG以外の新規接続にも影響するため、初回導入での入口全体停止を自動的な選択にしない。
成果物: /tmp/reports/pmg-nginx-recovery-probe-3396/ と同名.zip。ZIP SHA256=cb6994733506ebe845244af0f2fc9c182e88adfd556444578a7cb832cadcb973。前回151件の成果物は上書きせず保持。macOS上の試験であり、本番Docker/既存SSE/外部配信の成功試験ではない。

### 既存読取領域を利用する改訂案（2026-09-10、最新の初回導入案）

**選択理由**: docker-compose.yml:18に `./nginx/htpasswd.d:/etc/nginx/htpasswd.d:ro` が既にある。.gitignore:119はこの領域をGit管理外とする。deploy.yml:104,914はその中のdesign-siteだけを生成/削除する。従って、この領域内の独立したpmg-cutoverサブディレクトリを停止状態専用に使う案を採り、新しいmount追加案を第一候補から外す。checkout外という場所自体ではなく、通常配布/復旧が状態を置換しないことが要件である。

| 項目 | 改訂案 |
|---|---|
| ホストの状態場所 | /home/ubuntu/salesanchor/nginx/htpasswd.d/pmg-cutover/allow-writes |
| nginxからの参照場所 | /etc/nginx/htpasswd.d/pmg-cutover/allow-writes |
| 他ファイルとの境界 | design-site認証ファイルは読取/変更しない。停止専用directoryだけを扱い、公開URLへ配信しない |
| 権限 | 承認された運用担当だけが作成/取消。nginxは探索/statのみ。稼働owner/groupと必要modeは適用前検査で確定し、認証directory全体のchmodをしない |
| 判定 | 通常ファイルの存在を受付許可とする前節の実測済み判定。パスだけを上記へ変更する |
| 配布との関係 | 該当状態パスの追加/削除/上書きをgit差分へ入れず、通常配布・rollbackでも保持する。現在のgit check-ignoreは当該パスを除外する |

**初回導入の順序**:
1. 入口専用経路で対象commitと差分を固定し、通常配布/全体rollbackを起動しない。稼働nginxに既存directoryの読取接続があることを実機のmount情報で確認する。composeファイルの存在だけで合格にしない。
2. 既存認証ファイルを触らず専用サブdirectoryと明示的許可状態を用意する。host/containerの同じ状態を読み取れることを確認する。状態が読めなければ設定を適用しない。
3. 旧設定を退避し、候補設定を本番と切り離して構文検査する。現在bind mount中の設定ファイルをホスト側で同じinodeのまま更新する案とし、更新完了後にhost/container両方のdigestを照合してからnginx -tを実行する。inodeを変える通常のgit checkout/copy置換を混ぜない。書込み中にはreloadしない。
4. 構文/digestが一致した場合だけreloadする。正常な候補の新workerが出現するまで旧設定で動作している可能性を残す。失敗なら旧設定を同じinodeへ戻して再検査し、旧workerを強制終了しない。設定書込み中のプロセス異常/再起動に対する復旧は隔離試験に含める。
5. 停止機構を知らない旧workerが全て終了してから装着完了とする。長時間接続で残る場合は待機/保留し、強制終了しない。新workerがサービスを継続するreloadを使い、入口全体をQUITして待つ案を初回の既定にしない。
6. 当該便では許可状態のまま装着を終え、API/worker/beat/DB/RedisのID・起動時刻が変わっていないこと、認証と通常参照を維持したことを確認する。後日の停止は許可状態の取消で行い、受付済み処理の照合は別途実施する。

**残る制約**: 実機mountの確認は前回のファイルhash診断に含まれていない。この追加構成は現時点では未確認。稼働ファイルの同一inode更新/失敗復旧もDocker実証前であり、上記をそのまま実行カードにはしない。通常deployのnginx再作成経路と自動rollbackが停止機構のない設定へ戻らない条件は継続して必要。nginx/htpasswd.dを参照する既存手順の変更時にはこの状態保存も再点検する。

**接触面と維持**: 認証情報自体の変更は不要だが、認証ファイル用directory内に別用途の状態を追加するため、設計レビューでは境界/権限/削除範囲を確認する。手動git clean -x等をこの切替手順へ追加しない。入口専用経路の維持担当は本番配布担当、前後の不変条件と状態保持は前記の隔離試験で守る。仕組みは未実装で、既存CIが既に強制しているとは扱わない。

自己審査REVISE: 判定とreload/復旧/QUITの挙動は160件のローカル実測で確認。初回導入案は新規mount/入口再作成を不要にする方向へ縮小した。残件は既存mount/権限の実機照合、Docker上の同一inode更新と失敗復旧、旧版の解析/配信完了照合。設計草案の修正であり、POの承認原文や本番GOを追加していない。


### 離席中の最終確認・設計審査・引き継ぎ（2026-09-10）

**PO承認の原文**: 「離席するので最後まで進めてくれ、事前にPRマージも承認する」。直前に提示した本件の残件調査と文書PR #3396の保存/マージに適用する。製品実装、停止機構適用、手動の本番停止/変更、他PRマージには広げない。番号付きGO発言へ書き換えない。

**保存領域の実機確認**: nginx39782f43a552を対象に読取。/etc/nginx/htpasswd.dは/home/ubuntu/salesanchor/nginx/htpasswd.dのbind、RW=false、両側inode839048、UID/GID1000/1000、mode775。/etc/nginx/conf.d/default.confもbind・RW=false、両側inode659245、UID/GID1000/1000、mode664。psでのプロセス照会は失敗したが、それ以前のmount/stat出力は取得済み。/proc statusの限定読取へ切り替え、nginx master UID/GID0、worker4個のUID/GID101を確認（exit0）。認証ファイルの本文・一覧は取得していない。
将来作成するpmg-cutoverサブdirectoryはowner/group1000/1000・0755、allow-writesは同owner/group・0644を候補とし、既存親directoryのmodeを変更しない。nginx workerは探索でき、コンテナmountは読取専用を維持する。実際の作成・書込みは未実施。システム内の他主体の権限全体を検査した証拠ではない。

**最新mainへの追従**: origin/main a0c0eb7fを取り込み、台帳2件の競合は本件行と他PRの新しい状態/根拠を双方保持して解消した。PR #3393により解析はname-first-v3-workとなった。旧調査のname-first-v2/旧行番号は過去時点の記録とし、本便実装では現在のv3判定・作品根拠2列・手動商品訂正の保持を維持する。v3のルールを本便で再設計しない。
最新のtcg_analyzer_svc.pyでは共通解析入口1011、commit1260/1275/1286、任意master rollback785/847/948。途中保存3か所と全体rollback3か所という設計根拠は残る。load_work_master:398は通常SELECTで、必須作品masterのエラーを任意master欠落と同じ空代替にしない。tcg_extraction.pyはGemini呼出し時に作品masterを渡す。これを削除しない。
手動訂正がある商品を解析がスキップするv3の契約を、単一トランザクション化後も維持する。受入試験に「v3の作品根拠・明示訂正・未解決時の扱いが前後で変わらない」を追加する。本セッションでその製品試験を実行したとは扱わない。

**Architect自己審査の最終判定: REVISE（修正必要）**。同一AIによる自己審査であり、独立した第二者レビューではない。

| 観点 | 現在の判定・根拠 |
|---|---|
| 解析実行記録の必要性 | 自動/手動入口と最新v3コードを照合。途中commit3、rollback3の根拠あり |
| 状態/再試行/API/配信停止の契約 | 草案として具体化。旧結果から成功推定しない、同一keyの重複適用0、failed/unknownの未解決停止を規定 |
| 受付判定・reload・復旧 | ローカルnginx160/160成功。Docker/本番TLS/実handlerの合格ではない |
| 稼働接続/版/読取領域 | 診断時のDB一致、対象ファイル一致、mountと権限を確認。過去のhash一致をmain前進後の全コード一致に流用しない |
| 初回導入/停止復旧 | 既存bindを使うreload案まで具体化。同一inode更新と異常時復旧のLinux/Docker試験未実施 |
| 旧処理の完了 | API接続終了だけでは別スレッド/外部送信完了の証明にならない。実際の旧版処理と外部送信の照合は未完了 |
| 実装範囲 | 解析機能と先行する入口専用配布の責務を分離。後者の配布/復旧経路が未実装・未実証 |

**次の担当が行うこと**:
1. 本番資格を持ち込まないLinux/Docker検証環境で、前記9試験に同一inode更新・途中書込失敗・旧設定復旧を加え、実際の入口専用手順を検証する。現行SA-18専用workflowをそのまま実行して代用しない。
2. 旧版の同期解析/配信を長時間処理・通信断のfixtureで検証し、「完了」「失敗」「確認不能」の照合手順を確定する。確認不能を再送/成功補正で埋めない。
3. その根拠で設計を再審査する。合格後にADR-113の正式カード検査を行い、POの明示的実装承認が揃ってから実装役へ渡す。本書の草案を実装カードとして使わない。
4. 解析実行記録の後に、配信履歴/内容固定/重複配信防止、最後に総合画面統合へ進む。完了済みPR #3386は再実行しない。

**今回の終了境界**: 調査・設計草案・自己審査・根拠の文書保存まで。文書マージは設計合格/製品完成/本番切替完了を意味しない。ローカルDockerは利用できず、CI設定/運用scriptの変更は本セッションの担当範囲外なので、Docker実証を未実施のまま成功扱いにしない。PRマージ後の既存GitHub自動処理の状態は別に読み取り確認する。


### Linux/Docker隔離検証便（2026-09-10、mode: handoff）

本節は未検証の切替機構を本番から切り離して検証するための試験実装設計。親の製品設計はREVISEのまま。
PO原文: 「次に進む、また離席するのでPRマージとデプロイまで進めてくれ」。担当切替確認への返答「担当して良い」、実装モデル指定「codex terra」。設計担当は実装せず、Codex Terraへ委任する。
作業場所例外の質問への返答「許可する進める」を受領。release/pmg-cutover-rehearsalをorigin/main 89ad29ae起点で作成。既存worktree削除なし、UUID・分割台帳・フックを登録し、開始/所有検査を通過した。旧GOを転用していない。

目的: 同一ファイルへの設定更新と拒否状態の持続・異常復旧について、Linuxコンテナで観測可能な証拠を得る。試験成功を製品切替完了としない。
対象ファイルは tests/pmg_cutover_probe.py と .github/workflows/pmg-cutover-probe.yml の新規2件。製品nginx設定・deploy.yml・compose・DB・本番scripts・secretsは変更しない。
既存test-rollback.ymlにubuntu-latest/Docker隔離試験の実例がある。docker-compose.ymlのnginx:1.31.1を使用し、実際のimage digestとDocker版を出力する。独立したネットワークと一時directory、ランダムなcontainer名を使う。停止/削除は自分で作成した試験container/networkだけをIDで照合して行い、他資源を列挙して一括操作しない。

#### 試験契約

- Python3.12標準ライブラリとDocker CLI、runnerのopensslを用いる。実データ/実資格なし。localhost以外のAPIへ送信しない。image取得以外の外部接続を試験に要求しない。
- 同じホスト一時directory内に専用状態directoryと通常ファイルの設定を作り、nginxへread-only bindする。設定ファイル単体と状態directoryのmount種別/RW=false、host/containerのinode/digestを検査する。
- 前節の判定式を試験fixtureに含める。TLS serverをapp/apiの2個に分け、自己署名証明書でSNI/Hostを一致させた要求を送る。転送先は独立した架空HTTPサーバーで、到達件数を記録する。製品認証の試験ではない。
- 許可なし→許可あり→取消を両hostの2経路（tcg/super-admin/tcg）で照合。対象POSTは503/200/503、拒否時の転送0。参照GETと対象外POSTの200を維持する。許可と同名directoryは拒否する。
- 稼働設定を同一inodeのまま更新し、host/container digest一致、nginx -t成功、新worker出現を確認してreloadを判定する。停止状態を維持する。
- 不正設定へ更新した場合はnginx -t失敗。reloadを試験しても旧workerが残り拒否を維持することを検査。退避済み設定を同一inodeへ戻し構文成功・新worker出現・拒否持続を確認する。
- 途中まで書かれた不正設定の状態で試験containerを停止・再起動する。起動失敗を明示して記録し、退避設定の復元後に起動でき拒否が持続することを検査する。復元前の入口停止を「無停止成功」とは扱わない。
- 長時間の架空要求が開始したことをEvent等で確認してから許可取消とreload。新規対象POSTは503、受付済みの要求は解放後200で完了する。固定sleepだけで処理開始/終了を推定しない。
- 全assertionの名前/成否、試験対象commit、版、digest、例外の全文を結果JSON/ログへ保存する。必須シナリオ欠落やDocker不在は非0終了し、skip成功にしない。

CIはpull_request（本2ファイル変更時）と当該releaseブランチへのpushで起動する。permissionsはcontents:read、ubuntu-latest、Python3.12、timeout-minutes:15。本番secrets/SSH/deploy環境を指定しない。失敗時も結果をartifactへ保存する。既存checkの無効化なし。
対象試験コード自体をCIで実行するが、将来の本番配布scriptを検証した証拠にはならない。入口専用配布経路と旧処理の完了照合は引き続き別の未了条件。

代替: ローカルmacOS試験のみではDocker bind/restartの証拠不足。既存SA-18試験の流用は対象が異なる。専用隔離試験を選択する。実行時間/Actions利用枠を消費するが、本番データの読書きは0件。
維持担当: Terraが試験を実装、設計担当が差分とCI結果を確認する。将来配布担当は本試験を必要に応じ実手順の回帰試験へ更新する。外部企業の実績値は不要。ローカル契約と実コンテナの成否で判断する。
接触面: POには成否と限界を報告、実装役には本節の契約を渡す。CIに隔離job追加、DB/本番/外部配信への接触なし。mainマージによる既存自動deployは別に実行状況を確認する。

Architect自己審査: APPROVE（本節の隔離試験実装だけ）。根拠は既存CI/composeの実物と前節160件のローカル検証。本番投入設計はREVISE。審査は同一AIであり独立レビューではない。未検証の製品設計を実装可能に読み替えない。
公式仕様確認: Context7利用不可のため2026-09-10に https://docs.docker.com/engine/storage/bind-mounts/ と https://nginx.org/en/docs/control.html を直接確認。

試験ネットワーク補足（2026-09-10）: Docker28.0.4のinternal networkは外部接続設定を行わず、初回CIで公開ポートを取得できなかった（recon同日節）。通常の専用bridgeを使い、公開先を127.0.0.1に限定する。外向き通信の遮断保証は設けないが、試験の送信先はlocalhostと架空処理先に固定し、実資格を与えない。必須assertionは維持する。この試験fixture修正を自己審査APPROVEとし、製品設計REVISEは維持する。

### Linux/Docker実測結果と差分審査（2026-09-10）

HEAD879aa1f423f00ed15b9af1714f91070d813ac8f6のpush試験run34460419959/job102816671239は99/99 assertion成功、errors0、exit0。設計担当がActionsログの結果JSONを直接取得して確認した（他者の報告だけではない）。Docker28.0.4、Python3.12.14、nginx1.31.1 digest sha256:608a100c71651bf5b773c89083b4a1ad7ef4b2bd05d7a7e552271e03123692ad。
再起動前app/api公開ポート32769/32770、再起動後32773/32774を実測。前回の古い接続口再使用が整合しないことを確認し、再取得で復元後TLSと拒否維持が成功した。
同一inode・host/container digest、両TLS入口の許可なし/許可/取消、拒否時転送0、不正reload時の旧worker保持、途中設定の起動失敗、復元後の再起動、受付済み長時間要求の200完了を確認。自作資源の後始末エラー0。
根拠: https://github.com/shingo-ops/salesanchor/actions/runs/34460419959/job/102816671239 。artifact10145284758、zip SHA256=7d6385d6df251f98b73fb281a219409a9c7c5ce196255225ffd9ab0b777bc889（CI保持7日）。取得結果は/tmp/reports/pmg-cutover-3408/push-results-879aa1f4.json。
試験コードはPO指定Terra、設計/コード差分審査はroot。差分審査APPROVEは試験2ファイルのみ。独立した設計第二者レビューとは称さない。製品の初回配布手順・旧版の実送信完了照合は未実装/未確認で、親の製品設計REVISEを維持する。画面は未完成。

## 初回組込みと旧処理完了の契約案（2026-09-10）

本節はPlannerが前節のLinux/Docker実測とrecon「入口配布・旧処理照合の再調査」を基に具体化した草案。PO「次を進めるPRマージまで」は文書保存/マージの承認。下記方式への事業上の合意や本番操作GOを代筆しない。前節までの一時停止方針・failed/unknown停止方針の既承認は維持する。

### 目的・対象と変更前後

利用者の取込・解析・配信を、途中のまま成功表示したり二重送信したりせず、新しい履歴管理へ切り替える。いまは旧APIの停止やlast_resultから外部送信完了を証明できない。変更後は入口の拒否成立、処理の排出、結果照合、再開の各判定を別々に保存し、証拠が揃わなければ次へ進めない。
対象は入口専用組込みと通常配布/復旧との整合、旧実行の分類手順。履歴API・画面の実装、旧結果の成功補正、配信再送、running2件の復旧、辞書・v3判定変更は本便の対象外。文書差分は既存design/recon/tasks/evidenceの4件だけ。製品設定・CI・運用scriptの変更は0件。

### How：組込み・停止・復旧の段階

| 段階 | 必須の観測と遷移条件 | 不成立時 |
|---|---|---|
| 0 配布経路の保護 | 専用経路と通常配布の相互排他に加え、保留状態を後続配布が確認して止まる契約を先に実装/試験。状態は認証ファイルとは別の専用子directoryで持つ。既存secret本文は読まない | 現行deployの直列化だけでは合格にしない。入口の本番変更へ進まない |
| 1 設定の装着 | 差分/対象SHA、退避設定digest、host/container inode、対象container ID・起動時刻・nginx worker世代を固定。許可ありで制御を装着し、同一inode更新とnginx -t/reload。変更前後の参照/認証/streamの結果を比較 | 初回装着失敗は未装着として元設定へ復帰。まだ「遮断済み」と記録しない |
| 2 受付を停止 | 制御のない旧nginx workerが全て終了したことを確認後に許可を取消。両hostの対象書込拒否と転送0を検証。全writerの新規投入・取得停止も別に成立させる | 旧worker残存・無応答・裏口未分類を0件にしない。強制終了せず保留 |
| 3 排出と結果照合 | API/worker全所有者と対象一覧を固定し、下表の分類を実施。処理中0・未分類0・完了確認不能0が揃い、停止後の新規投入0を確認 | 時間経過・40秒stop・HTTP接続数0では代用しない。外部再送なし |
| 4 版の切替 | 前提維持を再確認して追加型migration/コード切替/実DBと版の一致を検査。新しいrun管理の成立前に受付を開けない | 拒否機構を含む検証済み基準版へ復旧。既存の自動rollbackが拒否なし版へ戻す経路は禁止 |
| 5 再開 | 切替・DB・旧処理の証拠を保存し、既定の再開承認を照合してから許可状態と処理取得を再開。再開直後も異常状態0を検査 | 拒否を維持して保留理由を残す。文書PRの承認を再開許可に読み替えない |

重要な境界: 段階1の装着失敗で元の未装着設定へ戻すことと、段階2以降の拒否状態を維持した復旧は別。後者で拒否なし旧設定へ戻すと遮断を失う。初回の退避設定を一律に戻し先とする手順は採らない。
配布中の異常だけでなく、専用job終了後にqueuedの通常deployが動く場合も対象。GitHubの実行中排他だけでは保留状態の持続を保証しない。永続保留のスキーマ・権限・所有者・照合不一致/欠落時の扱いと、既存通常配布への初回導入順序はまだ未確定。標準配布全体への影響を調査/試験するまで本節を実行カードにしない。

### 旧処理の分類：終了・成功・未変更を混同しない

照合票は対象job/配信先ID、固定した所有container/プロセス世代、観測時刻、外部処理の段階、DB記録の有無と根拠、分類理由を持つ。本文・資格情報は載せない。旧コードに存在しないrequest IDや履歴を生成済みとみなさない。

| 観測 | 分類と扱い | 次へ進むための証拠 |
|---|---|---|
| 同期処理が実行中、又は所有者が応答しない | 処理中又は確認不能。切替保留 | 同じ所有世代で実行終了を確認。外部/DB結果も別に照合 |
| 外部完了と対応するDB結果を特定できる | 成功確認済み候補 | 後続送信で上書きされていないことを含め対象対応を確認。last_*の単独一致は不可 |
| clear前の検証失敗を当該実行に結び付けられる | 未変更の失敗候補 | 外部変更開始前だった証拠と実行終了。一般的なerror文字列だけでは不可 |
| clear後の失敗、取消、外部応答欠落、DB記録欠落 | 部分変更又は確認不能。成功/未変更へ補正しない | 実行終了と外部結果の個別確認。自動再送・対象sheetの自動修復はしない |
| 現在のシート内容しか取得できない | 過去実行の完了根拠として不足 | 後続書込との区別がつく当該実行の根拠。件数が同じでも成功の証明にしない |

既存取消14件は「呼出し取消後にも外部処理が進む」根拠。過去の実送信との対応づけを回復する根拠ではない。旧実行の全件列挙方法と、既存ログ/外部履歴だけで不足するケースの解消経路は未確認。新しい観測を追加するだけでは過去の欠損を埋められない。

### 受入条件・次に行う試験

次の試験は実行前の契約であり、PR #3408の99項目に含まれるとは扱わない。実装する配布手順そのものを隔離環境で呼ぶ。手順を別の短いfixtureへ書き直して試験しない。

| ID | ○判定の条件 | 検証方法 |
|---|---|---|
| I1 | 実nginx設定の両TLS hostで対象書込のみ拒否、変更前後の認証/参照/stream結果一致 | 実設定を入力にして証明書/外部上流だけ隔離。通常のSNI選択・同一443で比較 |
| I2 | 制御装着前のworkerが残る間は遮断成立を宣言しない | 旧接続をEventで保持し、世代終了前後の判定を検査 |
| I3 | 装着途中の書込失敗・nginx -t失敗・HUP失敗で各段階の正しい基準版へ戻る | 各故障を注入しinode/digest、拒否、API/worker ID不変を照合 |
| I4 | 遮断後の専用job失敗→後続通常deployでも拒否を解除せず、旧処理の再作成0 | 実配布入口を連続実行。保留の読取不可/欠落/所有者不一致も成功扱いしない |
| I5 | 40秒超の処理でも時間満了を排出成功にしない | 実処理境界をstub化し明示開始/解放。強制終了0を検査 |
| I6 | clear前・clear後・append成功後DB未記録・待機task取消の4境界を正しく分類 | 実関数へ段階別故障を注入し架空sheetとDB記録を突合 |
| I7 | worker無応答・未分類所有者・再開競合があれば切替/再送0 | 所有世代を固定した複数writerで時系列を制御 |
| I8 | 既存通常rollbackが拒否なし版へ戻せない | 退避SHAが制御導入前の場合と制御導入後の場合を実経路で試験 |

### Why・代替案・維持

同一inode更新は99項目で基礎挙動を確認したが、実nginx設定と通常配布へ組み込んだ結果は未確認。既存blue-greenの40秒停止やlast_resultだけを使う案は観測不足なので採らない。固定時間を伸ばす案も完了の証拠にはならない。
専用組込み＋永続保留案は安全条件を分離できる一方、失敗時に通常の配布まで待たせる可能性がある。未確定の影響範囲と初回導入順序を残してAPPROVEを出さない。外部企業の改善率は本件の実行正当性を証明しないため不要。公式資料と同版コード、実測の適用限界をWhyの根拠とする。
維持担当は設計担当が契約/審査、PO指定Codex Terraが合格後の実装、配布担当が本番前後の照合。I1〜I8は将来の回帰検査であり既存CIが強制しているとは称さない。今回の文書CIは構造/参照/申告の確認で、製品の動作検証ではない。

### Architect自己審査の更新

判定REVISE（製品の初回切替設計）。同一AIがPlannerの草案作成後に審査したもので独立した第二者レビューではない。
根拠が揃った点: PR #3408実測と本番設定の試験差、旧配信2外部呼出し＋後置DB記録、40秒停止、通常配布/復旧の実経路をファイル行で特定し、8つの○×条件に落とした。
未解決: 永続保留の初回導入と全配布経路の強制、旧実行を漏れなく列挙し外部結果へ対応付ける具体手段、I1〜I8の実測。自己審査で不足を発見したため合格扱いしない。ADR-113の正式実装カードは発行しない。本節の文書保存/マージと製品設計の合否を区別する。
次の一手: まず旧実行の観測手段と永続保留の導入経路を調査し、実装対象ファイル/契約を確定する。その後に隔離統合試験の設計を審査・カード検査してTerraへ渡す。画面統合はその後の製品履歴実装に続く。

## 配布保留の具体契約と保証範囲の訂正（2026-09-10、草案）

### 先に訂正する範囲

前節の「旧実行を漏れなく列挙」は、切替境界に残る処理とその結果不明を対象とする。全過去配信の復元まで必須とする読み方は撤回する。既存§3の「導入前の最新記録を表示、存在しない過去runを生成しない」という契約を維持する。過去の記録欠落と切替時の処理中/結果不明を混ぜない。これは既承認条件の再承認依頼ではない。
新しい観測を追加しても既に動いている旧threadは自動登録されない。API監査やログ保管設定も全実行の証明ではない。切替境界の全所有プロセスを対象にした観測方法は引き続き未確認で、旧処理排出を完了扱いしない。

### POに求める判断（未回答）

推奨案: PMG切替中と異常保留中は通常の本番デプロイも停止する。後続配布が拒否機構や旧処理を変更することを防ぐ一方、他機能の更新も待つ。以前合意した「取込/解析/配信の一時停止」だけから、全機能の配布停止まで承認済みと推定しない。
代替: 他機能を配布できる分離方式を検討する。ただし現行通常配布は文書変更でもAPI/workerを更新するため、変更領域別の安全な配布分離を別途実装/検証する必要があり、本案より対象が広い。無停止・所要時間を約束しない。
POへ質問した文: 「PMGの切替中と、異常で保留した間は、通常の本番デプロイも停止する方式を採用してよいですか？ 停止状態を後続デプロイが消すのを防げますが、他機能の更新も待つことになります。」回答受領前は推奨案を採用決定にしない。

### 推奨案のHow（採用時に満たす契約）

永続する配布保留記録とnginxのallow-writesは別の意味を持つ。前者は版変更の可否、後者はHTTP書込受付の可否。片方の欠落を他方の許可と推定しない。保存場所候補は既存の専用子directory内state.json。認証ファイル本文/secretは含めない。

| 状態 | 通常配布 | 専用操作/次への条件 |
|---|---|---|
| 未初期化/読取不可/未知version/壊れたJSON | 拒否 | 初期化専用操作だけ。通常deployに自動初期化させない |
| idle | 許可候補 | 稼働版/状態revisionを検査し、実行中排他を取得してから変更開始 |
| preparing | 拒否 | 所有する切替だけが設定装着を行う。SHA/対象IDが変われば保留 |
| blocked | 拒否 | HTTP拒否と新規投入停止を確認し、排出/照合へ |
| switching | 拒否 | 排出/照合合格を根拠に、所有する切替だけが新方式へ変更 |
| hold | 拒否 | 原因と同一切替IDを照合した復旧のみ。job終了や時間経過でidleに戻さない |

記録項目候補: schema_version、revision、phase、cutover_id、owner_run_id、対象commit、既知の安全な復旧commit、更新時刻、根拠参照。機密なし。owner_run_id一致は操作認証の代わりではなく整合検査。状態更新は同じ排他の下で旧revision一致を確認し、同一directory内の一時ファイルから置換する。nginx設定の単体bindは別物であり同一inode更新を維持する。更新途中失敗/旧revision競合/読取不可は拒否する。
GitHub同groupの排他と、手動経路を含むホストでの排他を区別する。通常jobの実行中にpreparingへ割り込ませず、専用jobが終了してもholdを残す。単純な「開始時にファイルを読むだけ」では確認と変更の間に競合するため不合格。複数SSH stepをまたぐ所有の確保・中断時の回収方法は実装前に確定/試験する必要がある。

### 初回導入の順序と影響箇所

1. まず実際の通常配布・直接blue-green・SA-18リハーサル・復旧入口を列挙し、同じ検問を通る対象を確定する。全管理者の任意Docker操作まで技術的に封鎖できるとは称さない。
2. 通常配布の最初の本番変更より前に検問を置く。LP同期/認証ファイル更新より後に置かない。初回state未作成は配布拒否となることを明示し、未初期化をidle扱いしない。
3. 初期化専用経路を同時に用意し、既存stateの上書きなし、旧配布の終了確認、root directory/所有/権限/版の検査後にidleを作る。初期化のために製品API/workerを再起動しない。
4. 通常配布と復旧が新契約を守ることを隔離試験で確認した後に、nginxの停止制御と切替へ進む。未導入版へ戻るrollbackを無条件に許可しない。

将来変更が必要な既存接触点: .github/workflows/deploy.yml（最初の検問と復旧）、scripts/blue-green-cutover.sh（手動入口）、scripts/rehearsal_phase2.shと対応workflow（対象に含める場合）。共通検問/初期化/専用切替の新規ファイル名は未確定。これらは今回変更していない。現行AGENTS.mdのdeploy.yml/本番script変更禁止を、設計草案やマージ承認で解除したとは扱わない。実装前に担当範囲と正式カードを確定する。

### 受入条件・維持と自己審査

前節I4/I8を具体化: idle以外の全状態で通常配布の本番変更0、初期化再実行で既存記録上書き0、異常job終了後の通常配布変更0、同時開始で所有者1、旧revision更新0、guard未導入版への復旧0を実経路で検査する。これらは未実施。既存99項目はnginx基礎動作の根拠に限定する。
設計担当が契約と状態遷移を維持、PO指定Terraが明示的に許された実装だけを担当、配布担当が保留/解除の操作根拠を保存する。外部企業の実績値は不要。本件固有の副作用境界と競合試験が直接の判定根拠となる。
Architect自己審査REVISE。同一AIの自己審査。改善点は過去全件復元の過剰条件を除外し、配布可否の状態と初期化順序/検問位置を明記したこと。未解決はPOの配布停止範囲判断、複数SSH/手動入口の所有制御、切替境界の旧処理観測、実統合試験。実装カード未発行。PO判断を待つ間も無関係な製品修正へ移らない。

## 方針承認と総合ページ接続便（2026-09-10）

POへ、通常業務中の全停止ではなく、本番切替中に取込/解析/配信を一時停止し他の更新反映も待たせる手順と説明した。POの「理解した」は承認に扱わなかった。その後の原文「承認する推測は禁止して事実確認を怠らずに確実性を重視して最も効果があり、現状把握の粒度が細く、精度が高いエビデンスを確立して安全に進めてくれ、確立したならページ作成まですすめる」を受領。配布保留の方針採用と根拠確立後のページ実装を承認として記録。具体的本番停止の日時/操作は未承認、製品切替全体の審査REVISEは継続。

### ページ接続の設計と根拠

main4f1c2b81の実APIは取込progress/itemsを提供済み。tcg_import_progress.py:36-46のcoverage、read_progressのanalysis.execution_state=unrecordedとNULLをUIの事実とする。Terraの初回読取に「API未実装」の検索漏れがあり、rootが実ファイル/ルート存在を指摘、Terraが本文/実PGテストを読み訂正した。旧完了カードを再実行しない。
ページ作成は既存の読取APIと既存操作を接続する独立した範囲として進められる。新run管理の導入や本番配布制御を前提にしない。本便の成功を親設計の解析実行/永続配信履歴完成へ広げない。

目的: 既存インポートページで、選択取込の進捗・要対応明細と、全体の配信候補/最新結果を区別して確認できるようにする。既存入力・確認工程・配信確認ダイアログは維持する。配信ボタンはユーザー操作時だけ既存APIを呼び、自動送信しない。配信範囲は現在の全体データで固定。
対象: TcgLineImportPageへワークフロー表示を追加し、配信領域はTcgDistributionPageと共有する内容部品へ切り出す。既存route/権限を維持、PageLayoutの入れ子は禁止。実装ファイルの所有範囲はカードに明記する。Backend/DB/CI/本番設定は変更0。

How:
- 既存取込履歴と新規取込結果からimport IDを選べる。選択をURL search parameterへ保存し、再読込後に同じIDで取得。選択なしでは取込APIを呼ばず案内を表示。選択ID/フィルタ/ページ変更で旧応答を無効化し、別取込の値を混ぜない。
- 工程は取込（投稿数）、抽出（ジョブ数）、解析結果（商品数）。抽出の完了はdone/empty/errorの合計、成功と分ける。解析は結果あり/なし/要確認と「実行履歴は未記録」を表示し、結果数から成功率を作らない。coverage非completeとtotal:nullは「記録なし/確認待ち」を区別し、0や100%にしない。
- 明細は既存itemsのall/needs_review/extraction_error、limit25、offsetを使用。NOTE_JA、理由、元の商品情報と結果有無を表示。理由の重複を失敗件数として合算しない。null itemsと空配列を区別。
- 読取更新は表示中のみ5秒間隔。前回要求未完了なら重複取得せず、非表示/アンマウント/ID変更時の古い応答を捨てる。失敗時は最後の値と取得時刻JSTを残し、古い値とエラー/再取得を表示。取得失敗を0で埋めない。
- 配信の表示は常に「現在の全体データ」。取込選択を配信要求のquery/bodyに送らない。既存Preview/TargetList/Formの操作を共有部品化し単独配信ページにも使う。既存配信の安全装置・確認・押下中の二重操作防止を維持。POST失敗を自動再送しない。
- 配信先のlast_*は「最新保存記録」、その場のrun応答は「今回の応答」として区別。記録日時から導入前後を判定するAPIはないため、導入前と断定しない。永続した全履歴/実行IDが未提供なことを平易に説明し、架空のID・終了時刻・成功履歴を生成しない。履歴タブを空の完了済みとして偽装しない。
- 視覚は既存の業務画面部品・フォント・トークンを使用。上部に取込選択/最終取得、続いて工程の比較、明細、区切った全体配信。意味のない大型数値カードや装飾は増やさない。狭い幅で順に積み、表は既存の横スクロール方式。ja/en同一キー、共通アイコンのみ。

受入条件: (1) complete0件とlegacy_unknownを区別 (2) 抽出errorと残存結果から解析成功にしない (3) 遅い旧ID応答が新IDを上書き0 (4) 非表示中poll0、表示復帰後更新 (5) エラー時に古い値/時刻保持 (6) フィルタ/ページをサーバへ渡し25件以下 (7) URL再読込で選択復元 (8) 非管理者の新規要求0 (9) 配信要求にimport ID混入0 (10) POST自動実行/自動再送0 (11) 既存取込/保留確定/配信操作維持 (12) ja/en、明暗、狭幅で情報欠落/操作不能0。
検証: React単体試験でNULL/エラー/競合/poll/権限を制御。Playwrightで実route/既存取込/配信確認をstub APIへ接続し、送信回数/URL/画面を検査。npm build/check:all、既存unit、E2Eを実行し失敗を直す。実DBの新試験は不要（既存API不変更）、本番配信でUIテストしない。

Why: 既存GETにscope/as_of/coverageとNULL契約があり、未提供の履歴を推測せずページへ接続できる。全バックエンド改修まで画面を作らない順序から、API事実表示を先行する順序へ分ける。完成したページでも履歴未提供の制約は残る。全体の総合画面完成をこの便だけで宣言しない。維持担当はTerra実装、root差分/画面確認。外部導入事例不要、実API契約/画面試験を直接の根拠とする。
Architect自己審査APPROVEは本節の既存API接続ページだけ。実API/権限/既存部品/試験基盤を照合し、受入条件を上記12件に固定。同一AIの自己審査で独立レビューではない。親の新実行記録/切替設計REVISEを解除しない。正式カード検査後にTerraへ実装を委任する。

### ページ接続便の実装確認

実装commit ccc105ad、main4734fe7f取り込みcommit4619e7a8。rootによる最新main統合後のbuild/check:allはexit0、unitは16ファイル133件成功。既存lint警告219件/エラー0、既存bundle-size警告あり。変更TSX/CSSはcommit hookのeslint --max-warnings=0と各検査を通過。E2Eと目視の範囲はrecon末尾に記録する。
本便の差分確認APPROVE。既存GETと配信部品の接続・表示契約・旧応答無効化・POST自動再送なしの範囲に限定する。新解析実行記録/永続配信履歴/切替全体のREVISEは継続。PR #3416提出済み。CI確認を進める。POの番号付きGOは創作せず、本番反映済みとは記録しない。

ページ接続便GO: PO原文「GO #3416」を受領（受領後記録時刻2026-09-10 21:17 JST）。当該PRのマージと通常デプロイの確認を進める。新実行履歴/切替全体のREVISEを解除せず、将来の本番停止操作には流用しない。

### ページ接続便のマージ・本番反映完了（2026-09-10）

PO原文GO #3416に基づき、最終HEAD6459e7ca1a71bfead06f561826496fe6384ac8e7の37成功/8対象外skip・失敗0、CLEANと所有権を確認。2026-09-10T12:24:21Z、merge commit17ebe93f9259e5d5930cc6f7c26f90f14f433ea5でマージした。
[本番デプロイ34476536034](https://github.com/shingo-ops/salesanchor/actions/runs/34476536034)はsuccess。実配備ログのHEAD is now at17ebe93f、事前バックアップ・コンテナ更新・Finalize・Verify成功を確認。SA-19 smokeは対象外skipで、実行成功と扱わない。
公開Appのscriptはindex-CU1MBcSm.jsからindex-i0HIAxuW.jsへ更新。新JSのSHA256はadc6e6c79bf4adb70f057fce2552b2fce1a3cca9e0629616984ba50c87e46f3b、進捗表/配信範囲/取込IDのコード存在を確認。公開API healthはstatus ok、database/redis/celery connected。rootがコマンド結果を直接確認した。管理者ログイン後の実データ画面操作・実配信は行っていない。
状態: ページ接続の設計/PO承認/実装/検証/PRマージ/本番反映は完了。新しい解析実行記録・永続配信履歴・将来の本番切替は未実装、設計REVISE継続。確認方法は管理者で「取込・解析・配信」画面を再読込し取込を選択、既存記録の進捗/明細と全体配信境界を見る。
