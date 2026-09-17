# 実DBの読み取り確認項目

親: [DB設計のSSOT化](../../specs/db-ssot/README.md)
設計: [design-status.md](design-status.md)

目的: ソースにある定義を実DBの事実と混同せず、スタッフ・利用者・ロールの移行対象を確定する。これは読み取りの準備文書であり、SQLは未実行。製品・DB変更の許可書ではない。

## 現在の接続確認

2026-09-10、`docs/runbooks/funnel-pr1-deploy.md`に記載のSSH接続先・鍵・ディレクトリを使い、非対話・既知ホスト確認必須・接続待ち8秒で稼働状況取得を試した。

- 指定鍵`/Users/tanizawashingo/.ssh/id_ed25519`は存在しないという警告。
- 接続の終了コードは0だが、要求したcomposeのJSON一覧ではなく、コンテナのCPU/メモリ・free・df・uptimeの監視情報が返った。
- 終了0を要求コマンド実行成功と扱わない。DB名・実スキーマ・対象テナントのデータは未確認。
- `docs/runbooks/claude-monitor-access.md`には監視情報を返す専用アクセスの記載があるが、今回の応答がどの設定で制限されたかは未特定。別の鍵・アカウントを試して制限を回避しない。
- 必要な外部情報: Sales Anchorの実DBに対して、以下の読み取りを行える既存の接続方法または承認済みの取得手順。監視専用アクセスの権限変更を要求するものではない。

## 第1段階：接続先と構造

対象環境の正式な読み取り経路で、読み取り専用セッションと短い実行時間制限を設定して実施する。接続方法が未確認なので実行コマンドは確定していない。

```sql
SELECT current_database() AS database_name,
       current_user AS database_role,
       current_setting('server_version') AS server_version,
       current_setting('transaction_read_only') AS transaction_read_only;
```

次に、必要なテーブルだけの列を取得する。個人名・メール・認証情報の値は取得しない。

```sql
SELECT table_schema, table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE (table_schema = 'public' AND table_name = 'users')
   OR (table_schema ~ '^tenant_[0-9]+$'
       AND table_name IN ('staff', 'roles', 'role_permissions', 'user_roles'))
ORDER BY table_schema, table_name, ordinal_position;
```

制約を確認する。カタログはアプリ利用者の参照範囲制御が機能する証明にはならない。

```sql
SELECT n.nspname AS schema_name, t.relname AS table_name,
       c.conname AS constraint_name, c.contype AS constraint_type,
       pg_get_constraintdef(c.oid) AS definition
FROM pg_constraint c
JOIN pg_class t ON t.oid = c.conrelid
JOIN pg_namespace n ON n.oid = t.relnamespace
WHERE (n.nspname = 'public' AND t.relname = 'users')
   OR (n.nspname ~ '^tenant_[0-9]+$'
       AND t.relname IN ('staff', 'roles', 'role_permissions', 'user_roles'))
ORDER BY n.nspname, t.relname, c.conname;
```

合格条件: 環境・DB・対象テナントを正式な運用情報と照合できること。列・制約が取得できたこと。返却0行をテーブル不存在と断定せず、読み取りロールの可視範囲を確認すること。表の不存在・列差異があれば、次段のSQLをソース定義から推測して実行しない。

## 第2段階：ID対応と実効権限

第1段階の実物に合わせてSQLを確定するため、この時点では未作成。対象は正式に確認されたテナントに絞り、氏名・メール・トークンを返さない。

取得項目: テナントID、staffのIDと接続user_id、Userの所属・利用可否、旧staff.role_id、user_rolesの割当集合、ロールごとの権限キー集合、admin互換動作の有無。M1〜M6の件数だけでなく該当する対象IDを記録する。

M1〜M6の規則は設計文書を参照する。実効権限はUserの直接role='admin'等の互換処理まで含めて評価する。読み取り結果だけを移行承認としない。

## 未完了と停止条件

現時点は第1段階の接続方法確認待ち。実DBの件数・スキーマ・分類を確認済みとはしない。認証失敗・監視情報への置換・参照権限不足・環境不一致があれば当該DB調査を止め、既存の読み取り経路を確認する。製品コード・DB・外部認証・権限を変更しない。
