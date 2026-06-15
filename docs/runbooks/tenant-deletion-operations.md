# テナント削除 運用 Runbook

対象API実装: `backend/app/routers/super_admin_tenants.py`  
監査ログ: `public.tenant_deletion_audit`  
実装根拠: PR #2149 / PR #2154 / PR #2159  
関連設計: `docs/handoff/tenant-deletion-cache-fix/recon.md`, `docs/handoff/tenant-deletion-cache-fix/design.md`

---

## 1. 用語

| 用語 | 説明 |
|------|------|
| **論理削除** | `public.tenants.is_active = false` にしてログイン / API利用を止める。データは残る。通常の利用停止はこれ。 |
| **物理削除** | `DROP SCHEMA CASCADE` で tenant schema を削除し、`public.tenants` からも行を削除する。基本的に戻せない。 |

---

## 2. 通常運用

**契約停止・未払い・休止・誤操作防止はすべて論理削除で対応する。**

物理削除は通常運用では使わない。

```
論理削除 API: DELETE /api/v1/super-admin/tenants/{tenant_id}
Body: { "confirm": "DELETE:<tenant_code>" }
```

論理削除後の動作:
- 対象テナントのユーザーは次回リクエスト時に HTTP 403 が返る（キャッシュ無効化により即時）
- データは `tenant_{NNN}` schema に残る
- `public.tenant_deletion_audit` に `mode='logical'` / `status='succeeded'` が記録される

---

## 3. 物理削除を検討してよい条件

以下のいずれかに該当し、かつ PO が対象 tenant_id を明示して承認した場合のみ。

- テストテナントを完全に消す必要がある
- 顧客から完全削除依頼がある
- 法務・契約上の保持期間終了後の削除義務がある

---

## 4. 物理削除 実行前チェックリスト

以下が**すべて**揃わない限り実行禁止。

- [ ] 対象 `tenant_id` が確定している
- [ ] 削除理由が文書化されている
- [ ] 対象テナントが**論理削除済み**（`is_active = false`）であること
- [ ] バックアップが**成功**していること（ファイルパス確認済み）
- [ ] PO 個別 GO が発行されていること（§6 書式参照）

---

## 5. バックアップ手順

```bash
bash scripts/backup_tenant_before_drop.sh <tenant_id>
```

実行後、バックアップファイルが生成されていることを確認する。  
ファイルパスを §6 の PO GO 書式に記載する。

---

## 6. PO GO の書式

物理削除を承認する際、PO は以下の形式で GitHub PR コメントまたは Slack に記録する。

```
GO: tenant_id=<ID> の物理削除を承認します。
バックアップ: <backup file path>
理由: <削除理由>
日時: <YYYY-MM-DD HH:mm JST>
承認者: Shingo
```

---

## 7. 物理削除 実行

PO GO 確認後、以下のAPIを実行する。

```
物理削除 API: DELETE /api/v1/super-admin/tenants/{tenant_id}/physical
Body: { "confirm": "DELETE:<tenant_code>" }
```

> **注意**: このAPIは論理削除済みテナントにのみ実行できる。`is_active = true` のテナントには 400 が返る。

---

## 8. 実行後確認

物理削除完了後、以下をすべて確認する。

```sql
-- 1. 監査ログ確認
SELECT * FROM public.tenant_deletion_audit
WHERE tenant_id = <ID> AND mode = 'physical';
-- status = 'succeeded' であること

-- 2. schema が存在しないこと
SELECT schema_name FROM information_schema.schemata
WHERE schema_name = 'tenant_<NNN>';
-- 0件であること

-- 3. public.tenants から削除されていること
SELECT * FROM public.tenants WHERE id = <ID>;
-- 0件であること
```

確認後、実行した事実を active-work.md または該当運用ログに記録する。

---

## 9. 禁止事項

- PO 個別 GO なしに物理削除APIを実行しない
- バックアップなしに実行しない
- tenant_id が曖昧な状態（コードのみ、口頭確認のみ等）で実行しない
- 通常の利用停止目的で物理削除を使わない

---

## 10. 現在の状態（2026-06-14 時点）

- **物理削除APIは本番未実行**
- 実行した tenant_id は存在しない
- 物理削除が必要になった場合は本 Runbook §3〜§8 に従って個別対応する
