# 実装カード schedule-gcal-clone 便15A — 予定の繰り返しの裏側（表の欄・受け口・回の広げ方・3 択・Google 同期・試験）

> この文書は何か：予定の画面を Google カレンダーと同じ使い心地にする件の便15A（裏側だけ）の作業指示書です。予定に繰り返しの決まりを 1 か所（元の行の `recurrence_rule`）だけ持たせ、一覧のときに回へ広げます。直す・消すときの 3 択（この予定／これ以降／すべて）を受け口で受けます。画面（便15B）はまだ変えないので、便15A の後も利用者に見える動きは変わりません。

- 設計: docs/handoff/schedule-gcal-clone/design.md §12（§12.4 データ・§12.5 受け口・§12.7 Google 同期・§12.8 移行・§12.10 守り手）。ADR-1075（Proposed）
- 状態: 設計は審査15 で APPROVE。成功条件 G69〜G79 と実装の開始は PO 承認済み（2026-11-12 選択「1」）。本カードは設計の範囲を変えない。設計に書いていない細部（§2 の末尾の 3 点）は本カードで決めた
- 危険便: **はい**（`migrations/` と `scripts/run_all_migrations.sh` を含む。ADR-136 の GO は Opus が委任の手順で記録する。担当は push まで）
- 担当: 実装 Sonnet（クラウド）／PR 作成・審査・GO 記録・マージ・本番反映の確認 Opus

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は Opus が作る（担当は push まで）と明記 | ○（§8） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§9） |
| 4 | 1便1目的 | ○（繰り返しの裏側だけ。画面は便15B） |
| 5 | 既存ブランチへの追記ではない（新規ブランチ） | ○（release/schedule-recurrence-backend） |
| 6 | 書式は実例で示した | ○（§4 に新しいファイルの全文と変更前後） |
| 7 | 合格基準を出力まで縛った | ○（§5） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-1 の 3 は試験の名前ごとの結果を出す） |
| 9 | 出力量に上限のないコマンドを使わない | ○（pytest は `-q` と `tail -n 60`） |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○（§9・受領確認・末尾） |
| 11 | 期待値は実物から | ○（行番号は origin/main 63709b0eb で確かめた） |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§10） |

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md（1 手順 1 コマンド・出力に上限・プレースホルダなし）・11-lint.md（L01〜L33）。照合: `gh pr create` なし（L08）・`rm ` なし（L11）・`timeout ` なし（L16）・`--admin` `--auto` なし（L18）・`gh run view` なし（L21）。

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード schedule-gcal-clone 便15A の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. 新しい移行 `migrations/20261112_160000_add_calendar_events_recurrence.sql`（欄 4 つ・CHECK 4 つ・部分 UNIQUE 1 つ。会社ごとに回す・何度流しても同じ）
2. 移行の載せ先 4 か所: `scripts/run_all_migrations.sh` の末尾・`backend/tests/rls_bootstrap.py` `_TENANT_LOOP_MIGRATIONS`・`backend/tests/test_tenant_loop_migration_guard.py` `_REVIEWED` の 2 組・`backend/tests/test_calendar_sync_tenant_reset_pg.py` `_MIGRATIONS`
3. 分類表 `migrations/20261024_100300_create_ai_cloud_views.sql` に `recurrence_rule` の 1 行（mask）と、行数 1109 → 1110（同じファイルの 3 行目と `backend/tests/ops/test_ai_cloud_views.py:486`）
4. `backend/requirements.txt` に `python-dateutil==2.9.0.post0`
5. 新しいファイル `backend/app/services/calendar_recurrence.py`（§4-2 の全文をそのまま）
6. `backend/app/services/google_calendar.py` に `get_instance`
7. `backend/app/services/calendar_service.py`: 予定 1 行の読み方・判定 `check_recurrence_request`・作る道の繰り返し・一覧の広げ方・直す 3 択・消す 3 択・取り込みの飛ばし・Google の本文
8. `backend/app/routers/calendar.py`: 作る・直す・消すの受け口に繰り返しの値と 422
9. 試験: 新しい `backend/tests/test_calendar_recurrence.py`、`backend/tests/test_calendar_service.py`・`backend/tests/test_calendar_owner_api.py`・`backend/tests/test_calendar_sync_tenant_reset_pg.py` への追加

入れない:
- `frontend/` の全部（便15B）。i18n の文言ファイル
- `meet_url` の分類表の行（設計 §12.8 で別の件とした）
- `backend/app/services/google_webhook.py`（取り込みの道は `upsert_from_google` の中で直す）
- 失敗した行を後から送り直す仕組み（設計 §12.7 で作らないと決めた）
- Google 側で直した回を取り込むこと（設計 §12.7 の範囲の外）
- `.github/workflows/`・`deploy.yml`・secrets・本番
- 台帳 `.claude-pipeline/active-work.d/release-schedule-recurrence-backend.md` の commit（作るが commit しない。クラウドの決まりで active-work.d は commit しない）

## 2. 前提の事実（origin/main 63709b0eb）

- 予定の表は各会社の部屋の `calendar_events`（`migrations/078_create_calendar_events_tenant.sql:44-65`）。`sync_status` の初期値は `'synced'`（同じファイルの 59 行目）なので、新しく入れる行は `'pending'` を明示する。
- 欄足しの手本は `migrations/20261104_161223_add_calendar_events_meet_url.sql`（会社の部屋を `^tenant_\d+$` で回し、表が無い部屋は飛ばす）。
- 一覧 `backend/app/services/calendar_service.py:150` `list_events`。期間の条件は始まりと終わりの 2 つを足し、`ce.` を付けて ` AND ` でつなぐ（`:168-183`。文の形は §4-6 の 1 本の条件の中にそのまま残る）。見せ方の絞りは `:185-189`。読む欄は 19 個で、最後が `ce.meet_url`（`:195-216`）。
- 作る `:247`・直す `:336`・消す `:483`・取り込み `:551`（アプリ起源の判定 `_is_app_origin` は `:129`、取り込みでの呼び出しは `:573`）・Google の本文 `_to_google_event_body` `:652`。終日の終わりはアプリでは終わりの日の 23:59 日本時間、Google では次の日の日付。
- 受け口 `backend/app/routers/calendar.py`: `MEET_NOT_ALLOWED_DETAIL` `:108`・`CreateEventBody` `:111`・`UpdateEventBody` `:122`・作る `:405`・直す `:446`（持ち主の確かめは `:464` の 5 欄の SELECT）・消す `:538`（3 欄の SELECT・`cal_svc.delete_event` を try 無しで呼ぶ）。`from typing import Optional` はあり、`Annotated`・`Literal` は無い。`Query` は fastapi から読み込み済み。
- Google の呼び口 `backend/app/services/google_calendar.py`: `create_event` `:390`・`update_event` `:410`（patch）・`delete_event` `:430`・`__all__` `:443`。32 行目は `from datetime import datetime, timezone`。
- python-dateutil 2.9.0.post0 は今も間接に入っている（設計 recon §9.3）。
- Google の `events.instances`（公式 reference・Context7 /websites/developers_google_workspace_calendar_api・2026-11-12）: `timeMin` は「回の終わりの下限（含む）」、`timeMax` は「回の始まりの上限（含まない）」、どちらも時差つきの RFC3339。回には `originalStartTime`（`dateTime` か `date`）が付き、動かした回でも元の始まりで 1 つに決まる。
- 本カードで決めた細部:
  1. 設計 §12.7 からの変更（設計側も同じ枝で直した）: `get_instance` は `originalStart` の引数を使わず、`timeMin`・`timeMax` で回の前後の窓を引いてから `originalStartTime` が一致する回を選ぶ（`originalStart` の値の形が終日で公式に書かれていないため）。
  2. 一覧は、期間の始まりと終わりの両方があるとき、元の行も同じ 1 本の SELECT で取る（§4-6）。元の行が 1 件も無ければ SELECT は今と同じ 1 回だけなので、今の一覧の試験の多くはそのまま通る。
  3. 422 の `detail` は §4-5 の 8 つの識別の文字（画面の文言は便15B で i18n のキーに当てる）。

## 3. 触るファイル

| ファイル | 変更 |
|---|---|
| `migrations/20261112_160000_add_calendar_events_recurrence.sql` | 新規（§4-1） |
| `scripts/run_all_migrations.sh` | 末尾に 2 行（§4-1） |
| `backend/tests/rls_bootstrap.py` | `_TENANT_LOOP_MIGRATIONS` に 1 行（§4-1） |
| `backend/tests/test_tenant_loop_migration_guard.py` | `_REVIEWED` の 2 組に 1 つずつ（§4-1） |
| `backend/tests/test_calendar_sync_tenant_reset_pg.py` | `_MIGRATIONS` に 1 行・試験の追加（§4-1・§4-9） |
| `migrations/20261024_100300_create_ai_cloud_views.sql` | 1 行追加・3 行目の数（§4-1） |
| `backend/tests/ops/test_ai_cloud_views.py` | 486 行目の数（§4-1） |
| `backend/requirements.txt` | 2 行（§4-1） |
| `backend/app/services/calendar_recurrence.py` | 新規（§4-2） |
| `backend/app/services/google_calendar.py` | `get_instance`（§4-3） |
| `backend/app/services/calendar_service.py` | §4-4〜§4-8 |
| `backend/app/routers/calendar.py` | §4-5 |
| `backend/tests/test_calendar_recurrence.py` | 新規（§4-9） |
| `backend/tests/test_calendar_service.py` | 追加・1 か所の直し（§4-9） |
| `backend/tests/test_calendar_owner_api.py` | `_event_db` の直し・追加（§4-9） |

## 4. 変更前後

### 4-1. 移行とその載せ先

新しいファイル `migrations/20261112_160000_add_calendar_events_recurrence.sql`（全文）:

```sql
-- ADR-1075 便15A: 予定の繰り返し（design.md §12.4・§12.8）
-- 各会社の部屋の calendar_events に欄 4 つ・CHECK 4 つ・部分 UNIQUE 1 つを足す。何度流しても同じになる。
-- 欄はどれも NULL 可か一定の初期値なので表を書き直さない（ADR-1037 のロック待ちの決まりの中）。
DO $cal_recurrence$
DECLARE
  schema_rec RECORD;
  tbl regclass;
  chk RECORD;
BEGIN
  FOR schema_rec IN SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_\d+$' LOOP
    IF to_regclass(format('%I.calendar_events', schema_rec.nspname)) IS NULL THEN
      CONTINUE;
    END IF;
    tbl := format('%I.calendar_events', schema_rec.nspname)::regclass;

    EXECUTE format('ALTER TABLE %s ADD COLUMN IF NOT EXISTS recurrence_rule TEXT', tbl);
    EXECUTE format(
      'ALTER TABLE %s ADD COLUMN IF NOT EXISTS recurring_event_id INTEGER REFERENCES %s(id) ON DELETE CASCADE',
      tbl, tbl
    );
    EXECUTE format('ALTER TABLE %s ADD COLUMN IF NOT EXISTS original_start_datetime TIMESTAMPTZ', tbl);
    EXECUTE format('ALTER TABLE %s ADD COLUMN IF NOT EXISTS is_cancelled BOOLEAN NOT NULL DEFAULT false', tbl);

    FOR chk IN
      SELECT * FROM (VALUES
        ('calendar_events_recurrence_role_check',
         'NOT (recurrence_rule IS NOT NULL AND recurring_event_id IS NOT NULL)'),
        ('calendar_events_exception_pair_check',
         '(recurring_event_id IS NULL) = (original_start_datetime IS NULL)'),
        ('calendar_events_cancelled_exception_check',
         'NOT is_cancelled OR recurring_event_id IS NOT NULL'),
        ('calendar_events_recurrence_rule_format_check',
         'recurrence_rule ~ ''^FREQ=(DAILY|WEEKLY|MONTHLY|YEARLY)(;[A-Z]+=[A-Z0-9,+-]+)*$''')
      ) AS v(name, expr)
    LOOP
      IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conrelid = tbl AND conname = chk.name
      ) THEN
        EXECUTE format('ALTER TABLE %s ADD CONSTRAINT %I CHECK (%s) NOT VALID', tbl, chk.name, chk.expr);
        EXECUTE format('ALTER TABLE %s VALIDATE CONSTRAINT %I', tbl, chk.name);
      END IF;
    END LOOP;

    EXECUTE format(
      'CREATE UNIQUE INDEX IF NOT EXISTS calendar_events_exception_unique_idx ON %s'
      ' (recurring_event_id, original_start_datetime) WHERE recurring_event_id IS NOT NULL',
      tbl
    );
  END LOOP;
END
$cal_recurrence$;
```

- 会社を選ぶ条件 `^tenant_\d+$` はこのファイルに 1 回だけ（`backend/tests/rls_bootstrap.py` の回数 1 と合わせる）。

`scripts/run_all_migrations.sh` の末尾（今の最後の 2 行は `# ADR-1061 便2-2a …` の説明と `run_sql migrations/20261112_150000_create_viewer_contract_public_tables.sql`）の後ろに 2 行を足す:

```
# ADR-1075 便15A: 予定の繰り返し（calendar_events に欄 4 つ・CHECK 4 つ・部分 UNIQUE）
run_sql migrations/20261112_160000_add_calendar_events_recurrence.sql
```

`backend/tests/rls_bootstrap.py` `_TENANT_LOOP_MIGRATIONS`: `meet_url` の行（181 行目・値 1）の次の行に、同じ書き方で `"20261112_160000_add_calendar_events_recurrence.sql": 1,` を足す。

`backend/tests/test_tenant_loop_migration_guard.py` `_REVIEWED`: `meet_url` の名前が載っている 2 か所（49 行目の "rls_bootstrap.py" の組・62 行目の "test_calendar_sync_tenant_reset_pg.py" の組）それぞれの次に、同じ書き方で `"20261112_160000_add_calendar_events_recurrence.sql",` を足す。

`backend/tests/test_calendar_sync_tenant_reset_pg.py` `_MIGRATIONS`（44-53 行目）の最後に `("20261112_160000_add_calendar_events_recurrence.sql", True),` を足す。

`migrations/20261024_100300_create_ai_cloud_views.sql`: `calendar_type` の allow の行（366 行目）の次に 1 行を足し、3 行目の `1109` を `1110` にする。

```
  ('tenant_*','calendar_events',ARRAY['recurrence_rule'],'mask','値の決まりが値の一覧でなく文字の形だけのため伏せる'),
```

（字下げと前後の行の書き方は 366 行目に合わせる。）`backend/tests/ops/test_ai_cloud_views.py:486` の `1109` を `1110` にする。

`backend/requirements.txt`: `holidays==0.108` の行の次に 2 行:

```
# 予定の繰り返しの決まり（RRULE）を回に広げる（ADR-1075 便15A）。今も間接に入っている版を明示する
python-dateutil==2.9.0.post0
```

### 4-2. 新しいファイル `backend/app/services/calendar_recurrence.py`（全文・このまま書く）

```python
"""予定の繰り返しの決まり（RRULE）を作る・読み戻す・回に広げる（ADR-1075・design.md §12.4・§12.5）。

表を読まない・書かない純粋な関数だけを置く。決まりの文字は calendar_events.recurrence_rule の 1 か所だけに持つ。
- 時刻つき: dtstart は日本時間の aware。UNTIL は UTC の Z 形（YYYYMMDDTHHMMSSZ）。
- 終日: dtstart は日本時間の日付の 0:00（naive）。UNTIL は日付の形（YYYYMMDD）。
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, time, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from dateutil.rrule import rrulestr

logger = logging.getLogger(__name__)

JST = ZoneInfo("Asia/Tokyo")

RECURRENCE_VALUES = (
    "none",
    "daily",
    "weekly",
    "monthly_nth",
    "monthly_last",
    "yearly",
    "weekdays",
)

MAX_OCCURRENCES = 1000

_DAYS = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")
_WEEKDAYS_RULE = "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"
_UNTIL_RE = re.compile(r";UNTIL=[0-9TZ]+")


def to_jst(dt: datetime) -> datetime:
    """日本時間の aware にそろえる（時差の無い値は日本時間とみなす）。"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=JST)
    return dt.astimezone(JST)


def build_rule(recurrence: str, start: datetime) -> Optional[str]:
    """選び方と開始日（日本時間で見る）から決まりの文字を作る。none は None。

    開始日で選べない値（第 5 週の monthly_nth・その月の最後の同じ曜日でない monthly_last）は ValueError。
    """
    if recurrence == "none":
        return None
    s = to_jst(start)
    day = _DAYS[s.weekday()]
    if recurrence == "daily":
        return "FREQ=DAILY"
    if recurrence == "weekly":
        return f"FREQ=WEEKLY;BYDAY={day}"
    if recurrence == "weekdays":
        return _WEEKDAYS_RULE
    if recurrence == "yearly":
        return "FREQ=YEARLY"
    if recurrence == "monthly_nth":
        n = (s.day - 1) // 7 + 1
        if n > 4:
            raise ValueError("monthly_nth_not_available")
        return f"FREQ=MONTHLY;BYDAY={n}{day}"
    if recurrence == "monthly_last":
        if (s + timedelta(days=7)).month == s.month:
            raise ValueError("monthly_last_not_available")
        return f"FREQ=MONTHLY;BYDAY=-1{day}"
    raise ValueError("unknown_recurrence")


def strip_until(rule: str) -> str:
    return _UNTIL_RE.sub("", rule)


def get_until(rule: str) -> Optional[str]:
    m = _UNTIL_RE.search(rule)
    return m.group(0)[len(";UNTIL="):] if m else None


def rule_to_recurrence(rule: Optional[str]) -> str:
    """決まりの文字から選び方を読み戻す（UNTIL は除いてから）。読み戻せないものは "custom"。"""
    if not rule:
        return "none"
    r = strip_until(rule)
    if r == "FREQ=DAILY":
        return "daily"
    if r == _WEEKDAYS_RULE:
        return "weekdays"
    if r == "FREQ=YEARLY":
        return "yearly"
    m = re.fullmatch(r"FREQ=WEEKLY;BYDAY=(MO|TU|WE|TH|FR|SA|SU)", r)
    if m:
        return "weekly"
    m = re.fullmatch(r"FREQ=MONTHLY;BYDAY=([1-4])(MO|TU|WE|TH|FR|SA|SU)", r)
    if m:
        return "monthly_nth"
    m = re.fullmatch(r"FREQ=MONTHLY;BYDAY=-1(MO|TU|WE|TH|FR|SA|SU)", r)
    if m:
        return "monthly_last"
    return "custom"


def until_before(occurrence_start: datetime, is_all_day: bool) -> str:
    """「これ以降」で切る UNTIL: その回の前の日の終わり（§12.5 following）。

    時刻つき: 前の日の 23:59:59 日本時間を UTC の Z 形。終日: 前の日の日付。
    """
    prev_day = to_jst(occurrence_start).date() - timedelta(days=1)
    if is_all_day:
        return prev_day.strftime("%Y%m%d")
    end_jst = datetime.combine(prev_day, time(23, 59, 59), tzinfo=JST)
    return end_jst.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def with_until(rule: str, until: str) -> str:
    """決まりに UNTIL を付ける。既に UNTIL があれば早い方を残す（§12.5 UNTIL の扱い）。

    同じ決まりの UNTIL どうしは同じ形（時刻つきは Z 形・終日は日付）なので文字の比べで早い方が分かる。
    """
    old = get_until(rule)
    if old is not None and old <= until:
        return rule
    return strip_until(rule) + f";UNTIL={until}"


def _until_value(dt: datetime, is_all_day: bool) -> str:
    """UNTIL と同じ形の文字（終日は日本時間の日付・時刻つきは UTC の Z 形）。"""
    j = to_jst(dt)
    if is_all_day:
        return j.strftime("%Y%m%d")
    return j.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def convert_until(until: str, to_all_day: bool) -> str:
    """UNTIL の形を終日／時刻つきに合わせ直す（終日⇄時刻つきを直した回で元の UNTIL を引き継ぐため）。

    時刻つき→終日: UTC の時刻を日本時間の日付にする。終日→時刻つき: その日の 23:59:59 日本時間を UTC の Z 形にする。
    """
    has_time = "T" in until
    if to_all_day and has_time:
        dt = datetime.strptime(until, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        return dt.astimezone(JST).strftime("%Y%m%d")
    if not to_all_day and not has_time:
        day = datetime.strptime(until, "%Y%m%d").date()
        end_jst = datetime.combine(day, time(23, 59, 59), tzinfo=JST)
        return end_jst.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return until


def carry_until(new_rule: str, old_rule: Optional[str], is_all_day: bool) -> str:
    """元の決まりの UNTIL を新しい決まりへ引き継ぐ（§12.5 UNTIL の扱い）。元に UNTIL が無ければそのまま。"""
    old = get_until(old_rule) if old_rule else None
    if old is None:
        return new_rule
    return with_until(new_rule, convert_until(old, is_all_day))


def starts_after_until(rule: str, start: datetime, is_all_day: bool) -> bool:
    """新しい始まりが決まりの UNTIL より後か（後なら 422 recurrence_after_until）。UNTIL が無ければ False。"""
    until = get_until(rule)
    if until is None:
        return False
    return _until_value(start, is_all_day) > convert_until(until, is_all_day)


def _dtstart(master_start: datetime, is_all_day: bool) -> datetime:
    s = to_jst(master_start)
    if is_all_day:
        return datetime.combine(s.date(), time(0, 0))
    return s


def _to_rule_tz(dt: datetime, is_all_day: bool) -> datetime:
    """比べる時刻を決まりの型にそろえる（終日は日本時間の naive）。"""
    j = to_jst(dt)
    return j.replace(tzinfo=None) if is_all_day else j


def _from_rule_tz(dt: datetime, is_all_day: bool) -> datetime:
    return dt.replace(tzinfo=JST) if is_all_day else dt.astimezone(JST)


def expand(
    rule: str,
    master_start: datetime,
    duration: timedelta,
    is_all_day: bool,
    window_start: datetime,
    window_end: datetime,
    limit: int = MAX_OCCURRENCES,
) -> list[datetime]:
    """期間の中の回の始まり（日本時間の aware）を返す。

    期間の始まり − 長さ から 期間の終わり まで（両端を含む）で取り、
    回の始まりが期間の終わりより前、かつ回の終わりが期間の始まりより後の回だけに最後に絞る（§12.5・審査1 ⑥）。
    limit を超えたら打ち切って警告を残す。
    """
    rr = rrulestr(rule, dtstart=_dtstart(master_start, is_all_day))
    lo = _to_rule_tz(window_start - duration, is_all_day)
    hi = _to_rule_tz(window_end, is_all_day)
    out: list[datetime] = []
    ws = to_jst(window_start)
    we = to_jst(window_end)
    for occ in rr.xafter(lo, inc=True):
        if occ > hi:
            break
        start = _from_rule_tz(occ, is_all_day)
        if start < we and start + duration > ws:
            if len(out) >= limit:
                logger.warning("繰り返しの回が %s を超えたので打ち切った: rule=%s", limit, rule)
                break
            out.append(start)
    return out


def is_occurrence(rule: str, master_start: datetime, is_all_day: bool, occurrence_start: datetime) -> bool:
    """occurrence_start が決まりの回に当たるか（その時刻 ±1 秒）。"""
    rr = rrulestr(rule, dtstart=_dtstart(master_start, is_all_day))
    o = _to_rule_tz(occurrence_start, is_all_day)
    return bool(rr.between(o - timedelta(seconds=1), o + timedelta(seconds=1), inc=True))


def occurrence_of(master_start: datetime, is_all_day: bool, occurrence_start: datetime) -> datetime:
    """回の始まりを表に入れる形にそろえる（終日はその日の日本時間 0:00・§12.4）。"""
    o = to_jst(occurrence_start)
    if is_all_day:
        return datetime.combine(o.date(), time(0, 0), tzinfo=JST)
    return o


def is_first_occurrence(master_start: datetime, is_all_day: bool, occurrence_start: datetime) -> bool:
    return occurrence_of(master_start, is_all_day, occurrence_start) == occurrence_of(
        master_start, is_all_day, master_start
    )


def google_recurrence(rule: str) -> list[str]:
    """Google へ送る本文の recurrence（§12.7）。"""
    return ["RRULE:" + rule]
```

### 4-3. `backend/app/services/google_calendar.py` に `get_instance`

- 32 行目 `from datetime import datetime, timezone` を `from datetime import datetime, timedelta, timezone` にする。その次の行に `from zoneinfo import ZoneInfo` を足す（標準の読み込みの並びに置く）。
- `delete_event`（`:430`）の後ろ、`__all__` の前に次を足し、`__all__` の最後（`"delete_event"` の次）に `"get_instance",` を足す。

```python
async def get_instance(
    db, tenant_id: int, recurring_event_id: str, original_start: datetime, is_all_day: bool
) -> dict:
    """繰り返しの予定の 1 回分を、決まりでの元の始まり（originalStartTime）で引いて返す（ADR-1075 §12.7 this）。

    timeMin（回の終わりの下限・含む）と timeMax（回の始まりの上限・含まない）で窓を作り（終日は前後 1 日ずつ広く）、
    返った回のうち originalStartTime が一致するものを返す。見つからなければ RuntimeError。
    """
    service = await _get_service(db, tenant_id)
    calendar_id = await get_calendar_id(db, tenant_id)
    jst = ZoneInfo("Asia/Tokyo")
    if original_start.tzinfo is None:
        original_start = original_start.replace(tzinfo=jst)
    start_jst = original_start.astimezone(jst)
    if is_all_day:
        # 終日の範囲は Google のカレンダーの時間帯で解かれるので、前後 1 日ずつ広く引いて originalStartTime で選ぶ
        day0 = datetime.combine(start_jst.date(), datetime.min.time(), tzinfo=jst)
        window_start = day0 - timedelta(days=1)
        window_end = day0 + timedelta(days=2)
    else:
        window_start = start_jst
        window_end = start_jst + timedelta(seconds=1)

    try:
        result = await asyncio.to_thread(
            service.events()
            .instances(
                calendarId=calendar_id,
                eventId=recurring_event_id,
                timeMin=window_start.isoformat(),
                timeMax=window_end.isoformat(),
                maxResults=10,
            )
            .execute
        )
    except Exception as e:
        raise RuntimeError(f"繰り返しの回の取得に失敗: {e}") from e

    for item in result.get("items", []):
        original = item.get("originalStartTime") or {}
        if is_all_day:
            if original.get("date") == start_jst.date().isoformat():
                return item
        elif original.get("dateTime"):
            if datetime.fromisoformat(original["dateTime"]) == start_jst:
                return item
    raise RuntimeError("繰り返しの回が見つかりません")
```

### 4-4. `backend/app/services/calendar_service.py` — 予定 1 行の読み方と Google の本文

- 読み込みに `from app.services import calendar_recurrence as rec` を足す（`from app.auth.dependencies import reset_tenant_context` の次）。
- `_is_app_origin`（`:129`）の後ろに次を足す。並び（18 欄）は受け口の試験の作り手 `_event_db` と同じにする。

```python
# 予定 1 行の読み方（受け口の持ち主の確かめ・繰り返しの判定・3 択の処理で同じ並びを使う）
EVENT_COLUMNS = (
    "created_by_user_id", "calendar_type", "user_id", "google_event_id", "meet_url",
    "id", "source", "recurrence_rule", "recurring_event_id", "original_start_datetime",
    "start_datetime", "end_datetime", "is_all_day", "is_cancelled",
    "title", "description", "location", "category",
)
EVENT_COLUMNS_SQL = ", ".join(EVENT_COLUMNS)


def event_from_row(row) -> dict:
    return {name: row[i] for i, name in enumerate(EVENT_COLUMNS)}


async def read_event(db: AsyncSession, event_id: int) -> Optional[dict]:
    row = await db.execute(
        text(f"SELECT {EVENT_COLUMNS_SQL} FROM calendar_events WHERE id = :id"),
        {"id": event_id},
    )
    record = row.first()
    return event_from_row(record) if record else None


def _google_body_for(ev: dict) -> dict:
    """表の 1 行（直した後の値）から Google の本文を作る。元の行なら recurrence を付ける（§12.7）。"""
    payload = {
        "title": ev.get("title") or "",
        "description": ev.get("description"),
        "location": ev.get("location"),
        "start_datetime": ev["start_datetime"].isoformat(),
        "end_datetime": ev["end_datetime"].isoformat(),
        "is_all_day": bool(ev.get("is_all_day")),
    }
    body = _to_google_event_body(payload)
    if ev.get("recurrence_rule"):
        body["recurrence"] = rec.google_recurrence(ev["recurrence_rule"])
    return body
```

- 作る道 `create_event`（`:247`）: `payload` の `recurrence` を読む（無ければ `"none"`）。INSERT の欄に `recurrence_rule` を足し、値は `rec.build_rule(recurrence, _parse_dt(payload["start_datetime"]))`（none なら NULL。選べない値は受け口が先に 422 で止めているので、ここでは ValueError は起きない）。Google へ送る本文は、決まりがあるときだけ `google_body["recurrence"] = rec.google_recurrence(決まり)` を足す。ほかは今のまま。

### 4-5. 判定と受け口（422 はどれも受け口の `try` の前）

`calendar_service.py` に判定を足す。表は読むだけ。誤りの識別の文字か None を返す。

| 識別の文字 | いつ |
|---|---|
| `recurrence_meet_not_allowed` | 繰り返しを付けて作る・直すときに `add_meet` が真／`meet_url` がある単発の行に繰り返しを付ける／元の行・例外の行に `add_meet` が真 |
| `recurrence_not_available` | `rec.build_rule` が ValueError（開始日で選べない。直すときは新しい始まりで作り直して確かめる。読み戻しが `"custom"` で始まりを変えるときも） |
| `recurrence_scope_not_allowed` | 単発の行に `scope` が来た |
| `recurrence_scope_required` | 元の行・例外の行に `scope` が無い |
| `recurrence_occurrence_invalid` | `occurrence_start` が無い・読めない・`rec.is_occurrence` が偽。例外の行の id のときは、その行の `original_start_datetime` と ±1 秒で一致しない |
| `recurrence_this_not_allowed` | `scope` が this で、`calendar_type` か `recurrence` を今の値から変える |
| `recurrence_google_source` | `source = 'google'` の行に none 以外の `recurrence` |
| `recurrence_after_until` | following・all で作る新しい決まりに元の UNTIL を引き継いだとき、新しい始まりが UNTIL より後（`rec.starts_after_until`） |

```python
def check_create_recurrence(payload: dict) -> Optional[str]: ...
async def check_recurrence_request(
    db: AsyncSession, *, event: dict, payload: Optional[dict], scope: Optional[str],
    occurrence_start: Optional[str],
) -> Optional[str]: ...
```

- `event` は受け口が `read_event` で読んだ行。例外の行なら関数の中で `read_event(db, event["recurring_event_id"])` で元の行を読む。`payload` は消すとき None。
- `recurrence` が今の選び方（`rec.rule_to_recurrence(元の行の決まり)`）と同じなら「変えない」として扱う（判定でも処理でも）。単発の行の `"none"` も同じ。
- following・all の新しい始まり: following は「押した回の新しい始まり」（`payload` の `start_datetime`、無ければその回の始まり）。all は §4-7 のずらした「元の行の新しい始まり」。
- 押した回が 1 回目（`rec.is_first_occurrence`）の following は all として判定する。

受け口 `backend/app/routers/calendar.py`:

- 読み込みを `from typing import Annotated, Literal, Optional` にする。
- `RecurrenceValue = Literal["none", "daily", "weekly", "monthly_nth", "monthly_last", "yearly", "weekdays"]` と `RecurrenceScope = Literal["this", "following", "all"]` を `MEET_NOT_ALLOWED_DETAIL` の近くに置く。
- `CreateEventBody` に `recurrence: RecurrenceValue = "none"`。`UpdateEventBody` に `recurrence: Optional[RecurrenceValue] = None`・`scope: Optional[RecurrenceScope] = None`・`occurrence_start: Optional[str] = None`。
- 作る（`:405`）: `calendar_type` の判定の直後・**Meet の判定（`:417-423`）より前**で `detail = cal_svc.check_create_recurrence(body.model_dump())`。None でなければ 422（繰り返しと `add_meet` が両方あるときは、つないでいるかに関係なく `recurrence_meet_not_allowed`）。
- 直す（`:446`）: `payload` から `scope` と `occurrence_start` を取り出して（`pop`）残りを直す値とする。持ち主の確かめの 5 欄の SELECT を `cal_svc.read_event(db, event_id)` に置き換え、例外の行なら元の行を読み、持ち主・見せ方の 404・403 は**元の行の値**で今と同じに判定する（今の `record[0]`〜`record[4]` は辞書の名前で読む）。`pop` の後に直す値が空なら今と同じ 422 `no_fields_to_update`。今の `calendar_type` の判定（`:483-495`）は今のまま残し、その**直後・Meet の判定（`:497-513`）より前**で `check_recurrence_request` を呼び、None でなければ 422。だから元の行・例外の行への `add_meet` は、つないだ本人かや Google の id の有無に関係なく `recurrence_meet_not_allowed` になる（試験で `can_add_meet` を patch しなくてよい）。Meet の判定は今のまま後ろに残す。そのあと、単発の行で `recurrence` が無い（または none）なら今の `cal_svc.update_event`、それ以外は `cal_svc.update_recurring_event(...)` を同じ `try` の中で呼ぶ。
- 消す（`:538`）: 引数に次の 2 つを足す。3 欄の SELECT を `read_event` に置き換え、例外の行なら元の行の値で持ち主を確かめる。判定を呼んで 422 の後、単発の行は今の `cal_svc.delete_event`、それ以外は `cal_svc.delete_recurring_event(...)`。

```python
    scope: Annotated[Optional[RecurrenceScope], Query()] = None,
    occurrence_start: Annotated[Optional[str], Query()] = None,
```

- `occurrence_start` を読むときは `cal_svc._parse_dt`（`+` が空白に化けた値も読める）を使い、日本時間にそろえてから比べる。

### 4-6. 一覧 `list_events`（`:150`）

- 期間の始まりと終わりの**両方**があり、`title_query` が無いとき: 期間の 2 つの条件（`:169-174`）を `filters` に**入れず**、`where = " AND ".join(...) or "TRUE"`（`:183`）の行の**後ろ**で `where += " AND " + 下の 1 本` とする（`filters` に入れると頭に `ce.` がもう 1 つ付いて SQL が壊れるため。`params` の `start`・`end` は今と同じに入れる）。片方だけのときと探すときは今のまま `filters` に入れ、探すときは `ce.recurrence_rule IS NULL` を足さない。一覧の試験では、SQL の文に `(ce.start_datetime < :end AND ce.end_datetime > :start AND ce.recurrence_rule IS NULL) OR` がそのまま入り、`ce.(` が入らないことを確かめる。

```
((ce.start_datetime < :end AND ce.end_datetime > :start AND ce.recurrence_rule IS NULL) OR (ce.recurrence_rule IS NOT NULL AND ce.start_datetime < :end))
```

- どの呼び方でも `AND NOT ce.is_cancelled` を足す（見せ方の絞りの後）。
- SELECT の最後（`ce.meet_url` の後ろ）に `ce.recurrence_rule, ce.recurring_event_id, ce.original_start_datetime` を足す（`r[19]`〜`r[21]`）。今の 19 欄の並びは変えない。
- 返す辞書には、どの行にも `recurrence_rule`・`recurrence`（`rec.rule_to_recurrence`）・`recurring_event_id`・`occurrence_start` を足す。単発の行は `None`・`"none"`・`None`・`None`。
- 期間で引いたとき、元の行（`r[19]` あり）は返さずに回へ広げる:
  1. 元の行の id があれば、例外の行を期間に関係なく 1 本で引く: `SELECT ce.recurring_event_id, ce.original_start_datetime FROM calendar_events ce WHERE ce.recurring_event_id = ANY(:ids)` に、上と同じ見せ方の絞り（`user_id` の有無で 2 通り）と `calendar_type` の絞りを付ける（消した印の行も含める）。
  2. 回は `rec.expand(決まり, 元の始まり, 元の終わり − 元の始まり, 終日か, 期間の始まり, 期間の終わり)`。1. の (元の id, 元の始まり) と一致する回は外す（`rec.occurrence_of` でそろえ、UTC の時刻で比べる）。
  3. 回の辞書は元の行の辞書の写しに、`start_datetime`・`end_datetime`（回の始まり・始まり＋長さ）・`recurring_event_id`＝元の id・`occurrence_start`＝回の始まり（isoformat）を入れる。`id` は元の id のまま。
- 例外の行（`r[20]` あり）は `occurrence_start`＝`r[21]` の isoformat。`recurrence` は元の行の選び方: 元の行が同じ結果の中にあればその決まり、無ければ `SELECT id, recurrence_rule FROM calendar_events WHERE id = ANY(:ids)` を 1 本だけ引く（要らなければ引かない）。
- 期間で引いたときは最後に始まりの時刻（datetime）で並べ直す。探すときは広げず、元の行は 1 件として返す（`occurrence_start` は None）。

### 4-7. 直す 3 択 `update_recurring_event`

```python
async def update_recurring_event(
    db: AsyncSession, tenant_id: int, user_id: int, event: dict, payload: dict,
    scope: Optional[str], occurrence_start: Optional[datetime],
) -> dict: ...
```

共通の決まり（設計 §12.5・§12.7 をそのまま）:
- `m` は元の行（`event` が例外の行なら読み直した元の行）。`occ = rec.occurrence_of(m 始まり, m 終日, occurrence_start)`。`dur = m 終わり − m 始まり`。押した回の今の値は、例外の行ならその行の値、それ以外は `occ` と `occ + dur`。
- `send_ok` は `m["google_event_id"]` があり、`_get_sync_mode` が `bidirectional` か `write_only`。偽なら Google に何も送らず、直した行・新しい行は `'pending'` のまま。
- 新しく入れる行は INSERT の文で `sync_status = 'pending'` と `source = 'app'` を明示し、`created_by_user_id`・`category` は `m` の写し。例外の行の `calendar_type`・`user_id` は `m` の写し、`meet_url` は NULL。
- 消える例外の行の Google の id（`is_cancelled = false` で `google_event_id` を持つ行）は、表を消す**前**に読む。表の変更を commit して `reset_tenant_context` の後に、先にそれぞれへ `update_event(id, {"status": "cancelled"})` を 1 件ずつ別の `try` で送り（失敗は警告だけ）、そのあと元の予定への送りを行う。
- 表を直す UPDATE の文（A・B'・C・D1〜D3 の `m` も例外の行も新しい行も）には、今の `update_event`（`:372`）と同じく必ず `sync_status = 'pending'` を入れる。`send_ok` が偽なら全部 `'pending'` のまま残る。
- 「変わる」かの比べ方: 直す値（`payload`）に入っている欄だけを、押した回の今の値（例外の行の id ならその行、それ以外は `occ`・`occ + dur`・`m` の終日）と比べる。日時は `_parse_dt` で読み日本時間の datetime どうしで比べ、`recurrence` は §4-5 の「変えない」の決まりで比べる。`payload` に無い欄は変わらないとみなす。だから動かした例外の回で題名だけを all で直すと D1 になる。
- Google への送りが通った行は `sync_status = 'synced', last_synced_at = NOW()`。commit のたびに `reset_tenant_context(db, tenant_id)`（Rule C）。

場合ごと:

| 場合 | 表 | Google（`send_ok` のとき・順番どおり） |
|---|---|---|
| A. 単発の行に none 以外の `recurrence` | その行に直す値と `recurrence_rule = build_rule(選び方, 新しい始まり)`、`'pending'` | 行の `google_event_id` があれば「消して作り直す道」 |
| B. this（例外の行が無い回） | `(m.id, occ)` の例外の行を INSERT（押した回の今の値に直す値を重ねる・`is_cancelled = false`） | `get_instance(m の Google の id, occ, 終日か)` → その id に `update_event(_google_body_for(例外の行))` → 例外の行に `google_event_id`＝回の id・`sync_origin_id`＝`_build_sync_origin_id(tenant_id, 例外の行の id)`・`'synced'`。どこかで失敗したら例外の行を `'failed'`（`google_event_id` は NULL のまま） |
| B'. this（例外の行の id か、その回の例外の行が既にある） | その行を直す | 行の `google_event_id` があればそれに `update_event`、無ければ B と同じく `get_instance` から。失敗は `'failed'` |
| C. following（1 回目でない） | `m` の決まりを `rec.with_until(m 決まり, rec.until_before(occ, m 終日))` に、`original_start_datetime >= occ` の例外の行を DELETE、新しい元の行を INSERT（押した回の値に直す値を重ね、決まりは `rec.carry_until(build_rule(新しい選び方, 新しい始まり), m 決まり, 新しい終日)`。新しい選び方が none なら決まりは NULL） | 例外の回へ cancelled → `update_event(m の id, {"recurrence": rec.google_recurrence(切った決まり)})`。失敗なら `m` と新しい行の両方を `'failed'` にして終わる（insert は送らない）。通れば `m` を `'synced'` → `create_event(_google_body_for(新しい行))`。通れば新しい行に id・`sync_origin_id`・`'synced'`、失敗なら新しい行だけ `'failed'`（id は NULL） |
| D1. all・始まり・終わり・終日・選び方は変わらない | `m` の変わった欄を直し、同じ欄を `recurring_event_id = m.id` の例外の行にも写す | `update_event(m の id, _google_body_for(m) から "recurrence" を除いた本文)`。失敗は `m` を `'failed'` |
| D2. all・始まり・終わり・終日・選び方のどれかが変わる（none 以外） | `m` の新しい始まり＝`m` の始まり＋（新しい始まり − `occ`）、終わりも同じだけ（押した回の終わりとの差）。決まりは `carry_until(build_rule(選び方, m の新しい始まり), m 決まり, 新しい終日)`。例外の行は全部 DELETE | 例外の回へ cancelled →「消して作り直す道」 |
| D3. all で none | 残る 1 件の日時は押した回の日時（直す値に日時があればその値）。`recurrence_rule = NULL`、例外の行は全部 DELETE | 例外の回へ cancelled →「消して作り直す道」 |

- 1 回目の following は D1〜D3 と同じに扱う。例外の行の id に following・all が来たら `m` に読み替える。
- 消して作り直す道: `delete_event(古い id)` が失敗したら行を `'failed'`（`google_event_id`・`sync_origin_id` は古いまま）で終わる。通ったら `create_event(_google_body_for(行))`。通れば新しい id と `sync_origin_id` と `'synced'`、失敗なら `'failed'` にして `google_event_id`・`sync_origin_id` を NULL。
- 返す値は今と同じ形 `{"id": 直した行か新しい元の行の id, "meet_url": None}`。

### 4-8. 消す 3 択 `delete_recurring_event` と取り込み

```python
async def delete_recurring_event(
    db: AsyncSession, tenant_id: int, event: dict, scope: str, occurrence_start: datetime,
) -> None: ...
```

| scope | 表 | Google（`send_ok` のとき。どの失敗も警告だけで `sync_status` は変えない） |
|---|---|---|
| this | 例外の行があれば `is_cancelled = true` に、無ければ元の値の写しで `is_cancelled = true`・`sync_status = 'pending'` の例外の行を INSERT | 行の `google_event_id` があればそれに、無ければ `get_instance` で引いた回に `update_event(id, {"status": "cancelled"})`。引けたら行に `google_event_id`・`sync_origin_id` を書く |
| following（1 回目でない） | `m` の決まりを UNTIL で切り、`original_start_datetime >= occ` の例外の行を DELETE | 消える例外の回へ cancelled → `update_event(m の id, {"recurrence": ...})`。新しい予定は作らない |
| all（1 回目の following も） | `m` を DELETE（例外の行は ON DELETE CASCADE で消える） | 全部の例外の回へ cancelled → `delete_event(m の id)` |

- 送り先の id は表を変える前に読み、commit と `reset_tenant_context` の後に送る。例外の回を先、元の予定を後。

取り込み `upsert_from_google`（`:551`）: `_is_app_origin` の判定（`:573`）の直後に、来た予定の `recurringEventId` があり `await _is_app_origin(db, それ, tenant_id)` が真なら `"skipped"` を返す 3 行を足す（アプリ起源の繰り返しの回を二重に入れない・§12.7）。

### 4-9. 試験

新しい `backend/tests/test_calendar_recurrence.py`（表を使わない純粋な試験。名前はこのとおり）:
- `test_build_rule_six_kinds`: 2026-11-12 10:00 日本時間で daily・weekly（`BYDAY=TH`）・weekdays・yearly・monthly_nth（`BYDAY=2TH`）、2026-11-30 で monthly_last（`BYDAY=-1MO`）
- `test_build_rule_not_available`: 2026-10-29（第 5 木曜）の monthly_nth と 2026-11-12 の monthly_last が ValueError
- `test_rule_to_recurrence_round_trip`: 6 つの決まりと UNTIL 付きが元の選び方に戻る・読めない決まりは `"custom"`・None は `"none"`
- `test_expand_two_months`: 期間は 2026-11-01 0:00〜2027-01-01 0:00 日本時間。2026-11-12 10:00 日本時間に始まる 1 時間の毎週（`FREQ=WEEKLY;BYDAY=TH`）は 8 回で最初の 2 つが 11/12 10:00・11/19 10:00。2026-11-30 10:00 に始まる毎月最終月曜（`FREQ=MONTHLY;BYDAY=-1MO`）は 2 回で 11/30 10:00・12/28 10:00。ほかの 4 つ（daily・weekdays・yearly・monthly_nth）は 2026-11-12 10:00 始まりで、回の数と最初の 2 つは daily 50（11/12・11/13）・weekdays 36（11/12・11/13）・yearly 1（11/12）・monthly_nth 2（11/12・12/10）。どれも 10:00 日本時間（数は Opus が §4-2 をそのまま Python 3.12・dateutil 2.9.0.post0 で動かして得た値）
- `test_expand_strict_window`: 期間の終わりちょうどに始まる回と、期間の始まりちょうどに終わる回が入らない
- `test_expand_all_day`: 終日の毎週で回の始まりが日本時間 0:00
- `test_expand_limit_1000`: 毎日・10 年の期間で 1000 件で止まり警告が 1 件（`caplog`）
- `test_until_before_and_with_until`: 時刻つきは前の日の 23:59:59 日本時間（2026-11-26 の回なら `20261125T145959Z`）・終日は `20261125`・既にある早い UNTIL は残る
- `test_carry_and_after_until`: 時刻つき⇄終日の UNTIL の引き継ぎと `starts_after_until`
- `test_is_occurrence_and_first`: 回に当たる・当たらない・1 回目の判定

`backend/tests/test_calendar_service.py` に足す（`patch("app.services.google_calendar.…", new=AsyncMock(...))` と `_make_db` の `side_effect` で、送った順と回数を `call_args_list` で確かめる）:
- 一覧: 元の行 1 件（毎週）が期間の中で回に広がる／例外の行の回が外れる／消した印の例外は返らない（SQL に `NOT ce.is_cancelled`）／例外の引き直しの SQL に見せ方の絞りが入る／探すときは広げない
- 今の `test_returns_events`（225 行目）の行の組に `None, None, None` の 3 つを足す（欄が 22 になるため）。ほかの今の一覧の試験は変えずに通ること
- 作る: 繰り返しありで INSERT に決まりが入り、Google の本文に `recurrence` が付く
- 直す: §4-7 の表の A・B・B'・C・D1・D2・D3 それぞれの表の文と Google への送り（順番・回数）。C で元への patch を失敗させたとき insert 0 件・両方 `'failed'`。C で insert だけ失敗させたとき元は `'synced'`・新しい行だけ `'failed'`。B・D1 の patch を失敗させたとき `'failed'`。消して作り直す道で delete 失敗・create だけ失敗のそれぞれ。`send_ok` が偽（同期の向きが none・元に Google の id が無い）で送り 0 件。例外の回への cancelled の 1 件の失敗で残りが続く。消える例外の id が DELETE の前に読まれている
- 消す: this・following・all の表の文と送り（this は cancelled の patch 1 件だけ・following は例外の数だけの cancelled と recurrence の patch 1 件で insert 0 件・all は例外の数だけの cancelled と delete 1 件）。どれも例外の回が先。送りを失敗させても `sync_status` を変える文が出ない
- 取り込み: `recurringEventId` がアプリ起源なら `"skipped"`
- 判定: §4-5 の 8 つの識別の文字がそれぞれ出る場合
- 次の 3 つは名前を付けて足す（設計 §12.10）: `test_update_all_none_keeps_pressed_occurrence`（all で none のとき、残る 1 件の始まり・終わりが押した回の日時。直す値に日時があればその値）／`test_update_and_delete_exception_id_routes_to_master`（例外の行の id に following・all で直す・消すと、表の文も Google への送りも元の行の id・元の Google の id に向く）／`test_send_ok_new_rows_synced`（元の行が `google_event_id` を持ち双方向のとき、following の新しい元の行は `create_event` が 1 件呼ばれ、this の例外の行は `get_instance` と `update_event` が 1 件ずつ呼ばれ、どちらの行も `sync_status = 'synced'` にする文が出る）

`backend/tests/test_calendar_owner_api.py`:
- `_event_db`（180 行目）を `cal_svc.EVENT_COLUMNS` の 18 欄の並びの組を返す形に広げる（今の 5 つの引数はそのまま・残りは初期値。`id` は 1・`source` は `"app"`・時刻は固定の値・`is_all_day` と `is_cancelled` は False）。今の 8 か所の呼び出し（192・205・218・232・245・314・330・348 行目）が変えずに通ること
- 足す: 単発に `scope` → 422 `recurrence_scope_not_allowed`／元の行に `scope` 無し → 422 `recurrence_scope_required`／Google から取り込んだ行に `recurrence` → 422 `recurrence_google_source`／繰り返しで `add_meet` → 422 `recurrence_meet_not_allowed`。どれも `cal_svc.update_event` が呼ばれないこと。消す受け口で `scope` 無しの元の行 → 422

`backend/tests/test_calendar_sync_tenant_reset_pg.py`（本物の PostgreSQL）:
- 移行の後に 4 つの欄と 4 つの CHECK と索引があること（`pg_constraint`・`pg_indexes` を読む）
- 元の行を作り、this で消すと例外の行が `is_cancelled = true`・`sync_status = 'pending'` で 1 行／all で消すと例外の行も消えること（ON DELETE CASCADE）
- 同じ回の例外の行を 2 つ入れると UNIQUE で止まること

## 5. 確かめ（担当が行う）

5-1. commit の前（どれも 1 回の Bash で `cd` から始める。`W` は作業場所の絶対パス `$HOME/worktrees/salesanchor/release-schedule-recurrence-backend`。Bash の呼び出しごとに場所は元に戻るので、毎回この形で書く）:
1. `cd "$HOME/worktrees/salesanchor/release-schedule-recurrence-backend/backend" && python -m pytest tests/test_calendar_recurrence.py tests/test_calendar_service.py tests/test_calendar_owner_api.py tests/test_tenant_loop_migration_guard.py tests/ops/test_ai_cloud_views.py -q 2>&1 | tail -n 60` … 最後の行に `failed` と `error` が無い（`skipped` はあってよい。手元に PostgreSQL が無いと要る試験は skip になる）
2. `cd "$HOME/worktrees/salesanchor/release-schedule-recurrence-backend/backend" && python -m pytest tests/test_calendar_sync_tenant_reset_pg.py -q 2>&1 | tail -n 30` … `failed`・`error` が無い。skip になったら skip の行をそのまま報告に写す（CI で走る）
3. `cd "$HOME/worktrees/salesanchor/release-schedule-recurrence-backend/backend" && python -m pytest tests/test_calendar_recurrence.py -v 2>&1 | grep -E "PASSED|FAILED|ERROR" | head -n 40` … §4-9 の 10 個の名前がすべて PASSED で、FAILED・ERROR が 0 行
4. `cd "$HOME/worktrees/salesanchor/release-schedule-recurrence-backend/backend" && python -m pytest tests/test_calendar_service.py -v 2>&1 | grep -E "test_update_all_none_keeps_pressed_occurrence|test_update_and_delete_exception_id_routes_to_master|test_send_ok_new_rows_synced" | head -n 10` … 3 つの名前がすべて PASSED
5. `grep -c "20261112_160000_add_calendar_events_recurrence.sql" "$HOME/worktrees/salesanchor/release-schedule-recurrence-backend/scripts/run_all_migrations.sh"` … 出力が `1`

5-2. commit の後・push の前: `git -C "$HOME/worktrees/salesanchor/release-schedule-recurrence-backend" diff --stat origin/main...HEAD | tail -n 25` … 変わったファイルが §3 の表の 15 件だけ（台帳は入らない）（新しいファイルも含まれる）。違えば止まる

5-3. push の後: `git -C "$HOME/worktrees/salesanchor/release-schedule-recurrence-backend" log origin/release/schedule-recurrence-backend -1 --oneline` が `git -C "$HOME/worktrees/salesanchor/release-schedule-recurrence-backend" log -1 --oneline` と同じ

## 6. 止まる条件

- origin/main の行番号や中身が §2 と違い、§4 の書き方が当てはまらない（どこが違うかを出して止まる）
- 今ある試験が、§4-9 で直すと書いた 2 か所（`test_returns_events` の行の組・`_event_db`）のほかで落ち、直すには試験の期待そのものを変える必要がある
- `migrations/` の別のファイルや `scripts/run_all_migrations.sh` の既にある行を変える必要が出た
- 設計 §12 と本カードが食い違い、どちらに従うか決められない

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 移行が会社ごとに冪等に欄 4・CHECK 4・索引 1 を足す | §4-9 の本物の PostgreSQL の試験（CI）と、移行の見張りの試験が緑 |
| 一覧が期間の中の回を返し、例外・消した印を正しく扱う（G71・G74 の裏側） | §5-1 の 1 の一覧の試験 |
| 3 択の 3 結果×直す／消すが設計 §12.5・§12.7 のとおり（G74・G79 の裏側） | §5-1 の 1 の直す・消すの試験（送った順番と回数まで） |
| 取り込みで二重にならない（G76 の裏側） | 取り込みの試験 |
| 今ある予定と単発の予定の動きが変わらない（G77） | 今の一覧・直す・消すの試験が変えずに通る（2 か所の組の直しを除く） |
| 422 はどれも `try` の前で、8 つの識別の文字が出る | 受け口の試験と判定の試験 |
| CI 緑（G78） | Opus が PR で確かめる |

## 8. 作業場所と push（PR は Opus が作る）

1. クラウドの写しの一番上（`git rev-parse --show-toplevel` の場所）で `git fetch origin && bash scripts/new-worktree.sh release/schedule-recurrence-backend`（origin/main 起点。`--claude` は付けない）。作成後に `git worktree list` で実在を確かめ、以後はその作業場所で行う
2. `git log origin/main -1 --oneline` で、このカードが origin/main にあることを `ls docs/handoff/schedule-gcal-clone/card-bin15a.md` で確かめる
3. 台帳 `.claude-pipeline/active-work.d/release-schedule-recurrence-backend.md` を Write ツールで作る（1 行目 `branch: release/schedule-recurrence-backend`、空行、表の頭 `| ブランチ名 | 担当機能エリア | 開始日時 | 状態 | PR# | main | 備考 |` と区切りの行、`| release/schedule-recurrence-backend | 予定の繰り返しの裏側（ADR-1075 便15A） | 2026-11-12 | IN_PROGRESS | | | |`）。この台帳は commit しない（§5 の add にも入れない）
4. §4 のとおりに書く（既にあるファイルは Edit ツール、新しいファイルは Write ツール。パスは作業場所の絶対パス）。§5-1 を通す
5. commit（`git -C "$HOME/worktrees/salesanchor/release-schedule-recurrence-backend" add migrations/20261112_160000_add_calendar_events_recurrence.sql scripts/run_all_migrations.sh backend/tests/rls_bootstrap.py backend/tests/test_tenant_loop_migration_guard.py backend/tests/test_calendar_sync_tenant_reset_pg.py migrations/20261024_100300_create_ai_cloud_views.sql backend/tests/ops/test_ai_cloud_views.py backend/requirements.txt backend/app/services/calendar_recurrence.py backend/app/services/google_calendar.py backend/app/services/calendar_service.py backend/app/routers/calendar.py backend/tests/test_calendar_recurrence.py backend/tests/test_calendar_service.py backend/tests/test_calendar_owner_api.py`（§3 の 15 件だけを名前で足す。`-A`・`.` は使わない）と `git -C "$HOME/worktrees/salesanchor/release-schedule-recurrence-backend" commit`。`--no-verify` は使わない。文: `feat(calendar): recurring events backend (ADR-1075 bin15A)`）→ `git -C "$HOME/worktrees/salesanchor/release-schedule-recurrence-backend" log -1 --oneline` → §5-2
6. `git -C "$HOME/worktrees/salesanchor/release-schedule-recurrence-backend" push -u origin release/schedule-recurrence-backend` → §5-3

## 9. 報告

- 冒頭に受領文。1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか
- 本文に: §5-1〜§5-3 の出力（生のまま）・push した commit・判断を要した点（事実のみ）
- 停止したときは: 停止した手順番号／最後に実行したコマンド／停止した理由の原文

## 10. 委任の定型

- sleep は使わない。CI は待たない
- ファイルの編集は Edit ツール、新しいファイルは Write ツールで行う（ヒアドキュメントで書かない）。rm は使わない
- PR は作らない。main にマージしない。本番・移行の適用・倉庫の設定に触れない
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える

## 11. 報告欄（担当が追記）

（未記入）

END OF CARD
