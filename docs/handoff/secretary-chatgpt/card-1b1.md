# 実装カード 1b-1: Gemini の呼び出しの失敗も使用の記録に1行残す（解析 v102・旧エンジン・翻訳）

設計者: Opus（2026-11-03）。設計: `docs/handoff/secretary-chatgpt/design.md` §4-2-1・§4-2-3・§7 の段1b-1・§10。決定: `docs/adr/ADR-1058-ai-job-assignments.md`（2026-11-03 PO が「この設計で決める」に「1」。2026-11-03 PO が「画面ができるまで審査と本番反映まで進める」に「1」。2026-11-03 PO が「失敗も記録に残す段の作業指示書を今から作る。本番に出すのは明日の確認に合格してから」に「1」）。
本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
担当: Sonnet（クラウド）。PR は作らない（手元の Opus が作る）。
読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md・guards/03-file.md・guards/05-pr.md（照合: 場所は行番号ではなく前後の文字で決める／commit と push の後は git log で確かめる／PR はクラウドで作らない）。

## 受領確認
着手前に、作業場所のブランチが `release/ai-roster-1b1-failure-rows` で、HEAD に `docs/handoff/secretary-chatgpt/card-1b1.md` があることを報告の1行目に書く。

## カード発行前チェック（design-partner.md §5.5）
- 1 記号: パス・SQL・値・関数名はすべてバッククォートで囲んだ ○
- 2 下書き禁止: PR はクラウドで作らない。手元の Opus が ready で作る ○
- 3 報告の宛先: 完了報告の本文に生出力を全文含める、と書いた ○
- 4 1便1目的: Gemini の3経路の失敗の行を書くことと、その試験だけ。担当表を読む処理・固定のモデル名を消すこと・秘書・容器・画面・一覧の照合（purpose・sdk・provider・job_key）は入れない（段1b-2） ○
- 5 起点: ブランチ `release/ai-roster-1b1-failure-rows` は手元の Opus が origin/main 起点で作って渡す ○
- 6 書式の実例: PR 本文は手元の Opus が書くので載せない（該当なし） ○
- 7 合格基準: ruff の出力の文言・main との差分のファイルの一覧・削除行の数まで書いた。DB の試験の PASSED は CI で手元の Opus が確かめる ○
- 8 名前を出す: 差分の数が違う時は、そのファイルの削除行を出す手順を対にした ○
- 9 出力の上限: 一覧は `grep` と `head` で絞る ○
- 10 報告の型: 冒頭に「本報告はカード 1b-1 の実行結果である」、止まった時は節の番号・最後のコマンド・理由、最終行は DONE / BLOCKED: / NEEDS_DECISION: ○
- 11 期待値: 場所は前後の文字で決める。数は実物から数える ○

## なぜ（短く）
段1a で使用の記録 `public.llm_usage_events` に `outcome`（`ok`/`failed`）と `error_code`（9つ）の列が入り、段1a-2 で集計は `outcome = 'ok'` だけを数えるようにした。今は Gemini の呼び出しが例外で終わると何も残らないので、後で作る「AI の担当」画面で「最後の失敗」「鍵切れ」が出せない。1回の API の呼び出しが例外で終わったら、その経路の書き手が `outcome='failed'` の行を1行書く。API を呼んでいない失敗（鍵が無い・時間切れの打ち切り等）は書かない。モデル名は今の固定値のまま（担当表から読むのは段1b-2）。

## 禁止（名指し）
- 下の「触るファイル」の11個以外を変えない。`migrations/`・`scripts/`・`frontend/`・`secretary-agent/`・`.github/`・`deploy.yml`・compose は変えない。
- `backend/app/routers/assistant.py`（秘書）は変えない（段1b-2）。
- `_classify_error`・`_safe_error_message`・`_HTTP_STATUS_RE`（`backend/app/services/gemini_extraction_svc.py`）の中身は変えない（今の解析の記録 `validation_result` の `category` の値を変えないため）。
- 成功の行の書き方（`record_usage_event_sync`・`record_usage_event`・`_INSERT_USAGE_EVENT_SQL`・v102 の `_record_usage`・翻訳の3か所の `record_usage_event`）は変えない。
- 送り直しの判定（`_is_transient_http`・`_IMMEDIATE_RETRY_DELAYS`・`_IMMEDIATE_RETRY_BUDGET_SECONDS`）と `recorder.record_error_detail` の呼び方は変えない。
- 今ある試験は書き換えない・消さない（足すだけ）。
- 本番に繋がない。本番の鍵を使わない。VPS に入らない。
- PR を作らない・マージしない。GO 記録を書かない。`/review` を実行しない。rebase・force push をしない。`git stash` を使わない。`rm -rf` を使わない。
- 全部の試験を流さない。使い捨ての PostgreSQL・venv を作らない（DB の試験は GitHub の CI で回る）。
- 試験のファイル（`.py`）を書く・直すときは、Write と Edit の道具だけを使う。Bash の python やヒアドキュメントで書き換えない。試験の共有の道具には使い捨て DB を消す後始末の文があり、Bash の命令に入るとクラウドの見張りが止めるため。Bash の命令の文にもその語を書かない。
- 例外の本文・鍵・使用量の中身をログに出さない（ログは種類だけ）。
- 見張り（フック）に止められたら、言い換えて同じことをしない。そこで止まる。

## 触るファイル（この11個だけ。ほかに docs/ のこのカード）
1. `backend/app/services/llm_budget.py`
2. `backend/app/services/gemini_raw_copy_v8.py`
3. `backend/app/services/line_analysis_v102_svc.py`
4. `backend/app/services/gemini_extraction_svc.py`
5. `backend/app/services/tcg_extraction_record_svc.py`
6. `backend/app/services/message_translator.py`
7. `backend/tests/test_llm_usage_failure_rows.py`（新しいファイル。DB 不要）
8. `backend/tests/test_llm_usage_failure_rows_pg.py`（新しいファイル。本物の DB）
9. `backend/tests/test_line_analysis_v102_pg.py`（3本足す）
10. `backend/tests/test_tcg_extraction_record_pg.py`（3本足す）
11. `backend/tests/test_gemini_raw_copy_v8.py`（1本足す）

## 0. 着手前の確かめ（読むだけ。前提が違えば NEEDS_DECISION で止まる）
- 0-1 `git show origin/main:migrations/20261103_120000_create_ai_job_assignments.sql | grep -n "error_code"` で、`llm_usage_events_error_code_check` の9つの値が `'auth_failed', 'timeout', 'rate_limited', 'http_error', 'unreadable', 'tool_used', 'not_ready', 'busy', 'other'` であること。
- 0-2 `grep -n "20261103_120000_create_ai_job_assignments.sql" backend/tests/test_tcg_work_matching_integration.py` が1行（共有の試験 DB に段1a の列がある）。
- 0-3 `git grep -n "def record_error_detail\|def on_response" -- backend/app` が `backend/app/services/tcg_extraction_record_svc.py` の2行だけ（旧エンジンの recorder の型は1つだけ）。
- 0-4 `git grep -n "ledger_api_called\|ledger_outcome\|record_usage_failure_sync\|record_usage_isolated\|gemini_ledger_error_code" -- backend` が0行。
- 0-5 `grep -n "def _classify_error" -A9 backend/app/services/gemini_extraction_svc.py` の返す値が `gemini_rate_limit`・`gemini_http_error`・`gemini_timeout`・`gemini_unknown` の4つだけ。
- 0-6 `grep -n "_call_gemini(" backend/app/services/message_translator.py` が、定義1行と呼び出し3行（受信・取り直し・送信）。

## 1. `backend/app/services/llm_budget.py`
- 1-1 `_INSERT_USAGE_EVENT_SQL = """` の塊の閉じ `"""` の次（空行2つ）に足す:
```python
# ADR-1058 段1b-1: 失敗の行（outcome='failed'）と、別の取引で書く行の INSERT。outcome・error_code の列を含む。
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


_LEDGER_AUTH_HTTP_CODES = frozenset({401, 403})
_LEDGER_AUTH_STATUS_NAMES = ("API_KEY_INVALID", "PERMISSION_DENIED")
_LEDGER_CLASSIFY_TO_ERROR_CODE = {
    "gemini_rate_limit": "rate_limited",
    "gemini_http_error": "http_error",
    "gemini_timeout": "timeout",
    "gemini_unknown": "other",
}
_LEDGER_CAUSE_MAX_DEPTH = 5


def gemini_ledger_error_code(exc: BaseException) -> str:
    """Gemini の呼び出しの例外を、使用の記録の error_code にする（台帳だけに使う。design.md §4-2-1）。

    ① 例外とその __cause__ の鎖（最大5段・輪は止める）に HTTP 401・403、または状態名 API_KEY_INVALID・
       PERMISSION_DENIED があれば auth_failed。
    ② それ以外は今ある分け方 _classify_error の値を写す。
    """
    # gemini_extraction_svc は頭でこのモジュールを読むので、頭で読むと循環になる。関数の中で読む。
    from app.services.gemini_extraction_svc import _HTTP_STATUS_RE, _classify_error

    seen: set[int] = set()
    current: BaseException | None = exc
    depth = 0
    while current is not None and depth < _LEDGER_CAUSE_MAX_DEPTH and id(current) not in seen:
        seen.add(id(current))
        code = getattr(current, "code", None)
        if isinstance(code, int) and code in _LEDGER_AUTH_HTTP_CODES:
            return "auth_failed"
        message = str(current)
        if any(name in message for name in _LEDGER_AUTH_STATUS_NAMES):
            return "auth_failed"
        if {int(m) for m in _HTTP_STATUS_RE.findall(message)} & _LEDGER_AUTH_HTTP_CODES:
            return "auth_failed"
        current = current.__cause__
        depth += 1
    return _LEDGER_CLASSIFY_TO_ERROR_CODE.get(_classify_error(exc), "other")
```
- 1-2 `async def record_usage_event(` の関数の終わり（`    return cols["id"]` の次）に、空行2つを置いて足す:
```python
def record_usage_failure_sync(
    session: Session,
    *,
    purpose: str,
    model: str,
    sdk: str,
    error_code: str,
    tenant_id: int | None = None,
    extraction_attempt_id: str | None = None,
    source_ref: str | None = None,
) -> str:
    """API を呼んで例外で終わった1回を、failed の行で INSERT する（sync Session 版、呼び出し元の取引の中）。

    使用量は分からないので全部 NULL・費用も NULL。commit しない（呼び出し元が commit する）。
    自分では例外を飲み込まない（record_usage_event_sync と同じ）。戻り値は生成した id。
    """
    cols = _usage_event_columns(
        purpose=purpose,
        model=model,
        sdk=sdk,
        counts=UsageCounts(),
        tenant_id=tenant_id,
        extraction_attempt_id=extraction_attempt_id,
        extraction_shadow_run_id=None,
        discord_inbound_message_id=None,
        source_ref=source_ref,
    )
    cols.update(_outcome_columns("failed", error_code))
    session.execute(text(_INSERT_USAGE_EVENT_OUTCOME_SQL), cols)
    return cols["id"]


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
- 1-3 `__all__` に5つ足す（今の並びはアルファベット順。その順に入れる）: `"USAGE_ERROR_CODES"`・`"USAGE_OUTCOMES"`・`"gemini_ledger_error_code"`・`"record_usage_failure_sync"`・`"record_usage_isolated"`。
- ほかの行は変えない。`Any`・`Session`・`text`・`logger` は今のファイルの頭にある（0 で無ければ止まる）。

## 2. `backend/app/services/gemini_raw_copy_v8.py`
API の呼び出しの except を、次の前後で変える。
- 前:
```python
    except Exception as exc:
        raise RuntimeError(f"Gemini v8 API 呼び出し失敗: {_gem._safe_error_message(exc)}") from exc
```
- 後:
```python
    except Exception as exc:
        wrapped = RuntimeError(f"Gemini v8 API 呼び出し失敗: {_gem._safe_error_message(exc)}")
        # ADR-1058 段1b-1: API を呼んで失敗した印。v102 の層がこの印のある例外だけ使用の記録に failed の行を書く。
        # 例外の型に無い属性なので setattr で付ける（mypy の attr-defined を出さない）。
        setattr(wrapped, "ledger_api_called", True)
        raise wrapped from exc
```
- `except SoftTimeLimitExceeded: raise` と try の外の `client = _gem._get_genai_client()` は変えない（印を付けない）。

## 3. `backend/app/services/line_analysis_v102_svc.py`
- 3-1 import の `from app.services.llm_budget import record_usage_event_sync` を `from app.services.llm_budget import gemini_ledger_error_code, record_usage_event_sync, record_usage_failure_sync` にする（今の行の形が違えば、名前だけ足す）。
- 3-2 `def _record_usage(` の関数の後ろ（空行2つ）に足す:
```python
def _record_usage_failure(session: Session, exc: BaseException, extraction_job_id: str, attempt_id: str | None) -> None:
    """API を呼んで例外で終わった1回を、llm_usage_events に failed の1行で書く（ADR-1058 段1b-1）。台帳の失敗で抽出を止めない。"""
    try:
        record_usage_failure_sync(
            session,
            purpose=_LEDGER_PURPOSE,
            model=_GEMINI_MODEL,
            sdk=_LEDGER_SDK,
            error_code=gemini_ledger_error_code(exc),
            source_ref=f"{_SOURCE_REF_PREFIX}{extraction_job_id}",
            extraction_attempt_id=attempt_id,
        )
        session.commit()
    except Exception:  # noqa: BLE001
        session.rollback()
        logger.exception("[line_analysis] 失敗の記録を台帳に書けませんでした: job=%s", extraction_job_id)
```
- 3-3 `def _call_gemini(session: Session, ctx, prompt_text: str, extraction_job_id: str, recorder) -> dict:` の中の `        except Exception as exc:` の次の行（`            if (` の前）に足す:
```python
            # ADR-1058 段1b-1: API を呼んで失敗した1回ごとに failed の行を1つ（送り直す前も、最後に投げる前も）。
            # 印の無い例外は API を呼んでいないので書かない。
            if getattr(exc, "ledger_api_called", False):
                _record_usage_failure(session, exc, extraction_job_id, recorder.id if recorder is not None else None)
```
- `except SoftTimeLimitExceeded:` の順番・送り直しの判定・`if recorder is None: raise`・`recorder.record_error_detail(...)` は変えない。

## 4. `backend/app/services/gemini_extraction_svc.py`
`call_gemini_extraction` の API の呼び出しの except を、次の前後で変える（足すのは注記1行と呼び出し1行だけ。`record_error_detail` の後ろに置き、判定が万一上げても今の記録を先に済ませる）。
- 前:
```python
            detail = _safe_error_message(exc)
            recorder.record_error_detail({"raw": detail, "category": _classify_error(exc)})
            raise RecordError("API_ERROR") from None
```
- 後:
```python
            detail = _safe_error_message(exc)
            recorder.record_error_detail({"raw": detail, "category": _classify_error(exc)})
            # ADR-1058 段1b-1: API を呼んで失敗した印。recorder.fail が使用の記録に failed の行を1行書く。
            recorder.mark_api_failed(llm_budget.gemini_ledger_error_code(exc))
            raise RecordError("API_ERROR") from None
```

## 5. `backend/app/services/tcg_extraction_record_svc.py`
- 5-1 import の `from app.services.llm_budget import UsageCounts, record_usage_event_sync` を `from app.services.llm_budget import UsageCounts, record_usage_event_sync, record_usage_failure_sync` にする。
- 5-2 `__init__` の `        self._usage_counts: UsageCounts | None = None` の次の行に足す:
```python
        self._api_failed_code: str | None = None  # ADR-1058 段1b-1: API を呼んで例外で終わった時の error_code
```
- 5-3 `    def record_error_detail(self, detail: dict) -> None:` の直前（空行1つを挟む）にメソッドを足す:
```python
    def mark_api_failed(self, error_code: str) -> None:
        """API を呼んで例外で終わった印（ADR-1058 段1b-1）。fail() が応答の無い失敗を台帳に1行書くのに使う。"""
        self._api_failed_code = error_code

```
- 5-4 `fail` の中の台帳の塊を、次の前後で変える。
  - 前:
```python
                # ADR-1004: 応答を受け取れていた（usage_counts あり）失敗のみ台帳に1行書く。
                # 応答が無い失敗（呼び出し自体の例外）は usage 不明のため書かない。
                if self._usage_counts is not None and self._requested_model:
                    record_usage_event_sync(
                        self.session,
                        purpose="line_extraction",
                        model=self._requested_model,
                        sdk="google-genai",
                        counts=self._usage_counts,
                        extraction_attempt_id=self.id,
                    )
```
  - 後:
```python
                # ADR-1004 / ADR-1058 段1b-1: 台帳の行は1つだけ。応答を受け取れていれば ok の行、
                # 応答が無く API を呼んで例外で終わった印があれば failed の行。どちらでもなければ書かない。
                # 台帳の INSERT だけを SAVEPOINT で囲む。失敗しても SAVEPOINT まで戻し、下の job の UPDATE と commit を進める。
                try:
                    with s.begin_nested():
                        if self._usage_counts is not None and self._requested_model:
                            record_usage_event_sync(
                                self.session,
                                purpose="line_extraction",
                                model=self._requested_model,
                                sdk="google-genai",
                                counts=self._usage_counts,
                                extraction_attempt_id=self.id,
                            )
                        elif self._api_failed_code is not None and self._requested_model:
                            record_usage_failure_sync(
                                self.session,
                                purpose="line_extraction",
                                model=self._requested_model,
                                sdk="google-genai",
                                error_code=self._api_failed_code,
                                extraction_attempt_id=self.id,
                            )
                except Exception:  # noqa: BLE001
                    logger.error("extraction_attempt=%s code=LEDGER_WRITE_FAILED", self.id)
```
- `except Exception:` は `with` の外に置く（中で飲み込むと RELEASE SAVEPOINT が失敗して全部が巻き戻る。design.md §4-2-3）。`complete` は変えない。

## 6. `backend/app/services/message_translator.py`
- 6-1 llm_budget の import に `gemini_ledger_error_code`・`record_usage_isolated` を足す（今の並びの順に入れる）。
- 6-2 `async def _call_gemini(` の直前（空行2つ）に足す:
```python
def _mark_ledger(exc: Exception, *, outcome: str, error_code: str | None, counts: UsageCounts) -> None:
    """呼び出しの結果を例外に印として付ける（ADR-1058 段1b-1）。台帳の行は呼び出し元の except が書く。"""
    # 例外の型に無い属性なので setattr / getattr で扱う（mypy の attr-defined を出さない）。
    setattr(exc, "ledger_outcome", outcome)
    setattr(exc, "ledger_error_code", error_code)
    setattr(exc, "ledger_counts", counts)


async def _record_call_error(
    exc: BaseException,
    *,
    purpose: str,
    model: str,
    tenant_id: int,
    source_ref: str | None,
) -> None:
    """印のある例外だけ、別の取引で使用の記録に1行書く（呼び出し元の取引は例外で巻き戻るため。design.md §4-2-3）。"""
    outcome = getattr(exc, "ledger_outcome", None)
    if outcome is None:
        return
    await record_usage_isolated(
        purpose=purpose,
        model=model,
        sdk="google-generativeai",
        counts=getattr(exc, "ledger_counts"),
        outcome=outcome,
        error_code=getattr(exc, "ledger_error_code"),
        tenant_id=tenant_id,
        source_ref=source_ref,
    )
```
- 6-3 `_call_gemini` の except と後ろを、次の前後で変える。
  - 前:
```python
    except Exception as exc:
        logger.exception("[message_translator] Gemini call failed (model=%s): %s", model_name, _safe_error_message(exc))
        raise LLMParseError(f"Gemini API 呼び出し失敗: {exc}") from exc

    text_payload = getattr(response, "text", "") or ""
    if not text_payload:
        raise LLMParseError("Gemini 応答が空でした")

    usage = getattr(response, "usage_metadata", None)
    counts = usage_counts_from(usage)
    input_tokens = counts.prompt_tokens or 0
```
  - 後:
```python
    except Exception as exc:
        logger.exception("[message_translator] Gemini call failed (model=%s): %s", model_name, _safe_error_message(exc))
        err = LLMParseError(f"Gemini API 呼び出し失敗: {exc}")
        _mark_ledger(err, outcome="failed", error_code=gemini_ledger_error_code(exc), counts=UsageCounts())
        raise err from exc

    # ADR-1058 段1b-1: 空の応答も API は応答を返している（ok の行）。使用量は空の判定より前に読む。
    usage = getattr(response, "usage_metadata", None)
    counts = usage_counts_from(usage)
    text_payload = getattr(response, "text", "") or ""
    if not text_payload:
        err = LLMParseError("Gemini 応答が空でした")
        _mark_ledger(err, outcome="ok", error_code=None, counts=counts)
        raise err

    input_tokens = counts.prompt_tokens or 0
```
- 6-4 呼び出し3か所を、それぞれ `_call_gemini(...)` の1行だけを try で囲む形にする（後ろの `record_cost`・`record_usage_event` は try の外のまま）。
  - 受信: `    response_text, in_tokens, out_tokens, counts = await _call_gemini(prompt, model)` の後に `record_usage_event(` で `purpose="translation_inbound"` が続く所:
```python
    try:
        response_text, in_tokens, out_tokens, counts = await _call_gemini(prompt, model)
    except Exception as exc:
        await _record_call_error(
            exc, purpose="translation_inbound", model=model, tenant_id=tenant_id, source_ref=message_id
        )
        raise
```
  - 取り直し: `            resp2, in2, out2, counts2 = await _call_gemini(prompt2, MODEL_SEND)`:
```python
            try:
                resp2, in2, out2, counts2 = await _call_gemini(prompt2, MODEL_SEND)
            except Exception as exc:
                await _record_call_error(
                    exc,
                    purpose="translation_inbound_escalation",
                    model=MODEL_SEND,
                    tenant_id=tenant_id,
                    source_ref=message_id,
                )
                raise
```
  - 送信: `generate_outbound_draft` の中の `    response_text, in_tokens, out_tokens, counts = await _call_gemini(prompt, model)`:
```python
    try:
        response_text, in_tokens, out_tokens, counts = await _call_gemini(prompt, model)
    except Exception as exc:
        await _record_call_error(
            exc,
            purpose="translation_outbound",
            model=model,
            tenant_id=tenant_id,
            source_ref=str(lead_id) if lead_id is not None else None,
        )
        raise
```
- 既知の穴（直さない・報告にも書かない）: `response.text` の読み取り自体が例外を上げた時は今と同じ動き（印が無いので行は出ない）。

## 7. 試験 `backend/tests/test_llm_usage_failure_rows.py`（新しいファイル。DB 不要）
- 7-1 `USAGE_ERROR_CODES` が9つで、0-1 の9つと同じ集合。
- 7-2 `_classify_error` の4つの値すべてが写る: 例外の文 `"429 RESOURCE_EXHAUSTED"`→`rate_limited`、`"500 INTERNAL"`→`http_error`、`"Deadline exceeded"`→`timeout`、`"boom"`→`other`（parametrize）。加えて `_LEDGER_CLASSIFY_TO_ERROR_CODE` の値がすべて `USAGE_ERROR_CODES` に入っていること。
- 7-3 auth_failed（parametrize）: `"401 UNAUTHENTICATED"`・`"403 PERMISSION_DENIED"`・`"400 INVALID_ARGUMENT. {'error': {'details': [{'reason': 'API_KEY_INVALID'}]}}"`、文は `"x"` で属性 `code = 403` を持つ例外。
- 7-4 鎖: `RuntimeError("Gemini v8 API 呼び出し失敗: リクエストエラー (HTTP 400)")` の `__cause__` が API_KEY_INVALID を含む例外 → `auth_failed`。6段目に API_KEY_INVALID がある鎖（外の5つの文は `"boom"`）→ `other`。2つの例外が互いを `__cause__` にした輪（文は `"boom"`）→ 止まって `other`。
- 7-5 `record_usage_failure_sync`: MagicMock の session で呼び、`session.execute` の2つ目の引数が `outcome == "failed"`・`error_code == "auth_failed"`・`cost_usd is None`・`prompt_tokens is None`。SQL の文に `outcome` を含む。`error_code="nope"` は `ValueError`。`session.commit` は呼ばれない。
- 7-6 `record_usage_isolated`: `app.database.AsyncSessionLocal` を、`execute`・`commit` が AsyncMock の偽のセッションを返す async の context manager の工場に差し替える。①呼ぶと execute が1回・commit が1回、引数の `outcome`・`error_code` が渡した値 ②execute が例外を上げると、例外は外に出ず commit は呼ばれない ③`outcome="ok", error_code="timeout"` は外に出ず execute も呼ばれない。
- 7-7 v102 の送り直しの輪（`from tests.test_api_error_auto_retry import EJ, _Env`）: `svc.record_usage_failure_sync` を MagicMock に差し替える。印の付いた例外の作り方は v8 と同じ（`RuntimeError("503 Service Unavailable")` に `ledger_api_called = True`）。①印あり 503・印あり 503・成功 → 差し替えが2回呼ばれ、2回とも `error_code == "http_error"`・`source_ref == f"extraction_job:{EJ}"`・`purpose == "line_extraction"`。`session.commit` は3回（呼ぶ前の1回＋失敗の行2回）。②印の無い 503 を3回 → 差し替えは0回（`RecordError` が上がる）。
- 7-8 旧エンジンの recorder（`tests/test_tcg_extraction_record_svc_usage_ledger.py` の `_recorder` の作りを写す。import して使ってよい）: `records.record_usage_failure_sync` と `records.record_usage_event_sync` を差し替え、①`mark_api_failed("auth_failed")` → `fail("API_ERROR")` → failure が1回（`error_code == "auth_failed"`・`extraction_attempt_id == recorder.id`・`model == "gemini-3.1-flash-lite"`）、event は0回 ②`on_response(...)` の後に `mark_api_failed("timeout")` → `fail` → event が1回・failure は0回 ③印なしで `fail` → どちらも0回。
- 7-9 翻訳（`tests/test_message_translator_usage_ledger.py` の差し替えの組を写す。`record_usage_isolated` は `app.services.message_translator.record_usage_isolated` を AsyncMock に差し替える）:
  - ① 受信で `generate_content_async.side_effect = Exception("403 PERMISSION_DENIED")`（`genai = _install_fake_genai(...)`、`genai.GenerativeModel.return_value.generate_content_async`）→ `translate_inbound` が `LLMParseError` を上げ、差し替えが1回、`purpose == "translation_inbound"`・`outcome == "failed"`・`error_code == "auth_failed"`・`source_ref` が message_id・`tenant_id == 1`・`counts.prompt_tokens is None`。`record_usage_event` は0回。
  - ② 受信で空の応答（`_make_gemini_json_response(...)` の `text` を `""` にする）→ 差し替えが1回、`outcome == "ok"`・`error_code is None`・`counts.prompt_tokens == 100`。
  - ③ 送信で①と同じ例外 → `purpose == "translation_outbound"`・`source_ref == str(lead_id)`。
  - ④ `_ensure_api_key` が `RuntimeError` を上げる → 差し替えは0回（印が無い）。

## 8. 試験（本物の DB。クラウドでは流さない）
- 8-1 `backend/tests/test_line_analysis_v102_pg.py` に3本足す（今の `v102` fixture・`make_job`・`one`・`run_extraction` を使う）。行は `SELECT outcome, error_code, cost_usd, model FROM public.llm_usage_events WHERE source_ref = %s ORDER BY occurred_at, id`（`source_ref` は `f"extraction_job:{job}"`）で読む。`run_extraction` が例外を上げるかどうかは実物に合わせる（上げるなら `pytest.raises(Exception)` で包む。判定は行で行う）。
  - (a) `test_api_key_invalid_inside_v8_writes_failed_auth_row`: `monkeypatch.setattr(svc, "call_gemini_raw_copy_v8", gemini_raw_copy_v8.call_gemini_raw_copy_v8)`（本物に戻す）と、`gemini_extraction_svc._get_genai_client` を、`models.generate_content` が `Exception("400 INVALID_ARGUMENT. {'error': {'code': 400, 'message': 'API key not valid.', 'status': 'INVALID_ARGUMENT', 'details': [{'reason': 'API_KEY_INVALID'}]}}")` を上げる偽に差し替える → 行が1つで `("failed", "auth_failed", None, svc._GEMINI_MODEL)`。本物の v8 が API の前の別の理由で落ちる時は止まって NEEDS_DECISION（ほかを差し替えて通さない）。
  - (b) `test_retried_api_failures_write_one_failed_row_each`: `svc.time.sleep` を何もしない関数に差し替え、偽の Gemini が印あり `RuntimeError("503 Service Unavailable")` を2回上げた後に今の fixture と同じ成功の値を返す → failed（`http_error`）が2行・ok が1行。
  - (c) `test_unmarked_exception_writes_no_ledger_row`: 偽の Gemini が印の無い `RuntimeError("架空")` を上げる → 行が0。
- 8-2 `backend/tests/test_tcg_extraction_record_pg.py` に3本足す（今の `seed_products`・`source`・`fake_model`・`run`・`rows` を使う。旧エンジンの道）。行は `SELECT outcome, error_code, extraction_attempt_id FROM public.llm_usage_events WHERE extraction_attempt_id = %s` で、試行の id は `rows(pg, jid)` の `id`。
  - (a) `test_api_failure_writes_one_failed_row`: `action` が `RuntimeError("403 PERMISSION_DENIED")` を上げる → 行が1つで outcome `failed`・error_code `auth_failed`。
  - (b) `test_soft_time_limit_writes_no_ledger_row`: `action` が `SoftTimeLimitExceeded()` → 行が0。
  - (c) `test_ledger_insert_failure_still_marks_job_error`: 先に `pg[0]` のカーソルで `ALTER TABLE public.llm_usage_events ADD CONSTRAINT test_no_failed_rows CHECK (outcome <> 'failed')` を流す（`pg[0]` が自動 commit でなければ commit する。DB は試験ごとに作り直される）。(a) と同じ例外 → 行が0、試行の `error_code` が `API_ERROR`、`SELECT status FROM {SCHEMA}.extraction_jobs WHERE id = %s`（jid）が `error`。
- 8-3 新しいファイル `backend/tests/test_llm_usage_failure_rows_pg.py`（共有の `pg` fixture: `from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture`）に1本: `test_error_code_list_matches_db_check`。`SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'llm_usage_events_error_code_check'` の文から `'...'` の値を正規表現で全部取り出し、`USAGE_ERROR_CODES` と同じ集合。

## 9. `backend/tests/test_gemini_raw_copy_v8.py` に1本
`test_call_v8_api_failure_marks_api_called_and_keeps_auth_cause`: 今の `client` fixture と `_call()` を使い、`client.models.generate_content.side_effect = Exception("400 INVALID_ARGUMENT. {'error': {'details': [{'reason': 'API_KEY_INVALID'}]}}")` → `RuntimeError` が上がり、`ledger_api_called is True`、`"API_KEY_INVALID" not in str(err)`（包み直しで状態名が消える前提の確かめ）、`gemini_ledger_error_code(err) == "auth_failed"`。

## 10. 確かめ方
- `uvx ruff check --config backend/pyproject.toml` に「触るファイル」の11個を並べた出力が `All checks passed!`。並びの直しだけを求められたら `--fix` の結果に従う。
- 新しいファイル2つは `uvx ruff format --config backend/pyproject.toml --check` が通る。ほかのファイルは整形し直さない。各ファイルについて `uvx ruff format --config backend/pyproject.toml --diff` の結果の `^@@` の行の数（`grep -c`）を、変える前（origin/main の写し）と変えた後で比べ、増えていないこと（増えたら足した行を直す）。前と後の数を報告に書く。
- mock の試験（DB 不要）だけ流す: `cd backend && uv run --no-project --with-requirements requirements.txt --with pytest --with pytest-asyncio python -m pytest tests/test_llm_usage_failure_rows.py tests/test_gemini_raw_copy_v8.py tests/test_api_error_auto_retry.py tests/test_tcg_extraction_record_svc_usage_ledger.py tests/test_message_translator.py tests/test_message_translator_usage_ledger.py -q`。この形で依存が入らない時は流さずに「mock の試験はクラウドで流せなかった」と書き、CI に任せる（venv は作らない）。流した時は出力を全文写す。
- DB の試験（8-1〜8-3 と今の `pg` を使う試験）はクラウドでは流さない。報告に「DB の試験はクラウドでは流さず CI に任せた」と書く。流していない試験を合格と書かない。
- `bash scripts/dev/check-before-submit.sh` があれば流し、出力の最後の20行と終了コードを写す（無ければ「無い」と書く）。
- `git diff origin/main...HEAD --name-only` が「触るファイル」の11個と `docs/handoff/secretary-chatgpt/card-1b1.md`・`docs/handoff/secretary-chatgpt/design.md` だけ（ほかがあれば止まる）。
- `git diff origin/main...HEAD --numstat` の削除の数（2列目）が、1 は 0、2 は 1、3 は 1 以下（import の1行）、4 は 0、5 は 12 以下（5-1 の import の1行と 5-4 の前の塊11行。字下げが変わるので全部が削除に数えられる）、6 は 12 以下（6-1 の import・6-3 の前の塊・6-4 の3行）、7〜11 は 0。違えば そのファイルを指定した `git diff origin/main...HEAD --` の `^-` の行（`grep` と `head -30`）を出して止まる。
- 生出力は作業場所の外の一時フォルダに保存し、パスと全文を報告に書く。

## 11. 想定される分岐と止まる条件
- 0 の前提が違う → 止まり、NEEDS_DECISION: で返す（違った所の生出力を付ける）。
- 2〜6 の「前」の文字列が見つからない（カードの前後の文字と違う） → 止まり、NEEDS_DECISION: で返す。
- 7-7 の `_Env` や 7-8 の `_recorder`、7-9 の差し替えの組が今の形で使えない → 同じ作りを新しいファイルの中に写してよい（今のファイルは変えない）。写せない時は止まる。
- 7-7 ① の `session.commit` の回数が3でない → 実物の数を報告に書いて止まる（数を合わせて書き換えない）。
- 8-1 (a) で本物の v8 が API の前に落ちる → 止まり、NEEDS_DECISION: で返す。
- 1-2 の `from app.database import AsyncSessionLocal` が循環の import で落ちる → 止まり、NEEDS_DECISION: で返す。
- カードに無いファイルを触る必要が出た → 止まり、NEEDS_DECISION: で返す。
- 迷ったら停止して NEEDS_DECISION: で Opus に戻す。
- 終わったら commit（最後の行は `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）→ `git log -1` で確かめる → `git push origin release/ai-roster-1b1-failure-rows` → `git log origin/release/ai-roster-1b1-failure-rows -1` で確かめる。PR は作らない。

## 合格の基準（手元の Opus が確かめる）
| 基準 | 確かめ方 |
|---|---|
| API を呼んだ失敗だけが1回1行で残る | CI の pytest で 7・8・9 の試験が PASSED（DB の記録で実行の跡も見る） |
| 鍵切れが auth_failed になる（v102 の包み直しを通っても） | CI の pytest で 8-1 (a)・9・7-4 が PASSED |
| 台帳が書けなくても旧エンジンの job が error になる | CI の pytest で 8-2 (c) が PASSED |
| 今の動きが変わらない | CI の pytest で今の解析・翻訳・送り直しの試験がすべて通る |
| 本番で失敗の行が9つの中・1回で2行出ない | 反映の後、読み取りの道で `outcome='failed'` の行の error_code の種類、旧エンジンの「同じ extraction_attempt_id に ok と failed の両方がある組」0件、v102 の「同じ extraction_attempt_id の failed が4以上」0件（design.md §7 の 1b-1 の行） |
| 差分が11ファイルだけ | `git diff origin/main...HEAD --name-only` |

## 報告の型
- 1行目: 受領確認。2行目: 「本報告はカード 1b-1 の実行結果である」。
- 本文: 0-1〜0-6 の生出力、「10. 確かめ方」の生出力、commit と push の後の git log の出力（すべて全文）。
- 止まった時: 止まった所（節の番号）・最後に実行したコマンド・止まった理由。
- 最終行: DONE / BLOCKED: / NEEDS_DECISION: のどれか1つで始める。

END OF CARD
