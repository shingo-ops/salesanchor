# recon: LLM 月次予算リセットの反映漏れ

対象ブランチ: `release/llm-budget-monthly-reset`（`origin/main` 起点）

## 事実

### 1. reset_monthly_if_needed / check_budget の定義

`backend/app/services/llm_budget.py:363-398`
```python
async def reset_monthly_if_needed(
    db: AsyncSession, tenant_id: int, *, now: datetime | None = None
) -> bool:
    """月初判定。last_reset_at が当月 1 日より前なら current_month_usd を 0 にリセット。

    呼び出しタイミング: parse_inventory_message() の冒頭。
    cron でも可だが、起動時 check の方が新規テナント直後でも安全。
    ...
    """
    snap = await _load_budget(db, tenant_id)
    if snap is None:
        return False
    boundary = _month_start_utc(now)
    if snap.last_reset_at >= boundary:
        return False
    # 月跨ぎ。リセット。
    await db.execute(
        text(
            """
            UPDATE public.tenant_llm_budgets
               SET current_month_usd = 0,
                   last_reset_at     = :now
             WHERE tenant_id = :tid
            """
        ),
        {"tid": tenant_id, "now": now or datetime.now(timezone.utc)},
    )
    ...
    return True
```
`check_budget` は `backend/app/services/llm_budget.py:401-415`。`UPDATE` 文はこの関数内で `db.execute()` するのみで、関数自体は `commit()` しない（呼び出し側のトランザクションに乗る）。

### 2. 唯一の本番呼び出し元: inventory_parser.py

`backend/app/services/inventory_parser.py:939` のコメントで手順が明記されている:
```
    分岐:
        1. budget 月初リセット (reset_monthly_if_needed)
        2. budget チェック:
```
実装（`backend/app/services/inventory_parser.py:959-966`）:
```python
    # Step 1: 月初リセット
    try:
        await llm_budget.reset_monthly_if_needed(db, tenant_id)
    except Exception as exc:  # noqa: BLE001 - budget エラーで解析を止めない
        logger.warning("[inventory_parser] budget reset failed: %s", exc)

    # Step 2: budget チェック
    status = await llm_budget.check_budget(db, tenant_id)
```
`reset_monthly_if_needed` は `check_budget` の直前・同一 `db` セッションで呼ばれる。例外は握りつぶして解析を止めない設計。

コミットのタイミング: `_maybe_apply_llm_fallback` 自体は `commit()` しない。呼び出し階層は
`discord_gateway/inbound_writer.py:schedule_parse._runner()`（`backend/app/discord_gateway/inbound_writer.py:425-452`）が
```python
async with db_factory() as session:
    result = await parse_inventory_message(session, ...)
    ...
    await update_parse_result(session, inbound_id, ...)
```
という構造で、同一 `session` を `parse_inventory_message`（→ `reset_monthly_if_needed` の `UPDATE`）と `update_parse_result` の両方に渡している。`update_parse_result`（`backend/app/discord_gateway/inbound_writer.py:329-330`）が末尾で `await db.commit()` を実行し、同一トランザクション内の `reset_monthly_if_needed` の `UPDATE` もここで一緒にコミットされる。

### 3. 未呼び出し: message_translator.py（`origin/main` 基準・修正前）

`git grep -n "reset_monthly_if_needed\|check_budget(" origin/main -- backend/app` の結果、`reset_monthly_if_needed` を呼んでいるのは `backend/app/services/inventory_parser.py` のみ。`backend/app/services/message_translator.py` は `check_budget` のみを3箇所で呼ぶ（`origin/main` 時点の行番号）:
- `backend/app/services/message_translator.py:527`（`origin/main`） — `translate_inbound()` 初回呼び出し前
- `backend/app/services/message_translator.py:550`（`origin/main`） — `translate_inbound()` エスカレーション前
- `backend/app/services/message_translator.py:678`（`origin/main`） — `generate_outbound_draft()` 呼び出し前

`translate_inbound()`（`origin/main` 時点 `backend/app/services/message_translator.py:488-584`）は末尾 `:571` で `await db.commit()`。
`generate_outbound_draft()`（`origin/main` 時点 `backend/app/services/message_translator.py:660-700`）は末尾付近で `await db.commit()`（`save_outbound_draft` 直後）。

修正後（本ブランチ）の行番号: `reset_monthly_if_needed` の import 追加は `backend/app/services/message_translator.py:38`、呼び出しは `translate_inbound()` 内 `:528`（直後 `:529` の `check_budget` 初回呼び出し前）、`generate_outbound_draft()` 内 `:680`（直後 `:681` の `check_budget` 呼び出し前）。`db.commit()` はそれぞれ `:573`、`:711`（行がずれただけで commit 構造自体に変更なし）。

呼び出し元（`origin/main` 基準、`git grep`）:
- `backend/app/routers/conv_logs.py:153` → `ensure_inbound_translations()` → `translate_inbound()`
- `backend/app/tasks/translation.py:85, 219` → `ensure_inbound_translations()` → `translate_inbound()`
- `backend/app/routers/translation.py:142` → `generate_outbound_draft()`

いずれも `translate_inbound` / `generate_outbound_draft` に渡す `db` セッションを関数内部で `commit()` しており、`reset_monthly_if_needed` を同じ関数内で呼べば `backend/app/services/inventory_parser.py` と同じ「reset → check、同一トランザクションでまとめてコミット」というパターンを再現できる。

### 4. 本番データ（read-only、2026-10-02 取得）

```
tenant_id | monthly_budget_usd | current_month_usd | last_reset_at              | hard_stop
4         | 5.00                | 0.0000             | 2026-05-22 07:59:12.937633+00 | t
6         | 1.00                | 0.0145             | 2026-05-22 07:59:12.937633+00 | t
```
コマンド:
```
ssh -i ~/.ssh/manual-only/id_ed25519 -o BatchMode=yes ubuntu@49.212.137.46 'docker exec -i astro-webapp-postgres-1 psql -U jarvis -d jarvis_db -At -c "SELECT tenant_id, monthly_budget_usd, current_month_usd, last_reset_at, hard_stop FROM public.tenant_llm_budgets ORDER BY tenant_id"'
```
`last_reset_at` が 2026-05-22 のまま＝5ヶ月分（6-10月）`reset_monthly_if_needed` が一度も呼ばれていない。両テナントとも在庫解析（inventory_parser 経由）の呼び出し頻度が低い/ゼロで、翻訳機能（message_translator 経由）のみ使われていた場合、リセットが一度も走らない状態が継続する。tenant 6 の `current_month_usd=0.0145` は5月以降の累積値（本来は当月分のみであるべき）。

## 判断

- `reset_monthly_if_needed` は呼び出し側トランザクション内で `UPDATE` するだけで `commit()` しない設計のため、`backend/app/services/message_translator.py` の各エントリポイント冒頭（`check_budget` 直前）に追加しても、既存の `await db.commit()`（`translate_inbound` 末尾・`generate_outbound_draft` 末尾）でまとめてコミットされる。`backend/app/services/inventory_parser.py` と同じ「reset → check、まとめてコミット」のパターンが成立する。新規コミットの追加は不要かつ行わない。
- ADR-072（テナントスキーマ prefix 強制）の `reset_tenant_context()` 必須ルールは write endpoint の `db.commit()` 直後が対象。本変更は `tenant_llm_budgets`（`public` スキーマ、テナント非分離の共有テーブル）への `UPDATE` のみで、`reset_tenant_context` の対象になる tenant-prefixed write ではない（`backend/app/services/inventory_parser.py` の既存呼び出しも同様に `reset_tenant_context` を伴っていない）。ブロッカーなし。
