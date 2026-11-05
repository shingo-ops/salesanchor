# design: 試験 3 本の片付けを public の札の中へ

- recon: `docs/handoff/test-drop-public-lock/recon.md`
- 前の便: `docs/handoff/test-roles-ddl-scope/design.md` §11（同じ形の直し）
- 関係 ADR: ADR-034（全テナントへ移行を回す決まり。試験の片付けの札だけを直し、ADR は変えない）。新しい ADR は作らない（recon「既存 ADR・仕様の検索」）
- PO の承認: 「1」（2026-11-06・次は残りの3つの試験を直す）、「PRマージ、デプロイまで完走させてくれ」

## 1. 目的
CI の試験は 1 つの DB を並んで使う。片付けの DROP や public 表の DELETE が public の札の外にあると、同時に動く準備とぶつかって、たまたま落ちる。前の便で roles 試験だけ直した。残りの 3 本も同じ形に揃える。

## 2. 対象と対象外
- 対象: `backend/tests/test_rls_auth_audit.py`・`backend/tests/test_discord_oauth_rls.py`・`backend/tests/test_permission_resolution_pg.py` の 3 本だけ
- 対象外: `backend/app/`・`migrations/`・`.github/`・`backend/tests/rls_bootstrap.py`・他の試験。確かめ（assert）の中身。`backend/tests/test_rls_tenant_meta_config.py` と `backend/tests/test_countries_master.py` の 998/999 の重なり（次の便）。見張りが scoped 試験の schema_name を見ていない点（次の便）

## 3. 変更前と変更後

### 3-1. `backend/tests/test_rls_auth_audit.py`
- 前: `:68` tenant の札の中で、`:70`・`:81` の `_remove_test_tenant_rows(conn)` を public の札の外で流す
- 後: `:22` の import に `public_bootstrap_lock` を足す。`:69-70` と `:80-81` を次の形にする（2 か所とも同じ）
```python
        async with public_bootstrap_lock(admin_engine):
            async with admin_engine.begin() as conn:
                await _remove_test_tenant_rows(conn)
```
- 札の順: tenant（`:68`）→ public。逆にならない

### 3-2. `backend/tests/test_discord_oauth_rls.py`
- 前: 準備も片付けも札が無い
- 後:
  - import に `from tests.rls_bootstrap import public_bootstrap_lock` を足す
  - `_bootstrap_minimal_schema` の中の `async with admin_engine.begin() as conn:`（`:40`）を `async with public_bootstrap_lock(admin_engine):` で包む（中身は 1 段下げるだけ）
  - 片付けを関数 `_drop_minimal_schema(admin_engine)` にまとめる。2 つの finally（`:154-161`・`:209-216`）はこれを呼ぶ
```python
async def _drop_minimal_schema(admin_engine) -> None:
    """試験用のスキーマと public.tenants の行を、public の札の中で消す。"""
    async with public_bootstrap_lock(admin_engine):
        async with admin_engine.begin() as conn:
            await conn.execute(text(f"DROP SCHEMA IF EXISTS {_SCHEMA} CASCADE"))
            await conn.execute(
                text("DELETE FROM public.tenants WHERE id = :tid"),
                {"tid": _TENANT_ID},
            )
```
- tenant の札は足さない。理由: テナント 99 を使うのはこのファイルだけで、`--dist=loadfile` で同じワーカーが順に流す（recon 対象 2）。public の札だけを取る形は、tenant → public の順に反しない

### 3-3. `backend/tests/test_permission_resolution_pg.py`
- 前: `:37` テナント 998。`:98-99` の片付けは public の札の外。`:237-242` の finally は両方の札の外
- 後:
  - `:37` を `_TENANT_ID = 994` にする。`:57` の説明文の「id 998」を「id 994」にする（他の 998 を使う試験と重ならない番号。recon「テナント 998 の重なり」）
  - `:98-99` を public の札の中へ:
```python
            async with public_bootstrap_lock(admin_engine):
                async with admin_engine.begin() as conn:
                    await _remove_test_tenant_rows(conn)
```
  - `:237-242` の finally を、tenant の札 → public の札の順で取り直す形にする（本体の字下げは変えない）:
```python
    finally:
        async with tenant_schema_lock(admin_engine, _TENANT_ID):
            async with public_bootstrap_lock(admin_engine):
                async with admin_engine.begin() as conn:
                    await _remove_test_tenant_rows(conn)
                    for key in inserted_keys:  # この試験が入れたキーだけを消す（元からあるキーは消さない）
                        await conn.execute(text("DELETE FROM public.permissions WHERE key = :k"), {"k": key})
        await admin_engine.dispose()
```
- `:96` の外側の札の中で `:101` の public の札を取る形は、元のまま

## 4. 影響範囲
- 変わるのは試験の準備と片付けの札だけ。アプリの動き・本番・DB の形は変わらない
- 札を待つ時間が少し増える。public の札は短い処理だけを包む

## 5. 代替案
- A（採用）: 前の便と同じく、片付けを public の札の中へ入れる。形が揃い、見る所が少ない
- B: `backend/tests/rls_bootstrap.py` に片付け用の共通関数を作る。3 本の消す行が違う（tenant_settings・permissions の有無）ので、今は共通化しない
- C: 試験を直列で流す。CI が遅くなる

## 6. リスクと対処
- 札の順を逆にするとデッドロックが増える → 3 本とも tenant → public か public だけ。審査で確かめる
- 998 → 994 で試験の意味が変わる → 番号は試験が自分で作るテナントの名前で、確かめの中身には出ない（`_TENANT_ID` を通して使う）

## 7. 受入条件
| 基準 | 検証方法 |
|---|---|
| 変更は 3 ファイル（＋この docs）だけ | `git diff --stat origin/main...HEAD` |
| 3 本の DROP SCHEMA がすべて `public_bootstrap_lock` の中 | 差分を目で読む（審査役） |
| 札の順に public → tenant が無い | 差分を目で読む（審査役） |
| CI の pytest-run-internal で failed 0 | `gh run view` のログの最後の行 |
| DB ログの `deadlock detected` 0 件 | CI の DB ログを grep |
| DB の ERROR の種類が main の通った回と同じ（FATAL 3 種の件数の揺れは除く） | DB の ERROR の種類を数える台本（Opus の作業場所）で比べる |
| passed＋skipped の数が main と同じ | ログの最後の行 |
| `grep -rn "tenant_998\|_TENANT_ID = 998" backend/tests/test_permission_resolution_pg.py` が 0 件 | grep |

## 8. 外部・過去事例の参照と我々への応用
- PostgreSQL の公式文書（Explicit Locking・Advisory Locks）: デッドロックを避けるには、すべての処理が同じ順で鍵を取る。ここでの「tenant → public」がこれに当たる。数値の事例は使わない。この直しの効果は、この CI の DB ログ（deadlock 件数）で直接測るため

## 9. 維持の仕組み
- 守り手: CI の pytest（必須チェック・毎回走る）と、2026-11-19 の数え直しをする Opus
- 前の便の分類表の見張り（`backend/tests/test_tenant_loop_migration_guard.py`）は移行の範囲を見る。札の外の DROP は見ていない。見張りを足すかは、次の便で数え直しの結果（2026-11-19）を見て決める

## 10. 設計審査（同じ AI による自己審査）
- 判定: APPROVE
- 根拠: 変更前の行はすべて recon の file:line と一致。札の順は 3 本とも tenant → public か public だけ。受入条件はすべて CI のログか grep で ○× が決まる
- 未解決: なし（998/999 の残りの重なりと見張りの強化は次の便として明記）
