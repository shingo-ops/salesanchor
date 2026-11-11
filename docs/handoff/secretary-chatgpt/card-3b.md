# 実装カード 段3b: 秘書の宛先を担当表で選ぶ・ChatGPT の選択肢3つ・本番に容器を出す段（backend・migration・deploy.yml）

設計者: Opus（2026-11-11）。設計: `docs/handoff/secretary-chatgpt/design.md` §4-1・§5-1（使用量）・§5-3・§5-4・§6-1・§7 の段3。決定: `docs/adr/ADR-1058-ai-job-assignments.md`（2026-11-03 PO が設計に「1」。2026-11-04 PO「1,まず私と担当エンジニアだけで使用する」。2026-11-11 PO「PRマージ、デプロイまで完走させてくれ。」）。
本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
担当: Sonnet（クラウド）。PR は作らない（手元の Opus が作る）。カード 段3a の commit が同じブランチに先にあること。
読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md・guards/03-file.md・guards/05-pr.md（照合: 場所は行番号ではなく前後の文字で決める／commit と push の後は git log で確かめる／PR はクラウドで作らない）。

## 受領確認
着手前に、作業場所のブランチが `release/secretary-codex-stage3` で、HEAD までに `docs/handoff/secretary-chatgpt/card-3b.md` と `secretary-codex/server.mjs` があることを報告の1行目に書く。

## カード発行前チェック（design-partner.md §5.5）
- 1 記号: パス・値・関数名はすべてバッククォートで囲んだ ○
- 2 下書き禁止: PR はクラウドで作らない ○
- 3 報告の宛先: 完了報告の本文に生出力を全文含める ○
- 4 1便1目的: 秘書を ChatGPT の容器にも送れるようにする backend と、その選択肢と、容器を本番に出す段だけ。容器の中身は 段3a ○
- 5 起点: ブランチ `release/secretary-codex-stage3`（段3a の commit の上） ○
- 6 書式の実例: PR 本文は手元の Opus が書く（該当なし） ○
- 7 合格基準: 試験の名前・差分のファイルの一覧・削除行のあるファイルまで書いた ○
- 8 名前を出す: 削除行は 4・5・6・8・9 の各節の「前」に名指しした ○
- 9 出力の上限: 一覧は `grep` と `head` で絞る ○
- 10 報告の型: 冒頭に「本報告はカード 段3b の実行結果である」、最終行は DONE / BLOCKED: / NEEDS_DECISION: ○
- 11 期待値: 数は実物から数える ○

## なぜ（短く）
段3a で ChatGPT の容器 `secretary-codex` を作った。backend は今、担当表の provider が claude の時だけ容器（`secretary-agent`）を呼び、ほかは「準備ができていません」にする。本カードで、provider が codex なら `secretary-codex` に送るようにし、容器が返す使用量（4つの数）と合図の数を受け取って台帳に入れる。画面で ChatGPT を選べるよう選択肢3つを migration で足す。本番の deploy で容器を作って起こす段を足す。担当は Claude のまま（切り替えは PO と担当エンジニアが画面で行う。段3の測定の後）。

## 禁止（名指し）
- 下の「触るファイル」以外を変えない。`secretary-codex/`・`secretary-agent/`・`frontend/`・`docker-compose*.yml` は変えない。
- `migrations/20261103_120000_create_ai_job_assignments.sql` を変えない（新しいファイルで足す）。
- 担当表の今の担当（`ai_job_assignments`）を変える SQL を書かない。選択肢の行を消す SQL を書かない。
- 本番・VPS・本番の鍵に触らない。docker をクラウドで動かさない。
- PR を作らない・マージしない。GO 記録を書かない。rebase・force push をしない。`git stash` を使わない。ファイルを消すコマンドを使わない。
- 今ある試験を消さない。書き換えるのは 9・10 節で名指しした所だけ。
- 見張り（フック）に止められたら、言い換えて同じことをしない。そこで止まる。

## 触るファイル（この9個だけ。ほかに docs/ のこのカード）
1. backend/app/schemas/assistant.py
2. backend/app/routers/assistant.py
3. backend/app/routers/super_admin_ai_jobs.py
4. migrations/20261111_120000_add_codex_secretary_choices.sql（新しいファイル）
5. scripts/run_all_migrations.sh
6. .github/workflows/deploy.yml
7. backend/tests/test_assistant_router.py
8. backend/tests/test_super_admin_ai_jobs.py
9. backend/tests/ops/test_ai_job_assignments_db.py

## 0. 着手前の確かめ（読むだけ。違えば停止して NEEDS_DECISION で返す）
- 0-1 `git log --oneline -5` に 段3a の commit がある。`test -f secretary-codex/server.mjs; echo $?` が 0。
- 0-2 `grep -n '_SDK_BY_PROVIDER' backend/app/routers/assistant.py` が2行（定義と使う所）。
- 0-3 `grep -n 'SECRETARY_AGENT_URL' backend/app/routers/assistant.py backend/app/routers/super_admin_ai_jobs.py` が assistant.py に2行・super_admin_ai_jobs.py に2行（import と /health）。
- 0-4 `grep -n 'class AgentEnvelope' -A5 backend/app/schemas/assistant.py` が `intent: Intent` と `total_cost_usd: float | None = None` の2欄だけ。
- 0-5 `grep -n '"codex": frozenset' backend/app/services/llm_budget.py` が1行で `{"codex-cli"}`。
- 0-6 `grep -n "CHECK (provider IN ('gemini', 'codex', 'claude'))" migrations/20261103_120000_create_ai_job_assignments.sql` が1行。
- 0-7 `test -e migrations/20261111_120000_add_codex_secretary_choices.sql; echo $?` が 1。`tail -2 scripts/run_all_migrations.sh` の最後の行が `run_sql migrations/20261109_200000_drop_staff_firebase_uid.sql`。
- 0-8 `grep -n 'name: Start secretary-agent (ADR-1056)' .github/workflows/deploy.yml` が1行。`grep -n 'name: Start secretary-codex' .github/workflows/deploy.yml` が0行。
- 0-9 `grep -n 'pydantic' backend/requirements.txt | head -2` が `pydantic[email]==2.10.6` を含む。

## 1. backend/app/schemas/assistant.py
1-1 import の行（ファイルの頭の `from pydantic import` の行）に `StrictInt` を足す（今の import の名前はそのまま。並びは今の並びに合わせる）。
1-2 `class AgentEnvelope(BaseModel):` の塊を次に置き換える。

前:
```python
class AgentEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: Intent
    total_cost_usd: float | None = None
```
後:
```python
class AgentUsage(BaseModel):
    """ADR-1058 段3: secretary-codex が返す使用量（turn.completed の4つ。どれも 0 以上の整数か None。design.md §5-1）。"""

    model_config = ConfigDict(extra="forbid")

    input_tokens: StrictInt | None = Field(default=None, ge=0)
    cached_input_tokens: StrictInt | None = Field(default=None, ge=0)
    output_tokens: StrictInt | None = Field(default=None, ge=0)
    reasoning_output_tokens: StrictInt | None = Field(default=None, ge=0)


class AgentEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: Intent
    total_cost_usd: float | None = None
    # ADR-1058 段3: secretary-codex だけが返す2欄（secretary-agent は返さないので None のまま。design.md §5-3）
    usage: AgentUsage | None = None
    error_events: StrictInt | None = Field(default=None, ge=0)
```
（`Field` が import に無ければ足す。0-4 の時に `grep -n '^from pydantic' backend/app/schemas/assistant.py` を報告に写す。）

## 2. backend/app/routers/assistant.py
2-1 import: `from app.schemas.assistant import (` の並びに `AgentUsage,` を `AgentEnvelope,` の次に足す。`from app.services.llm_budget import UsageCounts, record_usage_isolated` を `from app.services.llm_budget import USAGE_SDKS_BY_PROVIDER, UsageCounts, record_usage_isolated` にする。

2-2 宛先。前:
```python
SECRETARY_AGENT_URL = os.getenv("SECRETARY_AGENT_URL", "http://secretary-agent:8090")
AGENT_TIMEOUT_SECONDS = 85.0
```
後:
```python
SECRETARY_AGENT_URL = os.getenv("SECRETARY_AGENT_URL", "http://secretary-agent:8090")
SECRETARY_CODEX_URL = os.getenv("SECRETARY_CODEX_URL", "http://secretary-codex:8090")
AGENT_TIMEOUT_SECONDS = 85.0
```

2-3 provider の対応。前:
```python
# ADR-1058 秘1: 担当表の provider → 使用の記録の sdk。ここに無い provider は容器が無いので not_ready（codex は段3で足す）。
_SDK_BY_PROVIDER = {"claude": "claude-code"}
```
後:
```python
def agent_url(provider: str) -> str | None:
    """ADR-1058 段3: 担当表の provider → 秘書の容器の宛先（配線の正本はここ1か所。design.md §5-3）。

    ここに無い provider は容器が無いので None（呼び手は not_ready にする）。
    呼ぶたびにこのモジュールの値を読む（試験で宛先を差し替えられるように）。
    """
    return {"claude": SECRETARY_AGENT_URL, "codex": SECRETARY_CODEX_URL}.get(provider)


def _sdk_for(provider: str) -> str | None:
    """使用の記録の sdk（正本は llm_budget.USAGE_SDKS_BY_PROVIDER）。1つに決まらなければ None。"""
    sdks = USAGE_SDKS_BY_PROVIDER.get(provider, frozenset())
    return next(iter(sdks)) if len(sdks) == 1 else None
```

2-4 `_log` に合図の数を足す。前:
```python
def _log(user_id: int, tenant_id: int, started: float, code: str, cost: float | None = None) -> None:
    logger.info(
        "assistant_message user_id=%s tenant_id=%s seconds=%.2f code=%s total_cost_usd=%s",
        user_id,
        tenant_id,
        time.monotonic() - started,
        code,
        cost if cost is not None else "-",
    )
```
後:
```python
def _log(
    user_id: int,
    tenant_id: int,
    started: float,
    code: str,
    cost: float | None = None,
    error_events: int | None = None,
) -> None:
    # error_events は secretary-codex の error の合図の数（1回あたり1を超えた件数を段3で数える。design.md §5-1）
    logger.info(
        "assistant_message user_id=%s tenant_id=%s seconds=%.2f code=%s total_cost_usd=%s error_events=%s",
        user_id,
        tenant_id,
        time.monotonic() - started,
        code,
        cost if cost is not None else "-",
        error_events if error_events is not None else "-",
    )
```

2-5 台帳。前:
```python
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
後:
```python
def _counts_from(usage: AgentUsage | None) -> UsageCounts:
    """容器の使用量を台帳の列へ（design.md §5-1。tool_use_prompt_tokens・total_tokens は足し算で埋めず None）。"""
    if usage is None:
        return UsageCounts()
    return UsageCounts(
        prompt_tokens=usage.input_tokens,
        cached_content_tokens=usage.cached_input_tokens,
        candidates_tokens=usage.output_tokens,
        thoughts_tokens=usage.reasoning_output_tokens,
    )


async def _record_ledger(
    tenant_id: int,
    model: str,
    sdk: str,
    outcome: str,
    error_code: str | None,
    counts: UsageCounts | None = None,
) -> None:
    """秘書の1回の頼みを使用の記録に1行（別の取引ですぐ commit。失敗は record_usage_isolated がログに出して飲み込む）。"""
    await record_usage_isolated(
        purpose="secretary_intent",
        model=model,
        sdk=sdk,
        counts=counts if counts is not None else UsageCounts(),
        outcome=outcome,
        error_code=error_code,
        tenant_id=tenant_id,
    )
```

2-6 `_call_agent`。前の頭:
```python
async def _call_agent(text: str, model: str) -> dict:
    """容器を呼ぶ（model は担当表から読んだ値）。失敗は (HTTPException, ログの code) に直す。"""
    now = datetime.now(_JST).isoformat(timespec="seconds")
    try:
        async with httpx.AsyncClient(timeout=AGENT_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{SECRETARY_AGENT_URL}/intent",
```
後の頭:
```python
async def _call_agent(text: str, model: str, url: str) -> dict:
    """容器を呼ぶ（model は担当表から読んだ値・url は agent_url の値）。失敗は (HTTPException, ログの code) に直す。"""
    now = datetime.now(_JST).isoformat(timespec="seconds")
    try:
        async with httpx.AsyncClient(timeout=AGENT_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{url}/intent",
```
同じ関数の 502 の読み替え。前:
```python
        if agent_code == "cli_failed":
            raise _fail(502, "agent_failed", "cli_failed")
        raise _fail(502, "unreadable")
```
後:
```python
        if agent_code == "cli_failed":
            raise _fail(502, "agent_failed", "cli_failed")
        if agent_code == "tool_used":
            # ADR-1058 段3: 道具を使った合図で答えを捨てた（K2②。台帳の error_code も tool_used）
            raise _fail(502, "agent_failed", "tool_used")
        raise _fail(502, "unreadable")
```

2-7 `post_assistant_message` の①。前:
```python
    sdk = _SDK_BY_PROVIDER.get(assignment.provider)
    if sdk is None:
        _log(user_id, tenant_id, started, "not_ready", None)
        raise _fail(503, "not_ready")
```
後:
```python
    url = agent_url(assignment.provider)
    sdk = _sdk_for(assignment.provider)
    if url is None or sdk is None:
        _log(user_id, tenant_id, started, "not_ready", None)
        raise _fail(503, "not_ready")
```

2-8 ③。前:
```python
    cost: float | None = None
    try:
        raw = await _call_agent(body.text, assignment.model)
        try:
            envelope = AgentEnvelope.model_validate(raw)
        except ValidationError:
            raise _fail(502, "unreadable")
        cost = envelope.total_cost_usd
        intent = envelope.intent
```
後:
```python
    cost: float | None = None
    error_events: int | None = None
    try:
        raw = await _call_agent(body.text, assignment.model, url)
        try:
            envelope = AgentEnvelope.model_validate(raw)
        except ValidationError:
            raise _fail(502, "unreadable")
        cost = envelope.total_cost_usd
        error_events = envelope.error_events
        intent = envelope.intent
```
同じ所の except の中。前:
```python
        _log(user_id, tenant_id, started, log_code, cost)
        await _record_ledger(tenant_id, assignment.model, sdk, "failed", _ledger_error_code(log_code))
        raise
```
後:
```python
        _log(user_id, tenant_id, started, log_code, cost, error_events)
        await _record_ledger(tenant_id, assignment.model, sdk, "failed", _ledger_error_code(log_code))
        raise
```
ok の台帳。前:
```python
    await _record_ledger(tenant_id, assignment.model, sdk, "ok", None)
```
後:
```python
    await _record_ledger(tenant_id, assignment.model, sdk, "ok", None, _counts_from(envelope.usage))
```
最後のログ。前:
```python
    _log(user_id, tenant_id, started, "ok", cost)
```
後:
```python
    _log(user_id, tenant_id, started, "ok", cost, error_events)
```
2-9 ファイル頭の説明文の「利用者の文を容器 secretary-agent（DB を持たない）に渡し」を「利用者の文を担当表の provider の容器（claude は secretary-agent・codex は secretary-codex。どちらも DB を持たない）に渡し」にする（1か所だけ）。

## 3. backend/app/routers/super_admin_ai_jobs.py
3-1 import。前: `from app.routers.assistant import SECRETARY_AGENT_URL` → 後: `from app.routers.assistant import agent_url`。`import re` が無ければ足す（標準の import の並びに）。

3-2 `_secretary_agent_ready` と `_agent_ready_for` の2つの関数を次に置き換える（前の2つの関数は丸ごと消える。ほかの関数は変えない）。
前:
```python
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
```
後:
```python
# codex の auth.json の last_refresh（例 2026-11-11T00:00:00.123456789Z）。秒の下は6桁に切ってから読む。
_REFRESHED_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d+))?(Z|[+-]\d{2}:\d{2})$")


async def _secretary_health(url: str) -> dict | None:
    """秘書の容器の /health を 2 秒で読む。200 で JSON の dict なら返す。返らない・届かない・形が違えば None。"""
    try:
        async with httpx.AsyncClient(timeout=HEALTH_TIMEOUT_SECONDS) as client:
            res = await client.get(f"{url}/health")
        body = res.json() if res.status_code == 200 else None
    except (httpx.HTTPError, ValueError):
        return None
    return body if isinstance(body, dict) else None


def _parse_refreshed(value: object) -> datetime | None:
    """codex のログインの更新日時を読む。読めなければ None（推測で埋めない）。"""
    if not isinstance(value, str):
        return None
    m = _REFRESHED_RE.match(value)
    if m is None:
        return None
    frac = f".{m.group(2)[:6]}" if m.group(2) else ""
    zone = "+00:00" if m.group(3) == "Z" else m.group(3)
    try:
        return datetime.fromisoformat(f"{m.group(1)}{frac}{zone}")
    except ValueError:
        return None


async def _agent_state_for(job: AiJobRow) -> tuple[bool | None, datetime | None]:
    """秘書の行だけ容器を見る（ready と、codex の時だけログインの更新日時）。ほかの行は (None, None)。

    宛先は assistant.agent_url（配線の正本）。容器の無い provider は not_ready。
    """
    if job.job_key != _SECRETARY_JOB_KEY:
        return None, None
    url = agent_url(job.provider)
    if url is None:
        return False, None
    health = await _secretary_health(url)
    if health is None or health.get("ready") is not True:
        return False, None
    refreshed = _parse_refreshed(health.get("last_refresh")) if job.provider == "codex" else None
    return True, refreshed
```
3-3 `_job_out` の中。前:
```python
    agent_ready = await _agent_ready_for(job)
```
後:
```python
    agent_ready, refreshed_at = await _agent_state_for(job)
```
前:
```python
        # 段2ではいつも null（codex のログインの更新日は段3で入れる）
        login_refreshed_at=None,
```
後:
```python
        # secretary_intent で provider=codex の時だけ値（design.md §6-1）
        login_refreshed_at=refreshed_at,
```
3-4 `_login_state` の docstring の「agent_ready は秘書の行だけ真偽」はそのまま。ほかは変えない。

## 4. migrations/20261111_120000_add_codex_secretary_choices.sql（新しいファイル・全文）
```sql
-- ADR-1058 段3: 秘書（secretary_intent）の選択肢に ChatGPT（codex）の3つを足す。足すだけ。今の担当は変えない（Claude のまま）。
-- 設計: docs/handoff/secretary-chatgpt/design.md §4-1（「codex の3行は段3の migration で足す」）・§7 の段3。
-- モデルの名前は手元の Codex CLI の一覧（docs/handoff/secretary-chatgpt/recon.md の 2026-11-02 の取得）で3つとも答えを返したもの。
-- 流し直しても壊れない: UNIQUE(job_key, provider, model) に当たれば何もしない（ON CONFLICT DO NOTHING）。
-- 表と provider の CHECK は migrations/20261103_120000_create_ai_job_assignments.sql が作る（その後に流す）。
--
-- 戻し方（流すのは PO。先に画面で秘書の担当を Claude に戻す。担当が codex の行を指していると外部キーで止まる）:
--   選択肢の表から job_key='secretary_intent' かつ provider='codex' の3行を外す。
BEGIN;

INSERT INTO public.ai_job_choices (job_key, provider, model) VALUES
    ('secretary_intent', 'codex', 'gpt-6-luna'),
    ('secretary_intent', 'codex', 'gpt-5.6-terra'),
    ('secretary_intent', 'codex', 'gpt-5.6-luna')
ON CONFLICT DO NOTHING;

COMMIT;
```

## 5. scripts/run_all_migrations.sh
ファイルの最後の行 `run_sql migrations/20261109_200000_drop_staff_firebase_uid.sql` の後ろに2行足す（ほかは変えない）:
```bash
# ADR-1058 段3: 秘書の選択肢に ChatGPT（codex）の3つを足す（足すだけ・冪等・今の担当は変えない）
run_sql migrations/20261111_120000_add_codex_secretary_choices.sql
```

## 6. .github/workflows/deploy.yml
「Start secretary-agent (ADR-1056)」の段の最後の行（`            exit 0`）の後、次の空行と `      # SA-18 Phase2: salesanchor_app ロールの bootstrap（冪等）` の前に、空行1つと次の段を足す（ほかの段は変えない）。
```yaml
      # ADR-1058 段3: ChatGPT の秘書の容器（secretary-codex）を作って起こす。secretary-agent と同じく付け足しの機能なので、
      # どの手順が失敗してもアプリの反映は止めない（警告だけ出して exit 0。continue-on-error と command_timeout も同じ）。
      # 秘密のファイルは持たない（ログインの鍵は名前付きボリューム secretary-codex-home の中。PO が scripts/ops/secretary-codex-login.sh で入れる）。
      # build はリポジトリの根を context にし、secretary-codex/Dockerfile.dockerignore の許す一覧の4ファイルだけを入れる（design.md §5-1・§5-4）。
      - name: Start secretary-codex (ADR-1058)
        if: ${{ success() }}
        continue-on-error: true
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.VPS_HOST }}
          username: ${{ secrets.VPS_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          command_timeout: 10m
          script: |
            cd /home/ubuntu/salesanchor
            df -h / | tail -1
            if ! DOCKER_BUILDKIT=1 docker build -t astro-webapp-secretary-codex -f secretary-codex/Dockerfile .; then
              echo "::warning::secretary-codex のイメージを作れませんでした（アプリの反映には影響しません）"
              exit 0
            fi
            codex_version="$(docker run --rm --entrypoint codex astro-webapp-secretary-codex --version 2>/dev/null || true)"
            echo "codex_version=${codex_version}"
            if [ "$codex_version" != "codex-cli 0.162.1" ]; then
              echo "::warning::secretary-codex の codex の版が 0.162.1 ではないため起こしません"
              exit 0
            fi
            probe_rc=0
            docker run --rm --network astro-webapp_frontnet --read-only --cap-drop ALL --security-opt no-new-privileges:true \
              -e PROBE_HTTPS_URL=https://chatgpt.com/ astro-webapp-secretary-codex node /app/probe.mjs || probe_rc=$?
            if [ "$probe_rc" -eq 1 ]; then
              echo "::warning::K4 不合格: secretary-codex から DB か redis に届きました"
            elif [ "$probe_rc" -ne 0 ]; then
              echo "::warning::secretary-codex の probe を流せませんでした（終了コード $probe_rc）"
            fi
            docker compose -p astro-webapp-secretary-codex -f docker-compose.secretary-codex.yml up -d --force-recreate --no-build \
              || echo "::warning::secretary-codex を起こせませんでした（アプリの反映には影響しません）"
            exit 0
```
（字下げは前の段と同じ。`python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/deploy.yml'))"` が通ること。）

## 7. backend/tests/test_assistant_router.py（足す・名指しの所だけ直す）
7-1 直す: `_codex_assignment` の関数を次に置き換える（試験の意味は「容器の無い provider は 503 で容器も台帳も呼ばない」のまま。codex は容器ができたので gemini にする）。
前:
```python
async def _codex_assignment(db, job_key):
    return AiAssignment("codex", "gpt-x")
```
後:
```python
async def _gemini_assignment(db, job_key):
    # 秘書の容器が無い provider（ADR-1058 段3 で codex は secretary-codex に送るようになった）
    return AiAssignment("gemini", "gemini-x")
```
同じく `@pytest.mark.parametrize("reader", [_raise_db_down, _codex_assignment])` を `@pytest.mark.parametrize("reader", [_raise_db_down, _gemini_assignment])` にする。
7-2 足す（`test_agent_failures` の parametrize の並びに1行）: `(502, {"code": "tool_used"}, 502, "agent_failed"),` を `(502, {"code": "cli_failed"}, 502, "agent_failed"),` の次に。
7-3 足す（`test_ledger_failed_row_for_agent_failures` の parametrize の並びに1行）: `(502, {"code": "tool_used"}, "tool_used"),` を `(502, {"code": "cli_failed"}, "other"),` の次に。
7-4 足す（ファイルの最後に、次の全文）:
```python
# ---- ADR-1058 段3: ChatGPT の容器（secretary-codex） ------------------------------


def _codex_envelope(**over) -> dict:
    env = _fixture("envelope-invoice.json")
    env.pop("total_cost_usd", None)
    env["usage"] = {"input_tokens": 10, "cached_input_tokens": 2, "output_tokens": 5, "reasoning_output_tokens": 3}
    env["error_events"] = 1
    env.update(over)
    return env


@pytest.fixture
def codex(allowed, monkeypatch):
    async def _assignment(db, job_key):
        return AiAssignment("codex", "gpt-5.6-luna")

    monkeypatch.setattr(assistant, "get_ai_assignment", _assignment)
    monkeypatch.setattr(assistant, "SECRETARY_AGENT_URL", "http://agent.test")
    monkeypatch.setattr(assistant, "SECRETARY_CODEX_URL", "http://codex.test")
    return allowed


def test_agent_url_mapping(monkeypatch):
    monkeypatch.setattr(assistant, "SECRETARY_AGENT_URL", "http://agent.test")
    monkeypatch.setattr(assistant, "SECRETARY_CODEX_URL", "http://codex.test")
    assert assistant.agent_url("claude") == "http://agent.test"
    assert assistant.agent_url("codex") == "http://codex.test"
    assert assistant.agent_url("gemini") is None
    assert assistant._sdk_for("claude") == "claude-code"
    assert assistant._sdk_for("codex") == "codex-cli"


@pytest.mark.asyncio
async def test_codex_goes_to_codex_container_with_model(codex, monkeypatch):
    sent = {}

    def handler(request: httpx.Request) -> httpx.Response:
        sent.update(json.loads(request.content))
        sent["url"] = str(request.url)
        return httpx.Response(200, json=_codex_envelope())

    _mock_agent(monkeypatch, handler)
    resp = await codex.post(URL, json={"text": "請求書"})
    assert resp.status_code == 200, resp.text
    assert sent["url"] == "http://codex.test/intent"
    assert sent["model"] == "gpt-5.6-luna"
    assert resp.json()["draft"]["company_name"] == "サンプル商事"


@pytest.mark.asyncio
async def test_claude_still_goes_to_agent_container(allowed, monkeypatch):
    monkeypatch.setattr(assistant, "SECRETARY_AGENT_URL", "http://agent.test")
    monkeypatch.setattr(assistant, "SECRETARY_CODEX_URL", "http://codex.test")
    sent = {}

    def handler(request: httpx.Request) -> httpx.Response:
        sent["url"] = str(request.url)
        return httpx.Response(200, json=_fixture("envelope-invoice.json"))

    _mock_agent(monkeypatch, handler)
    resp = await allowed.post(URL, json={"text": "a"})
    assert resp.status_code == 200, resp.text
    assert sent["url"] == "http://agent.test/intent"


@pytest.mark.asyncio
async def test_codex_ledger_ok_row_has_usage(codex, monkeypatch):
    _mock_agent(monkeypatch, _respond(200, _codex_envelope()))
    resp = await codex.post(URL, json={"text": "a"})
    assert resp.status_code == 200, resp.text
    kwargs = assistant.record_usage_isolated.await_args.kwargs
    assert kwargs["sdk"] == "codex-cli"
    assert kwargs["model"] == "gpt-5.6-luna"
    assert kwargs["outcome"] == "ok"
    assert kwargs["counts"] == UsageCounts(
        prompt_tokens=10, cached_content_tokens=2, candidates_tokens=5, thoughts_tokens=3
    )


@pytest.mark.asyncio
async def test_codex_usage_nulls_stay_null(codex, monkeypatch):
    usage = {"input_tokens": None, "cached_input_tokens": None, "output_tokens": None, "reasoning_output_tokens": None}
    _mock_agent(monkeypatch, _respond(200, _codex_envelope(usage=usage)))
    resp = await codex.post(URL, json={"text": "a"})
    assert resp.status_code == 200, resp.text
    assert assistant.record_usage_isolated.await_args.kwargs["counts"] == UsageCounts()


@pytest.mark.asyncio
async def test_codex_tool_used_is_recorded(codex, monkeypatch, caplog):
    _mock_agent(monkeypatch, _respond(502, {"code": "tool_used"}))
    with caplog.at_level(logging.INFO, logger=assistant.logger.name):
        resp = await codex.post(URL, json={"text": "a"})
    assert resp.status_code == 502
    assert resp.json()["detail"] == {"code": "agent_failed"}
    kwargs = assistant.record_usage_isolated.await_args.kwargs
    assert (kwargs["outcome"], kwargs["error_code"], kwargs["sdk"]) == ("failed", "tool_used", "codex-cli")
    lines = [r.getMessage() for r in caplog.records if "assistant_message" in r.getMessage()]
    assert len(lines) == 1
    assert "code=tool_used" in lines[0]


@pytest.mark.asyncio
async def test_codex_log_has_error_events_without_text(codex, monkeypatch, caplog):
    _mock_agent(monkeypatch, _respond(200, _codex_envelope(error_events=2)))
    with caplog.at_level(logging.INFO, logger=assistant.logger.name):
        resp = await codex.post(URL, json={"text": SECRET_TEXT})
    assert resp.status_code == 200, resp.text
    lines = [r.getMessage() for r in caplog.records if "assistant_message" in r.getMessage()]
    assert len(lines) == 1
    assert "code=ok" in lines[0] and "error_events=2" in lines[0] and "total_cost_usd=-" in lines[0]
    assert SECRET_TEXT not in "\n".join(r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "label,over",
    [
        ("usage extra key", {"usage": {"input_tokens": 1, "cache_write_input_tokens": 0}}),
        ("usage negative", {"usage": {"input_tokens": -1}}),
        ("usage string", {"usage": {"input_tokens": "5"}}),
        ("usage float", {"usage": {"input_tokens": 1.5}}),
        ("usage bool", {"usage": {"input_tokens": True}}),
        ("error_events negative", {"error_events": -1}),
        ("error_events string", {"error_events": "1"}),
    ],
)
async def test_codex_bad_envelope_is_unreadable(codex, monkeypatch, label, over):
    _mock_agent(monkeypatch, _respond(200, _codex_envelope(**over)))
    resp = await codex.post(URL, json={"text": "a"})
    assert resp.status_code == 502, label
    assert resp.json()["detail"] == {"code": "unreadable"}
    assert assistant.record_usage_isolated.await_args.kwargs["error_code"] == "unreadable"


@pytest.mark.asyncio
async def test_codex_unreachable_is_not_ready(codex, monkeypatch):
    def handler(request):
        raise httpx.ConnectError("refused")

    _mock_agent(monkeypatch, handler)
    resp = await codex.post(URL, json={"text": "a"})
    assert resp.status_code == 503
    assert resp.json()["detail"] == {"code": "not_ready"}
    kwargs = assistant.record_usage_isolated.await_args.kwargs
    assert (kwargs["error_code"], kwargs["sdk"]) == ("not_ready", "codex-cli")
```

## 8. backend/tests/test_super_admin_ai_jobs.py（名指しの所だけ直す・足す）
8-1 直す（`wired` の中の1行）: `monkeypatch.setattr(mod, "_secretary_agent_ready", AsyncMock(return_value=True))` → `monkeypatch.setattr(mod, "_secretary_health", AsyncMock(return_value={"ready": True, "last_refresh": None}))`。
8-2 直す（`test_secretary_row_is_not_ready_when_agent_is_down` の中の1行）: `monkeypatch.setattr(mod, "_secretary_agent_ready", AsyncMock(return_value=False))` → `monkeypatch.setattr(mod, "_secretary_health", AsyncMock(return_value=None))`。
8-3 直す（`test_agent_health_unreachable_is_false` の関数を丸ごと次に）:
```python
@pytest.mark.asyncio
async def test_agent_health_unreachable_is_none():
    """容器に届かない時は例外を出さず None（2 秒の打ち切りと同じ扱い）。"""
    assert await mod._secretary_health("http://127.0.0.1:9") is None
```
8-4 足す（ファイルの最後に、次の全文）:
```python
# --- ADR-1058 段3: ChatGPT の容器の ready とログインの更新日時 ------------------------


def _codex_jobs() -> list[AiJobRow]:
    rows = _jobs()
    return [
        AiJobRow(j.job_key, j.choice_id, "codex", "gpt-5.6-luna", (AiChoice(j.choice_id, "codex", "gpt-5.6-luna"),))
        if j.job_key == "secretary_intent"
        else j
        for j in rows
    ]


@pytest.mark.asyncio
async def test_codex_row_reads_codex_health_and_refreshed_at(wired, monkeypatch):
    monkeypatch.setattr(mod, "list_ai_jobs", AsyncMock(return_value=_codex_jobs()))
    health = AsyncMock(return_value={"ready": True, "last_refresh": "2026-11-11T00:00:00.123456789Z"})
    monkeypatch.setattr(mod, "_secretary_health", health)
    db = _FakeDb()
    async with _client(_app(db, _user(super_admin=True, role="admin"))) as c:
        r = await c.get("/api/v1/super-admin/ai-jobs")
    assert r.status_code == 200, r.text
    health.assert_awaited_once()
    from app.routers.assistant import agent_url

    assert health.await_args.args == (agent_url("codex"),)
    row = next(j for j in r.json()["jobs"] if j["job_key"] == "secretary_intent")
    assert (row["login_ok"], row["login_reason"]) == (True, None)
    got = datetime.fromisoformat(row["login_refreshed_at"].replace("Z", "+00:00"))
    assert got == datetime(2026, 11, 11, 0, 0, 0, 123456, tzinfo=timezone.utc)
    others = [j for j in r.json()["jobs"] if j["job_key"] != "secretary_intent"]
    assert all(j["login_refreshed_at"] is None for j in others)


@pytest.mark.asyncio
async def test_claude_row_has_no_refreshed_at(wired, monkeypatch):
    monkeypatch.setattr(mod, "_secretary_health", AsyncMock(return_value={"ready": True, "last_refresh": "2026-11-11T00:00:00Z"}))
    db = _FakeDb()
    async with _client(_app(db, _user(super_admin=True, role="admin"))) as c:
        r = await c.get("/api/v1/super-admin/ai-jobs")
    row = next(j for j in r.json()["jobs"] if j["job_key"] == "secretary_intent")
    assert row["login_ok"] is True
    assert row["login_refreshed_at"] is None


@pytest.mark.asyncio
async def test_codex_row_not_logged_in_is_not_ready(wired, monkeypatch):
    monkeypatch.setattr(mod, "list_ai_jobs", AsyncMock(return_value=_codex_jobs()))
    monkeypatch.setattr(mod, "_secretary_health", AsyncMock(return_value={"ready": False, "last_refresh": None}))
    db = _FakeDb()
    async with _client(_app(db, _user(super_admin=True, role="admin"))) as c:
        r = await c.get("/api/v1/super-admin/ai-jobs")
    row = next(j for j in r.json()["jobs"] if j["job_key"] == "secretary_intent")
    assert (row["login_ok"], row["login_reason"], row["login_refreshed_at"]) == (False, "not_ready", None)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-11-11T00:00:00Z", datetime(2026, 11, 11, tzinfo=timezone.utc)),
        ("2026-11-11T09:00:00+09:00", datetime(2026, 11, 11, tzinfo=timezone.utc)),
        ("2026-11-11T00:00:00.5Z", datetime(2026, 11, 11, 0, 0, 0, 500000, tzinfo=timezone.utc)),
        ("2026-11-11", None),
        ("あした", None),
        (123, None),
        (None, None),
        ("2026-13-40T00:00:00Z", None),
    ],
)
def test_parse_refreshed(value, expected):
    assert mod._parse_refreshed(value) == expected
```
（`AiChoice`・`datetime`・`timezone` の import が無ければ、ファイルの頭の今の import の並びに足す。0-3 の時に `sed -n 1,30p backend/tests/test_super_admin_ai_jobs.py` を報告に写す。）
8-5 `test_k11_only_secretary_is_switchable` の `assert all(j["login_refreshed_at"] is None for j in jobs)` はそのまま（`wired` の last_refresh は None なので通る）。

## 9. backend/tests/ops/test_ai_job_assignments_db.py（足すだけ）
9-1 定数を足す: `_AI_JOB_SQL = "20261103_120000_create_ai_job_assignments.sql"` の次の行に `_CODEX_CHOICES_SQL = "20261111_120000_add_codex_secretary_choices.sql"`。
9-2 ファイルの最後に次を足す:
```python
def test_g_codex_choices_added_once_and_assignment_kept(db):
    """ADR-1058 段3: codex の選択肢3つが足され、流し直しても増えず、秘書の担当は claude・sonnet のまま。"""
    c = db.cursor()
    c.execute(_read(_AI_JOB_SQL))
    c.execute(_read(_CODEX_CHOICES_SQL))
    c.execute(_read(_AI_JOB_SQL))
    c.execute(_read(_CODEX_CHOICES_SQL))
    assert _count(db, "ai_job_choices") == 20
    assert _rows(
        db,
        "SELECT model FROM public.ai_job_choices WHERE job_key = 'secretary_intent' AND provider = 'codex' ORDER BY model",
    ) == [("gpt-5.6-luna",), ("gpt-5.6-terra",), ("gpt-6-luna",)]
    assert _assignment(db, "secretary_intent") == ("claude", "sonnet")
    assert _count(db, "ai_job_assignment_history") == 0
```

## 14. 確かめ方
- `cd backend && python -m pytest tests/test_assistant_router.py tests/test_super_admin_ai_jobs.py -q` の最後の15行を写す（落ちが0）。
- `cd backend && python -m pytest tests/ops/test_ai_job_assignments_db.py -q` の最後の10行を写す（クラウドに PostgreSQL が無ければ skip になる。その時は skip の行を写し「実 DB の試験は CI で確かめる」と書く）。
- `cd backend && python -m pytest tests/test_realtime_topics.py -q` の最後の5行（変えていないので通るはず）。
- `cd backend && python -m ruff check app/routers/assistant.py app/routers/super_admin_ai_jobs.py app/schemas/assistant.py tests/test_assistant_router.py tests/test_super_admin_ai_jobs.py tests/ops/test_ai_job_assignments_db.py` と `python -m ruff format --check` の同じ6ファイル（ruff が無ければ「無い」と書く）。
- `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/deploy.yml')); print('yaml ok')"`。
- `grep -rn '_SDK_BY_PROVIDER\|_secretary_agent_ready\|_agent_ready_for' backend/ | head -5` が0行。
- `git diff origin/main...HEAD --name-only` が 段3a の7ファイル・カード2枚・本カードの9ファイル（と手元の Opus が先に積んだ docs/）だけ。
- `git diff origin/main...HEAD --numstat -- backend migrations scripts/run_all_migrations.sh .github/workflows/deploy.yml` の削除の数（2列目）を写す。削除があってよいのは 1〜3・7・8 の5ファイルだけ。`migrations/`・`scripts/run_all_migrations.sh`・`deploy.yml`・`test_ai_job_assignments_db.py` に削除があれば、その `^-` の行（`grep` と `head -30`）を出して停止。
- `bash scripts/dev/check-before-submit.sh` があれば流し、最後の20行と終了コードを写す。
- 生出力は作業場所の外の一時フォルダに保存し、パスと全文を報告に書く。

## 15. 想定される分岐と止まる条件
- 0 の前提が違う → 停止し NEEDS_DECISION:（違った所の生出力を付ける）。
- 前の文字が見つからない（ファイルが先に変わっていた） → 停止し NEEDS_DECISION:（その所の今の行を `grep -n` で写す）。
- `StrictInt | None = Field(default=None, ge=0)` が pydantic で受け付けられない → 停止し NEEDS_DECISION:（例外の全文）。勝手に別の書き方にしない。
- 今ある試験が落ちる → 本カードの名指しの所以外の試験なら停止し、落ちた試験の名前と出力を写す（期待を書き換えない）。
- 迷ったら停止して NEEDS_DECISION: で Opus に戻す。
- 終わったら commit（最後の行は `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）→ `git log -1` で確かめる → `git push origin release/secretary-codex-stage3` → `git log origin/release/secretary-codex-stage3 -1` で確かめる。PR は作らない。

## 合格の基準（手元の Opus が確かめる）
| 基準 | 確かめ方 |
|---|---|
| codex の担当なら secretary-codex に model 付きで送る・claude は今のまま | 試験 `test_codex_goes_to_codex_container_with_model`・`test_claude_still_goes_to_agent_container` |
| 容器の返事の usage・error_events で ValidationError が0件（§7 段3の基準） | 試験 `test_codex_ledger_ok_row_has_usage`・`test_codex_usage_nulls_stay_null` |
| 道具の合図は tool_used として台帳とログに残る（K2②） | 試験 `test_codex_tool_used_is_recorded`・`test_ledger_failed_row_for_agent_failures` の tool_used の行 |
| 選択肢は3つ足すだけ・担当は Claude のまま・流し直しても同じ | 試験 `test_g_codex_choices_added_once_and_assignment_kept`（CI の実 DB） |
| 画面のログインの○×と更新日時は codex の行だけ | 試験 `test_codex_row_reads_codex_health_and_refreshed_at` ほか3本 |
| 本番の deploy で容器を作って起こす（失敗しても反映は止めない） | deploy.yml の新しい段（Actions のログの `codex_version=` と probe の行） |

## 報告の型
- 1行目: 受領確認。2行目: 「本報告はカード 段3b の実行結果である」。
- 本文: 0-1〜0-9 の生出力、「14. 確かめ方」の生出力、commit と push の後の git log の出力（すべて全文）。
- 止まった時: 止まった所（節の番号）・最後に実行したコマンド・止まった理由。
- 最終行: DONE / BLOCKED: / NEEDS_DECISION: のどれか1つで始める。

END OF CARD
