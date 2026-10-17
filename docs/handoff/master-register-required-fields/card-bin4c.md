<!-- rules-ack: 607cd6e7 -->
# 実装カード 便4c — 共用商品の入れ忘れ件数と「調べたが無い」の印の件数を、毎週 Discord に知らせる（ADR-1020 定着）

> この文書は何か：ADR-1020 の定着点検（/tmp/CC報告ファイル/master-required-fields/governance/verdict.md の X4・X5）で、入れ忘れの件数（V1）を続けて測る仕組みが無く（台本は Mac の /tmp にだけある）、設計の「印の件数を PO に見せる」にも実行する仕組みが無いと分かった。本番の Celery の定期作業を1つ足し、毎週月曜 09:00（日本時間）に件数を管理者用の Discord に送る。0 件でも毎週送る（届かない＝止まった、と区別するため）。

- 設計: docs/handoff/master-register-required-fields/design.md（「維持の仕組み」:138-142 を本カードの形に書き直す。§4-4）
- PO 承認: PO 2026-10-17「y」（抜け道を塞ぎ、欠け5つを埋める便を設計から本番反映まで進める）
- 対象ADR: ADR-1020
- 状態: Opus 自己審査 APPROVE
- 危険便: いいえ（`migrations/`・`deploy.yml`・本番 `scripts/` を含まない。DB は読むだけ）。担当はマージしない
- 担当: 実装 Sonnet／審査・マージ・反映確認 Opus

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は ready で作る（下書きにしない）と明記 | ○（§7） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§8） |
| 4 | 1便1目的 | ○（件数の週次通知を1つ足す） |
| 5 | 起点と作業場所を明示 | ○（§7 手順1） |
| 6 | 書式は実例で示した | ○（§3 に完成形） |
| 7 | 合格基準を出力まで縛った | ○（§4） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§4-2） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実物から | ○（/tmp/CC報告ファイル/master-required-fields/bin4c/recon/） |
| 12 | 停止は本番影響のあるものに限る | ○（§5） |
| 13 | 委任文の定型4点 | ○（§9） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない | ○ |
| guards/03-file.md | 編集は Write/Edit | ○ |
| guards/04-worktree.md | 作業場所は `scripts/new-worktree.sh` | ○ |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh`。触る・削除するファイルは1行カンマ区切り | ○ |
| guards/08-vps.md | 本番には触らない | ○ |

## 受領確認

報告の冒頭へ「本報告はカード ADR-1020 便4c の実行結果である」と書くこと。

## 1. 事実（origin/main と本番の読み取り。生出力は /tmp/CC報告ファイル/master-required-fields/bin4c/recon/）
- 予定表: `backend/app/celery_app.py:62` の `beat_schedule`。作業モジュールの一覧は :21-43 の `include=[...]`。timezone は Asia/Tokyo（:50）
- 型にする作業: `backend/app/tasks/sa02_recon_monitor.py`。`_post_discord`（:31-45、環境変数 `ADMIN_NOTIFICATION_DISCORD_WEBHOOK`、空なら warning で送らない、`content[:1800]`）、Celery 入口（:137-148、`@shared_task(name=...)` が `asyncio.run(...)`、finally で `asyncio.run(engine.dispose())`）
- 型にする試験: `backend/tests/test_sa02_recon_monitor.py`（`patch("app.database.AsyncSessionLocal")`・`_post_discord` を AsyncMock に）。登録漏れは `backend/tests/test_celery_beat_registered.py:14-24` が検出する
- 本番の RLS（opus-rls.txt）: `public.products` と `public.product_blank_confirmations` は RLS あり。products の SELECT は `tenant_id IS NULL OR ...` なので共用の行はテナント設定なしで読める。印の表の SELECT は `USING (true)`。`public.product_search_keywords`・`public.product_exclude_keywords` は RLS なし。→ この作業はテナントの設定をせずに読む
- 本番の印の件数（2026-10-17）: exclude_keywords 2・mark 5・name_en 5・release_date 1
- 計り方の正本: /tmp/CC報告ファイル/master-required-fields/v1/v1.sh の SQL（9項目ごとの「空かつ印なし」）

## 2. 範囲
入れる: 作業1つ（`backend/app/tasks/master_required_fields_monitor.py`）・予定表への登録・試験・design.md の「維持の仕組み」の書き直し・このカードの写し
入れない: DB の変更・本番の scripts・画面・既存の作業

## 3. 実装

### 3-1. `backend/app/tasks/master_required_fields_monitor.py`（新規）

```python
"""ADR-1020 便4c: 共用商品の入れ忘れ件数と「調べたが無い」の印の件数を、毎週管理者用の Discord に送る。

0 件でも毎週送る（届かない＝止まった、と区別するため）。DB は読むだけ。
読む表のうち public.products は共用の行（tenant_id IS NULL）をテナント設定なしで読め、
印の表は SELECT が USING (true)、検索・除外ワードの表は RLS なし（2026-10-17 本番で確認）。
"""
import asyncio
import logging
import os

import httpx
from celery import shared_task
from sqlalchemy import text

logger = logging.getLogger(__name__)

_WEBHOOK_ENV = "ADMIN_NOTIFICATION_DISCORD_WEBHOOK"

# 便3（必須の検査）を本番に出した時刻。これ以降に作られた共用商品を「止める仕組みのあと」として数える
_SINCE = "2026-10-17 01:38:00+00"

_FIELDS = ("name", "name_en", "mark", "release_date", "search_keywords",
           "exclude_keywords", "work_id", "product_format_id", "product_category_id")

_COUNT_SQL = text(f"""
WITH p AS (
  SELECT * FROM public.products WHERE tenant_id IS NULL AND created_at >= :since
), c AS (
  SELECT product_id, field_code FROM public.product_blank_confirmations
)
SELECT
  count(*) AS new_rows,
  count(*) FILTER (WHERE coalesce(trim(name), '') = '') AS name,
  count(*) FILTER (WHERE coalesce(trim(name_en), '') = '' AND NOT EXISTS (SELECT 1 FROM c WHERE c.product_id = p.id AND c.field_code = 'name_en')) AS name_en,
  count(*) FILTER (WHERE coalesce(trim(mark), '') = '' AND NOT EXISTS (SELECT 1 FROM c WHERE c.product_id = p.id AND c.field_code = 'mark')) AS mark,
  count(*) FILTER (WHERE release_date IS NULL AND NOT EXISTS (SELECT 1 FROM c WHERE c.product_id = p.id AND c.field_code = 'release_date')) AS release_date,
  count(*) FILTER (WHERE NOT EXISTS (SELECT 1 FROM public.product_search_keywords k WHERE k.product_id = p.id AND trim(k.keyword) != '')) AS search_keywords,
  count(*) FILTER (WHERE NOT EXISTS (SELECT 1 FROM public.product_exclude_keywords k WHERE k.product_id = p.id AND trim(k.keyword) != '') AND NOT EXISTS (SELECT 1 FROM c WHERE c.product_id = p.id AND c.field_code = 'exclude_keywords')) AS exclude_keywords,
  count(*) FILTER (WHERE work_id IS NULL) AS work_id,
  count(*) FILTER (WHERE product_format_id IS NULL) AS product_format_id,
  count(*) FILTER (WHERE product_category_id IS NULL) AS product_category_id
FROM p
""")

_MARKS_SQL = text("SELECT field_code, count(*) FROM public.product_blank_confirmations GROUP BY field_code ORDER BY field_code")


async def _post_discord(content: str) -> None:
    url = (os.getenv(_WEBHOOK_ENV) or "").strip()
    if not url:
        logger.warning("%s is not set; skip master required fields report", _WEBHOOK_ENV)
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(url, json={"content": content[:1800], "username": "共用商品 必須項目 週次"})
        if res.status_code >= 400:
            logger.warning("master required fields report: discord status %s", res.status_code)
    except Exception as exc:  # noqa: BLE001
        logger.warning("master required fields report: discord error %s", type(exc).__name__)


def build_message(counts: dict, marks: list[tuple[str, int]]) -> str:
    ng = {f: int(counts.get(f) or 0) for f in _FIELDS}
    total_ng = sum(ng.values())
    head = "✅" if total_ng == 0 else "⚠️"
    lines = [
        f"{head} 共用商品の必須9項目（ADR-1020）: 便3反映後に作られた共用商品 {int(counts.get('new_rows') or 0)} 件",
        "空のまま・印なしの件数: " + " / ".join(f"{f} {n}" for f, n in ng.items()),
        "「調べたが無い」の印: " + (" / ".join(f"{code} {int(n)}" for code, n in marks) if marks else "0 件"),
    ]
    return "\n".join(lines)


async def _run_report() -> dict:
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        row = (await db.execute(_COUNT_SQL, {"since": _SINCE})).mappings().one()
        marks = [(r[0], r[1]) for r in (await db.execute(_MARKS_SQL)).all()]
    counts = dict(row)
    await _post_discord(build_message(counts, marks))
    return {"counts": counts, "marks": marks}


@shared_task(name="app.tasks.master_required_fields_monitor.report_master_required_fields")
def report_master_required_fields() -> dict:
    from app.database import engine

    try:
        return asyncio.run(_run_report())
    finally:
        asyncio.run(engine.dispose())
```

- `_SINCE` を `:since` に渡すとき、PostgreSQL の型で失敗したら（asyncpg が文字列を timestamptz にしない等）、`datetime(2026, 10, 17, 1, 38, tzinfo=timezone.utc)` を渡す形に直し、報告に書く
- `app.database` の import の置き方・`engine` の名前は sa02_recon_monitor.py の実物に合わせる（違えば実物どおりにし、報告に書く）

### 3-2. `backend/app/celery_app.py`
- `include=[...]` に `"app.tasks.master_required_fields_monitor",` を足す
- `beat_schedule` の末尾（`refresh-viewer-inventory` の後）に:

```python
    # ADR-1020 便4c: 共用商品の必須9項目の入れ忘れ件数と印の件数を毎週月曜 09:00 に管理者用 Discord へ
    "report-master-required-fields-weekly": {
        "task": "app.tasks.master_required_fields_monitor.report_master_required_fields",
        "schedule": crontab(hour=9, minute=0, day_of_week=1),
    },
```

### 3-3. 試験 `backend/tests/test_master_required_fields_monitor.py`（新規）

| # | 試験 | 期待 |
|---|---|---|
| 1 | `build_message` に全項目 0・印 [("mark", 5), ("name_en", 5)] | 1行目が ✅ で始まり「0 件」でなく「共用商品 N 件」を含む。3行目に `mark 5` と `name_en 5` |
| 2 | `build_message` に `work_id` 2 | 1行目が ⚠️ で始まり、2行目に `work_id 2` |
| 3 | `build_message` に印 [] | 3行目に「0 件」 |
| 4 | `_run_report` を `patch("app.database.AsyncSessionLocal")`・`_post_discord` を AsyncMock で実行（sa02 の試験の書き方を写す） | `_post_discord` が1回呼ばれ、文面の1行目に「ADR-1020」 |
| 5 | 予定表 | `celery_app.conf.beat_schedule["report-master-required-fields-weekly"]` の task 名が登録済みで、schedule が月曜 9:00 |
| 6 | （PG がある環境だけ。CI で印の試験と同時に走りデッドロックしたため、実装後に `backend/tests/test_product_blank_confirmations_pg.py` の末尾へ移した＝同じファイルは同じ作業員が順に流す）既存の `backend/tests/test_product_blank_confirmations_pg.py` の準備を写し、共用の行を2つ（1つは name_en 空・印なし、1つは name_en 空・印あり）を `created_at` 現在で作り、`_COUNT_SQL` を実行 | `name_en` が 1。PG が無ければ既存と同じ形で skip |

### 3-4. design.md の「維持の仕組み」（docs/handoff/master-register-required-fields/design.md:138-142）
- 「月1回、印の件数を PO に見せる」の行を、次の内容に置き換える（他の行は変えない。行番号が違えば「維持の仕組み」の節の該当行を探す）:
  `- 毎週月曜 09:00（日本時間）、本番の Celery の作業 report-master-required-fields-weekly（backend/app/tasks/master_required_fields_monitor.py）が、便3反映後に作られた共用商品の「空かつ印なし」の件数（9項目ごと）と「調べたが無い」の印の件数を管理者用 Discord に送る。0 件でも毎週送る。届かない週は作業が止まっている。⚠️ が出たら Opus が該当の商品を調べて PO に候補表を出す（ADR-1020 便4c）`

### 3-5. このカードの写しを `docs/handoff/master-register-required-fields/card-bin4c.md` に置く

## 4. 確かめ方
4-1. `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin4c/backend && python -m pytest -q tests/test_master_required_fields_monitor.py tests/test_celery_beat_registered.py tests/test_sa02_recon_monitor.py 2>&1 | tail -10`（PG の試験6が skip のときは既存の PG 試験の起動方法で走らせられるか試し、走ったか skip かを事実で書く）
4-2. `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin4c && grep -nE "^\s*(async )?def test_" backend/tests/test_master_required_fields_monitor.py | head -10` と `grep -n "master_required_fields_monitor" backend/app/celery_app.py | head -5`（include と beat の2か所）
4-3. `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin4c/backend && ruff check app/tasks/master_required_fields_monitor.py app/celery_app.py tests/test_master_required_fields_monitor.py 2>&1 | tail -5`
4-4. `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin4c && git diff origin/main...HEAD --stat | tail -8`（§2 のファイルだけ）

## 5. 分岐ごとの対処
- sa02_recon_monitor.py の形が §1 と違う → 実物を貼り、実物に合わせる。意味が変わるなら NEEDS_DECISION:
- 既存の試験が落ちる → 試験名と原文を貼り NEEDS_DECISION:（期待を勝手に変えない）
- 自動検査（husky・CI）が落ちる → 検査名と原文を貼る。迂回しない

## 6. 戻し方
この PR の revert（作業と予定表の登録が消える。DB は変えていない）

## 7. PR
手順1
    cd /Users/tanizawashingo/salesanchor && git fetch -q origin && bash scripts/new-worktree.sh release/master-register-required-fields-bin4c --claude 2>&1 | tail -3
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin4c && git status -sb | head -2 && git log -1 --oneline
期待する出力 origin/main の先頭から作られている（「Claude Code を起動しています」のあとのエラーは作業場所の作成と関係しないので無視してよい）
手順2 §3 を Write/Edit で実装し §4 を実行
手順3
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin4c && git add backend/app/tasks/master_required_fields_monitor.py backend/app/celery_app.py backend/tests/test_master_required_fields_monitor.py docs/handoff/master-register-required-fields && git status -s | head -10
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin4c && git commit -m "feat: ADR-1020便4c 共用商品の入れ忘れ件数と印の件数を毎週Discordへ"
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin4c && git push -q -u origin release/master-register-required-fields-bin4c && git log -1 --oneline && git log origin/release/master-register-required-fields-bin4c -1 --oneline
手順4 PR
- `gh auth status` で `shingo-cc` を確かめる
- 本文は Write で /private/tmp/claude-501/bin4c-pr-body.md に作り、作業場所に cd して `bash scripts/dev/validate-pr-body.sh < /private/tmp/claude-501/bin4c-pr-body.md` が exit 0（timeout を長めに）
- `bash scripts/gh-pr-create-safe.sh --base main --title "feat: ADR-1020便4c 共用商品の入れ忘れ件数と印の件数を毎週Discordへ" --body-file /private/tmp/claude-501/bin4c-pr-body.md`。ready で作る。マージしない
- 本文は PR テンプレートに沿い、`### 標準ワークフロー確認` に recon（docs/handoff/master-register-required-fields/recon.md）・設計（docs/handoff/master-register-required-fields/design.md）・このカード・ADR-1020。PO承認: 「PO 2026-10-17『y』（定着点検の抜け道1・欠け5を設計から本番反映まで）」
- `### GO記録` の見出しと空欄（`- GO発行者:`・`- 日時:`・`- GO原文:`・`- 対象 HEAD:`）
- `触るファイル:` と `削除するファイル:` は1行・カンマ区切り・バッククォートなし・注記なし。削除するファイル: は既存行を変えたファイル（新規を除く）
- 末尾に `🤖 Generated with [Claude Code](https://claude.com/claude-code)`

## 8. 報告
1行目 DONE／BLOCKED: 理由／NEEDS_DECISION: 内容。受領文／§4 の出力の要点／PR URL／生出力のパス（/tmp/CC報告ファイル/master-required-fields/bin4c/impl/）／§3-1 で実物に合わせた点。停止時は手順番号・最後のコマンド・理由の原文。

## 9. 委任の定型
- sleep しない
- ファイルの作成と編集は Write/Edit
- PR の前に validate-pr-body.sh で exit 0
- フックや自動判定に止められたら言い換えず報告して終える（登録ルールのフックも同じ。ack の行は書かない）

END OF CARD
