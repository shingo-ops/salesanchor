# 実装の手順書 — 予定のカルテ 直し1（card-secretary-karte-fix1）

- 設計: [design.md](design.md) ／ 現在地: [recon.md](recon.md) ／ 親: [../card.md](../card.md)
- 状態: 手順書（Opus 作成 2026-11-15）。PO 実装承認あり（2026-11-15 チャット「1」。design.md の「状態」）。
- ブランチ `release/secretary-karte-fix1-impl`。PR は作らない（Opus が作る）。危険 PR ではない（migrations・deploy.yml・本番 scripts を触らない）。
- 行番号と「前」の文面はすべて origin/main = 65a2bb376 のもの。

## 読んだ節

- docs/handoff/design-partner-card-ops/guards/00-common.md ○
- docs/handoff/design-partner-card-ops/guards/03-file.md ○
- docs/handoff/design-partner-card-ops/guards/10-executor.md ○
- docs/handoff/design-partner-card-ops/guards/11-lint.md ○

## 受領確認

着手前に、報告の 1 行目へ「受領確認: card-secretary-karte-fix1 を読んだ」と書く。

## この便で決めたこと

|決めたこと|理由・出典|
|---|---|
|`settle_dates` は例外を出さず、時刻として読めない始まり・終わりを null にする|design.md §3・§5 案 A|
|片方だけ時差の印が無く比べられない（`TypeError`）ときは終わりを null にする|design.md §3 (4)・§6|
|呼ぶ側 `backend/app/routers/assistant.py` は触らない（`try`/`except` は残す）|design.md §3|
|古い画面の道・`merge_karte`・`next_ask`・容器・画面は触らない|design.md §2|

## やること（この順）

### 1. 準備

- (1a) `cd /Users/tanizawashingo/salesanchor 2>/dev/null || cd "$(git rev-parse --show-toplevel)"; git fetch origin main`
- (1b) `git branch --list release/secretary-karte-fix1-impl` の出力が空であること。空でなければ `BLOCKED: 同名のブランチがある` で止まる。
- (1c) `bash scripts/new-worktree.sh release/secretary-karte-fix1-impl`（`--claude` は付けない）
- (1d) `git worktree list` に `$HOME/worktrees/salesanchor/release-secretary-karte-fix1-impl` があること。以下この場所を `$REPO` と書く（`REPO="$HOME/worktrees/salesanchor/release-secretary-karte-fix1-impl"`）。以降のコマンドはすべて `cd "$REPO"` してから流す。
- (1e) `./scripts/dev/executor-preflight.sh`。クラウドでは [1/3]・[2/3] が FAIL でもよい。[3/3] と [4/4] は OK であること。OK でなければ `BLOCKED:` で止まる。
- (1f) 次の出力が空であること（空でなければ `NEEDS_DECISION: 65a2bb376 から変わったファイル（一覧）` で止まる）:

```
git diff --stat 65a2bb376 HEAD -- backend/app/services/secretary_karte.py backend/tests/test_assistant_karte.py backend/app/schemas/assistant.py backend/app/routers/assistant.py
```

- (1g) `mkdir -p /tmp/CC報告ファイル`

### 2. 編集のきまり

- 書き換えは 1 か所ずつ。「前」の文面がファイルの中にちょうど 1 回だけあることを確かめてから「後」に置き換える。0 回か 2 回以上なら `BLOCKED: 前が一致しない（ファイル名・節の番号）` で止まる。
- 書いていない行は触らない。

### 3. `backend/app/services/secretary_karte.py`（:39-54 の `settle_dates` を置き換える）

前:

```python
def settle_dates(ev: IntentEvent) -> IntentEvent:
    """日時の検査（design.md §4-3 ⑤）。読めなければ ValueError / TypeError をそのまま出す（呼ぶ側が 502）。

    終日で終わりが空なら終わり＝始まり。終わり < 始まりなら終わりを null に戻す（もう一度聞く）。+1 時間は足さない。
    """
    if ev.start is None:
        if ev.end is not None:
            parse_iso(ev.end)
        return ev
    start = parse_iso(ev.start)
    end_text = ev.end
    if ev.is_all_day and end_text is None:
        end_text = ev.start
    if end_text is not None and parse_iso(end_text) < start:
        end_text = None
    return ev.model_copy(update={"end": end_text})
```

後:

```python
def _readable_time(value: str | None) -> str | None:
    """時刻として読めない文字は null にする（fix1/design.md §3。AI が「わからない」を時刻の欄に入れる場合）。"""
    if value is None:
        return None
    try:
        parse_iso(value)
    except ValueError:
        return None
    return value


def settle_dates(ev: IntentEvent) -> IntentEvent:
    """日時の検査（design.md §4-3 ⑤・fix1/design.md §3）。例外は出さない。

    始まり・終わりが時刻として読めなければ null に戻す（もう一度聞く）。終日で終わりが空なら終わり＝始まり。
    終わり < 始まり、または片方だけ時差の印が無く比べられなければ、終わりを null に戻す。+1 時間は足さない。
    """
    start_text = _readable_time(ev.start)
    end_text = _readable_time(ev.end)
    if start_text is None:
        return ev.model_copy(update={"start": None, "end": end_text})
    if ev.is_all_day and end_text is None:
        end_text = start_text
    if end_text is not None:
        try:
            if parse_iso(end_text) < parse_iso(start_text):
                end_text = None
        except TypeError:
            end_text = None
    return ev.model_copy(update={"start": start_text, "end": end_text})
```

### 4. `backend/tests/test_assistant_karte.py`

#### 4-1. :105-106 を置き換える

前:

```python
    with pytest.raises(ValueError):
        settle_dates(_ev(title="t", start="あした"))
```

後:

```python
    # fix1: 時刻として読めない文字は null（例外を出さない）
    assert settle_dates(_ev(title="t", start="あした")).start is None
    assert settle_dates(_ev(title="t", start="あした", end=E)).end == E
    assert settle_dates(_ev(title="t", start=S, end="わからない")).end is None
    # 片方だけ時差の印が無く比べられないときは終わりを null
    assert settle_dates(_ev(title="t", start=S, end="2026-11-02T11:00:00")).end is None
```

#### 4-2. :221-227 を置き換える

前:

```python
@pytest.mark.asyncio
async def test_unreadable_start_on_new_path_is_502(allowed, monkeypatch, meet):
    meet(False)
    _mock_agent(monkeypatch, _respond(200, _event(title="t", start="あした")))
    resp = await allowed.post(URL, json={"text": "a", "karte": None})
    assert resp.status_code == 502
    assert resp.json()["detail"] == {"code": "unreadable"}
```

後:

```python
@pytest.mark.asyncio
async def test_unreadable_start_on_new_path_is_200_and_asks_start(allowed, monkeypatch, meet):
    meet(False)
    _mock_agent(monkeypatch, _respond(200, _event(title="t", start="あした")))
    resp = await allowed.post(URL, json={"text": "a", "karte": None})
    assert resp.status_code == 200, resp.text
    d = resp.json()["draft"]
    assert (d["title"], d["start"], d["ask"], d["ask_count"]) == ("t", None, "start", 1)


@pytest.mark.asyncio
async def test_unreadable_end_after_two_asks_shows_final_draft(allowed, monkeypatch, meet):
    # fix1 F1: T10 の 3 通目。AI が終わりに「わからない」の文字を入れても確かめの欄（ask null・終わり空）
    meet(False)
    karte = _karte(title="棚卸し", start=S, asked="end", asked_count=1)
    _mock_agent(monkeypatch, _respond(200, _event(end="うーん")))
    resp = await allowed.post(URL, json={"text": "うーん", "karte": karte})
    assert resp.status_code == 200, resp.text
    d = resp.json()["draft"]
    assert (d["ask"], d["ask_count"], d["end"]) == ("end", 2, None)
    karte["asked_count"] = 2
    _mock_agent(monkeypatch, _respond(200, _event(end="わからない")))
    resp = await allowed.post(URL, json={"text": "わからない", "karte": karte})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["kind"] == "event"
    d = data["draft"]
    assert (d["ask"], d["end"], d["title"], d["start"]) == (None, None, "棚卸し", S)
```

### 5. 確かめ（どれも生の出力を /tmp/CC報告ファイル/ に保存し、全文を読んでから判定する）

- (5a) `cd "$REPO/backend" && uv run --no-project --python 3.12 --with ruff ruff check app/ tests/test_assistant_karte.py > /tmp/CC報告ファイル/ruff.txt 2>&1; echo "exit=$?"` → exit=0
- (5b) `cd "$REPO/backend" && ENVIRONMENT=test uv run --no-project --python 3.12 --with-requirements requirements.txt --with-requirements requirements-dev.txt python -m pytest --no-cov tests/test_assistant_router.py tests/test_assistant_karte.py tests/test_assistant_rules_router.py tests/test_assistant_karte_pg.py -q > /tmp/CC報告ファイル/pytest.txt 2>&1; echo "exit=$?"` → exit=0。最後の 1 行（passed・skipped の数）を報告に貼る。
- (5c) `cd "$REPO" && git diff --check > /tmp/CC報告ファイル/diff-check.txt 2>&1; echo "exit=$?"` → exit=0
- (5d) `cd "$REPO" && git diff --stat` を報告に貼る。変わるのは `backend/app/services/secretary_karte.py` と `backend/tests/test_assistant_karte.py` の 2 つだけ。
- (5a) の ruff が `F401`（未使用の import）などで落ちたら、この手順書の書き損じだけ直す。手順書と違う作りに変えないと通らないときは `NEEDS_DECISION:` で止まる。

### 6. 記録（commit）と送り出し（push）

- (6a) `git -C "$REPO" status --short` を報告に貼る。期待は変更 2 個（上の 2 つ）。違えば `NEEDS_DECISION:`。
- (6b) `git -C "$REPO" add backend/app/services/secretary_karte.py` と `git -C "$REPO" add backend/tests/test_assistant_karte.py`（`git add -A`・`git add .` は使わない）。
- (6c) commit の文:

```
fix(secretary): treat unreadable event times as empty in the karte (ADR-1078 fix1)

- settle_dates no longer raises: unreadable start/end become null and are asked again
- end is cleared when it cannot be compared with start (naive vs aware)
- old screens (no karte key) keep the current behaviour

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
```

- (6d) `git -C "$REPO" log --oneline -1` を報告に貼る。
- (6e) `cd "$REPO" && bash scripts/dev/check-before-submit.sh > /tmp/CC報告ファイル/check-before-submit.txt 2>&1; echo "exit=$?"` → exit=0（落ちたら生の出力のパスを添えて `NEEDS_DECISION:`）
- (6f) `git -C "$REPO" push -u origin release/secretary-karte-fix1-impl`

## 触らない

- `backend/app/routers/assistant.py`（呼ぶ側の `try`/`except` も古い画面の道も）・`backend/app/schemas/assistant.py`（`parse_iso`・`KarteIn`・`IntentEvent`）
- `merge_karte`・`next_ask`・`backend/tests/test_assistant_router.py`・`backend/tests/test_assistant_karte_pg.py`
- 容器（`secretary-agent/`・`secretary-codex/`）・画面（`frontend/`）・`migrations/`・`.github/`・`deploy.yml`・本番の `scripts/`
- PR は作らない（Opus が作る）

## 想定される分かれ道

|起きたこと|すること|
|---|---|
|(1f) で 65a2bb376 から変わったファイルがある|直さずに `NEEDS_DECISION:` で一覧を出す|
|「前」がちょうど 1 回一致しない|`BLOCKED:` でファイル名と節の番号を出す|
|既存の試験（`test_assistant_router.py` など）が落ちる|直さずに、落ちた試験の名前と生の出力のパスを添えて `NEEDS_DECISION:`|
|(5a) の ruff で `pytest` の import が未使用と言われる|`pytest` は fixture と `pytest.mark` で今も使うので起きない想定。起きたら `NEEDS_DECISION:`|
|PG の試験が skipped|続けてよい。報告に書く|
|push が見張りに止められる|言い換えずに止められた文面を貼って `BLOCKED:`|

## Opus が合流の前に確かめること（実装役はしない）

- 差分の全文をこの手順書の「後」と照合する。
- CI の結果（backend の試験・PG の試験が passed）。
- マージ前の審査役（reviewer・model opus）の判定。
- 本番反映の後: design.md §7 の F1（T10 を 3 回）・F4（見本 69 件・T1〜T9）・F5（予定の件数の前後）。

## 終わりの報告

- 1 行目: 「受領確認: card-secretary-karte-fix1 を読んだ」
- 途中で停止するときも、ここまでの観測を書いてから下の BLOCKED: か NEEDS_DECISION: の行で終える（続きの作業はしない）。
- 最後の行は次のどれか 1 つ:
  - `DONE: release/secretary-karte-fix1-impl を push（commit の短い番号）`
  - `BLOCKED: 理由（生の出力のパス）`
  - `NEEDS_DECISION: 決めてほしいこと（生の出力のパス）`
- 間に: (1e)〜(1f) の結果・§5 の各 exit と最後の行・§6 のファイルの数と `git log --oneline -1`。報告に書くのは観測した事実だけ（生の出力のパスを添える）。
- 1 つの発言は 600 文字以内。長いときは番号付きの発言に分ける。

END OF CARD
