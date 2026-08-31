# discord-lead-invite recon — Card #7

作業ブランチ: `release/oauth-state-extra`
対象SHA: `e0d3a0b90efed0f4255c9742b92399aa08bfabc5`（NEWSHA = origin/main）

---

## 変更対象ファイル

| ファイル | 変更種別 | 目的 |
|---------|---------|------|
| `backend/app/services/oauth_state.py` | 修正 | `issue_state` に `extra: dict | None = None` 追加 |
| `backend/tests/test_oauth_state_extra.py` | 新規 | extra パラメータの単体テスト（6ケース） |

---

## `oauth_state.py` 変更前後

### 変更前（シグネチャ）

```python
async def issue_state(
    tenant_id: int,
    staff_id: int,
    *,
    ttl_seconds: int = _DEFAULT_TTL_SECONDS,
) -> dict[str, object]:
```

### 変更後（シグネチャ）

```python
async def issue_state(
    tenant_id: int,
    staff_id: int,
    *,
    ttl_seconds: int = _DEFAULT_TTL_SECONDS,
    extra: dict | None = None,
) -> dict[str, object]:
```

### 追加ロジック（payload 構築後）

```python
if extra:
    _RESERVED = {"tenant_id", "staff_id", "created_at", "nonce"}
    conflicts = _RESERVED & extra.keys()
    if conflicts:
        raise ValueError(f"extra のキーが予約済みキーと衝突します: {conflicts}")
    payload.update(extra)
```

---

## 既存呼び出し元（影響なし）

- `backend/app/routers/discord_oauth.py:113-115` — `extra` 未指定のまま継続
- `backend/app/routers/meta_inbox.py:314-316` — `extra` 未指定のまま継続

---

## テスト結果サマリ

| suite | 件数 | 結果 |
|-------|------|------|
| test_oauth_state.py | 14 | PASS |
| test_oauth_state_extra.py | 6 | PASS |
| test_discord_oauth.py | 9 | PASS |
| test_meta_oauth_endpoints.py | 21 | PASS |
| test_502_paths.py | 3 | PASS |

---

## 次カードへの申し送り

Card #5（`discord_lead_invite` ルーター実装）では以下の呼び出しパターンが使用可能:

```python
await oauth_state.issue_state(
    tenant_id=tenant_id,
    staff_id=current_user.id,
    extra={"lead_id": lead.id},
)
```

`consume_state` の戻り値 dict に `lead_id` が含まれる（Fernet 暗号化/復号で往復確認済み）。
