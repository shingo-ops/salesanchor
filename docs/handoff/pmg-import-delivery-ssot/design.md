---
mode: handoff
---
# インポート・解析・配信の統合設計と第1段階

この文書は、取込から配信までを一画面で確認するための設計と、最初の実装範囲を記録する。
親: [商品マスタ](../../specs/product-master/README.md)
recon: docs/handoff/pmg-import-delivery-ssot/recon.md
対象ADR: ADR-113, ADR-154, ADR-072
日付: 2026-09-10

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
