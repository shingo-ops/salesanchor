# 実装カード celery-unregistered-tasks 便2 — 未登録の定期作業 2 つを登録し、まとめ翻訳を外す

> この文書は何か：設計 docs/handoff/celery-unregistered-tasks/design.md の便2（C1〜C9）の作業指示書です。写しシートの書き出し（tcg_mirror）と毎朝の件数の突き合わせ（sa02）を Celery に登録し、成果のない 15 分ごとのまとめ翻訳を外し、買取価格の取得に後片付けを足し、beat に書いた名前が登録済みかを確かめるテストを足します。本番への反映は通常の deploy（main へのマージ）で、このカードの担当は PR を作るところまでです。

- 設計: docs/handoff/celery-unregistered-tasks/design.md §3 C1〜C9・受け入れ基準 K0〜K7
- 事実確認: docs/handoff/celery-unregistered-tasks/recon.md（§1〜§6）。生出力は /tmp/CC報告ファイル/ai-ops-celery-fix/（A_〜E_*.txt・card/grep1.txt）
- 対象ADR: ADR-1012（AI保守運用 段階1。U11・U13 の出どころ）・ADR-110（翻訳）
- 状態: PO 実装承認済み。PO 原文「y」（2026-10-16。「実装（工事）に進めてよいか」への回答）
- 前提: このカードを含む文書 PR（release/celery-unregistered-tasks-design）が main にマージされていること（§10 で確かめる）
- 危険便: いいえ（`migrations/`・`.github/workflows/deploy.yml`・本番 `scripts/` を触らない。ADR-136 の危険 PR に当たらない）
- 担当: 実装 Sonnet／コード審査・GO 記録・マージ・反映確認 Opus

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は ready で作る（Draft にしない）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（beat に書いた定期作業を、登録と後片付けで正しく動く状態にそろえる。C1〜C9 は設計で 1 便にまとめた理由がある（設計 §4 案 D）） |
| 5 | 既存ブランチへの追記ではない（新規ブランチ） | ○（release/celery-unregistered-tasks-fix） |
| 6 | 書式は実例で示した | ○（§4 に変更前後のコード） |
| 7 | 合格基準を出力まで縛った | ○（§5） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-1 で名前の一覧と件数を対で出す） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実測から | ○（§2。2026-10-16 Opus が origin/main aef290b1 で読んだ行番号） |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§12） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない | ○（§5・§10・§12） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○ |
| guards/04-worktree.md | new-worktree.sh の出力をパイプに通さず、実在は `ls -1d` と `git worktree list` で確かめる | ○（§10） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh` で作る。触るファイル・削除するファイルは同一行カンマ区切り | ○（§10） |
| guards/10-executor.md | カードに無い確認を補わない。プレースホルダがあれば着手前に止まる | ○ |
| guards/11-lint.md | `rm`・`timeout`・上限の無い一覧・危険語を本文に入れない | ○ |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード celery-unregistered-tasks 便2 の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. C1: `backend/app/tasks/tcg_mirror.py` の `run_tcg_mirror_write` に登録のデコレータと後片付け
2. C2: `backend/app/tasks/sa02_recon_monitor.py` の `run_sa02_daily_recon` に登録のデコレータと後片付け
3. C3: `backend/app/celery_app.py` の beat から translate-pending-messages の 5 行（コメント 1 行＋設定 4 行）を消す
4. C4: `backend/app/tasks/translation.py` のまとめ翻訳（タスク・本体・件数上限・使わなくなる import）を消す
5. C5: `backend/app/services/message_translator.py` の 2 関数（§4-5 の再確認で呼び出しが 0 のときだけ）を消す
6. C6: まとめ翻訳を検査するテスト 2 本を消す
7. C7: `backend/app/tasks/buyback_scraper.py` の `fetch_all_buyback_prices` に後片付け
8. C8: 新規 `backend/tests/test_celery_beat_registered.py`
9. C9: `docs/runbooks/alerts.md` の CeleryTaskFailuresHigh の注記 1 行

入れない:
- 即時翻訳（`translate_inbound_message`・`_run_translate_inbound_message`）と健全性チェック（`check_translation_health_task`・`_run_health_check`）の中身
- 写しシートの書く中身・書き込み先（`MIRROR_SPREADSHEET_ID`）、突き合わせの中身・送り先、買取価格の取得の処理内容
- `message_translations` テーブル・migration・監視ルール（`monitoring/`）・deploy・secrets・`.env`
- 予算の判定（`backend/app/services/message_translator.py` の BudgetExceededError まわり）
- `backend/tests/test_sa02_recon_monitor.py`・`backend/tests/test_tcg_mirror.py`（変えずに通ることを §5 で確かめる）

## 2. 前提の事実（2026-10-16 Opus が origin/main aef290b1 で読んだもの）

| # | 事実 | 出典 |
|---|---|---|
| F1 | `run_tcg_mirror_write` にデコレータが無い。beat は `app.tasks.tcg_mirror.run_tcg_mirror_write` を呼ぶ | `backend/app/tasks/tcg_mirror.py:295`・`backend/app/celery_app.py:155-158` |
| F2 | `run_sa02_daily_recon` にデコレータが無い。beat は `app.tasks.sa02_recon_monitor.run_sa02_daily_recon` を呼ぶ | `backend/app/tasks/sa02_recon_monitor.py:136-140`・`backend/app/celery_app.py:130-133` |
| F3 | 登録の既存の型は `from celery import shared_task` と `@shared_task(name="...")` | `backend/app/tasks/buyback_scraper.py:16`・`:41` |
| F4 | 後片付けの既存の型は `from app.database import engine` と `finally: asyncio.run(engine.dispose())` | `backend/app/tasks/translation.py:45`・`:57-60` |
| F5 | tcg_mirror・sa02・買取価格の通知確認は、共用の `AsyncSessionLocal`（共用 engine）を使い、後片付けをしない | `backend/app/tasks/tcg_mirror.py:249`・`backend/app/tasks/sa02_recon_monitor.py:48`・`backend/app/tasks/buyback_scraper.py:54`（`alert_checker` 経由） |
| F6 | まとめ翻訳は beat `backend/app/celery_app.py:117-121`、タスク `backend/app/tasks/translation.py:123-148`、本体 `:151-257`、件数上限 `:20-21` | 各ファイル |
| F7 | `reset_tenant_context` と `LLMConfigError`・`LLMParseError` は、`backend/app/tasks/translation.py` の中では `_run_batch` だけが使う（`:14`・`:16` の import、`:236`・`:249` の使用） | card/grep1.txt |
| F8 | `get_required_inbound_targets`（`backend/app/services/message_translator.py:154`）と `get_existing_inbound_translation_targets`（`:195`）を呼ぶのは、tests を除くと `_run_batch` だけ | card/grep1.txt |
| F9 | まとめ翻訳を検査するテストは `backend/tests/test_translation_task_context.py:18` の `test_translate_pending_messages_sets_and_resets_tenant_context` と `backend/tests/test_ticket_channel_translation.py:195` の `test_batch_skips_completed_messages_and_translates_only_missing`（ファイルの最後の関数。230 行まで）。同じファイルのほかのテストは即時翻訳のもの | 各ファイル |
| F10 | `backend/tests/test_tcg_mirror.py:109-116` は `run_tcg_mirror_write()` を直接呼び、鍵が無いときのスキップを確かめる | 同ファイル |
| F11 | Celery 5.6.3 で、`Celery(include=[...])` の一覧は `celery_app.conf.include` で読め、`importlib.import_module` で読み込むと `@shared_task(name=...)` の名前が `celery_app.tasks` に入り、デコレータの無い関数は入らない。デコレータを付けた関数を直接呼ぶと、元の関数がそのまま動く | 2026-10-16 Opus が手元の Celery 5.6.3 で試した（Context7 は月の上限で使えなかった）。requirements は `backend/requirements.txt:17` の `celery[redis]>=5.4.0` |

## 3. 触るファイル（これ以外は触らない）

- 変更: `backend/app/tasks/tcg_mirror.py`
- 変更: `backend/app/tasks/sa02_recon_monitor.py`
- 変更: `backend/app/celery_app.py`
- 変更: `backend/app/tasks/translation.py`
- 変更: `backend/app/services/message_translator.py`（§4-5 で呼び出し 0 のときだけ）
- 変更: `backend/app/tasks/buyback_scraper.py`
- 変更: `backend/tests/test_translation_task_context.py`
- 変更: `backend/tests/test_ticket_channel_translation.py`
- 新規: `backend/tests/test_celery_beat_registered.py`
- 変更: `docs/runbooks/alerts.md`
- 変更: `docs/handoff/celery-unregistered-tasks/card-impl.md`（このカード。§13 報告欄の追記のみ）

## 4. 作り方（順番を守る。4-1 のテストを最初に書く）

4-1. 新規 `backend/tests/test_celery_beat_registered.py`（完成形）:

```python
"""beat_schedule に書いた task 名が、すべて Celery に登録されていることを確かめる。

登録されていない名前を beat が送ると、worker は "unregistered task" で捨て、
その定期作業は一度も動かない（2026-10 に tcg_mirror と sa02 で実際に起きた。
docs/handoff/celery-unregistered-tasks/recon.md）。
"""
from __future__ import annotations

import importlib

from app.celery_app import celery_app


def test_every_beat_task_is_registered() -> None:
    for module_name in celery_app.conf.include:
        importlib.import_module(module_name)

    registered = set(celery_app.tasks.keys())
    missing = sorted(
        f"{entry_name} -> {entry['task']}"
        for entry_name, entry in celery_app.conf.beat_schedule.items()
        if entry["task"] not in registered
    )
    assert missing == [], f"beat_schedule に未登録の task があります: {missing}"
```

- 書いたら §5-1 を実行し、修正前に落ちることを確かめる（K0 の前半）。期待: 落ちて、`missing` に `sa02-daily-recon -> app.tasks.sa02_recon_monitor.run_sa02_daily_recon` と `tcg-mirror-daily-write -> app.tasks.tcg_mirror.run_tcg_mirror_write` の 2 件だけが出る。ほかの名前が出たら止まる（§6）。

4-2. C1 `backend/app/tasks/tcg_mirror.py`:
- import の段（`:19-22`）の `from typing import Any` の後に、空行を 1 つ置いて `from celery import shared_task` を足す（ruff の import の並びの指摘があれば、その指示どおりに並べ直す）。
- `:295-324` を次に置き換える。変更前:

```python
def run_tcg_mirror_write() -> None:
    """
    Celery タスクのエントリポイント。
    TCG_SHEETS_SA_KEY_FILE が未設定の場合はスキップ（本番以外の環境で安全に無視）。
    シート自動作成は一切行わない。
    """
    import asyncio

    key_file = os.getenv("TCG_SHEETS_SA_KEY_FILE", "").strip()
    if not key_file:
        logger.info(
            "[tcg_mirror] TCG_SHEETS_SA_KEY_FILE 未設定 — スキップ"
        )
        return

    logger.info("[tcg_mirror] 書き出し開始: spreadsheetId=%s", MIRROR_SPREADSHEET_ID)
    try:
        stats = asyncio.run(_write_mirror_async())
        logger.info(
            ...（:314-321 の 8 行はそのまま）
        )
    except Exception as exc:
        logger.error("[tcg_mirror] 書き出し失敗: %s", exc, exc_info=True)
        raise
```

変更後（`:303-308` のスキップと、`:311-324` の try/except の中身は 1 字も変えない。足すのはデコレータ、`from app.database import engine`、外側の try/finally だけ）:

```python
@shared_task(name="app.tasks.tcg_mirror.run_tcg_mirror_write")
def run_tcg_mirror_write() -> None:
    """
    Celery タスクのエントリポイント。
    TCG_SHEETS_SA_KEY_FILE が未設定の場合はスキップ（本番以外の環境で安全に無視）。
    シート自動作成は一切行わない。
    """
    import asyncio

    from app.database import engine

    key_file = os.getenv("TCG_SHEETS_SA_KEY_FILE", "").strip()
    if not key_file:
        logger.info(
            "[tcg_mirror] TCG_SHEETS_SA_KEY_FILE 未設定 — スキップ"
        )
        return

    logger.info("[tcg_mirror] 書き出し開始: spreadsheetId=%s", MIRROR_SPREADSHEET_ID)
    try:
        try:
            stats = asyncio.run(_write_mirror_async())
            logger.info(
                ...（変更前と同じ 8 行。字下げを 4 つ深くするだけ）
            )
        except Exception as exc:
            logger.error("[tcg_mirror] 書き出し失敗: %s", exc, exc_info=True)
            raise
    finally:
        # 共用 engine の接続を捨てる（Celery worker の
        # "Future attached to a different loop" を避ける。translation.py と同じ）。
        asyncio.run(engine.dispose())
```

- 上の `...` は説明のための省略で、ファイルには変更前の 8 行をそのまま書く。スキップの経路（鍵が無い）では `engine.dispose()` を呼ばない（`backend/tests/test_tcg_mirror.py:109-116` が DB に触れない前提のため）。

4-3. C2 `backend/app/tasks/sa02_recon_monitor.py`:
- import の段（`:14-19`）の `import httpx` の後に `from celery import shared_task` を足す（並びは ruff の指示に従う）。
- `:136-140` を置き換える。変更前:

```python
def run_sa02_daily_recon() -> dict:
    """Celery タスクから呼ばれるエントリポイント（同期ラッパー）。"""
    import asyncio

    return asyncio.run(_run_daily_recon())
```

変更後:

```python
@shared_task(name="app.tasks.sa02_recon_monitor.run_sa02_daily_recon")
def run_sa02_daily_recon() -> dict:
    """Celery タスクから呼ばれるエントリポイント（同期ラッパー）。"""
    import asyncio

    from app.database import engine

    try:
        return asyncio.run(_run_daily_recon())
    finally:
        # 共用 engine の接続を捨てる（translation.py と同じ。"attached to a different loop" 対策）。
        asyncio.run(engine.dispose())
```

4-4. C3・C4（まとめ翻訳を外す）:
- `backend/app/celery_app.py:117-121` の 5 行（`# ADR-110: 未翻訳受信メッセージのバッチ翻訳（15分ごと）` から `},` まで）を消す。`:122` の `# ADR-110: 翻訳健全性チェック` 以降は変えない。
- `backend/app/tasks/translation.py`:
  - `:7` の `  - 未処理受信メッセージ（translated_text = NULL）を定期バッチ翻訳` を `  - 受信メッセージの単発翻訳（定期バッチ翻訳は 2026-10 に廃止。docs/handoff/celery-unregistered-tasks/design.md）` に置き換える。
  - `:14` を `from app.auth.dependencies import clear_tenant_context, set_tenant_context` にする（`reset_tenant_context` を外す）。
  - `:16` の `from app.services.llm_errors import LLMConfigError, LLMParseError` を消す。
  - `:20-22`（`# 1 回のバッチで処理する最大件数`・`_BATCH_SIZE = 20`・その後の空行 1 つ）を消す。
  - `:123-258`（`translate_pending_messages` のデコレータから `_run_batch` の `return` と、その後の空行 2 つのうち 1 つまで）を消し、`check_translation_health_task` のデコレータの前の空行が 2 つになるようにする。
  - `:273` のコメント `# translate_pending_messages と同様の EventLoop クラッシュ対策（recon.md A-1）。` を `# Celery fork-pool の EventLoop 再利用で起きる "Future attached to a different loop" 対策（recon.md A-1）。` に置き換える。
  - 消した後、`_run_translate_inbound_message`（変更前 `:63-120`）と `_run_health_check`（変更前 `:277-318`）の中身が 1 字も変わっていないことを §5-4 で確かめる。

4-5. C5（2 関数の削除。先に再確認する）:
- §5-2 の `git grep` を実行し、`get_required_inbound_targets` と `get_existing_inbound_translation_targets` の出現を名前ごとに数える。
- 分岐 A（定義の 1 行だけが残る）: `backend/app/services/message_translator.py` の `get_required_inbound_targets`（`:154` から、次の `# ----` の区切りの前まで）と `get_existing_inbound_translation_targets`（`:195` から、次の `async def _save_translation` の前まで）を消す。前後の空行は、関数の間が 2 行になるように整える。
- 分岐 B（tests 以外の呼び出しが 1 つでも残る）: その関数は消さない。消さなかった名前と、残った呼び出しの行を報告に書く。

4-6. C6（テストの削除）:
- `backend/tests/test_translation_task_context.py`: `:17` の `@pytest.mark.asyncio`（付いていれば）から `test_translate_pending_messages_sets_and_resets_tenant_context` の終わり（`:95` の次のテストのデコレータの前まで）を消す。冒頭の docstring の `  - translate_pending_messages が各 tenant ごとに context を設定する` の 1 行を消す。使わなくなった import があれば ruff の指示どおりに外す。`test_translate_inbound_message_sets_and_clears_tenant_context` は変えない。
- `backend/tests/test_ticket_channel_translation.py`: `:9` を `from app.tasks.translation import _run_translate_inbound_message, translate_inbound_message` にする。`:194` の `@pytest.mark.asyncio` から最後（`:230`）までの `test_batch_skips_completed_messages_and_translates_only_missing` を消す。使わなくなった import があれば ruff の指示どおりに外す。ほかの 4 本は変えない。

4-7. C7 `backend/app/tasks/buyback_scraper.py:41-68`。変更前の関数本体（`:49-68`）を、そのまま 1 段深くして try/finally で包む。変更後（本体の 20 行は字下げ以外を変えない）:

```python
@shared_task(name="buyback.fetch_all_prices")
def fetch_all_buyback_prices() -> None:
    """全店舗の買取価格を取得して DB に保存する。

    シンソク → 買取ホムラ の順に実行する。
    いずれかが失敗しても他方は続行する（各サービス内部でエラーハンドリング済み）。
    価格取得完了後、アラートチェックを実行して閾値超過時に Discord 通知を送る。
    """
    from app.database import engine

    try:
        logger.info("[buyback_scraper] 全店舗価格取得タスク開始")
        asyncio.run(_fetch_all())
        ...（変更前 :51-68 と同じ。字下げを 4 つ深くするだけ）
    finally:
        # アラートチェックが共用 engine（AsyncSessionLocal）を使うため、接続を捨てる。
        # 捨てないと、同じ worker で次に動く作業が "attached to a different loop" で落ちる
        # （docs/handoff/celery-unregistered-tasks/recon.md §4）。
        asyncio.run(engine.dispose())
```

- 自前で作る engine（`_build_async_session_factory`、`:28-38`）には触らない。`asyncio` はファイルの先頭（`:12`）で import 済みなので、関数の中で import しない。

4-8. C9 `docs/runbooks/alerts.md` の CeleryTaskFailuresHigh の節の注記（2026-10-16 時点 `:192`。`- 注記：2026-10-15 時点で translate_pending_messages が` で始まる 1 行）を次の 1 行に置き換える:

```markdown
- 注記：2026-10-15 まで translate_pending_messages が毎日 2〜3 回失敗していた。原因は買取価格の取得（buyback.fetch_all_prices）が共用 engine を片付けず、同じ worker で次に動いた作業が "attached to a different loop" で落ちていたこと。2026-10 にまとめ翻訳を廃止し、買取価格の取得に後片付けを足した（docs/handoff/celery-unregistered-tasks/design.md）。
```

## 5. 確かめ方（担当が実行し、出力を報告に貼る）

生出力はすべて /tmp/CC報告ファイル/celery-unregistered-tasks-fix/ に保存する。テストと lint は、backend の CI と同じ方法で実行する（実行方法は `.github/workflows/test.yml` の backend の pytest と ruff の段を読んで合わせる。読んだ行を報告に書く）。

5-1. 4-1 を書いた直後（4-2 より前）に `backend/tests/test_celery_beat_registered.py` だけを実行し、出力全文と終了コードを保存する（期待: 1 failed。`missing` に §4-1 の 2 件だけ）。4-2〜4-7 の後に、もう一度同じテストを実行する（期待: 1 passed）。この 2 つが K0。
5-2. `cd /Users/tanizawashingo/worktrees/salesanchor/release-celery-unregistered-tasks-fix && git grep -n -e get_required_inbound_targets -e get_existing_inbound_translation_targets -e translate_pending_messages -e _run_batch -e _BATCH_SIZE -- backend` を 4-5 の前に 1 回、全部の変更の後に 1 回実行する。後の 1 回の期待: `translate_pending_messages`・`_run_batch` は 0 行。`_BATCH_SIZE` は `backend/app/tasks/maintenance.py` と `backend/tests/test_data_deletion_helpers.py` の行だけ（別の定数で、触らない）。2 関数は分岐 A なら 0 行。
5-3. `cd /Users/tanizawashingo/worktrees/salesanchor/release-celery-unregistered-tasks-fix && python3 -c "from app.celery_app import celery_app; print(sorted(celery_app.conf.beat_schedule))"` を backend の CI と同じ場所・環境で実行する（期待: 19 個。`translate-pending-messages` が無い。`sa02-daily-recon`・`tcg-mirror-daily-write` はある）。名前の一覧と個数を対で貼る。
5-4. `cd /Users/tanizawashingo/worktrees/salesanchor/release-celery-unregistered-tasks-fix && git diff origin/main -- backend/app/tasks/translation.py` の全文を保存し、`_run_translate_inbound_message` と `_run_health_check` の中に `+` と `-` の行が無いことを書く。
5-5. 次のテストを実行し、件数の行を貼る（期待: 全件 pass）: `backend/tests/test_celery_beat_registered.py`・`backend/tests/test_tcg_mirror.py`・`backend/tests/test_sa02_recon_monitor.py`・`backend/tests/test_translation_task_context.py`・`backend/tests/test_ticket_channel_translation.py`。あわせて `git grep -l -e buyback -e translation -- backend/tests` で出たテストファイルも実行する（一覧と件数を対で貼る）。
5-6. backend の lint（CI と同じもの。ruff 等）を変更したファイルに対して実行し、終了コード 0 を貼る。
5-7. わざと壊して落ちることを確かめる: `backend/app/tasks/sa02_recon_monitor.py` のデコレータの 1 行だけを一時的に消して 5-1 のテストを実行し、1 failed と `missing` に sa02 の 1 件だけが出ることを貼る。確かめたら `git checkout -- backend/app/tasks/sa02_recon_monitor.py` ではなく Edit で元に戻し（ほかの変更を消さないため）、5-1 のテストが 1 passed に戻ることを貼る。
5-8. backend のテスト全体を CI と同じ方法で実行し、最後の要約行を貼る（期待: failed 0。変更前から落ちているものがあれば、origin/main でも同じく落ちることを同じ方法で確かめて、名前を対で書く）。
5-9. `cd /Users/tanizawashingo/worktrees/salesanchor/release-celery-unregistered-tasks-fix && git diff origin/main --stat` が §3 のファイルであること（§13 の追記前なら 9 または 10 ファイル。分岐 B で message_translator.py を変えなければ 9）。

## 6. 分岐ごとの対処

- 5-1 の修正前の実行で、`missing` に §4-1 の 2 件以外が出る → 作業を止める（NEEDS_DECISION:。出た名前を貼る）。設計の前提（未登録はこの 2 件だけ）が変わったため。
- 5-1 の修正前の実行が、落ちずに通る → 作業を止める（NEEDS_DECISION:）。
- 4-5 で分岐 B → 消さずに続ける（記録のみ）。
- 5-5・5-8 で、触っていないテストが新しく落ちる → 落ちたテストの名前と出力の最後の 30 行を貼って止まる（BLOCKED:）。テストを書き換えて合わせることはしない。
- 5-6 の lint の指摘 → 指示どおりに直してやり直す（記録のみ）。
- 前提の文書 PR がマージされていない → 作業を始めずに止まる（BLOCKED:）。

## 7. 受け入れ基準（設計 K0〜K7 のうち、この便で確かめるもの）

| 基準 | 検証方法 |
|---|---|
| K0 C8 のテストが、修正前は×、修正後は○ | §5-1・§5-7 |
| K6 beat_schedule に translate-pending-messages が無い | §5-2・§5-3 |
| K7 CI がすべて緑 | PR の checks（Opus が見る） |
| 即時翻訳と健全性チェックの中身が変わっていない | §5-4 |
| K1〜K5 | 反映後に Opus が観測する（設計の便3）。この便では確かめない |

## 8. 本番への反映

担当は行わない。Opus がコード審査と GO 記録の後に main にマージし、通常の deploy で反映する。反映後の観測（K1〜K5）は Opus が行う。反映前に Opus が K4 の基準値（反映前 7 日の `message_translations` の新規件数）を、PO 実行の読み取りで取る。

## 9. 戻し方

- この PR の revert を main にマージし、通常の deploy で戻す。DB と設定の変更は無いため、ほかの戻し作業は無い。
- 戻すと、写しシートと突き合わせはまた動かなくなり、まとめ翻訳が 15 分ごとにまた動く（成果は無いが害も無い。反映前と同じ状態）。

## 10. PR

- 作業場所: 文書 PR が main にマージされたことを `cd /Users/tanizawashingo/salesanchor && gh pr list --state merged --head release/celery-unregistered-tasks-design --limit 5 --json number,state` で確かめてから（合格は 1 件で state が MERGED。`[]` なら作業を始めずに BLOCKED:）、`cd /Users/tanizawashingo/salesanchor && git fetch origin && bash scripts/new-worktree.sh release/celery-unregistered-tasks-fix --claude`（origin/main 起点）。出力はパイプに通さない。最後に「Input must be provided」という表示が出て exit 1 になることがあるが、作業場所の作成とは無関係（2026-10-14・10-15 実測）。作成後に `cd /Users/tanizawashingo/salesanchor && ls -1d /Users/tanizawashingo/worktrees/salesanchor/release-celery-unregistered-tasks-fix && git worktree list --porcelain | grep -c release-celery-unregistered-tasks-fix` で実在を確かめる。`cd /Users/tanizawashingo/worktrees/salesanchor/release-celery-unregistered-tasks-fix && ls docs/handoff/celery-unregistered-tasks/card-impl.md` でこのカードが実在することを確かめる。以後の作業はすべてその作業場所に `cd` してから行う
- commit の後に `git log -1 --oneline`、push の後に `git log origin/release/celery-unregistered-tasks-fix -1 --oneline` で実在を確かめる
- PR は `scripts/gh-pr-create-safe.sh` に、先に Write ツールで作った本文ファイルを `--body "$(cat 本文ファイル)"` の形で渡して作る。作成後に `gh pr list --head release/celery-unregistered-tasks-fix --limit 5 --json number,isDraft` で 1 件・isDraft が false を確かめる
- 作成前に `gh auth status` で `shingo-cc` 名義であることを確かめる
- PR は ready で作る（Draft にしない）。base は main。マージは Opus の GO 記録の後に限る（担当はマージしない）
- 本文は PR テンプレートに沿い、`### 標準ワークフロー確認` に recon（docs/handoff/celery-unregistered-tasks/recon.md）・設計（docs/handoff/celery-unregistered-tasks/design.md）・このカード・ADR-1012 を書く（`対象ADR:` は設計 doc から参照されている ADR だけを書く。書いた ADR が設計 doc に無いと関所が落ちる）。`区分:` は A（`backend/app/tasks/` を触る）。PO 承認は「PO 原文『y』（2026-10-16）」。`Opus 審査記録:` は「コード審査はこれから」と書く（審査の後に Opus が記録のパスに書き換える）。`設計仕様書（あるべき姿）:` は「対象外」。`触るファイル:` と `削除するファイル:` は 1 行・カンマ区切り・バッククォートなし。`削除するファイル:` には行を書き換えた既存ファイルを全部書く（`validate-pr-body.sh` の規則）
- 本文に「反映すると写しシートの [MIRROR] の 5 タブと READ ME が毎晩全部上書きされる。ほかのタブには触らない」の 1 行を書く（設計 §5 の事前周知）
- 本文に IP・URL の秘密・鍵のパス・認証ファイルの中身を書かない。実在しないパスをバッククォートで書かない
- 作成前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し exit 0 を確かめる（2 分以上かかるので、コマンドの待ち時間を長めにする）

## 11. 報告

- 宛先は Opus。完了報告の本文に: 冒頭の受領文／§5-1〜5-9 の出力（長いものは保存先のパス）／PR の URL／生出力のパス／分岐 A・B のどちらだったか／判断を要した点（事実のみ）
- 停止したときは: 停止した手順番号／最後に実行したコマンド／停止した理由の原文
- 1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか

## 12. 委任の定型

- sleep しない（CI の待ちは Opus が行う）
- ファイルの作成と編集は Write/Edit ツールで行う（ヒアドキュメントで書かない）
- PR を作る前に `scripts/dev/validate-pr-body.sh` で exit 0 を確かめる
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える

## 13. 報告欄（担当が追記）

本報告はカード celery-unregistered-tasks 便2 の実行結果である。

- 分岐: C5 は分岐 A（get_required_inbound_targets・get_existing_inbound_translation_targets は、まとめ翻訳の削除後に定義の行だけが残るため 2 関数とも削除）。根拠: /tmp/CC報告ファイル/celery-unregistered-tasks-fix/grep_before.txt・grep_after.txt
- K0: 修正前は 1 failed（missing は sa02 と tcg_mirror の 2 件だけ）、修正後は 1 passed。生出力: /tmp/CC報告ファイル/celery-unregistered-tasks-fix/k0_before.txt・k0_after.txt
- §5-7: デコレータを一時的に外すと 1 failed（missing は sa02 の 1 件だけ）、戻すと 1 passed。生出力: k57_broken.txt・k57_restored.txt
- beat: 19 件、translate-pending-messages なし（beat.txt）
- 判断を要した点: test_translation_task_context.py は ruff の F401・F811 の指示で未使用の `call` の import 2 つを外した。PR 本文の `対象ADR:` は、設計 doc が参照している ADR-136 だけを書いた（ADR-1012 は対象ADR行の外に記載）

END OF CARD
