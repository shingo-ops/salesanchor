# 実装カード celery-unregistered-tasks 便2-追補 — 写しシートの問い合わせ 2 つの誤りを直す

> この文書は何か：#4344 で登録した写しシートの書き出し（tcg_mirror）が、2026-10-16 02:30 JST の初回の実行で失敗しました。このカードは、その失敗の原因になっている問い合わせ 2 つを直すための作業指示書です。本番への反映は通常の deploy（main へのマージ）で行います。このカードの担当は、PR を作るところまでです。

- 設計: docs/handoff/celery-unregistered-tasks/design.md（C1「写しシートを登録して毎晩動かす」と受け入れ基準 K2「READ ME の最終更新が毎晩変わる」）。このカードは C1 を K2 まで届かせるための追補で、設計の目的・範囲は変えない
- 事実確認: docs/handoff/celery-unregistered-tasks/recon.md。この追補で取った生出力は /tmp/CC報告ファイル/celery-unregistered-tasks-fix/k2/（Loki のログ）と /tmp/CC報告ファイル/celery-unregistered-tasks-fix/k2/explain/result.txt（本番 DB の EXPLAIN。PO が 2026-10-16 05:42 JST に読み取りだけで実行）
- 対象ADR: ADR-1012（AI保守運用 段階1。U11 の出どころ）
- 状態: PO の実装承認済み。PO 原文は「y」（2026-10-16。「写しシートと sa02 を直す」「実装（工事）に進めてよいか」への回答）。この追補は承認された C1 の範囲の中の修理で、Opus が管理者として発行する（PO 10/15 の委任「設計からずれる時だけ PO へ相談」）
- 危険便: いいえ。`migrations/`・`.github/workflows/deploy.yml`・本番の `scripts/` を触らないため、ADR-136 の危険 PR に当たらない
- 担当: 実装は Sonnet。コード審査・GO 記録・マージ・反映確認は Opus

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は ready で作る（Draft にしない）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（写しシートの書き出しが初回に落ちた原因の問い合わせ 2 つを直す。後片付け（engine.dispose）は変えない＝§1） |
| 5 | 既存ブランチへの追記ではない（新規ブランチ） | ○（release/fix-tcg-mirror-sql。Opus が 2026-10-16 に origin/main 2bd773fcd から作成済み） |
| 6 | 書式は実例で示した | ○（§4 に変更前後のコード） |
| 7 | 合格基準を出力まで縛った | ○（§5） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-4） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実測から | ○（§2。本番 EXPLAIN と Loki の実測） |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§12） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない | ○（§5・§10・§12） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○ |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh` で作る。触るファイル・削除するファイルは同一行カンマ区切り | ○（§10） |
| guards/10-executor.md | カードに無い確認を補わない | ○ |
| guards/11-lint.md | `rm`・`timeout`・上限の無い一覧・危険語を本文に入れない | ○ |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード celery-unregistered-tasks 便2-追補 の実行結果である」と書くこと。

## 1. 範囲

- 直すもの:
  - `_fetch_keywords` の問い合わせ。`UNION ALL` の前に `ORDER BY` があって、構文の誤りになっている
  - `_fetch_suppliers` の問い合わせ。表に無い列 `sc.channel_type`・`sc.channel_identifier` を読んでいる
- テスト 1 本を足す（§4-3）
- 直さないもの:
  - `run_tcg_mirror_write` の後片付け（`asyncio.run(engine.dispose())`）。初回の失敗の直後に `attached to a different loop` が 1 件出たが、変えない。理由は、変えずに次の晩の成功時にも出るかを測るため（変更は一度に 1 つ）。sa02・買取価格の取得と同じ書き方で、設計 K5 で観測中
  - ほかの 3 つの問い合わせ（`_fetch_products`・`_fetch_supplier_summary`・`_fetch_db_structure`）。本番の EXPLAIN で誤り 0 だった（§2）
  - シートの見出し（`headers`）。今の名前のままにする（読み手の GAS が見出しの名前で列を探すため）
  - docstring の「AM 02:00 JST」の記述（実際の実行は 02:30。動作に関係しないので触らない）

## 2. 前提の事実（2026-10-16 Opus が確認したもの）

| # | 事実 | 出典 |
|---|---|---|
| F1 | 02:30 JST の初回の実行は、`[tcg_mirror] 書き出し失敗: ... syntax error at or near "UNION"` で終わった。スタックの場所は `tcg_mirror.py` の 318 → 259 → 140（`_fetch_keywords`）。`書き出し完了` の行は 0 件 | /tmp/CC報告ファイル/celery-unregistered-tasks-fix/k2/tcg.txt・kakidashi.txt |
| F2 | 失敗の直後に、同じ worker で `AsyncEngine.dispose()` が `attached to a different loop` を 1 件出した | /tmp/CC報告ファイル/celery-unregistered-tasks-fix/k2/loop.txt |
| F3 | `_fetch_keywords` は `backend/app/tasks/tcg_mirror.py:137-162`。:149 と :158 の 2 か所に `ORDER BY p.id, k.keyword` があり、:150 に `UNION ALL` がある | 同ファイル（origin/main 2bd773fcd） |
| F4 | `_fetch_suppliers` は `backend/app/tasks/tcg_mirror.py:165-182`。:172-173 で `sc.channel_type`・`sc.channel_identifier` を読み、:177 で `sc.channel_type` で並べている | 同ファイル |
| F5 | 本番の `public.supplier_channels` の列は `channel` と `external_id`（repo の定義）。本番の EXPLAIN で `ERROR: column sc.channel_type does not exist` が出た | `migrations/20260921_110000_pipeline_tables_public.sql:11-17`・/tmp/CC報告ファイル/celery-unregistered-tasks-fix/k2/explain/result.txt（Q3） |
| F6 | §4-1 の直した後の keywords の問い合わせは、本番の EXPLAIN で通った。件数は search 3100・exclude 1168 | 同 result.txt（Q2b・Q2c） |
| F7 | products・supplier_summary・db_structure の 3 つは、本番の EXPLAIN で通った | 同 result.txt（Q1・Q4・Q5） |
| F8 | 既存のテスト `backend/tests/test_tcg_mirror.py` は、問い合わせを DB で実行していない（ID の固定・作成経路の封じ・鍵が無いときのスキップを見るだけ） | 同ファイル :37-123 |

## 3. 触るファイル（これ以外は触らない）

- `backend/app/tasks/tcg_mirror.py`（§4-1・§4-2 の 2 関数の SQL 文字列だけ）
- `backend/tests/test_tcg_mirror.py`（§4-3 のテストを足す）
- `docs/handoff/celery-unregistered-tasks/card-fix-mirror-sql.md`（このカード。§13 の報告欄に追記するだけ）

## 4. 作り方（順番を守る。4-3 のテストを最初に書く）

### 4-1. `_fetch_keywords`（`backend/app/tasks/tcg_mirror.py:140-158` の SQL 文字列）

変更前（:140-158）:

```python
    result = await db.execute(text("""
        SELECT
            p.id::text AS product_id,
            p.name AS product_name,
            'search' AS keyword_type,
            k.keyword
        FROM public.product_search_keywords k
        JOIN public.products p ON p.id = k.product_id
        ORDER BY p.id, k.keyword
        UNION ALL
        SELECT
            p.id::text AS product_id,
            p.name AS product_name,
            'exclude',
            k.keyword
        FROM public.product_exclude_keywords k
        JOIN public.products p ON p.id = k.product_id
        ORDER BY p.id, k.keyword
    """))
```

変更後（並び順は「検索語を全部 → 除外語を全部」。それぞれの中は商品 ID の数の順・語の順。元の書き方の意図と同じ並び）:

```python
    result = await db.execute(text("""
        SELECT product_id, product_name, keyword_type, keyword
        FROM (
            SELECT
                p.id AS sort_id,
                p.id::text AS product_id,
                p.name AS product_name,
                'search' AS keyword_type,
                k.keyword
            FROM public.product_search_keywords k
            JOIN public.products p ON p.id = k.product_id
            UNION ALL
            SELECT
                p.id AS sort_id,
                p.id::text AS product_id,
                p.name AS product_name,
                'exclude' AS keyword_type,
                k.keyword
            FROM public.product_exclude_keywords k
            JOIN public.products p ON p.id = k.product_id
        ) u
        ORDER BY u.keyword_type DESC, u.sort_id, u.keyword
    """))
```

`rows`・`headers`・`data` の行（:159-162）は変えない。

### 4-2. `_fetch_suppliers`（`backend/app/tasks/tcg_mirror.py:168-178` の SQL 文字列）

変更前の該当 3 行:

```sql
            sc.channel_type,
            sc.channel_identifier
...
        ORDER BY ps.supplier_code, sc.channel_type
```

変更後（見出しの名前を保つため、別名を付ける）:

```sql
            sc.channel AS channel_type,
            sc.external_id AS channel_identifier
...
        ORDER BY ps.supplier_code, sc.channel
```

ほかの行（`FROM`・`LEFT JOIN`・`headers`）は変えない。

### 4-3. テスト（`backend/tests/test_tcg_mirror.py` に足す）

先に、既存の `backend/tests/conftest.py` の `db_session`（SQLite）が、`products`・`product_search_keywords`・`product_exclude_keywords`・`suppliers`・`supplier_channels` を作っているかを `git grep -n` で確かめる（出た行を報告に貼る）。

- 分岐 A（5 表とも作っている）: `db_session` に商品 1 件・検索語 1 件・除外語 1 件・仕入元 1 件・チャネル 1 件を入れ、`_fetch_keywords(db_session)` と `_fetch_suppliers(db_session)` を呼ぶテストを 2 本足す。期待値は次のとおり
  - keywords: 2 行。1 行目の `keyword_type` が `search`、2 行目が `exclude`
  - suppliers: 1 行。4 列目が入れた `channel`、5 列目が入れた `external_id`
  - SQLite も `UNION ALL` の前の `ORDER BY` を拒むため、修正前のコードではこのテストが落ちる
- 分岐 B（どれかが無い）: DB を使わず、問い合わせの文字列を検査するテストを 1 本足す。`_fetch_keywords` と `_fetch_suppliers` に、SQL の文字列を受け取って記録するだけの偽の `db`（`execute` が `MagicMock` の結果を返す）を渡し、記録した SQL について次の 2 点を確かめる
  - keywords の SQL で、`ORDER BY` が 1 回だけ、かつ最後の `UNION ALL` より後にある
  - suppliers の SQL に `channel_type`・`channel_identifier` の文字列が、`AS` の後の別名としてだけ現れる（`sc.channel_type`・`sc.channel_identifier` を含まない）

どちらの分岐でも、§5-1 の「修正前に落ちる」を必ず確かめる。

## 5. 確かめ方（担当が実行し、出力を報告に貼る）

生出力は、すべて /tmp/CC報告ファイル/celery-unregistered-tasks-fix/fix-sql/ に保存する。テストと lint は、backend の CI と同じ方法で実行する（`.github/workflows/test.yml` の pytest と ruff の段を読んで合わせ、読んだ行を報告に書く）。

- 5-1. 4-3 を書いた直後（4-1・4-2 より前）に、`backend/tests/test_tcg_mirror.py` だけを実行する。出力全文と終了コードを保存する
  - 期待: 足したテストが failed。既存のテストは passed
  - 4-1・4-2 の後に、もう一度実行する。期待: 全件 passed
- 5-2. `cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-tcg-mirror-sql && git grep -n -e channel_type -e channel_identifier -- backend/app/tasks/tcg_mirror.py` を実行する
  - 期待: `AS channel_type`・`AS channel_identifier` の 2 行と、`headers` の 1 行だけ
- 5-3. `cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-tcg-mirror-sql && git diff origin/main -- backend/app/tasks/tcg_mirror.py` の全文を保存する
  - 確かめること: `+` と `-` の行が、`_fetch_keywords` と `_fetch_suppliers` の SQL 文字列の中だけにあること
- 5-4. 次のテストを実行し、ファイル名と件数を対で貼る。期待: 全件 pass
  - `backend/tests/test_tcg_mirror.py`
  - `backend/tests/test_celery_beat_registered.py`
- 5-5. 変更した 2 ファイルに backend の lint（CI と同じもの）を実行し、終了コード 0 を貼る
- 5-6. backend のテスト全体を、CI と同じ方法で実行し、最後の要約行を貼る
  - 期待: failed 0
  - 変更前から落ちているものがあれば、origin/main でも同じく落ちることを同じ方法で確かめる。その名前を対で書く
- 5-7. `cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-tcg-mirror-sql && git diff origin/main --stat` を実行する
  - 期待: §3 の 3 ファイル

## 6. 分岐ごとの対処

- 5-1 の修正前の実行で、足したテストが落ちずに通る → 作業を止める（NEEDS_DECISION:）。テストが誤りを捕まえていないため
- 5-6 で、触っていないテストが新しく落ちる → 落ちたテストの名前と、出力の最後の 30 行を貼って止まる（BLOCKED:）。テストを書き換えて合わせることはしない
- 5-5 の lint の指摘 → 指示どおりに直してやり直す（記録のみ）
- 4-3 の分岐 A・B → どちらでも続ける（どちらだったかを記録する）

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 足したテストが、修正前は×、修正後は○ | §5-1 |
| 変更は 2 つの SQL 文字列の中だけ | §5-3 |
| CI がすべて緑 | PR の checks（Opus が見る） |
| 直した 2 つの問い合わせが、本番の DB で通る | マージ前に、Opus が PO 実行の EXPLAIN（読み取りのみ）で確かめる。この便の担当は行わない |
| 反映後の最初の 02:30 JST に `[tcg_mirror] 書き出し完了` が出て、READ ME の最終更新が変わる（設計 K2） | 反映後に Opus が Loki で確かめる。PO が目で見る |
| 同じ実行の直後に `attached to a different loop` が出ない | 同上。出たら、後片付けの書き方を変える次の便を作る |

## 8. 本番への反映

担当は行わない。Opus が、コード審査と本番の EXPLAIN と GO 記録の後に main にマージし、通常の deploy で反映する。

## 9. 戻し方

- この PR の revert を main にマージし、通常の deploy で戻す。DB と設定の変更は無い
- 戻すと、写しシートの書き出しは毎晩また同じ誤りで落ちる（反映前と同じ状態。ほかの処理には影響しない）

## 10. PR

- 作業場所は `/Users/tanizawashingo/worktrees/salesanchor/release-fix-tcg-mirror-sql`（作成済み）。最初に `cd /Users/tanizawashingo/salesanchor && ls -1d /Users/tanizawashingo/worktrees/salesanchor/release-fix-tcg-mirror-sql && git worktree list --porcelain | grep -c release-fix-tcg-mirror-sql` で実在を確かめる。以後の作業は、すべてその作業場所に `cd` してから行う
- 実装の前に `cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-tcg-mirror-sql && ./scripts/dev/executor-preflight.sh` を実行し、終了コードを貼る
- commit の後に `git log -1 --oneline` を実行する。push の後に `git log origin/release/fix-tcg-mirror-sql -1 --oneline` を実行し、実在を確かめる
- PR の作り方
  - 先に Write ツールで本文ファイルを作る
  - その本文を `--body "$(cat 本文ファイル)"` の形で `scripts/gh-pr-create-safe.sh` に渡して作る
  - 作成後に `gh pr list --head release/fix-tcg-mirror-sql --limit 5 --json number,isDraft` を実行し、1 件で isDraft が false であることを確かめる
- 作成前に `gh auth status` を実行し、`shingo-cc` 名義であることを確かめる
- PR は ready で作る（Draft にしない）。base は main。マージは Opus の GO 記録の後に限る（担当はマージしない）
- 本文は PR テンプレートに沿って書く。各欄の書き方は次のとおり
  - `### 標準ワークフロー確認`: recon（docs/handoff/celery-unregistered-tasks/recon.md）・設計（docs/handoff/celery-unregistered-tasks/design.md）・このカード・ADR-1012 を書く
  - `区分:` は A
  - PO 承認は「PO 原文『y』（2026-10-16）」と書く
  - `Opus 審査記録:` は「コード審査はこれから」と書く
  - `設計仕様書（あるべき姿）:` は「対象外」と書く
  - `触るファイル:` と `削除するファイル:` は、1 行・カンマ区切り・バッククォートなしで書く。`削除するファイル:` には、行を書き換えた既存ファイルを全部書く
- 本文に IP・鍵のパス・認証ファイルの中身・スプレッドシートの ID を書かない
- 作成前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し、exit 0 を確かめる（2 分以上かかるので、コマンドの待ち時間を長めにする）

## 11. 報告

- 宛先は Opus
- 完了報告の本文に書くもの
  - 冒頭の受領文
  - §5-1〜5-7 の出力（長いものは保存先のパス）
  - PR の URL
  - 生出力のパス
  - 4-3 の分岐（A・B のどちらだったか）
  - 判断を要した点（事実のみ）
- 停止したときに書くもの: 停止した手順番号・最後に実行したコマンド・停止した理由の原文
- 1 行目は、DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか

## 12. 委任の定型

- sleep しない（CI の待ちは Opus が行う）
- ファイルの作成と編集は Write/Edit ツールで行う（ヒアドキュメントで書かない）
- PR を作る前に `scripts/dev/validate-pr-body.sh` で exit 0 を確かめる
- フックや自動判定に止められたら、言い換えて再試行しない。止まった手順・最後のコマンド・理由の原文を報告して終える

## 13. 報告欄（担当が追記）

2026-10-16 担当(Sonnet)の実行記録（生出力は /tmp/CC報告ファイル/celery-unregistered-tasks-fix/fix-sql/）:

- 4-3 の分岐: B（conftest.py に product_search_keywords・product_exclude_keywords・supplier_channels の作成が無いため）
- 5-1: 修正前は 2 failed・6 passed、修正後は 8 passed（5-1-before.txt・5-1-after.txt）。単体実行の終了コード 1 は coverage 60% 未達のみが理由
- 5-4: test_tcg_mirror.py と test_celery_beat_registered.py で 9 passed
- 5-5: `ruff check app/` は All checks passed。tests/test_tcg_mirror.py の ruff 指摘は変更前（origin/main 相当）から 4 件あり、CI の対象外
- 5-6: 全体は 2 failed・5214 passed・585 errors（ローカルに PostgreSQL が無い）。failed 2 件は test_unit_recovery.py の e5 で、変更前でも同じく落ちることを確認


END OF CARD
