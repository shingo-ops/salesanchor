# 実装カード 便2b: backend が承認済みの決まりを秘書の容器へ送り、決まり帳の口を足す（画面の見た目は変わらない）

- 設計: [design.md](design.md) §3（大きさ）・§4（表）・§5（手順と口の条件）・§11（R1・R3・R4・R5・R6・上限いっぱい・21 件目）・§12 便2b。ADR: `docs/adr/ADR-1077-secretary-rulebook.md`（Proposed のまま）。前の便: [card-bin1.md](card-bin1.md)（表）・[card-bin2a.md](card-bin2a.md)（容器が `rules` を受け取る）。
- 状態: 手順書の案（Opus 作成・2026-11-13）。設計審査 1 回目 APPROVE（クラウドの審査役 Opus・2026-11-13。低の指摘 1 件＝R1 の決めた人の検査を PG 試験に 1 行足した）。**PO の実装承認はまだ無い。** 承認があるまで実装役に渡さない。
- ブランチ: `release/secretary-rulebook-bin2b`（実装役が origin/main から作る）。PR は作らない（Opus が作る）。危険 PR ではない（`migrations/`・`deploy.yml`・本番 `scripts/` を触らない）。
- 行番号は origin/main e930f1b24（2026-11-13 12:25）で読んだもの。
- 便2b では表（migration）・容器（secretary-agent・secretary-codex）・指示文（prompt.txt）・答えの形（schema.json）・画面の部品を変えない。画面は失敗の言葉を 1 つ足すだけ（決まりが長すぎるときの 413）。決まりが 0 件の会社では、容器へ送る頼みは `"rules":[]` が増えるだけで、AI に渡る文は今と 1 文字も違わない（便2a の compose.mjs）。

## 読んだ節（設計パートナーの照合）

- docs/handoff/design-partner-card-ops/guards/00-common.md: コマンドは作業場所の `cd` から始める・1 手順 1 コマンド・置き換えの印を残さない（ファイル名・行・中身をすべて実名で書いた）・報告に無い出力を成功と扱わない（commit と push は `git log` と push の生出力で確かめる）。○
- docs/handoff/design-partner-card-ops/guards/03-file.md: 新しいファイルは中身を丸ごと書く・既存ファイルの直しは 1 か所ずつ（「前」と「後」を逐語で書いた。「前」は origin/main e930f1b24 で実測）。○
- docs/handoff/design-partner-card-ops/guards/10-executor.md: 迷ったら補わずに停止して報告する（分かれ道に書いた）。○
- docs/handoff/design-partner-card-ops/guards/11-lint.md: `scripts/card-lint.sh` を発行前に流す（Opus）。○

## 受領確認

着手前に、報告の 1 行目へ「受領確認: card-bin2b を読んだ」と書く。

## この便で決めたこと（Opus・設計からの細部）

| 決めたこと | 理由・出典 |
|---|---|
| 頼みの本文は backend が自分で JSON にして（区切りの空白なし・日本語はそのまま）バイト数を測り、測ったバイトをそのまま送る | 測る数と送る数を同じにする（design.md §3「15,000 バイトを超えたら送らない」）。httpx に `json=` で任せると測った物と送る物が別になる |
| 15,000 バイトを超えたら容器を呼ばず 413 `rules_too_long`。使用の記録（台帳）には書かない | AI を呼んでいない（担当を読めないときの 503 と同じ扱い・`backend/app/routers/assistant.py:209-220`）。15,000 は容器の上限 16,384（`secretary-agent/server.mjs:15` の `MAX_BODY`）より小さい |
| 決まりを読めないときは 503 `not_ready`（ログの code は `rules_unreadable`）。容器を呼ばず台帳にも書かない | 便1 の表が無い・DB が落ちたときに、決まり無しで黙って送らない（R5「承認済みは必ず付く」を崩さない） |
| 決まりを読むのは担当表を読んだ後・`db.commit()` の前 | AI を待つ間 DB の取引を開いたままにしない（`backend/app/routers/assistant.py:209`・design.md §5-3 の順番） |
| `rules` は毎回送る（0 件なら `[]`） | 容器は `[]` と「無い」を同じに扱う（便2a・`secretary-agent/compose.mjs`）。送る形を 1 つにする |
| 送る順は決めた時刻の古い順（同じ時刻なら番号順）。承認済みの読み取りに件数の上限は付けない | 上限 20 件は書く側（数えて書く）で守る。読む側で切ると、もし 21 件あっても黙って落ちる（落ちたことが見えない） |
| 決まりの文の検査（前後の空白を落とす・150 字まで・改行以外の制御文字を断る）は `backend/app/schemas/secretary_rules.py` の `clean_rule_text` 1 か所だけ。書くとき（承認・候補）だけ見る | design.md §3「制御文字の決まりは断る」。150 は表の CHECK と同じ数（`migrations/20261113_100000_create_secretary_rules.sql:23`）。検査を 2 か所に書かない |
| 候補の一覧は新しい順に 100 件まで。決まり（承認済み）の一覧は全部 | 承認済みは 20 件が上限。候補は「違う」を押すたびに増える |
| 承認済みを数えて書く間は `pg_advisory_xact_lock(1077, 会社の番号)` で 1 本ずつ | design.md §4「同時に押しても 21 件目が入らない」。1 つ目の数 1077 は ADR-1077（design.md §10 の 8 回目）。会社の番号は 1 から始まるので、便3 の試しの鍵 (1077, 0) と重ならない |
| 状態が違う（外した物をまた外す・候補でない物を承認する等）は 409 `wrong_status` 1 つ。番号が自社に無いときは 404 `rule_not_found` | 画面（便3）が出し分ける数を増やさない。ほかの会社の番号は「無い」と同じに見せる（RLS と WHERE の両方で自社だけ） |
| 外す・捨てる・承認は `decided_by` と `decided_at` を上書きする | 表の説明（`migrations/20261113_100000_create_secretary_rules.sql:69`「使う・捨てる・外すを決めた人」）のとおり、最後に決めた人と時刻を残す |
| 新しい口 6 つと秘書の口は同じ守りの一覧 `_SECRETARY_DEPENDENCIES` を使う | design.md §5「今の秘書の口と同じ 4 つの依存」・R6「判定 1 か所」。一覧を 1 つにして写しを作らない |
| 画面には `rules_too_long` の言葉（日本語・英語）と種類の読み替えだけを足す。決まり帳の画面は便3 | design.md §12 便2「画面の見た目は何も変わらない」。413 のときだけ言葉が出る |
| `frontend/api-contract/openapi.json` を作り直して同じ commit に入れる | 必須チェック「API contract is up to date」（`.github/workflows/api-contract-check.yml`）が口の形のずれを止めるため |
| `.github/workflows/deploy.yml` の注記は直さない | 便2a と同じ（危険パスを触らない） |

## やること（この順）

1. 作業場所を公式の台本で作る（card-bin2a.md のやること 1 と同じ形）。`<main>` はクラウドが最初に置いた場所。1 つずつ流し、出力を報告に書く。
   - (1a) `cd <main> && git fetch origin main`
   - (1b) `cd <main> && git branch --list release/secretary-rulebook-bin2b`。空であること。空でなければ消さずに BLOCKED:。
   - (1c) `cd <main> && bash scripts/new-worktree.sh release/secretary-rulebook-bin2b`（`--claude` は付けない）。
   - (1d) `cd <main> && git worktree list`。`$HOME/worktrees/salesanchor/release-secretary-rulebook-bin2b` が出ること。以後の `<repo>` はこの絶対パス。
   - (1e) `cd <repo> && ./scripts/dev/executor-preflight.sh`。生出力を報告に貼る。クラウドでは [1/3] network と [2/3] gh auth の FAIL は起こるものとして先へ進む。[3/3] と [4/4] が OK でなければ BLOCKED:。
   - (1f) `cd <repo> && git diff --stat e930f1b24 HEAD -- backend/app/routers/assistant.py backend/app/schemas backend/app/services/secretary_rules.py backend/tests/test_assistant_router.py backend/tests/test_secretary_rules_tables_pg.py frontend/src/features/secretary frontend/src/locales/ja.json frontend/src/locales/en.json migrations/20261113_100000_create_secretary_rules.sql`。空であること（行番号を読んだ後に誰も触っていない）。空でなければ BLOCKED:（差分の生出力を添える）。
   - (1g) `mkdir -p /tmp/CC報告ファイル`。結果ファイルの置き場を作る（やること 9〜14 が書き込む）。
2. 新しいファイル `backend/app/schemas/secretary_rules.py` を作る。中身は下の「schemas の中身」を 1 文字も変えずに使う。
3. 新しいファイル `backend/app/services/secretary_rules.py` を作る。中身は下の「services の中身」を 1 文字も変えずに使う。
4. `backend/app/routers/assistant.py` を 10 か所直す（下の「口の直し」）。
5. `backend/tests/test_assistant_router.py` を 1 か所直す（下の「今の試験の直し」）。
6. 新しいファイル `backend/tests/test_assistant_rules_router.py` を作る。中身は下の「口の試験の中身」を 1 文字も変えずに使う。
7. 新しいファイル `backend/tests/test_secretary_rules_service_pg.py` を作る。中身は下の「PG の試験の中身」を 1 文字も変えずに使う。
8. 画面の 4 ファイルを直す（下の「画面の直し」）。
9. 会社の文脈の検査: `cd <repo> && python3 scripts/lint_tenant_schema.py --mode strict backend/app/ > /tmp/CC報告ファイル/bin2b-tenant-lint.txt 2>&1; echo "exit=$?"`。exit=0 であること。結果ファイルの最後の 10 行を報告に貼る。0 でなければ直さずに NEEDS_DECISION:（結果ファイルの全文）。
10. ruff: `cd <repo>/backend && uv run --no-project --python 3.12 --with ruff ruff check app/ > /tmp/CC報告ファイル/bin2b-ruff.txt 2>&1; echo "exit=$?"`。exit=0 であること。落ちたのが I001（import の並び）だけで、場所が `app/routers/assistant.py`・`app/services/secretary_rules.py`・`app/schemas/secretary_rules.py` だけなら、`cd <repo>/backend && uv run --no-project --python 3.12 --with ruff ruff check --select I --fix app/routers/assistant.py app/services/secretary_rules.py app/schemas/secretary_rules.py` を 1 回だけ流し、`cd <repo> && git diff -- backend/app/routers/assistant.py` の import のあたりを報告に貼ってから、やること 10 の最初のコマンドをもう一度流す。I001 以外が出たら直さずに NEEDS_DECISION:（結果ファイルの全文）。
11. API の形の書き出し: `cd <repo>/backend && ENVIRONMENT=test uv run --no-project --python 3.12 --with-requirements requirements.txt python -m tools.export_openapi ../frontend/api-contract/openapi.json > /tmp/CC報告ファイル/bin2b-openapi.txt 2>&1; echo "exit=$?"`。exit=0 であること。続けて `cd <repo> && git diff --stat -- frontend/api-contract/openapi.json` と `cd <repo> && grep -n '"/api/v1/assistant/rules' frontend/api-contract/openapi.json` を報告に貼る。`/api/v1/assistant/rules`・`/api/v1/assistant/rules/feedback`・`/api/v1/assistant/rules/{rule_id}/approve`・`/reject`・`/remove` の 5 行が出ること。exit が 0 でない・5 行でない → BLOCKED:（結果ファイルの全文）。
12. backend の試験（SQLite）: `cd <repo>/backend && ENVIRONMENT=test uv run --no-project --python 3.12 --with-requirements requirements.txt --with-requirements requirements-dev.txt python -m pytest tests/test_assistant_router.py tests/test_assistant_rules_router.py tests/test_secretary_rules_service_pg.py -q > /tmp/CC報告ファイル/bin2b-pytest.txt 2>&1; echo "exit=$?"`。exit=0 であること。結果ファイルの最後の 15 行を報告に貼る（PG の試験はクラウドでは skip になる。CI で流れる）。試験が落ちた → 直さずに NEEDS_DECISION:（落ちた試験の題と、そのあたりの 40 行）。uv や依存が入らず試験まで行かない → 結果ファイルの最後の 30 行を添えて「未実行」と報告し、先へ進む（CI が流す）。
13. 画面の試験: `cd <repo>/frontend && npm ci > /tmp/CC報告ファイル/bin2b-npm-ci.txt 2>&1; echo "exit=$?"`。0 なら `cd <repo>/frontend && npx vitest run src/features/secretary > /tmp/CC報告ファイル/bin2b-vitest.txt 2>&1; echo "exit=$?"`。exit=0 であること。結果ファイルの最後の 15 行を報告に貼る。試験が落ちた → 直さずに NEEDS_DECISION:（落ちた試験の題と 40 行）。npm ci が通らない → 最後の 30 行を添えて「未実行」と報告し、先へ進む（CI が流す）。
14. commit（1 つ）。commit の前に `cd <repo> && git status --short` を報告に貼る。下の 11 ファイルだけであること（違えば commit せずに BLOCKED:。`frontend/node_modules` は .gitignore で出ない）。`git add` は 11 ファイルを名前で指定する: `backend/app/routers/assistant.py`・`backend/app/schemas/secretary_rules.py`・`backend/app/services/secretary_rules.py`・`backend/tests/test_assistant_router.py`・`backend/tests/test_assistant_rules_router.py`・`backend/tests/test_secretary_rules_service_pg.py`・`frontend/src/features/secretary/secretaryApi.ts`・`frontend/src/features/secretary/SecretaryChat.test.tsx`・`frontend/src/locales/ja.json`・`frontend/src/locales/en.json`・`frontend/api-contract/openapi.json`（11 個。数え直して 11 であること）。題は `feat(secretary): 承認済みの決まりを秘書へ送り、決まり帳の口を足す（ADR-1077 便2b）`。末尾に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`。`git log --oneline -1` を報告に貼る。
15. 提出前: `cd <repo> && bash scripts/dev/check-before-submit.sh > /tmp/CC報告ファイル/bin2b-check.txt 2>&1; echo "exit=$?"`。パスと最後の 5 行を報告する。通ったら `cd <repo> && git push origin release/secretary-rulebook-bin2b`。push の生出力を報告に貼る。

## schemas の中身（`backend/app/schemas/secretary_rules.py`）

```python
"""ADR-1077 便2b: 決まり帳の口の入れ物（design.md §3「大きさ」・§4・§5）。

決まりの文の検査（前後の空白を落とす・150 字まで・改行以外の制御文字を断る）は、このファイルの clean_rule_text だけに書く。
150 は表の CHECK（migrations/20261113_100000_create_secretary_rules.sql の ck_secretary_rules_rule_text_len）と同じ数。
"""

from __future__ import annotations

import unicodedata
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

RULE_TEXT_MAX = 150

# 一覧の口で選べる状態（捨てた・外した物は一覧に出さない）
RuleStatus = Literal["candidate", "approved"]
# 元になった秘書の答えの種類（表の CHECK ck_secretary_rules_source_kind と同じ 5 つ）
SourceKind = Literal["invoice", "event", "unknown", "rule_proposal", "rule_list"]


def has_control_chars(value: str) -> bool:
    """改行以外の制御文字（Unicode の分類 Cc。タブ・復帰・NUL など）があれば True。"""
    return any(ch != "\n" and unicodedata.category(ch) == "Cc" for ch in value)


def clean_rule_text(value: str, *, allow_empty: bool) -> str:
    """前後の空白を落とし、空・151 字以上・制御文字入りを断る（ValueError。口は 422 を返す）。"""
    value = value.strip()
    if not value and not allow_empty:
        raise ValueError("rule_text is empty")
    if len(value) > RULE_TEXT_MAX:
        raise ValueError("rule_text is too long")
    if has_control_chars(value):
        raise ValueError("rule_text has control characters")
    return value


class RuleTextIn(BaseModel):
    """承認する決まりの文（POST /assistant/rules・POST /assistant/rules/{rule_id}/approve）。"""

    model_config = ConfigDict(extra="forbid")

    rule_text: str

    @field_validator("rule_text")
    @classmethod
    def _check_rule_text(cls, value: str) -> str:
        return clean_rule_text(value, allow_empty=False)


class RuleFeedbackIn(BaseModel):
    """「違う」の 1 往復（POST /assistant/rules/feedback。候補として入る。rule_text は空でよい）。"""

    model_config = ConfigDict(extra="forbid")

    source_text: str = Field(min_length=1, max_length=1000)
    source_kind: SourceKind
    source_reply: str | None = Field(default=None, max_length=200)
    rule_text: str = ""

    @field_validator("rule_text")
    @classmethod
    def _check_rule_text(cls, value: str) -> str:
        return clean_rule_text(value, allow_empty=True)

    @field_validator("source_text", "source_reply")
    @classmethod
    def _no_nul(cls, value: str | None) -> str | None:
        # PostgreSQL の text には NUL を入れられない（入れると 500 になる）ため、ここで断る
        if value is not None and "\x00" in value:
            raise ValueError("NUL is not allowed")
        return value


class RuleOut(BaseModel):
    id: int
    status: Literal["candidate", "approved", "rejected", "removed"]
    rule_text: str
    source_text: str | None
    source_kind: str | None
    source_reply: str | None
    created_at: datetime
    decided_at: datetime | None


class RuleListOut(BaseModel):
    rules: list[RuleOut]
```

## services の中身（`backend/app/services/secretary_rules.py`）

```python
"""ADR-1077 便2b: 秘書の決まり帳（public.secretary_rules）を読む・書く（design.md §4・§5）。

この表の SQL はこのファイルにだけ書く。commit は呼ぶ側（口）がする。
RLS（自社の会社文脈）に加えて、WHERE でも tenant_id を見る。
承認済みを数えて書く間は、会社ごとに pg_advisory_xact_lock(1077, tenant_id) で 1 本ずつにする（design.md §4。
会社の番号は 1 から始まるので、便3 の試しの鍵 (1077, 0) とは重ならない）。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

MAX_APPROVED = 20  # 承認済みの上限（design.md §3「大きさ」・§4）
CANDIDATE_LIST_LIMIT = 100  # 候補の一覧に出す数（新しい順）
_LOCK_CLASS = 1077  # 鍵の 1 つ目の数（ADR-1077）


class RulesFull(Exception):
    """承認済みが MAX_APPROVED 件ある（口は 409 rules_full）。"""


class RuleNotFound(LookupError):
    """その番号の決まりが自社に無い（口は 404 rule_not_found）。"""


class RuleWrongStatus(Exception):
    """今の状態ではその操作ができない（口は 409 wrong_status）。"""


@dataclass(frozen=True)
class SecretaryRule:
    id: int
    status: str
    rule_text: str
    source_text: str | None
    source_kind: str | None
    source_reply: str | None
    created_at: datetime
    decided_at: datetime | None


_SELECT_APPROVED_TEXTS = text(
    "SELECT rule_text FROM public.secretary_rules "
    "WHERE tenant_id = :tenant_id AND status = 'approved' "
    "ORDER BY decided_at, id"
)
_SELECT_APPROVED = text(
    "SELECT id, status, rule_text, source_text, source_kind, source_reply, created_at, decided_at "
    "FROM public.secretary_rules "
    "WHERE tenant_id = :tenant_id AND status = 'approved' "
    "ORDER BY decided_at, id"
)
_SELECT_CANDIDATES = text(
    "SELECT id, status, rule_text, source_text, source_kind, source_reply, created_at, decided_at "
    "FROM public.secretary_rules "
    "WHERE tenant_id = :tenant_id AND status = 'candidate' "
    "ORDER BY id DESC LIMIT :limit"
)
_LOCK = text("SELECT pg_advisory_xact_lock(CAST(:lock_class AS integer), CAST(:tenant_id AS integer))")
_COUNT_APPROVED = text(
    "SELECT count(*) FROM public.secretary_rules WHERE tenant_id = :tenant_id AND status = 'approved'"
)
_INSERT_APPROVED = text(
    "INSERT INTO public.secretary_rules (tenant_id, status, rule_text, created_by, decided_by, decided_at) "
    "VALUES (:tenant_id, 'approved', :rule_text, :created_by, :decided_by, now()) "
    "RETURNING id, status, rule_text, source_text, source_kind, source_reply, created_at, decided_at"
)
_INSERT_CANDIDATE = text(
    "INSERT INTO public.secretary_rules "
    "(tenant_id, status, rule_text, source_text, source_kind, source_reply, created_by) "
    "VALUES (:tenant_id, 'candidate', :rule_text, :source_text, :source_kind, :source_reply, :created_by) "
    "RETURNING id, status, rule_text, source_text, source_kind, source_reply, created_at, decided_at"
)
_SELECT_STATUS = text("SELECT status FROM public.secretary_rules WHERE id = :rule_id AND tenant_id = :tenant_id")
_DECIDE = text(
    "UPDATE public.secretary_rules "
    "SET status = :to_status, rule_text = COALESCE(CAST(:rule_text AS text), rule_text), "
    "decided_by = :user_id, decided_at = now() "
    "WHERE id = :rule_id AND tenant_id = :tenant_id AND status = :from_status "
    "RETURNING id, status, rule_text, source_text, source_kind, source_reply, created_at, decided_at"
)


def _to_rule(row) -> SecretaryRule:
    return SecretaryRule(**dict(row))


async def list_approved_rule_texts(db: AsyncSession, tenant_id: int) -> list[str]:
    """秘書の容器へ送る承認済みの決まりの文（決めた時刻の古い順）。件数で切らない（上限は書く側で守る）。"""
    result = await db.execute(_SELECT_APPROVED_TEXTS, {"tenant_id": tenant_id})
    return [row[0] for row in result.all()]


async def list_rules(db: AsyncSession, tenant_id: int, status: str) -> list[SecretaryRule]:
    """一覧（approved は全部・決めた時刻の古い順。candidate は新しい順に CANDIDATE_LIST_LIMIT 件まで）。"""
    if status == "approved":
        result = await db.execute(_SELECT_APPROVED, {"tenant_id": tenant_id})
    elif status == "candidate":
        result = await db.execute(_SELECT_CANDIDATES, {"tenant_id": tenant_id, "limit": CANDIDATE_LIST_LIMIT})
    else:
        raise ValueError(f"unknown status: {status}")
    return [_to_rule(row) for row in result.mappings().all()]


async def _lock_and_count(db: AsyncSession, tenant_id: int) -> int:
    """会社ごとの鍵を取り（取引の終わりまで持つ）、承認済みの数を返す。"""
    await db.execute(_LOCK, {"lock_class": _LOCK_CLASS, "tenant_id": tenant_id})
    return (await db.execute(_COUNT_APPROVED, {"tenant_id": tenant_id})).scalar_one()


async def _status_of(db: AsyncSession, tenant_id: int, rule_id: int) -> str | None:
    result = await db.execute(_SELECT_STATUS, {"rule_id": rule_id, "tenant_id": tenant_id})
    return result.scalar_one_or_none()


async def add_approved_rule(db: AsyncSession, tenant_id: int, user_id: int, rule_text: str) -> SecretaryRule:
    """案の「承認」: いきなり approved で入れる（design.md §5（３））。20 件あれば RulesFull。"""
    if await _lock_and_count(db, tenant_id) >= MAX_APPROVED:
        raise RulesFull()
    params = {"tenant_id": tenant_id, "rule_text": rule_text, "created_by": user_id, "decided_by": user_id}
    row = (await db.execute(_INSERT_APPROVED, params)).mappings().one()
    return _to_rule(row)


async def add_candidate(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
    rule_text: str,
    source_text: str,
    source_kind: str,
    source_reply: str | None,
) -> SecretaryRule:
    """答えの「違う」: その 1 往復を candidate で入れる（design.md §5（４））。"""
    params = {
        "tenant_id": tenant_id,
        "rule_text": rule_text,
        "source_text": source_text,
        "source_kind": source_kind,
        "source_reply": source_reply,
        "created_by": user_id,
    }
    row = (await db.execute(_INSERT_CANDIDATE, params)).mappings().one()
    return _to_rule(row)


async def _decide(
    db: AsyncSession,
    tenant_id: int,
    rule_id: int,
    user_id: int,
    from_status: str,
    to_status: str,
    rule_text: str | None = None,
) -> SecretaryRule:
    params = {
        "to_status": to_status,
        "rule_text": rule_text,
        "user_id": user_id,
        "rule_id": rule_id,
        "tenant_id": tenant_id,
        "from_status": from_status,
    }
    row = (await db.execute(_DECIDE, params)).mappings().first()
    if row is None:
        current = await _status_of(db, tenant_id, rule_id)
        if current is None:
            raise RuleNotFound(rule_id)
        raise RuleWrongStatus(current)
    return _to_rule(row)


async def approve_candidate(
    db: AsyncSession, tenant_id: int, rule_id: int, user_id: int, rule_text: str
) -> SecretaryRule:
    """候補を文を付けて approved にする（design.md §5（５））。番号が無い・候補でないを先に見てから 20 件を見る。"""
    if await _lock_and_count(db, tenant_id) >= MAX_APPROVED:
        current = await _status_of(db, tenant_id, rule_id)
        if current is None:
            raise RuleNotFound(rule_id)
        if current != "candidate":
            raise RuleWrongStatus(current)
        raise RulesFull()
    return await _decide(db, tenant_id, rule_id, user_id, "candidate", "approved", rule_text)


async def reject_candidate(db: AsyncSession, tenant_id: int, rule_id: int, user_id: int) -> SecretaryRule:
    """候補を捨てる（candidate → rejected）。"""
    return await _decide(db, tenant_id, rule_id, user_id, "candidate", "rejected")


async def remove_rule(db: AsyncSession, tenant_id: int, rule_id: int, user_id: int) -> SecretaryRule:
    """決まりを外す（approved → removed）。次の頼みから容器へ送らない（R4）。"""
    return await _decide(db, tenant_id, rule_id, user_id, "approved", "removed")
```

## 口の直し（`backend/app/routers/assistant.py`）

1 か所ずつ Edit で直す。「前」が 1 つだけ見つかること。見つからない・2 つ以上なら BLOCKED:。上から順に直すと行番号がずれるので「前」の文字で探す。

- (a) 6 行目。前: `順番（厳守）: ①守りを通す・担当表を読む ②db.commit() ③容器を呼ぶ・使用の記録に1行 ④会社の文脈を張り直す ⑤名前探し ⑥返す。` → 後: `順番（厳守）: ①守りを通す・担当表と承認済みの決まりを読む・頼みの大きさを測る ②db.commit() ③容器を呼ぶ・使用の記録に1行 ④会社の文脈を張り直す ⑤名前探し ⑥返す。`
- (b) 7 行目 `DB の取引を開いたまま AI を待たない。ログは 1 回 1 行（text と答えの中身は書かない）。` の次の行に 1 行足す: `ADR-1077 便2b: 決まり帳の口（/assistant/rules・design.md §5）もここに置き、秘書の口と同じ守り _SECRETARY_DEPENDENCIES を使う。`
- (c) 12 行目 `import logging` の前の行に `import json` を 1 行足す。
- (d) 45 行目 `from app.services.ai_assignment import get_ai_assignment` の前の行に 1 行足す: `from app.schemas.secretary_rules import RuleFeedbackIn, RuleListOut, RuleOut, RuleStatus, RuleTextIn`
- (e) 47 行目 `from app.services.secretary_resolve import resolve_names` の次の行に、次を足す。

```python
from app.services.secretary_rules import (
    RuleNotFound,
    RulesFull,
    RuleWrongStatus,
    SecretaryRule,
    add_approved_rule,
    add_candidate,
    approve_candidate,
    list_approved_rule_texts,
    list_rules,
    reject_candidate,
    remove_rule,
)
```

- (f) 55 行目 `AGENT_TIMEOUT_SECONDS = 85.0` の次の行に、次の 2 行を足す。

```python
# 容器へ送る頼みの大きさの上限（バイト）。容器の上限 MAX_BODY 16,384（secretary-agent/server.mjs）より小さくする（design.md §3「大きさ」）
AGENT_BODY_MAX_BYTES = 15_000
```

- (g) 61 行目 `_perm_invoices_create = require_permission("invoices.create")` の次に、空行を 1 つ置いてから次を足す。

```python
# 秘書の口と決まり帳の口が同じ 4 つの守りを使う（ADR-1077 便2b・design.md §5。承認できる人の判定は require_super_admin だけ）
_SECRETARY_DEPENDENCIES = [
    Depends(_feature_secretary_chat),
    Depends(require_super_admin),
    Depends(_perm_customers_view),
    Depends(_perm_invoices_create),
]
```

- (h) 145〜153 行目を置き換える。前:

```python
async def _call_agent(text: str, model: str, url: str) -> dict:
    """容器を呼ぶ（model は担当表から読んだ値・url は agent_url の値）。失敗は (HTTPException, ログの code) に直す。"""
    now = datetime.now(_JST).isoformat(timespec="seconds")
    try:
        async with httpx.AsyncClient(timeout=AGENT_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{url}/intent",
                json={"text": text, "now": now, "model": model},
            )
```

後（154 行目 `    except httpx.TimeoutException:` から後ろは変えない）:

```python
def _agent_payload(text: str, model: str, rules: list[str]) -> bytes:
    """容器への頼みの本文（ADR-1077 便2b）。測ったバイト数と送るバイト数を同じにするため、ここで JSON にする。"""
    now = datetime.now(_JST).isoformat(timespec="seconds")
    body = {"text": text, "now": now, "model": model, "rules": rules}
    return json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


async def _call_agent(payload: bytes, url: str) -> dict:
    """容器を呼ぶ（payload は _agent_payload の値・url は agent_url の値）。失敗は (HTTPException, ログの code) に直す。"""
    try:
        async with httpx.AsyncClient(timeout=AGENT_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{url}/intent",
                content=payload,
                headers={"Content-Type": "application/json"},
            )
```

- (i) 193〜198 行目。前:

```python
    dependencies=[
        Depends(_feature_secretary_chat),
        Depends(require_super_admin),
        Depends(_perm_customers_view),
        Depends(_perm_invoices_create),
    ],
```

後: `    dependencies=_SECRETARY_DEPENDENCIES,`（1 行）

- (j) 222 行目 `    # ② 取引を閉じる（AI を待つ間 DB を開いたままにしない）` の前に、次を足す（その前の行 `        raise _fail(503, "not_ready")` との間に空行を 1 つ、足した物の後ろにも空行を 1 つ）。続けて 229 行目。前: `        raw = await _call_agent(body.text, assignment.model, url)` → 後: `        raw = await _call_agent(payload, url)`

```python
    # ①' 承認済みの決まりを読み、頼みの大きさを測る（commit の前。ADR-1077 便2b・design.md §3「大きさ」）
    # 読めない・大きすぎる時は容器を呼ばず、台帳にも書かない（AI を呼んでいないため）。
    try:
        rules = await list_approved_rule_texts(db, tenant_id)
    except Exception:  # noqa: BLE001
        _log(user_id, tenant_id, started, "rules_unreadable", None)
        raise _fail(503, "not_ready", "rules_unreadable") from None
    payload = _agent_payload(body.text, assignment.model, rules)
    if len(payload) > AGENT_BODY_MAX_BYTES:
        _log(user_id, tenant_id, started, "rules_too_long", None)
        raise _fail(413, "rules_too_long")
```

- (k) ファイルの最後（今は 301 行目 `    )` で終わる）の後ろに、空行を 2 つ置いてから次を足す。

```python
# ---- ADR-1077 便2b: 決まり帳の口（design.md §5）----------------------------------------
# 守りは秘書の口と同じ _SECRETARY_DEPENDENCIES。承認できる人の判定は require_super_admin だけ（R6）。
# 書く口は commit の後に会社の文脈を張り直す（ADR-072）。


def _rule_out(rule: SecretaryRule) -> RuleOut:
    return RuleOut.model_validate(rule, from_attributes=True)


@router.get("/assistant/rules", response_model=RuleListOut, dependencies=_SECRETARY_DEPENDENCIES)
async def get_assistant_rules(
    status: RuleStatus,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
) -> RuleListOut:
    rules = await list_rules(db, tenant_id, status)
    return RuleListOut(rules=[_rule_out(r) for r in rules])


@router.post(
    "/assistant/rules",
    response_model=RuleOut,
    status_code=201,
    dependencies=_SECRETARY_DEPENDENCIES,
)
async def post_assistant_rule(
    body: RuleTextIn,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> RuleOut:
    user_id = current_user.id
    try:
        rule = await add_approved_rule(db, tenant_id, user_id, body.rule_text)
    except RulesFull:
        raise _fail(409, "rules_full") from None
    await db.commit()
    await reset_tenant_context(db, tenant_id)
    return _rule_out(rule)


@router.post(
    "/assistant/rules/feedback",
    response_model=RuleOut,
    status_code=201,
    dependencies=_SECRETARY_DEPENDENCIES,
)
async def post_assistant_rule_feedback(
    body: RuleFeedbackIn,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> RuleOut:
    user_id = current_user.id
    rule = await add_candidate(
        db, tenant_id, user_id, body.rule_text, body.source_text, body.source_kind, body.source_reply
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)
    return _rule_out(rule)


@router.post(
    "/assistant/rules/{rule_id}/approve",
    response_model=RuleOut,
    dependencies=_SECRETARY_DEPENDENCIES,
)
async def approve_assistant_rule(
    rule_id: int,
    body: RuleTextIn,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> RuleOut:
    user_id = current_user.id
    try:
        rule = await approve_candidate(db, tenant_id, rule_id, user_id, body.rule_text)
    except RuleNotFound:
        raise _fail(404, "rule_not_found") from None
    except RuleWrongStatus:
        raise _fail(409, "wrong_status") from None
    except RulesFull:
        raise _fail(409, "rules_full") from None
    await db.commit()
    await reset_tenant_context(db, tenant_id)
    return _rule_out(rule)


@router.post(
    "/assistant/rules/{rule_id}/reject",
    response_model=RuleOut,
    dependencies=_SECRETARY_DEPENDENCIES,
)
async def reject_assistant_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> RuleOut:
    user_id = current_user.id
    try:
        rule = await reject_candidate(db, tenant_id, rule_id, user_id)
    except RuleNotFound:
        raise _fail(404, "rule_not_found") from None
    except RuleWrongStatus:
        raise _fail(409, "wrong_status") from None
    await db.commit()
    await reset_tenant_context(db, tenant_id)
    return _rule_out(rule)


@router.post(
    "/assistant/rules/{rule_id}/remove",
    response_model=RuleOut,
    dependencies=_SECRETARY_DEPENDENCIES,
)
async def remove_assistant_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> RuleOut:
    user_id = current_user.id
    try:
        rule = await remove_rule(db, tenant_id, rule_id, user_id)
    except RuleNotFound:
        raise _fail(404, "rule_not_found") from None
    except RuleWrongStatus:
        raise _fail(409, "wrong_status") from None
    await db.commit()
    await reset_tenant_context(db, tenant_id)
    return _rule_out(rule)
```

## 今の試験の直し（`backend/tests/test_assistant_router.py`）

- 46 行目 `    monkeypatch.setattr(assistant, "record_usage_isolated", AsyncMock())` の次の行に、次の 2 行を足す（4 空白のインデント）。ほかの行は変えない。

```python
    # ADR-1077 便2b: 決まり帳は SQLite に無いので、承認済みの決まりの読み取りは「0 件」を返す偽物にする
    monkeypatch.setattr(assistant, "list_approved_rule_texts", AsyncMock(return_value=[]))
```

（今の秘書の試験はすべて `allowed` か、それを土台にした `codex` を使う。使わない 2 つ（`test_no_feature_is_403`・`test_not_super_admin_is_403`）は守りで止まり、決まりを読む前に終わる。）

## 口の試験の中身（`backend/tests/test_assistant_rules_router.py`）

```python
"""ADR-1077 便2b: 決まり帳の口と、秘書の口が承認済みの決まりを容器へ送ることの試験（SQLite・design.md §3・§5・§11）。

決まり帳の読み書き（app/services/secretary_rules.py）は AsyncMock に差し替える。本物の PostgreSQL での試験は
tests/test_secretary_rules_service_pg.py。容器は httpx をモックする（tests/test_assistant_router.py と同じ道具）。
テストデータはすべて架空。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import HTTPException

from app.routers import assistant
from app.services.secretary_rules import RuleNotFound, RulesFull, RuleWrongStatus, SecretaryRule
from tests.test_assistant_router import _fixture, _mock_agent, _respond
from tests.test_assistant_router import allowed as allowed  # noqa: F401  fixture

URL = "/api/v1/assistant/messages"
RULES_URL = "/api/v1/assistant/rules"
WRITERS = ("add_approved_rule", "add_candidate", "approve_candidate", "reject_candidate", "remove_rule")
_T = datetime(2026, 11, 13, 0, 0, tzinfo=timezone.utc)


def _rule(**over) -> SecretaryRule:
    base = {
        "id": 5,
        "status": "approved",
        "rule_text": "決まり",
        "source_text": None,
        "source_kind": None,
        "source_reply": None,
        "created_at": _T,
        "decided_at": _T,
    }
    base.update(over)
    return SecretaryRule(**base)


def _capture(monkeypatch) -> dict:
    """容器へ送られた生のバイト・読んだ JSON・Content-Type を残す（容器は unknown の見本を返す）。"""
    sent: dict = {"calls": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        sent["calls"] += 1
        sent["raw"] = request.content
        sent["body"] = json.loads(request.content)
        sent["content_type"] = request.headers.get("content-type")
        return httpx.Response(200, json=_fixture("envelope-unknown.json"))

    _mock_agent(monkeypatch, handler)
    return sent


def _writers(monkeypatch) -> dict:
    mocks = {name: AsyncMock() for name in WRITERS}
    for name, mock in mocks.items():
        monkeypatch.setattr(assistant, name, mock)
    return mocks


def _log_lines(caplog) -> list[str]:
    return [r.getMessage() for r in caplog.records if "assistant_message" in r.getMessage()]


# ---- 秘書の口が決まりを送る（design.md §3・R4・R5）-------------------------------------


@pytest.mark.asyncio
async def test_approved_rules_are_sent_in_order(allowed, monkeypatch):
    reader = AsyncMock(return_value=["一つ目の決まり", "二つ目の決まり"])
    monkeypatch.setattr(assistant, "list_approved_rule_texts", reader)
    sent = _capture(monkeypatch)
    resp = await allowed.post(URL, json={"text": "請求書"})
    assert resp.status_code == 200, resp.text
    assert sent["body"]["rules"] == ["一つ目の決まり", "二つ目の決まり"]
    assert set(sent["body"]) == {"text", "now", "model", "rules"}
    assert "一つ目の決まり".encode("utf-8") in sent["raw"]
    assert sent["content_type"] == "application/json"
    reader.assert_awaited_once()
    assert reader.await_args.args[1] == 999


@pytest.mark.asyncio
async def test_no_rules_sends_empty_list(allowed, monkeypatch):
    sent = _capture(monkeypatch)
    resp = await allowed.post(URL, json={"text": "請求書"})
    assert resp.status_code == 200, resp.text
    assert sent["body"]["rules"] == []


@pytest.mark.asyncio
async def test_too_long_is_413_without_agent_or_ledger(allowed, monkeypatch, caplog):
    # 絵文字（1 字 4 バイト）で決まり 20 件 × 150 字＋文 1000 字 → 16,000 バイトを超える
    monkeypatch.setattr(assistant, "list_approved_rule_texts", AsyncMock(return_value=["😀" * 150] * 20))
    sent = _capture(monkeypatch)
    with caplog.at_level(logging.INFO, logger=assistant.logger.name):
        resp = await allowed.post(URL, json={"text": "😀" * 1000})
    assert resp.status_code == 413
    assert resp.json()["detail"] == {"code": "rules_too_long"}
    assert sent["calls"] == 0
    assert assistant.record_usage_isolated.await_count == 0
    lines = _log_lines(caplog)
    assert len(lines) == 1
    assert "code=rules_too_long" in lines[0]


@pytest.mark.asyncio
async def test_japanese_full_rules_fit(allowed, monkeypatch):
    # 日本語（1 字 3 バイト）で決まり 20 件 × 150 字＋文 1000 字は 15,000 バイトに収まり送られる
    monkeypatch.setattr(assistant, "list_approved_rule_texts", AsyncMock(return_value=["あ" * 150] * 20))
    sent = _capture(monkeypatch)
    resp = await allowed.post(URL, json={"text": "あ" * 1000})
    assert resp.status_code == 200, resp.text
    assert sent["calls"] == 1
    assert len(sent["raw"]) <= assistant.AGENT_BODY_MAX_BYTES


@pytest.mark.asyncio
@pytest.mark.parametrize("delta, expected", [(0, 200), (-1, 413)])
async def test_size_boundary(allowed, monkeypatch, delta, expected):
    sent = _capture(monkeypatch)
    limit = len(assistant._agent_payload("a", "sonnet", [])) + delta
    monkeypatch.setattr(assistant, "AGENT_BODY_MAX_BYTES", limit)
    resp = await allowed.post(URL, json={"text": "a"})
    assert resp.status_code == expected, resp.text
    if expected == 200:
        assert len(sent["raw"]) == limit
    else:
        assert sent["calls"] == 0


@pytest.mark.asyncio
async def test_rules_read_failure_is_503_without_agent_or_ledger(allowed, monkeypatch, caplog):
    monkeypatch.setattr(assistant, "list_approved_rule_texts", AsyncMock(side_effect=RuntimeError("db down")))
    sent = _capture(monkeypatch)
    with caplog.at_level(logging.INFO, logger=assistant.logger.name):
        resp = await allowed.post(URL, json={"text": "a"})
    assert resp.status_code == 503
    assert resp.json()["detail"] == {"code": "not_ready"}
    assert sent["calls"] == 0
    assert assistant.record_usage_isolated.await_count == 0
    lines = _log_lines(caplog)
    assert len(lines) == 1
    assert "code=rules_unreadable" in lines[0]


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["envelope-invoice.json", "envelope-event.json", "envelope-unknown.json"])
async def test_agent_answer_never_writes_rules(allowed, monkeypatch, name):
    # R1: AI の答えだけでは決まり帳に行が増えない
    writers = _writers(monkeypatch)
    _mock_agent(monkeypatch, _respond(200, _fixture(name)))
    resp = await allowed.post(URL, json={"text": "請求書"})
    assert resp.status_code == 200, resp.text
    for mock in writers.values():
        assert mock.await_count == 0


# ---- 守り（R6: 新しい口すべてで同じ 4 つ）----------------------------------------------

ENDPOINTS = [
    ("get", RULES_URL + "?status=approved", None),
    ("post", RULES_URL, {"rule_text": "決まり"}),
    ("post", RULES_URL + "/feedback", {"source_text": "元の文", "source_kind": "invoice"}),
    ("post", RULES_URL + "/5/approve", {"rule_text": "決まり"}),
    ("post", RULES_URL + "/5/reject", None),
    ("post", RULES_URL + "/5/remove", None),
    ("post", URL, {"text": "a"}),
]


async def _call(client, method: str, url: str, body):
    if method == "get":
        return await client.get(url)
    if body is None:
        return await client.post(url)
    return await client.post(url, json=body)


@pytest.mark.asyncio
@pytest.mark.parametrize("method, url, body", ENDPOINTS)
async def test_not_super_admin_is_403_everywhere(client, monkeypatch, method, url, body):
    from app.main import app

    async def _ok_feature():
        return None

    app.dependency_overrides[assistant._feature_secretary_chat] = _ok_feature
    monkeypatch.setattr(assistant, "list_rules", AsyncMock())
    writers = _writers(monkeypatch)
    # require_super_admin は上書きしない: モックユーザーは is_super_admin が偽
    resp = await _call(client, method, url, body)
    assert resp.status_code == 403
    assert assistant.list_rules.await_count == 0
    for mock in writers.values():
        assert mock.await_count == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("method, url, body", ENDPOINTS)
async def test_no_feature_is_403_everywhere(client, method, url, body):
    from app.main import app

    async def _no_feature():
        raise HTTPException(status_code=403, detail="機能が無効です: secretary_chat")

    app.dependency_overrides[assistant._feature_secretary_chat] = _no_feature
    resp = await _call(client, method, url, body)
    assert resp.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("method, url, body", ENDPOINTS)
async def test_missing_permission_is_403_everywhere(allowed, monkeypatch, method, url, body):
    async def _only_view(db, tenant_id, user_id):
        return {"customers.view"}

    monkeypatch.setattr("app.auth.dependencies.load_user_permissions", _only_view)
    resp = await _call(allowed, method, url, body)
    assert resp.status_code == 403


# ---- POST /assistant/rules（案の「承認」）----------------------------------------------


@pytest.mark.asyncio
async def test_post_rule_adds_approved(allowed, monkeypatch):
    add = AsyncMock(return_value=_rule(rule_text="決まり"))
    monkeypatch.setattr(assistant, "add_approved_rule", add)
    resp = await allowed.post(RULES_URL, json={"rule_text": "  決まり  "})
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["id"] == 5 and data["status"] == "approved" and data["rule_text"] == "決まり"
    assert add.await_args.args[1:] == (999, 999, "決まり")


@pytest.mark.asyncio
async def test_post_rule_full_is_409(allowed, monkeypatch):
    monkeypatch.setattr(assistant, "add_approved_rule", AsyncMock(side_effect=RulesFull()))
    resp = await allowed.post(RULES_URL, json={"rule_text": "決まり"})
    assert resp.status_code == 409
    assert resp.json()["detail"] == {"code": "rules_full"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        {"rule_text": ""},
        {"rule_text": "   "},
        {"rule_text": "あ" * 151},
        {"rule_text": "a\tb"},
        {"rule_text": "a\x00b"},
        {"rule_text": "a\rb"},
        {"rule_text": "決まり", "extra": 1},
        {},
    ],
)
async def test_post_rule_rejects_bad_text(allowed, monkeypatch, body):
    add = AsyncMock(return_value=_rule())
    monkeypatch.setattr(assistant, "add_approved_rule", add)
    resp = await allowed.post(RULES_URL, json=body)
    assert resp.status_code == 422
    assert add.await_count == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("rule_text", ["あ" * 150, "一行目\n二行目"])
async def test_post_rule_accepts_full_length_and_newline(allowed, monkeypatch, rule_text):
    add = AsyncMock(return_value=_rule(rule_text=rule_text))
    monkeypatch.setattr(assistant, "add_approved_rule", add)
    resp = await allowed.post(RULES_URL, json={"rule_text": rule_text})
    assert resp.status_code == 201, resp.text
    assert add.await_args.args[3] == rule_text


# ---- POST /assistant/rules/feedback（答えの「違う」）------------------------------------


@pytest.mark.asyncio
async def test_feedback_adds_candidate(allowed, monkeypatch):
    add = AsyncMock(
        return_value=_rule(
            status="candidate",
            rule_text="",
            source_text="元の文",
            source_kind="event",
            source_reply="答え",
            decided_at=None,
        )
    )
    monkeypatch.setattr(assistant, "add_candidate", add)
    resp = await allowed.post(
        RULES_URL + "/feedback",
        json={"source_text": "元の文", "source_kind": "event", "source_reply": "答え"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "candidate" and data["decided_at"] is None
    assert add.await_args.args[1:] == (999, 999, "", "元の文", "event", "答え")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "over",
    [
        {"source_text": ""},
        {"source_text": "あ" * 1001},
        {"source_text": "a\x00b"},
        {"source_kind": "other"},
        {"source_reply": "あ" * 201},
        {"source_reply": "a\x00b"},
        {"rule_text": "a\x07b"},
        {"rule_text": "あ" * 151},
        {"extra": 1},
    ],
)
async def test_feedback_rejects_bad_body(allowed, monkeypatch, over):
    add = AsyncMock(return_value=_rule(status="candidate", decided_at=None))
    monkeypatch.setattr(assistant, "add_candidate", add)
    body = {"source_text": "元の文", "source_kind": "invoice"}
    body.update(over)
    resp = await allowed.post(RULES_URL + "/feedback", json=body)
    assert resp.status_code == 422
    assert add.await_count == 0


# ---- GET /assistant/rules?status=（R3）--------------------------------------------------


@pytest.mark.asyncio
async def test_list_rules(allowed, monkeypatch):
    lister = AsyncMock(return_value=[_rule(id=1), _rule(id=2)])
    monkeypatch.setattr(assistant, "list_rules", lister)
    for status in ("approved", "candidate"):
        resp = await allowed.get(RULES_URL, params={"status": status})
        assert resp.status_code == 200, resp.text
        assert [r["id"] for r in resp.json()["rules"]] == [1, 2]
        assert lister.await_args.args[1:] == (999, status)


@pytest.mark.asyncio
@pytest.mark.parametrize("params", [{"status": "rejected"}, {"status": "removed"}, {}])
async def test_list_rules_rejects_other_status(allowed, monkeypatch, params):
    lister = AsyncMock(return_value=[])
    monkeypatch.setattr(assistant, "list_rules", lister)
    resp = await allowed.get(RULES_URL, params=params)
    assert resp.status_code == 422
    assert lister.await_count == 0


# ---- 承認・捨てる・外す ------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "action, service",
    [("approve", "approve_candidate"), ("reject", "reject_candidate"), ("remove", "remove_rule")],
)
@pytest.mark.parametrize(
    "exc, status_code, code",
    [(RuleNotFound(5), 404, "rule_not_found"), (RuleWrongStatus("removed"), 409, "wrong_status")],
)
async def test_decide_errors(allowed, monkeypatch, action, service, exc, status_code, code):
    monkeypatch.setattr(assistant, service, AsyncMock(side_effect=exc))
    body = {"rule_text": "決まり"} if action == "approve" else None
    resp = await _call(allowed, "post", f"{RULES_URL}/5/{action}", body)
    assert resp.status_code == status_code
    assert resp.json()["detail"] == {"code": code}


@pytest.mark.asyncio
async def test_approve_ok_and_full(allowed, monkeypatch):
    approve = AsyncMock(return_value=_rule(rule_text="決まり"))
    monkeypatch.setattr(assistant, "approve_candidate", approve)
    resp = await allowed.post(RULES_URL + "/5/approve", json={"rule_text": " 決まり "})
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "approved"
    assert approve.await_args.args[1:] == (999, 5, 999, "決まり")

    monkeypatch.setattr(assistant, "approve_candidate", AsyncMock(side_effect=RulesFull()))
    resp = await allowed.post(RULES_URL + "/5/approve", json={"rule_text": "決まり"})
    assert resp.status_code == 409
    assert resp.json()["detail"] == {"code": "rules_full"}


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [None, {"rule_text": ""}])
async def test_approve_needs_text(allowed, monkeypatch, body):
    approve = AsyncMock(return_value=_rule())
    monkeypatch.setattr(assistant, "approve_candidate", approve)
    resp = await _call(allowed, "post", RULES_URL + "/5/approve", body)
    assert resp.status_code == 422
    assert approve.await_count == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "action, service, status",
    [("reject", "reject_candidate", "rejected"), ("remove", "remove_rule", "removed")],
)
async def test_reject_and_remove_ok(allowed, monkeypatch, action, service, status):
    mock = AsyncMock(return_value=_rule(status=status))
    monkeypatch.setattr(assistant, service, mock)
    resp = await allowed.post(f"{RULES_URL}/5/{action}")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == status
    assert mock.await_args.args[1:] == (999, 5, 999)
```

## PG の試験の中身（`backend/tests/test_secretary_rules_service_pg.py`）

```python
"""ADR-1077 便2b: 決まり帳の読み書き（app/services/secretary_rules.py）を本物の PostgreSQL で試す
（design.md §11 の R1・R3・R4・R5・21 件目が入らない）。

PG（CI の使い捨て DB。pg fixture）。アプリの役割 salesanchor_app で、口と同じ set_tenant_context の会社文脈で呼ぶ。
表は本物の migration を流して作る（tests/test_secretary_rules_tables_pg.py の _setup）。テストデータはすべて架空。
"""

from __future__ import annotations

import asyncio
import os

import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.auth.dependencies import set_tenant_context
from app.services import secretary_rules as sr
from tests.test_secretary_rules_tables_pg import INSERT_RULE, _seed, _setup, needs_ci_pg
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture


def _engine(conn):
    url = make_url(os.environ["RLS_TEST_DATABASE_URL"]).set(
        database=conn.info.dbname, drivername="postgresql+asyncpg"
    )
    return create_async_engine(url, poolclass=NullPool)


async def _in_tenant(engine, tenant_id, fn, *, commit=True):
    """会社の文脈を張った 1 つの取引で fn(session) を呼ぶ。例外のときは戻して投げ直す。"""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        await set_tenant_context(session, tenant_id)
        try:
            result = await fn(session)
        except BaseException:
            await session.rollback()
            raise
        if commit:
            await session.commit()
        else:
            await session.rollback()
        return result


def _add_approved(cur, tenant_id, n):
    for i in range(n):
        cur.execute(INSERT_RULE, (tenant_id, "approved", f"fake rule {i}", tenant_id, "2026-11-12T02:00:00Z"))


def _one_id(cur, tenant_id, status):
    cur.execute(
        "SELECT id FROM public.secretary_rules WHERE tenant_id = %s AND status = %s ORDER BY id LIMIT 1",
        (tenant_id, status),
    )
    return cur.fetchone()[0]


def _approved_count(cur, tenant_id):
    cur.execute(
        "SELECT count(*) FROM public.secretary_rules WHERE tenant_id = %s AND status = 'approved'", (tenant_id,)
    )
    return cur.fetchone()[0]


@needs_ci_pg
def test_approved_texts_are_own_tenant_in_decided_order(pg):  # noqa: F811
    conn, _, _ = pg
    cur = _setup(conn)
    _seed(cur)
    cur.execute(INSERT_RULE, (999, "approved", "first rule", 999, "2026-11-11T00:00:00Z"))
    cur.execute(INSERT_RULE, (999, "approved", "second rule", 999, "2026-11-12T01:00:00Z"))

    async def main():
        engine = _engine(conn)
        try:
            own = await _in_tenant(engine, 999, lambda s: sr.list_approved_rule_texts(s, 999), commit=False)
            other = await _in_tenant(engine, 999, lambda s: sr.list_approved_rule_texts(s, 998), commit=False)
            return own, other
        finally:
            await engine.dispose()

    own, other = asyncio.run(main())
    assert own == ["first rule", "fake rule", "second rule"]  # 候補（fake candidate）とほかの会社は入らない
    assert other == []


@needs_ci_pg
def test_lists_are_own_tenant_only(pg):  # noqa: F811
    conn, _, _ = pg
    cur = _setup(conn)
    _seed(cur)

    async def main():
        engine = _engine(conn)
        try:
            cands = await _in_tenant(engine, 999, lambda s: sr.list_rules(s, 999, "candidate"), commit=False)
            approved = await _in_tenant(engine, 999, lambda s: sr.list_rules(s, 999, "approved"), commit=False)
            with pytest.raises(ValueError):
                await _in_tenant(engine, 999, lambda s: sr.list_rules(s, 999, "rejected"), commit=False)
            return cands, approved
        finally:
            await engine.dispose()

    cands, approved = asyncio.run(main())
    assert [(r.status, r.rule_text) for r in cands] == [("candidate", "fake candidate")]
    assert [(r.status, r.rule_text) for r in approved] == [("approved", "fake rule")]


@needs_ci_pg
def test_feedback_approve_remove_reject_flow(pg):  # noqa: F811
    conn, _, _ = pg
    cur = _setup(conn)
    _seed(cur)
    other_tenant_rule = _one_id(cur, 998, "candidate")

    async def main():
        engine = _engine(conn)
        try:
            cand = await _in_tenant(
                engine, 999, lambda s: sr.add_candidate(s, 999, 999, "", "fake source", "invoice", None)
            )
            assert cand.status == "candidate" and cand.rule_text == "" and cand.decided_at is None
            approved = await _in_tenant(
                engine, 999, lambda s: sr.approve_candidate(s, 999, cand.id, 999, "fake approved")
            )
            assert approved.status == "approved" and approved.rule_text == "fake approved"
            assert approved.decided_at is not None
            texts = await _in_tenant(engine, 999, lambda s: sr.list_approved_rule_texts(s, 999), commit=False)
            assert "fake approved" in texts
            removed = await _in_tenant(engine, 999, lambda s: sr.remove_rule(s, 999, cand.id, 999))
            assert removed.status == "removed"
            texts = await _in_tenant(engine, 999, lambda s: sr.list_approved_rule_texts(s, 999), commit=False)
            assert "fake approved" not in texts  # R4: 外すと次の頼みから送らない
            with pytest.raises(sr.RuleWrongStatus):
                await _in_tenant(engine, 999, lambda s: sr.remove_rule(s, 999, cand.id, 999))
            with pytest.raises(sr.RuleWrongStatus):
                await _in_tenant(engine, 999, lambda s: sr.approve_candidate(s, 999, cand.id, 999, "x"))

            idea = await _in_tenant(
                engine, 999, lambda s: sr.add_candidate(s, 999, 999, "fake idea", "fake source 2", "event", "r")
            )
            rejected = await _in_tenant(engine, 999, lambda s: sr.reject_candidate(s, 999, idea.id, 999))
            assert rejected.status == "rejected"
            with pytest.raises(sr.RuleWrongStatus):
                await _in_tenant(engine, 999, lambda s: sr.reject_candidate(s, 999, idea.id, 999))

            for rule_id in (other_tenant_rule, 999999):  # ほかの会社の番号は「無い」と同じ
                with pytest.raises(sr.RuleNotFound):
                    await _in_tenant(engine, 999, lambda s: sr.approve_candidate(s, 999, rule_id, 999, "x"))
                with pytest.raises(sr.RuleNotFound):
                    await _in_tenant(engine, 999, lambda s: sr.reject_candidate(s, 999, rule_id, 999))
                with pytest.raises(sr.RuleNotFound):
                    await _in_tenant(engine, 999, lambda s: sr.remove_rule(s, 999, rule_id, 999))
            return cand.id
        finally:
            await engine.dispose()

    rule_id = asyncio.run(main())
    cur.execute("SELECT status, decided_by FROM public.secretary_rules WHERE id = %s", (rule_id,))
    assert cur.fetchone() == ("removed", 999)
    cur.execute("SELECT status FROM public.secretary_rules WHERE id = %s", (other_tenant_rule,))
    assert cur.fetchone() == ("candidate",)  # ほかの会社の行は変わらない


@needs_ci_pg
def test_twenty_approved_refuses_more(pg):  # noqa: F811
    conn, _, _ = pg
    cur = _setup(conn)
    _seed(cur)
    _add_approved(cur, 999, 19)  # _seed の 1 件と合わせて 20 件
    cand_id = _one_id(cur, 999, "candidate")
    approved_id = _one_id(cur, 999, "approved")

    async def main():
        engine = _engine(conn)
        try:
            with pytest.raises(sr.RulesFull):
                await _in_tenant(engine, 999, lambda s: sr.add_approved_rule(s, 999, 999, "fake 21"))
            with pytest.raises(sr.RulesFull):
                await _in_tenant(engine, 999, lambda s: sr.approve_candidate(s, 999, cand_id, 999, "fake 21"))
            with pytest.raises(sr.RuleNotFound):
                await _in_tenant(engine, 999, lambda s: sr.approve_candidate(s, 999, 999999, 999, "x"))
            with pytest.raises(sr.RuleWrongStatus):
                await _in_tenant(engine, 999, lambda s: sr.approve_candidate(s, 999, approved_id, 999, "x"))
            # 上限は会社ごと（998 は 1 件なので入る）
            other = await _in_tenant(engine, 998, lambda s: sr.add_approved_rule(s, 998, 998, "fake other"))
            assert other.status == "approved"
        finally:
            await engine.dispose()

    asyncio.run(main())
    assert _approved_count(cur, 999) == 20
    assert _approved_count(cur, 998) == 2
    cur.execute("SELECT created_by, decided_by FROM public.secretary_rules WHERE rule_text = %s", ("fake other",))
    assert cur.fetchone() == (998, 998)  # R1: 決めた人が入る


@needs_ci_pg
def test_two_approvals_at_once_stop_at_twenty(pg):  # noqa: F811
    conn, _, _ = pg
    cur = _setup(conn)
    _seed(cur)
    _add_approved(cur, 999, 18)  # _seed の 1 件と合わせて 19 件

    async def main():
        engine = _engine(conn)
        added = asyncio.Event()

        async def first():
            async with AsyncSession(engine) as s:
                await set_tenant_context(s, 999)
                await sr.add_approved_rule(s, 999, 999, "fake 20th A")
                added.set()
                await asyncio.sleep(0.5)  # 鍵を持ったまま待つ（2 本目はこの間 鍵で待たされる）
                await s.commit()

        async def second():
            await added.wait()
            async with AsyncSession(engine) as s:
                await set_tenant_context(s, 999)
                try:
                    await sr.add_approved_rule(s, 999, 999, "fake 20th B")
                except sr.RulesFull:
                    await s.rollback()
                    return "full"
                await s.commit()
                return "added"

        try:
            _, result = await asyncio.gather(first(), second())
            return result
        finally:
            await engine.dispose()

    assert asyncio.run(main()) == "full"
    assert _approved_count(cur, 999) == 20
```

## 画面の直し

1 か所ずつ Edit で直す。「前」が 1 つだけ見つかること。

- `frontend/src/features/secretary/secretaryApi.ts` 56 行目。前: `export type SecretaryErrorKind = "notReady" | "busy" | "timeout" | "unreadable" | "generic" | "forbidden" | "authFailed" | "agentFailed";` → 後: `export type SecretaryErrorKind = "notReady" | "busy" | "timeout" | "unreadable" | "generic" | "forbidden" | "authFailed" | "agentFailed" | "rulesTooLong";`
- 同じファイル 64 行目 `  agent_failed: "agentFailed",` の次の行に `  rules_too_long: "rulesTooLong",` を 1 行足す。
- `frontend/src/locales/ja.json` 6088 行目。前: `      "agentFailed": "うまくいきませんでした。少し待ってからもう一度送ってください"` → 後: その行の最後に `,` を付け、次の行に `      "rulesTooLong": "決まりと文を合わせると長すぎます。文を短くするか、決まりを減らしてください"` を足す。
- `frontend/src/locales/en.json` 6088 行目。前: `      "agentFailed": "Something went wrong. Please wait a moment and send it again."` → 後: その行の最後に `,` を付け、次の行に `      "rulesTooLong": "Your message and the company rules are too long together. Shorten the message or remove some rules."` を足す。
- `frontend/src/features/secretary/SecretaryChat.test.tsx`: 173 行目から始まる試験 `it("shows the agentFailed text in full on 502 agent_failed, not the generic text", async () => {` の閉じ（181 行目 `  });`）の次に、空行を 1 つ置いてから次を足す（2 空白のインデント）。

```tsx
  it("shows the rulesTooLong text on 413 rules_too_long", async () => {
    mock.postWithTimeout.mockRejectedValue(new ApiError("x", 413, { code: "rules_too_long" }));
    renderChat();
    await sendMessage();
    expect(
      await screen.findByText("Your message and the company rules are too long together. Shorten the message or remove some rules."),
    ).toBeTruthy();
  });
```

（画面は `frontend/src/features/secretary/SecretaryChat.tsx:93` で種類をそのまま翻訳キーにして出す。部品・色・配置は触らない。）

## 触らない

- `migrations`（表は便1 で入っている）・`scripts`・`.github/workflows`（deploy.yml の注記も直さない）・`docker-compose*.yml`。
- `secretary-agent`・`secretary-codex` のすべて（容器・指示文・答えの形・compose.mjs）。
- `backend/app/schemas/assistant.py`・`backend/app/services/secretary_resolve.py`・`backend/app/services/ai_assignment.py`・`backend/app/routers/super_admin_ai_jobs.py`（容器の宛先は `agent_url` のまま。つながりの試しは `rules` を送らなくてよい）。
- 画面の部品・CSS・画面の型（答えの種類を足すのは便3）。
- design.md・kgi.md・recon.md・baseline.md・ADR（Opus が直す）。
- 本番のサーバー。

## 想定される分かれ道

- やること 9（会社の文脈の検査）で新しい口が Rule B・Rule C に当たる → 直さずに NEEDS_DECISION:（commit と張り直しの並びを変えてよいかは Opus が決める）。
- やること 10 で I001 以外の ruff の指摘 → 直さずに NEEDS_DECISION:。
- やること 11 で `/api/v1/assistant/rules` の行が 5 行でない（GET と POST は同じ道なので 1 行にまとまる。feedback・approve・reject・remove で計 5 行）→ BLOCKED:（grep の生出力）。
- やること 12 で今の秘書の試験（`tests/test_assistant_router.py`）が落ちる → 直さずに NEEDS_DECISION:（頼みの本文の作り方を変えた影響の恐れ。落ちた題と 40 行）。
- やること 12 で `test_size_boundary` だけが落ちる（時刻の文字の長さが変わる等）→ 直さずに NEEDS_DECISION:（`assistant._agent_payload("a", "sonnet", [])` の値と長さを添える）。
- やること 13 で今の秘書の画面の試験が落ちる → 直さずに NEEDS_DECISION:。
- `uv` が無い → やること 10 と 11 は BLOCKED:（11 の API の形は必須チェックが止めるため、書き出さずに出せない）。やること 12 は「未実行」として先へ進む。
- check-before-submit が落ちる → 直さずに、落ちた検査の名前とログの最後 30 行を添えて NEEDS_DECISION:。
- 「前」の文字が見つからない（誰かが先に直した）→ 補わずに BLOCKED:（その行の今の中身を添える）。

## Opus が合流の前に確かめること（実装役はしない）

- 本番に便1 の表 `public.secretary_rules` があること（読み取り専用の鍵で `to_regclass('public.secretary_rules')` を 1 回）。無いまま出すと、秘書の口がすべて 503 になる（決まりを読めないため）。
- PR の CI が緑であること。特に「pytest (SQLite + PostgreSQL RLS)」で `tests/test_secretary_rules_service_pg.py` の 5 件が skip ではなく通っていること（ログの件数で確かめる）・「API contract is up to date」・frontend-check。
- R6 の grep: `git diff origin/main...HEAD -- backend/app` に人の名前・会社や人の番号の直書きが無いこと（`is_super_admin` を見るのは `require_super_admin` だけ）。
- 合流と本番反映の後: 本番の秘書に 1 回頼んで今まで通り答えること（決まり 0 件なので送る頼みは `"rules":[]` だけ増える）・ログの code に `rules_unreadable` が出ていないこと。

## 終わりの報告（停止したときも同じ形で報告する）

- DONE: 受領確認の行・preflight の生出力・(1f) の出力・やること 9〜13 の結果（パスと貼る行）・commit 前の `git status --short`・commit の sha・check-before-submit の結果ファイルのパスと最後の 5 行・push の生出力。
- BLOCKED: 止まった手順・コマンド・生の出力。
- NEEDS_DECISION: 迷った点・選べる形・それぞれの影響。

END OF CARD
