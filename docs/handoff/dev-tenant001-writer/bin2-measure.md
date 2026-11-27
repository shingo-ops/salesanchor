# 便2 測定結果（生の値）

> 測った日: 2026-11-27。測った場所: このクラウドの中に立てた使い捨ての PostgreSQL 16（localhost・本番ではない）。
> 測った試験: `backend/tests/ops/test_ai_dev001_writer_db.py`（`-s` の標準出力を写した）。20 件すべて通った。単体試験 `test_dev001_write.py` 41 件も通った。
> tenant_001・tenant_004 は `backend/tests/rls_bootstrap.py` の `bootstrap_tenant_schema`（`app/services/tenant.py` の `create_tenant_schema`）で作った。
> この DB の tenant_001 は本番とは表の数が違う（下の「本番との違い」）。本番の数は migration 適用の直前に reader 鍵で数え直す（design §6 K5）。

## 規則 E（public に何も付けずに外部キーのある表へ足せるか）

- `companies`（`status` が `public.customer_statuses` を外部キーで指す）への INSERT（先に `leads` に 1 行）: **成功**（`RULE_E companies INSERT ... -> OK`）。
- 同じ transaction で public に付けた権限: 0。public の全表について `has_table_privilege('ai_dev001_writer', oid, 種類)` が true の数:
  SELECT 0 / INSERT 0 / UPDATE 0 / DELETE 0 / TRUNCATE 0 / REFERENCES 0 / TRIGGER 0。
- `has_schema_privilege('ai_dev001_writer','public','USAGE')` は true（PUBLIC から受け継ぐ。design §3-3 のとおり）。
- 結論: public の権限は 0 のままでよい。migration に public の GRANT は無い。

## 規則 B の表への INSERT（秘密でない列だけを列に挙げ、値はすべて DEFAULT）

| 表 | 秘密の列 | 秘密でない列の数 | 結果の SQLSTATE |
|---|---|---|---|
| bots | api_key_hash | 13 | 23502 |
| discord_channel_webhooks | webhook_token_encrypted | 5 | 23502 |
| staff | avatar_token | 18 | 23502 |
| tenant_invoice_payment_bank | bank_account_number | 11 | 23502 |
| tenant_invoice_payment_wise | iban | 12 | 23502 |

- 5 表とも権限エラー（42501）ではなく NOT NULL 違反（23502）。値を全部 DEFAULT にしたため、秘密の列以外の必須列でも止まる。どの列で止まったかは測っていない（未確認）。
- 秘密の列だけを挙げた INSERT は 5 表とも 42501（権限エラー）。
- `tcg_distribution_targets` はこの試験の DB に無い（本番の 6 表目。本番では migration 適用後に reader 鍵で数える）。

## K1〜K3（この DB）

- K1: `leads` への INSERT・`UPDATE ... SET`・DELETE が成功（同じ transaction）。
- K2: tenant_004 の `leads` への INSERT・UPDATE・DELETE は 3 件とも SQLSTATE 42501。
- K3(a): `public.tenants` と `tenant_001.tenant_meta_config` への INSERT・UPDATE・DELETE 6 件とも 42501。
- K3(b): `staff.avatar_token` の UPDATE と `DELETE FROM staff RETURNING *` は 2 件とも 42501。
- K3(c): `has_schema_privilege(..,'public','CREATE')`・`has_database_privilege(..,current_database(),'CREATE')`・`has_schema_privilege(..,'tenant_001','CREATE')` はすべて false。
- K3(d): SECURITY DEFINER で戻り値が trigger でない関数のうち、実行できる物: `[]`（0 個）。

## K5（aclexplode。grantor は migration を流したロール 1 人）

| 項目 | 測った行数 | 期待（表の実数から別に数えた） |
|---|---|---|
| (i) `pg_namespace.nspacl` | `[('tenant_001','USAGE')]` の 1 行 | 1 行 |
| (ii) `pg_class.relacl`（r・p） | 293 行・表 77 | 通常の表 72×4＋秘密の列を持つ表 5×DELETE＝293・表 72+5＝77 |
| (iii) `pg_attribute.attacl` | 177 行 | 5 表の秘密でない列 59×3＝177 |
| (iv) 連番 `relacl`（S） | 65 行（USAGE のみ） | tenant_001 の連番 65 |
| (v) tenant_001 以外 | 0 行（表・列・スキーマ） | 0 行 |

- `tenant_meta_config` は (ii)(iii) とも 0 行。秘密の 5 列は (iii) に 0 行。

## 本番との違い・未確認

- この DB の tenant_001 は 78 表（`tenant_meta_config` を含む）。本番は 112 表（design §3-2）。表が違うので数も違う（本番の期待は 426・207・74 等。design §6 K5）。本番の数は適用の直前に数え直して PR に書く。
- 本番での適用・K6（Loki の記録 14 本）・K7・K8 は測っていない（便3・便4）。
- 台本の終了コードは、環境変数が未設定のとき 6 とした（設計に指定が無い。3 は「成功したが AUDIT を送れず rollback」、5 は「拒否・DB エラーで AUDIT を送れない」に使うため）。
- migration を適用した DB での二重適用（冪等）・tenant_001 が無い DB での何もしない動作・ロールの属性が違うときの停止は試験で確認した。
- 手元の Python 3.13 の pytest は依存が無く動かなかったため、`/usr/bin/python3.12` の venv（作業場所の外）で動かした。`psql` を Bash に書いて見張りに止められた（使い捨ての DB を立てる手順で。その操作は使わず、クラスタの起動と pytest だけにした）。
