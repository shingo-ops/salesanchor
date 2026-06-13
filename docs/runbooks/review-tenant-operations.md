# review-tenant-operations Runbook (ADR-028)

`tenant-review` (`review@salesanchor.jp`) の運用手順。  
Meta App Review 撮影・QA Smoke 用テナントの日常管理、パスワード管理、セットアップ再実行。

---

## 1. テナント概要

| 項目 | 値 |
|------|----|
| tenant_code | `tenant-review` |
| tenant_id | 6 |
| schema | `tenant_006` |
| email | `review@salesanchor.jp` |
| 用途 | Meta App Review 撮影 / QA Smoke Suite |
| Demo データ | `scripts/qa/seed-tenant.sql` で管理 |

---

## 2. 通常セットアップ（テナント・ユーザー確認、パスワード変更なし）

```bash
# VPS で実行
docker compose exec \
  -e ALLOW_REVIEW_TENANT_SETUP=1 \
  backend python /app/scripts/setup_review_tenant.py
```

**動作**: テナント・スキーマ・staff レコードの冪等チェック・作成のみ。  
Firebase パスワードは**変更しない**。既存ログイン情報をそのまま使える。

---

## 3. パスワードリセット（明示許可が必要）

パスワードを変更する場合は `ALLOW_REVIEW_TENANT_PASSWORD_RESET=1` が必須。

```bash
# VPS で実行
docker compose exec \
  -e ALLOW_REVIEW_TENANT_SETUP=1 \
  -e ALLOW_REVIEW_TENANT_PASSWORD_RESET=1 \
  backend python /app/scripts/setup_review_tenant.py
```

**実行後**:

```bash
# 結果ファイルの取り出し（VPS で実行）
docker compose exec -T backend cat /tmp/review_tenant_setup_*.txt
```

> **注意**: `/tmp` はコンテナ再起動で消えます。取り出したらすぐに保存すること。

---

## 4. パスワードの Shingo への安全な共有方法

1. 結果ファイルを取り出す（上記手順 3）
2. **許可された手段のみ**: Claude Code ターミナル（ローカルセッション）または直接口頭
3. **禁止**:
   - ChatGPT へのペースト
   - PR 本文・GitHub コメントへの記載
   - Slack / Discord への平文送信
   - メールへの添付

---

## 5. /tmp の揮発性について

コンテナ内 `/tmp` は再起動で消える（tmpfs）。  
`review_tenant_setup_*.txt` をホスト側に保存する場合:

```bash
# VPS での実行例（ファイルをホスト上に書き出す）
docker compose exec -T backend cat /tmp/review_tenant_setup_*.txt > ~/review_setup_$(date +%Y%m%d).txt
chmod 600 ~/review_setup_$(date +%Y%m%d).txt
```

---

## 6. Demo データのシード（QA Smoke Suite）

`setup_review_tenant.py` は Demo データシードを行わない（ADR-089: customers テーブル廃止済み）。  
Demo companies が必要な場合は QA Smoke Suite のシードを使う:

```bash
# VPS で実行（QA Smoke Suite のセットアップ）
bash scripts/qa/reset-tenant.sh
```

詳細: `docs/runbooks/qa-smoke-operations.md`

---

## 7. ログイン確認

```
URL      : https://app.salesanchor.jp/
email    : review@salesanchor.jp
password : （直前のパスワードリセット結果ファイルを参照、または Shingo に確認）
```

---

## 8. トラブルシューティング

### ログインできない

1. Firebase Console で `review@salesanchor.jp` の disabled 状態を確認
2. `public.users` の `is_active` を確認:
   ```sql
   SELECT id, tenant_id, is_active FROM public.users WHERE email = 'review@salesanchor.jp';
   ```
3. パスワードが不明な場合は手順 3（パスワードリセット）を実行

### セットアップスクリプトがクラッシュした場合

- `customers` テーブルへの参照: ADR-089 対応済み（v2 以降は発生しない）
- `password_hash` 列への参照: ADR-138 対応済み（v2 以降は発生しない）
- Firebase 認証エラー: `/app/firebase-credentials.json` の存在を確認

---

## 9. 変更履歴

| 日付 | 内容 |
|------|------|
| 2026-06-14 | 初版作成（ADR-089/ADR-138 対応、パスワード保護ルール追加） |
