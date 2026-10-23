<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# 実装カード discord-pdca 便1.5 — 保守 API に Discord 発の件の入口を足す

> この文書は何か：Discord の不具合報告を障害記録の表に1件1行で残すため、Sales Anchor の保守 API に「人の報告から行を作る口」「件を閉じる口」と、出来事の口の「回の記録（`round`）」を足す作業指示書です。表の形は変えません（migration なし）。

**対象ADR**: ADR-1039（Proposed。Decision 10 で Discord 発の行を障害記録の表に入れる）、ADR-1012（障害記録の表と保守 API）  
**recon**: docs/handoff/discord-pdca-bin15/recon.md  
**設計**: agent-console リポジトリ docs/handoff/discord-pdca/design.md 第13版 §4-9・§8 便1.5・§11（別リポジトリのためバッククォートなし）  
**日付**: 2026-10-23  
**状態**: カード草案（Opus 作成）。審査は別の窓の審査役。PO の判断は「次の段階の指示書を作り、作る係に作らせる」（2026-10-23「1」）。本番に入れる前に PO に聞く  
**危険便**: いいえ（`migrations/`・`.github/workflows/deploy.yml`・本番 `scripts/` を含まない）。ただし main に入ると backend が本番に入る（recon §3）。担当はマージしない  
**担当**: 実装 Sonnet／コード審査・PO への確認・GO 記録・マージ・反映確認 Opus

---

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は ready で作る（Draft にしない）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（保守 API の口2つと `round`・大きさの検査・欄の絞りだけ。agent-console 側は便2） |
| 5 | 既存ブランチへの追記ではない（新規ブランチ） | ○（release/discord-pdca-bin15） |
| 6 | 書式は実例で示した | ○（§4 に完成形のコード） |
| 7 | 合格基準を出力まで縛った | ○（§5・§7） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-2） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○（§11・受領確認・END OF CARD） |
| 11 | 期待値は実物から | ○（origin/main cc000952f で行番号を読んだ。recon §2） |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§12） |

## 受領確認

担当は報告の冒頭に「本報告はカード discord-pdca 便1.5 の実行結果である」と書く。

## 1. 範囲

- 足すもの（`backend/app/routers/ops.py` の1ファイルに全部置く。口を別のファイルに分けない）:
  1. `POST /api/v1/ops/incidents/human` … 人の報告（Discord の投稿）から障害記録の行を1つ作る。同じ投稿なら作らずに既存の行を返す。
  2. `POST /api/v1/ops/incidents/{incident_id}/close` … Discord 発の行だけを閉じ、出来事 `result`（pass）を1つ足す。
  3. 既存の `POST /api/v1/ops/incidents/{incident_id}/events` に、省略できる `round` を足す。`detail` の大きさの検査（8000 バイト）と、Discord 発の行で書かせない5つの欄の拒否を足す。
- 通知の台帳 `backend/app/realtime/topics.py` に新しい2つの口を足す。
- 試験は `backend/tests/test_ops_router.py` に足す。openapi を作り直して `frontend/api-contract/openapi.json` をコミットする。
- 対象外（触らない）:
  - 表の形（列・制約・RLS）。migration を作らない。
  - 既存の受け口 `ingest_alertmanager`（`backend/app/routers/ops.py:213-267`）と `_UPSERT_INCIDENT_SQL`（:161-180）。1文字も変えない。
  - 読む口（:275-326）・全停止の口（:406-489）・鍵の関数（:85-133）。
  - `round` を省いた出来事の口の振る舞い（`detail` の形・答えの形・状態コード）。既存の試験は1つも書き換えない。
  - agent-console のリポジトリ（便2 で使う側を作る）。
  - `frontend/src/` の画面（この口は画面から呼ばない）。

## 2. 前提の事実と設計の細部

- 事実（recon §2）:
  - 出来事の `actor` は alertmanager/ops_token/super_admin だけ許される（mig :57）。新しい口は `require_ops_reader` を使い、その戻りの `who["actor"]`（`ops_token` か `super_admin`）をそのまま書く。表を変えずに済む。
  - `round` を書く出来事の `kind` は `ai`（設計 §4-9）。既存の Literal（ops.py:352）と制約（mig :55）の両方に `ai` がある。
  - 人の報告の行は `_UPSERT_INCIDENT_SQL` では作れない（衝突時に `notify_count` を増やして `status` を上書きする。時刻が `now()`。recon 不明点3）。新しい SQL（`ON CONFLICT DO NOTHING`）を足す。
  - Discord 発の行は `labels->>'source' = 'discord'` で見分ける（ADR-1039 Decision 10）。`labels` を書き換える口は無い。
- 設計の細部（Opus の技術判断。設計 §4-9 の目的・範囲を変えない）:
  - 鍵: 3つの口とも `require_ops_reader`（保守の鍵か super admin のログイン）。既存の出来事の口（ops.py:361）と同じ。取り込み用の鍵（Alertmanager）は 401。
  - 人の報告の入力は `message_id`（数字1〜20桁）・`posted_at`（時差付きの時刻。時差の無い時刻は 422）・`message_url`（`https://discord.com/channels/<数字>/<数字>/<数字>` の形で、最後の数字が `message_id` と同じ）・`test`（真偽。省略は false）。ほかの名前は 422。
  - `labels` は `{"source": "discord", "message_url": ...}`。`test` が true のときだけ `"test": "true"`（文字列。Alertmanager の labels と同じく値は文字列）。
  - 出来事の `detail.round.at`: 人の報告の口と閉じる口では、サーバーが受け付けた時刻（UTC の ISO 8601）を入れる。出来事の口の `round.at` は呼ぶ側が送る（必須）。
  - 閉じる口の入力は `n`（1〜99）と `session_id`（1〜64字）。答えは `{"incident_id", "closed"}`。既に閉じた行なら何も書かず `closed=false`（呼び直しで出来事が2つにならない）。Discord 発でない行は 409 `OPS_INCIDENT_NOT_DISCORD`。無い行は 404 `OPS_INCIDENT_NOT_FOUND`。
  - 出来事の口の `round`: `step` は start/launch_failed/kept/closed/measure/result/stop/notify_failed/suspicious、`n`（1〜99）と `at` は必須。`session_id`・`reservation_id`（1〜64字）・`reason`（14種）は省略できる。`result` は `step=result` のときだけ必須で `fail` だけ（`pass` は閉じる口だけが書く。合格を書く道を1つにするため）。`round` があるときは `kind` は `ai` だけ、`note` は 500 字まで。
  - 大きさ: `detail` を作ったあと、DB に触る前に `_dumps(detail)` の UTF-8 のバイト数を測り、8000 を超えたら 422 `OPS_DETAIL_TOO_LARGE`。列の書き換えも出来事の追加もしない。
  - 欄の絞り: 行の `labels.source` が `discord` で、`fields` に `ai_started_at`・`detection_path`・`first_aid_started_at`・`first_aid_done_at`・`first_aid_result` のどれかがあれば（null を送った場合も）422 `OPS_FIELD_LOCKED_FOR_DISCORD`。列の書き換えも出来事の追加もしない。`review_note`・`human_noticed_at`・`root_cause`・`fix_pr`・`needs_action` は書ける。Discord 発でない行は今までどおり全部書ける。
  - 3つとも `halt_all` を見ない（全停止の間も記録を続ける。`docs/handoff/ai-ops-247/stage2-design.md`:177）。

## 3. 触るファイル（これ以外は触らない）

| ファイル | 変えること |
|---|---|
| `backend/app/routers/ops.py` | §4-1〜§4-4 |
| `backend/app/realtime/topics.py` | §4-5（:119 の次に2行） |
| `backend/tests/test_ops_router.py` | §4-6（末尾に足すだけ。既存の試験と fixture は変えない） |
| `frontend/api-contract/openapi.json` | §4-7 の命令で作り直したものをそのままコミット（手で書かない） |
| `docs/handoff/discord-pdca-bin15/design.md` | §13 の報告欄だけ |

## 4. 作り方

### 4-1 import と定数（`backend/app/routers/ops.py`）

- :20 を次に変える。
  - 変更前: `from pydantic import BaseModel, ConfigDict, Field, ValidationError`
  - 変更後: `from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError, model_validator`
- :40 `_JSON_LIMIT_BYTES = 4000` の次に足す:

```python
_DETAIL_LIMIT_BYTES = 8000  # 表の制約は 8192（octet_length(detail::text)）。余白を残して入口で止める
_ROUND_NOTE_MAX = 500
```

- :54 `)`（`_ANNOTATABLE_COLUMNS` の終わり）の次に足す:

```python

# Discord 発の行（labels.source='discord'）に注記で書かせない列（ADR-1039・設計 §4-9 K15）
_DISCORD_LOCKED_COLUMNS = frozenset(
    {
        "ai_started_at",
        "detection_path",
        "first_aid_started_at",
        "first_aid_done_at",
        "first_aid_result",
    }
)
```

- `_dumps`（:188-189）の次に足す:

```python


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
```

### 4-2 出来事の口に `round` を足す（`OpsIncidentAnnotation`・`annotate_incident`）

- `OpsIncidentFields`（:334-346）は変えない。その次、`OpsIncidentAnnotation`（:349-354）の前に足す:

```python
class OpsRound(BaseModel):
    """Discord 発の件の回の記録（設計 §4-9）。accept と result の pass は別の口が書く。"""

    model_config = ConfigDict(extra="forbid")

    step: Literal[
        "start",
        "launch_failed",
        "kept",
        "closed",
        "measure",
        "result",
        "stop",
        "notify_failed",
        "suspicious",
    ]
    n: int = Field(ge=1, le=99)
    at: AwareDatetime
    session_id: str | None = Field(None, min_length=1, max_length=64)
    reservation_id: str | None = Field(None, min_length=1, max_length=64)
    result: Literal["fail"] | None = None
    reason: Literal[
        "failed-3",
        "unknown",
        "halt",
        "interrupted",
        "lost",
        "full",
        "not_ready",
        "failed",
        "cwd_invalid",
        "needs_decision",
        "blocked",
        "waiting_60m",
        "no-reply",
        "leftover",
    ] | None = None

    @model_validator(mode="after")
    def _result_only_on_result_step(self) -> "OpsRound":
        if (self.step == "result") != (self.result is not None):
            raise ValueError("result is required when step is result, and not allowed otherwise")
        return self
```

- `OpsIncidentAnnotation`（:349-354）を次に変える。
  - 変更前:

```python
class OpsIncidentAnnotation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["annotated", "first_aid", "ai"]
    note: str | None = Field(None, max_length=2000)
    fields: OpsIncidentFields = OpsIncidentFields()
```

  - 変更後:

```python
class OpsIncidentAnnotation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["annotated", "first_aid", "ai"]
    note: str | None = Field(None, max_length=2000)
    fields: OpsIncidentFields = OpsIncidentFields()
    round: OpsRound | None = None

    @model_validator(mode="after")
    def _round_rules(self) -> "OpsIncidentAnnotation":
        if self.round is not None:
            if self.kind != "ai":
                raise ValueError("round requires kind ai")
            if self.note is not None and len(self.note) > _ROUND_NOTE_MAX:
                raise ValueError(f"note must be at most {_ROUND_NOTE_MAX} characters when round is set")
        return self
```

- `annotate_incident`（:357-403）の本体を次に変える（関数の名前・引数・デコレータ・答えの形は変えない）。
  - 変更前: recon §2 の :364-403（`values = ...` から `return {...}` まで）
  - 変更後:

```python
    values = body.fields.model_dump(exclude_unset=True)
    columns = [c for c in _ANNOTATABLE_COLUMNS if c in values]
    detail: dict[str, Any] = {"fields": sorted(columns), "note": body.note, "user_id": who["user_id"]}
    if body.round is not None:
        detail["round"] = body.round.model_dump(mode="json", exclude_none=True)
    detail_json = _dumps(detail)
    if len(detail_json.encode("utf-8")) > _DETAIL_LIMIT_BYTES:
        raise HTTPException(status_code=422, detail="OPS_DETAIL_TOO_LARGE")
    await set_operator_context(db)
    try:
        inc = (
            await db.execute(
                text(
                    "SELECT id, labels->>'source' AS source "
                    "FROM public.ops_incidents WHERE id = :id"
                ),
                {"id": incident_id},
            )
        ).mappings().first()
        if inc is None:
            await db.rollback()
            raise HTTPException(status_code=404, detail="OPS_INCIDENT_NOT_FOUND")
        if inc["source"] == "discord" and _DISCORD_LOCKED_COLUMNS.intersection(columns):
            await db.rollback()
            raise HTTPException(status_code=422, detail="OPS_FIELD_LOCKED_FOR_DISCORD")
        if columns:
            assignments = ", ".join(f"{c} = :{c}" for c in columns)
            await db.execute(
                text(
                    f"UPDATE public.ops_incidents SET {assignments}, updated_at = now() "
                    "WHERE id = :id"
                ),
                {**{c: values[c] for c in columns}, "id": incident_id},
            )
        await db.execute(
            _INSERT_EVENT_SQL,
            {
                "incident_id": incident_id,
                "kind": body.kind,
                "actor": who["actor"],
                "detail": detail_json,
            },
        )
        await db.commit()
    finally:
        await _clear_operator(db)
    return {"incident_id": str(incident_id), "updated_fields": sorted(columns)}
```

- 注意: `round` が無いときの `detail` は今までと同じ3つの鍵だけ（`round` の鍵を null で入れない）。

### 4-3 人の報告の口（`annotate_incident` の次、`# B5 全停止スイッチ` の区切り（:406）の前に足す）

```python
# ---------------------------------------------------------------------------
# Discord 発の件（ADR-1039 Decision 10・設計 §4-9）
# ---------------------------------------------------------------------------


class OpsHumanReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message_id: str = Field(pattern=r"^[0-9]{1,20}$")
    posted_at: AwareDatetime
    message_url: str = Field(
        max_length=200,
        pattern=r"^https://discord\.com/channels/[0-9]{1,20}/[0-9]{1,20}/[0-9]{1,20}$",
    )
    test: bool = False

    @model_validator(mode="after")
    def _url_ends_with_message_id(self) -> "OpsHumanReport":
        if self.message_url.rsplit("/", 1)[-1] != self.message_id:
            raise ValueError("message_url must end with message_id")
        return self


_INSERT_HUMAN_INCIDENT_SQL = text(
    """
    INSERT INTO public.ops_incidents
        (fingerprint, starts_at, alertname, labels, status, detection_path,
         first_notified_at, last_notified_at, human_noticed_at)
    VALUES
        (:fingerprint, :posted_at, 'discord-bug-report', CAST(:labels AS jsonb), 'firing', 'human',
         :posted_at, :posted_at, :posted_at)
    ON CONFLICT (fingerprint, starts_at) DO NOTHING
    RETURNING id
    """
)


@router.post("/ops/incidents/human")
async def report_human_incident(
    body: OpsHumanReport,
    who: dict[str, Any] = Depends(require_ops_reader),
    db: AsyncSession = Depends(get_db),
):
    fingerprint = f"discord:{body.message_id}"
    labels: dict[str, str] = {"source": "discord", "message_url": body.message_url}
    if body.test:
        labels["test"] = "true"
    await set_operator_context(db)
    try:
        row = (
            await db.execute(
                _INSERT_HUMAN_INCIDENT_SQL,
                {"fingerprint": fingerprint, "posted_at": body.posted_at, "labels": _dumps(labels)},
            )
        ).first()
        inserted = row is not None
        if inserted:
            incident_id = row[0]
            await db.execute(
                _INSERT_EVENT_SQL,
                {
                    "incident_id": incident_id,
                    "kind": "notified",
                    "actor": who["actor"],
                    "detail": _dumps(
                        {"round": {"step": "accept", "n": 1, "at": _now_iso()}, "user_id": who["user_id"]}
                    ),
                },
            )
        else:
            incident_id = (
                await db.execute(
                    text(
                        "SELECT id FROM public.ops_incidents "
                        "WHERE fingerprint = :fingerprint AND starts_at = :posted_at"
                    ),
                    {"fingerprint": fingerprint, "posted_at": body.posted_at},
                )
            ).scalar_one()
        await db.commit()
    finally:
        await _clear_operator(db)
    return {"incident_id": str(incident_id), "inserted": inserted}
```

### 4-4 閉じる口（4-3 の次に足す）

```python
class OpsIncidentClose(BaseModel):
    model_config = ConfigDict(extra="forbid")

    n: int = Field(ge=1, le=99)
    session_id: str = Field(min_length=1, max_length=64)


@router.post("/ops/incidents/{incident_id}/close")
async def close_incident(
    incident_id: UUID,
    body: OpsIncidentClose,
    who: dict[str, Any] = Depends(require_ops_reader),
    db: AsyncSession = Depends(get_db),
):
    await set_operator_context(db)
    try:
        inc = (
            await db.execute(
                text(
                    "SELECT status, labels->>'source' AS source "
                    "FROM public.ops_incidents WHERE id = :id FOR UPDATE"
                ),
                {"id": incident_id},
            )
        ).mappings().first()
        if inc is None:
            await db.rollback()
            raise HTTPException(status_code=404, detail="OPS_INCIDENT_NOT_FOUND")
        if inc["source"] != "discord":
            await db.rollback()
            raise HTTPException(status_code=409, detail="OPS_INCIDENT_NOT_DISCORD")
        closed = inc["status"] != "resolved"
        if closed:
            await db.execute(
                text(
                    "UPDATE public.ops_incidents "
                    "SET status = 'resolved', resolved_at = now(), updated_at = now() "
                    "WHERE id = :id"
                ),
                {"id": incident_id},
            )
            await db.execute(
                _INSERT_EVENT_SQL,
                {
                    "incident_id": incident_id,
                    "kind": "resolved",
                    "actor": who["actor"],
                    "detail": _dumps(
                        {
                            "round": {
                                "step": "result",
                                "result": "pass",
                                "n": body.n,
                                "session_id": body.session_id,
                                "at": _now_iso(),
                            },
                            "user_id": who["user_id"],
                        }
                    ),
                },
            )
            await db.commit()
        else:
            await db.rollback()
    finally:
        await _clear_operator(db)
    return {"incident_id": str(incident_id), "closed": closed}
```

### 4-5 通知の台帳（`backend/app/realtime/topics.py`）

- :119（`("POST", "/api/v1/ops/incidents/{incident_id}/events"): ...`）の次に、同じ字下げで2行足す:

```python
    ("POST", "/api/v1/ops/incidents/human"): "保守 API ADR-1012: 運用者向けで画面更新の通知対象外",
    ("POST", "/api/v1/ops/incidents/{incident_id}/close"): "保守 API ADR-1012: 運用者向けで画面更新の通知対象外",
```

### 4-6 試験（`backend/tests/test_ops_router.py` の末尾に足す）

- 共通の助けを末尾に足す（既存の `_alert`・`_payload`・`env` は変えない）。Discord の行の指紋は `env.fingerprints` に入れて後片付けに乗せる。試験の id は乱数で、本物の Discord の id を書かない:

```python
def _discord_report(env: _Env, *, test: bool | None = None, posted_at=None):
    message_id = str(uuid.uuid4().int)[:18]
    env.fingerprints.append(f"discord:{message_id}")
    posted_at = posted_at or datetime(2026, 10, 23, 1, 0, 0, tzinfo=timezone.utc)
    body = {
        "message_id": message_id,
        "posted_at": posted_at.isoformat(),
        "message_url": f"https://discord.com/channels/1/2/{message_id}",
    }
    if test is not None:
        body["test"] = test
    return body


async def _new_discord_incident(env: _Env, **kw):
    body = _discord_report(env, **kw)
    resp = await env.client.post(f"{_BASE}/incidents/human", json=body, headers=env.api_headers())
    assert resp.status_code == 200
    return body, resp.json()["incident_id"]


def _round(**kw):
    return {"step": "start", "n": 1, "at": "2026-10-23T01:05:00+00:00", **kw}
```

- 足す試験（名前と順をこのとおりにする）:

| # | 名前 | 確かめること |
|---|---|---|
| T1 | `test_human_creates_discord_incident_and_accept_event` | 200・`inserted` が true。行は1つで、`alertname='discord-bug-report'`・`detection_path='human'`・`status='firing'`・`labels` が `{"source": "discord", "message_url": <送った値>}` ちょうど（`test` の鍵なし）・`starts_at`・`first_notified_at`・`last_notified_at`・`human_noticed_at` がすべて送った時刻・`ai_started_at` が None・`notify_count` が 1。出来事は1つで `kind='notified'`・`actor='ops_token'`・`detail["round"]` の `step='accept'`・`n=1`・`at` がある |
| T2 | `test_human_same_message_returns_existing_row` | 同じ本文を2回送る。2回目も 200 で `inserted` が false、`incident_id` が1回目と同じ。行は1つ・出来事は1つ・`notify_count` は 1 のまま |
| T3 | `test_human_test_flag_sets_label` | `test=True` で `labels["test"] == "true"`。`test=False` では `labels` に `test` の鍵が無い |
| T4 | `test_human_rejects_bad_input_and_ingest_token` | 422 になる5つ: `message_id` に数字以外／`message_url` の最後が `message_id` と違う／`message_url` が別のドメイン／`posted_at` に時差なし（`2026-10-23T01:00:00`）／知らない鍵（`body` など）。取り込み用の鍵は 401。どの場合も行が増えない |
| T5 | `test_close_resolves_discord_incident` | T1 の形で行を作り、`{"n": 2, "session_id": "s-1"}` で閉じる。200・`closed` が true。行は `status='resolved'`・`resolved_at` が None でない。出来事が1つ増え、`kind='resolved'`・`detail["round"]` が `step='result'`・`result='pass'`・`n=2`・`session_id='s-1'`・`at` がある |
| T6 | `test_close_twice_adds_no_second_event` | 閉じたあとにもう一度閉じる。200・`closed` が false。出来事の数は増えない・`resolved_at` は1回目の値のまま |
| T7 | `test_close_rejects_alertmanager_incident` | Alertmanager の口で作った行を閉じると 409・`detail == "OPS_INCIDENT_NOT_DISCORD"`。行は `firing` のまま・出来事は増えない |
| T8 | `test_close_unknown_incident_returns_404` | 乱数の UUID で 404 |
| T9 | `test_annotate_round_written_into_detail` | Discord の行に `{"kind": "ai", "note": "start", "round": _round(session_id="s-1", reservation_id="r-1")}`。200。足された出来事の `detail` が `fields`・`note`・`user_id`・`round` の4つの鍵で、`round` は送った値（`at` は ISO の文字列）。`step="result", result="fail", reason="failed"` も 200 |
| T10 | `test_annotate_round_rejects_bad_values` | 422 になる9つ: `step` が `accept`／`n=0`／`n=100`／`round` に知らない鍵／`step="result"` で `result="pass"`／`step="result"` で `result` なし／`step="start"` に `result="fail"`／`kind="annotated"` に `round`／`round` ありで `note` が 501 字。`session_id` が 65 字も 422。どの場合も出来事が増えない |
| T11 | `test_annotate_without_round_keeps_detail_shape` | Alertmanager の行に `round` なしで書く。200。出来事の `detail` の鍵がちょうど `fields`・`note`・`user_id` の3つ |
| T12 | `test_annotate_detail_size_limit` | `note` に `"😀" * 1950`（`round` なし）は 200。`"😀" * 2000` に `fields={"root_cause": "x"}` を付けると 422・`detail == "OPS_DETAIL_TOO_LARGE"`、`root_cause` は書かれず出来事も増えない |
| T13 | `test_annotate_discord_row_rejects_locked_fields` | Discord の行に、5つの欄（`ai_started_at`・`detection_path`・`first_aid_started_at`・`first_aid_done_at`・`first_aid_result`）を1つずつ送るとどれも 422・`detail == "OPS_FIELD_LOCKED_FOR_DISCORD"`。`{"ai_started_at": None}` も 422。行の `ai_started_at` は None・`detection_path` は `human` のまま・出来事は増えない。続けて `{"review_note": "r", "human_noticed_at": <時刻>}` は 200 で両方書ける |
| T14 | `test_annotate_alert_row_still_accepts_locked_fields` | Alertmanager の行には `ai_started_at` と `detection_path="ai"` を書ける（200・値が入る） |
| T15 | `test_discord_endpoints_record_while_halted` | `ops_control_lock` の中で halt を ON にし（`test_ingest_continues_while_halted` と同じ形、:396-412）、人の報告・`round` 付きの出来事・閉じるが3つとも 200。`finally` で `_clear_control` |

- 試験の値の読み方: `detail` と `labels` は admin の接続で読む（`_incidents`・`_events`）。jsonb は dict で返る【未確認: asyncpg の jsonb の戻りの型。dict でなく文字列なら `json.loads` してから比べる。どちらだったかを報告に書く】。

### 4-7 openapi を作り直す

```bash
cd /Users/tanizawashingo/worktrees/salesanchor/release-discord-pdca-bin15/backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json
cd /Users/tanizawashingo/worktrees/salesanchor/release-discord-pdca-bin15/frontend && npm run generate:api-types
```

- `frontend/api-contract/openapi.json` の差分だけをコミットする。frontend/src/api/generated/ は追跡外（`.gitignore`:128）なので差分に出ない。
- 差分に、今回の3つの口と `OpsRound`・`OpsHumanReport`・`OpsIncidentClose` 以外の変化（ほかの口の消滅・並び替え）が出たら §6 の分岐。

## 5. 確かめ方（担当が実行し、出力をファイルに保存して報告に書く）

生出力の置き場: /tmp/CC報告ファイル/discord-pdca-bin15/impl/

- 5-1 `cd backend && ruff check app/routers/ops.py app/realtime/topics.py tests/test_ops_router.py` → 0 件。
- 5-2 `grep -n "^async def test_" backend/tests/test_ops_router.py` → 既存の12本（:165〜:415）のあとに T1〜T15 の名前が §4-6 の順で15本。合わせて27本。名前の一覧を保存する。
- 5-3 `cd backend && pytest tests/test_ops_router.py tests/test_realtime_topics.py -q` → 手元では `backend/tests/test_ops_router.py` が skip になる（RLS_* が無い。recon §2 :22-31）。`backend/tests/test_realtime_topics.py` は全部 passed。skip は失敗ではない。実 PostgreSQL での合否は CI の「pytest (SQLite + PostgreSQL RLS)」（`.github/workflows/test.yml`:252）で見る。
- 5-4 `git diff --stat origin/main...HEAD` → §3 の5ファイルだけ。`git diff origin/main...HEAD -- backend/app/routers/ops.py | grep "^-" | grep -v "^---"` で消えた行を保存し、§4-1〜§4-2 の変更前の行（:20 の import・`OpsIncidentAnnotation` の終わりの行はそのまま残る・`annotate_incident` の :364-403）以外が無いことを確かめる。`ingest_alertmanager`・`_UPSERT_INCIDENT_SQL` の行が1行も消えていない。
- 5-5 §4-7 の2つの命令のあとに `git status --short frontend/` → `frontend/api-contract/openapi.json` だけ。
- 5-6 PR を作ったあと、CI の「pytest (SQLite + PostgreSQL RLS)」「API contract is up to date」の結果を `gh pr checks <番号>` で1回だけ取って保存する（待たない。終わっていなければ「実行中」と書く）。

## 6. 分岐ごとの対処

- §4 の目印の行が recon の行番号とずれている（ほかの PR が先に変えた）→ `git show origin/main:backend/app/routers/ops.py | grep -n "class OpsIncidentAnnotation"` のように origin/main で探し直し、同じ意味の位置で行う。意味が変わっていたら（関数の中身が recon と違う）NEEDS_DECISION: で、grep の出力を貼る。
- `AwareDatetime` か `model_validator` が import できない → `pip show pydantic` の出力を貼って BLOCKED:（`backend/requirements.txt`:8 は `pydantic[email]==2.10.6`。2系にはどちらもある）。
- openapi の差分に今回と関係ない変化が出る → 作り直しを1回やり直し、同じなら差分の要約（変わった口の名前）を貼って NEEDS_DECISION:。手で openapi.json を直さない。
- `backend/tests/test_realtime_topics.py` が落ちる → 落ちた口の名前を確かめ、§4-5 の2行の綴りを直す。それでも落ちたら BLOCKED:。
- CI の pytest で T12 の 1950 字が 422 か、DB の制約違反（500）になる → 8000 と DB の測り方の差が想定と違う。数字を変えずに失敗の原文を貼って BLOCKED:（Opus が測り方を見直す）。
- CI の pytest で RLS に拒まれる（`42501`）→ 原文を貼って BLOCKED:（権限の設計を Opus が見る。推測で直さない）。
- 既存の12本のどれかが落ちる → 自分の変更で落ちたかを `git stash` せずに、落ちた試験の原文と §4-2 の差分を貼って BLOCKED:。既存の試験を書き換えない。
- process-artifacts gate が「GO記録」が無いと落ちる → 想定どおり（`backend/app/routers` の変更は GO 記録が要る）。担当は直さない。報告に「GO 記録待ちで落ちている」と書く。

## 7. 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 人の報告の口が、設計 §4-9 の列の値で1行と出来事 `accept` を作る | CI pytest `test_human_creates_discord_incident_and_accept_event` |
| 同じ投稿 id で行が増えず `inserted=false` | CI pytest `test_human_same_message_returns_existing_row` |
| 閉じる口が Discord 発の行を閉じ、出来事 `result`（pass）を1つだけ足す | CI pytest `test_close_resolves_discord_incident`・`test_close_twice_adds_no_second_event` |
| Alertmanager の行を閉じられない | CI pytest `test_close_rejects_alertmanager_incident` |
| `round` の型の誤りが 422 | CI pytest `test_annotate_round_rejects_bad_values` |
| `round` が `detail.round` に入り、`round` なしの `detail` は今までの形のまま | CI pytest `test_annotate_round_written_into_detail`・`test_annotate_without_round_keeps_detail_shape` |
| 8000 バイトを超える `detail` が 422 | CI pytest `test_annotate_detail_size_limit` |
| Discord 発の行への `ai_started_at` などが 422、`review_note` は書ける | CI pytest `test_annotate_discord_row_rejects_locked_fields` |
| Alertmanager の行の書ける欄は変わらない | CI pytest `test_annotate_alert_row_still_accepts_locked_fields` と既存の `test_annotate_updates_allowed_fields_only` |
| 全停止の間も3つの口が記録する | CI pytest `test_discord_endpoints_record_while_halted` |
| 既存の12本が書き換えずに合格 | CI pytest（`backend/tests/test_ops_router.py` の既存の試験）と §5-4 の差分 |
| 新しい口が通知の台帳に載る | CI pytest `backend/tests/test_realtime_topics.py` |
| API の形が openapi.json にコミットされている | CI「API contract is up to date」（`.github/workflows/api-contract-check.yml`） |
| 本番で口が動く（反映のあと。Opus が行う） | §8 の手順の出力 |

## 8. 反映の前後（Opus が行う。担当はしない）

- マージの前に、PO に「本番に入れてよいか」を聞く（PO の「1」の約束）。GO 記録は PO の答えを受けてから PR 本文に転記する。
- 反映のあと: `GET /api/v1/ops/incidents?limit=1` が 200 のまま（既存の口が壊れていない）を保守の鍵で確かめる。新しい口の本番での試し（`test=true` の行を作る）は、時刻を PO に確かめてから行う（設計 第0段 0-9）。作った行は消せない表なので、`labels.test='true'` で分ける。

## 9. 戻し方と未解決事項

- 戻し方: 3つの変更（口2つと `round`・大きさの検査・欄の絞り）と台帳の2行を外す PR を出す。表の形は変えていないので、作られた行はそのまま残る（消さない決まりの表）。設計 §11 便1.5 と同じ。
- 未解決: §4-6 の jsonb の戻りの型（試験の書き方だけに関わる。分岐で吸う）。

## 外部・過去事例の参照と我々への応用

- 該当なし：保守 API の既存の口（`backend/app/routers/ops.py` の Alertmanager の受け口と注記の口）と同じ形を足すだけで、新しい技術の選択が無いため、外部事例の参照は不要と判断した。同じ表に別の出どころの行を入れる過去の例は ADR-1025（誤り報告）が agent-console の受け口で本番に入っており、出どころを分ける形（`labels.source`）は ADR-1039 Decision 10 で決まっている。

## 維持の仕組み

- 守り手: `.github/workflows/test.yml`
- 「pytest (SQLite + PostgreSQL RLS)」が毎回 `backend/tests/test_ops_router.py` を実 PostgreSQL で走らせ、§7 の T1〜T15 で欄の絞り・大きさ・冪等を守る。API の形は `.github/workflows/api-contract-check.yml` が、口の台帳への登録は `backend/tests/test_realtime_topics.py` が守る。

## 10. PR

- 作業場所: `cd /Users/tanizawashingo/salesanchor && bash scripts/new-worktree.sh release/discord-pdca-bin15 --claude`（origin/main 起点）。最後に「Input must be provided」が出て終了コードが 1 になることがあるが、作業場所の作成とは無関係（2026-10-23 実測）。作成後に `ls -1d /Users/tanizawashingo/worktrees/salesanchor/release-discord-pdca-bin15` と `git worktree list` で実在を確かめる。以後の作業はすべてその作業場所に `cd` してから行う（絶対パス）。
- このカードは origin/main に入ったものを読む（作業場所に `docs/handoff/discord-pdca-bin15/design.md` がある）。
- commit は `--no-verify` を使わない。commit の後に `git log -1 --oneline`、push の後に `git log origin/release/discord-pdca-bin15 -1 --oneline` で実在を確かめる。
- 作成前に `gh auth status` で `shingo-cc` 名義を確かめる。
- PR は `scripts/gh-pr-create-safe.sh` に、先に Write ツールで作った本文ファイルを絶対パスで渡して作る。ready で作る（`--draft` を付けない）。base は main。担当はマージしない。
- 本文は PR テンプレートに沿い、`### 標準ワークフロー確認` に次を書く: recon: docs/handoff/discord-pdca-bin15/recon.md ／ 設計: docs/handoff/discord-pdca-bin15/design.md ／ 対象ADR: ADR-1039, ADR-1012 ／ 触るファイル: backend/app/routers/ops.py, backend/app/realtime/topics.py, backend/tests/test_ops_router.py, frontend/api-contract/openapi.json, docs/handoff/discord-pdca-bin15/design.md ／ 削除するファイル: なし
- `### GO記録` は担当が書かない。本文に「GO 待ち（本番に入る backend の変更。Opus が PO に確かめてから転記する）」と1行書く。
- 本文に鍵の値・鍵のパス・本物の Discord の id を書かない。
- 作成前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し exit 0 を確かめる（時間がかかるので timeout を長めにする）。

## 11. 報告

- 1行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか。
- 完了報告に: 受領文／§5-1〜5-6 の結果（生出力のパス）／PR の URL／§4-6 の jsonb の型がどちらだったか／判断を要した点（事実のみ）。
- 停止したときは: 停止した手順番号／最後に実行したコマンド／停止した理由の原文。
- §13 の報告欄に同じ内容を短く追記してコミットする。

## 12. 委任の定型

- sleep しない（CI の待ちは Opus が行う）。
- ファイルの作成と編集は Write/Edit ツールで行う（ヒアドキュメントで書かない）。
- PR を作る前に `scripts/dev/validate-pr-body.sh` で exit 0 を確かめる。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。

## 13. 報告欄（担当が追記）

- （未記入）

END OF CARD
