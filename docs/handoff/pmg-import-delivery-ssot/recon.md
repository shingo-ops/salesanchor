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

### 初回専用経路と試験基盤の照合（2026-09-10）

- deploy.yml:3-16のmain push/排他、:331-335のworker再作成、:360-374のnginx再作成、:531以降のFinalize/rollbackを読取。nginxのみ更新してAPI/workerを維持する経路は確認できなかった。専用経路では全体rollback/failure cleanupも切り分ける必要がある。
- test-rollback.ymlはubuntu-latestでDockerを確認しscripts/test_rollback_simulation.shを実行。test-phase2-rehearsal.ymlは本番secretを注入しscripts/rehearsal_phase2.shを呼ぶ別の経路。どちらも本件の停止機構試験ではなく、このセッションでは実行していない。
- 最新origin/main=760532a9。PR #3398はmigration2件/登録のみで、deploy.ymlと対象解析コードの差分0。既存の配布/解析調査の根拠を変更する差分ではない。
- PR #3396 HEAD642da564のGitHubチェックはpass32/skipping8。本件新機能の試験成功とは扱わない。

### nginx受付判定のローカル実測（2026-09-10）

公式nginx1.31.1とPCRE2-10.46を/tmpに取得し、Apple clang15.0.0でビルド。Python3.14.3の架空HTTP処理先と127.0.0.1で試験。最終151/151 assertion成功・exit0。対象44組の許可なし/あり/取消後、状態directory探索不能、URI正規化、reloadの新worker出現、旧要求完了、再起動後の拒否維持を確認。
試験の全結果/実際の設定/ハーネス/ログは/tmp/reports/pmg-nginx-admission-probe-3396/、永続する要約とhashはdesign.md同日節。これはmacOS上の受付判定試験でありDocker/TLS/本番handlerの試験ではない。製品コード・CI・nginx設定・本番の変更なし。

### 復旧160件と既存mount候補の照合（2026-09-10）

/tmp/pmg-nginx-recovery-y5544801/probe.pyはexit0、160/160。不正設定reload失敗後の旧worker存続/拒否維持と復旧、QUIT中の新規接続停止/受付済み要求完了/正常終了等を追加確認した。成果物hashはdesign.md同日節。
停止状態の別候補をcompose.yml:18、.gitignore:119、deploy.yml:104,914と照合。git check-ignore -v nginx/htpasswd.d/pmg-cutover/allow-writesは.gitignore:119に一致。deploy/scripts内のhtpasswd.d参照を検索した範囲で生成/削除対象はdesign-siteであり、専用サブdirectoryはまだ存在すると確認したものではない。前回本番診断はmountやowner/modeを取得していない。追加SSH接続なし。
既存Dockerの一般的な6パスを確認したが存在せず、ローカルDocker試験未実施。PR #3396 HEADddcf962bのチェックはpass33/skipping8。

### 離席中の残件読取と最新main照合（2026-09-10）

PO原文「離席するので最後まで進めてくれ、事前にPRマージも承認する」を受領。直前に提示した保存領域/権限の読取と文書PR3396の保存/マージに適用。/tmp/pmg-cutover-mount-readonly.pyでnginxの対象bind2件とstatを取得。最後のps照会のみ失敗し全体exit1。取得できたmount/statと失敗を分離した。/tmp/pmg-nginx-process-readonly.pyの/proc Name/Uid/Gid限定読取はexit0。本文・認証ファイル・DBデータ・設定変更なし。詳細数値はdesignの最終確認節。
最新main a0c0eb7fを取り込み。PR3393のv3作品根拠/訂正保持を読み、3commit/3rollbackが残ることを再確認。PR3399など他PRの台帳更新を保持して文書競合を解消。以前のコードhash診断を最新版の一致証拠とは扱わない。


## 2026-09-10: Terraによる旧処理取消の隔離実測と次便準備

origin/main 89ad29aeで新規作業場所を作成。先のd21599c7以降はinventory系テスト/文書だけの変更で、対象の解析/配信2サービスのSHA256一致を確認した。
Codex TerraはPython3.12で実物のrun_distribution/reanalyze_extraction_jobをAST抽出し、そのままコンパイル。DB/資格/外部送信境界だけを架空実装へ置き換えて4シナリオを実行した。
初版は12assertion。設計担当は開始Eventの待機結果が未検査と指摘し、開始済みを検査する2件を追加。最終14/14成功、設計担当も同じハーネスを再実行しPASS assertions=14を確認した。
通常配信は成功記録、戻り値の送信エラーはエラー記録/通知。取消ケースでは開始確認後に待機taskをcancelし、その後に同期処理を解放。架空送信/解析は終了し、配信結果のDB記録は0件だった。
これは呼出し側の取消と同期処理の完了が異なることの証拠。実Sheetsへの送信完了、本番DBの状態、Uvicorn停止時の実態を証明しない。HTTP終了だけから旧配信の完了を推定しない契約を維持する。
根拠: /tmp/reports/pmg-legacy-completion-probe/RESULTS.md、probe_legacy_completion.py、run.log。run.log SHA256=e1c292a152364da624044a5bd9ae544f76c41ff85b6316b44c40c20094d6cfd5。
配信ソースSHA256=6a63cf5245113bb7ac678a5c993c00098c9bd1f71d7a09fc8eadee4aa289166c、再解析ソースSHA256=ec12593ef7d6ea90920a32518450b97ecd74821d415dcb5acdfcef5aac02af53。

現行new-worktree.sh:65-67は回収を実行するまま。既存保持オプションは文書PR3390だけで未実装。POに今回の作成例外を確認し「許可する進める」を受領した。
新規release/pmg-cutover-rehearsal、UUID c4aca19e-0e68-4a1c-acd7-f37c63d92ff9。担当台帳登録・フック設定、validate-worktree-start/validate-pr-ownership通過。既存worktreeの削除0件。本店AGENTS.mdの他者変更は保持した。
Docker実行環境はローカルに見つからず、既存test-rollback.ymlのubuntu-latest/Docker経路を参照した。製品/既存配布処理を変更せず、新規隔離CIで検証する設計を作成。正式card-lint exit0を確認してTerraへ試験2ファイルだけを委任した。
製品設計の自己審査REVISEは維持。隔離試験を実装する設計だけAPPROVE。新規試験CIはまだ実行しておらず、Docker成功とは扱わない。


### 配信安全装置8bの問い合わせ・本番読取（2026-09-10 17:41 JST）

POから「running2件で配信不可、今回の影響か」の問い合わせを受領。本便のgit差分は未コミット、当該headのPR一覧は空。製品変更/マージ/デプロイ未実施であり、本便の未公開試験は原因ではない。過去の他PRや停止そのものの原因を否定した証拠ではない。
本番API経由の接続設定でdefault_transaction_read_only=on、SHOW transaction_read_only=on、statement_timeout=5000を確認してSELECTのみ実施。DB時刻2026-09-10 08:41:47.993282+00、pending/extracted0、running2。
- 6da3ca68-651e-4ff6-8316-1c9135508ad2: source b1b58ee9-0d6a-4ed1-8034-f1d62a72b4b2、元データ無効、items0。
- bfa07018-9b34-42b6-990a-017e3c1cf140: source afbc08d1-cf3b-43be-87e5-4b7200144b6c、元データ有効、items0。
両方created_at=2026-09-10 02:49:21.105805+00、extracted_at/prompt_version NULL。docs/handoff/tcg-product-master-growth/recon.md:682の既往2IDと一致。本文や資格情報は取得/記録しない。
Celeryの読取inspectはcelery@19d5a281d647の1台から応答、active/reserved/scheduledは各0件。未確認の別worker/同期処理が存在しない証拠へ広げない。
現行tcg_distribution_svc.py:674-700は未完了jobがあれば配信前に中断する。tcg_diagnostics_svc.py:138,186の再試行対象はpending/errorだけで、running2件は対象外。安全装置を無効化せず、元データの有効/無効を分けた復旧設計が必要。DB状態変更・再実行・外部配信は未実施。停止原因は未確認。
診断実体: /tmp/pmg-running-two-readonly.py、/tmp/pmg-worker-presence-readonly.py。どちらもexit0、資格情報本文の出力なし。

### 実装担当停止

Terraの初回混雑は再試行で解消し、取消試験14件まで実施。その後Docker試験のコードレビューを差し戻し、修正継続を依頼したが、モデル利用上限エラーで停止。新規2ファイルは実装途中、Docker試験未実施、コードレビュー未合格。指定外モデルへの切替はしていない。再開時はカード契約との照合から続け、未完成差分をPR/マージしない。


### 実装再開・他セッションとの境界

PO原文「復旧は別セッションが対応しているので再開してくれ上限は解消した」を受領。running2件の復旧は本便から除外し、DB状態変更・再実行・配信を行わない。
Terraの編集に対し自動承認レビューが利用上限エラーで拒否。拒否をPOへ説明して、同じ隔離試験ファイルの編集再試行について返答「許可する」を受領した後、同じTerraで編集を再開した。自動審査/安全フックの無効化なし。
追加のPO原文「離席するので最後まで進めてくれ、事前にPRマージも承認する」を受領。既承認のマージ/デプロイ範囲で、試験実装・差分レビュー・CIへ進む。未完成コードや未検証の製品設計はマージしない。

### Docker初回CIの失敗と試験ネットワーク修正（2026-09-10）

PR #3408 HEAD098dd48aのpush/PR両試験は接続口取得でKeyError 443/tcp、assertion実行前に停止。PR run34459276866/job102812962329、Docker28.0.4、nginx digest sha256:608a100c71651bf5b773c89083b4a1ad7ef4b2bd05d7a7e552271e03123692ad。成功扱いしない。
同版の公式実装 https://github.com/moby/moby/blob/v28.0.4/libnetwork/endpoint.go#L698-L706 はinternal networkでProgramExternalConnectivityを実行しない。試験が指定した--internalとホスト公開ポート取得は整合していなかった。独立した通常bridgeへ修正し、公開先127.0.0.1とランダムポートの検査を維持する。外部通信を遮断するネットワークとは称さない。試験要求先はlocalhost/同networkの架空処理先のみで、資格情報を渡さない。修正後の実動確認はCIで行う。
Context7は利用可能ツールに存在せず、PO許可済みの公式資料直接確認を使用。PR本文の削除行申告もdesign.mdを列挙して修正した。

修正後HEADd6da86d3のrun34459910899/job102815014890は、nginxに同一443ポート公開を2回指定した箇所でaddress already in use。ネットワーク設定処理まで進んだがassertion0件。TLSの2serverを内部443/444に分けて公開するfixtureへ修正する。createでID取得後にstartする手順に分け、起動失敗時にも自作containerのIDを保持して後始末する。製品構成の変更ではない。

HEAD6b38e094のPR試験run34460163845/job102815839208（GitHub試験merge SHA24ad0ec6）は、受付拒否・更新・不正reload・起動失敗検出まで進み、復元後restart TLSでConnectionRefused/timeout。起動前に記憶したランダム公開ポートを再利用していた。再起動後のinspectを再取得・同じ公開範囲検査を実施し、前後の値を結果へ残して原因を照合する。失敗時点のログだけで再起動後のポート値は確認できておらず、タイムアウト延長で代用しない。

### Linux/Docker実測結果と差分審査（2026-09-10）

HEAD879aa1f423f00ed15b9af1714f91070d813ac8f6のpush試験run34460419959/job102816671239は99/99 assertion成功、errors0、exit0。設計担当がActionsログの結果JSONを直接取得して確認した（他者の報告だけではない）。Docker28.0.4、Python3.12.14、nginx1.31.1 digest sha256:608a100c71651bf5b773c89083b4a1ad7ef4b2bd05d7a7e552271e03123692ad。
再起動前app/api公開ポート32769/32770、再起動後32773/32774を実測。前回の古い接続口再使用が整合しないことを確認し、再取得で復元後TLSと拒否維持が成功した。
同一inode・host/container digest、両TLS入口の許可なし/許可/取消、拒否時転送0、不正reload時の旧worker保持、途中設定の起動失敗、復元後の再起動、受付済み長時間要求の200完了を確認。自作資源の後始末エラー0。
根拠: https://github.com/shingo-ops/salesanchor/actions/runs/34460419959/job/102816671239 。artifact10145284758、zip SHA256=7d6385d6df251f98b73fb281a219409a9c7c5ce196255225ffd9ab0b777bc889（CI保持7日）。取得結果は/tmp/reports/pmg-cutover-3408/push-results-879aa1f4.json。
試験コードはPO指定Terra、設計/コード差分審査はroot。差分審査APPROVEは試験2ファイルのみ。独立した設計第二者レビューとは称さない。製品の初回配布手順・旧版の実送信完了照合は未実装/未確認で、親の製品設計REVISEを維持する。画面は未完成。

## 入口配布・旧処理照合の再調査（2026-09-10、base b36041ed）

PO原文「次を進めるPRマージまで」。直前に提示した既存保持の作業場所例外と次の設計文書PRに適用。製品実装や個別の本番停止を実行した記録ではない。preflight・開始/所有検査exit0。release/pmg-cutover-integration-designをorigin/mainから作成、回収処理実行0。元作業場所の.worktree-idは読取時に存在しなかった。削除原因は未調査で断定しない。本店AGENTS.mdの他者変更を保持。

PR #3408はGitHubでMERGEDを再確認。merge0be59e5290cab4149aa5451920317f8fa7f7564c、2026-09-10T09:27:18Z。deploy34460726589は同SHAでsuccess。今回ローカルでDocker試験を再実行したものではない。既存CI99項目の結果は先行節の根拠を利用する。

| 観測事実 | 実物の根拠 | 設計への制約 |
|---|---|---|
| 試験は独自生成の2TLS serverを443/444に配置する | tests/pmg_cutover_probe.py:100 | 本番nginx全設定を読んだ統合試験ではない |
| 本番app/apiそれぞれに認証・stream・一般APIのlocationがある | nginx/nginx.conf:71,96,112,132,151,259,282,298,318,337 | fixtureで参照GET200でも実認証入口の挙動保証にならない |
| 旧配信の外部変更はclearとappendの2呼出し | backend/app/services/tcg_distribution_svc.py:463,465 | 間の失敗は外部変更なしと断定できない |
| 外部処理終了後にDB結果を保存する | backend/app/services/tcg_distribution_svc.py:762,773 | 外部成功/DB未記録の窓があり、last_resultだけで未実行とも成功とも推定しない |
| API切替はnginx reload後に旧backendを40秒でstopする | scripts/blue-green-cutover.sh:144,149 | 旧実行の排出を証明する専用手順にはそのまま使えない |
| 通常配布は同時実行groupを持つがhost側のPMG保留を参照しない | .github/workflows/deploy.yml:15,184,371,572 | 専用jobが失敗終了した後、後続の通常配布が停止状態を消さない仕組みが別途必要 |

Context7の利用可能ツール0件。許可済み代替により2026-09-10に公式資料を直接確認した。Docker stopは猶予後SIGKILL、nginx reload後の旧workerは既存clientを処理、Pythonの実行中Futureはcancelで止められない。これは仕様と既存取消14件の整合根拠であり、本番旧実行が存在しないという証明ではない。
- https://docs.docker.com/reference/cli/docker/container/stop/
- https://nginx.org/en/docs/control.html
- https://docs.python.org/3.12/library/concurrent.futures.html

索引からADR-113、ADR-115、ADR-137-nginx-config-deploy-reliabilityを照合。ADR-137の同番号別文書へ誤参照しない。ADR-115の旧版復帰が新しい拒否制御を消す場合には従来の自動復旧を成功と判定できないため、設計の不変条件へ明記した。本番読取/変更、旧2件復旧、外部API送信を本便では行っていない。

## 配布保留契約と観測範囲の確定調査（2026-09-10、base 411df652）

PO「次を進める」を受領。既存保持の作成手順を継続し、release/pmg-cutover-barrier-contractのUUID/台帳を登録、preflight/開始/所有検査exit0。mainの他者AGENTS.md変更を保持。PR3410のdeploy34468628611はmerge411df652と一致しsuccessを再確認。
設計担当rootが配布経路を読み、PO指定Terraには旧処理観測の読取だけを委任した。Terraは既存配信のclear/appendとlast_*上書き、実行中thread台帳の不存在を報告。rootは別途audit/ログ収集設定と既存の移行契約を照合した。製品コード・本番変更0。
検索文字列に含まれた破壊操作名にPreToolUseが反応し検索を拒否。操作の許可券発行やフック無効化をせず、対象ファイルをsedで読み取った。破壊操作未実行。

| 観測 | 根拠 | 限界/結論 |
|---|---|---|
| 旧配信はtarget単位のlast_*を上書き、thread台帳なし | backend/app/services/tcg_distribution_svc.py:602,762 | 全過去実行や同期処理中一覧はここから復元できない（Terra読取） |
| HTTP監査はcall_next後、書込かつstatus<500が記録条件 | backend/app/middleware/audit.py:106,130 | 応答記録は実行中threadの一覧や外部成功証明にならない |
| APIのコンテナログは20m×5、Loki設定retention30d | docker-compose.yml:140、monitoring/loki/loki-config.yaml:29 | ファイル上の設定値。稼働反映/欠落なしは未確認、過去全件保証ではない |
| 既存移行契約はlast_*を導入前の最新記録として表示 | docs/handoff/pmg-import-delivery-ssot/design.md:178 | 過去run復元は既に対象外。過去全件復元を切替前提に加えない |
| 通常配布にはLP同期、認証ファイル更新、コード/環境変更が分かれて存在 | .github/workflows/deploy.yml:76,92,161 | API切替直前だけの検問では通常配布全体を止めたことにならない |
| API切替と非API再作成、復旧は別箇所 | .github/workflows/deploy.yml:324,331,572、scripts/blue-green-cutover.sh:59,149 | 共通検問が必要な実接触点を特定。既存手動入口の全稼働調査は未完 |
| SA-18リハーサルはdeploy本文を抽出して実行する別経路 | .github/workflows/test-phase2-rehearsal.yml:36、scripts/rehearsal_phase2.sh | 名前がtestでも本件の無資格fixtureと同一視しない |

Context7利用不可。2026-09-10にGitHub公式concurrency資料を直接確認: https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency 。同groupの実行中排他はjob終了後のホスト保留を維持しない。既定ではpendingの置換があり、全PRが順番に必ず配布される保証とも異なる。本便ではconcurrency設定を変えない。

## ページ接続の再照合と承認（2026-09-10、4f1c2b81）

PR3413/deploy34470161574はsuccess。POの方針採用・根拠確立後のページ作成承認をdesign最終節に原文保存。本番停止承認ではない。新worktreeでpreflight/開始/所有検査exit0、本店の他者AGENTS.md変更保持。
backend/app/services/tcg_import_progress.py:36,49,129、routers/tcg_line_import.py:653-666、tests/test_tcg_import_progress_pg.py:149-235を照合。GETは実在し、NULL/coverage/ページングを既に提供。Terraの検索漏れによる不存在報告をrootが実ファイルで訂正させた。
frontend/src/pages/super-admin/TcgLineImportPage.tsxの履歴/入力/ReviewSection、TcgDistributionPage.tsxのPageLayoutとPreview/TargetList/Form、features/tcg-distribution/distributionApi.ts:95-124、lib/api.tsのGET限定retryを照合。配信runの永続履歴は未提供。既存GET/操作に限定した画面接続を独立設計として自己審査APPROVE。親設計の切替/実行履歴はREVISE。
frontend-designスキルを適用し既存の業務部品/色/フォントを優先。新しい外部ライブラリ/API仕様は導入しない。実装は指定Codex Terra。製品編集はカード検査後。

### ページ接続検証中の訂正（2026-09-10）

- 正式画面URLは `frontend/src/App.tsx:294` と `frontend/src/components/DesktopShell.tsx:191` の `/super-admin/tcg-line-import`。ページ先頭コメントの `/super-admin/tcg-import` は古く、初回E2Eで3件が経路不一致となった。routingを変更せずコメントとE2Eを修正し、再実行でURL復元/ページング・非管理者要求0の2件が成功。配信試験はaria-label不一致を検出し修正中。
- `migrations/20260906_120000_create_tcg_tables_t001.sql:426-427` の正規化数量/価格はNUMERIC。itemsのJSON数値として型を照合する。
- 検証中に取込切替の旧値表示、未翻訳キー、配信部品未接続を発見しTerraへ修正を委任。buildだけを完成根拠にせず、競合・空/未記録・配信確認の試験と視覚検証を実施する。

### ページ接続の差分レビュー（2026-09-10）

rootはPlanner/Architectを同一AIとして担当し、製品編集はPO指定Codex Terraへ委任した。以下はページ接続便の検証範囲。親の解析実行履歴・永続配信履歴・本番切替は含めない。

| 受入 | 確認する根拠 | 現段階 |
|---|---|---|
| 1/2 未記録と0、抽出失敗と残存結果 | ImportWorkflowPanel.test.tsx / 実APIのcoverage/null契約 | 対象unit成功。root全体unit133件成功も確認 |
| 3/4/5 旧応答・非表示・更新失敗 | useImportWorkflow.test.tsx / key・世代・allSettled | 遅延ID/inflight抑止/世代破棄8件成功のTerra報告、root全体unit133件成功 |
| 6/7 ページング・URL選択 | tcg-import-workflow.spec.ts | root E2Eで成功。25行・offset25・最終next無効を確認 |
| 8/9/10 権限・配信範囲・確認前送信0 | 同E2E / lib/api.tsのGETのみ再試行 | root E2Eで成功。503後5秒経過してもPOST1回だけを確認 |
| 11 既存操作維持 | TcgLineImportPage/TcgDistributionPageの差分、共有Workspace | 元の取込・保留確定処理と配信API・確認ダイアログは維持。日時/見出しのみ表示調整 |
| 12 ja/en・明暗・狭幅 | locale同一キー、check:all、PC/390px画像 | 静的検査成功報告。root E2Eで390px暗色英語/PC日本語を確認、一覧表画像を目視確認 |

既存配信機能のread-only移設を超える再試行・自動送信・バックエンド/DB変更はない。共有Workspaceは権限判定後だけマウントし、選択import IDをpropsにもAPIにも渡さない。実行ID/履歴がないというレビュー指摘は親設計の未完了事実として維持し、本便のページに架空データを加えない。

### ページ接続のローカル検証結果（2026-09-10）

- root実行: `npm run test:unit` 16ファイル/133件成功。`PORT=5193 npx playwright test tests-e2e/tcg-import-workflow.spec.ts --workers=1` 5件成功。すべて模擬APIで、実際の配信・本番操作は0。
- Terra実行の報告: 最終一覧表変更後のbuild/check:all/unitがexit0。rootもmain4734fe7f統合後にbuild/check:allをexit0、unit133件成功と確認した。
- root目視: PCの日本語一覧表、390pxの英語暗色表、工程内訳のラベルを確認。25枚の長い明細カードは一覧表へ修正済み。元の単位/状態/メモ/正規化値は行内詳細に保持。スマホでは表内だけ横スクロールしページ全体は横にはみ出さない。
- 撮影先: `/tmp/reports/pmg-screen-completion/desktop-table-ja.png`、`mobile-table-en.png`。アプリ内スクロール/固定ナビの影響で画面外要素を含むelement/fullPage画像は目視合格の根拠に用いず、対象を実際にスクロールしたviewport画像を使用する。
- 配信画像の初回は試験のmock不足で404表示となった。配信成功系/確認操作は別のE2Eで成功済み。撮影用fixtureも有効な既存API応答へ揃え、該当E2E1件成功・desktop-distribution-ja.pngの配信候補/全件配信ボタン/全体範囲をrootが再撮影画像で確認済み。

### PR3416リリースの一次情報

- PR: https://github.com/shingo-ops/salesanchor/pull/3416 。最終head6459e7ca、MERGED17ebe93f、mergedAt2026-09-10T12:24:21Z。最終検査37success/8skip。
- GO記録後の検査でDesktopShell.tsxの省略引用が不在判定になったため、実在するfrontend/src/components/DesktopShell.tsxへ修正。正式process-artifacts全検査をローカルとCIで通過。製品コード変更なし。
- deploy run34476536034/job102868559798 success。実ログ2026-09-10T12:25:06ZのHEAD17ebe93f、12:27:27ZのDeployment completed successfullyを照合。事前バックアップ/Finalize/Verify success、SA-19 smoke skipped。
- 公開Appのindex-i0HIAxuW.jsのSHA256 adc6e6c79bf4adb70f057fce2552b2fce1a3cca9e0629616984ba50c87e46f3b。pmg-workflow__table/distributionScope/import_job_idの存在を確認。https://api.salesanchor.jp/api/health はok/database connected/redis connected/celery connected。
- Python標準urllibはローカルCA設定不足でTLS検証に失敗した。証明書検証は無効化せず、OSの証明書を使用するcurlで正常取得した。
- UIの操作試験はローカル模擬APIの5件。稼働環境では公開ファイル/health/配備ログを確認し、管理者の実データ操作や実配信を実行したとは称しない。


### 2026-09-10 確認待ち取込の仕入元5件登録

PO原文「新規登録する」を、直前に提示した5名それぞれの新規登録の承認として実行。対象は import_job_id `f030f2e6-d6ce-46f5-ad45-c5f0ced9b866` のみ。POの残タスク委任とPRマージ承認は受領したが、cxastragoの代理GO経路を有効化したとは扱わない。

本番読取専用照会（transaction_read_only=on、2026-09-10 14:37:54 UTC）で91投稿、pending_review、未解決5名、messages_linked_at=NULLを確認。登録前に対象状態、同名仕入元0件、稼働中resolve_supplierのコード本文SHA256 `7ffaa0bebbeb7c802ed74d4c231a376188ebb5d43575229e27b1b0dd8a843128`を照合。最初のAST照合は不一致で書込前に停止し、本番コード本文を読み直して本文一致による検査へ修正した。

POが許可したSSH経路で、稼働中APIの既存resolve_supplierへaction=createを5回渡した。HTTP経由の認証付き画面操作ではなく、SSH上の管理操作として既存関数を直接実行した。対象jobと仕入元表を各登録中ロックし、状態変化・同名追加時には停止する。コード改変、解析開始、配信は実行0回。

| 新規コード | 名前 | LINE接続登録数 |
|---|---|---|
| SP0241 | Ryum. | 1 |
| SP0242 | 谷村 | 1 |
| SP0243 | Ty事務員 | 1 |
| SP0244 | 板谷よしみつ | 1 |
| SP0245 | 鈴木（板谷STAFFアカウント） | 1 |

直接実行した検証: /tmp/pmg-register-five.py の外側/内側Python構文検査成功、check exit0、apply exit0。登録応答の残件数4→3→2→1→0、登録後の読取専用照会で上記5コード・各LINE接続1件・unresolved_count=0を確認。review_status=pending_review、messages_linked_at=NULLは維持。次は取込確定と抽出開始の運用工程であり、仕入元登録だけで解析済みと扱わない。製品履歴/切替設計のREVISEは継続。


### 2026-09-11 進捗表示の情報階層調査

起点origin/main57eb951e。専用release/pmg-progress-visual-hierarchy、preflight成功。他者のAGENTS.md変更を保持。Terra読取報告とrootによるImportWorkflowPanel/Badge/ProgressBar/CSS照合で、8行の抽出内訳と主要値が同じ強さで並ぶことを確認。既存Badge5variantを利用可能。ProgressBarは100%で成功色/Doneになるため本件の終了割合へそのまま採用しない。外部根拠と検証可能な7条件はdesign末尾。スクリーンショットの51/37/14/1019/313は状態fixtureとして利用し、本番の現在値とは断定しない。


進捗表示改善の最終実測: root直接実行の全unit143件、E2E8件、build/check:allは成功。詳細と初回失敗の区別、3viewport画像はdesignの「表示改善の実装・最終レビュー」。本番操作なし。共通部品/集計契約を維持して要確認導線と情報階層を変更した。


## 2026-09-13 3段階CTA製品実装の実物照合

基準origin/main dd1df11c。rootがImportWorkflowPanel上部actions/3cardsとuseImportWorkflowの5秒更新・遅延応答破棄を読取。Terra調査: tcg_import_progress.py:13-34に取込リンク起点CTE、37-46にcoverage envelope、107-135にitems filter。正規migration20260831_110000...:221-252にraw_text/received_at/is_active、supplier_channel_id nullable、extraction_jobs.status/error_messageを確認。新しいmessages/job GETはSELECTのみで実現、0明細エラーをjobs起点で保持。既存正規PGfixture test_tcg_import_progress_pg.pyとunit/E2Eが再利用可能。固定ルートの後に新規可変ルートを置く。

PO「この表示に変更してくれ」を実装承認として受領。root同一AIによるPlanner→Architect整合検査APPROVE（限定3カードCTA+必要GET）。正式カードlint exit0。新しいライブラリ仕様の調査なし。本番への再抽出/配信POSTは含めない。詳細契約/受入表/Whyはdesign.mdの同日実装設計節。実装・試験結果は追記待ち。


## 2026-09-13 3カードCTA実装の未完了記録

設計APPROVE/実装承認済み、製品実装は未完了で審査REVISE。詳細はreports/pmg-stage-card-actions/HANDOFF.md。暫定実装の状態管理/表示/試験不足とRuff4件を根拠付き保存。既存担当の未実施報告反復により担当引継ぎを検討、新規起動のPO明示委任待ち。未コミット・PRなし・本番未変更。


### 3段階カードCTA・実装検収（2026-09-13）

担当交代: POの新規担当1名への委任承認「進める」を受け、pmg_cta_completionが同じカード/作業台の未完差分を継承して完成。rootは製品を編集せず、差分・試験ログ・画像を審査した。

実装: 3カード下部に主CTAの高さを揃えた確認操作、成功/対象なし/エラーの分割バー。投稿と抽出jobの取込限定GET、results_presentフィルター、詳細のページング/表示更新/遅延応答除外を追加。投稿の再利用・現在無効・受信日時を表示。明細0件の抽出エラーを表示し、生例外を公開しない。詳細の原因不明と調査依頼の重複文言を画像審査で解消。

実装担当実行・root原ログ確認: frontend全unit26ファイル273件成功（対象3ファイル29件を含む）、実PostgreSQL18件成功/skip0、Playwright12件成功33.1秒、build/check:all/backend lint-ci終了0。check:allは218警告/0errors。backend lint-ciはRuff成功・Bandit high0、mypy非blocking診断532件を含むため型診断全解消とはしない。追加サービスの診断0、routerのfilename型診断は追加GET外の既存行。rootが直接git diff --check終了0、製品差分/試験コードと保存ログを照合した。rootは試験そのものの再実行を行っていない。

画面は模擬APIのPC1440/狭幅390・日本語light/英語darkで確認。rootはcards-{1440,390}-{ja,en}.pngとanalysis-action-390-ja.png等を直接閲覧。縦並びの解析CTAはスクロール後viewport到達・クリック成功を試験。CTAからPOST0、JS error0、横溢れ0、原文HTML非実行。初回390jaの1失敗は辞書編集中の同URL再読み込みと重なり、固定差分では12/12成功。待機追加による試験基準緩和なし。画像の44/1019/313等はfixtureであり本番実数ではない。

証跡保存先: reports/pmg-stage-card-actions/{all-unit,pg,check-final,build,backend-lint,e2e,colima-stop}.txt、cards/error/analysis-actionのPNG、verification-manifest.json（各SHA256）。専用Colima dist01-3258停止ログ確認、他者profile/本番変更なし。Gitには正式設計・試験コードを保存し、旧unfinished差分/キャッシュは含めない。

最終差分/視覚審査: APPROVE（root、担当実装と照合）。限定設計の受入を満たし、PR/CI確認へ進める。新GO未受領、未マージ・本番未反映。設計審査は同一AI自己審査であり独立第二者レビューとは称さない。配信候補集計の不一致、再抽出操作、全体ダッシュボードの残設計は今回解消していない。


### 公開pushの承認待ち（2026-09-13）

ローカル実装commit8bb8df00、最新main af269ae2の文書変更を統合したHEAD f17d9c349eff0e1ae9c3b4360e12b366852273d8。統合は文書のみ、双方の根拠登録を保持。通常pushは実行前の自動承認レビューで2回拒否された。読み取り照合でorigin=https://github.com/shingo-ops/salesanchor.git、GitHub owner/name一致、isPrivate=falseを確認。拒否理由は「公開GitHubへの送信についてユーザー本人の明示承認が必要。表示変更依頼・担当カード/root指示では不足」。制限解除・別送信経路・force等の迂回はしない。

現在地: 実装/ローカル検証/審査/ローカルコミット済み。push未実施、PR未提出、PR CI未実行、マージ/本番未実施。次はPOの公開push・PR提出の明示承認を受領後に通常手順を再開。マージには別途新PR番号のGOが必要。検証ログと画面20ファイルは親引継ぎ作業台reports/pmg-stage-card-actions-final-20260913にもSHA256照合して複製済み。


### 公開push・PR提出の本人承認受領（2026-09-13）

直前の質問「公開GitHubリポジトリへ変更をpushし、PRを提出してよいですか？」に、PO原文「進めてくれ」を受領。公開送信先shingo-ops/salesanchorのrelease/pmg-stage-card-actionsへの通常pushとmain向けPR提出を承認した回答として記録する。上の公開送信承認待ちは解消。preflight終了0、ローカル検収済み差分と最新mainを照合して通常手順を再開する。これは新PR番号のマージGOではなく、本番反映は未承認・未実施。
