# ADR-131: テナントコンテキスト 自動クリア（get_db finally ブロック）

**Status**: Accepted  
**日付**: 2026-06-10（起案: Hikky-dev / PO承認: shingo-ops）  
**関連**: ADR-072（reset_tenant_context ルール）、ADR-SA-18（salesanchor_app NOBYPASSRLS接続）

---

## 背景

SA-18 Phase2 以降、バックエンドは `salesanchor_app`（NOBYPASSRLS）でPostgreSQLに接続する。  
RLSポリシーは `current_setting('app.tenant_id', true)::INTEGER` を評価するため、  
セッションに `app.tenant_id` が正しく設定されていないとクエリが0件返却またはエラーになる。

### 問題: セッションレベル SET の汚染

`set_tenant_context()` は以下の3つを**セッションレベル**で設定する:

```sql
SET search_path = tenant_NNN, public
SET app.tenant_id = 'N'
SET app.is_operator = ''
```

PostgreSQL の `SET`（`SET LOCAL` でない）はトランザクション終了後も**セッションに残る**。  
SQLAlchemy のコネクションプール（`pool_size=20, max_overflow=10`）は接続を再利用するため、  
**前のリクエストのテナントコンテキストが次のリクエストに持ち越される**可能性がある。

### 既存の対策の不完全性

ADR-072 は `db.commit()` 直後に `reset_tenant_context(db, tenant_id)` を呼ぶことを定めた。  
しかし以下の問題がある:

1. **再設定であり、クリアではない** — `reset_tenant_context` の実装 (`dependencies.py:317-336`) は  
   `set_tenant_context(db, tenant_id)` を呼ぶだけで、既知の `tenant_id` で上書きする。  
   コンテキストを「空の安全な状態」に戻すものではない。

2. **例外パスで呼ばれない** — `db.commit()` が例外を投げた場合、以後の `reset_tenant_context` 呼び出しは  
   実行されない。コネクションが汚染された状態でプールに返却される。

3. **新規 router での漏れが多発** — recon（`docs/recon/recon-sa-foundation-full-audit-20260610.md`）で  
   25 router ファイルが `reset_tenant_context` 未呼び出しと判定された。ルール遵守はヒューマン依存で  
   構造的に担保されていない。

4. **`get_current_tenant` に finally がない** — `dependencies.py:160-207` の `get_current_tenant` は  
   `yield` / `finally` を使わない通常の関数であり、リクエスト終了時の自動クリーンアップがない。

---

## 決定

**`get_db` の `finally` ブロックで `clear_tenant_context()` を呼び、コネクション返却前に必ずコンテキストをクリアする。**

### 変更対象ファイル（3ファイル）

#### 1. `backend/app/auth/dependencies.py` — `clear_tenant_context` 追加

```python
async def clear_tenant_context(db: AsyncSession) -> None:
    """コネクションプール返却前にテナントコンテキストを安全な初期状態に戻す。

    SET（セッションレベル）で設定した app.tenant_id / app.is_operator / search_path は
    コネクション返却後も PostgreSQL セッションに残る。次リクエストへの汚染を防ぐため、
    get_db の finally ブロックから必ず呼び出す。

    - search_path を public のみに戻す（テナントスキーマへのアクセス不能化）
    - app.tenant_id を空文字に（current_setting(..., true)::INTEGER が NULL を返す）
    - app.is_operator を空文字に（フェイルクローズ維持）

    SQLite (pytest) は no-op。
    """
    if not _dialect_supports_search_path(db):
        return
    await db.execute(text("SET search_path = public"))
    await db.execute(text("SET app.tenant_id = ''"))
    await db.execute(text("SET app.is_operator = ''"))
```

**設計根拠**:
- `SET search_path = public` — テナントスキーマへのアクセスを不能にする
- `SET app.tenant_id = ''` — `current_setting('app.tenant_id', true)::INTEGER` が `NULL` を返し  
  RLS で `tenant_id = NULL` となり全行が不可視（フェイルクローズ維持）
- `RESET app.tenant_id` は未設定時と同じ「unrecognized parameter」エラーになるため使用しない  
  （`missing_ok=true` があるため NULL 扱いになるが、空文字の方が明示的）
- 引数なし — `tenant_id` を知らないコンテキスト（`get_db`）から呼べること

#### 2. `backend/app/database.py` — `get_db` finally ブロック追加

```python
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            from app.auth.dependencies import clear_tenant_context  # 循環import回避
            await clear_tenant_context(session)
```

**設計根拠**:
- `finally` は成功・例外・両方のパスで実行される — 汚染コネクションの返却を構造的に防ぐ
- `get_admin_db` には適用しない — jarvis（BYPASSRLS）は RLS を評価しないためリスクなし
- 循環 import（`database.py` ← `dependencies.py` が `database.py` を import）を避けるため  
  `from app.auth.dependencies import clear_tenant_context` をローカル import にする

#### 3. `backend/tests/test_adr072_phase_2_reset_rollout.py` — テスト更新

既存テストは「router ファイルでの `reset_tenant_context` 呼び出し数」を数える方式。  
ADR-131 以降の正しい検証は「`get_db` の `finally` ブロックに `clear_tenant_context` があること」。

- 既存の「25 router 未適用」カウントテストを削除または skip
- 新しいテスト: `database.py` の `get_db` ソースコードに `clear_tenant_context` が含まれること  
  （`inspect.getsource` またはファイル読み取りによるアサーション）
- 新しいテスト: mock session で `get_db` を `async for` したとき `clear_tenant_context` が  
  呼ばれること（成功パスと例外パス両方）

---

## 却下した代替案

| 案 | 却下理由 |
|----|----------|
| SQLAlchemy `@event.listens_for(engine, "checkin")` | asyncpg の `checkin` イベントは同期コールバックであり、`await` が使えない。回避策が複雑になる |
| FastAPI Middleware でリクエスト終了後にクリア | Middleware は Response 送信後に実行されるが、コネクションはそれより先にプールに返却される可能性がある。確実ではない |
| `get_current_tenant` を yield 関数に変更 | `get_current_tenant` は `db` を受け取るが `db` 自体が別の Depends から来るため、finally で db を操作しても `get_db` の finally より先に実行されない。順序保証が複雑 |
| 既存 router への `reset_tenant_context` 追加（ADR-072 継続） | ヒューマン依存の継続。25 router 未対応の状況が示す通り、漏れを構造的に防げない |

---

## 実装スコープ外

- `reset_tenant_context(db, tenant_id)` の既存呼び出し（各 router の `db.commit()` 直後）は  
  **削除しない**。コミット後のクエリが正しいテナントコンテキストで動くためには引き続き必要。  
  ADR-131 はリクエスト**終了時**のクリアを保証するものであり、コミット後の再設定とは役割が異なる。
- BackgroundTasks（`webhook.py:289`, `meta.py:208`）は独自の `AsyncSessionLocal()` セッションを  
  使用するため `get_db` の finally に依存しない。ただしセッション終了時（`async with AsyncSessionLocal() as session:`）  
  にプールへ返却されるため、現状の `set_tenant_context` のみ実行で未クリアのリスクは残る。  
  → **ADR-132（BackgroundTasks テナント文脈）として別途検討。本ADRのスコープ外。**

---

## 受け入れ基準（Part C）

| # | 基準 | 検証方法 |
|---|------|----------|
| AC-1 | write request が正常終了した後、コネクションの `app.tenant_id` が `''` になること | pytest: mock session の execute 呼び出し履歴を検証 |
| AC-2 | write request が例外を投げた後も `clear_tenant_context` が呼ばれること | pytest: session.rollback() → raise のパスで finally が実行されることを確認 |
| AC-3 | `app.tenant_id` 未設定リクエスト（super_admin など）で `clear_tenant_context` が呼ばれても 500 にならないこと | pytest: テナントコンテキスト設定なしで get_db を使う場合でも no-op で通過 |
| AC-4 | `test_adr072_phase_2_reset_rollout.py` の新テストが CI で green になること | GitHub Actions: test.yml |
| AC-5 | `clear_tenant_context` の呼び出しを `get_db` から除去すると CI が red になること | テスト自体が `database.py` のソースを検証する構造 |
| AC-6 | smoke テスト（Phase2: salesanchor_app 接続）が全 pass であること | `.github/workflows/smoke.yml` |
| AC-7 | migration ファイルは追加しない | PR diff に `migrations/` 変更なし |

---

## リスクと軽減策

| リスク | 軽減策 |
|--------|--------|
| `finally` で例外が発生し、元の例外が隠れる | `clear_tenant_context` 内部の `db.execute(text(...))` は単純な SET 文のため実質的に失敗しない。失敗してもログに残し再 raise はしない |
| `SET app.tenant_id = ''` が PostgreSQL ログに大量出力される | `echo=False`（本番環境、`ENVIRONMENT=production`）のためSQLログ非出力 |
| `get_admin_db` に対して誤適用するリスク | 変更は `get_db` のみ。`get_admin_db` は別関数で手を加えない |
| BackgroundTasks のコンテキスト汚染（既存リスク・現状ギャップ確認済み） | `webhook.py:680-770` の `process_messenger_event` が `AsyncSessionLocal()` 独自セッションで `set_tenant_context` 後に `leads`/`meta_messages`（テナント私有）へ書き込み、`clear_tenant_context` なしでプール返却している。`meta.py:208` の `_enqueue_deletion_task` は Celery enqueue のみで DB 書き込みなし（リスクなし）。`process_messenger_event` の汚染コネクションは次回 `get_db` の finally で清掃されるが、BackgroundTask→BackgroundTask の連続汚染は本ADRでは遮断できない。ADR-132 で `process_messenger_event` 内の `async with` ブロック末尾に `clear_tenant_context` を追加して解消する。 |

---

## 参考

- `backend/app/database.py:46-55` — 変更対象の `get_db`
- `backend/app/auth/dependencies.py:255-277` — `set_tenant_context`
- `backend/app/auth/dependencies.py:317-336` — `reset_tenant_context`（ADR-072 定義）
- `backend/tests/test_adr072_phase_2_reset_rollout.py` — 更新対象テスト
- `docs/recon/recon-sa-foundation-full-audit-20260610.md` — 監査根拠（25 router 未適用の事実確認）
