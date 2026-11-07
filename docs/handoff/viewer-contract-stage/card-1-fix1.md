# card: 便1 直し1 試験の並び順を文字コード順に固定する（ADR-1061）

状態: カード発行（Opus、2026-11-07）。便1 の実装承認（PO 2026-11-07「1」）の範囲の直し。製品の動きは変えない（試験の確かめ方だけ）。
設計: docs/handoff/viewer-contract-stage/design.md §4（便1）。元のカード: docs/handoff/viewer-contract-stage/card-1.md。
担当: クラウドの Sonnet。触ってよいのは `backend/tests/test_viewer_purge.py` の 1 行だけ。本番・GitHub の secret・DB には触らない。PR は作らない（PR #5250 は Opus が持つ）。
基準: 枝 `release/viewer-retention-3y` の HEAD（この直しのカードを載せた commit）。

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

## 0. なぜ直すか（観測した事実）

- PR #5250 の CI「pytest-run-internal」で 1 件だけ失敗した（8493 passed・1 failed）。失敗は `tests/test_viewer_purge.py::test_suspended_uses_later_of_suspend_and_access_end`。
- CI の PostgreSQL が返した順: `s-late-end@x.com`・`snorecord@x.com`・`s-recent@x.com`。試験の期待: `s-late-end@x.com`・`s-recent@x.com`・`snorecord@x.com`。
- 残った 3 件の中身は期待どおり（消えるべき行は消えている）。違うのは並び順だけ。CI の DB の並べ方（照合順序）は `-` を飛ばして比べるため、`snorecord` が `s-recent` より前に来る。文字コード順（`COLLATE "C"`）なら `-`（0x2D）が英字より前なので、期待の順になる。
- 期待の順はカード 便1 §2-4 で Opus が書いた。書いたときに DB の並べ方を確かめなかったのが原因（Opus の書き損じ）。

`COLLATE "C"` にしたときの他の試験の期待（文字コード順で確かめた）:
- `["active@x.com", "t1090@x.com", "t91@x.com"]`: `a`<`t`、`t1`<`t9`。変わらない。
- `["p6@x.com", "trial8@x.com"]`: `p`<`t`。変わらない。

## 1. 触るファイル

1. backend/tests/test_viewer_purge.py（`_emails` の 1 行だけ）

触らない: これ以外のすべて。期待の並び（`assert _emails(cur) == [...]` の行）も変えない。

## 2. 変更

変更前（1 か所だけ。2 か所あれば BLOCKED: で停止）:

    cur.execute("SELECT email FROM public.viewer_accounts ORDER BY email")

変更後:

    cur.execute('SELECT email FROM public.viewer_accounts ORDER BY email COLLATE "C"')

## 3. 手順

手順1 枝を取る
    cd ~ && git clone https://github.com/shingo-ops/salesanchor.git sa && cd sa && git checkout release/viewer-retention-3y && git log --oneline -1 | tail -1

手順2 点検（期待: カードが在る・変更前の文が 1）
    cd ~/sa && git rev-parse HEAD | tail -1
    cd ~/sa && ls docs/handoff/viewer-contract-stage/card-1-fix1.md | tail -1
    cd ~/sa && grep -c 'ORDER BY email")' backend/tests/test_viewer_purge.py

手順3 §2 の変更をする（Edit ツールで行う）

手順4 道具を入れる（本番と同じ Python 3.12 の venv を作業場所の外 ~/venv312 に作る。素の pip は見張り py312-guard が止めるので使わない）
    python3.12 -m venv ~/venv312 2>&1 | tail -3
    cd ~/sa/backend && ~/venv312/bin/pip install -q -r requirements.txt 2>&1 | tail -3
    cd ~/sa/backend && ~/venv312/bin/pip install -q -r requirements-dev.txt 2>&1 | tail -3
  python3.12 が無いときだけ、1行目の代わりに次を流す（それも失敗したら `BLOCKED: python3.12 なし`）:
    uv venv --python 3.12 ~/venv312 2>&1 | tail -3
    ~/venv312/bin/python -m ensurepip 2>&1 | tail -1

手順5 形と試験（期待: ruff は All checks passed!、grep は 1、pytest は 1 passed と 4 skipped。PostgreSQL の試験は CI だけで動く）
    cd ~/sa && ~/venv312/bin/ruff check backend/tests/test_viewer_purge.py 2>&1 | tail -5
    cd ~/sa && grep -c 'ORDER BY email COLLATE "C"' backend/tests/test_viewer_purge.py
    cd ~/sa/backend && ~/venv312/bin/python -m pytest -q -p no:cacheprovider tests/test_viewer_purge.py 2>&1 | tail -8

手順6 差分を確かめる（期待: 1 file changed, 1 insertion(+), 1 deletion(-)）
    cd ~/sa && git status --short | tail -5
    cd ~/sa && git diff --stat | tail -3
    cd ~/sa && git diff | tail -15

手順7 記録して送る
    cd ~/sa && git add backend/tests/test_viewer_purge.py && git commit -q -m "test(viewer): sort emails by byte order so the expected order does not depend on DB collation (ADR-1061 bin1)" && git log --oneline -1 | tail -1
    cd ~/sa && git push origin release/viewer-retention-3y 2>&1 | tail -3
    cd ~/sa && git log --oneline origin/release/viewer-retention-3y -2 | tail -2

commit 文の末尾には空行を1つ置いて `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>` を付けてよい（付けるときは `-m` をもう1つ足す）。

## 4. 想定される分かれ道

- 停止する（その場で止め、それまでの出力と §5 の報告を返して終わる。別のやり方を試さない）:
  - カードが枝に無い → `BLOCKED: カードなし`。
  - 変更前の文が 0 か所・2 か所以上 → `BLOCKED: 変更前の文`。
  - 手順5 で failed か error が出た → 直さず最後の 8 行を貼って `BLOCKED: pytest`。
  - ruff が何か出した → 直さず貼って `BLOCKED: ruff`。
  - push が拒まれた → 最後の 3 行を貼って `BLOCKED: push`（force はしない）。
- 記録して続ける: requirements が一部入らない（手順5 の pytest が動けば続ける）。`git status` に他のファイルが出た（add せず名前を書く）。

## 5. 報告の形

- 宛先: 完了報告の本文（クラウドの実行の最後の返事）。ファイルに書かない。
- 1 行目: `RECEIVED viewer-retention-bin1-fix1 HEAD=`（続けて 40 桁）。2 行目: 「本報告はカード 便1 直し1 の実行結果である」。
- 手順2・5・6・7 の出力（tail の範囲）をそのまま貼る。要約しない。
- 停止したときは「停止した手順番号／最後に実行したコマンド／停止した理由」の 3 点。
- 最後の行: `DONE` か `BLOCKED: 理由`。

## 6. 委任の定型

- sleep しない。CI の結果は Opus が見る。
- ファイルの編集は Edit ツールで行う。ヒアドキュメントで書かない。
- PR は作らない。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。

END OF CARD
