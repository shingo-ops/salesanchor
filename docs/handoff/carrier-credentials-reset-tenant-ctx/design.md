# design: キャリア鍵保存後 reset_tenant_context 挿入（ADR-072 準拠）

## 参照

- recon: `docs/handoff/carrier-credentials-reset-tenant-ctx/recon.md`
- ADR-072: `docs/adr/ADR-072-reset-tenant-context-after-commit.md`

---

## KGI

`PUT /api/v1/integrations/carriers/fedex/credentials` が 500 を返さなくなる。
ガイド 1-7 と管理センター双方で sandbox/production いずれの鍵保存も成功し、
audit_logs に操作ログが記録される。

| 基準 | 検証方法 |
|---|---|
| ガイド 1-7 で sandbox 鍵保存 → 500 が出ない | 手動: ガイド 1-7 フォームで保存 → エラーなし |
| 保存後「接続OK」バッジが表示される | 手動: 同上 → CarrierCredentialForm の onSaved が呼ばれる |
| audit_logs に操作ログが記録される | DB確認: `SELECT * FROM tenant_006.audit_logs WHERE table_name='tenant_carrier_credentials' ORDER BY created_at DESC LIMIT 1;` |
| 管理センターからの保存も成功する | 手動: /management-center/integrations/fedex から保存 |
| lint / ruff エラーなし | CI: ADR-072 tenant schema lint |
| migration ゼロ | 検品 diff: `git diff --name-only origin/main...HEAD` に `.sql` がないこと |

---

## 外部・過去事例の参照と我々への応用

ADR-072 は本プロジェクト内で多発バグとして記録されている既知パターン。
`db.commit()` 後のコネクションプール切り替えで `app.tenant_id` が空文字になる
挙動は SQLAlchemy + asyncpg の組み合わせ固有の問題（SQLite テストでは再現しない）。
過去に同パターンで修正された実績のある write エンドポイントと同じ対処（`reset_tenant_context` 追加）を適用する。

---

## 設計詳細

### 変更内容（最小）

`backend/app/routers/integrations.py` の `save_carrier_credentials` ハンドラー内、
`save_credentials(...)` 呼び出し直後に `await reset_tenant_context(db, tenant_id)` を 1行追加。

```python
# 変更前
await carriers.save_credentials(...)
# NOTE: save_credentials は内部で db.commit() 済み
new_status = await carriers.get_status(...)

# 変更後
await carriers.save_credentials(...)
# NOTE: save_credentials は内部で db.commit() 済み（carrier_credentials.py:198）。
# ADR-072: 内部 commit 後にコネクションプールが別コネクションを払い出す可能性があるため
# app.tenant_id を再設定してから後続クエリ・audit_logs INSERT を実行する。
await reset_tenant_context(db, tenant_id)
new_status = await carriers.get_status(...)
```

### なぜ 1行で済むか

- `reset_tenant_context` は `set_tenant_context` の alias（同等処理）
- `save_credentials` を変更しない（サービス層は commit 後リセットしない設計のまま）
- ルーター側で「内部 commit を持つサービスを呼んだ直後に reset する」責務を持つ
  → 既存の他 write エンドポイントと同じパターン

### なぜ audit_logs RLS 修正（第2弾）と分けるか

- 第1弾: コード修正のみ（デプロイ即時反映・リスクゼロ・revert 容易）
- 第2弾: migration（全テナント対象・バックアップ必須・単独リリース）

第1弾で症状は完全に解消するため、第2弾は「フールプルーフ追加」として別スケジュール。

---

## 影響ファイル一覧

| ファイル | 変更種別 | 内容 |
|---|---|---|
| `backend/app/routers/integrations.py` | 修正 | `save_carrier_credentials` に `reset_tenant_context` 1行追加・コメント更新 |
| `docs/handoff/carrier-credentials-reset-tenant-ctx/recon.md` | 新規 | 調査成果物 |
| `docs/handoff/carrier-credentials-reset-tenant-ctx/design.md` | 新規 | 設計成果物 |

**触れないファイル**:
- `migrations/` — なし（コード修正のみ）
- `frontend/` — なし
- `.github/workflows/` — なし
- `backend/tests/` — 既存テストで回帰確認（新テスト不要: SQLite では非再現バグ）
