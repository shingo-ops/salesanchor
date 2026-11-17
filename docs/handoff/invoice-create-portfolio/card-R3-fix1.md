# card-R3-fix1: CI の赤を直す（便 R3・PR #5580）

作成: Opus（Planner）2026-11-17。実装承認は便 R3 の承認の範囲内（同じ PR の CI を通すための直し）。
枝: release/invoice-portfolio-r3-shipping（今の HEAD 7d5bfa65246c098ffc684c19092e1482624f903c に、このカードの commit が1つ乗っている）。
# rules-ack: d5738ef7

## 0. 起きたこと（事実）

- CI pytest-run-internal（run 44094452075）: `FAILED tests/test_realtime_topics.py::test_every_write_route_is_in_exactly_one_table - AssertionError: どちらの表にも無い書き込みルート: [('POST', '/api/v1/invoices/draft-shipping-quotes')]`。ほかは 9825 passed・failed はこの1件だけ。
- この試験は、POST・PUT・PATCH・DELETE の道がすべて backend/app/realtime/topics.py の `WRITE_ROUTE_TOPICS`（合図を出す）か `NO_SIGNAL_ROUTES`（合図を出さない・理由つき）のどちらか1つに載っていることを確かめる（ADR-1016）。
- 新しい道は読むだけで書かない（design-v2 §3-9「即時反映の表に載せる対象ではない」）。そのため `NO_SIGNAL_ROUTES` に理由つきで1行足す。card-R3 で入れ忘れたのが原因。
- origin/main がこの枝の祖先でなくなった（`git merge-base --is-ancestor origin/main HEAD` → 1）。main を取り込む。

## 1. 手順（1つずつ流し、出力を報告に書く）

手順1 作業場所（台本は手元に枝が無いと origin/main から枝を作る。そこへ PR の枝を merge して、PR の枝の中身と今の main の両方を持たせる。reset・rebase・force push はしない）
    cd /home/user/salesanchor && git fetch origin main release/invoice-portfolio-r3-shipping
    cd /home/user/salesanchor && git branch --list release/invoice-portfolio-r3-shipping
    cd /home/user/salesanchor && bash scripts/new-worktree.sh release/invoice-portfolio-r3-shipping
    cd /home/user/salesanchor && git worktree list
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping && git merge --no-edit origin/release/invoice-portfolio-r3-shipping 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping && git merge-base --is-ancestor origin/release/invoice-portfolio-r3-shipping HEAD; echo "pr-branch exit=$?"
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping && git merge-base --is-ancestor origin/main HEAD; echo "main exit=$?"
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping && git rev-parse HEAD
  期待: 2行目の出力が空（空でなければ `BLOCKED: 手順1 枝が既にある`）。4行目に `worktrees/salesanchor/release-invoice-portfolio-r3-shipping` が出る。5行目は衝突なし（衝突したら `git merge --abort` して `BLOCKED: merge conflict <ファイル名>`）。6行目 `pr-branch exit=0`・7行目 `main exit=0`。

手順2 実装前点検
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping && grep -c '^    ("POST", "/api/v1/invoices/preview"): _PENDING,$' backend/app/realtime/topics.py
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping && grep -c "draft-shipping-quotes" backend/app/realtime/topics.py
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping && grep -c "draft-shipping-quotes" backend/app/routers/invoices.py
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping && test -f docs/handoff/invoice-create-portfolio/card-R3-fix1.md; echo "card exit=$?"
  期待: 1、0、1以上、`card exit=0`。外れたら `BLOCKED: 手順2`。

手順3 （手順1 で main の取り込みは済み。この手順は無い）

手順4 backend/app/realtime/topics.py を Edit ツールで直す（1行足すだけ）
  変更前（ちょうど1か所）:
    ("POST", "/api/v1/invoices/preview"): _PENDING,
  変更後（2行。1行目は変更前と同じ・字下げは4つ）:
    ("POST", "/api/v1/invoices/preview"): _PENDING,
    ("POST", "/api/v1/invoices/draft-shipping-quotes"): "読むだけ。請求書の作成画面が送料の一覧を読む道で、DB に書かず、他の画面へ合図を出す相手もいない（design-v2 §3-9）",

手順5 道具と試験（~/venv312 が無いときは card-R3 の手順4 と同じ命令で作る）
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping && ~/venv312/bin/ruff check backend/app/realtime/topics.py 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping/backend && ~/venv312/bin/python -m pytest -q -p no:cacheprovider tests/test_realtime_topics.py tests/test_invoice_draft_shipping.py tests/test_fedex_rates.py 2>&1 | tail -10
  期待: ruff `All checks passed!`。pytest は failed 0・error 0。

手順6 変えたファイル
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping && git status --short | tail -10
  期待: ` M backend/app/realtime/topics.py` だけ（.claude-pipeline/active-work.d/ の未追跡は除く）。ほかが出たら `BLOCKED: 範囲外のファイル`。

手順7 記録と送り出し
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping && git add backend/app/realtime/topics.py && git config user.name "shingo-cc" && git config user.email "shingo-cc@users.noreply.github.com" && git commit -q -m "fix(realtime): list draft-shipping-quotes as a no-signal read-only route (invoice-portfolio R3 fix1)" && git log --oneline -3 | tail -3
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping && git push -u origin release/invoice-portfolio-r3-shipping 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping && git rev-parse HEAD
  push は --no-verify・force を付けない。止められたら言い換えず `BLOCKED: push`。

## 2. 想定される分かれ道

- 停止する: 手順1・2・6 の期待外れ／手順5 で failed・error（試験を直さず最後の 10 行を貼って `BLOCKED: pytest`）／見張りに止められた（言い換えない）。
- 記録して続ける: ruff が I（並び順）だけを出した → `~/venv312/bin/ruff check --fix --select I backend/app/realtime/topics.py` を流して結果を書く。

## 3. 報告

1 行目 `RECEIVED invoice-portfolio-R3-fix1 HEAD=<手順1 の後の git rev-parse HEAD の40桁>`。手順1・2・4〜7 の出力をそのまま貼る（1500 字を超えるときは手順1・5・7 を優先）。最後の行 `DONE` か `BLOCKED: 理由`。秘密の値は貼らない。sleep しない。PR は作らない。

## 4. 触らない範囲

backend/app/realtime/topics.py の上の1行以外、ほかのすべてのファイル（このカードの commit と main の取り込みで入るものを除く）。migrations/・deploy.yml・scripts/。

END OF CARD
