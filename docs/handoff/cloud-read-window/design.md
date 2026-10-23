# design: クラウドから本番を「読むだけ」できる窓口（段階2）

状態: 設計案作成済み／設計審査済み（同一AIの自己審査）／PO承認済み（2026-10-23 チャット「1」＝成功条件 K1〜K9 で進め、実装・確認・本番反映まで）／便1 実装・本番反映済み（#4687、2026-10-23 15:19 JST マージ。窓口コンテナ起動を deploy 記録で確認。鍵の GitHub secret 登録済み・次の deploy で有効化。K1〜K9 の測定は進行中）
根拠: [recon.md](recon.md)（同じフォルダ）、ADR 案: [ADR-1042](../../adr/ADR-1042-cloud-read-window.md)

## 1. 目的
PO 2026-10-22「クラウドでもいまと変わらない環境を構築したい、本番への読み取りも、hookも」。
手元の Mac では、ADR-1024 の道（SSH 鍵 → 専用コンテナ → 読み取り専用ユーザー）で本番を読んでいる。クラウドは SSH が使えず、HTTPS しか出られない（recon §7）。そこで、同じ守りのまま HTTPS で読める窓口を作る。
- 対象: 読み取りだけ。手元で使っている SQL の読み方（recon §6）がクラウドでもそのまま使えること。
- 対象外: 書き込み（当面は PO の `!` のまま）、段階3（社外秘の材料の置き場所）、段階4（結果の持ち帰り）、手元の SSH の道の変更。

## 2. 成功条件
| No | 基準（POが○×で判定） | 検証方法 |
|---|---|---|
| K1 | クラウドから本番の件数を読むと、手元の SSH の道と同じ数が返る | 同じ SQL 3本（在庫件数・解析件数・商品件数）を両方で実行し、3本とも一致 |
| K2 | 書き込みは必ず断られる | UPDATE・DELETE・INSERT・DROP・複文・SET・COPY・`\` 始まり・pg_sleep・EXPLAIN ANALYZE の10種を送り、10種とも拒否。DB の行数が前後で同じ |
| K3 | 鍵なし・違う鍵・鍵の設定が無いときは、誰も入れない | 3通りとも 401。サーバー側の鍵を空にした状態でも 401（fail-closed） |
| K4 | 秘密の列は伏せ字で返る | `*_token_encrypted` 等を含む SELECT で値が `<redacted>`（手元の道と同じ） |
| K5 | 1回読むごとに「いつ・何を読んだか」の記録が残る | 10回読んで、記録置き場（Loki）に10行。記録できないときは結果を返さない |
| K6 | 同時に読むのは2本まで。手元の SSH の道は今まで通り | 同時3本で3本目は「混雑」で断られる。手元の道で K1 の SQL が通る |
| K7 | 止めたいときは1分以内に全部止まる | 停止手順を実行し、60秒以内に全リクエストが 401 または 503 |
| K8 | 本番アプリに影響しない | 導入前後で app/api の応答（既存の死活監視）が全件成功。本番機のメモリ増加 150MB 以下 |
| K9 | クラウドの会話記録・環境変数に鍵の文字列が出ない | クラウド試行で `env` と会話記録を鍵の先頭8文字で検索し0件（照合は手元で、値は画面に出さない） |

## 3. 方式（採用: 案B）
クラウド → `https://api.salesanchor.jp/api/v1/ops/read-window/query`（POST、本文に SQL）→ nginx → **新しい専用コンテナ `ai-reader-http`** → `ai_reader` で DB を読む。

### 3-1. 専用コンテナ `ai-reader-http`
- docker-compose.ai-reader-http.yml（新規）。`ai-reader` と同じ守り: 環境変数は `AI_READER_DATABASE_URL` と窓口の鍵 `READ_WINDOW_TOKEN` だけ。volumes なし（/dev/log のみ）、`read_only`、`cap_drop: [ALL]`、`no-new-privileges`。
- ネットワークは frontnet（nginx から届くため）と backnet（DB へ届くため）。ports は開けない（外から直接は届かない）。
- 中身は backend/app/ops/read_window_http.py（新規）。検査・実行は readonly_query.py の関数をそのまま呼ぶ（拒否の規則・上限・伏せ字を二重に書かない＝正本は readonly_query.py の1か所）。
- 同時実行は1本まで（2本目は 429 で即答。待たせない。D1）。60秒で打ち切り。
- 鍵の比較は `secrets.compare_digest`（ops_error_reports.py:82 と同じ）。`READ_WINDOW_TOKEN` が空・未設定なら全員 401（ADR-1025 と同じ）。
- 監査: 1回ごとに AUDIT 行を /dev/log へ（ADR-1024 と同じ形に `via=https` を足す）。送れなければ 503 で結果を返さない。

### 3-2. nginx
- api の server ブロックに `location = /api/v1/ops/read-window/query` を1つ足し、`ai-reader-http:8080` へ送る。
- 専用の速度制限 `zone=read_window rate=2r/s burst=4`。本文の上限 `client_max_body_size 64k`（台本の SQL 上限と同じ）。
- IP 許可は使わない（クラウドの出口 IP は固定と書かれていない。recon §7）。認証は鍵だけになるので、鍵は長く（32バイト乱数）、90日で更新する。

### 3-3. 鍵の置き場所（データを分散させない）
- 正本は GitHub secret `READ_WINDOW_TOKEN` の1か所。deploy.yml がサーバーの env ファイルへ書き、コンテナへ渡す（`OPS_API_TOKEN` と同じ道。recon §4）。
- クラウド側は「ネットワークシークレット」に同じ値を1回だけ登録する（ホスト `api.salesanchor.jp`、ヘッダ `X-Read-Window-Token`、前置きなし。D6）。鍵は VM に出ない（recon §7）。環境変数には置かない。
- 登録は PO が claude.ai の画面で行う（外部の画面操作のため）。値の受け渡しは手元のファイル経由とし、チャットに出さない。
- docs/B-11_credential_management_policy.md の90日表に `READ_WINDOW_TOKEN` を足す。

### 3-4. GO の境界
- `backend/app/ops/` と docker-compose.ai-reader.yml は既に process-artifacts gate の危ない変更に入っている（ADR-1024 §7）。新しいファイル名がこの対象に入るかは、便1カードで定義の実物と照合し、入らなければ対象に足す。窓口のコードを変えるには GO 記録が要る形にする。docker-compose.ai-reader-http.yml を DANGEROUS_PATTERNS に足す（D4）。nginx/nginx.conf は足さない（窓口の守りは鍵と DB の権限にあり、nginx の変更では広がらない）。

## 4. 代替案
| 案 | 内容 | 判断 |
|---|---|---|
| A | backend に専用鍵の API を足し、`AI_READER_DATABASE_URL` を backend に渡す | 不採用。ADR-1024:59 が不採用にした「書ける接続・暗号鍵と同じ場所」をそのまま作る。blue-green 切替中に窓口が消える |
| B | ai_reader だけを持つ専用コンテナを常駐させ、nginx から送る | **採用**。ADR-1024 の守り（接続は読む人だけ・秘密を置かない）をそのまま保つ |
| C | 専用コンテナが要求ごとに `ai-reader` を起動する | 不採用。docker の操作口をコンテナに渡すことになり、本番機全体を動かせてしまう |
| D | 新しいサブドメイン（read.salesanchor.jp）を作る | 不採用。DNS と証明書の外部操作が増える。パスを分けるだけで速度制限・監査は分けられる |
| E | IP 許可で守る | 不可。クラウドの出口 IP が固定と書かれていない |

## 5. リスクと対処
- 鍵が漏れると、外から本番を読まれる → 読めるのは ai_ro（秘密列なし）だけ。同時1本（手元の SSH の道と合わせて全体で2本まで）・2回/秒。90日更新。K7 で即停止。
- 常駐コンテナでメモリが増える → K8 で150MB以下を確認。prod1 の空きを実装の最初に測り、足りなければ止めて相談。
- デプロイ中の約70秒は ai_ro が外れる（recon §3）→ 窓口はエラーを返すだけ。クラウドへの依頼文に「42P01 なら1分待って再試行」と書く。
- 中身（本番の値）は Anthropic のクラウドを通る → PO 2026-10-22「データをクラウドに預けることを許容する」で許容済み。ただし PR・リポジトリには載せない決まりは残る。

## 6. 戻し方
- 即停止（K7）: `docker stop ai-reader-http`（nginx は 503）。止め続けるには加えて GitHub secret `READ_WINDOW_TOKEN` を消す（空なら全員 401。サーバーの鍵を空にするだけでは次の deploy で secret から書き戻される。D7）。
- 完全撤去: compose ファイル・台本・nginx の1か所を git revert、GitHub secret を削除、PO がクラウドのネットワークシークレットを削除。DB は何も変えないので戻す作業は無い。

## 7. 実装の分け方（カードは PO 承認後に発行）
- 便1: 窓口コンテナ・nginx・deploy・B-11 追記（本番変更。GO 記録が要る）。手元で K2〜K6 を試す。
- 便2: 鍵を作り GitHub secret へ（PO が `!` で実行）→ PO がクラウドにネットワークシークレットを登録 → クラウド試行で K1・K7・K9、本番で K8。

## 8. 外部・過去事例の参照と我々への応用
- Anthropic 公式文書が、クラウドから社内 API を呼ぶ方法としてネットワークシークレットを示している（recon §7）。数値つきの導入事例は見つけていないため、成功の証明には使わない。効果は K1〜K9 の実測で測る。

## 9. 維持の仕組み
- 守り手: Opus（設計統括）。鍵の90日更新は B-11 の表に載せ、週次保守の点検対象に入れる。
- 拒否の規則・伏せ字の正本は readonly_query.py の1か所。窓口は呼ぶだけなので、手元の道を直せば窓口も同時に直る。

## 10. 審査（Architect・同一AIの自己審査）
判定: APPROVE（設計として）。実装は PO 承認後。
- 根拠: 守りの本体（DB の GRANT・ai_ro・GO 境界）は ADR-1024 のまま変えない。新しく足すのは「入口」だけで、鍵・速度・監査・停止のそれぞれに検証方法がある。
- 未解決（実装で測るもの。設計の成立は妨げない）: prod1 の空きメモリ（K8）、routine でネットワークシークレットが効くか、会話記録に鍵が出ないか（K9）。いずれも外れたら止めて相談する。

## 11. 実装前の具体化（2026-10-23）
便1 実装カード（card-1.md §0）での Opus 決定。実物（本番実測・コード）に合わせて §3・§5・§6 を直した。
- D1 同時数: ai_reader の接続上限は 2（本番実測 rolconnlimit=2、max_connections=100）。窓口は同時1本、もう1本は手元の SSH の道に残す。全体で2本まで。DB の上限は変えない。
- D2 別プロジェクト: deploy.yml の `--remove-orphans` に消されないよう、compose の `name:` は `astro-webapp-readwindow`。ネットワークは既存の `astro-webapp_frontnet` と `astro-webapp_backnet` を external で使う。`container_name: ai-reader-http`。.env の COMPOSE_PROJECT_NAME が top-level の name: より優先されるため、起動は必ず -p astro-webapp-readwindow を付ける。
- D3 nginx は resolver 127.0.0.11 と変数で送る（コンテナが居なくても nginx は起動する）。落ちているときは 503（`error_page 502 504 =503`）。
- D4 GO の境界: `docker-compose.ai-reader-http.yml` を DANGEROUS_PATTERNS に足す。nginx/nginx.conf は足さない。
- D5 接続情報の正本は VPS の /home/ubuntu/.config/salesanchor/ai-reader.env の1か所。compose は `env_file` で読む（値を写さない）。窓口の鍵は deploy が .env に書く `READ_WINDOW_TOKEN`（空なら全員 401）。
- D6 鍵のヘッダは専用の `X-Read-Window-Token`（前置きなし）。`Authorization` は使わない（保守用 OPS_API_TOKEN と取り合わない）。クラウドのネットワークシークレットはヘッダ名を変えられる。
- D7 止め続ける手順: 即停止は `docker stop ai-reader-http`。止め続けるには加えて GitHub secret `READ_WINDOW_TOKEN` を消す。
- D8 既知の重なり: 窓口の読み（最長60秒）と deploy の ai_ro 作り直し（ロック待ち1秒・最大40回、ADR-1037）が重なると作り直しが失敗しうる。失敗時の作り直しは #4618 の仕組み。usage-cloud.md に「重い読みは短く分ける」を書き、K8 の測定期間に deploy があれば結果を記録する。
