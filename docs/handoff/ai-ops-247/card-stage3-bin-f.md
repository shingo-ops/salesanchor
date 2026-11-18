# 実装カード 段階3 便F — 保守 API に「auto で未処置の一覧」と「直近の処置の出来事」の口を足す

> この文書は何か：AI保守運用24時間化 段階3 便F の作業指示書です。障害記録を読む窓口（保守 API）に、絞り込みを 2 つ足します。①札が auto で、まだ誰も処置していない障害だけを一覧にする。②直近の処置の出来事を、種類と時刻で読む。どちらも読むだけで、書き込み・表・列は増やしません。便G（その場で直す係）がこの 2 つを使います。

- 設計: docs/handoff/ai-ops-247/stage3-design.md §2 便F（:89-97）・§6（:123）
- 親設計: docs/handoff/ai-ops-247/design.md §5 段階3
- ロードマップ: docs/handoff/ai-ops-247/stage4-requirements.md「引き直した順番」2 行目（便F の実装カード → 実装 → 本番）
- 対象ADR: ADR-1012（本テーマ）、ADR-135（main マージ＝本番投入可）、ADR-1018・ADR-131（運用者の旗）
- 状態: 設計案作成済み・Opus 自己審査 APPROVE（§14。同一 AI の自己審査で、独立した第二者の審査ではない）。PO の実装承認は未（2026-11-19 時点）
- 危険便: いいえ（触るのは `backend/app/routers/ops.py` と試験だけ。`migrations/`・`deploy.yml`・本番 `scripts/` を含まない）。ただし main マージで本番に出る（ADR-135）。本番の変更は 1 つ出したら 24 時間見てから次（stage4-requirements.md C6）
- 担当: 実装 Sonnet（クラウド）／審査・マージ・反映確認 Opus

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は ready で作る（Draft にしない）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（読む口の絞り込みだけ） |
| 5 | 既存ブランチへの追記ではない（新規ブランチ） | ○ |
| 6 | 書式は実例で示した | ○（§4 に変更前後のコード） |
| 7 | 合格基準を出力まで縛った | ○（§5） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-1 は試験名を出す `-v`） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実物から | ○（行番号は origin/main 15cf536f0 で確かめた） |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§12） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・報告に無い出力を成功と扱わない・プレースホルダを残さない | ○（§5・§10・§12） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○（§12） |
| guards/04-worktree.md | new-worktree.sh の出力をパイプに通さず、実在は `ls -1d` と `git worktree list` で確かめる。追加の push は `git push -u origin HEAD` | ○（§10） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh` で作る。触るファイル・削除するファイルは同一行カンマ区切り。PR 番号は `.pr-number` と `gh pr list --head` で取る | ○（§10） |
| guards/08-vps.md | 本番（prod1・prod2）には触らない | ○（§8 は Opus） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード 段階3 便F の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. 一覧の口 `GET /api/v1/ops/incidents` に、引数 `tier` と `first_aid` を足す（§4-1）
2. 新しい読む口 `GET /api/v1/ops/events` を足す（§4-2）
3. 試験 4 つを `backend/tests/test_ops_router.py` の末尾に足す（§4-3）

入れない:
- 書き込みの口・表・列・migration（設計 §2 便F「新しい表・列・migration は作らない」）
- 応急処置係そのもの（便G）
- 見張りの札 `ContainerUnhealthy` の page → auto への切り替え（便G）
- nginx・deploy・画面の変更

## 2. 前提の事実と設計の細部

### 2-1. 事実（origin/main 15cf536f0・2026-11-19 取得）

| # | 事実 | 出典 |
|---|---|---|
| F1 | 一覧の口の引数は `status`・`since`・`limit`（1〜100・既定 50）だけ。並びは `first_notified_at` の新しい順 | `backend/app/routers/ops.py:292-315` |
| F2 | 読む口の鍵は `require_ops_reader`。保守の鍵（OPS_API_TOKEN）か super admin のログインで通る。受け口の鍵（OPS_INGEST_TOKEN）は 401。鍵が空の間は 401 | `backend/app/routers/ops.py:115-130` |
| F3 | 読み書きは「運用者の旗を立てる → 処理 → 旗を戻す」の形（`set_operator_context` → `_clear_operator`） | `backend/app/routers/ops.py:6,302-314` |
| F4 | 見張りの札は labels の `tier` に入り、障害記録の `labels`（jsonb）にそのまま入る。labels が 4000 バイトを超えたときだけ alertname と severity に縮め、tier は落ちる | `backend/app/routers/ops.py:209-217`（`_shrink_labels`） |
| F5 | 今の見張りの札は page 10 本・ticket 28 本・auto 0 本 | `monitoring/prometheus/alert_rules.yml` の `tier:` の数（`grep` の集計） |
| F6 | 札の値の正本は見張りの検査（page・auto・ticket のどれか） | `monitoring/scripts/check_alert_rules.py`（便E カード §2-1 F5） |
| F7 | 注記の口（B4）が出来事に書く detail の形は `{"fields": [...], "note": ..., "user_id": ..., ("round": ...)}` に固定。呼ぶ側が `service` などの任意の鍵を detail に入れる道は無い | `backend/app/routers/ops.py:430,438`（`annotate_incident` の `detail`） |
| F8 | 出来事の表 `ops_incident_events` の列は id・incident_id・occurred_at・kind・actor・detail。索引は (incident_id, occurred_at) だけ | `migrations/20261016_100000_create_ops_incident_tables.sql:48-63` |
| F9 | 出来事の kind の値の正本は表の制約 `ops_incident_events_kind_check`（今は notified・resolved・annotated・first_aid・ai・halt・case_report） | `migrations/20261113_200000_add_ops_case_report_kind.sql:89-96` |
| F10 | `/ops/events` という道はアプリにまだ無い。nginx で個別に扱っている ops の道は alertmanager・read-window・case・unmask だけで、ほかは `/api/` の扱い | `git grep "/ops/events" origin/main -- backend/app`（0 件）・`nginx/nginx.conf:622,642,725,745,765,785` |
| F11 | 試験は実 PostgreSQL を使う。共有の DB なので、試験は自分の fingerprint の行だけを見て判定している | `backend/tests/test_ops_router.py:37-62,292-316` |

### 2-2. 決めたこと（Opus）

| # | 決めたこと | 理由 |
|---|---|---|
| D1 | `tier` は文字の形（`^[a-z]{1,16}$`）だけを確かめ、値の一覧をコードに書かない。知らない値は 0 件が返る | 札の値の正本は見張りの検査（F6）。ここに一覧を書くと正本が 2 つになる |
| D2 | `first_aid=pending` は「`status = 'firing'` かつ `first_aid_started_at IS NULL`」。値は `pending` だけを受ける | 設計 §2 便F B7 のとおり。鳴り止んだ障害は処置しない |
| D3 | 新しい口 `GET /ops/events` の引数は `kind`・`service`・`since`・`limit`（1〜100・既定 50）。並びは `occurred_at` の新しい順。返す行に、障害の `alertname` と `labels->>'service'` を `alertname`・`service` として付ける | 設計 B8 は「detail の service で数える」としていたが、注記の口は detail に service を入れられない（F7）。service は障害の labels に既にある（ContainerUnhealthy は labels に service を持つ）。障害の表から読めば、書き込みの口を変えずに済み、正本も 1 つのまま。設計の目的（同じ service の直近の処置を数える）は変えない |
| D4 | `kind` も文字の形（`^[a-z_]{1,32}$`）だけを確かめる。`service` は `^[a-z0-9_-]{1,64}$` | kind の値の正本は表の制約（F9）。D1 と同じ理由 |
| D5 | 索引は足さない | migration を作らない便（設計 §2 便F）。出来事の行数が増えて遅くなったら、別の便で索引を足す。便G は 1 分に 1 回、直近 1 時間だけを読む |
| D6 | 返す形は既存の口と同じ `{"items": [...]}` | 呼ぶ側（便G）が同じ読み方で済む |

## 3. 触るファイル（これ以外は触らない）

- 変更: `backend/app/routers/ops.py`（§4-1 の置き換えと、§4-2 の追記）
- 変更: `backend/tests/test_ops_router.py`（末尾に追記のみ・§4-3）
- 変更: `docs/handoff/ai-ops-247/card-stage3-bin-f.md`（このカード。§13 報告欄の追記のみ）

## 4. 作り方

### 4-1. `backend/app/routers/ops.py` の一覧の口（:292-315）を置き換える

変更前（origin/main 15cf536f0 の :292-315）:

```python
@router.get("/ops/incidents", dependencies=[Depends(require_ops_reader)])
async def list_incidents(
    status: Literal["firing", "resolved"] | None = None,
    since: datetime | None = None,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    if since is not None and since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)
    await set_operator_context(db)
    try:
        result = await db.execute(
            text(
                "SELECT * FROM public.ops_incidents "
                "WHERE (CAST(:status AS text) IS NULL OR status = CAST(:status AS text)) "
                "AND (CAST(:since AS timestamptz) IS NULL OR first_notified_at >= CAST(:since AS timestamptz)) "
                "ORDER BY first_notified_at DESC LIMIT :limit"
            ),
            {"status": status, "since": since, "limit": limit},
        )
        items = [dict(r) for r in result.mappings().all()]
    finally:
        await _clear_operator(db)
    return {"items": items}
```

変更後:

```python
@router.get("/ops/incidents", dependencies=[Depends(require_ops_reader)])
async def list_incidents(
    status: Literal["firing", "resolved"] | None = None,
    since: datetime | None = None,
    limit: int = Query(50, ge=1, le=100),
    tier: str | None = Query(None, pattern=r"^[a-z]{1,16}$"),
    first_aid: Literal["pending"] | None = None,
    db: AsyncSession = Depends(get_db),
):
    # tier の値の正本は monitoring/scripts/check_alert_rules.py。ここでは形だけを確かめる（便F D1）
    # first_aid=pending は「鳴っていて、まだ処置を始めていない」（設計 stage3-design.md §2 便F B7）
    if since is not None and since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)
    await set_operator_context(db)
    try:
        result = await db.execute(
            text(
                "SELECT * FROM public.ops_incidents "
                "WHERE (CAST(:status AS text) IS NULL OR status = CAST(:status AS text)) "
                "AND (CAST(:since AS timestamptz) IS NULL OR first_notified_at >= CAST(:since AS timestamptz)) "
                "AND (CAST(:tier AS text) IS NULL OR labels->>'tier' = CAST(:tier AS text)) "
                "AND (CAST(:first_aid AS text) IS NULL "
                "     OR (status = 'firing' AND first_aid_started_at IS NULL)) "
                "ORDER BY first_notified_at DESC LIMIT :limit"
            ),
            {
                "status": status,
                "since": since,
                "limit": limit,
                "tier": tier,
                "first_aid": first_aid,
            },
        )
        items = [dict(r) for r in result.mappings().all()]
    finally:
        await _clear_operator(db)
    return {"items": items}
```

### 4-2. `backend/app/routers/ops.py` に新しい口を足す

置く場所：`get_incident`（`@router.get("/ops/incidents/{incident_id}"` で始まる関数・:318-343）の直後、`# B4 注記` の区切りのコメントの前。

```python
@router.get("/ops/events", dependencies=[Depends(require_ops_reader)])
async def list_events(
    kind: str | None = Query(None, pattern=r"^[a-z_]{1,32}$"),
    service: str | None = Query(None, pattern=r"^[a-z0-9_-]{1,64}$"),
    since: datetime | None = None,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """B8 直近の出来事（ADR-1012 段階3 便F）。

    kind の値の正本は表の制約 ops_incident_events_kind_check。ここでは形だけを確かめる。
    service は出来事ではなく障害の labels から読む（注記の detail は形が決まっていて service を持たない。便F D3）。
    """
    if since is not None and since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)
    await set_operator_context(db)
    try:
        result = await db.execute(
            text(
                "SELECT e.id, e.incident_id, e.occurred_at, e.kind, e.actor, e.detail, "
                "       i.alertname, i.labels->>'service' AS service "
                "FROM public.ops_incident_events e "
                "JOIN public.ops_incidents i ON i.id = e.incident_id "
                "WHERE (CAST(:kind AS text) IS NULL OR e.kind = CAST(:kind AS text)) "
                "AND (CAST(:service AS text) IS NULL OR i.labels->>'service' = CAST(:service AS text)) "
                "AND (CAST(:since AS timestamptz) IS NULL OR e.occurred_at >= CAST(:since AS timestamptz)) "
                "ORDER BY e.occurred_at DESC LIMIT :limit"
            ),
            {"kind": kind, "service": service, "since": since, "limit": limit},
        )
        items = [dict(r) for r in result.mappings().all()]
    finally:
        await _clear_operator(db)
    return {"items": items}
```

### 4-3. `backend/tests/test_ops_router.py` の末尾に試験 4 つを足す

既存の `_alert`・`_payload`・`_incidents`・`_as_dict`（jsonb が文字列で返る環境の吸収・:463-467）・`env` をそのまま使う。追加の import は無い（`datetime`・`timedelta`・`timezone`・`uuid` は既に import 済み・:4-7）。

```python
# ---------------------------------------------------------------------------
# 便F（ADR-1012 段階3）: auto で未処置の一覧・直近の出来事
# ---------------------------------------------------------------------------


async def _ingest_one(env: _Env, fp: str, **labels):
    resp = await env.client.post(
        f"{_BASE}/alertmanager",
        json=_payload(_alert(fp, **labels)),
        headers=env.ingest_headers(),
    )
    assert resp.status_code == 200
    return (await _incidents(env, fp))[0]


async def test_list_incidents_auto_pending_filter(env):
    auto_fp = env.new_fingerprint()
    page_fp = env.new_fingerprint()
    resolved_fp = env.new_fingerprint()
    auto_row = await _ingest_one(env, auto_fp, tier="auto", service="celery-worker")
    await _ingest_one(env, page_fp, tier="page", service="celery-worker")
    starts = datetime(2026, 10, 16, 0, 0, 0, tzinfo=timezone.utc)
    await _ingest_one(env, resolved_fp, tier="auto", service="celery-beat")
    resp = await env.client.post(
        f"{_BASE}/alertmanager",
        json=_payload(
            _alert(
                resolved_fp,
                status="resolved",
                starts_at=starts,
                ends_at=starts + timedelta(minutes=5),
                tier="auto",
                service="celery-beat",
            )
        ),
        headers=env.ingest_headers(),
    )
    assert resp.status_code == 200

    mine = {auto_fp, page_fp, resolved_fp}
    resp = await env.client.get(
        f"{_BASE}/incidents?tier=auto&first_aid=pending&limit=100",
        headers=env.api_headers(),
    )
    assert resp.status_code == 200
    got = [i["fingerprint"] for i in resp.json()["items"] if i["fingerprint"] in mine]
    assert got == [auto_fp]

    resp = await env.client.post(
        f"{_BASE}/incidents/{auto_row['id']}/events",
        json={
            "kind": "first_aid",
            "fields": {"first_aid_started_at": datetime.now(timezone.utc).isoformat()},
        },
        headers=env.api_headers(),
    )
    assert resp.status_code == 200

    resp = await env.client.get(
        f"{_BASE}/incidents?tier=auto&first_aid=pending&limit=100",
        headers=env.api_headers(),
    )
    assert resp.status_code == 200
    got = [i["fingerprint"] for i in resp.json()["items"] if i["fingerprint"] in mine]
    assert got == []

    resp = await env.client.get(
        f"{_BASE}/incidents?tier=auto&limit=100", headers=env.api_headers()
    )
    got = sorted(i["fingerprint"] for i in resp.json()["items"] if i["fingerprint"] in mine)
    assert got == sorted([auto_fp, resolved_fp])


async def test_list_events_kind_service_since_filter(env):
    before = datetime.now(timezone.utc) - timedelta(seconds=5)
    worker_fp = env.new_fingerprint()
    beat_fp = env.new_fingerprint()
    worker_row = await _ingest_one(env, worker_fp, tier="auto", service="celery-worker")
    beat_row = await _ingest_one(env, beat_fp, tier="auto", service="celery-beat")
    for row in (worker_row, beat_row):
        resp = await env.client.post(
            f"{_BASE}/incidents/{row['id']}/events",
            json={
                "kind": "first_aid",
                "fields": {"first_aid_started_at": datetime.now(timezone.utc).isoformat()},
            },
            headers=env.api_headers(),
        )
        assert resp.status_code == 200
    mine = {worker_row["id"], beat_row["id"]}
    mine_str = {str(x) for x in mine}

    resp = await env.client.get(
        f"{_BASE}/events",
        params={"kind": "first_aid", "service": "celery-worker", "since": before.isoformat(), "limit": 100},
        headers=env.api_headers(),
    )
    assert resp.status_code == 200
    got = [e for e in resp.json()["items"] if e["incident_id"] in mine_str]
    assert len(got) == 1
    assert got[0]["incident_id"] == str(worker_row["id"])
    assert got[0]["kind"] == "first_aid"
    assert got[0]["service"] == "celery-worker"
    assert got[0]["alertname"] == "TestAlert"
    assert "first_aid_started_at" in _as_dict(got[0]["detail"])["fields"]

    resp = await env.client.get(
        f"{_BASE}/events",
        params={"kind": "notified", "service": "celery-beat", "since": before.isoformat(), "limit": 100},
        headers=env.api_headers(),
    )
    got = [e["incident_id"] for e in resp.json()["items"] if e["incident_id"] in mine_str]
    assert got == [str(beat_row["id"])]

    future = datetime.now(timezone.utc) + timedelta(hours=1)
    resp = await env.client.get(
        f"{_BASE}/events",
        params={"kind": "first_aid", "since": future.isoformat(), "limit": 100},
        headers=env.api_headers(),
    )
    assert [e for e in resp.json()["items"] if e["incident_id"] in mine_str] == []


async def test_list_events_rejects_missing_or_ingest_token(env):
    resp = await env.client.get(f"{_BASE}/events")
    assert resp.status_code == 401
    resp = await env.client.get(
        f"{_BASE}/events", headers={"Authorization": f"Bearer {env.ingest_token}"}
    )
    assert resp.status_code == 401


async def test_new_filters_reject_bad_values(env):
    for path in (
        f"{_BASE}/incidents?tier=AUTO",
        f"{_BASE}/incidents?first_aid=done",
        f"{_BASE}/events?kind=first-aid;",
        f"{_BASE}/events?service=Celery%20Worker",
        f"{_BASE}/events?limit=101",
    ):
        resp = await env.client.get(path, headers=env.api_headers())
        assert resp.status_code == 422, path
```

試験の意味:

| 試験 | 確かめること |
|---|---|
| `test_list_incidents_auto_pending_filter` | auto かつ鳴っていて未処置の 1 件だけが出る（page の行と鳴り止んだ行は出ない）。処置を始める注記の後は消える。`tier` だけなら鳴り止んだ行も出る |
| `test_list_events_kind_service_since_filter` | kind と service と since の絞り込み。返す行に service・alertname・detail が付く |
| `test_list_events_rejects_missing_or_ingest_token` | 鍵なしと受け口の鍵は 401 |
| `test_new_filters_reject_bad_values` | 形の合わない値と上限超えは 422 |

## 5. 確かめ方（担当が実行し、出力を報告に貼る。生出力は作業場所の外の /tmp/CC報告ファイル/ai-ops-stage3/bin-f-impl/ に置く）

5-1. 試験：Mac では試験を回さない（PO 2026-11-02「試験は Mac で回さず GitHub とクラウドで」）。クラウドの作業場所に PostgreSQL が無い場合は、試験は CI（PR の pytest）に任せ、手元では 5-2 だけを行う。PostgreSQL がある場合だけ `cd backend && python -m pytest tests/test_ops_router.py -v 2>&1 | tail -40` を流し、4 つの試験名が PASSED であることと、既存の試験が FAILED 0 件であることを貼る

5-2. 書式の確認：作業場所で `python3 -m py_compile backend/app/routers/ops.py backend/tests/test_ops_router.py; echo rc=$?` が `rc=0`

5-3. 差分：`git diff origin/main --stat` が §3 のファイルだけ。加えて `git diff origin/main | grep "^-[^-]"` の出力が、`ops.py` の `            {"status": status, "since": since, "limit": limit},` の 1 行と、このカードの §13 の `（未記入）` の 1 行の 2 行だけ

5-4. PR の CI の結果は担当が待たない。PR を作ったら URL を報告して終える（CI の結果は Opus が見る）

## 6. 分岐ごとの対処

- §4-1 の変更前のコードが origin/main と一致しない（ほかの PR が先に変えた）→ 一致しない部分の原文を貼って NEEDS_DECISION:
- `/ops/events` の道が既にある → 原文を貼って NEEDS_DECISION:
- CI の pytest が落ちる → 担当は直さない。Opus が落ちた試験名と原文を読み、§4 との違いなら担当に戻す。共有 DB のぶつかり（既知・メモリ test_lock_collisions）なら Opus が流し直す

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 新しい試験 4 つと既存の試験がすべて pass | CI の pytest（PR の checks）の記録で 4 つの試験名が passed |
| auto かつ未処置だけが一覧に出て、処置の注記の後は消える | 同上（`test_list_incidents_auto_pending_filter`） |
| 出来事を kind・service・since で絞れ、行に service が付く | 同上（`test_list_events_kind_service_since_filter`） |
| 鍵なし・受け口の鍵では 401、形の合わない値は 422 | 同上（残りの 2 つ） |
| 触ったファイルが §3 だけ | §5-3 |
| 本番：反映後、保守の鍵で `GET /api/v1/ops/incidents?tier=auto&first_aid=pending` が 200 で `items` が空（auto の見張りが 0 本のため）。`GET /api/v1/ops/events?kind=notified&limit=1` が 200 で 1 件 | §8-3 の生出力（件数と状態コードだけを記録し、中身は出さない） |
| 本番：反映後 24 時間、この口が原因の 5xx が 0 件 | §8-4 |

## 8. 反映の手順（Opus が行う。担当はしない）

1. 審査：差分を §4 と照らし、CI が緑なら、マージ前の審査役（reviewer・opus）の APPROVE を得て、確認済みのコメントを残してマージする（危険 PR ではないので GO 記録は要らない）
2. deploy.yml の成功を Actions の記録で確かめる
3. prod1 の中から（ubuntu の鍵・読むだけ）`docker compose exec -T backend` で、`.env` の OPS_API_TOKEN を使って §7 の 2 つの口を `localhost:8000` に向けて呼び、状態コードと `len(items)` だけを出す。鍵の値は画面にもファイルにも出さない
4. 24 時間後に backend のログで `/api/v1/ops/events` と `/api/v1/ops/incidents` の 5xx を数える（読むだけ）
5. 生出力は /tmp/CC報告ファイル/ai-ops-stage3/bin-f-deploy/ に置く

## 9. 弊害と戻し方

- 弊害：出来事の口は索引の無い条件（kind・occurred_at）で読む。行数が増えると遅くなる。今は便G が 1 分に 1 回呼ぶだけ。遅さが見えたら別の便で索引を足す（D5）
- 弊害：labels が 4000 バイトを超えた障害は tier が落ちるので、auto の一覧に出ない（F4）。見張りの labels は短いので今は起きない。起きると処置されないが、同じ障害は Discord と page に出るので人の目には残る
- 戻し方：この PR の revert を main にマージする。書き込みも表の変更も無いので、データの戻しは要らない

## 10. PR

- 作業場所: `cd /Users/tanizawashingo/salesanchor && bash scripts/new-worktree.sh release/ai-ops-incidents-filter-bin-f --claude`（origin/main 起点）。クラウドで clone した場合も、commit の前に必ずこの手順で作業場所を作る（メモリ cloud_card_new_worktree）。出力はパイプに通さない。作成後に `git worktree list` で実在を確かめる。以後の作業はすべてその作業場所に `cd` してから行う
- push は `git push -u origin HEAD` を使う。commit の後に `git log -1 --oneline`、push の後に `git log origin/release/ai-ops-incidents-filter-bin-f -1 --oneline` で実在を確かめる。`--no-verify` は使わない
- PR は `scripts/gh-pr-create-safe.sh` に、先に Write ツールで作った本文ファイルを絶対パスで渡して作る（`$変数` を使わない）
- 作成前に `gh auth status` で `shingo-cc` 名義であることを確かめる
- PR は ready で作る（`--draft` を付けない）。base は main。担当はマージしない
- 本文は PR テンプレートに沿い、`### 標準ワークフロー確認` に、recon（docs/handoff/ai-ops-247/recon.md）・設計（docs/handoff/ai-ops-247/stage3-design.md）・このカード・ADR-1012 を書く。`触るファイル:` と `削除するファイル:` は 1 行・カンマ区切り・バッククォートなし・注記なし（触るファイル: backend/app/routers/ops.py, backend/tests/test_ops_router.py, docs/handoff/ai-ops-247/card-stage3-bin-f.md ／ 削除するファイル: backend/app/routers/ops.py, docs/handoff/ai-ops-247/card-stage3-bin-f.md）
- 作成前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し exit 0 を確かめる（2 分以上かかるので timeout を長めにする）

## 11. 報告

- 完了報告の本文に: 冒頭の受領文／§5-1〜5-3 の出力（長いものは生出力のパスと要点の行）／PR の URL／判断を要した点（事実のみ）
- 停止したときは: 停止した手順番号／最後に実行したコマンド／停止した理由の原文
- 1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか

## 12. 委任の定型

- CI・デプロイは待たない（待ちは Opus が行う）
- ファイルの作成と編集は Write/Edit ツールで行う（ヒアドキュメントで書かない）
- PR を作る前に `scripts/dev/validate-pr-body.sh` で exit 0 を確かめる
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える

## 13. 報告欄（担当が追記）

（未記入）

## 14. 設計審査（Opus 自己審査・2026-11-19）

判定: APPROVE（設計合格）。同一 AI の自己審査であり、独立した第二者の審査ではない。PO の実装承認を兼ねない。

| 観点 | 結果 | 根拠 |
|---|---|---|
| 既存の設計との整合 | ○ | 設計 §2 便F の B7 は D2 でそのまま。B8 は「service をどこから読むか」だけを D3 で直した（注記の detail は形が固定・F7）。目的（同じ service の直近の処置を数える）と「書き込み・表・列・migration を足さない」は守った |
| 正本の 1 か所 | ○ | 札の値（D1）・kind の値（D4）は一覧をコードに書かず、形だけを確かめる。service は障害の labels（既存の 1 か所）から読む |
| 鍵 | ○ | 2 つの口とも既存の `require_ops_reader`（F2）。新しい鍵は無い |
| 運用者の旗 | ○ | 既存の口と同じ形（F3） |
| 受け入れ基準の検証可能性 | ○ | §7 の各行が CI の試験名か本番の状態コード・件数で ○× になる |
| 実装範囲の明確さ | ○ | §3 の 3 ファイル・§4 に変更前後の全文 |
| 未解決の前提 | なし | 道の重なり 0 件（F10）。危険パスなし |

END OF CARD
