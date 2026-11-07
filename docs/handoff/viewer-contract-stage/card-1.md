# card: 便1 閲覧者の名簿を3年残す・公開ポリシーの改訂（ADR-1061）

状態: カード発行（Opus、2026-11-07）。PO の設計承認と実装承認は 2026-11-07「1」（設計を承認し、実装の準備も進める）。3年保持の進め方は 2026-11-07「2」（専門家に確かめずに進める。公開から14日以上たって効くようにする）。
設計: docs/handoff/viewer-contract-stage/design.md §3-9・§4（便1）。現状の記録: docs/handoff/viewer-contract-stage/recon.md §4。
担当: クラウドの Sonnet。触ってよいのは下の「1. 触るファイル」だけ。本番・GitHub の secret・DB には触らない。PR は作らない（Opus が作る）。
基準: origin/main `b803ee5a7bfd6be2a78c904479aa6de1d3aac9ed` で行番号を測った（931be583e と同じ行）。行番号がずれていたら「変更前」の文で場所を探す（同じ文が 2 か所あれば BLOCKED: で停止）。
ポリシーの日付: 改訂日は §2-5 のとおり 2026-11-08（November 8, 2026）で書く。実際のマージの日と違えば、マージの前に Opus が直す（設計 §3-9。効力発生日は改訂日から14日以上あと）。担当は日付を変えない。
危険便か: いいえ（`migrations/`・`.github/workflows/`・本番 `scripts/` を含まない）。ただし本番の自動削除の条件を変えるので、マージ前に Opus の審査役の APPROVE と CI 全通過を必須にする（担当の作業ではない）。

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

## 0. カード発行前チェック（docs/ai-agents/design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は担当が作らない（Opus が ready で作る） | ○（冒頭・§5） |
| 3 | 報告の宛先と生出力の扱い | ○（§5。完了報告の本文に各手順の出力を tail の範囲でそのまま貼る） |
| 4 | 1便1目的 | ○（閲覧者の名簿の保存期間を3年にする。その約束の文であるポリシーの改訂は同じ目的の表と裏） |
| 5 | 既存ブランチへの追記ではない | ○（Opus が origin/main から作った新しい枝 `release/viewer-retention-3y` にこのカードだけが載っている） |
| 6 | 書式は実例で示した | ○（§2 に変更前・変更後の全文） |
| 7 | 合格基準を出力まで縛った | ○（§3 の各手順の期待） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（手順8 の `git status --short` と `git diff --stat`） |
| 9 | 出力量に上限のないコマンドを使わない | ○（すべて tail） |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○（§4・§5・末尾） |
| 11 | 期待値は実測から | ○（境目の日数は 3 年 ≒ 1095〜1096 日に対して 1090 と 1100 で余裕を取った。PostgreSQL 16 の公式説明書で `make_interval(years => n)` の名前付きの書き方と、`GREATEST` が NULL を無視することを確かめた。Context7 は月の上限で使えなかったため公式の文書を直接読んだ） |
| 12 | 停止は本番影響のあるものに限る | ○（§4。push の失敗・既存の試験の失敗だけ停止。件数の食い違いは記録して続ける） |
| 13 | 委任文の定型4点 | ○（§6） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない（commit は git log で確かめる） | ○（§3） |
| guards/03-file.md | 編集は Edit ツール。プレースホルダを残さない | ○（§2 は全文） |
| guards/10-executor.md | 散文で頼まない。手順はコマンドで書く | ○（§3） |

## 受領確認（最初の報告の 1 行目に書く）

`RECEIVED viewer-retention-bin1 HEAD=`（続けて `git rev-parse HEAD` の 40 桁）。2 行目に「本報告はカード 便1 閲覧者の名簿を3年残す の実行結果である」と書く。

## 0-3. 実装前点検（手順2 で流す。外れたら実装せず BLOCKED: で停止）

- P1 `docs/handoff/viewer-contract-stage/card-1.md`（このカード）が枝に在る。
- P2 `grep -c "VIEWER_RETENTION_DAYS" backend/app/tasks/maintenance.py` が 3。
- P3 `grep -rn "VIEWER_RETENTION_DAYS" backend --include=*.py` の行が maintenance.py の 3 行だけ。
- P4 `grep -c "Issuing invoices to contracted Inventory Viewer customers" lp/src/pages/privacy.astro` が 1。
- P5 `grep -c "Version: 1.5" lp/src/pages/privacy.astro` が 1。`grep -c "<td>1.7</td><td>2026-06-03</td>" lp/src/pages/privacy.astro` が 1。

## 1. 触るファイル

1. backend/app/tasks/maintenance.py
2. backend/tests/test_viewer_purge.py
3. lp/src/pages/privacy.astro

触らない: これ以外のすべて。特に `backend/app/celery_app.py`（定時の登録は変えない）・`migrations/`・`.github/`・`lp/src/pages/terms.astro`（会社の解約の90日は別の話で、変えない）・`frontend/`。

## 2. 変更

### 2-1 maintenance.py（保存期間の定数）

変更前（:33）:
```python
VIEWER_RETENTION_DAYS = 90  # 期限切れ trial・停止 suspended を消すまで
```
変更後:
```python
VIEWER_RETENTION_YEARS = 3  # 見られる期限（停止はその日と最後の停止の遅い方）から消すまで（ADR-1061）
```
:34 の `VIEWER_PENDING_DAYS = 7` と :35 の `VIEWER_LOGIN_EVENT_RETENTION_DAYS = 90` は変えない。

### 2-2 maintenance.py（purge_viewer_accounts の説明）

変更前（:202〜:208）:
```python
    """閲覧専用アカウントの毎日の掃除（ADR-1019 Q7）。public の表なのでテナント文脈は使わない。

    1. 期限切れから 90 日たった trial  2. 停止（suspend 記録）から 90 日たった suspended
    3. 7 日たった pending  4. 90 日より古いログイン記録
    アカウントを消すと、ログイン記録・状態履歴・鍵は CASCADE で一緒に消える。
    件数だけログに出す（email は出さない）。
    """
```
変更後:
```python
    """閲覧専用アカウントの毎日の掃除（ADR-1019 Q7。期間は ADR-1061 で3年）。public の表なのでテナント文脈は使わない。

    1. 見られる期限（trial_expires_at）から 3 年たった trial
    2. 最後の停止記録と見られる期限の遅い方から 3 年たった suspended（停止記録の無い行は消さない）
    3. 7 日たった pending  4. 90 日より古いログイン記録
    本契約（active）は消さない。
    アカウントを消すと、ログイン記録・状態履歴・鍵・請求先は CASCADE で一緒に消える。
    件数だけログに出す（email は出さない）。
    """
```

### 2-3 maintenance.py（trial と suspended の DELETE）

変更前（:212〜:227）:
```python
        trial_expired = session.execute(
            text(f"""
                DELETE FROM public.viewer_accounts
                WHERE status = 'trial' AND trial_expires_at < NOW() - INTERVAL '{VIEWER_RETENTION_DAYS} days'
            """)
        ).rowcount
        suspended = session.execute(
            text(f"""
                DELETE FROM public.viewer_accounts a
                WHERE a.status = 'suspended'
                  AND (
                      SELECT max(c.created_at) FROM public.viewer_status_changes c
                      WHERE c.viewer_id = a.id AND c.action = 'suspend'
                  ) < NOW() - INTERVAL '{VIEWER_RETENTION_DAYS} days'
            """)
        ).rowcount
```
変更後:
```python
        trial_expired = session.execute(
            text(
                "DELETE FROM public.viewer_accounts "
                "WHERE status = 'trial' AND trial_expires_at < NOW() - make_interval(years => :y)"
            ),
            {"y": VIEWER_RETENTION_YEARS},
        ).rowcount
        # 停止の人: 最後の停止記録と見られる期限の遅い方から数える（GREATEST は NULL を無視する）。
        # 停止記録の無い行は EXISTS で外す（今までと同じく消さない）
        suspended = session.execute(
            text("""
                DELETE FROM public.viewer_accounts a
                WHERE a.status = 'suspended'
                  AND EXISTS (
                      SELECT 1 FROM public.viewer_status_changes c
                      WHERE c.viewer_id = a.id AND c.action = 'suspend'
                  )
                  AND GREATEST(
                      (
                          SELECT max(c.created_at) FROM public.viewer_status_changes c
                          WHERE c.viewer_id = a.id AND c.action = 'suspend'
                      ),
                      a.trial_expires_at
                  ) < NOW() - make_interval(years => :y)
            """),
            {"y": VIEWER_RETENTION_YEARS},
        ).rowcount
```
pending の DELETE（:228〜:233）・ログイン記録・返り値の dict のキー（`trial_expired`・`suspended`・`pending`・`login_events`）は変えない。

### 2-4 test_viewer_purge.py

(a) 1 行目の説明を直す。
変更前 `"""閲覧専用アカウントの毎日の掃除 purge_viewer_accounts の試験（ADR-1019 Q7・段4a-1）。`
変更後 `"""閲覧専用アカウントの毎日の掃除 purge_viewer_accounts の試験（ADR-1019 Q7・段4a-1、ADR-1061 で3年）。`

(b) `test_trial_expired_91_days_is_deleted_89_days_stays` の関数をまるごと次に置き換える（関数名も変える）:
```python
@needs_ci_pg
def test_trial_is_kept_3_years_after_expiry(pg):  # noqa: F811
    conn, engine, async_url = pg
    cur = _prepare(conn, async_url)
    _account(cur, "t1100@x.com", "trial", trial_days_ago=1100)
    _account(cur, "t1090@x.com", "trial", trial_days_ago=1090)
    _account(cur, "t91@x.com", "trial", trial_days_ago=91)  # 前の決まり（90日）では消えていた行
    _account(cur, "active@x.com", "active", trial_days_ago=2000, created_days_ago=2000)  # 本契約は消さない
    result = _run_purge(engine)
    assert result["trial_expired"] == 1
    assert _emails(cur) == ["active@x.com", "t1090@x.com", "t91@x.com"]
```

(c) `test_suspended_by_suspend_record_age` の関数をまるごと次に置き換える（関数名も変える）:
```python
@needs_ci_pg
def test_suspended_uses_later_of_suspend_and_access_end(pg):  # noqa: F811
    conn, engine, async_url = pg
    cur = _prepare(conn, async_url)
    old = _account(cur, "s-old@x.com", "suspended", trial_days_ago=1100)
    late_end = _account(cur, "s-late-end@x.com", "suspended", trial_days_ago=1090)
    recent = _account(cur, "s-recent@x.com", "suspended")
    _account(cur, "snorecord@x.com", "suspended", trial_days_ago=2000, created_days_ago=2000)  # 停止記録が無い行は消えない
    _suspend_record(cur, old, 1100)
    _suspend_record(cur, late_end, 1100)  # 停止は3年より前でも、見られる期限が3年以内なので残る
    _suspend_record(cur, recent, 91)  # 前の決まり（90日）では消えていた行
    result = _run_purge(engine)
    assert result["suspended"] == 1
    assert _emails(cur) == ["s-late-end@x.com", "s-recent@x.com", "snorecord@x.com"]
```

(d) `test_deleting_account_cascades_and_old_login_events_are_purged` の中の 1 行だけ変える:
変更前 `    gone = _account(cur, "gone@x.com", "trial", trial_days_ago=95)`
変更後 `    gone = _account(cur, "gone@x.com", "trial", trial_days_ago=1100)`

それ以外（`test_task_is_registered_and_scheduled`・`test_pending_older_than_7_days_is_deleted_trial_stays`・補助の関数）は変えない。

### 2-5 privacy.astro（公開ポリシー。英語の文はこのとおり一字も変えずに入れる）

(a) 版と日付（:14〜:16）
変更前:
```
    Effective Date: May 21, 2026<br>
    Last Updated: May 21, 2026<br>
    Version: 1.5
```
変更後:
```
    Effective Date: December 1, 2026<br>
    Last Updated: November 8, 2026<br>
    Version: 1.8
```

(b) 利用目的（:177 の次の行に 1 行足す）
変更前:
```
    <li>Issuing invoices to contracted Inventory Viewer customers</li>
```
変更後:
```
    <li>Issuing invoices to contracted Inventory Viewer customers</li>
    <li>Preventing repeated free-trial registrations by former Inventory Viewer users</li>
```

(c) 保存期間の表（:215〜:216 の 2 行を 3 行に）
変更前:
```
      <tr><td>Inventory Viewer Account</td><td>During the trial or contract period; deleted 90 days after the trial expires without extension or 90 days after suspension. Login records: 90 days</td></tr>
      <tr><td>Inventory Viewer Billing Information</td><td>Deleted together with the Inventory Viewer Account</td></tr>
```
変更後:
```
      <tr><td>Inventory Viewer Account</td><td>During the trial or contract period, and for 3 years after access ends (the trial or payment deadline passes, or the account is suspended, whichever is later). Unconfirmed applications: 7 days. Login records: 90 days</td></tr>
      <tr><td>Inventory Viewer Billing Information</td><td>Deleted together with the Inventory Viewer Account</td></tr>
      <tr><td>Inventory Viewer Invoices</td><td>7 years from issuance (tax-law retention obligation)</td></tr>
```

(d) 委託先の表の Google（:247）
変更前:
```
      <tr><td>Google LLC</td><td>Authentication (Google Identity Platform) / AI-assisted message translation (Gemini API — paid tier, DPA in place)</td><td>United States</td></tr>
```
変更後:
```
      <tr><td>Google LLC</td><td>Authentication (Google Identity Platform) / AI-assisted message translation (Gemini API — paid tier, DPA in place) / Storage of issued invoices (Google Drive)</td><td>United States</td></tr>
```

(e) 改訂の履歴（`<td>1.7</td><td>2026-06-03</td>` で始まる行の次に 1 行足す）
足す行:
```
      <tr><td>1.8</td><td>2026-11-08</td><td>§5.1 added: preventing repeated free-trial registrations; §6.3 updated: Inventory Viewer Account retained for 3 years after access ends, Inventory Viewer Invoices retained for 7 years; §7.2 updated: Google Drive added for invoice storage; header version and dates corrected (effective December 1, 2026)</td></tr>
```

## 3. 手順

手順1 枝を取る
    cd ~ && git clone https://github.com/shingo-ops/salesanchor.git sa && cd sa && git checkout release/viewer-retention-3y && git log --oneline -1 | tail -1

手順2 実装前点検 P1〜P5 を流し、結果をそのまま報告に貼る
    cd ~/sa && git rev-parse HEAD | tail -1
    cd ~/sa && ls docs/handoff/viewer-contract-stage/card-1.md | tail -1
    cd ~/sa && grep -c "VIEWER_RETENTION_DAYS" backend/app/tasks/maintenance.py
    cd ~/sa && grep -rn "VIEWER_RETENTION_DAYS" backend --include=*.py | tail -5
    cd ~/sa && grep -c "Issuing invoices to contracted Inventory Viewer customers" lp/src/pages/privacy.astro
    cd ~/sa && grep -c "Version: 1.5" lp/src/pages/privacy.astro
    cd ~/sa && grep -c "<td>1.7</td><td>2026-06-03</td>" lp/src/pages/privacy.astro

手順3 §2 の変更をする（2-1 から 2-5 の順。Edit ツールで行う）

手順4 道具を入れる（本番と同じ Python 3.12 の venv を作業場所の外 ~/venv312 に作る。素の pip は見張り py312-guard が止めるので使わない）
    python3.12 --version 2>&1 | tail -1
    python3.12 -m venv ~/venv312 2>&1 | tail -3
    ~/venv312/bin/python --version 2>&1 | tail -1
    cd ~/sa/backend && ~/venv312/bin/pip install -q -r requirements.txt 2>&1 | tail -3
    cd ~/sa/backend && ~/venv312/bin/pip install -q -r requirements-dev.txt 2>&1 | tail -3
    ~/venv312/bin/ruff --version | tail -1
  python3.12 が無いときだけ、1行目と2行目の代わりに次を流す（それも失敗したら `BLOCKED: python3.12 なし`）:
    uv venv --python 3.12 ~/venv312 2>&1 | tail -3
    ~/venv312/bin/python -m ensurepip 2>&1 | tail -1

手順5 形（期待: ruff は All checks passed!、残りの grep は 0・3・1・1・1・1）
    cd ~/sa && ~/venv312/bin/ruff check backend/app/tasks/maintenance.py backend/tests/test_viewer_purge.py 2>&1 | tail -10
    cd ~/sa && grep -rn "VIEWER_RETENTION_DAYS" backend --include=*.py | wc -l
    cd ~/sa && grep -c "VIEWER_RETENTION_YEARS" backend/app/tasks/maintenance.py
    cd ~/sa && grep -c "Preventing repeated free-trial registrations" lp/src/pages/privacy.astro
    cd ~/sa && grep -c "Inventory Viewer Invoices" lp/src/pages/privacy.astro
    cd ~/sa && grep -c "Storage of issued invoices (Google Drive)" lp/src/pages/privacy.astro
    cd ~/sa && grep -c "<td>1.8</td><td>2026-11-08</td>" lp/src/pages/privacy.astro

手順6 試験（期待: 1 passed と 4 skipped。PostgreSQL の試験は GitHub の CI だけで動くので、ここでは skipped で良い。本当の合否は CI で Opus が見る）
    cd ~/sa/backend && ~/venv312/bin/python -m pytest -q -p no:cacheprovider tests/test_viewer_purge.py 2>&1 | tail -15

手順7 ポリシーのページを組み立てる（期待: 最後の数行に Complete が出て、エラーが無い）
    cd ~/sa/lp && npm ci 2>&1 | tail -3
    cd ~/sa/lp && npm run build 2>&1 | tail -8
    cd ~/sa/lp && grep -c "3 years after access ends" dist/privacy/index.html

手順8 差分を確かめる（期待: 変更は §1 の 3 個とその他なし。削除行は maintenance.py と test_viewer_purge.py と privacy.astro の §2 で置き換えた行だけ）
    cd ~/sa && git status --short | tail -20
    cd ~/sa && git diff --stat | tail -10
    cd ~/sa && git diff lp/src/pages/privacy.astro | tail -60

手順9 記録して送る（§1 の 3 個だけを add する）
    cd ~/sa && git add backend/app/tasks/maintenance.py backend/tests/test_viewer_purge.py lp/src/pages/privacy.astro && git commit -q -m "feat(viewer): keep viewer accounts 3 years after access ends and update privacy policy (ADR-1061 bin1)" && git log --oneline -1 | tail -1
    cd ~/sa && git push origin release/viewer-retention-3y 2>&1 | tail -3
    cd ~/sa && git log --oneline origin/release/viewer-retention-3y -2 | tail -2

commit 文の末尾には空行を1つ置いて `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>` を付けてよい（付けるときは `-m` をもう1つ足す）。

## 4. 想定される分かれ道

停止の2段（design-partner.md §5.5 の 12）:
- 停止する（その場で作業を停止し、それまでの出力と §5 の報告を返して終わる。別のやり方を試さない）:
  - P1 が外れた（このカードが枝に無い）→ `BLOCKED: P1`。
  - §2 の変更前の文が見つからない・2 か所ある → `BLOCKED: ファイル名 変更前の文`。
  - 手順6 で failed か error が 1 件でも出た → 試験を直さず最後の 15 行を貼って `BLOCKED: pytest`。ただしカードからの書き写し間違い（字・字下げ）が出力から分かるときだけ、カードの文に合わせて直してよい。直したら何をどう直したかを書く。
  - 手順7 の build が失敗した → 最後の 8 行を貼って `BLOCKED: lp build`。
  - push が拒まれた → 最後の 3 行を貼って `BLOCKED: push`（force はしない）。
- 記録して続ける（値を報告に書き、判定は Opus がする）:
  - P2〜P5 や手順5 の件数が期待と違う。
  - 手順4 の requirements が一部入らない（手順6 で import できれば続ける）。
  - ruff が I（並び順）だけを出した → `~/venv312/bin/ruff check --fix --select I` を同じ 2 ファイルに流して、その結果を書く。I 以外を出したら `BLOCKED: ruff`。
  - `git status` に §1 の 3 個以外が出た → それを add せず、名前を報告に書く。

## 5. 報告の形

- 宛先: 完了報告の本文（クラウドの実行の最後の返事）。ファイルに書かない。
- 1 行目: `RECEIVED viewer-retention-bin1 HEAD=…`。2 行目: 「本報告はカード 便1 閲覧者の名簿を3年残す の実行結果である」。
- 手順2・4・5・6・7・8・9 の出力（tail の範囲）をそのまま貼る。要約しない。
- 停止したときは「停止した手順番号／最後に実行したコマンド／停止した理由」の 3 点。
- 秘密の値・鍵・パスワードは貼らない。
- 最後の行: `DONE` か `BLOCKED: 理由`。

## 6. 委任の定型

- sleep しない。待ちが要るものは Opus が見る（CI の結果など）。
- ファイルの編集は Edit ツールで行う。ヒアドキュメントで書かない。
- PR は作らない（Opus が作り、`scripts/dev/validate-pr-body.sh` で確かめる）。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。

END OF CARD
