# 実装カード 便1 — ログイン自社化の置き場（migration・構造のみ）

> この文書は何か：ADR-1013（ログイン自社化とパスキー）の便1 として、データベースに列と表を足すだけの作業の指示書です。アプリの動きは変えません。

- 設計: docs/handoff/auth-self-hosted-passkey/design.md §2・§6 便1
- 対象ADR: ADR-1013（本テーマ）・ADR-1007（migration は構造のみ・1 回実行）・ADR-1008（人の正本＝public.users.id）・ADR-136（危険PRのGO）
- 危険便: はい（`migrations/`・`scripts/run_all_migrations.sh` を含む）。GO は「POの委任に基づくClaude Opus発行」（PO 2026-10-13 チャットの一任）
- 担当: 実装 Sonnet／コード審査 Fable／GO・マージ Opus

## 1. 目的

public.users に 4 列、public に新表 3 つを足す。値は入れない。既存の画面・API・ログインは何も変わらない。

## 2. 前提の事実（調査 2026-10-13・origin/main 基準）

| # | 事実 | 出典 |
|---|---|---|
| F1 | 本番は毎デプロイ、登録済み migration を先頭から全件やり直す | `scripts/run_all_migrations.sh` 冒頭コメント・`.github/workflows/deploy.yml` の「Run database migrations」 |
| F2 | 409 行目で `ALTER TABLE public.users DROP COLUMN IF EXISTS password_hash;` が毎回走る | `scripts/run_all_migrations.sh:409`・`migrations/20260612_150000_drop_password_hash.sql` |
| F3 | よって列名 `password_hash` は使えない（毎デプロイ消える）。列名は `password_argon2_hash` にする | F1・F2 |
| F4 | 登録は `scripts/run_all_migrations.sh` の末尾に、コメント 1 行＋`run_sql migrations/<file>.sql` 1 行 | 同ファイル末尾の実例 |
| F5 | 命名は `YYYYMMDD_HHMMSS_説明.sql`。刻印の重複は CI が拒否。`20261013_150000` は PR #4217 が使用中 | `.github/workflows/migration-guard.yml`（チェック5） |
| F6 | `REFERENCES public.X` の X は許可リストにある表だけ。users は載っている | `.github/workflows/migration-guard.yml`（チェック4） |
| F7 | public 新表への GRANT は `salesanchor_app` が存在するときだけ行う書き方が慣例 | `migrations/20261010_120000_create_analysis_soldout_extra_targets.sql` |
| F8 | public.users には RLS が無い（ログイン時はテナントが決まる前に引くため） | `git grep` で users の POLICY 無し |
| F9 | `backend/app/models.py` に `Column(` を足すと、`.github/workflows/migration-guard.yml` チェック1 が deploy.yml の追記を求める。便1 ではモデルを触らない | 同ワークフロー チェック1 |

## 3. 触るファイル（これ以外は触らない）

1. 新設 `migrations/20261013_160000_add_self_hosted_auth_tables.sql`（刻印が main または開いている PR と重なったら、`20261013_16xx00` の空いている値に変え、報告する）
2. `scripts/run_all_migrations.sh` の末尾に 2 行追記
3. 本便の PR を起票する前に、設計者が docs-only PR（#4225）で次を main にマージしておく: (a) `docs/adr/ADR-1012-self-hosted-auth-and-passkey.md` を `docs/adr/ADR-1013-self-hosted-auth-and-passkey.md` に改名し本文の ADR-1012 を ADR-1013 に置換、`node scripts/generate-adr-index.js` で README.md 再生成 (b) design.md の対象ADR と新しい列の `password_hash` を `password_argon2_hash` に置換し、§2 に「password_hash は `scripts/run_all_migrations.sh:409` が毎デプロイ `migrations/20260612_150000_drop_password_hash.sql` を再実行するため使わない」を追記 (c) recon.md に F1・F2 を `scripts/run_all_migrations.sh:409` の file:line で追記。実装担当は docs-only PR のマージを確認してから release ブランチを `origin/main` から切る（実装担当は recon・design を触らない）

触らない: `backend/`（models.py・conftest.py を含む）・`frontend/`・`.github/`・`docker-compose.yml`・既存の migration ファイル（とくに `migrations/20260612_150000_drop_password_hash.sql` は変更しない）

## 4. migration の中身（この SQL をそのまま使う。変えたい点があれば変えずに報告）

```sql
-- ADR-1013 便1: ログイン自社化の置き場（構造のみ・冪等・値は入れない）
-- 列名 password_argon2_hash: password_hash は 20260612_150000_drop_password_hash.sql が毎デプロイ消すため使わない
-- RLS は付けない: public.users と同じく、テナントが決まる前（ログイン時）に引くため
-- ロールバック: 列と表は残してコードが使わない（削除は別便・PO GO）

ALTER TABLE public.users ADD COLUMN IF NOT EXISTS password_argon2_hash TEXT NULL;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMPTZ NULL;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS failed_login_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ NULL;

COMMENT ON COLUMN public.users.password_argon2_hash IS 'Argon2id のハッシュ文字列。NULL はパスワード未設定（ADR-1013）';
COMMENT ON COLUMN public.users.password_changed_at IS '最後にパスワードを変えた時刻。これより前に発行したトークンを拒否する基準（ADR-1013）';
COMMENT ON COLUMN public.users.failed_login_count IS '連続したログイン失敗の回数。成功で 0（ADR-1013）';
COMMENT ON COLUMN public.users.locked_until IS 'ログイン停止の期限。NULL か過去なら停止なし（ADR-1013）';

CREATE TABLE IF NOT EXISTS public.webauthn_credentials (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    credential_id BYTEA NOT NULL,
    public_key BYTEA NOT NULL,
    sign_count BIGINT NOT NULL DEFAULT 0,
    transports TEXT[] NOT NULL DEFAULT '{}',
    backup_eligible BOOLEAN NOT NULL DEFAULT FALSE,
    backup_state BOOLEAN NOT NULL DEFAULT FALSE,
    aaguid UUID NULL,
    label TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at TIMESTAMPTZ NULL,
    CONSTRAINT uq_webauthn_credentials_credential_id UNIQUE (credential_id),
    CONSTRAINT ck_webauthn_credentials_credential_id_len CHECK (octet_length(credential_id) BETWEEN 1 AND 1023),
    CONSTRAINT ck_webauthn_credentials_sign_count CHECK (sign_count >= 0)
);
CREATE INDEX IF NOT EXISTS ix_webauthn_credentials_user_id ON public.webauthn_credentials (user_id);
COMMENT ON TABLE public.webauthn_credentials IS 'パスキーの公開鍵（顔・指紋そのものは端末から出ない）。ADR-1013';
COMMENT ON COLUMN public.webauthn_credentials.user_id IS '人の正本 public.users.id';
COMMENT ON COLUMN public.webauthn_credentials.credential_id IS '認証器が作ったパスキーの ID（W3C は 1023 バイト以下）';
COMMENT ON COLUMN public.webauthn_credentials.public_key IS 'COSE 形式の公開鍵';
COMMENT ON COLUMN public.webauthn_credentials.sign_count IS '署名回数。同期型パスキーは 0 のまま';
COMMENT ON COLUMN public.webauthn_credentials.transports IS '端末との通信方法（usb・nfc・ble・internal・hybrid）';
COMMENT ON COLUMN public.webauthn_credentials.backup_eligible IS 'バックアップ可能なパスキーか';
COMMENT ON COLUMN public.webauthn_credentials.backup_state IS 'いまバックアップされているか';
COMMENT ON COLUMN public.webauthn_credentials.aaguid IS '認証器の種類を表す ID';
COMMENT ON COLUMN public.webauthn_credentials.label IS '利用者が付ける名前';
COMMENT ON COLUMN public.webauthn_credentials.created_at IS '登録した時刻';
COMMENT ON COLUMN public.webauthn_credentials.last_used_at IS '最後にログインに使った時刻';

CREATE TABLE IF NOT EXISTS public.password_reset_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    purpose TEXT NOT NULL,
    token_hash BYTEA NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_password_reset_tokens_token_hash UNIQUE (token_hash),
    CONSTRAINT ck_password_reset_tokens_purpose CHECK (purpose IN ('reset', 'invite')),
    CONSTRAINT ck_password_reset_tokens_token_hash_len CHECK (octet_length(token_hash) = 32)
);
CREATE INDEX IF NOT EXISTS ix_password_reset_tokens_user_id ON public.password_reset_tokens (user_id);
COMMENT ON TABLE public.password_reset_tokens IS '再設定リンク（reset・30分）と初回設定リンク（invite・72時間）の使い捨て鍵。ハッシュだけ保存。ADR-1013';
COMMENT ON COLUMN public.password_reset_tokens.user_id IS '人の正本 public.users.id';
COMMENT ON COLUMN public.password_reset_tokens.purpose IS 'reset＝再設定／invite＝新規ユーザーの初回設定';
COMMENT ON COLUMN public.password_reset_tokens.token_hash IS '鍵の sha256（32 バイト）。鍵そのものは保存しない';
COMMENT ON COLUMN public.password_reset_tokens.expires_at IS '期限';
COMMENT ON COLUMN public.password_reset_tokens.used_at IS '使った時刻。NULL は未使用';
COMMENT ON COLUMN public.password_reset_tokens.created_at IS '作った時刻';

CREATE TABLE IF NOT EXISTS public.auth_refresh_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    token_hash BYTEA NOT NULL,
    family_id UUID NOT NULL,
    family_created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at TIMESTAMPTZ NULL,
    user_agent_hash BYTEA NULL,
    CONSTRAINT uq_auth_refresh_tokens_token_hash UNIQUE (token_hash),
    CONSTRAINT ck_auth_refresh_tokens_token_hash_len CHECK (octet_length(token_hash) = 32)
);
CREATE INDEX IF NOT EXISTS ix_auth_refresh_tokens_user_id ON public.auth_refresh_tokens (user_id);
CREATE INDEX IF NOT EXISTS ix_auth_refresh_tokens_family_id ON public.auth_refresh_tokens (family_id);
COMMENT ON TABLE public.auth_refresh_tokens IS 'ログイン継続用の更新トークン。ハッシュだけ保存。使うたびに入れ替え、使い回しを検知したら family ごと失効。ADR-1013';
COMMENT ON COLUMN public.auth_refresh_tokens.user_id IS '人の正本 public.users.id';
COMMENT ON COLUMN public.auth_refresh_tokens.token_hash IS 'トークンの sha256（32 バイト）';
COMMENT ON COLUMN public.auth_refresh_tokens.family_id IS '最初のログインから入れ替わった一連のトークンの組 ID';
COMMENT ON COLUMN public.auth_refresh_tokens.family_created_at IS '組の作成時刻。期限はここから絶対 30 日';
COMMENT ON COLUMN public.auth_refresh_tokens.expires_at IS '期限';
COMMENT ON COLUMN public.auth_refresh_tokens.revoked_at IS '失効した時刻。NULL は有効';
COMMENT ON COLUMN public.auth_refresh_tokens.created_at IS '作った時刻';
COMMENT ON COLUMN public.auth_refresh_tokens.last_used_at IS '最後に使った時刻';
COMMENT ON COLUMN public.auth_refresh_tokens.user_agent_hash IS 'ブラウザ情報の sha256。記録と検知だけに使い、拒否には使わない';

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE ON public.webauthn_credentials, public.password_reset_tokens, public.auth_refresh_tokens TO salesanchor_app;
        GRANT USAGE, SELECT ON SEQUENCE public.webauthn_credentials_id_seq, public.password_reset_tokens_id_seq, public.auth_refresh_tokens_id_seq TO salesanchor_app;
    END IF;
END $$;
```

`scripts/run_all_migrations.sh` の末尾に追記する 2 行:

```
# ログイン自社化の置き場（users に 4 列・新表 3 つ。構造のみ・冪等。ADR-1013 便1）
run_sql migrations/20261013_160000_add_self_hosted_auth_tables.sql
```

## 5. 分岐ごとの対処

| 起きたこと | 対処 |
|---|---|
| main の `scripts/run_all_migrations.sh` 末尾が #4217 などで変わり衝突 | 両方の行を残す（順序は main の行の後に本便の行）。それ以外の衝突は止まって報告 |
| CI「マイグレーションSQL 実行（内部）」が users 以外の表が無いと言う | 止まって報告（`.github/` は触らない） |
| migration-guard のチェック4（REFERENCES の許可リスト）で落ちる | 止まって報告 |
| 刻印 `20261013_160000` が使われている | 空いている `20261013_16xx00` に変えて報告 |
| フックに止められた | 言い換えて再試行せず止まって報告 |

- 将来の便で新表 3 つを別の migration から `REFERENCES` する場合は、`.github/workflows/migration-guard.yml` チェック4 の許可リストへの追加が要る（本便は users だけを参照するので不要。Fable 審査 LOW-2）。
- 設計審査: Fable 2026-10-13 REVISE（限定）→ HIGH-1・MEDIUM-1 を指定文どおり反映済み（再審査不要の判定）。

## 6. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 変更ファイルは §3 の 2 つ（＋設計者の docs）だけ | `git diff origin/main --name-only` |
| PostgreSQL 16 で 2 回実行してもエラー 0 | CI「マイグレーションSQL 実行（内部）」の step『変更 SQL を 1回目実行』『変更 SQL を 2回目実行（冪等性テスト）』が緑。`gh run view <run-id> --log --job <job-id>` でその 2 step の生ログを PR コメントに貼る。ローカル実行はしない（Docker 停止・psql 書き込みはフックが止める） |
| 本番の既存の値に触れない（INSERT・UPDATE・DELETE・DROP が 0 行） | `grep -inE '^\s*(insert|update|delete|drop)' migrations/20261013_160000_add_self_hosted_auth_tables.sql` が 0 件 |
| CI の必須チェックが全部緑 | `gh pr checks <PR>` |
| 本番に反映された | デプロイ後、deploy の実行ログで本 migration の行が `ALTER TABLE`・`CREATE TABLE` 等で終わり ERROR が無い。かつ本番 DB の `information_schema.columns` で users の 4 列、`information_schema.tables` で新表 3 つを確認（読み取りのみ） |
| 今のログインに影響なし | デプロイ後に `https://app.salesanchor.jp/` と `https://api.salesanchor.jp/` の応答（HTTP 状態）がデプロイ前と同じ |

## 7. PR

- タイトル: `feat: add self-hosted auth tables (ADR-1013 stage 1)`
- `### 標準ワークフロー確認` に recon・design・ADR-1013・本カードのパス
- `### GO記録` は GO 発行後に設計者が転記する（実装担当は書かない）
- Draft にしない。マージは設計者が行う
