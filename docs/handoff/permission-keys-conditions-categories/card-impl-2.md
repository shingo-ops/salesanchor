# card: 便2 コードが求めるのに権限の一覧に無いキーを見張る（クラウドの Sonnet 向け）

## カードチェック（design-partner.md §5.5）
| # | 項目 | 結果 |
|---|---|---|
| 0 | 冒頭に ○× | ○ |
| 1 | 記号を `` ` `` で囲む | ○ |
| 2 | PR | ○ 担当は PR を作らない。Opus が差分を読んでから作る |
| 3 | 報告先 | ○ 生出力入りの報告ファイル（§5） |
| 4 | 目的は 1 つ | ○ 権限の一覧に無いキーを数えて知らせる |
| 5 | 土台のブランチ | ○ `origin/main`（§0） |
| 6 | 形は例で示す | ○ §1 に変更後のコード |
| 7 | 合格基準に出力 | ○ §3 |
| 8 | 対象の名前 | ○ 触ってよいファイル 8 つ（§1 の 6・§2 の 1・§5 の報告 1） |
| 9 | 出力の上限 | ○ tail -80 |
| 10 | 受付と終わりの合図 | ○ 最後の行は `DONE` / `BLOCKED: <理由>` / `NEEDS_DECISION: <問い>` |
| 11 | 想定値は実測 | ○ §0 の想定は 2026-11-04 origin/main b3156b3ba の実物 |
| 12 | 止まる条件 2 段 | ○ §4 |
| 13 | sleep なし・Write/Edit・見張りで止まったら言い換えない | ○ |

- 設計: [design.md](design.md) §5（設計審査 3 回目 APPROVE・[review-opus.md](review-opus.md)）
- PO の実装承認: 2026-11-04 チャット「1」（権限の抜けを見張る仕組みを作る作業に進む）
- 作業ブランチ: `release/permission-keys-watch-code`（`origin/main` から新しく作る）。このカードのブランチには書かない。
- 本番の実測（2026-11-04 12:40 JST・Opus）: コードの `require_permission(...)` に書かれたキー 96 種のうち、権限の一覧（130 行）に無いのは `companies.view`・`customers.edit`・`leads.edit` の 3 つだけ。よって反映後の本番の値は 0 になる見込み。

## §0 着手前の点検（違えば NEEDS_DECISION で止まる）
次の行が、そのとおりの文字列であること。`grep -n` の結果を報告に貼る。
| ファイル | 想定 |
|---|---|
| `backend/app/auth/dependencies.py` | `def require_permission(*permission_keys: str):` があり、その中に `required: set[str] = set(permission_keys)` と `checker.required_permission_keys = frozenset(required)` がある |
| `backend/app/metrics.py` | `async def _update_viewer_inventory_gauges() -> None:` と `async def metrics() -> Response:` がある。`metrics()` の最後が `return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)` |
| `backend/app/database.py` | `AsyncSessionLocal = sessionmaker(` がある |
| `monitoring/prometheus/alert_rules.yml` | `- name: application_alerts` の群がある |
| `monitoring/prometheus/tests/alert_rules_test.yml` | `rule_files:` の下に `- ../alert_rules.yml` |
| `docs/runbooks/alerts.md` | `## OpsMailPollStale` の節がある |
| `.github/workflows/monitoring-check.yml` | `promtool` の `check rules` と `test rules` を流す段がある（読むだけ。変えない） |

## §1 コードの変更（6 ファイル）
(1) `backend/app/auth/dependencies.py`
- モジュールの上の方（`require_permission` より前）に置く:
```python
# コードが require_permission で求めたキーの集合。経路の読み込み（アプリの起動）でそろう。
# 権限の一覧（public.permissions）との差を見張るために使う（design.md §5）。
REGISTERED_PERMISSION_KEYS: set[str] = set()
```
- `require_permission` の中、`if not required: raise ValueError(...)` の直後に 1 行足す。判定の中身は変えない。
```python
    REGISTERED_PERMISSION_KEYS.update(required)
```

(2) `backend/app/auth/permission_catalog.py`（新規）
```python
"""コードが求めるのに権限の一覧（public.permissions）に無いキーを数える（design.md §5-2）。

一覧の正は DB。ここに一覧の写しは置かない。
"""
from __future__ import annotations

from sqlalchemy import text

from app.auth.dependencies import REGISTERED_PERMISSION_KEYS

# 既知の欠け。キー: 残す理由。PO が扱いを決めたら、その PR でここから消し、
# backend/tests/test_permission_catalog.py の上限の数字を下げる（design.md §5-3）。
KNOWN_MISSING: dict[str, str] = {
    "companies.view": "PO 判断待ち: duplicates.py の経路。一覧に足すか、別のキーへ付け替えるか",
    "customers.edit": "PO 判断待ち: contacts.py の経路。一覧に足すか、別のキーへ付け替えるか",
    "leads.edit": "PO 判断待ち: discord_channel_invite.py・discord_role_resync.py の経路。一覧に足すか、別のキーへ付け替えるか",
}


async def count_missing_permission_keys(db) -> list[str]:
    """コードが求めるキーのうち、一覧にも KNOWN_MISSING にも無いものを名前順で返す。"""
    result = await db.execute(text("SELECT key FROM public.permissions"))
    in_catalog = {row[0] for row in result.fetchall()}
    return sorted(REGISTERED_PERMISSION_KEYS - in_catalog - set(KNOWN_MISSING))
```

(3) `backend/app/metrics.py`
- Gauge を足し、作った直後に -1 を入れる:
```python
PERMISSION_KEYS_MISSING = Gauge(
    "salesanchor_permission_keys_missing",
    "コードが求めるのに権限の一覧に無いキーの数（-1 はまだ数えていない・数えられなかった）",
)
PERMISSION_KEYS_MISSING.set(-1)

_PERMISSION_CHECK_INTERVAL_SEC = 300.0
_PERMISSION_CHECK_TIMEOUT_SEC = 2.0
_permission_check_last_at: float | None = None
```
- 数える関数を足す。DB を読むのは最大 300 秒に 1 回。失敗・時間切れでも次は 300 秒後:
```python
async def _update_permission_keys_gauge() -> None:
    global _permission_check_last_at
    now = time.monotonic()
    if _permission_check_last_at is not None and now - _permission_check_last_at < _PERMISSION_CHECK_INTERVAL_SEC:
        return
    _permission_check_last_at = now
    from app.auth.permission_catalog import count_missing_permission_keys  # noqa: PLC0415
    from app.database import AsyncSessionLocal  # noqa: PLC0415

    async def _count() -> list[str]:
        async with AsyncSessionLocal() as session:
            return await count_missing_permission_keys(session)

    try:
        missing = await asyncio.wait_for(_count(), _PERMISSION_CHECK_TIMEOUT_SEC)
    except Exception:
        logger.warning("権限キーの見張り: 数えられなかった", exc_info=True)
        PERMISSION_KEYS_MISSING.set(-1)
        return
    PERMISSION_KEYS_MISSING.set(len(missing))
    if missing:
        logger.warning("権限の一覧に無いキー: %s", ", ".join(missing))
```
- `logger` が無ければ、ファイルの上で `import logging` と `logger = logging.getLogger(__name__)` を足す。
- `metrics()` の中、`_update_ops_mail_gauges` の try の後・`return` の前に足す:
```python
        await _update_permission_keys_gauge()
```
  （中で例外を受けて -1 にしているので、外の try は要らない）

(4) `monitoring/prometheus/alert_rules.yml`
- `application_alerts` の群の最後に 2 本を足す。書き方（labels・annotations の並び・runbook_url の形）は同じ群の既存の規則に合わせる。
```yaml
      - alert: PermissionKeyMissing
        expr: salesanchor_permission_keys_missing{job="backend"} > 0
        for: 10m
        labels:
          severity: warning
          tier: ticket
        annotations:
          summary: "コードが求める権限が、権限の一覧にありません"
          description: "一覧に無いキーが {{ $value }} 個あります。その権限が要る画面は、所有者でも開けません。"
          runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#permissionkeymissing"

      - alert: PermissionKeyCheckFailed
        expr: salesanchor_permission_keys_missing{job="backend"} == -1
        for: 30m
        labels:
          severity: warning
          tier: ticket
        annotations:
          summary: "権限の一覧との突き合わせが 30 分できていません"
          description: "権限の抜けの見張りが止まっています。抜けがあっても知らせが出ません。"
          runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#permissionkeycheckfailed"
```

(5) `monitoring/prometheus/tests/alert_rules_test.yml`
- 試験を 2 つ足す（書き方は既存の試験に合わせる。`interval: 1m`）。
  - `PermissionKeyMissing`: 系列 `salesanchor_permission_keys_missing{job="backend", instance="b1"}` の値 `1+0x30` → `eval_time: 11m` で発火（labels と annotations を exp に書く。description の `{{ $value }}` は `1`）。`eval_time: 5m` では `exp_alerts: []`。もう 1 つ値 `0+0x30` の系列だけの試験で `eval_time: 20m` に `exp_alerts: []`。
  - `PermissionKeyCheckFailed`: 値 `-1+0x40` → `eval_time: 31m` で発火。`eval_time: 20m` では `exp_alerts: []`。
- ファイルの頭の「全 N 本」の数が規則の数を表していれば、新しい数（2 本増）に直す。

(6) `docs/runbooks/alerts.md`
- 最後に 2 節を足す。書き方は `## OpsMailPollStale` の節に合わせる（札・何が起きているか・最初に見るもの・直し方・止め方）。
  - `## PermissionKeyMissing`: 札 ticket。何が起きているか＝コードが require_permission で求めるキーが、権限の一覧に無い。その経路は所有者でも 403 になる。最初に見るもの＝backend のログの「権限の一覧に無いキー:」の行。直し方＝キーが正しければ、`docs/handoff/permission-keys-conditions-categories/data-change-1/README.md` と同じ形の 1 回だけのデータ変更で一覧に足す（PO の使い捨て許可が要る）。キーの書き間違いなら、コードを直す。止め方＝`amtool silence add alertname=PermissionKeyMissing --duration=PERIOD --comment=REASON`。
  - `## PermissionKeyCheckFailed`: 札 ticket。何が起きているか＝見張りが DB を読めない（2 秒の時間切れか例外）状態が 30 分続いた。最初に見るもの＝backend のログの「権限キーの見張り: 数えられなかった」の行と、DB の具合（BackendHighErrorRate など）。直し方＝DB が戻れば次の 300 秒の数え直しで 0 以上に戻る。止め方＝同じ形。

触らない: `require_permission` の判定・`load_user_permissions`・経路のファイル・`frontend/`・`migrations/`・`alertmanager.yml`・`.github/`。

## §2 試験（新しいファイル 1 つ）
`backend/tests/test_permission_catalog.py`（DB を使わない）
- 注意（便1 の教訓・impl-report-2.md）: ファイルの頭で `from app.main import app` をしない。試験の中で読み込む:
```python
def _load_routes() -> None:
    from app.main import app  # noqa: F401  経路を読み込んで REGISTERED_PERMISSION_KEYS をそろえる
```
- C1: `_load_routes()` のあと、`KNOWN_MISSING` の各キーが `REGISTERED_PERMISSION_KEYS` に入っている（使われなくなったキーを消させる）。
- C2: `len(KNOWN_MISSING) <= 3`。
- C3: `_load_routes()` のあと、`REGISTERED_PERMISSION_KEYS` に `conditions.view` と `product_categories.view` が入っている（集め方が働いている）。
- C4: `count_missing_permission_keys` に、`execute` が決まった行を返す偽の session を渡す。`REGISTERED_PERMISSION_KEYS` を `monkeypatch` で `{"a.view","b.view","companies.view"}` に差し替え、一覧の行を `["a.view"]` にすると、結果は `["b.view"]`（既知の欠けは数えない・名前順）。差し替えは `monkeypatch.setattr` で `app.auth.permission_catalog.REGISTERED_PERMISSION_KEYS` を替える。
- C5（`metrics._update_permission_keys_gauge`）: `app.auth.permission_catalog.count_missing_permission_keys` と `app.database.AsyncSessionLocal` を差し替え、`metrics._permission_check_last_at` を `None` に戻してから呼ぶ。
  - 例外を投げる → Gauge の値が -1（`PERMISSION_KEYS_MISSING._value.get()` で読む）。
  - `[]` を返す → 0。
  - `["x.view"]` を返す → 1。
  - 続けてもう 1 回呼ぶ（300 秒たっていない）→ 数える関数が呼ばれない（呼ばれた回数で確かめる）。
- asyncio の試験の書き方は、既存の backend/tests の async 試験に合わせる。

## §3 確かめ（出力はファイルへ。tail -80 で読む）
Python は 3.12 の venv を使う（便1 と同じ。`python3.12 -m venv /tmp/venv312` → `requirements.txt` と試験の道具を入れる）。
```
cd backend && /tmp/venv312/bin/python -m pytest tests/test_permission_catalog.py tests/test_conditions_permission_keys.py -q -p no:cacheprovider > /tmp/pytest.txt 2>&1; tail -80 /tmp/pytest.txt
cd backend && /tmp/venv312/bin/python -m pytest tests/test_conditions_permission_keys.py tests/test_permission_catalog.py -q -p no:cacheprovider > /tmp/pytest2.txt 2>&1; tail -80 /tmp/pytest2.txt
/tmp/venv312/bin/python monitoring/scripts/check_alert_rules.py > /tmp/rules.txt 2>&1; tail -80 /tmp/rules.txt
bash scripts/dev/check-before-submit.sh > /tmp/cbs.txt 2>&1; tail -80 /tmp/cbs.txt
```
- 合格: 2 つの順のどちらでも、新しい試験が全部 passed・失敗 0（末尾の coverage の閾値の行は、一部だけ流したためなので失敗に数えない）。check_alert_rules.py が誤り 0。check-before-submit が成功で終わる。
- promtool はクラウドに無ければ流さなくてよい。GitHub の「監視スタック整合性チェック」が流す。流せたら `check rules` と `test rules` の tail も貼る。

## §4 止まる条件
- 1 段目（NEEDS_DECISION で止まる）: §0 の想定と違う。§1・§2 の触ってよいファイル以外を変えないと通らない。`REGISTERED_PERMISSION_KEYS` に経路のキーがそろわない（読み込みの順番の問題など）。
- 2 段目（BLOCKED で止まる）: 見張り（hook）に止められた（言い換えない）。push が断られた。§3 が 2 回直しても通らない（原因の生出力を報告に貼る）。

## §5 報告
- `docs/handoff/permission-keys-conditions-categories/impl-report-3.md` を作り、同じブランチにコミットして push する。
- 中身: §0 の grep の生出力、変えたファイルの一覧（`git diff --stat origin/main`）、§3 の tail の生出力、最後の HEAD の sha、最後の行に `DONE` / `BLOCKED: <理由>` / `NEEDS_DECISION: <問い>`。

## §6 マージのあと（Opus が行う。担当はしない）
1. backend の反映（deploy.yml）の成功を Actions の記録で確かめる。
2. prod2 の監視の置き場（`/opt/salesanchor-monitoring/monitoring/prometheus/`）へ、main の `alert_rules.yml` を置いて `POST /-/reload` する。手順は docs/handoff/ai-ops-247/card-stage1-bin7.md §8（控えを取る→置く→読み直す→drift の確認）に合わせ、PO の `!` で流す台本として用意する。
3. prod2 の Prometheus で `salesanchor_permission_keys_missing{job="backend"}` が 0 になったことを確かめる（反映から 300 秒以内に -1 から 0 へ変わる見込み）。
