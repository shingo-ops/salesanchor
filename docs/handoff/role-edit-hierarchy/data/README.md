# ロール画面の編集の決まり: 一度きりのデータ SQL（本 PR では実行しない）

設計: `docs/handoff/role-edit-hierarchy/design.md` §5。前例: `docs/handoff/roles-system-key-data/`（形を写した）。ADR-155 により `migrations/` には何も足さない。

## やること（7 + 6）

| 会社 | ロール名 | id | 入れる system_key | 消す保存行（roles.view） |
|---|---|---|---|---|
| t001 | マネージャー | 2536 | manager | 1 |
| t003 | マネージャー | 2536 | manager | 1 |
| t004 | マネージャー | 2514 | manager | 1 |
| t005 | マネージャー | 2514 | manager | 1 |
| t006 | マネージャー | 3 | manager | 1 |
| t001 | 点検用（見るだけ） | 2611 | inspector | 1 |
| t004 | スモーク専用 | 2589 | smoke | 0 |

id は recon（2026-11-08 読み取り）の値。実行時に読み直し、名前・id・tenant_id・`system_key IS NULL` がすべて 1 件で一致しなければ全体を止める。保存済みの roles.* の行数も、表の想定（roles.view だけ）と違えば止める。

## 手順

1. `precheck.sql`（読み取りのみ）
2. `dryrun.sql`（apply と同じ中身。最後に ROLLBACK）
3. `apply.sql`（1 トランザクション・lock_timeout 10s・COMMIT・audit_log に会社ごと 1 行。消した行の鍵も audit_log に残る）
4. `postcheck.sql`（読み取りのみ。system_key 合計 17 = オーナー・システム管理者 10 + 7）
5. 戻し: `rollback.sql`（新たな PO の判断が必要。audit_log の記録から system_key を空に戻し、消した roles.view を戻す）

## 順番（重要）

**データ SQL を先に入れ、そのあとでコードを反映する。** 値が先なら古いコードには影響しない。コードが先だと、値が入るまでマネージャーは「その他」扱いでロール画面を失う。

## 実行の条件

- 本番への適用は手元で PO の GO の後（クラウドでは流さない）。
- 本 PR の作成時点では **未実行**。実行記録（時刻・sha256・件数）は実行した時にこの README の末尾へ追記する。

## 実行記録

（未実行）
