# 実装カード 段2: 解析ダッシュボードに「AI の担当」タブと、その API（表示と秘書の切り替え）

設計者: Opus（2026-11-03）。設計: `docs/handoff/secretary-chatgpt/design.md` §4-3・§6・§6-1・§7 の段2・§8 の K3・K4・K7・K9・K10・K11・§10。決定: `docs/adr/ADR-1058-ai-job-assignments.md`（2026-11-03 PO が「この設計で決める」に「1」。2026-11-03 PO が「画面ができるまで審査と本番反映まで進める」に「1」。2026-11-03 PO が「秘書の道を先にして、今日から始める」に「1」。2026-11-03 PO が「秘書の動作の確かめは後にして、画面の段の準備を進める」に「3」）。
本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
担当: Sonnet（クラウド）。PR は作らない（手元の Opus が作る）。
読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md・guards/03-file.md・guards/05-pr.md（照合: 場所は行番号ではなく前後の文字で決める／commit と push の後は git log で確かめる／PR はクラウドで作らない）。

## 受領確認
着手前に、作業場所のブランチが `release/ai-roster-2-screen` で、HEAD に `docs/handoff/secretary-chatgpt/card-2.md` があることを報告の1行目に書く。

## カード発行前チェック（design-partner.md §5.5）
- 1 記号: パス・SQL・値・関数名はすべてバッククォートで囲んだ ○
- 2 下書き禁止: PR はクラウドで作らない。手元の Opus が ready で作る ○
- 3 報告の宛先: 完了報告の本文に生出力を全文含める、と書いた ○
- 4 1便1目的: 担当の画面（表示と、今コードが担当表を読む秘書だけの切り替え）とその API・試験だけ。解析と翻訳のコード（段1b-1・1b-2）・codex の容器と選択肢（段3）・秘書の口 `assistant.py` の中身は入れない ○
- 5 起点: ブランチ `release/ai-roster-2-screen` は手元の Opus が origin/main 起点で作って渡す ○
- 6 書式の実例: PR 本文は手元の Opus が書くので載せない（該当なし） ○
- 7 合格基準: ruff の出力の文言・main との差分のファイルの一覧・削除行の数まで書いた。DB の試験と画面の試験の PASSED は CI で手元の Opus が確かめる ○
- 8 名前を出す: 差分の数が違う時は、そのファイルの削除行を出す手順を対にした ○
- 9 出力の上限: 一覧は `grep` と `head` で絞る ○
- 10 報告の型: 冒頭に「本報告はカード 段2 の実行結果である」、止まった時は節の番号・最後のコマンド・理由、最終行は DONE / BLOCKED: / NEEDS_DECISION: ○
- 11 期待値: 場所は前後の文字で決める。数は実物から数える ○

## なぜ（短く）
段1a で担当表（`public.ai_job_choices`・`public.ai_job_assignments`・`public.ai_job_assignment_history`）が入り、段 秘1 で秘書が担当表からモデルを読むようになった。この便で、スーパー管理者が解析ダッシュボードの新しいタブで、5つの仕事の今の AI・モデル・ログインの○×・使った回数を見られるようにし、秘書の行だけ担当を変えられるようにする。ほかの4つの仕事はまだコードが担当表を読まない（段1b-2 で読む）ので、変えても何も変わらない。そのため画面には「変える」を出さず、API は 409 `not_wired` で断る（design.md §7 の段2）。
なお段2の時点で秘書の選択肢は `('secretary_intent', 'claude', 'sonnet')` の1つだけ（`migrations/20261103_120000_create_ai_job_assignments.sql` の最後の選択肢の行）。ChatGPT の選択肢は段3の migration で足す。

## 禁止（名指し）
- 下の「触るファイル」の13個以外を変えない。`migrations/`・`scripts/`・`.github/`・`deploy.yml`・compose・`secretary-agent/` は変えない。
- `backend/app/routers/assistant.py` は変えない（読むだけ。`SECRETARY_AGENT_URL` を import する）。`assistant.py` の `_SDK_BY_PROVIDER` も変えない（段3でまとめる）。
- 解析と翻訳のコード（`backend/app/services/gemini_extraction_svc.py`・`gemini_raw_copy_v8.py`・`line_analysis_v102_svc.py`・`tcg_extraction_record_svc.py`・`message_translator.py`・`backend/app/tasks/`）は変えない。
- `ai_assignment.py` の今ある `_SELECT_ASSIGNMENT_SQL`・`AiAssignment`・`AiAssignmentMissing`・`get_ai_assignment` の中身は変えない。足すだけ（`__all__` を除く）。
- `llm_budget.py` は 1 の2か所に足すだけ。今ある定数と関数の中身は変えない。
- 担当表と履歴の表の SQL は `backend/app/services/ai_assignment.py` の中だけに置く（design.md §4-3。router に担当表の SQL を書かない）。
- 新しい CSS のファイル・CSS の行を足さない。生の `<select>`・`<input>`・`<button>`・`<table>` を書かない。色・大きさの直値を書かない。画面の文字はすべて `t()` を通す（ADR-144・ADR-067・ADR-027）。
- 今ある試験は書き換えない・消さない（足すだけ）。
- 本番に繋がない。本番の鍵を使わない。VPS に入らない。
- PR を作らない・マージしない。GO 記録を書かない。`/review` を実行しない。rebase・force push をしない。`git stash` を使わない。`rm -rf` を使わない。
- 全部の試験を流さない。使い捨ての PostgreSQL・venv を作らない（DB の試験は GitHub の CI で回る）。
- 試験のファイル（`.py`）を書く・直すときは、Write と Edit の道具だけを使う。Bash の python やヒアドキュメントで書き換えない。DB の試験のファイルには表の行を消す文と使い捨て DB を消す後始末の文があり、Bash の命令に入るとクラウドの見張りが止めるため。Bash の命令の文にもその語を書かない。
- 鍵の値・メールを画面・返事・ログに出さない（K4）。
- 見張り（フック）に止められたら、言い換えて同じことをしない。そこで止まる。

## 触るファイル（この13個だけ。ほかに docs/ のこのカード）
1. `backend/app/services/llm_budget.py`
2. `backend/app/services/ai_assignment.py`
3. backend/app/routers/super_admin_ai_jobs.py（新しいファイル）
4. `backend/app/main.py`
5. `backend/app/realtime/topics.py`
6. backend/tests/test_super_admin_ai_jobs.py（新しいファイル。DB 不要）
7. `backend/tests/ops/test_ai_job_assignments_db.py`（2本足す。本物の DB）
8. frontend/src/pages/super-admin/components/AiJobsSection.tsx（新しいファイル）
9. frontend/src/pages/super-admin/components/AiJobsSection.test.tsx（新しいファイル）
10. `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx`
11. `frontend/src/pages/super-admin/components/LlmUsageSection.tsx`（関数1つに `export` を付けるだけ）
12. `frontend/src/locales/ja.json`
13. `frontend/src/locales/en.json`

## 0. 着手前の確かめ（読むだけ。前提が違えば NEEDS_DECISION で止まる）
- 0-1 `grep -n "def get_ai_assignment\|^__all__" backend/app/services/ai_assignment.py` が2行で、`__all__` の行が `__all__ = ["AiAssignment", "AiAssignmentMissing", "get_ai_assignment"]`。
- 0-2 `git grep -n "SWITCHABLE_JOB_KEYS\|USAGE_SDKS_BY_PROVIDER\|super_admin_ai_jobs\|AiJobsSection\|aiJobs\|tabAi" -- backend frontend/src` が0行。
- 0-3 `test -e backend/app/routers/super_admin_ai_jobs.py; echo $?`・`test -e backend/tests/test_super_admin_ai_jobs.py; echo $?`・`test -e frontend/src/pages/super-admin/components/AiJobsSection.tsx; echo $?` がどれも `1`。
- 0-4 `grep -n '^USAGE_SDKS: frozenset\[str\] = frozenset({"google-genai", "google-generativeai", "codex-cli", "claude-code"})$' backend/app/services/llm_budget.py` が1行。`grep -n '^    "USAGE_SDKS",$' backend/app/services/llm_budget.py` が1行。
- 0-5 `grep -n '^SECRETARY_AGENT_URL = ' backend/app/routers/assistant.py` が1行。
- 0-6 `grep -n '    super_admin_link_templates,  # SA-05\|    super_admin_aliases,$\|^    super_admin_llm_budget.router, prefix="/api/v1", tags=\["super-admin"\],$' backend/app/main.py` が3行。
- 0-7 `grep -n '("POST", "/api/v1/super-admin/aliases"): _PENDING,' backend/app/realtime/topics.py` が1行。
- 0-8 `grep -n 'type DashboardTab = "import" | "extraction" | "analysis" | "distribution" | "usage";\|{ key: "usage", label: t("analysisRules.dashboard.tabUsage") },\|{activeTab === "usage" && <LlmUsageSection days={trendDays} t={t} />}\|^import { LlmUsageSection } from "./LlmUsageSection";' frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx` が4行。
- 0-9 `grep -n '^function formatFetchedAtJst(isoString: string, language: string): string {' frontend/src/pages/super-admin/components/LlmUsageSection.tsx` が1行。
- 0-10 `grep -n '^      "tabUsage": ' frontend/src/locales/ja.json frontend/src/locales/en.json` が各1行（`"使用量",`・`"Usage",`）。
- 0-11 `grep -n "('secretary_intent', 'claude', 'sonnet')" migrations/20261103_120000_create_ai_job_assignments.sql` が1行。`grep -n "updated_by INTEGER NULL REFERENCES public.users(id) ON DELETE SET NULL\|updated_at TIMESTAMPTZ NOT NULL DEFAULT now()" migrations/20261103_120000_create_ai_job_assignments.sql` が2行。
- 0-12 `grep -n "^security = HTTPBearer()$" backend/app/auth/dependencies.py` が1行。`grep -n "^fastapi==" backend/requirements.txt` の版を報告に書く。
- 0-13 `grep -n "def test_f_get_ai_assignment_reads_choice_and_raises_when_missing" backend/tests/ops/test_ai_job_assignments_db.py` が1行で、それがファイルの最後の試験（`grep -c "^def test_" backend/tests/ops/test_ai_job_assignments_db.py` の数を報告に書く）。

## 1. `backend/app/services/llm_budget.py`
1-1 前（1行）:
```python
USAGE_SDKS: frozenset[str] = frozenset({"google-genai", "google-generativeai", "codex-cli", "claude-code"})
```
後（この行はそのまま、すぐ下に足す）:
```python
USAGE_SDKS: frozenset[str] = frozenset({"google-genai", "google-generativeai", "codex-cli", "claude-code"})

# ADR-1058 段2: 担当表の provider → 使用の記録の sdk の集合（design.md §6 の①）。
# 画面のログインの○×と回数はこの対応で `sdk = ANY(:sdks)` を引く。対応はここ1か所だけ。
USAGE_SDKS_BY_PROVIDER: dict[str, frozenset[str]] = {
    "gemini": frozenset({"google-genai", "google-generativeai"}),
    "codex": frozenset({"codex-cli"}),
    "claude": frozenset({"claude-code"}),
}
```
1-2 `__all__` の `    "USAGE_SDKS",` の行のすぐ下に `    "USAGE_SDKS_BY_PROVIDER",` を1行足す。

## 2. `backend/app/services/ai_assignment.py`
2-1 先頭の説明文の最後の行 `app.database は読まない（読むとエンジンを作るため。セッションは呼び手から受け取る）。` のすぐ下（閉じの `"""` の前）に1行足す:
```
段2: 画面の一覧・切り替え・変えた記録もここに置く（担当表の SQL はこのファイルだけ）。確定（commit）は呼び手がする。
```
2-2 前（ファイルの最後の行）:
```python
__all__ = ["AiAssignment", "AiAssignmentMissing", "get_ai_assignment"]
```
後（`get_ai_assignment` の関数の後、`__all__` の前に下を足し、`__all__` を置き換える）:
```python
# ---------------------------------------------------------------------------
# 段2: 画面（design.md §6・§6-1）
# ---------------------------------------------------------------------------

# 今コードが担当表を読む仕事（design.md §7 の段2）。1b-2 で5つ全部が読むようになったら、
# この定数と画面の switchable の欄と PUT の 409 not_wired を消す。
SWITCHABLE_JOB_KEYS: frozenset[str] = frozenset({"secretary_intent"})

_LIST_ASSIGNMENTS_SQL = """
    SELECT a.job_key, a.choice_id, c.provider, c.model
    FROM public.ai_job_assignments a
    JOIN public.ai_job_choices c ON c.id = a.choice_id AND c.job_key = a.job_key
    ORDER BY a.job_key
"""

_LIST_CHOICES_SQL = """
    SELECT id, job_key, provider, model
    FROM public.ai_job_choices
    ORDER BY job_key, id
"""

_LOCK_ASSIGNMENT_SQL = """
    SELECT choice_id
    FROM public.ai_job_assignments
    WHERE job_key = :job_key
    FOR UPDATE
"""

_CHOICE_OF_JOB_SQL = """
    SELECT 1
    FROM public.ai_job_choices
    WHERE id = :choice_id AND job_key = :job_key
"""

_UPDATE_ASSIGNMENT_SQL = """
    UPDATE public.ai_job_assignments
    SET choice_id = :choice_id, updated_by = :user_id, updated_at = now()
    WHERE job_key = :job_key
"""

_INSERT_HISTORY_SQL = """
    INSERT INTO public.ai_job_assignment_history (job_key, old_choice_id, new_choice_id, changed_by)
    VALUES (:job_key, :old_choice_id, :new_choice_id, :user_id)
"""

_LIST_HISTORY_SQL = """
    SELECT h.job_key,
           oc.provider AS old_provider, oc.model AS old_model,
           nc.provider AS new_provider, nc.model AS new_model,
           u.full_name AS changed_by_name, h.changed_by AS changed_by_id, h.changed_at
    FROM public.ai_job_assignment_history h
    JOIN public.ai_job_choices nc ON nc.id = h.new_choice_id
    LEFT JOIN public.ai_job_choices oc ON oc.id = h.old_choice_id
    LEFT JOIN public.users u ON u.id = h.changed_by
    ORDER BY h.changed_at DESC, h.id DESC
    LIMIT :limit
"""


class AiChoice(NamedTuple):
    choice_id: int
    provider: str
    model: str


class AiJobRow(NamedTuple):
    job_key: str
    choice_id: int
    provider: str
    model: str
    choices: tuple[AiChoice, ...]


class AiJobHistoryRow(NamedTuple):
    job_key: str
    old_provider: str | None
    old_model: str | None
    new_provider: str
    new_model: str
    changed_by_name: str | None
    changed_by_id: int | None
    changed_at: datetime


class AiJobNotFound(LookupError):
    """担当表に job_key の行が無い（5つの仕事の外）。画面の API は 404 not_found。"""


class AiJobNotWired(Exception):
    """job_key は5つの中だが、今のコードが担当表を読まない仕事。画面の API は 409 not_wired。"""


class AiChoiceMismatch(ValueError):
    """choice_id がその job_key の選択肢ではない。画面の API は 422 choice_mismatch。"""


async def list_ai_jobs(db: AsyncSession) -> list[AiJobRow]:
    """担当表の全行（今の担当と、その仕事の選択肢）を job_key の順に返す。仕事の一覧はここから作る。"""
    choices: dict[str, list[AiChoice]] = {}
    for row in (await db.execute(text(_LIST_CHOICES_SQL))).all():
        choices.setdefault(row[1], []).append(AiChoice(choice_id=row[0], provider=row[2], model=row[3]))
    return [
        AiJobRow(
            job_key=row[0],
            choice_id=row[1],
            provider=row[2],
            model=row[3],
            choices=tuple(choices.get(row[0], [])),
        )
        for row in (await db.execute(text(_LIST_ASSIGNMENTS_SQL))).all()
    ]


async def change_ai_assignment(db: AsyncSession, job_key: str, choice_id: int, user_id: int | None) -> bool:
    """担当を変え、履歴を1行書く（同じ取引。確定は呼び手）。変えた時 True、今と同じ choice_id なら何も書かず False。

    判定の順は 404 → 409 → 422 で、どれも書き込みより前（design.md §6-1）。
    今の行を FOR UPDATE で押さえてから old_choice_id を読む（2人が同時に変えても履歴の old がずれない）。
    """
    current = (await db.execute(text(_LOCK_ASSIGNMENT_SQL), {"job_key": job_key})).first()
    if current is None:
        raise AiJobNotFound(job_key)
    if job_key not in SWITCHABLE_JOB_KEYS:
        raise AiJobNotWired(job_key)
    found = (await db.execute(text(_CHOICE_OF_JOB_SQL), {"choice_id": choice_id, "job_key": job_key})).first()
    if found is None:
        raise AiChoiceMismatch(choice_id)
    old_choice_id = current[0]
    if old_choice_id == choice_id:
        return False
    params = {"job_key": job_key, "choice_id": choice_id, "user_id": user_id}
    await db.execute(text(_UPDATE_ASSIGNMENT_SQL), params)
    await db.execute(
        text(_INSERT_HISTORY_SQL),
        {"job_key": job_key, "old_choice_id": old_choice_id, "new_choice_id": choice_id, "user_id": user_id},
    )
    return True


async def list_ai_job_history(db: AsyncSession, limit: int) -> list[AiJobHistoryRow]:
    """変えた記録を新しい順に limit 件。名前は users.full_name だけ（メール・username は読まない。K4）。"""
    rows = (await db.execute(text(_LIST_HISTORY_SQL), {"limit": limit})).all()
    return [AiJobHistoryRow(*row) for row in rows]


__all__ = [
    "SWITCHABLE_JOB_KEYS",
    "AiAssignment",
    "AiAssignmentMissing",
    "AiChoice",
    "AiChoiceMismatch",
    "AiJobHistoryRow",
    "AiJobNotFound",
    "AiJobNotWired",
    "AiJobRow",
    "change_ai_assignment",
    "get_ai_assignment",
    "list_ai_job_history",
    "list_ai_jobs",
]
```
2-3 import に `from datetime import datetime` を足す（`from typing import NamedTuple` の上。並びは ruff の `I` に従う）。

## 3. backend/app/routers/super_admin_ai_jobs.py（新しいファイル。中身はこのとおり）
```python
"""ADR-1058 段2: AI の担当の画面の API（スーパー管理だけ）。design.md §6・§6-1。

担当表の読み書きは app.services.ai_assignment の1か所（design.md §4-3）。ここは使用の記録
（public.llm_usage_events）からログインの○×と回数を足して返すだけ。鍵の値・メールは返さない（K4）。
"""

from __future__ import annotations

import os
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.models import User
from app.routers.assistant import SECRETARY_AGENT_URL
from app.services.ai_assignment import (
    SWITCHABLE_JOB_KEYS,
    AiChoiceMismatch,
    AiJobNotFound,
    AiJobNotWired,
    AiJobRow,
    change_ai_assignment,
    list_ai_job_history,
    list_ai_jobs,
)
from app.services.llm_budget import USAGE_SDKS_BY_PROVIDER

router = APIRouter()

# 秘書の容器の /health を待つ上限（design.md §6-1。GET 全体が容器を待って遅くならないように）
HEALTH_TIMEOUT_SECONDS = 2.0
_SECRETARY_JOB_KEY = "secretary_intent"

# 1つの仕事の使用の記録の集計（purpose＝job_key・今の provider の sdk の集合。design.md §6 の①・§6-1 の数え方）
_USAGE_STATS_SQL = """
    SELECT
        (SELECT max(e.occurred_at) FROM public.llm_usage_events e
          WHERE e.purpose = :job_key AND e.sdk = ANY(:sdks) AND e.outcome = 'ok') AS last_ok_at,
        (SELECT count(*) FROM public.llm_usage_events e
          WHERE e.purpose = :job_key AND e.sdk = ANY(:sdks) AND e.outcome = 'ok'
            AND e.occurred_at >= now() - interval '24 hours') AS count_24h,
        (SELECT count(*) FROM public.llm_usage_events e
          WHERE e.purpose = :job_key AND e.sdk = ANY(:sdks) AND e.outcome = 'failed'
            AND e.occurred_at >= now() - interval '24 hours') AS failed_24h,
        (SELECT e.error_code FROM public.llm_usage_events e
          WHERE e.purpose = :job_key AND e.sdk = ANY(:sdks)
          ORDER BY e.occurred_at DESC, e.id DESC LIMIT 1) AS newest_error_code,
        (SELECT e.error_code FROM public.llm_usage_events e
          WHERE e.purpose = :job_key AND e.sdk = ANY(:sdks) AND e.outcome = 'failed'
          ORDER BY e.occurred_at DESC, e.id DESC LIMIT 1) AS last_error_code,
        (SELECT max(e.occurred_at) FROM public.llm_usage_events e
          WHERE e.purpose = :job_key AND e.sdk = ANY(:sdks) AND e.outcome = 'failed') AS last_error_at
"""


class AiChoiceOut(BaseModel):
    choice_id: int
    provider: str
    model: str


class AiJobOut(BaseModel):
    job_key: str
    provider: str
    model: str
    choice_id: int
    choices: list[AiChoiceOut]
    login_ok: bool
    login_reason: str | None
    last_ok_at: datetime | None
    count_24h: int
    failed_24h: int
    last_error_code: str | None
    last_error_at: datetime | None
    login_refreshed_at: datetime | None
    switchable: bool


class AiJobsOut(BaseModel):
    jobs: list[AiJobOut]


class AiJobChangeIn(BaseModel):
    choice_id: int


class AiProviderModel(BaseModel):
    provider: str
    model: str


class AiJobHistoryItem(BaseModel):
    job_key: str
    old: AiProviderModel | None
    new: AiProviderModel
    changed_by_name: str | None
    changed_by_id: int | None
    changed_at: datetime


class AiJobHistoryOut(BaseModel):
    items: list[AiJobHistoryItem]


def _login_state(
    provider: str,
    newest_error_code: str | None,
    gemini_key_present: bool,
    agent_ready: bool | None,
) -> tuple[bool, str | None]:
    """ログインの○×と理由（design.md §6 の①②③。どれかで ×。理由の優先は auth_failed > key_missing > not_ready）。

    agent_ready は秘書の行だけ真偽、ほかの行は None（容器を見ない）。
    """
    if newest_error_code == "auth_failed":
        return False, "auth_failed"
    if provider == "gemini" and not gemini_key_present:
        return False, "key_missing"
    if agent_ready is False:
        return False, "not_ready"
    return True, None


def _gemini_key_present() -> bool:
    """Gemini の鍵が環境にあるかどうかだけを見る（値は読まない・返さない。K4）。"""
    return bool(os.getenv("GEMINI_API_KEY", "").strip())


async def _secretary_agent_ready() -> bool:
    """秘書の容器の /health が 2 秒以内に ready=true を返せば True。返らない・届かない・形が違えば False。"""
    try:
        async with httpx.AsyncClient(timeout=HEALTH_TIMEOUT_SECONDS) as client:
            res = await client.get(f"{SECRETARY_AGENT_URL}/health")
        return res.status_code == 200 and res.json().get("ready") is True
    except (httpx.HTTPError, ValueError, AttributeError):
        return False


async def _agent_ready_for(job: AiJobRow) -> bool | None:
    """秘書の行だけ容器を見る。段2では容器があるのは claude だけなので、ほかの provider は not_ready。"""
    if job.job_key != _SECRETARY_JOB_KEY:
        return None
    if job.provider != "claude":
        return False
    return await _secretary_agent_ready()


async def _usage_stats(db: AsyncSession, job_key: str, provider: str) -> dict:
    sdks = sorted(USAGE_SDKS_BY_PROVIDER.get(provider, frozenset()))
    row = (await db.execute(text(_USAGE_STATS_SQL), {"job_key": job_key, "sdks": sdks})).mappings().one()
    return dict(row)


async def _job_out(db: AsyncSession, job: AiJobRow, gemini_key_present: bool) -> AiJobOut:
    stats = await _usage_stats(db, job.job_key, job.provider)
    agent_ready = await _agent_ready_for(job)
    login_ok, login_reason = _login_state(job.provider, stats["newest_error_code"], gemini_key_present, agent_ready)
    return AiJobOut(
        job_key=job.job_key,
        provider=job.provider,
        model=job.model,
        choice_id=job.choice_id,
        choices=[AiChoiceOut(choice_id=c.choice_id, provider=c.provider, model=c.model) for c in job.choices],
        login_ok=login_ok,
        login_reason=login_reason,
        last_ok_at=stats["last_ok_at"],
        count_24h=int(stats["count_24h"] or 0),
        failed_24h=int(stats["failed_24h"] or 0),
        last_error_code=stats["last_error_code"],
        last_error_at=stats["last_error_at"],
        # 段2ではいつも null（codex のログインの更新日は段3で入れる）
        login_refreshed_at=None,
        switchable=job.job_key in SWITCHABLE_JOB_KEYS,
    )


@router.get("/super-admin/ai-jobs", response_model=AiJobsOut)
async def get_ai_jobs(
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> AiJobsOut:
    gemini_key_present = _gemini_key_present()
    jobs = await list_ai_jobs(db)
    return AiJobsOut(jobs=[await _job_out(db, job, gemini_key_present) for job in jobs])


@router.get("/super-admin/ai-jobs/history", response_model=AiJobHistoryOut)
async def get_ai_job_history(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> AiJobHistoryOut:
    rows = await list_ai_job_history(db, limit)
    return AiJobHistoryOut(
        items=[
            AiJobHistoryItem(
                job_key=r.job_key,
                old=(
                    AiProviderModel(provider=r.old_provider, model=r.old_model)
                    if r.old_provider is not None and r.old_model is not None
                    else None
                ),
                new=AiProviderModel(provider=r.new_provider, model=r.new_model),
                changed_by_name=r.changed_by_name,
                changed_by_id=r.changed_by_id,
                changed_at=r.changed_at,
            )
            for r in rows
        ]
    )


@router.put("/super-admin/ai-jobs/{job_key}", response_model=AiJobOut)
async def put_ai_job(
    job_key: str,
    body: AiJobChangeIn,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> AiJobOut:
    try:
        await change_ai_assignment(db, job_key, body.choice_id, current_user.id)
    except AiJobNotFound:
        raise HTTPException(status_code=404, detail={"code": "not_found"}) from None
    except AiJobNotWired:
        raise HTTPException(status_code=409, detail={"code": "not_wired"}) from None
    except AiChoiceMismatch:
        raise HTTPException(status_code=422, detail={"code": "choice_mismatch"}) from None
    await db.commit()
    gemini_key_present = _gemini_key_present()
    for job in await list_ai_jobs(db):
        if job.job_key == job_key:
            return await _job_out(db, job, gemini_key_present)
    raise HTTPException(status_code=404, detail={"code": "not_found"})
```

## 4. `backend/app/main.py`
4-1 import の一覧で、前（1行）:
```python
    super_admin_aliases,
```
後（すぐ上に1行足す）:
```python
    super_admin_ai_jobs,  # ADR-1058 段2: AI の担当の画面
    super_admin_aliases,
```
4-2 前（3行）:
```python
app.include_router(
    super_admin_llm_budget.router, prefix="/api/v1", tags=["super-admin"],
)
```
後（この3行はそのまま、すぐ下に足す）:
```python
app.include_router(
    super_admin_llm_budget.router, prefix="/api/v1", tags=["super-admin"],
)
# ADR-1058 段2: AI の担当（public.ai_job_assignments）の画面の API
app.include_router(
    super_admin_ai_jobs.router, prefix="/api/v1", tags=["super-admin"],
)
```

## 5. `backend/app/realtime/topics.py`
前（1行）:
```python
    ("POST", "/api/v1/super-admin/aliases"): _PENDING,
```
後（すぐ上に1行足す。前例の llm-budget の PUT と同じ `_PENDING`。design.md §6-1）:
```python
    ("PUT", "/api/v1/super-admin/ai-jobs/{job_key}"): _PENDING,
    ("POST", "/api/v1/super-admin/aliases"): _PENDING,
```

## 6. backend/tests/test_super_admin_ai_jobs.py（新しいファイル。DB 不要。中身はこのとおり）
```python
"""ADR-1058 段2: AI の担当の画面の API の試験（DB 不要。担当表の読み書きは差し替える）。

K10（スーパー管理だけ）・判定の順 404 → 409 → 422・K11（switchable）・ログインの○×・K4（鍵とメールが出ない）。
本物の DB での切り替えと履歴（K9）は tests/ops/test_ai_job_assignments_db.py。
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import User
from app.routers import super_admin_ai_jobs as mod
from app.services.ai_assignment import (
    AiChoice,
    AiChoiceMismatch,
    AiJobHistoryRow,
    AiJobNotFound,
    AiJobNotWired,
    AiJobRow,
)
from app.services.llm_budget import USAGE_SDKS, USAGE_SDKS_BY_PROVIDER

_JOB_KEYS = [
    "line_extraction",
    "secretary_intent",
    "translation_inbound",
    "translation_inbound_escalation",
    "translation_outbound",
]

_FAKE_GEMINI_KEY = "AIza" + "x" * 35

_K4_PATTERNS = [
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"eyJ[A-Za-z0-9_-]{10,}\."),
    re.compile(r"refresh_token"),
    re.compile(r"access_token"),
]


class _FakeDb:
    def __init__(self):
        self.commit = AsyncMock()


def _user(*, super_admin: bool, role: str) -> User:
    """role は試験の読みやすさのための名前だけ（User に role の列は無い。判定は is_super_admin だけ）。"""
    return User(
        id=7,
        tenant_id=1,
        username=f"u7-{role}",
        email="u7@example.test",
        full_name="担当者",
        is_super_admin=super_admin,
    )


def _app(db: _FakeDb, user: User | None) -> FastAPI:
    app = FastAPI()
    app.include_router(mod.router, prefix="/api/v1")

    async def _db():
        yield db

    app.dependency_overrides[get_db] = _db
    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user
    return app


def _client(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


def _jobs() -> list[AiJobRow]:
    rows = []
    for i, key in enumerate(_JOB_KEYS, start=1):
        if key == "secretary_intent":
            rows.append(AiJobRow(key, i, "claude", "sonnet", (AiChoice(i, "claude", "sonnet"),)))
        else:
            rows.append(AiJobRow(key, i, "gemini", "gemini-3.1-flash-lite", (AiChoice(i, "gemini", "gemini-3.1-flash-lite"),)))
    return rows


def _stats(**over) -> dict:
    base = {
        "last_ok_at": None,
        "count_24h": 0,
        "failed_24h": 0,
        "newest_error_code": None,
        "last_error_code": None,
        "last_error_at": None,
    }
    base.update(over)
    return base


@pytest.fixture()
def wired(monkeypatch):
    """担当表の読み書き・使用の記録・容器の /health を差し替える。"""
    monkeypatch.setenv("GEMINI_API_KEY", _FAKE_GEMINI_KEY)
    monkeypatch.setattr(mod, "list_ai_jobs", AsyncMock(return_value=_jobs()))
    monkeypatch.setattr(mod, "_usage_stats", AsyncMock(return_value=_stats()))
    monkeypatch.setattr(mod, "_secretary_agent_ready", AsyncMock(return_value=True))
    change = AsyncMock(return_value=True)
    monkeypatch.setattr(mod, "change_ai_assignment", change)
    history = AsyncMock(
        return_value=[
            AiJobHistoryRow(
                "secretary_intent", "claude", "sonnet", "claude", "sonnet", "担当者", 7,
                datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc),
            )
        ]
    )
    monkeypatch.setattr(mod, "list_ai_job_history", history)
    return {"change": change, "history": history}


# --- K10: スーパー管理だけ ---------------------------------------------------------


@pytest.mark.asyncio
async def test_k10_tenant_admin_gets_403(wired):
    db = _FakeDb()
    async with _client(_app(db, _user(super_admin=False, role="admin"))) as c:
        r = await c.put("/api/v1/super-admin/ai-jobs/secretary_intent", json={"choice_id": 1})
    assert r.status_code == 403, r.text
    wired["change"].assert_not_awaited()


@pytest.mark.asyncio
async def test_k10_general_user_gets_403(wired):
    db = _FakeDb()
    async with _client(_app(db, _user(super_admin=False, role="staff"))) as c:
        r = await c.put("/api/v1/super-admin/ai-jobs/secretary_intent", json={"choice_id": 1})
    assert r.status_code == 403, r.text
    wired["change"].assert_not_awaited()


@pytest.mark.asyncio
async def test_k10_no_login_gets_401(wired):
    db = _FakeDb()
    async with _client(_app(db, None)) as c:
        r = await c.put("/api/v1/super-admin/ai-jobs/secretary_intent", json={"choice_id": 1})
    assert r.status_code == 401, r.text
    wired["change"].assert_not_awaited()


@pytest.mark.asyncio
async def test_get_routes_are_super_admin_only(wired):
    db = _FakeDb()
    async with _client(_app(db, _user(super_admin=False, role="admin"))) as c:
        r1 = await c.get("/api/v1/super-admin/ai-jobs")
        r2 = await c.get("/api/v1/super-admin/ai-jobs/history")
    assert (r1.status_code, r2.status_code) == (403, 403)


# --- PUT の失敗の返事（判定の順は本物の DB の試験で見る） -----------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("exc", "status", "code"),
    [
        (AiJobNotFound("nope"), 404, "not_found"),
        (AiJobNotWired("line_extraction"), 409, "not_wired"),
        (AiChoiceMismatch(99), 422, "choice_mismatch"),
    ],
)
async def test_put_errors_have_code_and_do_not_commit(wired, exc, status, code):
    wired["change"].side_effect = exc
    db = _FakeDb()
    async with _client(_app(db, _user(super_admin=True, role="admin"))) as c:
        r = await c.put("/api/v1/super-admin/ai-jobs/secretary_intent", json={"choice_id": 1})
    assert r.status_code == status, r.text
    assert r.json() == {"detail": {"code": code}}
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_put_success_commits_and_returns_get_row_shape(wired):
    db = _FakeDb()
    async with _client(_app(db, _user(super_admin=True, role="admin"))) as c:
        put = await c.put("/api/v1/super-admin/ai-jobs/secretary_intent", json={"choice_id": 2})
        got = await c.get("/api/v1/super-admin/ai-jobs")
    assert put.status_code == 200, put.text
    wired["change"].assert_awaited_once_with(db, "secretary_intent", 2, 7)
    db.commit.assert_awaited_once()
    row = next(j for j in got.json()["jobs"] if j["job_key"] == "secretary_intent")
    assert set(put.json()) == set(row)
    assert put.json()["job_key"] == "secretary_intent"


# --- K11: switchable ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_k11_only_secretary_is_switchable(wired):
    db = _FakeDb()
    async with _client(_app(db, _user(super_admin=True, role="admin"))) as c:
        r = await c.get("/api/v1/super-admin/ai-jobs")
    assert r.status_code == 200, r.text
    jobs = r.json()["jobs"]
    assert sorted(j["job_key"] for j in jobs) == _JOB_KEYS
    assert {j["job_key"]: j["switchable"] for j in jobs} == {k: k == "secretary_intent" for k in _JOB_KEYS}
    assert all(j["login_refreshed_at"] is None for j in jobs)


# --- ログインの○×（design.md §6 の①②③） ------------------------------------------


@pytest.mark.parametrize(
    ("provider", "newest", "key", "ready", "expected"),
    [
        ("gemini", None, True, None, (True, None)),
        ("gemini", "auth_failed", True, None, (False, "auth_failed")),
        ("gemini", None, False, None, (False, "key_missing")),
        ("gemini", "auth_failed", False, None, (False, "auth_failed")),
        ("gemini", "timeout", True, None, (True, None)),
        ("claude", None, False, True, (True, None)),
        ("claude", None, True, False, (False, "not_ready")),
        ("claude", "auth_failed", True, False, (False, "auth_failed")),
        ("codex", None, False, False, (False, "not_ready")),
    ],
)
def test_login_state(provider, newest, key, ready, expected):
    assert mod._login_state(provider, newest, key, ready) == expected


@pytest.mark.asyncio
async def test_secretary_row_is_not_ready_when_agent_is_down(wired, monkeypatch):
    monkeypatch.setattr(mod, "_secretary_agent_ready", AsyncMock(return_value=False))
    db = _FakeDb()
    async with _client(_app(db, _user(super_admin=True, role="admin"))) as c:
        r = await c.get("/api/v1/super-admin/ai-jobs")
    row = next(j for j in r.json()["jobs"] if j["job_key"] == "secretary_intent")
    assert (row["login_ok"], row["login_reason"]) == (False, "not_ready")


@pytest.mark.asyncio
async def test_gemini_rows_are_key_missing_without_key(wired, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    db = _FakeDb()
    async with _client(_app(db, _user(super_admin=True, role="admin"))) as c:
        r = await c.get("/api/v1/super-admin/ai-jobs")
    rows = [j for j in r.json()["jobs"] if j["provider"] == "gemini"]
    assert len(rows) == 4
    assert all((j["login_ok"], j["login_reason"]) == (False, "key_missing") for j in rows)


@pytest.mark.asyncio
async def test_agent_health_unreachable_is_false(monkeypatch):
    """容器に届かない時は例外を出さず False（2 秒の打ち切りと同じ扱い）。"""
    monkeypatch.setattr(mod, "SECRETARY_AGENT_URL", "http://127.0.0.1:9")
    assert await mod._secretary_agent_ready() is False


def test_usage_sdks_belong_to_exactly_one_provider():
    """USAGE_SDKS のどの値もどれか1つの provider に属する（design.md §6 の①）。"""
    for sdk in USAGE_SDKS:
        owners = [p for p, sdks in USAGE_SDKS_BY_PROVIDER.items() if sdk in sdks]
        assert len(owners) == 1, (sdk, owners)
    assert set().union(*USAGE_SDKS_BY_PROVIDER.values()) == set(USAGE_SDKS)
    assert set(USAGE_SDKS_BY_PROVIDER) == {"gemini", "codex", "claude"}


# --- 履歴 -------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_history_limit_default_and_bounds(wired):
    db = _FakeDb()
    async with _client(_app(db, _user(super_admin=True, role="admin"))) as c:
        ok = await c.get("/api/v1/super-admin/ai-jobs/history")
        low = await c.get("/api/v1/super-admin/ai-jobs/history?limit=0")
        high = await c.get("/api/v1/super-admin/ai-jobs/history?limit=201")
    assert ok.status_code == 200, ok.text
    wired["history"].assert_awaited_once_with(db, 50)
    assert (low.status_code, high.status_code) == (422, 422)
    item = ok.json()["items"][0]
    assert item["old"] == {"provider": "claude", "model": "sonnet"}
    assert item["changed_by_name"] == "担当者"
    assert item["changed_by_id"] == 7


# --- K4: 鍵・メールが出ない -------------------------------------------------------------


@pytest.mark.asyncio
async def test_k4_responses_have_no_secret_or_email(wired):
    db = _FakeDb()
    async with _client(_app(db, _user(super_admin=True, role="admin"))) as c:
        jobs = await c.get("/api/v1/super-admin/ai-jobs")
        history = await c.get("/api/v1/super-admin/ai-jobs/history")
    for r in (jobs, history):
        assert r.status_code == 200, r.text
        for pattern in _K4_PATTERNS:
            assert pattern.search(r.text) is None, (pattern.pattern, r.text)
```

## 7. `backend/tests/ops/test_ai_job_assignments_db.py`（ファイルの最後に2本足す。今の行は変えない）
今の最後の試験 `test_f_get_ai_assignment_reads_choice_and_raises_when_missing` の後に、空行2つを置いて下を足す:
```python
def _run_async(db, fn):
    """db の準備で作った DB に asyncpg で繋ぎ、fn(session) を流す（test_f と同じ作り方）。"""
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    url = _psycopg_url(ADMIN_PG_URL, db.info.dbname).replace("postgresql://", "postgresql+asyncpg://", 1)

    async def go():
        eng = create_async_engine(url)
        try:
            async with AsyncSession(eng) as s:
                return await fn(s)
        finally:
            await eng.dispose()

    return asyncio.run(go())


def test_g_change_assignment_k9_and_order(db):
    """段2（K9・判定の順）: 秘書の担当を変えると次の読み取りが新しい model・履歴が1行。
    同じ choice は何も書かない。読まない仕事は 409 相当・別の仕事の choice は 422 相当で、どちらも書かない。
    """
    from app.services.ai_assignment import (
        AiAssignment,
        AiChoiceMismatch,
        AiJobNotFound,
        AiJobNotWired,
        change_ai_assignment,
        get_ai_assignment,
        list_ai_jobs,
    )

    c = db.cursor()
    c.execute(_read(_AI_JOB_SQL))
    c.execute("INSERT INTO public.users (id, email, full_name) VALUES (1002, 'ai-job-g@example.test', '担当G')")
    c.execute("INSERT INTO public.ai_job_choices (job_key, provider, model) VALUES ('secretary_intent', 'claude', 'test-model-g')")
    sonnet_id = _choice_id(db, "secretary_intent", "claude", "sonnet")
    new_id = _choice_id(db, "secretary_intent", "claude", "test-model-g")
    line_id = _choice_id(db, "line_extraction", "gemini", "gemini-3.1-flash-lite")

    async def change(s, job_key, choice_id):
        changed = await change_ai_assignment(s, job_key, choice_id, 1002)
        await s.commit()
        return changed

    assert _run_async(db, lambda s: change(s, "secretary_intent", new_id)) is True
    assert _run_async(db, lambda s: get_ai_assignment(s, "secretary_intent")) == AiAssignment("claude", "test-model-g")
    assert _rows(
        db,
        "SELECT job_key, old_choice_id, new_choice_id, changed_by FROM public.ai_job_assignment_history",
    ) == [("secretary_intent", sonnet_id, new_id, 1002)]
    assert _rows(db, "SELECT updated_by FROM public.ai_job_assignments WHERE job_key = 'secretary_intent'") == [(1002,)]

    # 同じ choice は何も書かない
    assert _run_async(db, lambda s: change(s, "secretary_intent", new_id)) is False
    assert _count(db, "ai_job_assignment_history") == 1

    # 判定の順: 5つの外は 404 → 読まない仕事は（choice が合っていても違っても）409 → 別の仕事の choice は 422
    with pytest.raises(AiJobNotFound):
        _run_async(db, lambda s: change(s, "no_such_job", 999999))
    with pytest.raises(AiJobNotWired):
        _run_async(db, lambda s: change(s, "line_extraction", line_id))
    with pytest.raises(AiJobNotWired):
        _run_async(db, lambda s: change(s, "line_extraction", sonnet_id))
    with pytest.raises(AiChoiceMismatch):
        _run_async(db, lambda s: change(s, "secretary_intent", line_id))
    assert _count(db, "ai_job_assignment_history") == 1
    assert _assignment(db, "line_extraction") == ("gemini", "gemini-3.1-flash-lite")
    assert _assignment(db, "secretary_intent") == ("claude", "test-model-g")

    # 一覧は担当表の5行から作られ、秘書の選択肢は2つ
    jobs = _run_async(db, list_ai_jobs)
    assert [j.job_key for j in jobs] == sorted(_JOB_KEYS)
    secretary = next(j for j in jobs if j.job_key == "secretary_intent")
    assert (secretary.provider, secretary.model, secretary.choice_id) == ("claude", "test-model-g", new_id)
    assert sorted(ch.model for ch in secretary.choices) == ["sonnet", "test-model-g"]


def test_h_history_names_fall_back(db):
    """段2: 変えた記録の名前は full_name。空なら id だけ、その人が消えたら名前も id も None。"""
    from app.services.ai_assignment import change_ai_assignment, list_ai_job_history

    c = db.cursor()
    c.execute(_read(_AI_JOB_SQL))
    c.execute("INSERT INTO public.users (id, email, full_name) VALUES (1003, 'ai-job-h1@example.test', '担当H')")
    c.execute("INSERT INTO public.users (id, email) VALUES (1004, 'ai-job-h2@example.test')")
    c.execute("INSERT INTO public.users (id, email, full_name) VALUES (1005, 'ai-job-h3@example.test', '担当消える')")
    c.execute("INSERT INTO public.ai_job_choices (job_key, provider, model) VALUES ('secretary_intent', 'claude', 'test-model-h')")
    sonnet_id = _choice_id(db, "secretary_intent", "claude", "sonnet")
    new_id = _choice_id(db, "secretary_intent", "claude", "test-model-h")

    async def change(s, choice_id, user_id):
        await change_ai_assignment(s, "secretary_intent", choice_id, user_id)
        await s.commit()

    _run_async(db, lambda s: change(s, new_id, 1003))
    _run_async(db, lambda s: change(s, sonnet_id, 1004))
    _run_async(db, lambda s: change(s, new_id, 1005))
    c.execute("DELETE FROM public.users WHERE id = 1005")

    items = _run_async(db, lambda s: list_ai_job_history(s, 50))
    assert [(i.changed_by_name, i.changed_by_id) for i in items] == [(None, None), (None, 1004), ("担当H", 1003)]
    assert [(i.old_model, i.new_model) for i in items] == [
        ("sonnet", "test-model-h"),
        ("test-model-h", "sonnet"),
        ("sonnet", "test-model-h"),
    ]
    assert len(_run_async(db, lambda s: list_ai_job_history(s, 2))) == 2
```
（`_JOB_KEYS`・`_choice_id`・`_assignment`・`_rows`・`_count`・`_read`・`_AI_JOB_SQL`・`_psycopg_url`・`ADMIN_PG_URL` はこのファイルに今あるものを使う。`_JOB_KEYS` の値が5つの job_key でなければ止まり、NEEDS_DECISION: で返す。）

## 8. frontend/src/pages/super-admin/components/AiJobsSection.tsx（新しいファイル。中身はこのとおり）
```tsx
/**
 * ADR-1058 段2: 解析ダッシュボードの「AI の担当」タブ（design.md §6）。
 * 仕事の一覧は持たない（GET の行をそのまま出す）。切り替えは switchable の行だけ。
 * Modal は1つだけ開き、中を「選ぶ」→「確かめる」の2段で替える（ConfirmModal は使わない）。
 */
import { useCallback, useEffect, useState } from "react";
import i18n from "../../../i18n";
import { api } from "../../../lib/api";
import { Badge } from "../../../components/Badge";
import { Button } from "../../../components/Button";
import { Card } from "../../../components/Card";
import { DataTable } from "../../../components/DataTable";
import type { DataTableColumn } from "../../../components/DataTable";
import { Modal } from "../../../components/Modal";
import { Select } from "../../../components/Select";
import { LoadingBlock } from "../../../components/loading";
import { formatFetchedAtJst } from "./LlmUsageSection";

interface AiChoice {
  choice_id: number;
  provider: string;
  model: string;
}

interface AiJob {
  job_key: string;
  provider: string;
  model: string;
  choice_id: number;
  choices: AiChoice[];
  login_ok: boolean;
  login_reason: string | null;
  last_ok_at: string | null;
  count_24h: number;
  failed_24h: number;
  last_error_code: string | null;
  last_error_at: string | null;
  login_refreshed_at: string | null;
  switchable: boolean;
}

interface AiJobsResponse {
  jobs: AiJob[];
}

interface AiProviderModel {
  provider: string;
  model: string;
}

interface AiJobHistoryItem {
  job_key: string;
  old: AiProviderModel | null;
  new: AiProviderModel;
  changed_by_name: string | null;
  changed_by_id: number | null;
  changed_at: string;
}

interface AiJobHistoryResponse {
  items: AiJobHistoryItem[];
}

type TFn = (key: string, options?: Record<string, unknown>) => string;

export interface AiJobsSectionProps {
  t: TFn;
}

// 値ごとの言葉（キーの有無は AiJobsSection.test.tsx で ja・en とも確かめる）
export function jobLabel(jobKey: string, t: TFn): string {
  return t(`analysisRules.dashboard.aiJobs.job.${jobKey}`, { defaultValue: jobKey });
}

export function providerLabel(provider: string, t: TFn): string {
  return t(`analysisRules.dashboard.aiJobs.provider.${provider}`, { defaultValue: provider });
}

export function errorCodeLabel(code: string, t: TFn): string {
  return t(`analysisRules.dashboard.aiJobs.errorCode.${code}`, { defaultValue: code });
}

export function loginReasonLabel(reason: string, t: TFn): string {
  return t(`analysisRules.dashboard.aiJobs.loginReason.${reason}`, { defaultValue: reason });
}

function choiceLabel(c: AiProviderModel, t: TFn): string {
  return t("analysisRules.dashboard.aiJobs.choiceLabel", { provider: providerLabel(c.provider, t), model: c.model });
}

function formatAt(iso: string | null, t: TFn): string {
  return iso ? formatFetchedAtJst(iso, i18n.language) : t("analysisRules.dashboard.aiJobs.none");
}

function changedByLabel(item: AiJobHistoryItem, t: TFn): string {
  if (item.changed_by_name) return item.changed_by_name;
  if (item.changed_by_id != null) return t("analysisRules.dashboard.aiJobs.userId", { id: item.changed_by_id });
  return t("analysisRules.dashboard.aiJobs.unknownUser");
}

export function AiJobsSection({ t }: AiJobsSectionProps) {
  const [jobs, setJobs] = useState<AiJob[]>([]);
  const [history, setHistory] = useState<AiJobHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<AiJob | null>(null);
  const [step, setStep] = useState<"select" | "confirm">("select");
  const [selected, setSelected] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      api.get<AiJobsResponse>("/super-admin/ai-jobs"),
      api.get<AiJobHistoryResponse>("/super-admin/ai-jobs/history?limit=50"),
    ])
      .then(([jobsRes, historyRes]) => {
        setJobs(jobsRes.jobs);
        setHistory(historyRes.items);
      })
      .catch(() => setError(t("analysisRules.dashboard.fetchError")))
      .finally(() => setLoading(false));
  }, [t]);

  useEffect(() => {
    load();
  }, [load]);

  const openChange = (job: AiJob) => {
    setEditing(job);
    setStep("select");
    setSelected(String(job.choice_id));
    setSaveError(null);
  };

  const close = () => {
    if (saving) return;
    setEditing(null);
  };

  const save = () => {
    if (!editing) return;
    setSaving(true);
    setSaveError(null);
    api
      .put<AiJob>(`/super-admin/ai-jobs/${editing.job_key}`, { choice_id: Number(selected) })
      .then(() => {
        setEditing(null);
        load();
      })
      .catch(() => setSaveError(t("analysisRules.dashboard.aiJobs.saveError")))
      .finally(() => setSaving(false));
  };

  if (loading) return <LoadingBlock />;
  if (error) return <p className="analysis-dashboard-error">{error}</p>;

  const jobColumns: DataTableColumn<AiJob>[] = [
    { key: "job_key", header: t("analysisRules.dashboard.aiJobs.colJob"), renderCell: (row) => jobLabel(row.job_key, t) },
    { key: "provider", header: t("analysisRules.dashboard.aiJobs.colProvider"), renderCell: (row) => providerLabel(row.provider, t) },
    { key: "model", header: t("analysisRules.dashboard.aiJobs.colModel"), renderCell: (row) => row.model },
    {
      key: "login_ok",
      header: t("analysisRules.dashboard.aiJobs.colLogin"),
      renderCell: (row) =>
        row.login_ok ? (
          <Badge variant="success" size="sm">{t("analysisRules.dashboard.aiJobs.loginOk")}</Badge>
        ) : (
          <Badge variant="danger" size="sm">
            {row.login_reason ? loginReasonLabel(row.login_reason, t) : t("analysisRules.dashboard.aiJobs.loginNg")}
          </Badge>
        ),
    },
    { key: "last_ok_at", header: t("analysisRules.dashboard.aiJobs.colLastOk"), renderCell: (row) => formatAt(row.last_ok_at, t) },
    { key: "count_24h", header: t("analysisRules.dashboard.aiJobs.colCount24h"), align: "right", renderCell: (row) => String(row.count_24h) },
    { key: "failed_24h", header: t("analysisRules.dashboard.aiJobs.colFailed24h"), align: "right", renderCell: (row) => String(row.failed_24h) },
    {
      key: "last_error_code",
      header: t("analysisRules.dashboard.aiJobs.colLastError"),
      renderCell: (row) =>
        row.last_error_code
          ? t("analysisRules.dashboard.aiJobs.lastErrorWithAt", {
              reason: errorCodeLabel(row.last_error_code, t),
              at: formatAt(row.last_error_at, t),
            })
          : t("analysisRules.dashboard.aiJobs.none"),
    },
    {
      key: "login_refreshed_at",
      header: t("analysisRules.dashboard.aiJobs.colLoginRefreshed"),
      renderCell: (row) => formatAt(row.login_refreshed_at, t),
    },
    {
      key: "switchable",
      header: t("analysisRules.dashboard.aiJobs.colAction"),
      renderCell: (row) =>
        row.switchable ? (
          <Button variant="secondary" size="sm" onClick={() => openChange(row)}>
            {t("analysisRules.dashboard.aiJobs.change")}
          </Button>
        ) : (
          t("analysisRules.dashboard.aiJobs.notSwitchable")
        ),
    },
  ];

  const historyColumns: DataTableColumn<AiJobHistoryItem>[] = [
    { key: "changed_at", header: t("analysisRules.dashboard.aiJobs.colChangedAt"), renderCell: (row) => formatAt(row.changed_at, t) },
    { key: "job_key", header: t("analysisRules.dashboard.aiJobs.colJob"), renderCell: (row) => jobLabel(row.job_key, t) },
    {
      key: "new",
      header: t("analysisRules.dashboard.aiJobs.colFromTo"),
      renderCell: (row) =>
        t("analysisRules.dashboard.aiJobs.fromTo", {
          from: row.old ? choiceLabel(row.old, t) : t("analysisRules.dashboard.aiJobs.none"),
          to: choiceLabel(row.new, t),
        }),
    },
    { key: "changed_by_name", header: t("analysisRules.dashboard.aiJobs.colChangedBy"), renderCell: (row) => changedByLabel(row, t) },
  ];

  const current = editing?.choices.find((c) => c.choice_id === editing.choice_id) ?? null;
  const target = editing?.choices.find((c) => String(c.choice_id) === selected) ?? null;

  return (
    <div className="analysis-dashboard-existing-section">
      <Card variant="container">
        <div className="analysis-dashboard-section-title">{t("analysisRules.dashboard.aiJobs.title")}</div>
        <DataTable columns={jobColumns} data={jobs} rowKey={(row) => row.job_key} emptyState={t("analysisRules.dashboard.aiJobs.none")} />
      </Card>
      <Card variant="container">
        <div className="analysis-dashboard-section-title">{t("analysisRules.dashboard.aiJobs.historyTitle")}</div>
        <DataTable
          columns={historyColumns}
          data={history}
          rowKey={(row) => `${row.job_key}:${row.changed_at}`}
          emptyState={t("analysisRules.dashboard.aiJobs.noHistory")}
        />
      </Card>
      <Modal
        open={editing !== null}
        onClose={close}
        title={editing ? t("analysisRules.dashboard.aiJobs.modalTitle", { job: jobLabel(editing.job_key, t) }) : ""}
        footer={
          step === "select" ? (
            <>
              <Button variant="secondary" onClick={close}>
                {t("analysisRules.dashboard.aiJobs.cancel")}
              </Button>
              <Button variant="primary" onClick={() => setStep("confirm")}>
                {t("analysisRules.dashboard.aiJobs.next")}
              </Button>
            </>
          ) : (
            <>
              <Button variant="secondary" onClick={() => setStep("select")} disabled={saving}>
                {t("analysisRules.dashboard.aiJobs.back")}
              </Button>
              <Button variant="primary" onClick={save} loading={saving}>
                {t("analysisRules.dashboard.aiJobs.change")}
              </Button>
            </>
          )
        }
      >
        {editing && step === "select" && (
          <Select
            label={t("analysisRules.dashboard.aiJobs.selectLabel")}
            options={editing.choices.map((c) => ({ value: String(c.choice_id), label: choiceLabel(c, t) }))}
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
            fullWidth
          />
        )}
        {editing && step === "confirm" && current && target && (
          <p>
            {t("analysisRules.dashboard.aiJobs.confirmText", {
              job: jobLabel(editing.job_key, t),
              from: choiceLabel(current, t),
              to: choiceLabel(target, t),
            })}
          </p>
        )}
        {saveError && <p className="analysis-dashboard-error">{saveError}</p>}
      </Modal>
    </div>
  );
}
```
- `Button` に `disabled` が無い・`Select` の `onChange` の型が合わない等で型の検査が落ちたら、部品の今の引数（`frontend/src/components/Button.tsx`・`Select.tsx`）を読み、合わせる直しだけをしてよい（部品は変えない）。直した所を報告に書く。
- ui の点検（`scripts/check-ui-governance.js`）が `<p>` や `<div className=...>` を止めたら止まり、NEEDS_DECISION: で返す。

## 9. frontend/src/pages/super-admin/components/AiJobsSection.test.tsx（新しいファイル。中身はこのとおり）
```tsx
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../../i18n";
import { api } from "../../../lib/api";
import { AiJobsSection } from "./AiJobsSection";

vi.mock("../../../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn() },
  ApiError: class extends Error {},
}));

const JOB_KEYS = [
  "line_extraction",
  "secretary_intent",
  "translation_inbound",
  "translation_inbound_escalation",
  "translation_outbound",
];
const ERROR_CODES = ["auth_failed", "timeout", "rate_limited", "http_error", "unreadable", "tool_used", "not_ready", "busy", "other"];
const PROVIDERS = ["gemini", "codex", "claude"];
const LOGIN_REASONS = ["auth_failed", "key_missing", "not_ready"];

function job(jobKey: string, over: Record<string, unknown> = {}) {
  const secretary = jobKey === "secretary_intent";
  return {
    job_key: jobKey,
    provider: secretary ? "claude" : "gemini",
    model: secretary ? "sonnet" : "gemini-3.1-flash-lite",
    choice_id: secretary ? 17 : 1,
    choices: secretary
      ? [
          { choice_id: 17, provider: "claude", model: "sonnet" },
          { choice_id: 18, provider: "claude", model: "test-model" },
        ]
      : [{ choice_id: 1, provider: "gemini", model: "gemini-3.1-flash-lite" }],
    login_ok: true,
    login_reason: null,
    last_ok_at: null,
    count_24h: 0,
    failed_24h: 0,
    last_error_code: null,
    last_error_at: null,
    login_refreshed_at: null,
    switchable: secretary,
    ...over,
  };
}

const HISTORY = {
  items: [
    { job_key: "secretary_intent", old: { provider: "claude", model: "sonnet" }, new: { provider: "claude", model: "test-model" }, changed_by_name: "Tanaka", changed_by_id: 7, changed_at: "2026-11-03T03:00:00Z" },
    { job_key: "secretary_intent", old: { provider: "claude", model: "test-model" }, new: { provider: "claude", model: "sonnet" }, changed_by_name: null, changed_by_id: 8, changed_at: "2026-11-03T02:00:00Z" },
    { job_key: "secretary_intent", old: { provider: "claude", model: "sonnet" }, new: { provider: "claude", model: "test-model" }, changed_by_name: null, changed_by_id: null, changed_at: "2026-11-03T01:00:00Z" },
  ],
};

function mockGets(jobs = JOB_KEYS.map((k) => job(k))) {
  vi.mocked(api.get).mockImplementation((path: string) => {
    if (path.startsWith("/super-admin/ai-jobs/history")) return Promise.resolve(HISTORY as never);
    return Promise.resolve({ jobs } as never);
  });
}

const view = () => render(<AiJobsSection t={i18n.t.bind(i18n)} />);

describe("AiJobsSection", () => {
  beforeEach(async () => {
    vi.resetAllMocks();
    await i18n.changeLanguage("en");
  });

  it("shows 5 rows and the change button only on switchable rows (K3・K11)", async () => {
    mockGets();
    view();
    await screen.findByText(i18n.t("analysisRules.dashboard.aiJobs.job.secretary_intent"));
    for (const key of JOB_KEYS) {
      expect(screen.getAllByText(i18n.t(`analysisRules.dashboard.aiJobs.job.${key}`)).length).toBeGreaterThan(0);
    }
    expect(screen.getAllByRole("button", { name: i18n.t("analysisRules.dashboard.aiJobs.change") })).toHaveLength(1);
    expect(screen.getAllByText(i18n.t("analysisRules.dashboard.aiJobs.notSwitchable"))).toHaveLength(4);
  });

  it("shows the login reason when login is not ok", async () => {
    mockGets(JOB_KEYS.map((k) => (k === "line_extraction" ? job(k, { login_ok: false, login_reason: "key_missing" }) : job(k))));
    view();
    expect(await screen.findByText(i18n.t("analysisRules.dashboard.aiJobs.loginReason.key_missing"))).toBeTruthy();
  });

  it("changes the secretary in two steps and sends a numeric choice_id", async () => {
    mockGets();
    vi.mocked(api.put).mockResolvedValue(job("secretary_intent", { choice_id: 18, model: "test-model" }) as never);
    view();
    fireEvent.click(await screen.findByRole("button", { name: i18n.t("analysisRules.dashboard.aiJobs.change") }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText(i18n.t("analysisRules.dashboard.aiJobs.selectLabel")), { target: { value: "18" } });
    fireEvent.click(within(dialog).getByRole("button", { name: i18n.t("analysisRules.dashboard.aiJobs.next") }));
    expect(api.put).not.toHaveBeenCalled();
    fireEvent.click(within(dialog).getByRole("button", { name: i18n.t("analysisRules.dashboard.aiJobs.change") }));
    await waitFor(() => expect(api.put).toHaveBeenCalledWith("/super-admin/ai-jobs/secretary_intent", { choice_id: 18 }));
  });

  it("shows name, ID or unknown for who changed", async () => {
    mockGets();
    view();
    expect(await screen.findByText("Tanaka")).toBeTruthy();
    expect(screen.getByText(i18n.t("analysisRules.dashboard.aiJobs.userId", { id: 8 }))).toBeTruthy();
    expect(screen.getByText(i18n.t("analysisRules.dashboard.aiJobs.unknownUser"))).toBeTruthy();
  });

  it("has ja and en keys for every job, provider, login reason and error code (K7)", () => {
    const keys = [
      ...JOB_KEYS.map((k) => `analysisRules.dashboard.aiJobs.job.${k}`),
      ...PROVIDERS.map((k) => `analysisRules.dashboard.aiJobs.provider.${k}`),
      ...LOGIN_REASONS.map((k) => `analysisRules.dashboard.aiJobs.loginReason.${k}`),
      ...ERROR_CODES.map((k) => `analysisRules.dashboard.aiJobs.errorCode.${k}`),
    ];
    for (const lng of ["ja", "en"]) {
      const missing = keys.filter((k) => !i18n.exists(k, { lng }));
      expect(missing).toEqual([]);
    }
  });
});
```
- `screen.findByRole("dialog")` で Modal が見つからない時は、`frontend/src/components/Modal.tsx` の役割（role）の付け方を読み、試験の探し方だけを直してよい（部品は変えない）。
- 「変える」の数え方: 表の「変える」は秘書の1行だけ。Modal を開いた後は footer にも「変える」が出るので、最初の数えは Modal を開く前にする（上の並びのとおり）。
- 名前の行の探し方が合わない（DataTable が同じ文字を2か所に出す等）時は、`getAllByText(...).length > 0` に直してよい。

## 10. `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx`
10-1 前（1行）:
```tsx
import { LlmUsageSection } from "./LlmUsageSection";
```
後:
```tsx
import { LlmUsageSection } from "./LlmUsageSection";
import { AiJobsSection } from "./AiJobsSection";
```
10-2 前（1行）:
```tsx
type DashboardTab = "import" | "extraction" | "analysis" | "distribution" | "usage";
```
後:
```tsx
type DashboardTab = "import" | "extraction" | "analysis" | "distribution" | "usage" | "ai";
```
10-3 前（1行）:
```tsx
    { key: "usage", label: t("analysisRules.dashboard.tabUsage") },
```
後（すぐ下に1行足す）:
```tsx
    { key: "usage", label: t("analysisRules.dashboard.tabUsage") },
    { key: "ai", label: t("analysisRules.dashboard.tabAi") },
```
10-4 前（1行）:
```tsx
      {activeTab === "usage" && <LlmUsageSection days={trendDays} t={t} />}
```
後（すぐ下に1行足す）:
```tsx
      {activeTab === "usage" && <LlmUsageSection days={trendDays} t={t} />}
      {activeTab === "ai" && <AiJobsSection t={t} />}
```
- `activeTab` を `"usage"` などの文字の一覧で調べている所（例: 期間の選択を出すかどうか）があれば、`grep -n 'activeTab' frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx` の出力を報告に写す。`ai` を足さないと動きが変わる所があれば止まり、NEEDS_DECISION: で返す（自分で足さない）。

## 11. `frontend/src/pages/super-admin/components/LlmUsageSection.tsx`
前（1行）:
```tsx
function formatFetchedAtJst(isoString: string, language: string): string {
```
後:
```tsx
export function formatFetchedAtJst(isoString: string, language: string): string {
```
（日本時間の日時の書き方を1か所にするため。中身は変えない。）

## 12. `frontend/src/locales/ja.json`
前（1行。`analysisRules.dashboard` の中）:
```json
      "tabUsage": "使用量",
```
後（すぐ下に足す）:
```json
      "tabUsage": "使用量",
      "tabAi": "AI の担当",
      "aiJobs": {
        "title": "仕事ごとの AI の担当",
        "historyTitle": "変えた記録",
        "colJob": "仕事",
        "colProvider": "AI",
        "colModel": "モデル",
        "colLogin": "ログイン",
        "colLastOk": "最後にうまく動いた日時",
        "colCount24h": "直近24時間の回数",
        "colFailed24h": "直近24時間の失敗",
        "colLastError": "最後の失敗の理由",
        "colLoginRefreshed": "ChatGPT のログインの更新日",
        "colAction": "切り替え",
        "colChangedAt": "いつ",
        "colChangedBy": "誰が",
        "colFromTo": "何から何へ",
        "loginOk": "ログインできています",
        "loginNg": "ログインできていません",
        "loginReason": {
          "auth_failed": "最後の呼び出しで認証に失敗",
          "key_missing": "鍵が設定されていません",
          "not_ready": "準備ができていません"
        },
        "job": {
          "line_extraction": "LINE の解析",
          "translation_inbound": "受信の翻訳",
          "translation_inbound_escalation": "受信の翻訳（やり直し）",
          "translation_outbound": "送信の翻訳",
          "secretary_intent": "チャット秘書"
        },
        "provider": {
          "gemini": "Gemini",
          "codex": "ChatGPT",
          "claude": "Claude"
        },
        "errorCode": {
          "auth_failed": "認証の失敗",
          "timeout": "時間切れ",
          "rate_limited": "回数の上限",
          "http_error": "通信の失敗",
          "unreadable": "答えが読めない",
          "tool_used": "許していない操作",
          "not_ready": "準備ができていない",
          "busy": "混み合い",
          "other": "その他"
        },
        "choiceLabel": "{{provider}}・{{model}}",
        "lastErrorWithAt": "{{reason}}（{{at}}）",
        "fromTo": "{{from}} → {{to}}",
        "notSwitchable": "まだ切り替えられません",
        "change": "変える",
        "next": "次へ",
        "back": "戻る",
        "cancel": "やめる",
        "modalTitle": "{{job}} の担当を変える",
        "selectLabel": "AI・モデル",
        "confirmText": "{{job}} の担当を {{from}} から {{to}} に変えます。次の呼び出しから効きます。",
        "saveError": "変えられませんでした。もう一度お試しください",
        "none": "—",
        "noHistory": "まだ変えた記録はありません",
        "userId": "ID {{id}}",
        "unknownUser": "ID 不明"
      },
```

## 13. `frontend/src/locales/en.json`
前（1行。`analysisRules.dashboard` の中）:
```json
      "tabUsage": "Usage",
```
後（すぐ下に足す。キーは 12 と同じ集合）:
```json
      "tabUsage": "Usage",
      "tabAi": "AI assignments",
      "aiJobs": {
        "title": "AI assigned to each job",
        "historyTitle": "Change history",
        "colJob": "Job",
        "colProvider": "AI",
        "colModel": "Model",
        "colLogin": "Login",
        "colLastOk": "Last success",
        "colCount24h": "Calls (24h)",
        "colFailed24h": "Failures (24h)",
        "colLastError": "Last failure",
        "colLoginRefreshed": "ChatGPT login refreshed",
        "colAction": "Switch",
        "colChangedAt": "When",
        "colChangedBy": "By",
        "colFromTo": "From → to",
        "loginOk": "Logged in",
        "loginNg": "Not logged in",
        "loginReason": {
          "auth_failed": "Authentication failed on the last call",
          "key_missing": "API key is not set",
          "not_ready": "Not ready"
        },
        "job": {
          "line_extraction": "LINE analysis",
          "translation_inbound": "Inbound translation",
          "translation_inbound_escalation": "Inbound translation (retry)",
          "translation_outbound": "Outbound translation",
          "secretary_intent": "Chat secretary"
        },
        "provider": {
          "gemini": "Gemini",
          "codex": "ChatGPT",
          "claude": "Claude"
        },
        "errorCode": {
          "auth_failed": "Authentication failed",
          "timeout": "Timed out",
          "rate_limited": "Rate limited",
          "http_error": "Connection failed",
          "unreadable": "Unreadable answer",
          "tool_used": "Disallowed action",
          "not_ready": "Not ready",
          "busy": "Busy",
          "other": "Other"
        },
        "choiceLabel": "{{provider}} · {{model}}",
        "lastErrorWithAt": "{{reason}} ({{at}})",
        "fromTo": "{{from}} → {{to}}",
        "notSwitchable": "Cannot be switched yet",
        "change": "Change",
        "next": "Next",
        "back": "Back",
        "cancel": "Cancel",
        "modalTitle": "Change the AI for {{job}}",
        "selectLabel": "AI and model",
        "confirmText": "Change {{job}} from {{from}} to {{to}}. It takes effect from the next call.",
        "saveError": "Could not change it. Please try again",
        "none": "—",
        "noHistory": "No changes yet",
        "userId": "ID {{id}}",
        "unknownUser": "Unknown ID"
      },
```
- 12・13 の後、`node -e 'for (const f of ["frontend/src/locales/ja.json","frontend/src/locales/en.json"]) JSON.parse(require("fs").readFileSync(f,"utf8")); console.log("json ok")'` が `json ok`。

## 14. 確かめ方
- `uvx ruff check --config backend/pyproject.toml backend/app/services/llm_budget.py backend/app/services/ai_assignment.py backend/app/routers/super_admin_ai_jobs.py backend/app/main.py backend/app/realtime/topics.py backend/tests/test_super_admin_ai_jobs.py backend/tests/ops/test_ai_job_assignments_db.py` の出力が `All checks passed!`。並びの直しだけを求められたら `--fix` の結果に従う。
- 新しい2ファイル（router と試験）と `ai_assignment.py` は `uvx ruff format --config backend/pyproject.toml --check` が通る（通らなければ `uvx ruff format` で整えてよい）。`llm_budget.py`・`main.py`・`topics.py`・`test_ai_job_assignments_db.py` は整形し直さない。この4つについて `uvx ruff format --config backend/pyproject.toml --diff` の結果の `^@@` の行の数（`grep -c`）を、変える前（origin/main の写し）と変えた後で比べ、増えていないこと（増えたら足した行を直す）。前と後の数を報告に書く。
- mock の試験（DB 不要）だけ流す: `cd backend && uv run --no-project --with-requirements requirements.txt --with pytest --with pytest-asyncio python -m pytest tests/test_super_admin_ai_jobs.py tests/test_realtime_topics.py -q`。この形で依存が入らない時は流さずに「mock の試験はクラウドで流せなかった」と書き、CI に任せる（venv は作らない）。流した時は出力を全文写す。`test_k10_no_login_gets_401` が 403 で落ちた時は止まり、NEEDS_DECISION: で返す（期待を書き換えない）。
- 画面: `cd frontend && npx vitest run src/pages/super-admin/components/AiJobsSection.test.tsx src/pages/super-admin/components/LlmUsageSection.test.tsx` を試す。依存が無くて流せない時は `npm ci` をしてよい（1回だけ）。それでも流せない時は「画面の試験はクラウドで流せなかった」と書き、CI に任せる。
- 画面の点検（依存が入った時だけ）: `cd frontend && npx tsc --noEmit -p .`・`node scripts/check-i18n-missing-keys.js`・`node scripts/check-css-hardcoded-colors.js`・`node scripts/check-css-hardcoded-values.js`・`npx eslint src/pages/super-admin/components/AiJobsSection.tsx src/pages/super-admin/components/AiJobsSection.test.tsx src/pages/super-admin/components/AnalysisDashboardPanel.tsx`、リポジトリの根で `node scripts/check-ui-governance.js`。それぞれの終了コードと出力の最後の20行を写す（K7）。
- DB の試験（7）はクラウドでは流さない。報告に「DB の試験はクラウドでは流さず CI に任せた」と書く。流していない試験を合格と書かない。
- `bash scripts/dev/check-before-submit.sh` があれば流し、出力の最後の20行と終了コードを写す（無ければ「無い」と書く）。
- `git diff origin/main...HEAD --name-only` が「触るファイル」の13個と `docs/handoff/secretary-chatgpt/card-2.md` だけ（ほかがあれば止まる）。
- `git diff origin/main...HEAD --numstat` の削除の数（2列目）が、1 は 0、2 は 1（`__all__` の1行）、3 は 0、4 は 0、5 は 0、6 は 0、7 は 0、8 は 0、9 は 0、10 は 2（10-1 と 10-3 は足すだけなので 0。10-2 の1行と、10-4 は足すだけなので、合計は 1。説明文の行が変わっていれば 2 以下）、11 は 1、12 は 0、13 は 0。10 が 2 を超える時と、ほかが違う時は、そのファイルを指定した `git diff origin/main...HEAD --` の `^-` の行（`grep` と `head -30`）を出して止まる。
- 生出力は作業場所の外の一時フォルダに保存し、パスと全文を報告に書く。

## 15. 想定される分岐と止まる条件
- 0 の前提が違う → 止まり、NEEDS_DECISION: で返す（違った所の生出力を付ける）。
- 1〜13 の「前」の文字列が見つからない（カードの前後の文字と違う） → 止まり、NEEDS_DECISION: で返す。
- `from app.routers.assistant import SECRETARY_AGENT_URL` が循環の import で落ちる → 止まり、NEEDS_DECISION: で返す（URL を router に写さない）。
- `test_realtime_topics.py` が 5 の1行の後も赤 → 落ちた試験の名前と出力を写して止まる。
- 型の検査（tsc）・ui の点検が止める → 8 の箇条書きの範囲の直しだけをし、それで通らなければ止まる。
- カードに無いファイルを触る必要が出た → 止まり、NEEDS_DECISION: で返す。
- 迷ったら停止して NEEDS_DECISION: で Opus に戻す。
- 終わったら commit（最後の行は `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）→ `git log -1` で確かめる → `git push origin release/ai-roster-2-screen` → `git log origin/release/ai-roster-2-screen -1` で確かめる。PR は作らない。

## 合格の基準（手元の Opus が確かめる）
| 基準 | 確かめ方 |
|---|---|
| K3 画面に5行・各項目 | CI の vitest で 9 の1本目が PASSED。本番の反映後、PO が画面で5行・各列を数える |
| K4 鍵・メールが出ない | CI の pytest で `test_k4_responses_have_no_secret_or_email` が PASSED。本番の反映後、GET の2つの返事を手元の Opus が同じ型で数えて0件 |
| K7 金型・トークン・i18n | 14 の点検が違反0。CI の vitest で 9 の5本目（ja・en のキー）が PASSED |
| K9 切り替えが次の読み取りから効く・履歴が1行 | CI の DB の試験で `test_g_change_assignment_k9_and_order` が PASSED（SKIPPED でないこと） |
| K10 スーパー管理だけ | CI の pytest で `test_k10_*` の3本と `test_get_routes_are_super_admin_only` が PASSED |
| K11 読まない担当は変えられない | CI の pytest で `test_k11_only_secretary_is_switchable`・`test_put_errors_have_code_and_do_not_commit`、DB の試験で `test_g` の 409 の2か所、vitest で 9 の1本目が PASSED。本番の反映後、PO が画面で秘書の行にだけ「変える」があることを見る |
| 判定の順 404 → 409 → 422・同じ choice は書かない | CI の DB の試験で `test_g` が PASSED |
| 変えた記録の名前 | CI の DB の試験で `test_h_history_names_fall_back`、vitest で 9 の4本目が PASSED |
| ログインの○× | CI の pytest で `test_login_state` の9組・`test_secretary_row_is_not_ready_when_agent_is_down`・`test_gemini_rows_are_key_missing_without_key`・`test_agent_health_unreachable_is_false` が PASSED |
| provider→sdk の対応 | CI の pytest で `test_usage_sdks_belong_to_exactly_one_provider` が PASSED |
| 差分が13ファイルとカードだけ | `git diff origin/main...HEAD --name-only` |

## 報告の型
- 1行目: 受領確認。2行目: 「本報告はカード 段2 の実行結果である」。
- 本文: 0-1〜0-13 の生出力、「14. 確かめ方」の生出力、commit と push の後の git log の出力（すべて全文）。
- 止まった時: 止まった所（節の番号）・最後に実行したコマンド・止まった理由。
- 最終行: DONE / BLOCKED: / NEEDS_DECISION: のどれか1つで始める。

END OF CARD
