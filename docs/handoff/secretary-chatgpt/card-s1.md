# 実装カード 秘1: 秘書が担当表からモデルを読み、使用の記録に1回1行を残す

設計者: Opus（2026-11-03）。設計: `docs/handoff/secretary-chatgpt/design.md` §4-2-1・§4-2-3・§4-3・§5-1・§5-3・§7 の段 秘1・§10。決定: `docs/adr/ADR-1058-ai-job-assignments.md`（2026-11-03 PO が「この設計で決める」に「1」。2026-11-03 PO が「画面ができるまで審査と本番反映まで進める」に「1」。2026-11-03 PO が「秘書の道を先にして、今日から始める。失敗の記録の段は明日の確かめの後に回す」に「1」）。
本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
担当: Sonnet（クラウド）。PR は作らない（手元の Opus が作る）。
読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md・guards/03-file.md・guards/05-pr.md（照合: 場所は行番号ではなく前後の文字で決める／commit と push の後は git log で確かめる／PR はクラウドで作らない）。

## 受領確認
着手前に、作業場所のブランチが `release/ai-roster-s1-secretary` で、HEAD に `docs/handoff/secretary-chatgpt/card-s1.md` があることを報告の1行目に書く。

## カード発行前チェック（design-partner.md §5.5）
- 1 記号: パス・SQL・値・関数名はすべてバッククォートで囲んだ ○
- 2 下書き禁止: PR はクラウドで作らない。手元の Opus が ready で作る ○
- 3 報告の宛先: 完了報告の本文に生出力を全文含める、と書いた ○
- 4 1便1目的: 秘書が担当表からモデルを読むことと、秘書の使用の記録の行と、その試験と使用量画面の名前だけ。解析・翻訳のコード・Gemini の失敗の行（段1b-1）・codex の容器（段3）・担当の画面（段2）は入れない ○
- 5 起点: ブランチ `release/ai-roster-s1-secretary` は手元の Opus が origin/main 起点で作って渡す ○
- 6 書式の実例: PR 本文は手元の Opus が書くので載せない（該当なし） ○
- 7 合格基準: ruff の出力の文言・node の試験の数・main との差分のファイルの一覧・削除行の数まで書いた。DB の試験と画面の試験の PASSED は CI で手元の Opus が確かめる ○
- 8 名前を出す: 差分の数が違う時は、そのファイルの削除行を出す手順を対にした ○
- 9 出力の上限: 一覧は `grep` と `head` で絞る ○
- 10 報告の型: 冒頭に「本報告はカード 秘1 の実行結果である」、止まった時は節の番号・最後のコマンド・理由、最終行は DONE / BLOCKED: / NEEDS_DECISION: ○
- 11 期待値: 場所は前後の文字で決める。数は実物から数える ○

## なぜ（短く）
段1a で担当表 `public.ai_job_assignments`・`public.ai_job_choices` と、使用の記録 `public.llm_usage_events` の `outcome`・`error_code` の列が入った。秘書は今、容器 `secretary-agent/server.mjs` が `"--model", "sonnet"` を固定で持ち、使用の記録に何も書かない。この便で、backend が担当表から秘書の担当を読んで容器へ model を渡し、1回の頼みごとに使用の記録へ ok か failed を1行書く。後の段2（画面で切り替え）・段3（ChatGPT の容器）はこの形の上に乗る。

## 禁止（名指し）
- 下の「触るファイル」の12個以外を変えない。`migrations/`・`scripts/`・`.github/`・`deploy.yml`・compose・`secretary-agent/Dockerfile`・`backend/app/schemas/assistant.py` は変えない。
- 解析と翻訳のコード（`backend/app/services/gemini_extraction_svc.py`・`gemini_raw_copy_v8.py`・`line_analysis_v102_svc.py`・`tcg_extraction_record_svc.py`・`message_translator.py`・`backend/app/tasks/`）は変えない。
- `llm_budget.py` の今ある関数（`record_usage_event_sync`・`record_usage_event`・`_usage_event_columns`・`calculate_usage_cost`・`_INSERT_USAGE_EVENT_SQL`）の中身は変えない。足すだけ（`USAGE_PURPOSES`・`USAGE_SDKS` の値を足すのと `__all__` を除く）。
- `gemini_ledger_error_code`・`record_usage_failure_sync` は足さない（段1b-1）。
- `assistant.py` の失敗の読み替え（`_call_agent` の status ごとの分け方）と返事の作り方（④〜⑥）は変えない。
- 今ある試験は書き換えない・消さない（足すだけ）。例外は 4-1 の `allowed` の準備と、6-1 の body に `model` を足すことだけ。
- 本番に繋がない。本番の鍵を使わない。VPS に入らない。
- PR を作らない・マージしない。GO 記録を書かない。`/review` を実行しない。rebase・force push をしない。`git stash` を使わない。`rm -rf` を使わない。
- 全部の試験を流さない。使い捨ての PostgreSQL・venv を作らない（DB の試験は GitHub の CI で回る）。
- 試験のファイル（`.py`）を書く・直すときは、Write と Edit の道具だけを使う。Bash の python やヒアドキュメントで書き換えない。DB の試験のファイルには表の行を消す文と使い捨て DB を消す後始末の文があり、Bash の命令に入るとクラウドの見張りが止めるため。Bash の命令の文にもその語を書かない。
- 頼みの文・答えの中身・鍵をログに出さない（ログは種類だけ）。
- 見張り（フック）に止められたら、言い換えて同じことをしない。そこで止まる。

## 触るファイル（この12個だけ。ほかに docs/ のこのカード）
1. `backend/app/services/llm_budget.py`
2. backend/app/services/ai_assignment.py（新しいファイル）
3. `backend/app/routers/assistant.py`
4. `backend/tests/test_assistant_router.py`
5. backend/tests/test_llm_usage_isolated.py（新しいファイル。DB 不要）
6. `backend/tests/ops/test_ai_job_assignments_db.py`（1本足す。本物の DB）
7. `secretary-agent/server.mjs`
8. `secretary-agent/server.test.mjs`
9. `frontend/src/pages/super-admin/components/LlmUsageSection.tsx`
10. `frontend/src/pages/super-admin/components/LlmUsageSection.test.tsx`
11. `frontend/src/locales/ja.json`
12. `frontend/src/locales/en.json`

## 0. 着手前の確かめ（読むだけ。前提が違えば NEEDS_DECISION で止まる）
- 0-1 `grep -n "secretary_intent\|codex-cli\|claude-code" migrations/20261103_120000_create_ai_job_assignments.sql | head -20` で、purpose の CHECK に `'secretary_intent'`、sdk の CHECK に `'codex-cli', 'claude-code'` があり、初めの選択肢に `('secretary_intent', 'claude', 'sonnet')` がある。
- 0-2 `git grep -n "record_usage_isolated\|USAGE_ERROR_CODES\|_INSERT_USAGE_EVENT_OUTCOME_SQL\|_outcome_columns\|get_ai_assignment\|AiAssignment" -- backend secretary-agent frontend/src` が0行。
- 0-3 `test -e backend/app/services/ai_assignment.py; echo $?` と `test -e backend/tests/test_llm_usage_isolated.py; echo $?` がどちらも `1`。
- 0-4 `grep -n '"--model", "sonnet",' secretary-agent/server.mjs` が1行。`grep -n "function runClaude(text, now)" secretary-agent/server.mjs` が1行。`grep -n "runClaude(text, now)" secretary-agent/server.mjs` が2行（定義と呼び出し）。
- 0-5 `grep -c 'now: "' secretary-agent/server.test.mjs` が `9`（POST の body の数。(1) の1つと、ほかの8つ）。
- 0-6 `git grep -n "secretary_intent" -- frontend/src` が0行。`grep -n '"translation_outbound": ' frontend/src/locales/ja.json frontend/src/locales/en.json` が各1行（`"送信翻訳"`・`"Outbound Translation"`）。
- 0-7 `grep -n "async def _call_agent(text: str) -> dict:\|await db.commit()\|raw = await _call_agent(body.text)\|getattr(exc, \"_log_code\", \"unreadable\")" backend/app/routers/assistant.py` が4行。

## 1. `backend/app/services/llm_budget.py`
- 1-1 `USAGE_PURPOSES` の塊の `        "translation_outbound",` の次の行に `        "secretary_intent",` を足す。
- 1-2 `USAGE_SDKS: frozenset[str] = frozenset({"google-genai", "google-generativeai"})` を次に替える:
```python
USAGE_SDKS: frozenset[str] = frozenset({"google-genai", "google-generativeai", "codex-cli", "claude-code"})
```
- 1-3 `_INSERT_USAGE_EVENT_SQL = """` の塊の閉じ `"""` の次（空行2つ）に足す:
```python
# ADR-1058: outcome（ok/failed）と error_code を含む行の INSERT と、その値の一覧。
# 値の一覧の正本は DB の CHECK（migrations/20261103_120000_create_ai_job_assignments.sql）。ここは写し。
USAGE_ERROR_CODES: frozenset[str] = frozenset(
    {
        "auth_failed",
        "timeout",
        "rate_limited",
        "http_error",
        "unreadable",
        "tool_used",
        "not_ready",
        "busy",
        "other",
    }
)
USAGE_OUTCOMES: frozenset[str] = frozenset({"ok", "failed"})

_INSERT_USAGE_EVENT_OUTCOME_SQL = """
    INSERT INTO public.llm_usage_events
        (id, purpose, tenant_id, model, sdk,
         prompt_tokens, cached_content_tokens, candidates_tokens, thoughts_tokens,
         tool_use_prompt_tokens, total_tokens, cost_usd,
         extraction_attempt_id, extraction_shadow_run_id, discord_inbound_message_id, source_ref,
         outcome, error_code)
    VALUES
        (:id, :purpose, :tenant_id, :model, :sdk,
         :prompt_tokens, :cached_content_tokens, :candidates_tokens, :thoughts_tokens,
         :tool_use_prompt_tokens, :total_tokens, :cost_usd,
         :extraction_attempt_id, :extraction_shadow_run_id, :discord_inbound_message_id, :source_ref,
         :outcome, :error_code)
"""


def _outcome_columns(outcome: str, error_code: str | None) -> dict[str, Any]:
    """outcome と error_code の組を DB の CHECK と同じ決まりで確かめる（ok なら NULL、failed なら9つのどれか）。"""
    if outcome not in USAGE_OUTCOMES:
        raise ValueError(f"unknown llm_usage_events outcome: {outcome!r}")
    if outcome == "ok" and error_code is not None:
        raise ValueError("outcome='ok' の行に error_code は入れない")
    if outcome == "failed" and error_code not in USAGE_ERROR_CODES:
        raise ValueError(f"unknown llm_usage_events error_code: {error_code!r}")
    return {"outcome": outcome, "error_code": error_code}
```
- 1-4 `async def record_usage_event(` の関数の終わり（`    return cols["id"]` の次。その後ろの `# DB ops` の区切りの前）に、空行2つを置いて足す:
```python
async def record_usage_isolated(
    *,
    purpose: str,
    model: str,
    sdk: str,
    counts: UsageCounts,
    outcome: str,
    error_code: str | None,
    tenant_id: int | None = None,
    source_ref: str | None = None,
) -> None:
    """自分専用の取引で1行書いてすぐ commit する（呼び出し元の取引が巻き戻っても行が残る。design.md §4-2-3）。

    自分の失敗はログに種類だけ出して飲み込む（呼び出し元の元の例外を隠さない）。
    """
    try:
        cols = _usage_event_columns(
            purpose=purpose,
            model=model,
            sdk=sdk,
            counts=counts,
            tenant_id=tenant_id,
            extraction_attempt_id=None,
            extraction_shadow_run_id=None,
            discord_inbound_message_id=None,
            source_ref=source_ref,
        )
        cols.update(_outcome_columns(outcome, error_code))
        # app.database は読み込むとエンジンを作るので、使う時だけ読む。
        from app.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            await db.execute(text(_INSERT_USAGE_EVENT_OUTCOME_SQL), cols)
            await db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.error("[llm_budget] 使用の記録に書けませんでした: purpose=%s kind=%s", purpose, type(exc).__name__)
```
- 1-5 `__all__` に3つ足す: `"USAGE_SDKS",` の次の行に `"USAGE_ERROR_CODES",` と `"USAGE_OUTCOMES",`（この順）、`"record_usage_event_sync",` の次の行に `"record_usage_isolated",`。
- ほかの行は変えない。`Any`・`text`・`logger`・`UsageCounts` は今のファイルにある（0 で無ければ止まる）。

## 2. backend/app/services/ai_assignment.py（新しいファイル。中身はこのとおり）
```python
"""ADR-1058: AI の担当表を読む所（ここ1か所だけ。design.md §4-3）。

行が無ければ AiAssignmentMissing を上げる（既定値に逃げない）。sync 版は段1b-2 で同じ SQL から足す。
app.database は読まない（読むとエンジンを作るため。セッションは呼び手から受け取る）。
"""

from __future__ import annotations

from typing import NamedTuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_SELECT_ASSIGNMENT_SQL = """
    SELECT c.provider, c.model
    FROM public.ai_job_assignments a
    JOIN public.ai_job_choices c ON c.id = a.choice_id AND c.job_key = a.job_key
    WHERE a.job_key = :job_key
"""


class AiAssignment(NamedTuple):
    provider: str
    model: str


class AiAssignmentMissing(LookupError):
    """担当表に job_key の行が無い。"""


async def get_ai_assignment(db: AsyncSession, job_key: str) -> AiAssignment:
    """job_key の今の担当（provider・model）を返す。行が無ければ AiAssignmentMissing。"""
    row = (await db.execute(text(_SELECT_ASSIGNMENT_SQL), {"job_key": job_key})).first()
    if row is None:
        raise AiAssignmentMissing(job_key)
    return AiAssignment(provider=row[0], model=row[1])


__all__ = ["AiAssignment", "AiAssignmentMissing", "get_ai_assignment"]
```

## 3. `backend/app/routers/assistant.py`
- 3-1 頭の説明文の `順番（厳守）: ①守りを通す ②db.commit() ③容器を呼ぶ ④会社の文脈を張り直す ⑤名前探し ⑥返す。` を次に替える:
```
順番（厳守）: ①守りを通す・担当表を読む ②db.commit() ③容器を呼ぶ・使用の記録に1行 ④会社の文脈を張り直す ⑤名前探し ⑥返す。
```
- 3-2 `from app.services.secretary_resolve import resolve_names` の前の行に足す（並びは ai_assignment・llm_budget・secretary_resolve）:
```python
from app.services.ai_assignment import get_ai_assignment
from app.services.llm_budget import UsageCounts, record_usage_isolated
```
- 3-3 `_perm_invoices_create = require_permission("invoices.create")` の次（空行2つ）に足す:
```python
# ADR-1058 秘1: 担当表の provider → 使用の記録の sdk。ここに無い provider は容器が無いので not_ready（codex は段3で足す）。
_SDK_BY_PROVIDER = {"claude": "claude-code"}
# 使用の記録の error_code にそのまま使うログの code（design.md §4-2-1 の秘書の読み替え）。ほかは "other"。
_LEDGER_ERROR_CODES = frozenset({"auth_failed", "timeout", "unreadable", "tool_used", "not_ready", "busy"})
```
- 3-4 `def _log(` の関数の終わり（`    )` の次）に、空行2つを置いて足す:
```python
def _ledger_error_code(log_code: str) -> str:
    return log_code if log_code in _LEDGER_ERROR_CODES else "other"


async def _record_ledger(tenant_id: int, model: str, sdk: str, outcome: str, error_code: str | None) -> None:
    """秘書の1回の頼みを使用の記録に1行（別の取引ですぐ commit。失敗は record_usage_isolated がログに出して飲み込む）。"""
    await record_usage_isolated(
        purpose="secretary_intent",
        model=model,
        sdk=sdk,
        counts=UsageCounts(),
        outcome=outcome,
        error_code=error_code,
        tenant_id=tenant_id,
    )
```
- 3-5 `_call_agent` の頭の2行を替える。前:
```python
async def _call_agent(text: str) -> dict:
    """容器を呼ぶ。失敗は (HTTPException, ログの code) に直す。"""
```
後:
```python
async def _call_agent(text: str, model: str) -> dict:
    """容器を呼ぶ（model は担当表から読んだ値）。失敗は (HTTPException, ログの code) に直す。"""
```
- 3-6 `                json={"text": text, "now": now},` を `                json={"text": text, "now": now, "model": model},` に替える。
- 3-7 `post_assistant_message` の中の次の3行（前）:
```python
    started = time.monotonic()
    user_id = current_user.id

```
の後、`    # ② 取引を閉じる（AI を待つ間 DB を開いたままにしない）` の前に足す:
```python
    # ① 担当を読む（commit の前。後に読むと AI を待つ間 DB の取引が開いたままになる。design.md §5-3）
    # 読めない時は容器を呼ばず、台帳にも書かない（sdk と model が分からないため）。
    try:
        assignment = await get_ai_assignment(db, "secretary_intent")
    except Exception:  # noqa: BLE001
        _log(user_id, tenant_id, started, "not_ready", None)
        raise _fail(503, "not_ready") from None
    sdk = _SDK_BY_PROVIDER.get(assignment.provider)
    if sdk is None:
        _log(user_id, tenant_id, started, "not_ready", None)
        raise _fail(503, "not_ready")

```
- 3-8 `        raw = await _call_agent(body.text)` を `        raw = await _call_agent(body.text, assignment.model)` に替える。
- 3-9 except の塊を替える。前:
```python
    except HTTPException as exc:
        _log(user_id, tenant_id, started, getattr(exc, "_log_code", "unreadable"), cost)
        raise

    # ④ 会社の文脈を張り直す
```
後:
```python
    except HTTPException as exc:
        log_code = getattr(exc, "_log_code", "unreadable")
        _log(user_id, tenant_id, started, log_code, cost)
        await _record_ledger(tenant_id, assignment.model, sdk, "failed", _ledger_error_code(log_code))
        raise

    # AI の呼び出しが成功した（容器が 200・形と日時の検査を通った）。この後の失敗でも ok のまま（design.md §4-2-3）
    await _record_ledger(tenant_id, assignment.model, sdk, "ok", None)

    # ④ 会社の文脈を張り直す
```
- ほかの行は変えない。

## 4. `backend/tests/test_assistant_router.py`
- 4-1 頭の import に足す: `from unittest.mock import AsyncMock`（`from pathlib import Path` の次）と、`from app.services.ai_assignment import AiAssignment` と `from app.services.llm_budget import UsageCounts`（`from app.routers import assistant` の次。この順）。
- 4-2 `allowed` の準備を替える。前:
```python
@pytest.fixture
def allowed(client):
    """会社の入口・super admin の守りを通す（権限は conftest が全付与）。"""
```
後:
```python
@pytest.fixture
def allowed(client, monkeypatch):
    """会社の入口・super admin の守りを通す（権限は conftest が全付与）。

    試験の DB（SQLite）に担当表は無いので、担当の読み取りは claude・sonnet を返す偽物に、
    使用の記録は AsyncMock に差し替える（試験からは assistant.record_usage_isolated で見る）。
    """

    async def _assignment(db, job_key):
        assert job_key == "secretary_intent"
        return AiAssignment("claude", "sonnet")

    monkeypatch.setattr(assistant, "get_ai_assignment", _assignment)
    monkeypatch.setattr(assistant, "record_usage_isolated", AsyncMock())
```
（この後の `from app.main import app` からの行は今のまま。）
- 4-3 ファイルの最後に足す試験（名前はこのとおり。今の試験と同じく `async def`・`allowed` を使い、容器の偽物は今ある `_mock_agent(monkeypatch, handler)` と `_respond(status, body)` を使う。送られた body は handler の中で `json.loads(request.content)` で取る）:
  - ① `test_agent_receives_model_from_assignment`: 容器の偽物で送られた body を取り、`sent["model"] == "sonnet"`・`sent["text"] == "請求書"`。見本は `envelope-invoice.json`。
  - ② `test_assignment_read_failure_is_503_without_agent_or_ledger`（parametrize 2組）: (a) `assistant.get_ai_assignment` を `RuntimeError("db down")` を上げる async 関数に差し替え (b) `AiAssignment("codex", "gpt-x")` を返す async 関数に差し替え。どちらも、容器の偽物が呼ばれた回数が0、`status_code == 503`、`detail == {"code": "not_ready"}`、`assistant.record_usage_isolated.await_count == 0`、caplog の `assistant_message` の行が1つで `code=not_ready` を含む。
  - ③ `test_ledger_ok_row_for_each_fixture`（parametrize: `envelope-invoice.json`・`envelope-event.json`・`envelope-unknown.json`）: 200、`assistant.record_usage_isolated.await_count == 1`、その kwargs が `purpose == "secretary_intent"`・`model == "sonnet"`・`sdk == "claude-code"`・`outcome == "ok"`・`error_code is None`・`tenant_id == 999`・`counts == UsageCounts()`。
  - ④ `test_ledger_failed_row_for_agent_failures`（parametrize。容器の答え → 期待の error_code）: `(503, {"code": "not_ready"})`→`not_ready`、`(429, {"code": "busy"})`→`busy`、`(504, {"code": "timeout"})`→`timeout`、`(502, {"code": "cli_failed"})`→`other`、`(502, {"code": "auth_failed"})`→`auth_failed`、`(502, {"code": "unreadable"})`→`unreadable`、`(200, {"kind": "invoice"})`→`unreadable`。どれも `await_count == 1`、kwargs が `outcome == "failed"`・`error_code` が期待どおり・`purpose == "secretary_intent"`・`sdk == "claude-code"`・`model == "sonnet"`・`tenant_id == 999`。
  - ⑤ `test_ledger_failed_row_for_transport_errors`（parametrize）: 容器の偽物が `httpx.ConnectError("refused")` を上げる→`not_ready`、`httpx.ReadTimeout("slow")` を上げる→`timeout`。④と同じ確かめ。
  - ⑥ `test_ledger_unit_mapping`: `assistant._ledger_error_code` が `"cli_failed"`→`"other"`、`"agent_failed"`→`"other"`、`"tool_used"`→`"tool_used"`、`"auth_failed"`→`"auth_failed"`。`assistant._LEDGER_ERROR_CODES` が `USAGE_ERROR_CODES`（`from app.services.llm_budget import USAGE_ERROR_CODES`）の部分集合。
- 今ある試験は変えない（`allowed` を使う試験はこの差し替えでそのまま通る想定。通らなければ 11 の分岐）。

## 5. backend/tests/test_llm_usage_isolated.py（新しいファイル。DB 不要）
- 5-1 `USAGE_PURPOSES` がちょうど `{"line_extraction", "line_extraction_shadow", "inventory_parse_fallback", "translation_inbound", "translation_inbound_escalation", "translation_outbound", "secretary_intent"}`。`USAGE_SDKS` がちょうど `{"google-genai", "google-generativeai", "codex-cli", "claude-code"}`。`USAGE_ERROR_CODES` がちょうど 0-1 の migration の9つ（`auth_failed`・`timeout`・`rate_limited`・`http_error`・`unreadable`・`tool_used`・`not_ready`・`busy`・`other`）。`USAGE_OUTCOMES == {"ok", "failed"}`。
- 5-2 `_outcome_columns`（parametrize）: `("ok", None)` は `{"outcome": "ok", "error_code": None}`。`("failed", "timeout")` は `{"outcome": "failed", "error_code": "timeout"}`。`("ok", "timeout")`・`("failed", None)`・`("failed", "nope")`・`("maybe", None)` は `ValueError`。
- 5-3 `_usage_event_columns(purpose="secretary_intent", model="sonnet", sdk="claude-code", counts=UsageCounts(), tenant_id=1, extraction_attempt_id=None, extraction_shadow_run_id=None, discord_inbound_message_id=None, source_ref=None)` が例外にならず、`cost_usd is None`、`prompt_tokens is None`、`total_tokens is None`。`sdk="codex-cli"` でも例外にならない。
- 5-4 `record_usage_isolated`: `monkeypatch.setattr("app.database.AsyncSessionLocal", factory)` で、`execute`・`commit` が AsyncMock の偽のセッションを返す async の context manager の工場に差し替える。①`purpose="secretary_intent", model="sonnet", sdk="claude-code", counts=UsageCounts(), outcome="failed", error_code="auth_failed", tenant_id=1` で呼ぶと execute が1回・commit が1回、execute の2つ目の引数が `outcome == "failed"`・`error_code == "auth_failed"`・`purpose == "secretary_intent"`・`cost_usd is None`、1つ目の引数の文に `outcome` を含む ②execute が例外を上げると、例外は外に出ず commit は呼ばれず、caplog に `使用の記録に書けませんでした` を含む行が1つ ③`outcome="ok", error_code="timeout"` は外に出ず execute も呼ばれない ④`purpose="nope"` も外に出ず execute も呼ばれない。

## 6. `backend/tests/ops/test_ai_job_assignments_db.py`（ファイルの最後に1本足す。今の行は変えない）
```python
def test_f_get_ai_assignment_reads_choice_and_raises_when_missing(db):
    """秘1: 読む関数が担当表から provider・model を返し、行が無ければ例外（既定値に逃げない）。"""
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.services.ai_assignment import AiAssignment, AiAssignmentMissing, get_ai_assignment

    c = db.cursor()
    c.execute(_read(_AI_JOB_SQL))
    url = _psycopg_url(ADMIN_PG_URL, db.info.dbname).replace("postgresql://", "postgresql+asyncpg://", 1)

    async def read(job_key):
        eng = create_async_engine(url)
        try:
            async with AsyncSession(eng) as s:
                return await get_ai_assignment(s, job_key)
        finally:
            await eng.dispose()

    assert asyncio.run(read("secretary_intent")) == AiAssignment("claude", "sonnet")
    assert asyncio.run(read("line_extraction")) == AiAssignment("gemini", "gemini-3.1-flash-lite")
    c.execute("DELETE FROM public.ai_job_assignments WHERE job_key = 'secretary_intent'")
    with pytest.raises(AiAssignmentMissing):
        asyncio.run(read("secretary_intent"))
```
- 頭の説明文の `(e) outcome と error_code の組み合わせの決まり。` の次の行に `(f) 読む関数 get_ai_assignment（秘1）。` を足す。
- このファイルは Write か Edit の道具だけで直す（禁止の項）。

## 7. `secretary-agent/server.mjs`
- 7-1 `// claude を 1 回動かす。返り値: { status, body }` の前の行に足す（後ろに空行1つ）:
```js
// model は backend が担当表から読んで送る（ADR-1058）。容器は既定のモデルを持たない。
// 引数に渡すので、- で始まる値や記号は通さない。
const MODEL_RE = /^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/;
```
- 7-2 `function runClaude(text, now) {` を `function runClaude(text, now, model) {` に替える。
- 7-3 `        "--model", "sonnet",` を `        "--model", model,` に替える。
- 7-4 `      let text, now;` を `      let text, now, model;` に、`        ({ text, now } = JSON.parse(raw));` を `        ({ text, now, model } = JSON.parse(raw));` に替える。
- 7-5 次の塊（前）:
```js
      if (typeof text !== "string" || typeof now !== "string" || !text) {
        return send(res, 400, { code: "bad_request" });
      }
```
の次の行に足す（鍵の検査 `if (!process.env.CLAUDE_CODE_OAUTH_TOKEN)` より後のまま。試験 (1) の 503 を保つ）:
```js
      if (typeof model !== "string" || !MODEL_RE.test(model)) {
        return send(res, 400, { code: "bad_request" });
      }
```
- 7-6 `        const { status, body } = await runClaude(text, now);` を `        const { status, body } = await runClaude(text, now, model);` に替える。

## 8. `secretary-agent/server.test.mjs`
- 8-1 POST の body のうち、`test("(1) トークン無しは 503` の中の1つ以外の8つに `model: "sonnet"` を足す（例: `{ text: "a", now: "n" }` → `{ text: "a", now: "n", model: "sonnet" }`。`const body = { text: "a", now: "2026-11-01T10:00:00+09:00" };` と `{ text, now: "2026-11-01T10:00:00+09:00" }` も同じ）。期待は変えない。
- 8-2 `test("probe: 閉じた port と` の前に3本足す:
  - ⑦ `test("(8) body の model が --model の次の引数に入る", ...)`: 偽の claude は今の (4)(5) と同じく `printf '%s\\n' "$@" > "${argsLog}"; cat >/dev/null; echo '{"structured_output":{"kind":"unknown","invoice":null,"event":null,"reply":"r"}}'`。`{ text: "a", now: "n", model: "opus" }` で 200。`args.log` を行に分け、`--model` の次の行が `opus`、`sonnet` の行が0。
  - ⑧ `test("(9) model が無い・文字でない・空・- で始まる・記号入りは 400 bad_request で claude を呼ばない", ...)`: 偽の claude は `touch "${work}/called"; cat >/dev/null; echo '{}'`。body を `{ text: "a", now: "n" }`・`{ text: "a", now: "n", model: 5 }`・`{ text: "a", now: "n", model: "" }`・`{ text: "a", now: "n", model: "--dangerously-skip-permissions" }`・`{ text: "a", now: "n", model: "a b" }` の5つで送り、どれも `status == 400`・`json` が `{ code: "bad_request" }`。最後に `fs.existsSync(path.join(work, "called"))` が `false`。
  - ⑨ `test("(10) 鍵が無い時は model が無くても 503", ...)`: 今の (1) と同じ起動で `{ text: "x", now: "n" }` → 503（設計の⑨。(1) はそのまま残す）。

## 9. 画面
- 9-1 `frontend/src/pages/super-admin/components/LlmUsageSection.tsx` の `KNOWN_PURPOSES` の `  "translation_outbound",` の次の行に `  "secretary_intent",` を足す。
- 9-2 `frontend/src/locales/ja.json` の `          "translation_outbound": "送信翻訳"` を `          "translation_outbound": "送信翻訳",` にし、次の行に `          "secretary_intent": "チャット秘書"` を足す。
- 9-3 `frontend/src/locales/en.json` の `          "translation_outbound": "Outbound Translation"` を `          "translation_outbound": "Outbound Translation",` にし、次の行に `          "secretary_intent": "Chat Secretary"` を足す。
- 9-4 `frontend/src/pages/super-admin/components/LlmUsageSection.test.tsx` の `it("falls back to the raw purpose code for an unknown purpose"` の試験の次に足す:
```ts
it("shows the localized label for secretary_intent", async () => {
  vi.mocked(api.get).mockResolvedValue({
    ...response,
    by_purpose: [{ ...response.by_purpose[0], purpose: "secretary_intent" }],
  });
  view();
  expect((await screen.findAllByText("Chat Secretary")).length).toBeGreaterThan(0);
  expect(screen.queryByText("secretary_intent")).toBeNull();
});
```

## 10. 確かめ方
- `uvx ruff check --config backend/pyproject.toml backend/app/services/llm_budget.py backend/app/services/ai_assignment.py backend/app/routers/assistant.py` の出力が `All checks passed!`。並びの直しだけを求められたら `--fix` の結果に従う。
- backend/app/services/ai_assignment.py は `uvx ruff format --config backend/pyproject.toml --check` が通る。llm_budget.py と assistant.py は整形し直さない。この2つについて `uvx ruff format --config backend/pyproject.toml --diff` の結果の `^@@` の行の数（`grep -c`）を、変える前（origin/main の写し）と変えた後で比べ、増えていないこと（増えたら足した行を直す）。前と後の数を報告に書く。
- `node --test secretary-agent/server.test.mjs` を流し、出力を全文写す。`# fail 0` と `# pass` の数（今の数＋3）を報告に書く。
- mock の試験（DB 不要）だけ流す: `cd backend && uv run --no-project --with-requirements requirements.txt --with pytest --with pytest-asyncio python -m pytest tests/test_llm_usage_isolated.py tests/test_assistant_router.py -q`。この形で依存が入らない時は流さずに「mock の試験はクラウドで流せなかった」と書き、CI に任せる（venv は作らない）。流した時は出力を全文写す。
- 画面の試験: `cd frontend && npx vitest run src/pages/super-admin/components/LlmUsageSection.test.tsx` を試す。依存が無くて流せない時は `npm ci` をしてよい（1回だけ）。それでも流せない時は「画面の試験はクラウドで流せなかった」と書き、CI に任せる。
- DB の試験（6）はクラウドでは流さない。報告に「DB の試験はクラウドでは流さず CI に任せた」と書く。流していない試験を合格と書かない。
- `bash scripts/dev/check-before-submit.sh` があれば流し、出力の最後の20行と終了コードを写す（無ければ「無い」と書く）。
- `git diff origin/main...HEAD --name-only` が「触るファイル」の12個と `docs/handoff/secretary-chatgpt/card-s1.md` だけ（ほかがあれば止まる）。
- `git diff origin/main...HEAD --numstat` の削除の数（2列目）が、1 は 1、2 は 0、3 は 6 以下（3-1・3-5 の2行・3-6・3-8・3-9 の1行）、4 は 1 以下（`def allowed(client):` の1行。説明文が1行の時は 2 以下）、5 は 0、6 は 0、7 は 5、8 は 8、9 は 0、10 は 0、11 は 1、12 は 1。違えば そのファイルを指定した `git diff origin/main...HEAD --` の `^-` の行（`grep` と `head -30`）を出して止まる。
- 生出力は作業場所の外の一時フォルダに保存し、パスと全文を報告に書く。

## 11. 想定される分岐と止まる条件
- 0 の前提が違う → 止まり、NEEDS_DECISION: で返す（違った所の生出力を付ける）。
- 1〜9 の「前」の文字列が見つからない（カードの前後の文字と違う） → 止まり、NEEDS_DECISION: で返す。
- 今ある `allowed` を使う試験が、4-2 の差し替えの後に落ちる → 落ちた試験の名前と出力を写して止まる（試験を書き換えて通さない）。
- `node --test` で今ある試験が落ちる → 8-1 の足し忘れを先に疑い、足し忘れでなければ止まる。
- 1-4 の `from app.database import AsyncSessionLocal` が循環の import で落ちる → 止まり、NEEDS_DECISION: で返す。
- 画面の試験で `Chat Secretary` が見つからない → `response` の作り（どこに purpose が出るか）を読み、試験の探し方だけを直してよい。画面の部品は 9-1 以外を変えない。
- カードに無いファイルを触る必要が出た → 止まり、NEEDS_DECISION: で返す。
- 迷ったら停止して NEEDS_DECISION: で Opus に戻す。
- 終わったら commit（最後の行は `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）→ `git log -1` で確かめる → `git push origin release/ai-roster-s1-secretary` → `git log origin/release/ai-roster-s1-secretary -1` で確かめる。PR は作らない。

## 合格の基準（手元の Opus が確かめる）
| 基準 | 確かめ方 |
|---|---|
| 容器へ担当表の model が届き、容器は既定のモデルを持たない | CI の pytest で 4-3 ①、node の試験で ⑦・⑧ が PASSED。`git grep -n '"sonnet"' -- secretary-agent/server.mjs` が0行 |
| 担当が読めない時は 503 not_ready・容器も台帳も呼ばない | CI の pytest で 4-3 ② が PASSED |
| 1回の頼みで台帳が1行（ok か failed）・error_code は決まりどおり | CI の pytest で 4-3 ③〜⑥・5-4 が PASSED |
| 読む関数が本物の担当表を読み、行が無ければ例外 | CI の DB の試験で 6 が PASSED（SKIPPED でないこと） |
| 使用量画面に「チャット秘書」と出る | CI の vitest で 9-4 が PASSED |
| 今の秘書の動きが変わらない | CI の pytest で今の `test_assistant_router.py` の試験、node の試験で今の試験がすべて通る |
| 本番で秘書を1回呼ぶと台帳に1行 | 反映の後、読み取りの道で `purpose = 'secretary_intent'` の行が1つ増え、`sdk = 'claude-code'`・`model = 'sonnet'`・`outcome = 'ok'`（design.md §7 の秘1 の行） |
| 差分が12ファイルとカードだけ | `git diff origin/main...HEAD --name-only` |

## 報告の型
- 1行目: 受領確認。2行目: 「本報告はカード 秘1 の実行結果である」。
- 本文: 0-1〜0-7 の生出力、「10. 確かめ方」の生出力、commit と push の後の git log の出力（すべて全文）。
- 止まった時: 止まった所（節の番号）・最後に実行したコマンド・止まった理由。
- 最終行: DONE / BLOCKED: / NEEDS_DECISION: のどれか1つで始める。

END OF CARD
