<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# recon — マイグレーション実行方式の見直し

**仕事名**: migration-runner-redesign  
**日付**: 2026-10-04  
**対象ADR**: ADR-1005（草案）、ADR-045、ADR-082、ADR-1002  
**担当**: 設計担当 Opus（調査は Sonnet に委任、主要な事実は Opus が実物で再確認）

---

## 0. 一言でいうと（PO 向け）

DB を変える手順（マイグレーション）は 317 件あり、デプロイのたびに 1 番から全部やり直している。どれを実行済みかの記録は無い。この「毎回やり直し」が、2026-10-03 の事故（商品の表の列番号を使い切った）など少なくとも 4 件の障害の原因になった。一方で、新しいテナントを作るときの「ひな形」が手順より遅れており、その穴を「次のデプロイでのやり直し」が埋めている。だから、やり直しをいきなり止めることはできない。

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `scripts/run_all_migrations.sh:14` | 「全マイグレーションは冪等設計（何度実行しても安全）」が前提として書かれている |
| `scripts/run_all_migrations.sh:20` | `set -e`。どこかで1件失敗すると以降は実行されない |
| `scripts/run_all_migrations.sh:530` | `migrations/20260831_110000_create_tcg_analysis_tables_t004.sql` の登録（1回目） |
| `scripts/run_all_migrations.sh:536` | 同じファイルの登録（2回目・重複） |
| `.github/workflows/deploy.yml:501` | 実行条件は広いフィルタ `steps.changes.outputs.migrations`（backend/** の変更でも全件やり直し） |
| `.github/workflows/deploy.yml:514` | `bash scripts/run_all_migrations.sh` を実行 |
| `.github/workflows/deploy.yml:178` | デプロイ前バックアップは狭いフィルタ `db_migrations`（#3955） |
| `.github/workflows/migration-test.yml:937` | 「変更されたSQLを2回実行」の対象は3桁数字で始まるファイル名 |
| `.github/workflows/migration-test.yml:1660` | 「全件ドライラン」の対象は 0 / 20260604〜20260629 で始まるファイルだけ |
| `docs/adr/ADR-045-migration-055-deploy-automation.md:96` | 「migration 適用は冪等なので、2回実行されても安全」（全件やり直しを選んだ理由） |
| `docs/adr/ADR-082-deploy-skip-migrations-on-frontend-only.md:44` | 冪等なので、新しい手順が無いデプロイでは実行を省いても状態は同じ |
| `docs/adr/ADR-1002-unify-product-id-and-fix-migration-compat.md:23` | 「全242本を毎回再実行する設計。実行済み台帳によるスキップ機構はない」（同じ課題が既に記録済み） |
| `backend/app/services/tenant.py:184` | 新テナント用ひな形 `_TENANT_TABLES_SQL` の開始 |
| `backend/app/services/tenant.py:586` | ひな形の staff 表（586〜607 行）。phone・avatar_token・is_employee の列が無い |
| `backend/app/services/tenant.py:1620` | `create_tenant_schema`（新テナント作成時にひな形から表を作る） |
| `backend/app/services/tenant.py:1652` | `CREATE SCHEMA IF NOT EXISTS` |
| `migrations/083_add_staff_phone.sql:42` | 既存の全テナントに staff.phone を足す手順（毎デプロイ再実行） |
| `migrations/20261001_120000_add_staff_avatar_token.sql:36` | 既存の全テナントに staff.avatar_token を足す手順 |

---

## 1. 数の事実（Sonnet 調査、設計担当が主要部を再確認）

- 登録数：run_sql 291 行（同じファイルの重複 1 件を含むため、ファイルとしては 290 件）＋run_py 26 行＝317 行（設計担当が `^run_sql ` と `^run_py ` の行数で再計測。分類の 317 行と一致）。migrations/ にあるが登録されていないファイル：62 件（古い番号付きの手順が中心。意図的に外したかは【未確認】）。
- 手順の分類（317 登録行・正規表現による自動分類＋人の目で確認）：
  - A 一度で済む構造変更：225
  - B 一度で済むデータ変更：52
  - C 毎回の実行に意味があるもの：22
  - D 無効化済み（何もしない）：18
  - 分類の確度：C の 22 件は自動判定と人の目の両方で確認（高）。テナント全体に繰り返す A 約 115 件は自動の列名照合のみ（中）。
- 実行済みの記録：リポジトリに記録の仕組みは無い（schema_migrations / alembic / flyway の検索 0 件）。本番 DB に名前に migrat を含む表は 0 件（読み取り確認）。
- 所要時間：直近の成功デプロイ 4 回で「Run database migrations」は 66〜67 秒。
- 事前テスト：全件ドライランの対象は、登録された SQL 290 件（重複を除く）のうち 128 件。162 件（56%）が対象外（設計担当が `.github/workflows/migration-test.yml:1660` と同じ条件で再計測）。

## 2. 「毎回やり直し」が原因の障害（事実）

1. 2026-10-03：列の追加→削除の繰り返しで商品の表の列番号が上限 1600 に到達。修正に PR 5 本（#3958〜#3963）。
2. 2026-09-15：古い表を削除した後、過去の手順の再実行が古い表を参照して失敗（ADR-1002）。
3. 追加→削除のデータ手順の組が毎デプロイ衝突（`migrations/20260924_040000_seed_knowledge_extraction_vocab.sql` の注記）。
4. 同じ手順の二重登録による順序の事故（docs/handoff/fix-migration-runner-dup/design.md）。現在も別ファイルで二重登録が 1 件残る（530 行と 536 行）。

## 3. 新テナントの作り方とひな形の遅れ（最重要）

- 新テナントの表は、手順の再実行ではなく `create_tenant_schema` がひな形から作る（`backend/app/services/tenant.py:1620`）。
- しかし、ひな形は手順より遅れている。テナント全体に列を足す手順のうち、ひな形に無い列が少なくとも 19 手順・約 40 列（例：staff.phone、staff.avatar_token、staff.is_employee、leads の各種リンク列、invoices の PayPal 列、meta_messages の 8 列、tenant_meta_config.granted_scopes）。設計担当が staff 表で実物を確認（586〜607 行に phone・avatar_token・is_employee が無い）。
- 今は問題が表に出ていない理由：新テナントを作った後の次のデプロイで、全件やり直しが足りない列を足すため。本番の全 5 テナントの staff には 3 列とも存在（読み取り確認）。
- 本番のテナントは 5 件、最後の作成は 2026-05-14。それ以降は作られていない（読み取り確認）。
- 権限付与：テナントごとの権限付与（`migrations/20260605_040000_grant_salesanchor_app_tenant_schemas.sql`）は、ひな形側にも同じ処理がある（tenant.py の create_tenant_schema 内）。public の権限付与（`migrations/20260605_030000_create_salesanchor_app_role.sql`）は「その時点の全表」に付与する形。

## 4. テナント間の表の作り（本番・読み取り確認）

| テナント | 表の数 | 列の数 | 形の指紋 |
|---|---|---|---|
| tenant_001 | 101 | 1173 | bddf259d… |
| tenant_003 | 71 | 908 | adfd0b79… |
| tenant_004 | 93 | 1074 | 2d6aa328… |
| tenant_005 | 71 | 908 | adfd0b79… |
| tenant_006 | 71 | 908 | adfd0b79… |

- 003・005・006 は完全に同じ形。001 と 004 は表が多い。何の表が多いのかは【未確認】（次の調査で確かめる）。
- 注：本 §4 と §3 の本番の数字は設計担当 Opus が読み取りで確認したもので、Architect 審査は本番に触れていない（第三者による再確認は未実施）。
- 注：この確認の SQL で、設計担当は区切り文字を文字コード指定（chr）で書いた。読み取りのみで実害は無いが、符号化を避ける自分の規則に反するため、以後は使わない。

## 5. 外部の一般的なやり方（公式資料で確認、Sonnet 調査）

- Flyway：実行済み記録の表（flyway_schema_history）にファイルごとの版・チェックサム・成否を残し、未実行のものだけを実行。既存 DB には baseline（その時点までを実行済みとして記録）。毎回実行したいものは R__ の別種類として扱い、内容が変わったときだけ再実行。実行済みファイルを書き換えると検証で停止（CHECKSUM_MISMATCH）。テナントごとのスキーマは「ループで1テナントずつ適用する」方式が公式 FAQ に記載。PostgreSQL では 1 手順を 1 トランザクションで実行し、失敗時は巻き戻す。
- Alembic：alembic_version 表に現在の版を記録。既存 DB には stamp。
- golang-migrate：schema_migrations 表と dirty フラグ。既存 DB には force。
- PostgreSQL 16：削除した列も 1600 列の上限に数えられる（https://www.postgresql.org/docs/16/limits.html）。

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | tenant_001・tenant_004 の多い表は何か（現役か、古い残骸か） | 本番の表名一覧を読み取りで比較 | 未解消（設計の段階1で確認） |
| 2 | ひな形に無い列の全件（自動照合で約 40 列。改名・型変更は照合できていない） | 本番の tenant_003 とひな形から作った表の列を機械比較 | 未解消（段階1で確認） |
| 3 | 登録されていない 62 件は本番に適用済みか | 本番の表・列と照合 | 未解消（段階2の前に確認） |
| 4 | 「後で実行される手順を前提にした」注記のある約 30 件の安全性 | 1 件ずつ読む | 未解消（段階2の前に確認） |
| 5 | 全件ドライランが 2026-06-30 以降を対象外にしている理由（正規表現の更新漏れか、意図か） | migration-test.yml の履歴と注記 | 未解消（段階0で確認） |

**未解決ゼロ確認**: 未解決あり（上記 5 件）。いずれも実装の各段階に入る前に解消し、解消するまでその段階に入らない。

---

## 補足

- 生の調査結果（317 行の分類表）は設計担当の作業領域に保存。repo には件数と根拠のみ載せる。
