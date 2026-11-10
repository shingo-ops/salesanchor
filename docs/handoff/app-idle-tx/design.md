<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ。このPRに含まれない新しいファイルにはバッククォートを付けない。 -->
# 設計 — 受信箱の通知の流れが DB の取引を開いたままにし、本番反映の点検を止める件

**親**: `docs/handoff/deploy-db-stall/design.md`（ADR-1037 の移行前の点検）。**関連 ADR**: ADR-1016（即時反映の通り道）、ADR-1037、ADR-1070、ADR-131、ADR-1015（区分）。  
**日付**: 2026-11-10。**担当**: Planner（Opus）。  
**状態**: 設計案作成済み。設計審査済み（1回目 REVISE 4件・2回目 REVISE 3件を反映、3回目 APPROVE。低い指摘2件も §5-5 に反映。記録は docs/handoff/app-idle-tx/review-architect.md）。PO 承認済み（2026-11-11「1」、案 A を実装）。実装は便1（`docs/handoff/app-idle-tx/card-bin1.md`）で進行中。  
**PO の選択**: 2026-11-10「1」（理由を調べ、直す設計案を作る。実装の前に報告）。  
**根拠**: `docs/handoff/app-idle-tx/recon.md`（以下 recon）。

---

## 1. 目的（PO の言葉に沿って）
- 本番反映の前の点検（開いたままの取引を数えて 0 本が 3 回続くのを待つ）が、アプリを開いている利用者がいるだけで待たされたり止まったりしない。
- データの置き場と配線は今の1か所のまま（新しい置き場・二つ目の認証を作らない）。

## 2. KGI と KPI（PO が ○× で判定できる形）

KGI: アプリを開いている利用者がいても、本番反映の前の点検が、アプリ本体（salesanchor_backend）の握り手で待たされない。

| 番号 | 基準 | 検証方法 | 基準値（今） |
|---|---|---|---|
| K1 | アプリのダッシュボードを 1 枚開いたまま 5 分数えて、salesanchor_backend の「5 秒より長く開いた取引」が 0 本 | 本番反映後、recon B-C1 と同じ読み取り専用の数え方（5 秒おき・5 分）を同じ手順で流す。生出力をファイルに残す | 常に 1 本（idle-tx-sample-20261110T122507Z.txt） |
| K2 | 「流し続ける口は DB の取引を依存に持たない」見張りの試験が緑。直す前の main に当てると conversations/stream の名前を出して赤 | CI の backend の試験。実装役が直す前の状態で赤になる出力を PR に貼る | 見張り無し |
| K3 | 受信箱の流れの認証の結果が変わらない。トークン無し→401 か 403、閲覧者のトークン→401、messaging.view が無い→403、ある→200 で ": ping" が届く | 新しい試験（§5-4）と `backend/tests/test_viewer_isolation.py`、既存の試験全部が CI で緑 | 今の動き（試験は無い） |
| K4 | 最初のかたまりを送る時点で、受信箱の流れの DB セッションが閉じている | 新しい試験（§5-4、`backend/tests/test_realtime_events.py` :52-73 と同じ形） | 閉じていない（recon B-C2） |
| K5 | 次の移行ありの本番反映 3 回で、点検の段の記録に salesanchor_backend の握り手が 1 行も出ない | deploy の記録の点検の段を読んで数える | 11/10 1 回目で 2 本（deploy-5364-failed.log） |
| K6 | 即時反映の通り道（events/stream）の動きが変わらない | `backend/tests/test_realtime_events.py` が緑 | 緑 |
| K7 | API の約束が変わらない。`frontend/api-contract/openapi.json` を触らずに `api-contract-check` が緑 | CI の `api-contract-check`。PR の変更ファイルに openapi.json が無いことを `git diff --name-only` で確かめる | 緑 |

## 3. 原因（recon の要約。全部事実）
1. 全画面の外枠が `/api/v1/conversations/stream` を開く（recon A-10）。
2. この口は認証（利用者・会社・権限）を `get_db` の yield 依存で行う。経路の依存に加えて、登録時にも `get_current_tenant` が付いている（recon A-9）。yield 依存の後始末は流れを送り終えた後なので、認証で表を読んだ取引が流れている間ずっと開いたまま（recon A-6〜A-8、B-C2）。
3. 流れは約 30 秒で自分で終わり、画面が 2 秒後につなぎ直す。だから 1 枚のタブで約 32 秒ごとに約 25 秒の握り手が 1 本できる（recon B-C3）。
4. 点検は 5 秒より長い取引を数えるので、タブが 2 枚以上あると 0 本が 3 回続きにくい（recon A-3・A-5）。

即時反映の通り道 `/api/v1/events/stream` は同じ問題を既に避けている。認証を短いセッションで済ませて閉じてから流す（`backend/app/routers/realtime_events.py` :53-71）。今回はこの形に受信箱の流れを揃える。

## 4. 方法の比較

| 案 | 中身 | 効き目 | 影響の広さ | 判定 |
|---|---|---|---|---|
| A（採用） | 受信箱の流れだけ、events/stream と同じ形にする（短いセッションで認証して閉じてから流す） | 握り手の元を消す | 経路 1 本・試験。nginx・画面・DB は触らない | 採用 |
| B | ADR-1016 段階3（受信箱・リードの流れを events/stream へ移し、古い2本を消す） | 同じ。古い2本の 30 秒切れ・422 も消える | nginx・画面・backend。nginx を含むので危険 PR（GO が要る） | 正しい行き先だが大きい。A の後に別の仕事で行う |
| C | 認証の依存の中で commit して取引を閉じる | 全部の経路で取引が短くなる | 認証の正本（`backend/app/auth/`）と全経路。ADR-1015 で A 区分 | 広すぎる。不採用 |
| D | `Depends(scope="function")` で受信箱の流れだけ後始末を早める | 効く見込み | 認証の関数が共有する `get_db` の依存の扱いが入り組む。動きを確かめていない | 確かめていない動きに頼るので不採用 |
| E | アプリの DB 利用者（salesanchor_app）に取引を開いたままの上限を付ける | 握り手を切る | アプリの全接続。正しい長い取引も切る | 不採用 |
| F | 点検で salesanchor_backend を数えない | 点検は通る | 本当に移行を止める握り手を見逃す | 隠すだけ。不採用 |

## 5. 変更前 → 変更後（便1。触るのはこの表のファイルだけ）

| ファイル | 変更 |
|---|---|
| backend/app/realtime/stream_db.py（新規） | 短いセッションの入口 `short_db_scope()` を1か所に置く |
| `backend/app/routers/realtime_events.py` | 自分の `_db_scope`（:53-55）をやめ、上の入口を使う。動きは同じ |
| `backend/tests/test_realtime_events.py` | 差し替え先を `ev.get_db` から入口のモジュールの `get_db` へ（:34 の1行） |
| `backend/app/routers/meta_inbox.py` | 受信箱の流れ（:1045-1101）を、登録時の依存を持たない別の経路の束へ移し、短いセッションで認証する |
| `backend/app/main.py` | 上の束を、受信箱の経路（:556-559）の直前に、依存なしで登録する |
| backend/tests/test_sse_no_db_hold.py（新規） | 見張り（§5-5）と受信箱の流れの試験（§5-4） |
| `docs/adr/ADR-1016-realtime-change-signal-standard.md` | 追記（§5-6）。`node scripts/generate-adr-index.js` で `docs/adr/README.md` を作り直す |

触らないもの: `backend/app/auth/`、`backend/app/database.py`、`/api/v1/leads/stream`（§7）、nginx、画面（`frontend/src/`）、migrations、deploy。

### 5-1. 入口 backend/app/realtime/stream_db.py（新規）
```python
"""流し続ける口（SSE）の認証用の短い DB セッション（ADR-1016 追記）。

yield 依存の get_db は流れを送り終えるまで閉じないので、流し続ける口では依存にしない。
認証はこの入口で開いたセッションで済ませ、流し始める前に閉じる。後始末は get_db と同じ。
"""
from contextlib import asynccontextmanager

from app.database import get_db


def short_db_scope():
    return asynccontextmanager(get_db)()
```

### 5-2. `backend/app/routers/realtime_events.py`
- 変更前: :8 `from contextlib import asynccontextmanager`、:15 `from app.database import get_db`、:53-55 `def _db_scope(): ...`、:69 `async with _db_scope() as db:`
- 変更後: :8 と :15 を消し、`from app.realtime import stream_db` を足す。:53-55 を消す。:69 を `async with stream_db.short_db_scope() as db:`。
- 試験の差し替え: `backend/tests/test_realtime_events.py` :34 `monkeypatch.setattr(ev, "get_db", fake_get_db)` → `monkeypatch.setattr(stream_db, "get_db", fake_get_db)`（`from app.realtime import stream_db` を足す）。ほかの行は変えない。

### 5-3. `backend/app/routers/meta_inbox.py` と `backend/app/main.py`
- 読み込み（:28-33）に `security` を足す。`from fastapi.security import HTTPAuthorizationCredentials` と `from app.realtime import stream_db` を足す。
- :46 `router = APIRouter()` の次に `stream_router = APIRouter()` を足す（登録時の依存を付けないための束。コメントで理由を1行）。
- 権限の判定は今と同じ関数を使う。経路の外で一度だけ作る: `_MESSAGING_VIEW = require_permission("messaging.view")`（`REGISTERED_PERMISSION_KEYS` への登録も今と同じ）。
- 変更前（:1045-1052）:
```python
@router.get(
    "/conversations/stream",
    dependencies=[Depends(require_permission("messaging.view"))],
)
async def stream_inbox_updates(
    request: Request,
    tenant_id: int = Depends(get_current_tenant),
) -> StreamingResponse:
```
- 変更後:
```python
@stream_router.get("/conversations/stream")
async def stream_inbox_updates(
    request: Request,
    cred: HTTPAuthorizationCredentials = Depends(security),
) -> StreamingResponse:
    ...（docstring は 1 文字も変えない。理由は下の # の行に書く）
    # DB 依存（Depends）は持たない。yield 依存は流れを送り終えるまで閉じないため（ADR-1016 追記）
    async with stream_db.short_db_scope() as db:
        user = await get_current_user(request, cred, db)
        tenant_id = await get_current_tenant(request, user, db)
        await _MESSAGING_VIEW(current_user=user, tenant_id=tenant_id, db=db)
```
  その後（接続数の確かめ・event_generator・StreamingResponse）は 1 文字も変えない。
- `backend/app/main.py` :556 の直前に足す:
```python
# 受信箱の流れ（SSE）。認証は経路の中の短いセッションで行うので、登録時の依存を付けない（ADR-1016 追記）
app.include_router(meta_inbox.stream_router, prefix="/api/v1", tags=["meta-inbox"])
```
- API の約束（`frontend/api-contract/openapi.json` :46877-46902）は変えない。docstring・関数名・戻り型・tags `meta-inbox`・`security` による HTTPBearer は今と同じなので、書き出しは同じになる（`backend/tools/export_openapi.py` :17 は sort_keys で書くので、登録の順も差分にならない）。openapi.json は触らない。`api-contract-check` が緑であることを K7 で確かめる。
- 道の重なり: `/api/v1/conversations/...` を持つ経路は meta_inbox の中だけ（`git grep` で確かめた。`/conversations` :866 と `/conversations/stream` :1046 の2本）。受信箱の経路の直前に置くので、今より前の経路との順は変わらない。

### 5-4. 受信箱の流れの試験（backend/tests/test_sse_no_db_hold.py）
`backend/tests/test_realtime_events.py` :19-82 と同じ作り。`stream_db.get_db`・`meta_inbox.get_current_user`・`meta_inbox.get_current_tenant`・`meta_inbox._MESSAGING_VIEW` を差し替え、`increment_connection`・`subscribe_inbox` も差し替える。
- T1: 最初のかたまりを受け取った時点で、記録が `["open", "auth", "tenant", "perm", "closed"]`、かたまりは ": ping" で始まる（K4）。
- T2: トークン無しは 401 か 403 で、DB を開かない（K3）。
- T3: 権限の判定が 403 を出すと 403 で、DB は閉じている（K3）。
- T4: アプリの経路表で `GET /api/v1/conversations/stream` が 1 本だけ。

### 5-5. 見張り（同じファイル）
- 集め方（3つの和集合）: `app.main.app` の全経路（`APIRoute`）のうち、
  (1) `typing.get_type_hints(route.endpoint).get("return")` が `StreamingResponse` かその子のもの（meta_inbox.py と leads.py は `from __future__ import annotations` なので、`__annotations__` の文字列を直接比べない）。
  (2) `inspect.getsource(route.endpoint)` に `text/event-stream` を含むもの（戻り型を書かない流し口を拾う補助）。
  (3) `route.response_class`（`DefaultPlaceholder` なら `.value`）が `StreamingResponse` の子のもの、または `inspect.isasyncgenfunction(route.endpoint)` か `inspect.isgeneratorfunction(route.endpoint)` が真のもの（FastAPI 0.136.3 の `fastapi.sse.EventSourceResponse` で書いた流し口と、同期の generator で書いた流し口を拾う。設計審査2回目の指摘1・3回目の指摘2。今の 712 経路では当たり 0 件）。
- 集めた経路の (メソッド, 道) の集合が、次の 3 本と完全に一致することを確かめる: `GET /api/v1/events/stream`・`GET /api/v1/conversations/stream`・`GET /api/v1/leads/stream`。増えたら赤（新しい流し口はこの表に足して審査を通す）。減っても赤（集め方の空振りを防ぐ）。
- 集めた各経路の依存の木（登録時の依存を含む `route.dependant` を `dependencies` でたどり、各 `call` を見る）に、yield 依存が無いことを確かめる。判定は FastAPI 自身の判定 `sub.is_gen_callable or sub.is_async_gen_callable`（`sub` は依存の木の各 `Dependant`）が真なら赤。`functools.partial(get_db)` のような包み方も拾う（設計審査3回目の指摘1。手で `call.__call__` を見る判定は partial を見逃した。今の全経路では両方の判定の結果は同じ）。`{app.database.get_db, app.database.get_admin_db}`（`backend/app/database.py` :112 の get_admin_db も同じ yield 依存）はこれに含まれ、get_db を包んだ別の yield 依存も拾う（設計審査2回目の指摘3）。赤の出力には依存の名前を出す。
- 例外の表（理由付き）: `("GET", "/api/v1/leads/stream")` だけ。理由「`/leads/{lead_id}` が先に登録されていて流れに入らない（recon B の別の不具合）。直すときに例外を消す」。
- 例外の表の経路がまだ在り、まだ get_db を持つことも確かめる（直したのに例外が残ったら赤）。

### 5-6. ADR-1016 への追記（本文の決定は書き換えない）
「流し続ける口（SSE）は、流している間 DB の接続と取引を持たない。認証・会社・権限は backend/app/realtime/stream_db.py の短いセッションで済ませ、流し始める前に閉じる。見張りは backend/tests/test_sse_no_db_hold.py。理由: yield 依存の後始末は応答を送り終えた後に走るので、流れ1本ごとに取引が開いたままになり、本番反映の前の点検（ADR-1037）を止めた（docs/handoff/app-idle-tx/recon.md）。」

## 6. 弊害と対処
| 弊害 | 対処 |
|---|---|
| 権限の判定を経路の依存から関数の呼び出しに変えるので、経路の情報から鍵を読む試験が鍵を見つけられない | 経路の鍵を読む試験は特定の経路だけを見る（`backend/tests/test_permission_catalog.py` :115-165 など。受信箱の流れは入っていない）。鍵の登録（`REGISTERED_PERMISSION_KEYS`）は同じ関数を通るので変わらない |
| 登録時の `get_current_tenant` が外れる | 同じ関数を経路の中で呼ぶ（§5-3）。会社の判定は1か所のまま |
| 閲覧者のトークンが通るようになる恐れ | `get_current_user` は同じ関数。`backend/tests/test_viewer_isolation.py` が全経路を叩いて 401 を確かめる（K3） |
| テナント文脈が後の要求に残る恐れ | 短いセッションも `get_db` の finally（`backend/app/database.py` :70-85 の `clear_tenant_context`）を通る。events/stream と同じ |
| events/stream を触る | 入口を差し替えるだけ。`backend/tests/test_realtime_events.py` の4本が守る（K6） |

戻し方: 実装 PR のマージを `git revert -m 1` で戻して本番反映する。DB・nginx・画面・設定の変更は無い。

## 7. 対象外（別の仕事として記録する）
- `/api/v1/leads/stream` が本番で 422 になり、リード画面の即時更新が届いていない（recon B の別の不具合）。直すと流れに入るので、同時に今回の形にする必要がある。ADR-1016 段階3（案 B）で消えるので、段階3 と一緒に扱うかを PO が決める。
- 受信箱の流れが 30 秒で自分で終わる（recon B-C3）。つなぎ直しの約 2 秒に来た合図が届かない。これも段階3で消える。今回直すと、仕様の動き（未読の数の更新）が変わるので分ける。
- deploy-db-stall の未確認 U1（11/10 1 回目の握り手の正体）は、K5 で同じ形が消えたかで確かめる。

## 8. 区分（ADR-1015）
新しいファイルを足し、ADR を追記するので **A**（PO 判断）。B-1 の「期待値の ADR の行」に当たる行は今の ADR に無い（recon A-12）。この設計の §5-6 でその行を足す。

## 9. 計画
1. この設計を審査（クラウドの architect）→ PO に報告し、実装の承認をもらう。
2. 承認後、実装カードを作り、クラウドの Sonnet に実装を頼む（§5 の表のファイルだけ）。
3. CI 緑・審査役（opus）APPROVE → マージ → 本番反映。危険なパス（migrations・deploy・本番 scripts・nginx）を含まないので GO の手順は不要。
4. 本番反映の後に K1 を測る（読み取り専用の数え方。PO の同意票で流す）。K5 は次の移行ありの本番反映 3 回で数える。

## 10. 外部・過去事例の参照と我々への応用
- FastAPI 公式文書（Context7 /websites/fastapi_tiangolo、2026-11-10 に参照）: yield 依存の既定の範囲は要求全体で、後始末は応答を送り終えた後。`scope="function"` は 0.121.0 から。今回の原因（流れの間ずっと後始末されない）はこの文書どおりの動き。
- 数値付きの他社事例は使わない。理由: 原因と効き目は自分の本番の実測（recon B）で示せ、K1 で同じ物差しで測れるため。

## 11. 維持の仕組み
- 守り手: `backend/tests/test_sse_no_db_hold.py`（新しい流し続ける口が yield 依存を持った時点で CI が赤になる）。
- 決まりの置き場: ADR-1016 の追記（§5-6）。
- 本番の見張り: 本番反映の前の点検（`scripts/deploy-db-precheck.sh`、ADR-1037）が握り手の名前を記録し続ける。K5 で数える。
