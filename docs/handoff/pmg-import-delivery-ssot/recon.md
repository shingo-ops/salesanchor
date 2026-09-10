# インポート関連・進捗APIの実物確認

この文書は、引き継ぎ内容と今回確認したコードの事実を分けて記録する。
親: [商品マスタ](../../specs/product-master/README.md)
design: docs/handoff/pmg-import-delivery-ssot/design.md
対象ADR: ADR-113, ADR-154, ADR-072（索引を検索・本文参照）
確認日: 2026-09-10
HEAD/origin/main: 8206ba2844921c1efb3ca4fd647230e76bb0c5c6（fetch後差分0）

## 今回確認した事実

- backend/app/services/tcg_line_import_svc.py:299-302 は最新本文と先頭日時を組み合わせる。
- 同ファイル:324-429 は投稿を毎回新設し、旧投稿をsupersedeする。再利用分岐なし。
- 同ファイル:476-495 はファイルSHAの重複のみ防止する。
- backend/app/routers/tcg_line_import.py:560-644 は保留確定時の投稿作成とcommit後queue起動。
- backend/app/tcg_config.py:17-31 はTCG_SCHEMAをtenant_NNNに検証し、既定tenant_004。
- backend/app/auth/dependencies.py:453-482 は中央super-admin権限。一般テナントadminは403。
- migrations/20260831_110000_create_tcg_analysis_tables_t004.sql:223-325 は既存投稿・抽出・解析表とanalysis_results.extraction_item_idのUNIQUE。
- backend/app/services/tenant.py のTCG表名検索: 新規TCG表作成処理なし。TCG初期表は専用migrationで作成。
- 作業場所・台帳検査はexit 0。UUIDは4aa45d5a-7c65-4150-bd2e-ac0f45255edc。作業場所再作成なし。
- 競合候補の旧台帳release/tcg-import-fk-order-fixはgh pr listでPR #3296 MERGED確認。

## 引き継がれた観測（今回の本番実測ではない）

仕様v1の観測表をdesign.mdに原文保存。抽出done966/empty72/error57、商品・結果各23456、errorに結果166、NOTE_JA1234/2855を現在値や保証に読み替えない。
元報告の指定パス4本は本セッションで内容を再確認していない。生の本番データをコミットしない。
本番・Gemini・実配信は操作しない。APIコンテナ実コード・外部シート・NOTE_JA空欄原因・全件再解析済みかは未確認。


## 2026-09-10 後続便: 解析実行記録の確認

本節は、解析が終わったかを画面で正しく表示するための実物確認。
親: [商品マスタ](../../specs/product-master/README.md)。設計: [design.md](design.md)の同日後続便節。
基点: origin/main=5d26b70a186479e32e5105ac2e04b92b38eeacec。旧調査SHAからの製品コード変更はないことをgit diffで確認。PR #3386はgh pr viewでMERGED、merge=60132b058ba52f24afdb50d683a216d88f5fdd59と再確認。既存本文末尾のOPEN・マージ未実施は提出時点の記録。

### 1. 全体像

- backend/app/tasks/tcg_extraction.py:104-142 はpending取得とrunning更新を別SQLで実施。取得時の行ロックはない。
- 同ファイル:194-225 は抽出完了をcommitした後、自動解析を直接呼ぶ。解析実行履歴のINSERTはない。
- backend/app/services/tcg_product_master_svc.py:536-550 は手動再解析のrunをINSERTしてcommit。:552-598 は再解析前snapshotを保存、:639 は共通解析、:657-686 は完了記録。
- backend/app/routers/tcg_product_master.py:280-282 のレスポンスモデルはbefore/afterのみ。サービスが返すrun_idはHTTPレスポンスに載らない。

### 2. 共用部品

本節の部品は解析関数・実行管理・集計・配信判定を指す。
- backend/app/services/tcg_analyzer_svc.py:908 の共通関数を、通常アプリでは上記の自動・手動2経路が呼ぶ。backend/scriptsのPython呼出しを検索した範囲で別の直接呼出しはない。
- 同ファイル:1128,1143,1154 の3か所にcommit。後処理の順序はE3a/E5→E3b→E4。
- 同ファイル:682,744,845 の3か所で任意マスタの照会例外時にsession全体をrollbackしている。

### 3. 非共用部品

- backend/app/tasks/tcg_extraction.py:78-95 は内部例外を戻り値status=errorへ変換。:261-267 のCelery retryへ必ず例外が届く構造ではない。
- backend/app/services/tcg_product_master_svc.py:520-686 は手動だけの履歴処理。例外時のrun終端処理はない。
- backend/app/services/tcg_import_progress.py:84-96 は商品数・結果数と、未記録の実行状態を区別。:118 の明細実行状態もunrecorded固定。
- backend/app/services/tcg_distribution_svc.py:646-699 はcompleted_at NULLのrunと未完了抽出ジョブで全体配信を止める。:602-620 は配信先ごとに最新結果を更新・commitする。

### 4. ルールの所在

- ADR-113: 設計持ち込みと実物整合確認。ADR-154: 解析順序と任意マスタ欠落時の互換。最新mainのv3作品照合案は別テーマのため混載しない。
- backend/AGENTS.md: additive-only、既存・後発TCG schemaへの適用確認。
- migrations/20260903_220000_create_tcg_analysis_history_t004.sql:27-42 は既存analysis_runs。状態・request key・worker所有情報はない。tenant_001側にも既存履歴DDLがある。
- docs/handoff/pmg-import-delivery-ssot/design.md:159-165 は結果の存在から実行成功を推定しない契約。

### 5. 維持の仕組み

- backend/tests/test_tcg_gemini_extraction.py:239,280 はauto analyzeのOFF/ONをモックで検証。実行記録の再配達・worker消失を検証する試験ではない。
- backend/tests/test_tcg_distribution.py:193 は未完了runによる停止を検証。
- backend/tests/test_tcg_import_progress_pg.py:200 はエラーと残存結果・明細を実DBで検証する基盤。
- .github/workflows/test.yml:206-241 にPostgreSQL付き試験経路。新規の実行記録試験は未実装。

### 6. 既存設計との差分

| あるべき姿 | 実物 | 判定 |
|---|---|---|
| 自動・手動を同じ実行履歴へ | 手動だけrun保存 | 不足 |
| 成功と結果の存在を分離 | 進捗APIは既にunrecorded/nullを返す | 一致・維持 |
| 成功記録と全解析結果が一致 | 最大3回の途中commitと別の完了commit | 不足 |
| 再配達は同一attempt、明示再試行は新attempt | request key・attempt所有情報なし | 不足 |
| 停止workerをunknown表示 | 履歴の状態列なし | 不足 |
| 取込選択は進捗だけ | 進捗APIはimport関連経由、配信は全体 | 一致・維持 |
| 旧データの実行成功を作らない | 未記録表示あり | 一致・維持 |

### 7. 境界と未確認

本番データ、稼働コンテナの環境値・worker実体は今回未確認。過去の57/166等を現在件数として使わない。テストは本ターンでは実行せず、既存定義を読んだ。
backend/app/tasks/tcg_extraction.py:42 はTCG_DB_URLをDATABASE_URLより優先。backend/app/services/tcg_product_master_svc.py:515 とbackend/app/database.py:8 はDATABASE_URLを使用。compose設定キーの確認だけでは稼働環境の接続先一致は証明できない。認証情報を表示せずに確認する必要がある。
Context7は利用可能ツールの名前・説明を検索したが0件。起動指示の代替許可に基づきPostgreSQL16、SQLAlchemy2.0、Celeryの公式資料を確認。Celery依存は>=5.4.0であり、稼働版は未確認。

### 作業場所と承認の範囲

今回の文書保存にも削除なし直接作成・担当登録・安全チェックを適用してよいかを尋ね、PO原文「合意」を受領。対象はこの設計保存の作業場所。製品実装・マージ承認には流用しない。
専用branch=release/pmg-analysis-run-design、UUID=5a84cc02-0d8a-4121-8dfc-4b444b26a0e7。preflight、validate-worktree-start、validate-pr-ownershipは各exit0。旧worktree・本店AGENTS.mdを編集せず、回収処理・新AIセッションを起動していない。


### 2026-09-10 稼働環境の読取試行

- 制限付き鍵salesanchor-claude、IdentitiesOnly/BatchMode/ConnectTimeout=10を指定し、claude-monitor@49.212.137.46へdocker psの名前一覧を要求した。
- exit0だが、返ったのはdocker stats / free / df / uptimeの監視出力。要求コマンドの成功と扱わない。ForceCommandによる置換は既存docs/handoff/rehearsal-env/design-b-ssh-isolation.md:58の記載と一致。
- 監視出力にはastro-webapp-backend-1 / astro-webapp-celery-worker-1 / astro-webapp-celery-beat-1が存在した。DB接続先・稼働ライブラリ版はこの出力では確認できない。
- 人間用鍵への切替、制限の変更、DB更新・サービス再起動はしていない。
- ローカルに読み取り診断案 /tmp/pmg-runtime-db-identity-readonly.py を準備。API/worker/beatの接続からtransaction_read_only=onを確認し、DB名・サーバーアドレス/ポート/起動時刻をまとめたSHA256とTCG_SCHEMA・対象4表の存在だけを返す。認証情報・例外本文は返さない。SQLはSHOW/SELECTのみ、接続5秒・SQL5秒、各コンテナ25秒で打切り。
- 診断案はAST構文確認のみ実施。本番では未実行。人間用鍵はタスク単位の明示許可が必要（CLAUDE.md「VPS直作業禁止」）。
- 配布順序を .github/workflows/deploy.yml:149-158,319-335 と scripts/blue-green-cutover.sh:147-150 で確認。コードがmigrationより先、新APIがworker/beatより先に切り替わる。実行中排出の保証を推測しない。


### 2026-09-10 DB接続先の読取診断結果（前節の未実行状態を更新）

- 許可対象: 今回のDB接続先確認に限る人間用SSH鍵の使用。更新・再起動・配信なしと説明した確認へのPO原文は「進める」。この診断以外への鍵利用を許可済みと扱わない。
- 実行: `ssh -i /Users/tanizawashingo/.ssh/manual-only/id_ed25519 -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=10 ubuntu@49.212.137.46 'python3 -' < /tmp/pmg-runtime-db-identity-readonly.py` → exit0。
- 診断内容: 3コンテナにdocker execで一時Pythonを実行。API/beatはDATABASE_URL、workerはTCG_DB_URL優先・なければDATABASE_URLを使用し、新しい読取専用接続でSHOW/SELECTのみ実行。TCG_SCHEMA未設定時の既定値はtenant_004。アプリの設定やDBデータは変更しない。
- DB識別値はcurrent_database / inet_server_addr / inet_server_port / pg_postmaster_start_timeの組をJSON化したSHA256。3出力とも `ad5f1cdff1217be570b63fd6a0e89ed21cbbddced29c522e7ce5ed523afad7d3`。

| role / container | transaction_read_only | schema | 対象表 |
|---|---|---|---|
| api / astro-webapp-backend-1 | on | tenant_004 | analysis_results, analysis_runs, extraction_jobs, source_messages（4/4） |
| worker / astro-webapp-celery-worker-1 | on | tenant_004 | 同4表（4/4） |
| beat / astro-webapp-celery-beat-1 | on | tenant_004 | 同4表（4/4） |

判定: 診断時点の3コンテナの接続設定から、同じDB・schemaへの接続に成功した。既存アプリ接続、全worker個体、稼働コード版、処理中件数、列やmigrationの適用は調べていない。4表の存在だけからPR #3386本番反映済みとは断定しない。旧実行の排出と切替手順の確認は残る。製品試験は未実行。


### 切替の追加読取（2026-09-10）

- .github/workflows/deploy.yml:331-335: API切替後にfrontend/celery-worker/celery-beat/discord-gatewayをdocker rm -fで削除して再作成。処理完了待ちの検査はこの箇所にない。
- docker-compose.yml:190-192: workerは1サービス定義、concurrency=2。これは構成定義であり実機の全worker数ではない。
- backend/app/celery_app.py:20-36: TCGと翻訳・メール・保守等を同じCeleryアプリに登録。停止影響をTCGだけに限定する根拠はない。
- scripts/blue-green-cutover.sh:147-150: 旧APIの停止は40秒指定。その時間内に全手動解析・外部配信が必ず完了する実測はない。
- backend/app/tasks/tcg_import_discard.py:57は保留ジョブの更新commit。tcg_mirror.pyはミラーシートへ書く別タスク。解析2入口だけの確認では全ての関連書込・外部送信を網羅しない。
- docs/runbooks配下をtcg/drain/停止/メンテナンス/Celery/revokeで検索した範囲では本件の排出手順を確認できなかった。検索範囲外にも存在しないとは断定しない。
- 本番追加接続はしていない。前回の人間用鍵の許可はDB接続先診断だけとして維持する。
- PR #3396 HEAD e7da4a85947dc9b6f05e23ff4c93382fee640ee9のGitHubチェック: pass31、skipping9、失敗/待機0。文書PRの検査であり解析実行管理の製品試験完了ではない。

### 初回停止の追加根拠（2026-09-10）

- main.py:456,569-604とTCG各routerを照合し、商品変更・分類変更・抽出retryも停止候補に追加。詳細のfile:lineはdesign.mdの入口表。
- nginx/nginx.conf:71,259の2公開ホストと:44のlegacy転送、docker-compose.yml:11の単体bind mountを確認。ADR-130/137を読み、reloadだけで設定反映したと断定できない制約を確認。
- backend/Dockerfile末尾はuvicorn workers=2。稼働プロセス数・既存要求完了は未確認。backend/app内のmaintenance/READ_ONLY等の検索では本件の初回停止機構を確認できず、保守タスク等が該当した。不存在の証明とはしない。
- Context7ツール検索0件。Celery Workers Guide、Docker stop、nginx returnの公式資料を確認。停止仕様とバージョン依存をdesignへ記録。ライブラリの本番版を照会したとは扱わない。
- 一時停止方針へのPO原文「GO」を受領。説明した一時停止/共有業務待機の許容だけであり、本番操作・追加SSH利用はしていない。

### 配布中の遮断維持の照合（2026-09-10）

- deploy.yml:182-184,360-374のreset/設定再作成を照合。一時的に追跡ファイルを書換える案は配布で失われ得るため不採択。
- APIの同期解析・外部配信は別スレッドを使用する実装。HTTP応答だけでその終了を判定しない（design.md同日節）。
- ローカルdocker versionはcommand not found、exit127。Docker試験を行ったとは報告しない。
- 稼働版/構成の読取診断を/tmp/pmg-cutover-runtime-readonly.pyに準備、AST確認のみ成功。本番未実行。許可範囲を広げて人間用鍵を再使用していない。
- PR #3396 HEAD 6ba0ebf8のGitHubチェックはpass31/skipping9。新たな実装試験の成功ではない。


### 稼働版・構成の読取結果（2026-09-10）

承認: 「本番の稼働版・コンテナ一覧・設定とコードの一致確認。この読み取り確認に限り、人間用SSH鍵を使用してよいですか。更新・停止・再起動・配信は行わない」と説明した質問に、PO原文「許可」。診断対象以外への許可として扱わない。
実行コマンド: `ssh -i /Users/tanizawashingo/.ssh/manual-only/id_ed25519 -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=10 ubuntu@49.212.137.46 'python3 -' < /tmp/pmg-cutover-runtime-readonly.py` → exit0。実行直前に診断ファイルのSHA256が準備時の8e355d21acc44058e43febf28532d64ddfbd9d7935c670857c939d904ac8e3faと一致した。

| 対象 | 実測 |
|---|---|
| Docker client/server | 両方29.4.0 |
| API（7b6a0d641833） | running、起動2026-09-10T01:51:34.091810063Z、PID1実行名uvicorn |
| worker（d69fa4e27f98） | running、起動2026-09-10T01:52:09.466315736Z、PID1実行名celery |
| beat（56a615bcadbb） | running、起動2026-09-10T01:52:09.462362811Z、PID1実行名celery |
| 3コンテナ内のインストール済み版 | Celery5.6.3 / Uvicorn0.34.0 / SQLAlchemy2.0.38が3/3一致 |
| TERM置換の環境設定 | 診断プロセスから見たREMAP_SIGTERMは3/3未設定 |
| nginx（39782f43a552） | running、設定ファイルのSHA256が手元と一致 |
| 稼働名一覧 | 当該Docker daemonで13件、うちastro-webappラベル対象12件、残りpushgateway。別名worker/旧greenという名前は一覧にない |

API/worker/beatのイメージIDはそれぞれ異なる。イメージ全体の同一性を主張せず、コンテナ内7ファイルのSHA256をローカルbranch HEAD 0b218a94の同ファイルと比較して21/21一致を確認。

| backend/からの相対パス | SHA256（3コンテナと手元が一致） |
|---|---|
| app/main.py | c2f7ff4ff0e9b81b7a9a2bbd2707f3bd4e6812cc4b2048cbe605ae5ba96703c8 |
| app/celery_app.py | 759ab157063c6ebda436f85f504f7e95d65463bb83ac9eeaeebefdd08e619e4a |
| app/tasks/tcg_extraction.py | 85d435184dbb8594a23df2a617f01c9ce1857f27c288f69ff3fc3601ab966330 |
| app/tasks/tcg_import_discard.py | b4c5f66bfff9a101139fe12c1ce0704de5ecc7b185e77269d4235d77db762c15 |
| app/services/tcg_product_master_svc.py | ec12593ef7d6ea90920a32518450b97ecd74821d415dcb5acdfcef5aac02af53 |
| app/services/tcg_distribution_svc.py | 6a63cf5245113bb7ac678a5c993c00098c9bd1f71d7a09fc8eadee4aa289166c |
| app/services/tcg_analyzer_svc.py | 292f355e9ed04d5feb1f30064a27733b49df934d189f3e5ab69a614591eedc08 |

nginx /etc/nginx/conf.d/default.confと手元nginx/nginx.confはSHA256=97972f76aabaa29b88cc16a0e99db2df31b731abbfe1fcb3f6cedaa8557938a9で一致。
限界: ディスク上のファイル・インストール済みパッケージ・診断プロセスの環境を確認した。既存プロセスが読み込んだ全module/設定、全イメージ内容、他ホストやコンテナ外のwriter、処理中/予約件数、DBの列やmigration、配信の完了は未確認。nginx設定ファイル一致は、稼働masterが既にその版を読み込んでいる証明ではない。PR #3386の全本番反映を断定しない。診断による停止・更新・配信なし。

### 入口一覧と復旧経路の追加照合（2026-09-10）

- Python ASTでtcg_*.pyとsuper_admin_tcg.pyのrouter decoratorsを抽出: 定義43件、GET21/非GET22。結果は/tmp/pmg-tcg-routes-readonly.json。サービス副作用や本番ルート網羅の検証結果ではない。main.pyの/api/v1登録と合わせ、公開2ホスト×非GET22の44組を試験対象にした。
- backend/app/middleware/audit.py:106以降はcall_next後の記録。完了待ち専用の実行管理ではない。Uvicorn0.34.0公式server.pyのrun/shutdownも確認し、timeout時のcancelを成功扱いしない条件を追加。公式_compat.pyの同tag取得は404で、根拠には使わない。
- ADR-115は自動rollbackと本番相当Docker試験を規定する。受付停止の状態だけが残っても、旧設定が参照しなければ遮断を維持できないため、制御を含む戻し先の確保を設計条件に追加。
- docker/nginx/podmanを本ローカル環境で確認できず、Pythonは3.14.3。Dockerfileの3.12と相違するため、本番相当の停止試験は未実施。
