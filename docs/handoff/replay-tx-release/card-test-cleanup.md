# 実装カード — 接続上限の試験の後片付けを「付いているときだけ外す」にする

読んだ節: guards/00-common.md・guards/03-file.md・guards/04-worktree.md・guards/05-pr.md（照合: 危険パスなし・作業枝は Opus が new-worktree.sh で作成済み・PR は gh-pr-create-safe.sh・触るファイルは同一行カンマ区切り）

受領確認
  最初の応答で「受領。」と1行返してから始める。

停止時の報告
  止まったときは、画面に出たエラー出力を全文そのまま報告に貼る。報告は DONE / BLOCKED: / NEEDS_DECISION: のどれかで始める。

- 根拠: PR #5357 のマージ前審査 reviewer（opus）VERDICT: APPROVE on 5cdb50af7 の軽い指摘 (1)。「試験B の finally は、受け手が付いていないときも event.remove を呼ぶ。付いていないと `sqlalchemy.exc.InvalidRequestError: No listeners found` が出て、本当の失敗（assert event.contains が False）を隠す」。赤の実演 CI run 42758847247 の記録で、この重なりが実際に出た（AssertionError の後に InvalidRequestError）。
- 設計: docs/handoff/replay-tx-release/design.md §14 K5'（試験の目的は変えない）
- PO 承認: 2026-11-10 PO「つぎを進める」（前の作業の確認済みコメントで「次の作業で直す」と書いた件）
- 起点: 作業枝 release/tx-guard-test-cleanup（origin/main から作成済み。このカードだけが入っている）。この枝に積む
- 触るファイル（これ以外は触らない）: backend/tests/test_tx_guard_pool.py
- 触らない: backend/app/・migrations/・.github/・scripts/・ほかの試験ファイル
- 危険なパス（migrations/・deploy.yml・本番 scripts/）は含まない

## 1. 変更（backend/tests/test_tx_guard_pool.py の finally 2か所だけ）

変更前（:46〜:48 と :62〜:64。2か所とも同じ形）:
```python
    finally:
        event.remove(engine, "connect", _tx_guard._on_connect_set_idle_limit)
        engine.dispose()
```
変更後（2か所とも）:
```python
    finally:
        # 付いていないときに外すと InvalidRequestError が本当の失敗を隠すため、付いているときだけ外す
        if event.contains(engine, "connect", _tx_guard._on_connect_set_idle_limit):
            event.remove(engine, "connect", _tx_guard._on_connect_set_idle_limit)
        engine.dispose()
```
ほかの行は変えない（assert・engine の作り方・import はそのまま）。

## 2. 確かめ（生の出力を PR に貼る）

- `cd backend && ruff check tests/test_tx_guard_pool.py`
- `git diff origin/main --stat` が backend/tests/test_tx_guard_pool.py とこのカードだけ
- PR の CI「pytest (SQLite + PostgreSQL RLS)」で試験A・B が passed（skipped でない）。手元は DB が無いので `Disposable CI service required` で ERROR になるのは想定どおり（名前と最後の行を報告に書く）

## 3. 想定の分かれ道

- `event.contains` が手元で import できない・名前が違う → 止めて BLOCKED:
- 変更前の行が上の形と違う（すでに直っている）→ 何もせず NEEDS_DECISION:
- ruff の指摘 → 指摘どおりに直す（中身は変えない）

## 4. PR

- commit・push・PR 作成は段を分ける。各段の後で git log と .pr-number の実在を確かめてから次へ進む。push は毎回 git push -u origin HEAD。
- gh auth status で shingo-cc を確かめる。PR は scripts/gh-pr-create-safe.sh で作り、本文は先にファイルに書いてその実在パスを渡す。Draft にしない。マージはしない（Opus が審査してマージする）。
- PR 本文は .github/pull_request_template.md に従う。`### 標準ワークフロー確認` に recon: docs/handoff/replay-tx-release/recon.md・設計: docs/handoff/replay-tx-release/design.md・対象ADR: ADR-1037 を書く。触るファイル: は1行・カンマ区切り。削除するファイルは無し。

END OF CARD
