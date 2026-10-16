# 実装カード 段階2 便B — 保守 API を作る（受け口・読む・注記・止める）

> この文書は何か：AI保守運用24時間化 段階2 便B の作業指示書です。便A で作った障害記録の表 3 つに、読み書きする口（保守 API）を 1 本のルーターで作ります。Alertmanager から通知を受ける口は、監視サーバ（prod2）の IP からしか届かないように nginx で絞ります。鍵が無い間は、どの口も 401 で閉じたままです。

- 設計: docs/handoff/ai-ops-247/stage2-design.md §2 便B・§1 T10〜T17・§6
- 親設計: docs/handoff/ai-ops-247/design.md §5 段階2（:103-110）
- 前便: 便A（#4357 マージ cd3c35daa・本番の表 3 つは空で RLS・ポリシー・権限とも合格。/tmp/CC報告ファイル/ai-ops-stage2-bin-a/deploy/catalog_result.txt）
- 対象ADR: ADR-1012（本テーマ）、ADR-1018（運用者の旗の RLS）、ADR-131（get_db の後片付け）、ADR-135・ADR-136（危険 PR の GO）
- 状態: 設計は Opus 自己審査 APPROVE（stage2-design.md §9）。段階2 の着手は PO の「次を進める」（2026-10-16）。このカードの §2-2 の設計の細部の決定は Opus の技術判断（親設計の目的・範囲を変えない）
- 危険便: はい（`.github/workflows/deploy.yml` を含む）。GO は ADR-136 の手順で Opus（PO の委任）が出す。担当はマージしない
- 担当: 実装 Sonnet／コード審査・GO・マージ・反映確認 Opus

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は ready で作る（Draft にしない）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（保守 API と、それを外に出す設定だけ。Alertmanager の送り先は便C） |
| 5 | 既存ブランチへの追記ではない（新規ブランチ） | ○ |
| 6 | 書式は実例で示した | ○（§4 に nginx・env・SQL の完成形） |
| 7 | 合格基準を出力まで縛った | ○（§5） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-2・§5-4） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実物から | ○（行の目印は origin/main 539b0fe41 で確かめた） |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§12） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない | ○（§5・§10・§12） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○ |
| guards/04-worktree.md | new-worktree.sh の出力をパイプに通さず、実在は `ls -1d` と `git worktree list` で確かめる | ○（§10） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh` で作る。触るファイル・削除するファイルは同一行カンマ区切り | ○（§10） |
| guards/08-vps.md | 本番には触らない（本番の確認は Opus が行う） | ○（§8） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード 段階2 便B の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. 新しいルーター `backend/app/routers/ops.py`（§4-1〜4-6）
2. `backend/app/main.py` に include の 1 か所（§4-7）
3. nginx の受け口の location 1 つ（§4-8）
4. env 2 つを deploy.yml の 2 か所と docker-compose.yml の backend に足す（§4-9）
5. 試験 `backend/tests/test_ops_router.py` と、ops_control の試験を直列にする小さな部品 `backend/tests/ops_control_lock.py`、便A の試験 1 本にその部品を使わせる変更（§4-10）

入れない:
- Alertmanager の設定・prod2 の秘密ファイル（便C）
- migration（表は便A で作り済み。列も足さない）
- 画面（月次成績表は段階6）
- 全停止スイッチを読む処置・AI 起動の側（段階3・4）
- `backend/app/auth/dependencies.py` の変更（鍵の照合はルーターの中に書く。既存の `get_current_user` を呼ぶだけ）
- `backend/tests/rls_bootstrap.py` の変更

## 2. 前提の事実と設計の細部

### 2-1. 事実（origin/main 539b0fe41・生出力 /tmp/CC報告ファイル/ai-ops-stage2-bin-b/recon/）

| # | 事実 | 出典 |
|---|---|---|
| F1 | `set_operator_context(db: AsyncSession)` は async で、`SET app.is_operator = 'true'` をセッション単位で打つ。`reset_operator_context(db)` は commit の後に呼ぶ。SQLite では何もしない | `backend/app/auth/dependencies.py:489-520` |
| F2 | 運用者の書き込みの前例：`await set_operator_context(db)` → `try:` 生 SQL → `await db.commit()` → `finally: await reset_operator_context(db)` | `backend/app/routers/fx_rate_admin.py:135-149` |
| F3 | `get_current_user(request, cred, db)` は `HTTPBearer()` の資格情報と `get_db` のセッションを取る。`require_super_admin` は `is_super_admin` が偽なら 403 | `backend/app/auth/dependencies.py:35`・`:131-`・`:523-551` |
| F4 | 機械の鍵の照合の前例：`secrets.compare_digest` で比べ、`TypeError`・`ValueError` は不一致に倒す | `backend/app/auth/dependencies.py:119-128` |
| F5 | `get_db` は `AsyncSessionLocal` の 1 セッションを yield し、例外で rollback、最後に `clear_tenant_context` | `backend/app/database.py:46-61` |
| F6 | ルーターの付け方：大半は `prefix="/api/v1"` で、パスはルーター側が持つ。最後の include は `super_admin_db_schema.router`（`backend/app/main.py:757-759`） | `backend/app/main.py:235-759` |
| F7 | super admin 用のルーターは `get_current_tenant` を付けずに include し、`text()` の生 SQL で public を読む | `backend/app/routers/super_admin_suppliers.py:92-100`・`backend/app/main.py:513-516` |
| F8 | api.salesanchor.jp の 443 の server は `nginx/nginx.conf:285`。その中の `location /api/ {` が `:387`、server の `client_max_body_size 10m;` が `:306`。prod2 の IP だけを許す前例は app 側の `location = /metrics`（`:246-255`） | `nginx/nginx.conf` |
| F9 | deploy.yml の古い行の削除は `-e '/^AUTH_VIEWER_JWT_SECRET=/d' \`（`:289`）の次が `-e '/^COMPOSE_FILE=/d' \`。書き込みは `AUTH_VIEWER_JWT_SECRET=${{ secrets.AUTH_VIEWER_JWT_SECRET }}`（`:332`）の次が `COMPOSE_FILE=...`（`:333`） | `.github/workflows/deploy.yml` |
| F10 | docker-compose.yml の backend の environment に `- AUTH_VIEWER_JWT_SECRET=${AUTH_VIEWER_JWT_SECRET:-}`（`:135`）がある（1 か所だけ） | `docker-compose.yml:135` |
| F11 | ルーターを実 PostgreSQL で叩く試験の前例：`httpx.AsyncClient(transport=ASGITransport(app=app))`、`app.dependency_overrides[get_db]` にアプリのロールのセッションを渡し、最後に `clear()` | `backend/tests/test_countries_master.py`（:6・:121 付近・:178-185・:216） |
| F12 | pytest は `-n auto --dist=loadfile`（同じファイルの試験は同じ worker、別ファイルは並行に走りうる）。便A の試験 `test_ops_control_allows_only_id_1` が ops_control の id=1 を作って消す | `backend/pyproject.toml:65`・`backend/tests/test_ops_incident_tables_rls.py:243-` |
| F13 | ops_control は `id SMALLINT PRIMARY KEY`・`halt_all`・`changed_at`・`changed_by NOT NULL`・`reason`、`CHECK (id = 1)`。ops_incident_events の `incident_id` は NOT NULL | `migrations/20261016_100000_create_ops_incident_tables.sql:65-72`・`:30-42` |
| F14 | pydantic は 2.10.6 | `backend/requirements.txt:8` |
| F15 | `backend/app/routers/` に ops の名のファイルは無く、`/ops` を使う既存の口も無い | recon/q11.txt |

### 2-2. 設計の細部の決定（Opus・stage2-design.md からの補い）

| # | 決めたこと | 理由 |
|---|---|---|
| D1 | 便B で本番に置く鍵は保守の鍵（`OPS_API_TOKEN`）だけ。受け口の鍵（`OPS_INGEST_TOKEN`）は便C で作って置く | 受け口の鍵を使うのは Alertmanager だけで、置き場所（prod2）を触るのは便C。env が空の間、受け口は 401 で閉じている（B6）。便B の段で作ると、便C まで値をどこかに預ける必要が出る |
| D2 | 全停止（ON・OFF）の出来事は ops_incident_events に書かない。ops_control の行（最後の変更者・時刻・理由）と、アプリのログ（`logger.warning`）に残す | 出来事の表は `incident_id` が NOT NULL（F13）で、障害に結び付かない出来事を入れられない。表を変えるのは migration で危険便が増えるため、段階2 ではしない |
| D3 | 保守の鍵での OFF は 403（401 ではない）。受け口の鍵を B2〜B5 に出したら 401 | 設計 §6「保守の鍵で OFF は 403」。鍵は正しいが権限がない、を区別する |
| D4 | 本体の大きさは、アプリでも 256KB を超えたら 413（nginx の 256k と二重）。`alerts` が 100 件を超えたら 413 | 設計 §2 便B。試験は nginx を通らないので、アプリの側にも置く |
| D5 | labels・annotations が 4,000 バイトを超えたら、小さく作り直して保存する（labels は `alertname`・`severity` と `"_truncated": true` だけ、annotations は `summary` の先頭 1,000 文字と `"_truncated": true` だけ） | 表の CHECK は 4,096 バイト（便A）。JSONB の文字の形とずれても超えないように余裕を取る。列は足さない |
| D6 | 本番では全停止を ON にしない（便B の反映確認でも打たない） | ON を戻すのは super admin のログインだけで、いまは戻す画面が無い。段階2 では pytest で確かめ、本番の 1 回の切り替えは戻す手段ができる段に移す（§9 の未解決 V5） |

## 3. 触るファイル（これ以外は触らない）

- 新規: `backend/app/routers/ops.py`
- 変更: `backend/app/main.py`（include の 3 行の追記のみ）
- 変更: `nginx/nginx.conf`（location 1 つの追記のみ）
- 変更: `.github/workflows/deploy.yml`（4 行の追記のみ）
- 変更: `docker-compose.yml`（backend の environment に 3 行の追記のみ）
- 新規: `backend/tests/test_ops_router.py`
- 新規: `backend/tests/ops_control_lock.py`
- 変更: `backend/tests/test_ops_incident_tables_rls.py`（`test_ops_control_allows_only_id_1` を部品で囲むだけ）
- 変更: `docs/handoff/ai-ops-247/card-stage2-bin-b.md`（このカード。§13 報告欄の追記のみ）

## 4. 作り方

### 4-1. ルーターの骨組み（`backend/app/routers/ops.py`）

- `router = APIRouter(tags=["ops"])`。パスはルーター側に `/ops/...` で書く（main.py で `prefix="/api/v1"`）
- 依存：`from app.database import get_db`、`from app.auth.dependencies import get_current_user, set_operator_context, reset_operator_context`。`get_current_user` はモジュールの名前として import し、関数の中で `get_current_user(request, cred, db)` と呼ぶ（試験で `app.routers.ops.get_current_user` を差し替えるため）
- `_bearer = HTTPBearer(auto_error=False)`（ヘッダが無いときに 403 ではなく自分で 401 を返すため）
- 鍵の値は関数の中で毎回 `os.getenv("OPS_INGEST_TOKEN", "")`・`os.getenv("OPS_API_TOKEN", "")` で読む（モジュールの読み込み時に固定しない。試験の `monkeypatch.setenv` を効かせるため）
- 照合の関数（F4 と同じ形）:

```python
def _token_matches(presented: str | None, expected: str) -> bool:
    if not presented or not expected:
        return False
    try:
        return secrets.compare_digest(presented, expected)
    except (TypeError, ValueError):
        return False
```

- DB の読み書きは、すべて F2 の形で行う：`await set_operator_context(db)` → `try:` → 生 SQL（`text()`・値は必ずバインド変数）→ 書き込みなら `await db.commit()` → `finally: await reset_operator_context(db)`。読むだけの口も同じ形（commit は不要）

### 4-2. 鍵の依存関数 3 つ

| 関数 | 通すもの | 拒むもの |
|---|---|---|
| `require_ops_ingest(cred=Depends(_bearer))` | `OPS_INGEST_TOKEN` と一致 | ヘッダなし・不一致・env が空 → 401 |
| `require_ops_reader(request, cred=Depends(_bearer), db=Depends(get_db))` | `OPS_API_TOKEN` と一致 → `{"actor": "ops_token", "user_id": None}`。それ以外は `get_current_user(request, cred, db)` を呼び、`is_super_admin` が真なら `{"actor": "super_admin", "user_id": user.id}` | ヘッダなし → 401。`OPS_INGEST_TOKEN` と一致 → 401（ログインの照合に回さない）。ログインの照合の例外はそのまま上げる（401）。ログインできても super admin でなければ 403 |
| `require_ops_super_admin(request, cred=Depends(_bearer), db=Depends(get_db))` | `get_current_user` の利用者で `is_super_admin` が真 → `{"actor": "super_admin", "user_id": user.id}` | ヘッダなし → 401。`OPS_API_TOKEN` か `OPS_INGEST_TOKEN` と一致 → 403（D3）。super admin でない → 403 |

- 401 は `HTTPException(status_code=401, detail="OPS_UNAUTHORIZED", headers={"WWW-Authenticate": "Bearer"})`、403 は `HTTPException(status_code=403, detail="OPS_FORBIDDEN")`

### 4-3. B1 受け口 `POST /ops/alertmanager`（`dependencies=[Depends(require_ops_ingest)]`）

- 引数は `request: Request` と `db: AsyncSession = Depends(get_db)`。本体は `body = await request.body()` で読み、`len(body) > 262144` なら 413（`detail="OPS_PAYLOAD_TOO_LARGE"`）。次に `AlertmanagerPayload.model_validate_json(body)`（失敗は 422）。`len(payload.alerts) > 100` なら 413
- pydantic のモデル（`model_config = ConfigDict(extra="ignore")`。知らない項目は捨てる）:
  - `AlertmanagerAlert`: `status: Literal["firing", "resolved"]`・`labels: dict[str, str] = {}`・`annotations: dict[str, str] = {}`・`startsAt: datetime`・`endsAt: datetime | None = None`・`fingerprint: str = Field(min_length=1, max_length=200)`
  - `AlertmanagerPayload`: `status: str | None = None`・`receiver: str | None = None`・`groupKey: str | None = None`・`alerts: list[AlertmanagerAlert]`
- 1 件ごとに、次の SQL を 1 回（同じトランザクション。最後に 1 回だけ commit）:

```sql
INSERT INTO public.ops_incidents
    (fingerprint, starts_at, alertname, severity, labels, annotations, status,
     first_notified_at, last_notified_at, resolved_at, recurrence_of)
VALUES
    (:fingerprint, :starts_at, :alertname, :severity, CAST(:labels AS jsonb), CAST(:annotations AS jsonb), :status,
     now(), now(), :resolved_at,
     (SELECT p.id FROM public.ops_incidents p
       WHERE p.fingerprint = :fingerprint AND p.starts_at < :starts_at
       ORDER BY p.starts_at DESC LIMIT 1))
ON CONFLICT (fingerprint, starts_at) DO UPDATE SET
    last_notified_at = now(),
    notify_count = public.ops_incidents.notify_count + 1,
    status = EXCLUDED.status,
    resolved_at = COALESCE(EXCLUDED.resolved_at, public.ops_incidents.resolved_at),
    updated_at = now()
RETURNING id, (xmax = 0) AS inserted
```

  - `alertname` は `labels.get("alertname") or "unknown"`、`severity` は `labels.get("severity")`
  - `resolved_at` は `status == "resolved"` のときだけ `endsAt`、ほかは `None`
  - `labels`・`annotations` は `json.dumps(..., ensure_ascii=False)` の文字列で渡す。4,000 バイトを超えたら D5 の形に作り直す
- 続けて出来事を 1 行足す：`INSERT INTO public.ops_incident_events (incident_id, kind, actor, detail) VALUES (:incident_id, :kind, 'alertmanager', CAST(:detail AS jsonb))`。`kind` は firing なら `notified`、resolved なら `resolved`。`detail` は `{"status": alert.status, "receiver": payload.receiver, "groupKey": (payload.groupKey or "")[:500]}`
- 全停止スイッチは見ない（記録は止めない。設計 §3-2）
- 応答は 200 で `{"received": 件数, "created": inserted が真の件数, "updated": 偽の件数}`

### 4-4. B2・B3 読む（`require_ops_reader`）

- `GET /ops/incidents`：`status: Literal["firing", "resolved"] | None = None`・`since: datetime | None = None`（`first_notified_at >= :since`。時差の無い値が来たら UTC として `tzinfo=timezone.utc` を付けてから渡す）・`limit: int = Query(50, ge=1, le=100)`。`ORDER BY first_notified_at DESC LIMIT :limit`。応答は `{"items": [行の全列の dict, ...]}`（`result.mappings()` を dict にし、FastAPI の JSON 変換に任せる）
- `GET /ops/incidents/{incident_id}`（`incident_id: UUID`）：障害の 1 行と、出来事を `occurred_at` の順に全部。無ければ 404（`detail="OPS_INCIDENT_NOT_FOUND"`）。応答は `{"incident": {...}, "events": [...]}`

### 4-5. B4 注記 `POST /ops/incidents/{incident_id}/events`（`require_ops_reader`）

- 本体のモデル（`ConfigDict(extra="forbid")`。知らない項目は 422）:
  - `kind: Literal["annotated", "first_aid", "ai"]`
  - `note: str | None = Field(None, max_length=2000)`
  - `fields: OpsIncidentFields = OpsIncidentFields()`
- `OpsIncidentFields`（`extra="forbid"`・全部省略可）：`human_noticed_at: datetime`・`needs_action: bool`・`first_aid_started_at: datetime`・`first_aid_done_at: datetime`・`first_aid_result: Literal["recovered", "not_recovered", "escalated"]`・`ai_started_at: datetime`・`root_cause: str（max_length=4000）`・`fix_pr: int（ge=1）`・`review_note: str（max_length=4000）`・`detection_path: Literal["alert", "human", "ai"]`
- 更新する列は、`fields.model_dump(exclude_unset=True)` の名前を、ルーターに書いた固定の一覧 `_ANNOTATABLE_COLUMNS`（上の 10 個）と照らして作る。SQL の列名に利用者の文字列をそのまま入れない。`UPDATE public.ops_incidents SET root_cause = :root_cause, fix_pr = :fix_pr, updated_at = now() WHERE id = :id RETURNING id`（例は root_cause と fix_pr の 2 列のとき。列は一覧から選んだものだけを並べる）。更新する列が無ければ `SELECT id ... WHERE id = :id` で在るかだけ確かめる。どちらも 0 行なら 404
- 出来事を 1 行：`kind` はそのまま、`actor` は依存関数の `actor`、`detail` は `{"fields": 更新した列名の並び替えた一覧, "note": note, "user_id": user_id}`
- 応答は 200 で `{"incident_id": "...", "updated_fields": [...]}`

### 4-6. B5 全停止スイッチ

- `GET /ops/control`（`require_ops_reader`）：`SELECT halt_all, changed_at, changed_by, reason FROM public.ops_control WHERE id = 1`。行が無ければ `{"halt_all": false, "changed_at": null, "changed_by": null, "reason": null}`
- `POST /ops/control/halt`（`require_ops_reader`）：本体 `{"reason": str（min_length=1・max_length=500）}`（`extra="forbid"`）

```sql
INSERT INTO public.ops_control (id, halt_all, changed_at, changed_by, reason)
VALUES (1, true, now(), :changed_by, :reason)
ON CONFLICT (id) DO UPDATE SET
    halt_all = true, changed_at = now(), changed_by = EXCLUDED.changed_by, reason = EXCLUDED.reason
RETURNING halt_all, changed_at, changed_by, reason
```

- `POST /ops/control/resume`（`require_ops_super_admin`）：同じ形で `halt_all = false`
- `changed_by` は、保守の鍵なら `"ops_token"`、super admin なら `"super_admin:<user_id>"`
- ON・OFF のたびに `logger.warning("[ops] halt_all=%s by=%s reason=%s", ...)`（D2）
- 応答は SQL の RETURNING の 1 行

### 4-7. main.py（`backend/app/main.py`）

`super_admin_db_schema.router` の include（いまは :757-759）の直後に、次の 3 行を足す（import は同じファイルのほかのルーターと同じ書き方で `ops` を足す）:

```python
# ADR-1012 段階2 便B: 保守 API（鍵か super admin のログイン。テナント文脈なし）
app.include_router(ops.router, prefix="/api/v1")

```

（`get_current_tenant` は付けない。F7 の super admin 用ルーターと同じ）

### 4-8. nginx（`nginx/nginx.conf`）

api.salesanchor.jp の server の中、`location /api/ {`（いまは :387）の直前に、次を足す（中身は `/api/` の写しに、IP の制限と大きさの上限を足したもの）:

```nginx
    # ADR-1012 段階2 便B: Alertmanager の受け口は監視サーバ（prod2）からだけ
    location = /api/v1/ops/alertmanager {
        allow 49.212.160.98;
        deny all;
        client_max_body_size 256k;
        limit_req zone=api burst=50;
        limit_req_status 429;

        proxy_pass http://$backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Request-ID $request_id;
        proxy_connect_timeout 10s;
        proxy_send_timeout    60s;
        proxy_read_timeout    120s;
    }

```

### 4-9. env（3 か所）

- `.github/workflows/deploy.yml` の削除の側：`-e '/^AUTH_VIEWER_JWT_SECRET=/d' \` の行の直後に、同じ字下げで次の 2 行:

```text
              -e '/^OPS_API_TOKEN=/d' \
              -e '/^OPS_INGEST_TOKEN=/d' \
```

- `.github/workflows/deploy.yml` の書き込みの側：`AUTH_VIEWER_JWT_SECRET=${{ secrets.AUTH_VIEWER_JWT_SECRET }}` の行の直後に、同じ字下げで次の 2 行:

```text
            OPS_API_TOKEN=${{ secrets.OPS_API_TOKEN }}
            OPS_INGEST_TOKEN=${{ secrets.OPS_INGEST_TOKEN }}
```

- 上の 2 か所で deploy.yml は 4 行の追記になる（§5-4 は 4 行で判定する）
- `docker-compose.yml`：`- AUTH_VIEWER_JWT_SECRET=${AUTH_VIEWER_JWT_SECRET:-}` の行の直後に、同じ字下げで次の 3 行:

```yaml
      # ADR-1012 段階2 便B: 保守 API の鍵（空なら口は全部 401）
      - OPS_API_TOKEN=${OPS_API_TOKEN:-}
      - OPS_INGEST_TOKEN=${OPS_INGEST_TOKEN:-}
```

- secret が未登録でも deploy は空の値で書く（既存の決まり。deploy.yml:294-298 のコメント）。空なら口は閉じたまま

### 4-10. 試験

`backend/tests/ops_control_lock.py`（新規。ops_control の id=1 を触る試験を、ファイルをまたいで直列にする）:

```python
"""ops_control（id=1 の 1 行）を触る試験を直列にする。pytest は --dist=loadfile で別ファイルが並行に走るため。"""

from contextlib import asynccontextmanager

from sqlalchemy import text

_LOCK_KEY = 1012002  # ADR-1012 段階2


@asynccontextmanager
async def ops_control_lock(admin_engine):
    async with admin_engine.connect() as conn:
        await conn.execute(text("SELECT pg_advisory_lock(:k)"), {"k": _LOCK_KEY})
        try:
            yield
        finally:
            await conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": _LOCK_KEY})
```

`backend/tests/test_ops_incident_tables_rls.py` の `test_ops_control_allows_only_id_1`：本体（準備の後から後片付けの終わりまで）を `async with ops_control_lock(admin_engine):` で囲む。ほかの試験は変えない。

`backend/tests/test_ops_router.py`（新規）:
- 冒頭の環境の扱い（2 本の接続・skip の条件・`pytest.mark.asyncio`）は `backend/tests/test_ops_incident_tables_rls.py:1-26` と同じ。準備で同じ migration を `public_bootstrap_lock` の中で `_apply_migration` する
- `app.dependency_overrides[get_db]` に、アプリのロール（`RLS_TEST_DATABASE_URL`）のセッションを yield する関数を入れる（F11）。試験の終わりに `app.dependency_overrides.clear()`
- 鍵は `monkeypatch.setenv("OPS_INGEST_TOKEN", "test-ingest-" + uuid4().hex)` と `monkeypatch.setenv("OPS_API_TOKEN", "test-api-" + uuid4().hex)`
- super admin の試験は `monkeypatch.setattr("app.routers.ops.get_current_user", 偽の関数)`。偽の関数は `is_super_admin` を持つ利用者を返す async 関数
- 作る行の `fingerprint` は `"test-ops-api-" + uuid4().hex`。後片付けは管理の接続で、その fingerprint の出来事 → 障害の順に消す。ops_control を触る試験は `ops_control_lock` の中で行い、後片付けで `id = 1` の行を消す
- 試験は次の 12 本（名前もこのとおり）:

| # | 試験の名前 | 確かめること |
|---|---|---|
| 1 | `test_ingest_creates_incident_and_event` | firing 1 件で 200・`created` 1、管理の接続で障害 1 行（`notify_count` 1・`status` firing）と出来事 1 行（`notified`・`alertmanager`） |
| 2 | `test_ingest_same_alert_twice_merges` | 同じ中身を 2 回送ると障害は 1 行のまま `notify_count` 2、出来事は 2 行 |
| 3 | `test_ingest_resolved_sets_resolved_at` | firing の後に同じ fingerprint・startsAt で resolved を送ると `status` resolved・`resolved_at` が endsAt と同じ |
| 4 | `test_ingest_recurrence_links_previous` | 同じ fingerprint で startsAt が後の通知を送ると新しい行ができ、`recurrence_of` が前の行の id |
| 5 | `test_ingest_rejects_missing_wrong_or_empty_token` | ヘッダなし 401・保守の鍵 401・`OPS_INGEST_TOKEN` を空にすると任意の鍵で 401 |
| 6 | `test_ingest_payload_limits_return_413` | 256KB を超える本体で 413・`alerts` 101 件で 413（どちらも行は増えない） |
| 7 | `test_reader_rejects_ingest_token_and_empty_env` | 受け口の鍵で `GET /api/v1/ops/incidents` が 401・`OPS_API_TOKEN` を空にすると 401 |
| 8 | `test_list_and_detail_with_ops_token` | 1 件受けた後、保守の鍵で一覧が 200 でその行を含み、詳細が 200 で出来事 1 件。無い id で 404 |
| 9 | `test_annotate_updates_allowed_fields_only` | `fields` に `root_cause` と `fix_pr` で 200・2 列が入り、出来事 `annotated` が 1 行増える。`fields` に知らない名前で 422 |
| 10 | `test_halt_with_ops_token_resume_requires_super_admin` | 保守の鍵で halt 200（`halt_all` true）→ 保守の鍵で resume 403 → super admin でない利用者で resume 403 → super admin で resume 200（`halt_all` false） |
| 11 | `test_ingest_continues_while_halted` | halt の後に受け口へ 1 件送ると 200 で障害が 1 行できる |
| 12 | `test_rows_invisible_without_operator_flag_after_request` | 受け口で 1 件作った後、アプリのロールの別の接続で旗を立てずに読むと 0 行（口の後に旗が残っていない） |

## 5. 確かめ方（担当が実行し、出力を報告に貼る）

5-1. 静的検査：作業場所で `cd backend && ruff check app/routers/ops.py tests/test_ops_router.py tests/ops_control_lock.py tests/test_ops_incident_tables_rls.py` が 0 件。

5-2. 試験の名前の対：`grep -nE "^async def test_" backend/tests/test_ops_router.py` が 12 行で、名前が §4-10 の表のとおり。

5-3. 試験：`cd backend && python3 -m pytest tests/test_ops_router.py tests/test_ops_incident_tables_rls.py -q -p no:cacheprovider` の出力。手元に PostgreSQL が無ければ skip になる（19 skipped）。そのときは「手元では skip・CI の pytest-run-internal で実行」と書く。

5-4. 差分：`git diff origin/main --stat` が §3 の 9 ファイル。加えて `git diff origin/main -- .github/workflows/deploy.yml docker-compose.yml nginx/nginx.conf backend/app/main.py | grep -c "^-[^-]"` が 0（削除の行が無い）。deploy.yml の追加の行は 4 行。

5-5. SQL の列名に利用者の文字列が入らないこと：`grep -n "_ANNOTATABLE_COLUMNS" backend/app/routers/ops.py` の出力（定義の行と、使う行）。

5-6. PR の CI の結果は担当が待たない。PR を作ったら URL を報告して終える（CI は Opus が見る）。

## 6. 分岐ごとの対処

- §4-7〜4-9 の目印の行が見つからない（ほかの PR が先に変えた）→ 目印の行を `git show origin/main:nginx/nginx.conf | grep -n "location /api/"` のように、そのファイルを origin/main で grep して探し直し、同じ意味の位置に足す。意味の同じ位置が決められなければ NEEDS_DECISION: で、探した grep の出力を貼る
- 試験 10 で、保守の鍵の resume が 403 以外 → 依存関数の順番（鍵の照合をログインの照合より先に）を確かめる。直せなければ BLOCKED:
- 試験 12 で行が見える → `reset_operator_context` を `finally` で呼んでいるかを確かめる。直せなければ BLOCKED:（旗の漏れは権限の穴なので推測で直さない）
- `INSERT ... ON CONFLICT` が RLS で拒まれる（`42501`）→ 失敗の出力をそのまま貼って BLOCKED:（ポリシーの設計を Opus が見る）
- CI の migration-guard・nginx の検査が落ちる → 失敗の原文を貼って BLOCKED:

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 同じ通知 2 回で 1 行・`notify_count` 2、resolved で `resolved_at`、再発で `recurrence_of` | CI の pytest（§4-10 の 1〜4） |
| 鍵の取り違え・空の鍵で 401、保守の鍵での OFF は 403 | CI の pytest（5・7・10） |
| 上限を超えると 413 | CI の pytest（6） |
| 止めている間も記録は続く | CI の pytest（11） |
| 口の後に運用者の旗が残らない | CI の pytest（12） |
| 触ったファイルが 9 つで、既存の行を消していない | §5-4 |
| 反映後、Mac から受け口は 403、保守の鍵で一覧が 200 で空 | §8（Opus） |

## 8. 反映の前後（Opus が行う。担当はしない）

- 反映の前：保守の鍵を作る PO の `!` スクリプト（`secrets.token_urlsafe(32)` → `gh secret set OPS_API_TOKEN` → Mac の `~/.claude-access.env` に追記。値は画面に出さない）。secrets の変更なので、実行の前に PO に y/n を聞く
- マージ → deploy の成功（nginx の force-recreate の段を含む）を Actions の記録で確かめる
- Mac から：`POST https://api.salesanchor.jp/api/v1/ops/alertmanager` が 403（nginx の IP 制限）。保守の鍵で `GET https://api.salesanchor.jp/api/v1/ops/incidents` が 200 で `{"items": []}`。鍵なしで同じ口が 401。鍵の値は出さない
- 全停止は本番で打たない（D6）
- 生出力は /tmp/CC報告ファイル/ai-ops-stage2-bin-b/deploy/ に置く

## 9. 戻し方と未解決事項

- 戻し方：この PR の revert を main にマージ（表は残る。env は残っても使う口が無い）。nginx の location も revert で消える
- 鍵の作り直し：PO の `!` スクリプトをもう一度実行 → deploy
- V5（新規）：本番での全停止の 1 回の切り替え（設計 §6）は、super admin が OFF に戻す手段（画面か PO の手順）ができる段で行う。段階3 の設計で決める

## 10. PR

- 作業場所: `cd /Users/tanizawashingo/salesanchor && bash scripts/new-worktree.sh release/ai-ops-stage2-bin-b --claude`（origin/main 起点）。出力はパイプに通さない。最後に「Input must be provided」という表示が出て終了コードが 1 になることがあるが、作業場所の作成とは無関係（2026-10-14・10-16 実測）。作成後に `ls -1d /Users/tanizawashingo/worktrees/salesanchor/release-ai-ops-stage2-bin-b` と `git worktree list` の両方で実在を確かめる。以後の作業はすべてその作業場所に `cd` してから行う
- commit は `PATH="/Library/Frameworks/Python.framework/Versions/3.14/bin:$PATH" git commit ...` で行う（`--no-verify` は使わない）。commit の後に `git log -1 --oneline`、push の後に `git log origin/release/ai-ops-stage2-bin-b -1 --oneline` で実在を確かめる
- PR は `scripts/gh-pr-create-safe.sh` に、先に Write ツールで作った本文ファイルを絶対パスで渡して作る（`$変数` を使わない）。作成後に `.pr-number` と `gh pr list --head release/ai-ops-stage2-bin-b --json number` の一致を確かめる
- 作成前に `gh auth status` で `shingo-cc` 名義であることを確かめる
- PR は ready で作る（`--draft` を付けない）。base は main。担当はマージしない（危険便。GO は Opus）
- 本文は PR テンプレートに沿い、`### 標準ワークフロー確認` に、recon（docs/handoff/ai-ops-247/recon.md）・設計（docs/handoff/ai-ops-247/stage2-design.md）・このカード・ADR-1012 を書く。`触るファイル:` と `削除するファイル:` は 1 行・カンマ区切り・バッククォートなし・注記なし（良い例: 触るファイル: backend/app/routers/ops.py, backend/app/main.py, nginx/nginx.conf, .github/workflows/deploy.yml, docker-compose.yml, backend/tests/test_ops_router.py, backend/tests/ops_control_lock.py, backend/tests/test_ops_incident_tables_rls.py, docs/handoff/ai-ops-247/card-stage2-bin-b.md ／ 削除するファイル: に書くのは、差分に削除の行があるファイルだけ（§13 の「（未記入）」を書き換えるこのカードと、§4-10 で字下げが変わる test_ops_incident_tables_rls.py））
- `### GO記録` は担当が書かない（Opus が書く）。本文に「GO 待ち（危険便・ADR-136）」と 1 行書く
- 本文に IP・鍵の値・鍵のパスを書かない。実在しないパスをバッククォートで書かない
- 作成前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し exit 0 を確かめる（2 分以上かかるので timeout を長めにする）

## 11. 報告

- 完了報告の本文に: 冒頭の受領文／§5-1〜5-5 の出力／PR の URL／生出力のパス（/tmp/CC報告ファイル/ai-ops-stage2-bin-b/impl/）／判断を要した点（事実のみ）
- 停止したときは: 停止した手順番号／最後に実行したコマンド／停止した理由の原文
- 1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか

## 12. 委任の定型

- sleep しない（待ちは Opus が行う）
- ファイルの作成と編集は Write/Edit ツールで行う（ヒアドキュメントで書かない）
- PR を作る前に `scripts/dev/validate-pr-body.sh` で exit 0 を確かめる
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える

## 13. 報告欄（担当が追記）

- 本報告はカード 段階2 便B の実行結果である
- §5-1 ruff: 0 件（All checks passed!）。生出力 /tmp/CC報告ファイル/ai-ops-stage2-bin-b/impl/ruff.txt
- §5-2 試験名: 12 本、カード §4-10 の表の名前・順と一致。生出力 impl/test_names.txt
- §5-3 pytest: 手元では 19 skipped（RLS_* 環境変数なし）。実 PostgreSQL での試験は CI の pytest-run-internal に任せる。生出力 impl/pytest.txt（カバレッジ下限 60% の判定で終了コード 1）
- §5-4 差分: 8 ファイル（本カードを含めて 9）、既存行の削除 0、deploy.yml の追加 4 行。生出力 impl/diff_stat.txt
- §5-5 `_ANNOTATABLE_COLUMNS`: 定義 backend/app/routers/ops.py:43、使用 :358。生出力 impl/annotatable.txt
- 判断を要した点: 手元の一時 PostgreSQL は、フックに止められたため作らず、Opus の指示で skip の扱いとした

END OF CARD
