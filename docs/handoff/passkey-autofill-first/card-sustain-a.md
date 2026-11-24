---
mode: handoff
---
# 実装カード 続ける仕組み A: パスキーの週報の係

親: [sustain-design.md](./sustain-design.md) §5-1・§8（受入条件）

- 状態: カード作成済み（2026-11-24 Opus）。PO 実装承認: 2026-11-24 チャット「1,…PRマージ、デプロイまで完走させてくれ」（5-1・5-2・5-4 の3つ）。マージと本番反映の判断は Opus が行う（担当はしない）。
- 担当: クラウドの Sonnet（実装）。Opus は審査・マージ判断。
- 区分: B（backend の係を1つ足すだけ。migrations・scripts・deploy.yml・frontend を触らない。新しい表・列・設定・secrets なし）。

## 0. カード発行前チェック

| 番号 | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲む | ○ |
| 2 | PR は Opus が作る（担当は作らない） | ○（§5 手順7 で push まで） |
| 3 | 報告の宛先（最後の返事に生出力の全文） | ○（§6） |
| 4 | 1便1目的（週報の係だけ） | ○ |
| 5 | 起点の明示（origin/main から new-worktree.sh） | ○（§5 手順1） |
| 7 | 合格基準を出力まで縛る（差分のファイル一覧） | ○（§5 手順6） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 受領と終端の合図・停止の3点 | ○（§6） |
| 11 | 行番号は目印（ずれたら前後の文で探す） | ○ |
| 13 | sleep 禁止・Write/Edit で書く・フックに止められたら言い換えない | ○（§4） |

読んだ節（docs/handoff/design-partner-card-ops/guards/）: 00-common.md（全命令を cd で始める・1手順1命令・待たない・commit と push の後に git log と ls-remote で実在を確かめる）、04-worktree.md（起点は origin/main・`new-worktree.sh` で作る・push は `git push -u origin HEAD`）、05-pr.md（`gh pr create` を直に使わない → PR は Opus が作る）。

基準: origin/main 1e37c0198。行番号はこの時点の目印。

## 1. 目的（利用者に見える変化）

- 毎週月曜 09:10（日本時間）に、管理者用 Discord に「パスキーの週報」が1通届く。全社の管理者1人ごとに、前の週（7日）と30日の、パスキーでのログイン回数・パスワードでのログイン回数・パスキーの割合・知らない機械の確認を通ったログイン回数が並ぶ。
- 数えられなかったときも「数えられなかった」の1通が届く（届かない＝止まっている、と分かる）。

## 2. 触るファイル（これ以外は触らない）

| ファイル | 何をする |
|---|---|
| `backend/app/tasks/passkey_weekly_report.py` | 新しく作る（§3-1） |
| `backend/app/celery_app.py` | `include` に1行・`beat_schedule` に1件（§3-2） |
| `backend/tests/test_passkey_weekly_report.py` | 新しく作る（§3-3） |
| `docs/handoff/passkey-autofill-first/card-sustain-a.md` | 手順2 の取り込みで入るだけ。中身は変えない |

触らないもの: migrations・scripts・`.github/`・frontend・`.env` の類・ほかの係。新しい設定・secrets を作らない。人の id を設定にもコードにも書かない（is_super_admin で選ぶ）。

## 3. 作るものの決まり（sustain-design.md §5-1 が正。食い違えば報告する）

### 3-1. passkey_weekly_report.py（下の全文をそのまま Write で作る）

前例は `backend/app/tasks/tenant_isolation_daily_check.py`（送り方・動けなかったときの1通・係の形）。設計との違い1点: 設計は「id と role」だが、`backend/app/models.py:22-38` の User に role の列の定義が無く、数える人は全員が全社の管理者なので、id だけを書く（名前・メール・IP・端末を出さない点は同じ）。

```python
"""ADR-1013 パスキーの週報: 全社の管理者のログイン成功を週1回数え、管理者用 Discord に送る。

設計: docs/handoff/passkey-autofill-first/sustain-design.md §5-1。
区切りは日本時間の暦日。月曜の回は、前の週の月曜 00:00〜日曜 24:00（7日）と、その日曜 24:00 までの30日。
数える人は public.users の is_super_admin が true の人だけ。通知には id だけを書く（名前・メール・IP・端末は書かない）。
割合はパスキー÷(パスキー＋パスワード)（docs/specs/auth-login/kgi.md の KPI の測り方）。知らない機械の確認や復旧を通ったログインは割合に入れず、件数だけ添える。
毎回送る（届かない＝止まっている）。DB は読むだけ。
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
from celery import shared_task
from sqlalchemy import text

logger = logging.getLogger(__name__)

_WEBHOOK_ENV = "ADMIN_NOTIFICATION_DISCORD_WEBHOOK"
_JST = ZoneInfo("Asia/Tokyo")

PASSKEY_PATH = "/api/v1/auth/passkey/login/verify"
LOGIN_PATH = "/api/v1/auth/login"
POLL_PATH = "/api/v1/auth/login-requests/poll"
RECOVERY_PATH = "/api/v1/auth/login-requests/recovery"
POLL_APPROVED = ("approved_admin", "approved_device")
KINDS = ("passkey", "password", "other")

ADMINS_SQL = "SELECT id FROM public.users WHERE is_super_admin ORDER BY id"
EVENTS_SQL = (
    "SELECT e.user_id, e.path, e.status_code, e.reason, e.created_at "
    "FROM public.auth_events e "
    "JOIN public.users u ON u.id = e.user_id "
    "WHERE u.is_super_admin "
    "AND e.created_at >= :start AND e.created_at < :end "
    "AND e.path IN ('/api/v1/auth/passkey/login/verify', '/api/v1/auth/login', "
    "'/api/v1/auth/login-requests/poll', '/api/v1/auth/login-requests/recovery')"
)


def windows(now: datetime) -> tuple[datetime, datetime, datetime]:
    """(30日の始め, 7日の始め, 終わり) を返す。終わり＝now 以前で最も近い日本時間の月曜 00:00。"""
    local = now.astimezone(_JST)
    day = local.replace(hour=0, minute=0, second=0, microsecond=0)
    end = day - timedelta(days=local.weekday())
    return end - timedelta(days=30), end - timedelta(days=7), end


def classify(path: str, status_code: int, reason: str | None) -> str | None:
    """1件を passkey（パスキー）／password（パスワード）／other（確認・復旧）／None（数えない）に分ける。"""
    if path == PASSKEY_PATH and status_code == 200:
        return "passkey"
    if path == LOGIN_PATH and status_code == 200:
        return "password"
    if path == POLL_PATH and reason in POLL_APPROVED:
        return "other"
    if path == RECOVERY_PATH and status_code == 200:
        return "other"
    return None


def tally(
    admin_ids: list[int], rows: list[tuple], start30: datetime, start7: datetime, end: datetime
) -> dict[int, dict[str, dict[str, int]]]:
    """人ごとに 7日・30日の回数を数える。管理者でない人の行と数えない行は捨てる。"""
    out = {uid: {"7": dict.fromkeys(KINDS, 0), "30": dict.fromkeys(KINDS, 0)} for uid in admin_ids}
    for user_id, path, status_code, reason, created_at in rows:
        kind = classify(path, status_code, reason)
        if kind is None or user_id not in out:
            continue
        if start30 <= created_at < end:
            out[user_id]["30"][kind] += 1
        if start7 <= created_at < end:
            out[user_id]["7"][kind] += 1
    return out


def ratio(c: dict[str, int]) -> str:
    denom = c["passkey"] + c["password"]
    if denom == 0:
        return "-"
    return f"{round(c['passkey'] * 100 / denom)}%"


def build_message(
    counts: dict[int, dict[str, dict[str, int]]], start30: datetime, start7: datetime, end: datetime
) -> str:
    last = end - timedelta(days=1)
    lines = [
        f"🔑 パスキーの週報（ADR-1013）: 7日 {start7:%m/%d}〜{last:%m/%d}・30日 {start30:%m/%d}〜{last:%m/%d}（日本時間）",
        "割合＝パスキー÷(パスキー＋パスワード)。確認＝知らない機械の確認や復旧を通ったログイン（割合に入れない）",
    ]
    if not counts:
        lines.append("全社の管理者: 0 人")
    for uid in sorted(counts):
        c7, c30 = counts[uid]["7"], counts[uid]["30"]
        lines.append(
            f"id {uid}: 7日 パスキー {c7['passkey']}・パスワード {c7['password']}・割合 {ratio(c7)}・確認 {c7['other']}"
            f" ／ 30日 パスキー {c30['passkey']}・パスワード {c30['password']}・割合 {ratio(c30)}・確認 {c30['other']}"
        )
    return "\n".join(lines)


async def collect(conn, start30: datetime, end: datetime) -> tuple[list[int], list[tuple]]:
    """DB から管理者の id と、30日分の記録を読む。conn は SQLAlchemy の非同期接続。"""
    admin_ids = [row[0] for row in (await conn.execute(text(ADMINS_SQL))).all()]
    rows = [tuple(row) for row in (await conn.execute(text(EVENTS_SQL), {"start": start30, "end": end})).all()]
    return admin_ids, rows


async def _post_discord(content: str) -> None:
    url = (os.getenv(_WEBHOOK_ENV) or "").strip()
    if not url:
        logger.warning("%s is not set; skip passkey weekly report", _WEBHOOK_ENV)
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(url, json={"content": content[:1800], "username": "パスキーの週報"})
        if res.status_code >= 400:
            logger.warning("passkey weekly report: discord status %s", res.status_code)
    except Exception as exc:  # noqa: BLE001
        logger.warning("passkey weekly report: discord error %s", type(exc).__name__)


async def _run_report(now: datetime | None = None) -> dict:
    from app.database import engine

    start30, start7, end = windows(now or datetime.now(UTC))
    try:
        async with engine.connect() as conn:
            admin_ids, rows = await collect(conn, start30, end)
    except Exception as exc:  # noqa: BLE001
        # 数えられなかったことも1通で知らせる（届かない週と区別するため）。中身の文は書かない。
        await _post_discord(f"🔴 パスキーの週報（ADR-1013）: 数えられなかった（{type(exc).__name__}）")
        raise
    counts = tally(admin_ids, rows, start30, start7, end)
    await _post_discord(build_message(counts, start30, start7, end))
    return {
        "counts": counts,
        "start30": start30.isoformat(),
        "start7": start7.isoformat(),
        "end": end.isoformat(),
    }


@shared_task(name="app.tasks.passkey_weekly_report.run_passkey_weekly_report")
def run_passkey_weekly_report() -> dict:
    from app.database import engine

    try:
        return asyncio.run(_run_report())
    finally:
        asyncio.run(engine.dispose())
```

### 3-2. celery_app.py（Edit で2か所）

(1) `include=[...]` の最後の行（`:50` 目印）

変更前:
```python
        "app.tasks.tenant_isolation_daily_check",  # ADR-1063 便6: 会社の分け方（RLS）の毎日点検
    ],
```
変更後:
```python
        "app.tasks.tenant_isolation_daily_check",  # ADR-1063 便6: 会社の分け方（RLS）の毎日点検
        "app.tasks.passkey_weekly_report",  # ADR-1013: パスキーの週報（sustain-design §5-1）
    ],
```

(2) `beat_schedule` の最後の項目（`:255-259` 目印）

変更前:
```python
    "tenant-isolation-daily-check": {
        "task": "app.tasks.tenant_isolation_daily_check.run_tenant_isolation_daily_check",
        "schedule": crontab(hour=9, minute=5),
    },
}
```
変更後:
```python
    "tenant-isolation-daily-check": {
        "task": "app.tasks.tenant_isolation_daily_check.run_tenant_isolation_daily_check",
        "schedule": crontab(hour=9, minute=5),
    },
    # ADR-1013: パスキーの週報を毎週月曜 09:10 JST に管理者用 Discord へ（sustain-design §5-1）
    "passkey-weekly-report": {
        "task": "app.tasks.passkey_weekly_report.run_passkey_weekly_report",
        "schedule": crontab(day_of_week=1, hour=9, minute=10),
    },
}
```

### 3-3. 試験 test_passkey_weekly_report.py（DB なし。前例 backend/tests/test_tenant_isolation_daily_check.py と backend/tests/test_bundle_bulk_monitor.py の形）

時刻は `datetime(…, tzinfo=ZoneInfo("Asia/Tokyo"))` で作る。

- W1 区切り: `windows(2026-11-30 09:10 JST)` が (10/31 00:00 JST, 11/23 00:00 JST, 11/30 00:00 JST)。月曜 00:00 ちょうどでも同じ終わり。日曜 23:59 なら終わりは 11/23 00:00。
- W2 暦日の境目: 管理者 id 3 に passkey 200 を 11/29 23:59 JST と 11/30 00:00 JST に1件ずつ入れて `tally` → 7日の passkey が 1（前者だけ）。
- W3 分母0: 記録の無い管理者の行が `割合 -` を2つ含む。
- W4 数え分け: login 200・poll approved_admin・poll approved_device・recovery 200 を1件ずつ、login 202 と poll の reason が pending のもの1件ずつ、passkey 200 を1件 → password 1・other 3・passkey 1・割合 `50%`。
- W5 人を選ぶ: 管理者の一覧に無い user_id の行は数えない。
- W6 人の情報が出ない: `build_message` の本文に `@` が無い。`ADMINS_SQL` と `EVENTS_SQL` に `email`・`full_name`・`client_ip`・`user_agent` の文字が無い。
- W7 送る: `app.database.engine` を差し替え（`engine.connect()` が `__aenter__` で conn を返す MagicMock、conn.execute は AsyncMock で2回分の戻り値を side_effect に）・`_post_discord` を AsyncMock にして `_run_report(now)` → `_post_discord` が1回・本文の1行目が `🔑 パスキーの週報`。
- W8 動けなかった: conn.execute が例外 → `_post_discord` が `🔴` で始まる文で1回呼ばれ、例外がそのまま上がる。
- W9 登録: `celery_app.conf.beat_schedule["passkey-weekly-report"]` の task が `app.tasks.passkey_weekly_report.run_passkey_weekly_report`・include にあり・`celery_app.tasks` にある・crontab の `_orig_hour == 9`・`_orig_minute == 10`・`str(_orig_day_of_week) == "1"`（test_bundle_bulk_monitor.py の最後の試験と同じ書き方）。

## 4. 守ること

- 担当は sleep しない。
- ファイルの作成と編集は Write／Edit ツールで行い、ヒアドキュメントで書かない。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。
- 止まるのは次のときだけ: 本番への接続・DB への書き込み・マージ・`main` への push・`--force`・ファイルの削除が要るとき／§3-1 の全文が ruff・試験で通らず、直し方が §3 の決まりを変えるとき。
- 行番号のずれは記録して続行し、報告に書く。
- 本番 DB・本番サーバーに接続しない。PR を作らない。マージしない。

## 5. 手順

クラウドで行う。手順1 で `new-worktree.sh` が作った作業場所のパス（以下「作業場所」）を報告に書く。`cd 取り出した場所` はクラウドがこのリポジトリを取り出した最上位の場所に、`cd 作業場所` はそのパスに読み替える。1手順1命令。executor-preflight.sh はクラウドでは流さない（gh の認証が無く必ず失敗する・2026-11-24 実測）。PR の名義は PR を作る Opus が手元で確かめる。

手順1 枝を作る（起点は origin/main）
    cd 取り出した場所 && git fetch origin
    cd 取り出した場所 && bash scripts/new-worktree.sh release/passkey-weekly-report
    cd 作業場所 && git log -1 --format=%H
    cd 作業場所 && git rev-parse origin/main
    期待する出力: 作業場所のパスと、2つの番号が同じこと。報告に書く。

手順2 このカードを取り込む（Opus が push した枝）
    cd 作業場所 && git checkout origin/release/passkey-sustain-impl -- docs/handoff/passkey-autofill-first/card-sustain-a.md
    cd 作業場所 && git diff --cached --stat origin/main
    期待する出力: card-sustain-a.md の1ファイルだけ。merge は使わない（クラウドの決まり）。

手順3 対象ファイルが基準から変わっていないか確かめる
    cd 作業場所 && git diff --stat 1e37c0198 origin/main -- backend/app/celery_app.py
    期待する出力: 空。差分があれば記録して続行し、報告に書く。

手順4 §3-1 を Write で作り、§3-2 を Edit で直し、§3-3 の試験を Write で書く。

手順5 試験と検査を流す
    cd 作業場所/backend && pip install -r requirements.txt -r requirements-dev.txt
    cd 作業場所/backend && python -m pytest tests/test_passkey_weekly_report.py tests/test_celery_beat_registered.py tests/test_tenant_isolation_daily_check.py -q
    cd 作業場所/backend && ruff check app/tasks/passkey_weekly_report.py app/celery_app.py tests/test_passkey_weekly_report.py
    期待する出力: 失敗 0（実 PostgreSQL の無い試験の skip はよい）・ruff の違反 0。落ちたら直してからもう一度流す。3回直しても落ちたら停止して BLOCKED:（生出力の全文を付ける）。

手順6 差分のファイル一覧を確かめる
    cd 作業場所 && git add backend/app/tasks/passkey_weekly_report.py backend/app/celery_app.py backend/tests/test_passkey_weekly_report.py docs/handoff/passkey-autofill-first/card-sustain-a.md
    cd 作業場所 && git diff --cached --stat origin/main
    期待する出力: §2 の表の4ファイルだけ。deletions がある行は名前を報告に書く。`git add -A` は使わない（登録ファイルを巻き込む）。

手順7 記録して送る
    commit の文を Write で作業場所の外の一時の場所（以下 /tmp/commit-msg.txt と書く）に書く。1行目「feat(auth): weekly passkey usage report to admin Discord」、空行、最後の行「Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>」。
    cd 作業場所 && git commit -F /tmp/commit-msg.txt
    cd 作業場所 && git log -2 --oneline
    cd 作業場所 && git push -u origin HEAD
    cd 作業場所 && git ls-remote origin refs/heads/release/passkey-weekly-report
    期待する出力: git log の先頭が手順7 の commit。ls-remote の番号が `git rev-parse HEAD` と同じ。

## 6. 報告

- 受け取ったら最初に「カード 続ける仕組み A 週報 を受領」と1行書く（受領確認）。
- 報告は PR コメントにしない。最後の返事に、手順1・2・3・5・6・7 の出力の全文を書く。
- 止まったら（停止）、止まった手順・最後のコマンド・理由の原文を書き、最後の行を `BLOCKED:` か `NEEDS_DECISION:` で終える。終えたら最後の行を `DONE: ` と push した HEAD の40桁で終える。

END OF CARD
