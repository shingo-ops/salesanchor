本報告はカード card-impl-3 の実行結果である

## 土台
- 作業場所: /root/worktrees/salesanchor/release-permission-keys-known-missing
- 手順: git fetch origin → new-worktree.sh → git switch -C release/permission-keys-known-missing origin/release/permission-keys-known-missing
- 切替直後の `git rev-parse HEAD`: eb2236f014bb79ab5b25c65468efae0e10621091（eb2236f01 で始まる。合っている）
- 6 ファイルの commit: af606f903

## §0 の grep の生出力
```
release/permission-keys-known-missing
659:    dependencies=[Depends(require_permission("customers.edit"))],
backend/app/routers/discord_channel_invite.py:63:    dependencies=[Depends(require_permission("leads.edit"))],
backend/app/routers/discord_role_resync.py:43:    dependencies=[Depends(require_permission("leads.edit"))],
69:    dependencies=[Depends(require_permission("companies.view"))],
13:KNOWN_MISSING: dict[str, str] = {
21:    """コードが求めるキーのうち、一覧にも KNOWN_MISSING にも無いものを名前順で返す。"""
24:    return sorted(REGISTERED_PERMISSION_KEYS - in_catalog - set(KNOWN_MISSING))
24:    assert len(KNOWN_MISSING) <= 3
56:    monkeypatch.setattr(catalog, "REGISTERED_PERMISSION_KEYS", {"a.view", "b.view", "companies.view"})
```
想定どおり（各 1 行ずつ）。

## §3 の生出力
### pytest（tail -80 の末尾。前半は coverage 表で長いため、最後の 3 行だけ貼る。全文は /tmp/pytest.txt）
```
TOTAL                                                45977  32451    29%
FAIL Required test coverage of 60% not reached. Total coverage: 29.42%
12 passed, 2 warnings in 32.65s
```
失敗 0。coverage 閾値の行は一部だけ流したためで、失敗に数えない。

### old_keys
```
old_keys_lines=0
```

### git diff --stat（比較先 d948cf9c7。main が先に進んだため Opus 指示）
```
 backend/app/auth/permission_catalog.py             |  10 +-
 backend/app/routers/contacts.py                    |   2 +-
 backend/app/routers/discord_channel_invite.py      |   2 +-
 backend/app/routers/discord_role_resync.py         |   2 +-
 backend/app/routers/duplicates.py                  |   2 +-
 backend/tests/test_permission_catalog.py           |  29 +++-
 .../card-impl-3.md                                 | 162 +++++++++++++++++++++
 .../design.md                                      |  73 +++++++++-
 8 files changed, 269 insertions(+), 13 deletions(-)
```
（card-impl-3.md・design.md は土台の枝にすでに入っている文書。d948cf9c7 との差に出るだけ）

### numstat（backend）
```
3	7	backend/app/auth/permission_catalog.py
1	1	backend/app/routers/contacts.py
1	1	backend/app/routers/discord_channel_invite.py
1	1	backend/app/routers/discord_role_resync.py
1	1	backend/app/routers/duplicates.py
28	1	backend/tests/test_permission_catalog.py
```
backend の変更は 6 ファイルだけ。消した行は各 1〜7 行（permission_catalog.py は 7 行。カード想定の 1〜6 を 1 行超えるが、カード §1 (5) の前 7 行どおりの置き換えによる）。

### check-before-submit（tail の末尾）
```
合計 11.9 秒 / 必須 16 件を表示 / 流した検査 18 件 / 落ちた検査 0 件
注意: この枝は main より遅れている。main を取り込んでから流すと CI と同じ結果になる
結果: ○ 流した検査は全部通りました（終了コード 0）
```
（Python 3.11 / CI は 3.12 の注記あり。最終判定は CI）

## 最終 HEAD
この報告を commit する前の HEAD: af606f903（報告の commit 後の sha は push 結果を参照）

DONE
