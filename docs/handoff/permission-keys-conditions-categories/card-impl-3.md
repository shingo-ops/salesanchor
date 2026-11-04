# card: 便3 一覧に無い 3 つの鍵を、一覧にある鍵へ付け替える（クラウドの Sonnet 向け）

本カードの許可・禁止は、過去便のカードの禁止条項をすべて上書きする。カードに無い作業はしない。

## カードチェック（design-partner.md §5.5）
| # | 項目 | 結果 |
|---|---|---|
| 0 | 冒頭に ○× | ○ |
| 1 | 記号を `` ` `` で囲む | ○ |
| 2 | PR | ○ 担当は PR を作らない。Opus が差分を読んでから作る |
| 3 | 報告先 | ○ 生出力入りの報告ファイル（§5） |
| 4 | 目的は 1 つ | ○ 4 本の道の鍵を、一覧にある鍵へ付け替える |
| 5 | 土台のブランチ | ○ 既存の `origin/release/permission-keys-known-missing`（§0）。新しいブランチは作らない |
| 6 | 形は例で示す | ○ §1 に変更前後の行 |
| 7 | 合格基準に出力 | ○ §3 |
| 8 | 対象の名前 | ○ 触ってよいファイル 7 つ（§1 の 6・§5 の報告 1） |
| 9 | 出力の上限 | ○ tail -80 |
| 10 | 受付と終わりの合図 | ○ 受領確認は §5 の 1 行目。最後の行は `DONE` か、`BLOCKED:` に理由を続けた行か、`NEEDS_DECISION:` に問いを続けた行 |
| 11 | 想定値は実測 | ○ §0 の想定は 2026-11-04 origin/main d948cf9c7 の実物 |
| 12 | 止まる条件 2 段 | ○ §4 |
| 13 | sleep なし・Write/Edit・見張りで止まったら言い換えない | ○ |

- 設計: [design.md](design.md) §11（自己審査 APPROVE）
- PO の実装承認: 2026-11-04 チャット「1」（3 つとも案のとおり付け替える）
- 作業ブランチ: `release/permission-keys-known-missing`（設計の文書が先に入っている。その上に積む）

## 読んだ節（docs/handoff/design-partner-card-ops/guards/）
| 節 | 引いたこと | 反映 |
|---|---|---|
| guards/00-common.md | 出力に上限（tail -80）・sleep しない・パスは一字一句そのまま | ○（§3・§4） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○（§1・§5） |
| guards/10-executor.md | 止まったら言い換えず、停止した手順・最後のコマンド・理由を報告する | ○（§4・§5） |

## §0 着手前の点検（違えば NEEDS_DECISION で止まる）
```
git fetch origin
git checkout -B release/permission-keys-known-missing origin/release/permission-keys-known-missing
git rev-parse --abbrev-ref HEAD
grep -n 'require_permission("customers.edit")' backend/app/routers/contacts.py
grep -n 'require_permission("leads.edit")' backend/app/routers/discord_channel_invite.py backend/app/routers/discord_role_resync.py
grep -n 'require_permission("companies.view")' backend/app/routers/duplicates.py
grep -n "KNOWN_MISSING" backend/app/auth/permission_catalog.py
grep -n "len(KNOWN_MISSING)" backend/tests/test_permission_catalog.py
grep -n '"companies.view"' backend/tests/test_permission_catalog.py
```
想定（どれも 1 行ずつ。行番号は参考で、止まる条件にしない）:
- `contacts.py` に `require_permission("customers.edit")` が 1 行
- `discord_channel_invite.py` と `discord_role_resync.py` に `require_permission("leads.edit")` が 1 行ずつ
- `duplicates.py` に `require_permission("companies.view")` が 1 行
- `permission_catalog.py` の `KNOWN_MISSING: dict[str, str] = {` の中に 3 つの鍵
- `test_permission_catalog.py` に `assert len(KNOWN_MISSING) <= 3` と、`{"a.view", "b.view", "companies.view"}` を含む行

## §1 コードの変更（6 ファイル。Edit ツールで、前後の文字の一致で置き換える）
(1) `backend/app/routers/contacts.py`
- 前: `    dependencies=[Depends(require_permission("customers.edit"))],`
- 後: `    dependencies=[Depends(require_permission("customers.update"))],`

(2) `backend/app/routers/discord_channel_invite.py`
- 前: `    dependencies=[Depends(require_permission("leads.edit"))],`
- 後: `    dependencies=[Depends(require_permission("leads.update"))],`

(3) `backend/app/routers/discord_role_resync.py`
- (2) と同じ置き換え。

(4) `backend/app/routers/duplicates.py`
- 前: `    dependencies=[Depends(require_permission("companies.view"))],`
- 後: `    dependencies=[Depends(require_permission("customers.view"))],`

(5) `backend/app/auth/permission_catalog.py`
- 前（注記 2 行と dict 全体）:
```python
# 既知の欠け。キー: 残す理由。PO が扱いを決めたら、その PR でここから消し、
# backend/tests/test_permission_catalog.py の上限の数字を下げる（design.md §5-3）。
KNOWN_MISSING: dict[str, str] = {
    "companies.view": "PO 判断待ち: duplicates.py の経路。一覧に足すか、別のキーへ付け替えるか",
    "customers.edit": "PO 判断待ち: contacts.py の経路。一覧に足すか、別のキーへ付け替えるか",
    "leads.edit": "PO 判断待ち: discord_channel_invite.py・discord_role_resync.py の経路。一覧に足すか、別のキーへ付け替えるか",
}
```
- 後:
```python
# 既知の欠け。キー: 残す理由。今は空（design.md §11 で 3 キーを付け替えた）。
# 足すには PO の判断と、backend/tests/test_permission_catalog.py の上限の数字を変える PR が要る（design.md §5-3）。
KNOWN_MISSING: dict[str, str] = {}
```

(6) `backend/tests/test_permission_catalog.py`
- C2 の前: `    assert len(KNOWN_MISSING) <= 3`
- C2 の後: `    assert len(KNOWN_MISSING) == 0`
- C4 の前:
```python
    monkeypatch.setattr(catalog, "REGISTERED_PERMISSION_KEYS", {"a.view", "b.view", "companies.view"})
```
- C4 の後（1 行足す）:
```python
    monkeypatch.setattr(catalog, "REGISTERED_PERMISSION_KEYS", {"a.view", "b.view", "companies.view"})
    monkeypatch.setattr(catalog, "KNOWN_MISSING", {"companies.view": "試験"})
```
- ファイルの末尾に C5 を足す:
```python
_REASSIGNED_ROUTES = [
    ("POST", "/api/v1/contacts/{contact_id}/channel-acknowledge-duplicate", "customers.update"),
    ("POST", "/api/v1/discord/channel-invite/{lead_id}", "leads.update"),
    ("POST", "/api/v1/discord/sync-role/{lead_id}", "leads.update"),
    ("GET", "/api/v1/companies/duplicates", "customers.view"),
]


def test_reassigned_routes_require_catalog_keys():
    """C5: 一覧に無かった 3 キーを、一覧にある鍵へ付け替えた（design.md §11-3）。"""
    from app.main import app

    for method, path, key in _REASSIGNED_ROUTES:
        found = [
            r for r in app.routes
            if getattr(r, "path", None) == path and method in getattr(r, "methods", set())
        ]
        assert len(found) == 1, f"route not found: {method} {path}"
        keys = [
            set(dep.call.required_permission_keys)
            for dep in found[0].dependant.dependencies
            if getattr(dep.call, "required_permission_keys", None) is not None
        ]
        assert keys == [{key}], f"{method} {path}: {keys}"
```

## §2 触らないもの
- 上の 6 ファイル以外のコード・画面・DB・migration・CI 設定。
- `backend/tests/test_conditions_permission_keys.py`（読むだけ。C5 の探し方の手本）。

## §3 確かめ（出力はファイルへ。tail -80 で読む）
Python は 3.12 の venv を使う（`python3.12 -m venv /tmp/venv312` → `backend/requirements.txt` と試験の道具を入れる）。
```
cd backend && /tmp/venv312/bin/python -m pytest tests/test_permission_catalog.py tests/test_conditions_permission_keys.py -q -p no:cacheprovider > /tmp/pytest.txt 2>&1; tail -80 /tmp/pytest.txt
cd .. && git grep -n -e 'require_permission("customers.edit")' -e 'require_permission("leads.edit")' -e 'require_permission("companies.view")' -- backend/app > /tmp/old-keys.txt 2>&1; echo "old_keys_lines=$(grep -c . /tmp/old-keys.txt)"
git diff --stat origin/main > /tmp/diffstat.txt 2>&1; tail -80 /tmp/diffstat.txt
git diff origin/main --numstat -- backend > /tmp/numstat.txt 2>&1; tail -80 /tmp/numstat.txt
bash scripts/dev/check-before-submit.sh > /tmp/cbs.txt 2>&1; tail -80 /tmp/cbs.txt
```
- 合格: pytest で失敗 0（末尾の coverage の閾値の行は、一部だけ流したためなので失敗に数えない）。`old_keys_lines=0`。numstat で backend の変更は 6 ファイルだけ、消した行の数は各ファイル 1〜6 行（大きな削除が無い）。check-before-submit が成功で終わる。
- 値が合わないときは止まらず、生の出力を報告に貼る（判定は Opus が行う）。

## §4 止まる条件
- 1 段目（NEEDS_DECISION で止まる）: §0 の想定の文字列が見つからない。§1 の 6 ファイル以外を変えないと試験が通らない。
- 2 段目（BLOCKED で止まる）: 見張り（hook）に止められた（言い換えない。止まった手順・最後のコマンド・理由の原文を報告する）。push が断られた。§3 の pytest が 2 回直しても通らない（原因の生出力を報告に貼る）。
- 待つために sleep しない。

## §5 報告
- `docs/handoff/permission-keys-conditions-categories/impl-report-4.md` を Write ツールで作る。同じブランチにコミットして `git push origin release/permission-keys-known-missing` する（force は使わない）。
- 中身の 1 行目: `本報告はカード card-impl-3 の実行結果である`
- 中身: §0 の生出力、§3 の tail の生出力すべて、最後の HEAD の sha、止まったときは「止まった手順の番号／最後に流したコマンド／止まった理由」。
- 停止したとき: 報告の中に「停止した手順の番号／最後に流したコマンド／停止した理由の原文」を書き、それでもコミットと push をして報告を届ける。
- 最後の行: `DONE` か、`BLOCKED:` に理由を続けた 1 行か、`NEEDS_DECISION:` に問いを続けた 1 行。
- 受領確認: 報告の 1 行目（上の「本報告は…」の行）が受領確認を兼ねる。

END OF CARD
- コミットの文の末尾: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`

## §6 マージのあと（Opus が行う。担当はしない）
1. backend の反映（deploy.yml）の成功を Actions の記録で確かめる。
2. 反映から 300 秒あと以降に、Grafana 経由で `salesanchor_permission_keys_missing{job="backend"}` が 0 であることを確かめる（K8）。
3. 001 の所有者で Discord の案内の道が 403 にならないことを確かめる（K9）。
