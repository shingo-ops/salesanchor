# SA-02 段階2 設計: meta_messages → conversation_logs 移行

> ADR-096 参照: conversation_logs を全会話ログの SSOT にする（SA-02 KGI G1）

## What（何をするか）

`meta_messages`（Messenger/Instagram/Discord 受信履歴 = 旧保存先）のデータを
`conversation_logs`（ADR-096 SSOT = 新保存先）にコピーする。

**移行後の状態**:
- `meta_messages`: 変更なし（並走期間は残す）
- `conversation_logs`: meta_messages 由来の行 + 手動記録（段階3）+ 新規受信（段階1）が混在

## Why（なぜ必要か）

- 段階1（PR #1932）で新規受信は `conversation_logs` に入るようになったが、**既存データ（highlife-jpn本番の蓄積分）は `meta_messages` に残っている**
- `v_company_stats` が `conversation_logs` を参照しているため、移行しないと `conversation_count=0` / `last_conversation_at=NULL` のまま
- G1「3ヶ月分の会話ログが conversation_logs に集約される」の実現に必須

## 設計決定

| 決定 | 内容 | 理由 |
|------|------|------|
| meta_messages は削除しない | コピーのみ | 安全なロールバックのため |
| 冪等性 | `external_message_id` UNIQUE + ON CONFLICT DO NOTHING | 再実行可能 |
| message_id なし行 | 合成キー `meta_legacy:{id}` | 古いレコードも移行できる |
| company_id 導出 | `companies WHERE lead_id = mm.lead_id` | leads に company_id 列なし（SSOT は companies.lead_id） |
| contact_id | NULL | meta_messages に contact 情報なし |
| is_manual | false | 自動取り込み行として区別 |

## 検証基準

| 基準 | 検証方法 |
|------|---------|
| coverage 100% | `verify_sa02_stage2_count_check.py` で gap=0 |
| ロールバック可能 | `is_manual=false AND external_message_id LIKE 'meta_legacy:%' OR IN (mm.message_id)` で特定・削除できる |
| 冪等 | 再実行後も件数が変わらない（ON CONFLICT DO NOTHING） |

## 外部・過去事例の参照と我々への応用

- **Stripe `charges` → `payment_intents`**: 旧テーブル削除せずコピー + IDマッピングで冪等性確保 → 我々も `meta_messages` を削除せず `conversation_logs` にコピーし、`external_message_id` UNIQUE で冪等にする（同一パターン）
- **GitHub issues → discussions**: 合成IDで重複防止 → 我々も `message_id=NULL` 行に `meta_legacy:{id}` 合成キーを採用（同一パターン）

> 参照: `docs/handoff/sa-02-stage2-migration/recon.md`

## 本番実行チェックリスト（Shingo GO後）

- [ ] VPS上で `--dry-run` を実行し件数を確認
- [ ] `--tenant-id 1`（テスト用テナント）で試し実行
- [ ] 検証スクリプトで確認
- [ ] 全テナントに本実行
- [ ] 検証スクリプトで coverage 100% を確認
- [ ] `v_company_stats` の conversation_count が 0 以外になっていることを会社詳細ページで確認

---

## バグ修正メモ（2026-06-15: asyncpg + SET LOCAL 非互換）

### 障害概要

R3 本移行（2026-06-15）実行時に `highlife-jpn`（tenant_id=4）の最初のバッチで以下のエラーが発生：

```
asyncpg.exceptions.PostgresSyntaxError: syntax error at or near "$1"
```

DB への INSERT は 0 件（エラーは最初の SET LOCAL 呼び出し時点で発生）。

### 根本原因

移行スクリプト内の `SET LOCAL app.tenant_id = :tid` において、asyncpg が `:tid` を
PostgreSQL の `$1` プレースホルダに変換するが、PostgreSQL の `SET` コマンドは
バインドパラメータを受け付けないため構文エラーが発生。

### 修正内容

`_set_tenant_context()` ヘルパーを追加し、`set_config()` SQL 関数経由で設定するよう変更：

```python
await conn.execute(
    text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
    {"tenant_id": str(int(tenant_id))},
)
```

`set_config()` は通常の SELECT 関数として扱われるためバインドパラメータが使える。
`is_local=true` を指定することで `SET LOCAL` 相当のトランザクションスコープを維持。

### dry-run 検証ギャップの修正

元の dry-run パスは `if total == 0 or dry_run: return` で早期リターンしていたため、
`SET LOCAL` のバグがステージング（dry-run）で検出されなかった。

修正後は dry-run でも `engine.begin()` → `_set_tenant_context()` 経路を通ることで
同バグを事前に検出できるようにした。
