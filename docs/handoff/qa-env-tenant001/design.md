# QA環境（tenant_001）設計 — 第1段

- **テーマ**: QA-02（tenant_001 を画面から触れるようにする）
- **区分**: 既存の延長・修正（STANDARD-WORKFLOW §1.8）／新規設計仕様書は作らない
- **置き場所**: `docs/handoff/qa-env-tenant001/design.md`
- **起点 SHA**: `367ace2b0febb16430aaffffbc110d4f92165494`
- **作成日**: 2026-09-06

---

## 0. この文書の根拠と、根拠のないもの

### 実測で確認済みの事実（カード QA-02-RECON-02 / 03 の生出力）

| # | 事実 | 出所 |
|---|------|------|
| 1 | `tenant_001` のテーブルは **97本**（`tenant_004` は114本）。`tcg_products` `tcg_suppliers` `analysis_results` `extraction_items` `extraction_jobs` `source_messages` `unparsed_lines` が実在 | recon02 STEP 2 |
| 2 | `tenant_001.tcg_suppliers` は3件（`SP9001` `SP9002` `SP9003`・全て `is_active = t`） | recon02 STEP 3 |
| 3 | ログイン可能ロールは3つ：`jarvis`（超ユーザー）／`qa_tenant006_rw`／`salesanchor_app` | recon02 STEP 4-2 |
| 4 | `salesanchor_app` は `tenant_001` と `tenant_004` の**両方に USAGE あり・CREATE なし** | recon02 STEP 4-3 |
| 5 | nginx はホストの `nginx/nginx.conf` **1ファイル**を `/etc/nginx/conf.d/default.conf` に read-only bind mount。`conf.d/` に追加ファイルは置けない | recon02 STEP 5-1 / STEP 7-2 |
| 6 | 現行 `nginx/nginx.conf` は **477行**、server ブロックは5ドメイン分（`jarvis-claude.uk` / `app.salesanchor.jp` / `api.salesanchor.jp` / `monitor.salesanchor.jp` / `salesanchor.jp`） | recon03 STEP 1 / STEP 2 |
| 7 | certbot はコンテナ常駐。`certbot renew` を12時間ごとに実行。`./certbot/conf` を rw マウント | recon02 STEP 6-1 / STEP 7-1 |
| 8 | 証明書は5ドメイン分が `live/` に実在（`app` `api` `monitor` `salesanchor.jp` `jarvis-claude.uk`） | recon02 STEP 6-3代替 |
| 9 | `deploy.yml` は `nginx/**` または `docker-compose.yml` の変更を検出すると nginx を `--force-recreate` する（ADR-137） | recon03 STEP 6 |
| 10 | `app.salesanchor.jp` ブロックは ADR-133 により変数化済み：`resolver 127.0.0.11 valid=5s;` `set $backend backend;` `set $frontend frontend;` | recon03 STEP 2（`nginx.conf:101-103`） |
| 11 | `TCG_SCHEMA` は `backend/app/tcg_config.py:20` で `os.getenv("TCG_SCHEMA", "tenant_004")`。19本のサービスが import | recon01 STEP 7 |
| 12 | `scripts/blue-green-cutover.sh:130` は `--env TCG_SCHEMA="${TCG_SCHEMA:-tenant_004}"` を既に渡している | recon01 STEP 4 |
| 13 | `qa_tenant006_rw` は `migrations/` `scripts/` `docs/` の**どこにも定義がない**（git grep が空） | recon03 STEP 7-2 / 7-3 |

### まだ確認していないこと（この design の未確定部分）

以下は**推定で埋めていない**。着手前に確認する手順を §5 に置く。

- **F-3**: DNS の管理先（お名前.com / Cloudflare / さくら等）。**PO 回答待ち**
- **F-4**: `qa_tenant006_rw` が誰にいつ作られたか。git に記録がないため追跡不能。

### 確認済みに変わったもの（カード QA-02-RECON-04・2026-09-06）

| # | 事実 | 出所 |
|---|------|------|
| 14 | 認証は `signInWithEmailAndPassword` のみ。ポップアップ・リダイレクトを使わない。**アクセス元ドメインの承認済み登録に依存しない**（F-1 解決：`qa.salesanchor.jp` の Firebase 側追加は不要） | recon04 STEP 2（`AuthContext.tsx:64`） |
| 15 | `authDomain` は `VITE_FIREBASE_AUTH_DOMAIN` から取り、`frontend/Dockerfile:8,12` で**ビルド時に焼き込まれる**。変更には再ビルドが要る | recon04 STEP 3（`docs/ENVIRONMENT_VARIABLES.md:66`） |
| 16 | backend は `public` を広範に読み書きする（`public.users` `public.permissions` `public.tenant_features` `public.tenants` 等）。**認証の入口から使われる**（F-2 解決：`public` 権限は必須） | recon04 STEP 4 / STEP 5 |
| 17 | `salesanchor_app` の migration は `GRANT CONNECT ON DATABASE jarvis_db` と `ALTER DEFAULT PRIVILEGES FOR ROLE jarvis IN SCHEMA public` を含む（テーブルの所有者が `jarvis` のため `FOR ROLE` が必要） | recon04 STEP 6-2 |
| 18 | `migrations/20260906_120000_create_tcg_tables_t001.sql` が実在。冒頭に「TCG 27本を作成」「tenant_001 は既存（68テーブルあり）」と記載。68 + 27 = 95、実測97との差2はビュー（`v_company_stats` `v_senders`）と整合 | recon04 STEP 7 |

---

## 1. 到達形と、第1段の範囲

到達形は前ターンで合意した4原則（環境定義を1か所に集約＋DB権限で本番書き込みを機械的に禁止）。第1段では次の範囲に絞る。

| 原則 | 第1段での扱い |
|------|--------------|
| 1. 環境定義は1ファイルに1環境 | **適用する**。`config/environments/{prod,qa}.env` を新設し、QA はここからのみ値を引く |
| 2. nginx はテンプレ1枚を2回使う | **第2段に送る**。第1段では QA ブロックを追記する |
| 3. 起動台本は1本、引数が環境名 | **第2段に送る**。第1段では `scripts/qa-backend-up.sh` を別途置く |
| 4. DB権限で本番書き込みを禁止 | **適用する**。第1段の必須要件 |

原則2・3を第2段に送る理由は、**本番の入口と起動台本を書き換える作業を、QA 立ち上げと同じ日に混ぜない**ため。混ぜると障害時に切り分けができない。第2段の受入基準は §7 に明記する。

---

## 2. 構成（第1段の到達状態）

```
app.salesanchor.jp → nginx（server_name で振り分け） → $backend    → 本番backend（TCG_SCHEMA=tenant_004・salesanchor_app）
qa.salesanchor.jp  → nginx（server_name で振り分け） → $qa_backend → QA backend （TCG_SCHEMA=tenant_001・qa_tenant001_rw）
```

frontend は本番と共用する。`frontend/src/lib/api.ts:28` が `const API_BASE = "/api/v1"` の相対パスであるため（recon01 STEP 8）、配信されたドメインの `/api/v1` を呼ぶ。**frontend の再ビルドは不要**。

**ただし共用が成立する条件が1つある。** `VITE_FIREBASE_AUTH_DOMAIN` はビルド時に焼き込まれるため（事実15）、QA と本番で認証ドメインを分けたくなった時点で、共用は成立しなくなる。今回は両者とも `auth.salesanchor.jp`（ADR-032）で同一のため共用できる。**無条件に共用できるわけではない**ことを、将来 QA の認証を分離したくなった場合の注意として記録しておく。

---

## 3. 【最重要】PR を2本に分ける理由

### 分けないと本番が全滅する

nginx は `ssl_certificate` が指すファイルが存在しない場合、**設定読み込みに失敗して起動できない**。`deploy.yml` は `nginx/**` の変更を検出すると `--force-recreate` する（事実9）ため、証明書を取得する前に HTTPS ブロックを入れた PR をマージすると、次の流れになる。

1. nginx コンテナが削除される
2. 新コンテナが `qa.salesanchor.jp` の証明書を読もうとする
3. ファイルが無いため起動失敗
4. **`app` `api` `monitor` `salesanchor.jp` `jarvis-claude.uk` の全5ドメインが落ちる**

`nginx -t` は事前に構文検査できるが、これは**ホスト側では実行されない**。`deploy.yml` の該当ステップ（recon03 STEP 6・`Recreate nginx`）に `nginx -t` は無く、いきなり `docker compose up -d --no-deps --force-recreate nginx` を叩く。

### したがって順序を固定する

| PR | 内容 | 前提 | 危険度 |
|----|------|------|--------|
| PR-1 | `qa.salesanchor.jp` の **HTTP(:80) ブロックのみ**追加。`/.well-known/acme-challenge/` を `/var/www/certbot` に向ける。HTTPS ブロックは書かない | DNS が引けること | 中 |
| （手作業） | certbot で証明書を新規取得 | PR-1 反映済み | 中 |
| PR-2 | `qa.salesanchor.jp` の **HTTPS(:443) ブロック**追加 | `live/qa.salesanchor.jp/fullchain.pem` が実在すること | 高 |

PR-1 と PR-2 の間に証明書取得を挟むこと。**この順序は省略できない。**

---

## 4. 変更の中身

### 4-1. 環境定義ファイル（新規）

`config/environments/qa.env`

```
ENV_NAME=qa
HOSTNAME=qa.salesanchor.jp
BACKEND_CONTAINER=astro-webapp-backend-qa
NETWORK_ALIAS=qa-backend
TCG_SCHEMA=tenant_001
DB_ROLE=qa_tenant001_rw
```

`config/environments/prod.env`（現状を書き写すのみ・参照はまだしない）

```
ENV_NAME=prod
HOSTNAME=app.salesanchor.jp
BACKEND_CONTAINER=astro-webapp-backend
NETWORK_ALIAS=backend
TCG_SCHEMA=tenant_004
DB_ROLE=salesanchor_app
```

パスワードは書かない。`.env` から引く。

### 4-2. nginx（PR-1：HTTP のみ）

`nginx/nginx.conf` の末尾に追記する。既存の5ドメインのブロックには**1行も触れない**。

```nginx
# ============================================================
# QA環境: qa.salesanchor.jp（tenant_001）
# PR-1: 証明書取得のための HTTP ブロックのみ。HTTPS は PR-2 で追加する。
# ============================================================
server {
    listen 80;
    listen [::]:80;
    server_name qa.salesanchor.jp;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 200 "qa: certificate pending\n";
        add_header Content-Type text/plain;
    }
}
```

`return 301 https://...` にしない。証明書が無い状態でリダイレクトすると接続エラーになり、取得作業の確認が難しくなるため。

### 4-3. nginx（PR-2：HTTPS）

`app.salesanchor.jp` のブロック（`nginx.conf:76-243`）を土台にする。**変える点は3つだけ**。

| 箇所 | 本番 | QA |
|------|------|-----|
| `server_name` | `app.salesanchor.jp` | `qa.salesanchor.jp` |
| `ssl_certificate` / `_key` | `live/app.salesanchor.jp/` | `live/qa.salesanchor.jp/` |
| backend 変数 | `set $backend backend;` | `set $backend qa-backend;` |

`set $frontend frontend;` は本番と同じ（frontend 共用）。`resolver 127.0.0.11 valid=5s;` も同じ。

**持ち込まないもの**（QA には不要かつ危険）:

- `location /grafana/` `location /status/`（外部IP `49.212.160.98` 向け・監視系）
- `location = /metrics`（`allow 49.212.160.98` の監視専用）
- `location /design/` と `location = /design`（ADR-134 の設計図書サイト。htpasswd が無いと 500 を返す fail-closed 構造のため、持ち込むと QA で意図しない500が出る）

**持ち込むもの**: `/api/v1/auth/`、SSE 2本（`= /api/v1/conversations/stream`、`= /api/v1/leads/stream`）、`/api/`、`location /`。セキュリティヘッダーとレート制限は本番と同一にする。

PR-1 で入れた HTTP ブロックの `location /` は、PR-2 で `return 301 https://$host$request_uri;` に置き換える。

### 4-4. DB ロール（migration）

`migrations/<日時>_create_qa_tenant001_role.sql`

設計方針：**`tenant_004` への権限を一切与えない**。QA backend が設定ミスで本番スキーマを掴んだ場合、書き込めずエラーで止まる。これが原則4 の実体。

```sql
-- QA用ロール。tenant_001 のみ読み書き可。tenant_004 には一切の権限を与えない。
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qa_tenant001_rw') THEN
    CREATE ROLE qa_tenant001_rw LOGIN PASSWORD :'qa_password';
  END IF;
END
$$;

GRANT CONNECT ON DATABASE jarvis_db TO qa_tenant001_rw;

-- public スキーマ: 認証・権限判定・テナント解決に必須（事実16）
-- 本番と共用のため分離できない（§4-4「残存リスク」参照）
GRANT USAGE ON SCHEMA public TO qa_tenant001_rw;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO qa_tenant001_rw;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO qa_tenant001_rw;
ALTER DEFAULT PRIVILEGES FOR ROLE jarvis IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO qa_tenant001_rw;
ALTER DEFAULT PRIVILEGES FOR ROLE jarvis IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO qa_tenant001_rw;

-- tenant_001 スキーマ
GRANT USAGE ON SCHEMA tenant_001 TO qa_tenant001_rw;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA tenant_001 TO qa_tenant001_rw;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA tenant_001 TO qa_tenant001_rw;
ALTER DEFAULT PRIVILEGES FOR ROLE jarvis IN SCHEMA tenant_001
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO qa_tenant001_rw;
ALTER DEFAULT PRIVILEGES FOR ROLE jarvis IN SCHEMA tenant_001
  GRANT USAGE, SELECT ON SEQUENCES TO qa_tenant001_rw;

-- tenant_004 には GRANT を書かない（既定で権限なし）
```

`ALTER DEFAULT PRIVILEGES` に `FOR ROLE jarvis` を必ず付ける。テーブルの所有者が `jarvis` であるため、これを省くと将来作られるテーブルに権限が付かない（`salesanchor_app` の migration がこの形を採っている・事実17）。

#### 残存リスク：`public` は本番と共用される

原則4 が守れるのは **`tenant_004` だけ**である。`public` スキーマは本番・QA の両方が同じものを使い、分離できない（事実16：認証・権限判定・テナント解決が `public` に依存するため、権限を落とすと QA でログインできない）。

したがって次のリスクが残る。

- QA での操作が `public.users` `public.tenants` 等を書き換えた場合、**本番にも反映される**
- 具体的には、QA でユーザーを作る・権限を変える・テナント設定を触る操作は本番に影響する

第1段では**運用上の申し合わせ**で対処する（QA で `public` 配下を書き換える操作をしない）。機械的な保証は第1段の範囲外とし、§7 の第2段以降で「`public` のうち QA が書いてよいテーブルを絞る」を検討課題として送る。この制約を知らずに QA を使うと事故になるため、QA 環境の利用開始時に周知すること。

migration には**テーブル全体の件数一致チェックを書かない**（本テーマの既知の落とし穴）。検算は「`qa_tenant001_rw` が `tenant_004` に対して `has_schema_privilege` = false であること」を確認する形にする。

### 4-5. QA backend の起動

`scripts/qa-backend-up.sh`（新規・`blue-green-cutover.sh` は変更しない）

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source config/environments/qa.env

docker rm -f "${BACKEND_CONTAINER}" 2>/dev/null || true

docker run -d \
  --name "${BACKEND_CONTAINER}" \
  --env-file .env \
  --env TCG_SCHEMA="${TCG_SCHEMA}" \
  --env DATABASE_URL="${QA_DATABASE_URL}" \
  --restart unless-stopped \
  <その他は blue-green-cutover.sh の docker run と同一>

docker network connect --alias "${NETWORK_ALIAS}" astro-webapp_frontnet "${BACKEND_CONTAINER}"
```

`--env-file .env` を先に置き、`TCG_SCHEMA` と `DATABASE_URL` を**後から上書き**する順序が重要。逆にすると本番の値が勝つ。

`QA_DATABASE_URL` は `.env` に追加する（`qa_tenant001_rw` の接続文字列）。git には入れない。

---

## 5. 実施手順（危険度つき）

| # | 手順 | 実施者 | 危険度 | 前提 |
|---|------|--------|--------|------|
| 0-a | ~~F-1（Firebase 承認済みドメイン）~~ | — | — | **完了**（不要と確定） |
| 0-b | ~~F-2（`public` 参照）~~ | — | — | **完了**（必須と確定） |
| 0-c | F-3（DNS 管理先）を回答 | PO | 低 | **未** |
| 1 | `qa.salesanchor.jp` の A レコードを `49.212.137.46` に登録 | **PO** | 低 | 0-c |
| 2 | `dig qa.salesanchor.jp` で引けることを確認 | 実装役 | 低 | 1 |
| 3 | PR-1（nginx HTTP ブロック）を作成・PO の GO でマージ | 実装役 | 中 | 2 |
| 4 | **`app.salesanchor.jp` の疎通確認**（最優先） | 実装役 | — | 3 |
| 5 | certbot `--dry-run` で1回試す | 実装役 | 低 | 4 |
| 6 | certbot 本番取得 | 実装役 | 中 | 5 が成功 |
| 7 | DB ロール migration の PR を作成・GO でマージ | 実装役 | 中 | — |
| 8 | PR-2（nginx HTTPS ブロック）を作成・GO でマージ | 実装役 | **高** | 6 |
| 9 | **`app.salesanchor.jp` の疎通確認**（最優先） | 実装役 | — | 8 |
| 10 | QA backend 起動 | 実装役 | 中 | 7・9 |
| 11 | `qa.salesanchor.jp` の疎通確認 | 実装役 | 低 | 10 |

**手順4 と手順9 を飛ばさない。** QA を作るために本番を止めては本末転倒。

### certbot の実行方法

renew は常駐コンテナが担うが、**新規取得は別に1回叩く**。

```bash
docker compose run --rm certbot certonly --webroot -w /var/www/certbot -d qa.salesanchor.jp --dry-run
```

`--dry-run` が成功してから `--dry-run` を外す。Let's Encrypt のレート制限（同一ドメインへの失敗にも上限がある）を踏まないため、この2段階を守る。取得後の更新は常駐 certbot が自動で拾う（追加設定不要）。

---

## 6. 受入基準（第1段）

| # | 基準 | 測り方 |
|---|------|--------|
| 1 | PR-1・PR-2 の diff が**追加行のみ**で、既存5ドメインのブロックに変更行が0であること | `git diff` の `-` 行が空（コメント除く） |
| 2 | PR-1 マージ後、`app` `api` `monitor` `salesanchor.jp` の4ドメインが応答すること | 各 URL への HTTP ステータス（200 または 301） |
| 3 | `live/qa.salesanchor.jp/fullchain.pem` が実在すること | `ls` の出力 |
| 4 | PR-2 マージ後、基準2 が再度成立すること | 同上 |
| 5 | `qa_tenant001_rw` が `tenant_004` に対して権限を持たないこと | `has_schema_privilege('qa_tenant001_rw','tenant_004','USAGE')` = `false` |
| 5-b | `qa_tenant001_rw` が `tenant_001` と `public` に USAGE を持つこと | `has_schema_privilege` = `true` を両方で確認 |
| 5-c | QA でログインできること（`public` 権限が足りているかの実地確認） | QA 画面でログイン成功 |
| 6 | QA backend が `tenant_001` を見ていること | QA の API が返す仕入元が `SP9001` `SP9002` `SP9003` の3件であること |
| 7 | 本番 backend の `TCG_SCHEMA` が `tenant_004` のままであること | 本番コンテナの環境変数 |

### 切り戻し

nginx が原因で本番が落ちた場合、**その PR を revert して再デプロイ**の1手に固定する。手でサーバ上の `nginx.conf` を編集しない（ADR-137 の inode ズレにより、手編集は反映されないか、次のデプロイで巻き戻る）。

---

## 7. 第2段（原則2・3の完了）— 送り先

第1段の完了後に着手する。受入基準を先に決めておく。

| # | 基準 |
|---|------|
| 1 | `nginx/nginx.conf` が単一テンプレと `config/environments/*.env` から生成され、**生成物が現行ファイルと diff ゼロ**であること |
| 2 | `blue-green-cutover.sh` が環境名を引数に取り、`prod` 指定時の挙動が現行と同一であること |
| 3 | `backend/tcg_migration/scripts/dry_run_parity02_phase_e.py:74` の `TCG_SCHEMA = "tenant_004"` 直書きが解消されていること |
| 4 | `public` スキーマのうち QA が書き込んでよい範囲を絞る方針が決まっていること（第1段では運用申し合わせのみ） |

「いつかやる」で終わらせないため、第1段の完了報告に第2段の起票を含める。

---

## 8. 積み残し

- **F-4**: `qa_tenant006_rw` が git に定義なしのまま本番 DB に存在する。第1段の範囲外だが、由来不明のロインロールが残る状態は望ましくない。別テーマで棚卸しを起票する。
- 引き継ぎ資料の「TCG テーブル27本」は解決済み。migration の冒頭コメントに「TCG 27本を作成」「tenant_001 は既存（68テーブルあり）」とあり、68 + 27 = 95。実測97との差2はビュー2本（`v_company_stats` `v_senders`）で整合する。矛盾ではなかった。
- `docs/handoff/tcg-2026-09-05-summary/recon.md` は未読のまま。第1段の設計には不要と判断したが、必要が生じたら読む。
