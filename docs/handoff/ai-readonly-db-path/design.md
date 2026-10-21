---
mode: handoff
adr: ADR-1024
status: Proposed（設計のみ・実装未着手）
---

# 設計: AI 用「本番 DB を読むだけの道」

> この文書は何か（専門用語なしの1行）:
> AI の担当が、許可待ちで止まらずに本番のデータを「読むだけ」できる専用の道を作るための設計。書き込みはできない形にする。

- 親（ADR）: [ADR-1024](../../adr/ADR-1024-ai-readonly-db-path.md)
- 根拠（現状）: [recon.md](recon.md)（docs/handoff/ai-readonly-db-path/recon.md）
- 実装カード: [card-bin3a.md](card-bin3a.md)（便3a）
- 設計仕様書（あるべき姿）: 該当する仕様書は未作成（索引 [docs/specs/README.md](../../specs/README.md) に載る領域ではない）。近い領域は [開発の無駄な停止ゼロ](../../specs/dev-continuity/README.md)。実装便に進む前に、仕様書を作るか対象外とするかを PO が決める（§10 未決 1）。
- PO 決定: PO 承認済み（2026-10-17 チャット、原文 y）。Q0「読むだけの DB 利用者と読むだけの鍵で進める」、Q1「全テナントを読めるようにする」、Q2「強めた構成で進める（ビュー専用スキーマ ai_ro を最初から入れ、BYPASSRLS と pg_read_all_data は付けない。専用 ai-reader コンテナ、log_statement=all、restrict と expiry-time、CODEOWNERS で PO 必須レビュー、秘密列は外す）」。
- 状態: 設計案／同じ AI による設計審査（Fable、判定 REVISE）の指摘 9 件を反映済み／PO 承認済み／実装未着手

## 1. 目的と KGI

PO の言葉: 「権限不足で停止することが多い。どの権限を移譲すれば無駄な停止がなくなるか」。

KGI: 担当 Sonnet が、PO の `!` 実行と permit チケットなしで、本番 DB に読み取りの SQL を流し、結果をファイルに保存できる。その道では、書き込み・秘密列の読み取り・設定の迂回ができない。

## 2. 成功条件（○×で判定）

| # | 基準 | 検証方法 |
|---|---|---|
| K1 | 担当 Sonnet が、PO の `!` 実行と permit チケットなしで、本番 DB に SELECT を 1 本流し、結果をファイルに保存できる | 担当に `SELECT count(*) FROM ai_ro.<ビュー>` を依頼し、出力ファイルの件数と実行時刻を確認 |
| K2 | 同じ道では書き込みが失敗する（INSERT / UPDATE / DELETE / DDL がすべてエラー） | 試験用の 4 文を流して 4 本ともエラーになることを確認。台本の文字列拒否を通る形（台本を介さない `ai_reader` の直接接続）でも、DB の権限が拒否することを確認 |
| K3 | 1 回ごとに誰が何を読んだかがサーバー側に記録される | postgres のログと Loki（prod2）に K1 の SQL と時刻が 1 行ある（`log_statement=all`） |
| K4 | 書き込み用の鍵（manual-only）と PO の `!` 実行の決まりは変わらない | authorized_keys の manual-only に当たる行の差分が 0（追加は reader 鍵の 1 行だけ） |
| K5 | 読み取りの調査メモを書いただけでフックに止められない | 本文に「ssh」「psql」「<」を含む md を Write で保存し、拒否 0 |
| K6 | 秘密列が読めない | `ai_ro` のビューに、拒否リスト（`password*`・`*_encrypted`・`*_secret*`・`*_token*`・hash 系）に当たる列が 0 本（情報スキーマで数える）。別名を付けた `SELECT password_argon2_hash AS x FROM public.users` が権限エラー |
| K7 | `ai_reader` に BYPASSRLS・`pg_read_all_data` が付いていない | `pg_roles` の `rolbypassrls=false`、`pg_auth_members` に `pg_read_all_data` なし |
| K8 | 全テナントのビューが読める | `ai_ro` から tenant_001/003/004/005/006 と public の代表ビューを各 1 本 SELECT でき、件数が jarvis の直接 SELECT と一致 |
| K9 | 新しい表は、ビューを作るまで読めない（fail-closed） | テスト用に表を 1 つ足し、ビュー生成の前に `ai_reader` が読めないこと |
| K10 | `pg_authid` が読めない | `SELECT has_table_privilege('ai_reader','pg_authid','SELECT')` が false |
| K11 | 設定の迂回は境界でないことの証明（事故防止の位置づけの確認） | `ai_reader` が `SET statement_timeout='0'` を通せること（通っても、書き込み権限がないので被害は出ない） |
| K12 | `log_statement` を `ai_reader` が戻せない | `ai_reader` で `SET log_statement='none'` がエラー |
| K13 | 台本は `AI_READER_DATABASE_URL` 以外の環境変数を読まない | 未設定で終了コード 3。専用コンテナ内で `env` を取り、`DATABASE_URL`・`ADMIN_DATABASE_URL`・`METADATA_FERNET_KEY` が無い |
| K14 | 固定コマンド以外は動かない | reader 鍵で別のコマンドを指定しても、固定コマンドの標準入力として扱われるだけ（`SSH_ORIGINAL_COMMAND` を読まない）。`sshd -T` の `permituserenvironment`・`permituserrc`・`forcecommand`・`acceptenv` の結果を PO `!` で保存 |
| K15 | 鍵に期限と制限が付いている | authorized_keys の reader 行が `restrict` と `expiry-time`（90 日後）を含む。期限切れの日付で接続が拒否される試験（過去日の一時行は使わず、`ssh-keygen` の説明と実機の期限日付で確認） |
| K16 | 台本・compose 定義の変更は GO 記録なしでは止まる | `backend/app/ops/` と `docker-compose.ai-reader.yml` が process-artifacts gate で dangerous と判定され、GO 記録の無い本文では rc=1 になる（設計 K16 改訂の G1・G2 と同じ手順）。改訂前は CODEOWNERS の必須レビューを基準にしていたが、ruleset が強制しないため差し替えた |
| K17 | フック免除が鍵パスの完全一致だけ | `~/.ssh/salesanchor-reader` は免除、`~/.ssh/salesanchor-reader-rw` などの前方一致は免除されない（単体試験） |
| K18 | 負荷の上限 | 60 秒を超える照会が打ち切られる。行数の既定は 200、上限は 5000。同時 3 本目の接続が拒否される |

## 3. 方式（最初に入れるもの）

「何でもできる鍵を許可で縛る」から「読むことしかできない道」へ変える。読むことしかできないので、伝聞かどうかを問わず担当が使ってよい。

1. **DB**: 読み取り専用ユーザー `ai_reader`（LOGIN・NOSUPERUSER・NOCREATEDB・NOCREATEROLE・NOREPLICATION・CONNECTION LIMIT 2）。BYPASSRLS と `pg_read_all_data` は付けない。付ける権限は `ai_ro` スキーマの USAGE とビューの SELECT だけ。`ALTER ROLE` で `log_statement='all'`（利用者が戻せない設定）。`default_transaction_read_only=on`・`statement_timeout='60s'`・`idle_in_transaction_session_timeout='60s'` は事故防止として残すが、境界とは書かない（利用者が戻せる）。
2. **ビュー専用スキーマ `ai_ro`**: 秘密列を外したビューだけを置く。ビューの持ち主は jarvis（superuser は行の制限を受けない）。`security_invoker` は付けない。新しい表はビューを作るまで読めない。`scripts/run_all_migrations.sh` の最後でビューを作り直す。拒否リストは列名の型で決め、生成テストで「当たる列が 0 本」を確かめる。
3. **専用コンテナ `ai-reader`**: 環境変数は `AI_READER_DATABASE_URL` のみ、volumes なし、`read_only: true`、`cap_drop: [ALL]`、`no-new-privileges`、backnet のみ。固定コマンドは `docker compose -f <絶対パス> run --rm -T --no-deps ai-reader`。稼働中の backend に依存しない（blue-green の切替の影響も受けない）。
4. **台本 readonly_query.py（backend の ops 配下に新規）**: 標準入力の SQL を受ける（64KB まで）。クライアント側で `BEGIN READ ONLY` と `SET LOCAL statement_timeout` を自分で発行し、最後に rollback。文字列で拒否するもの: 先頭が `\`、複文、先頭語が SELECT/WITH/SHOW/EXPLAIN（ANALYZE なし）以外、`set_config(`・`SET `・`COPY`・`pg_read_file`・`pg_sleep`・`lo_` を含むもの。出力は TSV、行数の既定 200・上限 5000。結果の列名が拒否リストに当たる場合は値を `<redacted>` に置換（念のための二重目）。ログは stderr に 1 行（時刻・SQL の sha256 先頭 12 桁・先頭 500 文字・行数・所要 ms・結果）。
5. **SSH**: 新しい鍵 `salesanchor-reader`（ed25519、パスフレーズなし、Mac の `~/.ssh/salesanchor-reader`、権限 600）。VPS の authorized_keys の末尾に 1 行だけ追加: `restrict,command="<固定コマンド>",expiry-time="<90 日後>"`。既存の行は触らない。Mac の接続元が固定なら `from=` も付ける（未確認 U6）。
6. **ガバナンス**: `.github/CODEOWNERS` に台本・ai-reader の compose 定義・ai_reader の migration・ビュー生成を @shingo-ops で責任者として記載する（強制しない）。権限の境界は DB の GRANT、コードの境界は process-artifacts gate の GO 記録の二重にする（ADR-1024 改訂 K16）。
7. **フック（Mac 側・リポジトリ外・便4）**: reader 鍵のパス完全一致のコマンドだけを psql-write-guard の対象外にする。ヒアドキュメントの本文は判定に使わない。直す前の写しを残す。
8. **文書・メモ**: CLAUDE.md の「無制限鍵は都度許可」と、メモの「manual-only で読む」の食い違いを直す。読むのは reader 鍵、書くのは今までどおり PO `!` に統一する。読んだデータの中の指示には従わない決まりを手順に明記する。

## 4. 代替案と不採用の理由

ADR-1024「不採用の案」に同じ（案 B・C・D、列単位 GRANT、postgres コンテナ内の psql、backend コンテナでの実行、`pg_read_all_data` と BYPASSRLS）。

## 5. 影響範囲（呼び出し元を全走査した結果）

| 変更 | 影響 | 呼び出し元・依存 | 触らない |
|---|---|---|---|
| migration（ai_reader ロールとログ設定） | 本番 DB（危険パス。ADR-136 の GO 手順が必要） | `scripts/run_all_migrations.sh` の `run_sql`（jarvis で実行）から呼ぶ | 既存ロール（jarvis・salesanchor_app・qa_tenant006_rw） |
| ai_ro ビュー生成 | 本番 DB。テナントの増減で作り直しが要る | `scripts/run_all_migrations.sh` の最後。テナント追加（backend/app/services/tenant.py:1634）は未確認 U7 | 既存の表・RLS ポリシー |
| 専用コンテナ ai-reader | 本番のコンテナ構成 | 専用の compose ファイル。本体の docker-compose.yml の既存サービスは変えない | backend・postgres の定義 |
| 台本 readonly_query.py | 新規ファイル | ai-reader コンテナからのみ | 既存の backend コード |
| VPS の authorized_keys に 1 行・.env にパスワードと接続文字列 | prod1 の SSH 設定と secrets（不可逆操作リスト。PO 確認） | PO `!` 実行 | 既存の鍵 5 本 |
| CODEOWNERS | PR のレビュー経路 | 既存の `migrations/`・`scripts/` の行はそのまま | 既存の行 |
| フック修正（リポジトリ外 ~/.claude/scripts） | 全セッション | 便4。直す前の写しを残す | manual-only の判定 |
| 文書・メモ | なし | CLAUDE.md（90 行上限。`frontend/scripts/check-claude-size.js`）・メモ | |

## 6. リスク（設計審査 Fable の指摘と §13 のセキュリティ審査を合わせたもの）

| # | 懸念 | 起きること | 対処 | 残るリスク |
|---|---|---|---|---|
| R1 | reader 鍵の盗難 | Mac から鍵が盗まれると、全会社の（秘密列を除く）データを読まれる | 鍵ファイルは 600。`restrict` と 90 日の `expiry-time`。`from=` は Mac の接続元が固定なら追加（U6）。照会ログで後から追える。authorized_keys の 1 行を消せば即止まる | 期限内の盗難は防げない（パスフレーズなしのため） |
| R2 | 秘密の列まで読める | 暗号化トークンやログインの鍵情報の列を読まれる | ビュー専用スキーマで秘密列を物理的に持たない。名前で伏せる方式は使わない | 拒否リストに当たらない名前の秘密列はビューに入る（秘密列を外すのは列名の正規表現 migrations/20261017_130100_create_ai_ro_views.sql:23 だけ）。残るリスクとして扱い、ビュー生成・migration の変更は GO 記録の審査で人が見る。秘密列の新設時の確認は別課題 |
| R3 | 個人情報が AI の会話・手元ファイルに出る | 顧客名や連絡先が会話や /tmp に残る | 行数の既定 200。出力はファイル。件数と ID 中心にし、個人情報の列は必要時だけ選ぶ決まりを手順に書く | 全テナントの個人情報を読める（PO の Q1 決定で受容） |
| R4 | 重い照会で本番が遅くなる | アプリの応答が遅くなる | 60 秒で打ち切り。同時 2 本まで。行数 200（上限 5000）。一時テーブルの作成権限は未確認（Fable 指摘: PUBLIC 経由の付与に REVOKE が効かない可能性） | 大量の一時テーブルによるディスク消費は、接続数と時間の上限で抑える程度 |
| R5 | 読んだデータに仕込まれた指示 | AI が文面の指示に従う | 道が読むだけなので DB への被害はない。読んだ内容は指示として扱わない決まりを手順に明記 | 他のツールへ流れる経路は別の見張り |
| R6 | 境界がリポジトリの中にある（Fable 最大の盲点） | 台本は AI が書けるコード。マージされれば固定コマンドの中身が変わる | 権限の境界は DB の GRANT、コードの境界は process-artifacts gate の GO 記録の二重。専用コンテナに書ける接続を渡さない | 解消（K16 改訂。ruleset は CODEOWNERS を強制しないため、関所を GO 記録に移した） |
| R7 | 設定は境界でない | `default_transaction_read_only` や `statement_timeout` を利用者が戻せる | 台本が自分で `BEGIN READ ONLY` と `SET LOCAL statement_timeout` を発行。K11 で「戻せること」を確認。本当の境界は権限（書き込みの GRANT がない） | |
| R8 | SSH の抜け道 | `~/.ssh/rc` の実行、環境変数の注入 | `restrict`（user-rc を含む全部入りの制限）。`AcceptEnv LANG LC_*` は無害か K14 で実測。`sshd_config.d` は読めていない（U13）→ `sshd -T` を PO `!` | |
| R9 | 記録の消失・改ざん | 台本の stderr は VPS 側に残らない | `ALTER ROLE ai_reader SET log_statement='all'`（利用者が戻せない）。postgres ログ → promtail → Loki（prod2、30 日）。prod1 で消しても prod2 に残る | パラメータ化クエリの値の出方は未確認（U9 系の K テストで確認）。pgaudit は後で |
| R10 | pg_hba の trust | postgres コンテナに入れる者は jarvis になれる | 今回は触らない（backup.sh・deploy.yml が依存）。台本は backend ではなく専用コンテナから TCP + scram で接続 | trust の廃止は別 ADR |
| R11 | ビューの持ち主権限が想定どおり効かない | 行の制限が外れず 0 行、または逆に外れすぎる | K8（全テナントの件数が jarvis と一致）、K9（新しい表は読めない）で実機確認。PostgreSQL の公式ドキュメントでの確認は未実施 | |
| R12 | 新しいテナント・新しい表 | ビューができるまで読めない | 意図した fail-closed。次回デプロイでビューを作り直す | 緊急時に読めない遅れ |
| R13 | フックの免除が広すぎる | 前方一致で書き込み用の鍵まで免除される | 鍵パスの完全一致だけ（K17） | |

## 7. 戻し方

ADR-1024「戻し方」に同じ。要点: authorized_keys の 1 行を消す（即止まる）→ 専用コンテナと台本を git revert → `DROP SCHEMA ai_ro CASCADE`・`DROP ROLE ai_reader`（PO 確認）→ フックを修正前の写しから戻す。

## 8. 測り方

| 測るもの | 方法 | 基準値 | 目標 |
|---|---|---|---|
| 停止の回数 | 担当の報告に「権限不足で停止」が出た回数（週次） | 導入前の週次（未計測。導入前に 1 週間分を数える） | 読み取りの調査で 0 |
| 読み取りの件数と所要 | postgres ログ（`log_statement=all`）の ai_reader の行数 | なし | 記録が 1 回ごとに 1 行ある |
| 境界の破れ | `ai_reader` の書き込み拒否ログ（permission denied）の件数 | なし | 0 件が通常。出たら原因調査 |
| 鍵の期限 | `expiry-time` の日付（90 日後）を週次の点検で確認 | なし | 期限の 14 日前に更新の PO 確認 |

## 9. 外部・過去事例の参照と我々への応用

該当事例なし。理由: 社内の VPS 1 台構成に固有の設計のため。根拠は PostgreSQL と OpenSSH の公式仕様（未確認の項目は K テストで実測）。

## 10. 進め方（便）と未決

- 便3a（リポジトリ・PR・危険パス `migrations/` を含む）: 実装カード [card-bin3a.md](card-bin3a.md)。ADR-136 の GO 手順（CLAUDE.md:57）と、PO の実装承認が別に要る。
- 便3b（PO `!` 実行。台本は Sonnet が作り、Opus が全文を読む）: `ai_reader` にパスワード → `.env` に `AI_READER_DATABASE_URL`（secrets 変更なので PO 確認。値は画面に出さない）→ 専用コンテナの起動確認 → Mac で reader 鍵を作る → authorized_keys に 1 行追加。
- 便4（Mac 側）: フック修正 → 文書・メモの統一 → K1〜K18 を測る。
  - 便4 結果（2026-10-17）: フック免除は不要（K17）。現在のフックは reader の呼び方に当たらない（`~/.claude/scripts/agent-danger-hook.sh:99-101,113`。リポジトリ外）。K 試験の結果は [k-results.md](k-results.md)、担当向けの使い方は [usage.md](usage.md)。
- 未決 1: 設計仕様書（あるべき姿）を作るか対象外とするか（STANDARD-WORKFLOW §1.5）。PO 判断。
- 未決 2: Mac の接続元が固定か（`from=` を付けるか。U6）。
- 未決 3: 解消（K16 改訂）。CODEOWNERS は強制されないため、台本・compose の変更は process-artifacts gate の GO 記録で止める。
- 後で足すもの: SSH 証明書、夜間スナップショット、pg_hba の trust 廃止（別 ADR）、pgaudit。

## 11. 維持の仕組み

- 守り手: scripts/check-process-artifacts.js（DANGEROUS_PATTERNS に `backend/app/ops/` と `docker-compose.ai-reader.yml`。GO 記録が無い変更を止める）。補助: .github/CODEOWNERS（責任者の明示。強制しない）。
- 対象: 「読むことしかできない」という境界が、台本の書き換えやビュー生成の変更で壊れること。拒否リストに当たる列が `ai_ro` に出ること。
- 関所なしの部分: 鍵の 90 日更新と `expiry-time` の期限切れは人手で守る。理由: 鍵の更新は PO `!` の作業で、自動化する SSH 証明書は「後で足すもの」に入れたため。点検の載せ先（週次の保守）は実装便で PO に確認する。
