# recon — 設定配線SSOT

この文書は何か（専門用語なしの1行）: アプリの設定値が今どこに書かれ、どの部品に届いて届いていないかを、実測だけで書き出した現状報告。

親（設計仕様書）へのリンク: ../../specs/config-delivery-ssot/README.md

- 仕事名: config-delivery-ssot
- 日付: 2026-09-06
- 実測時の origin/main SHA: b877b14a865a5609278fcc876e6be9e4e890d99a
- 対象ADR: ADR-115（deploy-safety）
- 担当: 設計パートナー（実測は実装役カード R-01〜R-08 の生出力による）
- 区分（STANDARD-WORKFLOW 1.8）: 新規テーマ（索引 docs/specs/README.md に設定配線の項目が無く、既存の secrets-permission-ssot は鍵と権限のみを対象とするため）

---

## 0. 既存ADR検索の結果

- `git grep -il -E "環境変数|env-file|docker run|compose|cutover|blue-green" -- docs/adr/` → 30件（head 上限に達したため全件ではない）。うち deploy 系は ADR-045 / ADR-082 / ADR-092 / ADR-115 / ADR-130 / ADR-137 / ADR-SA-19。
- `docs/adr/FEATURE-INDEX.md` の一致は1件（:58 migration の expand-contract 運用）。設定の伝達経路に関する項目は無い。

事実: 設定をどの経路でコンテナへ渡すかを決めたADRは、本検索の範囲では見つかっていない。

---

## 1. 全体像（設定が届く3つの経路）

- `scripts/blue-green-cutover.sh:80` の `docker run` が backend を起動する。
- 同:92 `--env-file "${REPO_DIR}/.env"` が、.env に文字として書かれた行だけをコンテナへ渡す。
- 同:93,94 が個別指定の2行（GOOGLE_APPLICATION_CREDENTIALS / TCG_SCHEMA）。
- `.github/workflows/deploy.yml:335` の `docker compose up -d --no-deps` が frontend・celery-worker・celery-beat・discord-gateway を起動する。
- `docker-compose.yml:65` 以下の `environment` は、compose が `${VAR:-既定値}` を展開して渡す。

事実: backend だけが compose を経由しない。compose の `environment` に書いた既定値は backend に届かない。

---

## 2. .env に何が書かれるか

- `.github/workflows/deploy.yml:206` 付近が `touch .env` → `sed -i.bak` で既存行を削除 → `cat >> .env` で追記する。
- 追記される名前は同ファイルの heredoc に列挙されたものに限る。
- `git grep -n "TCG_SCHEMA" -- .env.example .github/workflows/deploy.yml scripts/blue-green-cutover.sh` の一致は1件（cutover.sh:94 のみ）。deploy.yml と .env.example は0件。
- `.env.example:129` に `TCG_SHEETS_SA_KEY_FILE` が在る。`DEPLOY_LOG.md:60` に、これを .env へ手で追加した記録が在る。

事実: TCG系の設定は deploy.yml の自動書き込みの対象外であり、人手または cutover.sh の個別指定で届いている。

---

## 3. 既定値の所在

`git grep -n -E ":-tenant_004" -- docker-compose.yml scripts/ .github/ backend/app/tcg_config.py` の一致4件。

- docker-compose.yml:116（backend）
- docker-compose.yml:219（celery-worker）
- docker-compose.yml:256（celery-beat）
- scripts/blue-green-cutover.sh:94

加えて `backend/app/tcg_config.py:20` に `os.getenv("TCG_SCHEMA", "tenant_004")` が在る。

事実: 同じ既定値 `tenant_004` が5か所に書かれている。QA用スキーマへ切り替える際にどこを変えるのが正かは、文書に定義されていない。

---

## 4. 名前の突き合わせ

- `backend/app` 配下で `os.getenv` / `os.environ.get` が読む名前 = 70種。
- `docker-compose.yml` の backend サービスが渡す名前 = 31種。
- 差分（コードが読むが backend の environment に無い）= 43種。

事実: 43種が未宣言である。ただし各名前が既定値で足りているか、celery 専用かは本reconでは判定していない。

---

## 5. 維持の仕組み

守り手の実物。

- `backend/tests/test_tcg_schema_qualification.py` — SQL文字列のスキーマ修飾を静的に検査する。
- `backend/tests/test_tcg_config.py` — TCG_SCHEMA の既定値・不正値・上書きを検査する。
- `backend/app/tcg_config.py:21-27` — `^tenant_\d{3}$` に合わない値でコンテナ起動を失敗させる。

守り手が無い箇所（名指し）。

- 「コードが読む設定名」と「compose が渡す設定名」を突き合わせる検査は存在しない。
- `scripts/smoke_test_post_deploy.sh`（195行）の `docker exec` 17か所はすべて postgres コンテナを対象とする。backend コンテナ内の設定値を読む処理は存在しない。
- 設定を新しく足すときの手順書は、`git grep -il -E "環境変数を(追加|足す)|新しい環境変数|環境変数の追加" -- docs/ README.md CLAUDE.md .env.example` の一致1件（docs/PHASE5_DOMAIN_CUTOVER_RUNBOOK.md）のみ。設定追加の一般手順としては未確認。

---

## 6. 同じ原因で起きた過去の事象

- `docs/handoff/tcg-auto-analyze-enable/` — TCG_AUTO_ANALYZE を compose にだけ足し、backend に届かなかった。
- `docs/handoff/dist-sa-key-mount/` — 鍵ファイルのマウントを compose にだけ足し、backend に届かなかった。
- `docs/handoff/tcg-schema-env/` — 同じ原因を踏まえ、compose と cutover の両方へ足した。design.md は「全経路で `${TCG_SCHEMA:-tenant_004}` 形式を採用」と、既定値の複製を設計として選んでいる。維持の仕組みは「PR前に git grep する運用」＝人手。
- `docs/handoff/tcg-2026-09-05-summary/recon.md:52` — 2026-09-05 に同一原因で2回、本番が停止したとの記録。

分裂の起点。`docs/handoff/zero-downtime-deploy/design.md:74` の `docker run` 例は、渡す環境変数を `... (同等 env) \` と省略で記している。同 design.md に「維持の仕組み」の節は無い（`grep -n "^## "` の一致6件に含まれない）。

---

## 7. 設計図との対照（一致／不足／余剰）

親 docs/specs/config-delivery-ssot/kgi.md の各KGIと、実物の対照。

| KGIの項目 | 現状値（実測） | 判定 |
|---|---|---|
| K1 cutover の個別指定が0行 | 2行（cutover.sh:93,94） | 不足 |
| K2 `:-tenant_004` の重複が0行 | 4行（compose 116/219/256・cutover 94） | 不足 |
| K3 名前の突き合わせ検査 | 存在しない | 不足 |
| K4 起動後の設定値実測 | 存在しない | 不足 |
| K5 業務ON/OFFのDB一本化 | 環境変数を読む実行行1件（tcg_extraction.py:219）。受け皿の表は実在（migrations/20260903_210000・tcg_distribution_svc.py:578,586） | 不足 |
| K6 設定追加の手順書 | 一般手順としては未確認 | 不足 |
| 設計図に記載なし | tcg_config.py の起動時バリデーション（不正値でコンテナ起動失敗） | 余剰・要判定 |
| 設計図に記載なし | test_tcg_schema_qualification.py（SQL修飾の静的検査） | 余剰・要判定 |

余剰2項目は、POが「残す（あるべき姿に採用）」か「除く」かを判定する対象。本reconでは判定しない。

---

## 8. ノイズと境界

本reconで見ないと決めた範囲。

- monitoring 系 compose（docker-compose.monitoring.yml / .exporters.yml / .test.yml）— 存在のみ確認、中身は読んでいない。
- deploy.yml の全体（設定の書き込み部分と cutover 呼び出し部分のみ実測）。
- VPS 上の .env の実物 — 本reconはリポジトリのみを対象とし、サーバーへ接続していない。
- 差分43種の内訳（どれが実害か）。

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|---|---|---|
| 1 | 差分43種のうち実害があるのは何件か | サービス別に読み手を分けて再集計 | 未解消 |
| 2 | cutover.sh:93 の認証情報指定を compose へ寄せてよいか | ファイルパスの前提を design で確認 | 未解消 |
| 3 | K4 を本番でどう実行するか（機体・鍵） | design 局面で実測 | 未解消 |
| 4 | 余剰2項目を残すか除くか | POの判定 | 未解消 |
| 5 | 設定追加の手順書が既に別名で存在しないか | 追加の横断検索 | 未解消 |

未解決ゼロ確認: 未解決5件あり。いずれも design 局面またはPO判断で解消する。

---

## 実測の出所

- ファイル実測: 全て `git show origin/main:<path>` および `git grep ... origin/main` を SHA b877b14a865a5609278fcc876e6be9e4e890d99a 指定で実行。ローカル作業ツリーは読んでいない。
- サーバー・DBへの接続は行っていない。書き込みは一切行っていない。
- 一部の出力は head で上限に達している（§0 のADR一覧30件、backend/app の前後文脈120行）。全件ではないことを明記する。
