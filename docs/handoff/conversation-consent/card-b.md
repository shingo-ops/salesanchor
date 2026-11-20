# 実装カード 便B: 見張りが「1」を末尾から必要なだけ（最大 64MB）読んで見つける

正本: docs/handoff/conversation-consent/design.md §16-3(b)・§16-7 K77・K78・§16-8 便B。PO 実装承認 2026-11-20（返事「1」。便C → 便A → 便B の順）。
ブランチ: release/consent-k0-bin-b（origin/main から新しく作る）。
行番号の基準:
- docs/handoff/conversation-consent/hooks/consent_check.py は origin/main 50f305fc9 の値（便A は触らない）。
- scripts/dev/consent-unit-tests.py は便A の後（153ec193c）の値。
- docs/handoff/conversation-consent/design.md は設計 v6.2 の合流の後の値。
このカード自身も、同じ commit で docs/handoff/conversation-consent/card-b.md として足す（下の「作業場所の作り方」の 3）。

## 作業場所の作り方（クラウド）

1. `git fetch origin`
2. `bash scripts/new-worktree.sh release/consent-k0-bin-b`
3. worktree に移る（`cd` で new-worktree.sh が出した場所へ）。そこで `git show origin/release/consent-k0-card-b:docs/handoff/conversation-consent/card-b.md > docs/handoff/conversation-consent/card-b.md`
4. 以後の作業はすべてこの worktree の中。clone のまま commit しない。
5. 作業前の点検（executor-preflight.sh）はクラウドでは流さない（Opus が手元で流し済み）。

## 触るファイル（これ以外は触らない）

1. docs/handoff/conversation-consent/hooks/consent_check.py
2. scripts/dev/consent-unit-tests.py
3. docs/adr/ADR-1033-conversation-consent-ticket.md（18 行目だけ）
4. docs/adr/README.md（`node scripts/generate-adr-index.js` で差分が出たときだけ）
5. docs/handoff/conversation-consent/design.md（26・75・80・81 行目だけ）
6. docs/handoff/conversation-consent/card-b.md（このカードの写し。中身は変えない）

触らない: scripts/dev/consent-audit.py（末尾 4MB の読みが別にあるが、便B の対象外）、scripts/dev/test-agent-hooks.sh、scripts/dev/permission-delegation-tests.py、po-apply-consent.sh、ワークフロー、ほかの ADR、design.md の上の4行以外、~/.claude 配下すべて、.claude-pipeline/active-work.d/。
変えないもの（設計 §16-3(b)）: 判定 1・2・5・7〜10、同意票の文法（parse_ticket）、除外（excluded）、台帳（_ledger_consume）、_is_human・_is_compact・_is_typed_one・_parse_ts。

## 手順 consent_check.py

### H1. 上限の定数を足す（:20 の直後）

変更前（:20-21）:
```python
TAIL_BYTES = 4 * 1024 * 1024
WINDOW = datetime.timedelta(minutes=30)
```
変更後:
```python
TAIL_BYTES = 4 * 1024 * 1024
MAX_TAIL_BYTES = 64 * 1024 * 1024  # 読む範囲の上限（design §16-3(b)・R14）。上げる・外すときは審査をやり直す
WINDOW = datetime.timedelta(minutes=30)
```

### H2. `_read_tail_records` を読み足しの部品に置き換える（:140-163 の関数まるごと）

変更前は :140 `def _read_tail_records(path):` から :163 `return recs` まで。これを消し、同じ場所に次を置く。
```python
class _Unparsable:
    """JSON でない行の印。捨てずに並びの元の位置に残す（design §16-3(b)）。"""
    __slots__ = ()


UNPARSABLE = _Unparsable()


class _TailReader:
    """記録を末尾から段々に読み足す（4・8・16・32・64MiB。design §16-3(b)）。

    - 大きさは最初に1回だけ測る（fstat）。判定の途中で記録が伸びても、伸びた分は読まない。
    - 読み始めが 0 でない段では、最初の改行までを carry に取っておき、次の段で足した部分とつないで1行に戻す。
    - 改行で終わらない最後の行は捨てる。
    - どの行も JSON にするのは1回だけ。JSON でない行は UNPARSABLE を置く。
    """

    def __init__(self, f):
        self.f = f
        self.size = os.fstat(f.fileno()).st_size
        self.start = self.size   # 読んだ範囲の先頭のバイト位置
        self.carry = b""         # 前の段で捨てた、途中から始まる最初の行
        self.tail_cut = False    # 改行で終わらない最後の行を捨て終えたか
        self.recs = []           # 読んだ行（古い順）
        self.step = 0            # 最後に読んだ段の大きさ（0 は未読）
        self.read_bytes = 0      # 末尾から読んだ大きさ
        self.more()

    def exhausted(self):
        return self.start == 0 or self.step >= MAX_TAIL_BYTES

    def more(self):
        """次の段を読む。読めたら True、もう読めなければ False。"""
        if self.step and self.exhausted():
            return False
        self.step = TAIL_BYTES if not self.step else self.step * 2
        new_start = max(0, self.size - self.step)
        self.f.seek(new_start)
        data = self.f.read(self.start - new_start) + self.carry
        self.start = new_start
        self.read_bytes = self.size - new_start
        self.carry = b""
        if not self.tail_cut:
            j = data.rfind(b"\n")
            if j < 0:
                return True  # まだ最後の行の途中。次の段で続きを捨てる
            data = data[: j + 1]
            self.tail_cut = True
        if self.start > 0:
            i = data.find(b"\n")
            if i < 0:
                self.carry = data
                return True
            self.carry = data[:i]
            data = data[i + 1:]
        new = []
        for raw in data.split(b"\n"):
            if not raw.strip():
                continue
            try:
                new.append(json.loads(raw.decode("utf-8")))
            except Exception:
                new.append(UNPARSABLE)
        self.recs = new + self.recs
        return True


def _oldest_ts_expired(recs, now):
    """範囲の中で timestamp の読める一番前の行が、now − 30 分より前なら True（design §16-3(b) 判定の順 1）。"""
    for r in recs:
        if isinstance(r, dict):
            ts = _parse_ts(r.get("timestamp"))
            if ts is not None:
                return now - ts > WINDOW
    return False
```

### H3. `_check_inner` の 3〜6 を読み足しの形にする（:276〜:303）

変更前（:276-303）は `# 3. 末尾 4MB` から、a_idx を探すループの後の `if a_idx is None: return False, "no_assistant_text"` まで。
```python
    # 3. 末尾 4MB
    recs = _read_tail_records(real_tp)
    if recs is None:
        return False, "transcript_unparsable"
    # 4. 最後の人の入力 H
    ...（:281-303 そのまま）
    if a_idx is None:
        return False, "no_assistant_text"
```
変更後（:304 の `msg = recs[a_idx].get("message")` から下は変えない）:
```python
    # 3〜6. 末尾から必要なだけ（最大 MAX_TAIL_BYTES）読む（design §16-3(b)）
    with open(real_tp, "rb") as f:
        rd = _TailReader(f)
        while True:
            info["read_bytes"] = rd.read_bytes
            recs = rd.recs
            # 4. 最後の人の入力 H（JSON でない行の印は _is_human が False なので飛ばす）
            h_idx = None
            for i in range(len(recs) - 1, -1, -1):
                if _is_human(recs[i]):
                    h_idx = i
                    break
            if h_idx is None:
                if rd.exhausted() or _oldest_ts_expired(recs, now):
                    return False, "no_human_input"
                rd.more()
                continue
            H = recs[h_idx]
            info["h_uuid"] = H.get("uuid")
            info["h_timestamp"] = H.get("timestamp")
            info["h_typed_one"] = _is_typed_one(H)
            # 5. H が typed の「1」
            if not info["h_typed_one"]:
                return False, "h_not_typed_one"
            # 6. H の直前の AI の行
            a_idx = None
            for i in range(h_idx - 1, -1, -1):
                r = recs[i]
                if isinstance(r, dict) and r.get("type") == "assistant" and not r.get("isSidechain"):
                    a_idx = i
                    break
            if a_idx is not None:
                break
            if rd.exhausted():
                return False, "no_assistant_text"
            h_ts = _parse_ts(H.get("timestamp"))
            if h_ts is not None and now - h_ts > WINDOW:
                return False, "expired"
            rd.more()
    # JSON でない行が a_idx から末尾までにあれば不可（a_idx より前は判定に使わない。R19）
    if any(r is UNPARSABLE for r in recs[a_idx:]):
        return False, "transcript_unparsable"
```
注意:
- `rd.more()` が False を返すのは exhausted() のときだけで、その前に exhausted() を見て return しているので、ループは必ず終わる。
- :304 以降の `msg = recs[a_idx]...`・:313-315 の間の確かめ・判定 7〜10 は1文字も変えない。

### H4. probe に read_bytes を足す（check() の :354 と :377-378）

変更前（:354）: `    info = {"h_uuid": None, "h_timestamp": None, "h_typed_one": None}`
変更後: `    info = {"h_uuid": None, "h_timestamp": None, "h_typed_one": None, "read_bytes": None}`

変更前（:377-378）:
```python
            if hi.get("tool_use_id"):
                probe["tool_use_id"] = hi.get("tool_use_id")
```
変更後:
```python
            if hi.get("tool_use_id"):
                probe["tool_use_id"] = hi.get("tool_use_id")
            if info.get("read_bytes") is not None:
                probe["read_bytes"] = info["read_bytes"]
```
理由: 便A の K79 の数えは `"read_bytes" not in p` で対象を外す（scripts/dev/consent-audit.py の k79_counts）。読む前に止めた probe（agent_id など）にはキーを付けない。

### H5. 先頭の説明文

:4 の `設計: docs/handoff/conversation-consent/design.md §4-1〜4-4（ADR-1033）。` を `設計: docs/handoff/conversation-consent/design.md §4-1〜4-4・§16-3(b)（ADR-1033）。` にする。

## 手順 consent-unit-tests.py

### U1. import に time を足す（:1）

変更前: `import sys, os, json, importlib.util, datetime, threading`
変更後: `import sys, os, json, importlib.util, datetime, threading, time`

### U2. T5-x の期待を「通る」に変える（:236・:243）

変更前（:236）: `# 4MB の境目`
変更後: `# 4MB の境目（便B の後は、30 分以内なら 4MB の外も読み足して見つける）`

変更前（:243）: `rep("T5-x", "止まる: 同意票が末尾 4MB の外 (%s)" % why, not ok)`
変更後: `rep("T5-x", "通る: 同意票が末尾 4MB の外でも、30 分以内なら読み足して見つける (%s)" % why, ok)`

### U3. K77・K78 を足す（:445 の K15-8 の rep の後（:446 は空行）、:447 の `print("DONE", flush=True)` の前。前に空行1つ）

```python
# K77・K78: 末尾から必要なだけ（最大 64MB）読む（design §16-3(b)・§16-7）
MiB = 1024 * 1024


def line_bytes(r):
    return (json.dumps(r, ensure_ascii=False) + "\n").encode("utf-8")


def big(ts, n):
    # 今の詰め物（:237）と同じ attachment の行。rendered の長さ n
    return common("attachment", ts, attachment={"type": "date"}, rendered="y" * n, renderedRole="user")


def fill_exact(ts, total, line=100000):
    """行の合計がちょうど total バイトになる詰め物の並び（1行は rendered が line 前後）。"""
    out = []
    while total > 0:
        r = big(ts, 0)
        o = len(line_bytes(r))
        rest = total - o
        assert rest >= 0, "fill_exact: 残り %d バイトが1行に足りない" % total
        if rest <= 2 * line:
            r["rendered"] = "y" * rest
            out.append(r)
            break
        r["rendered"] = "y" * line
        out.append(r)
        total -= len(line_bytes(r))
    return out


def mid_char(rec, ch):
    """rec の行の中で、ch の 1001 文字目の2バイト目の位置（行の先頭から）。"""
    b = line_bytes(rec)
    e = ch.encode("utf-8")
    return b.find(e) + len(e) * 1000 + 1


def cut_mid_char(path, boundary):
    """末尾から boundary バイトの境目が、日本語の文字の途中（UTF-8 の続きのバイト）か。"""
    with open(path, "rb") as f:
        data = f.read()
    return 0x80 <= data[len(data) - boundary] < 0xC0


def last_probe(h):
    ev = [json.loads(x) for x in open(os.path.join(h, ".claude/logs/agent-events.jsonl"))]
    return [e for e in ev if e["type"] == "consent_probe"][-1]


NOW70 = T0 + td(70)  # run() の既定の now

# (1) 同意票と「1」の後に 10MB の詰め物（30 分以内）→ 通る
(ok, why), h = run(std([CMD]) + fill_exact(T0 + td(20), 10 * MiB), CMD)
rep("K77-1", "通る: 「1」の後に 10MB の詰め物 (%s, read_bytes=%s)" % (why, last_probe(h).get("read_bytes")), ok)

# (2)・K78 同意票 → 70MiB の詰め物（1行 約 5KB、30 分以内）→ typed の「1」→ no_assistant_text、read_bytes=64MiB
h = newhome()
recs = [human("x", T0 - td(60)), atext(ticket([CMD]), T0)] + fill_exact(T0 + td(5), 70 * MiB, line=5000) + [human("1", T0 + td(10))]
p = write_tr(h, recs)
hi = {"session_id": "s1", "transcript_path": p, "tool_input": {"command": CMD}}
t = time.perf_counter()
(ok, why) = cc.check(hi, CMD, NOW70, home=h)
dt = time.perf_counter() - t
print("TIME K78 %.3f" % dt, flush=True)
rb = last_probe(h).get("read_bytes")
rep("K77-2", "止まる: 同意票が 64MiB の外 → no_assistant_text・read_bytes=64MiB (%s, %s)" % (why, rb), (not ok) and why == "no_assistant_text" and rb == 64 * MiB)
os.remove(p)

# (3) 人の入力が無く、詰め物 10MB がすべて 31 分より前 → no_human_input、read_bytes=4MiB ちょうど
(ok, why), h = run(fill_exact(NOW70 - td(31 * 60), 10 * MiB), CMD)
rb = last_probe(h).get("read_bytes")
rep("K77-3", "止まる: 人の入力が無く古い詰め物だけ → no_human_input・read_bytes=4MiB (%s, %s)" % (why, rb), (not ok) and why == "no_human_input" and rb == 4 * MiB)

# (4a) 段の境目（末尾 4MiB）が同意票の行の、日本語の文字の途中 → 通る
h = newhome()
tk = atext("あ" * 3000 + "\n" + ticket([CMD]), T0)
H1 = human("1", T0 + td(10))
after = 4 * MiB - (len(line_bytes(tk)) - mid_char(tk, "あ")) - len(line_bytes(H1))
p = write_tr(h, [human("x", T0 - td(60)), tk] + fill_exact(T0 + td(5), after) + [H1])
setup = cut_mid_char(p, 4 * MiB)
(ok, why), _ = run(None, CMD, home=h, tp=p)
rep("K77-4a", "通る: 境目が同意票の行の日本語の途中（境目の確かめ=%s） (%s)" % (setup, why), setup and ok)

# (4b) 段の境目が H の行の、日本語の文字の途中 → 通る
h = newhome()
H2 = human("1", T0 + td(10))
H2["slug"] = "あ" * 3000
tail = fill_exact(T0 + td(20), 4 * MiB - (len(line_bytes(H2)) - mid_char(H2, "あ")))
p = write_tr(h, [human("x", T0 - td(60)), atext(ticket([CMD]), T0), H2] + tail)
setup = cut_mid_char(p, 4 * MiB)
(ok, why), _ = run(None, CMD, home=h, tp=p)
rep("K77-4b", "通る: 境目が H の行の日本語の途中（境目の確かめ=%s） (%s)" % (setup, why), setup and ok)

# (4c) 古い詰め物 4MiB 以上 → 同意票 → queued の人の入力（境目をまたぐ）→ 約 4MiB の詰め物 → 「1」
#      → input_between_ticket_and_one、read_bytes=8MiB（つなぎ戻しを誤ってこの行が消えると通ってしまう向き）
h = newhome()
Q = queued_human("待って" * 2000, T0 + td(5))
H3 = human("1", T0 + td(10))
after = 4 * MiB - (len(line_bytes(Q)) - mid_char(Q, "待")) - len(line_bytes(H3))
recs = fill_exact(NOW70 - td(31 * 60), 4 * MiB + 500000) + [atext(ticket([CMD]), T0), Q] + fill_exact(T0 + td(6), after) + [H3]
p = write_tr(h, recs)
setup = cut_mid_char(p, 4 * MiB) and os.path.getsize(p) > 8 * MiB
(ok, why), _ = run(None, CMD, home=h, tp=p)
rb = last_probe(h).get("read_bytes")
rep("K77-4c", "止まる: 境目をまたぐ queued の入力を戻して見つける → input_between_ticket_and_one・read_bytes=8MiB（境目の確かめ=%s） (%s, %s)" % (setup, why, rb),
    setup and (not ok) and why == "input_between_ticket_and_one" and rb == 8 * MiB)


def write_lines(h, lines):
    p = os.path.join(h, ".claude", "projects", "-p", "s1.jsonl")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return p


def js(r):
    return json.dumps(r, ensure_ascii=False)


# (6) a_idx より前に JSON でない行 → 通る
h = newhome()
p = write_lines(h, ["not json at all", js(human("x", T0 - td(60))), js(atext(ticket([CMD]), T0)), js(human("1", T0 + td(10)))])
(ok, why), _ = run(None, CMD, home=h, tp=p)
rep("K77-6", "通る: 同意票より前の JSON でない行は判定に使わない (%s)" % why, ok)

# (7a) a_idx と H の間に JSON でない行 → transcript_unparsable
h = newhome()
p = write_lines(h, [js(human("x", T0 - td(60))), js(atext(ticket([CMD]), T0)), "not json at all", js(human("1", T0 + td(10)))])
(ok, why), _ = run(None, CMD, home=h, tp=p)
rep("K77-7a", "止まる: 同意票と H の間の JSON でない行 → transcript_unparsable (%s)" % why, (not ok) and why == "transcript_unparsable")

# (7b) H の後に JSON でない行 → transcript_unparsable
h = newhome()
p = write_lines(h, [js(r) for r in std([CMD])] + ["not json at all"])
(ok, why), _ = run(None, CMD, home=h, tp=p)
rep("K77-7b", "止まる: H の後の JSON でない行 → transcript_unparsable (%s)" % why, (not ok) and why == "transcript_unparsable")

# (9) H が 31 分前の typed の「1」で、同意票が 4MB の外 → expired、read_bytes=4MiB
recs = [human("x", T0 - td(60)), atext(ticket([CMD]), T0)] + fill_exact(T0 + td(1), 5 * MiB) + [human("1", T0 + td(10))]
(ok, why), h = run(recs, CMD, now_off=10 + 31 * 60)
rb = last_probe(h).get("read_bytes")
rep("K77-9", "止まる: 31 分前の「1」で同意票が 4MB の外 → expired・read_bytes=4MiB (%s, %s)" % (why, rb), (not ok) and why == "expired" and rb == 4 * MiB)

# (10) H が「1」でない入力で、その前の AI の行が 4MB の外 → h_not_typed_one、read_bytes=4MiB
recs = [human("x", T0 - td(60)), atext(ticket([CMD]), T0)] + fill_exact(T0 + td(1), 5 * MiB) + [human("あ", T0 + td(10))]
(ok, why), h = run(recs, CMD)
rb = last_probe(h).get("read_bytes")
rep("K77-10", "止まる: H が「1」でない → h_not_typed_one・read_bytes=4MiB (%s, %s)" % (why, rb), (not ok) and why == "h_not_typed_one" and rb == 4 * MiB)

# (p) probe の read_bytes: 読んだ呼び出しには付き、読む前に止めた呼び出し（agent_id）には付かない
(ok, why), h = run(std([CMD]), CMD)
pr_read = last_probe(h)
(ok2, why2), h2 = run(std([CMD]), CMD, hook_extra={"agent_id": "a1"})
pr_agent = last_probe(h2)
rep("K77-p", "probe: 読んだときは read_bytes あり（%s）・agent_id で止めたときは無し（%s）" % (pr_read.get("read_bytes"), "read_bytes" in pr_agent),
    ok and isinstance(pr_read.get("read_bytes"), int) and pr_read["read_bytes"] > 0 and "read_bytes" not in pr_agent)

```
注意:
- `run(None, ..., tp=p)` は write_tr を呼ばずに、渡した p をそのまま使う（:109-111 の `tp or write_tr(...)` の道）。
- (8)「T5-x 以外の今の T1〜T9 が全件 PASS」は、全体の FAIL 0 で確かめる（T7〜T9 は po-apply の test-agent-hooks.sh 側）。
- K78 は rep にしない（実行機の遅れで時々赤になるのを避ける）。`TIME K78 <秒>` の行を出すだけ。Opus が GitHub の確かめのログでこの行を読む。
- (2) の記録は約 70MiB なので、判定の後に os.remove で消す。

## 手順 文書

### D1. ADR-1033:18

変更前: `   - 判定は新しい部品 `consent_check.py` が、会話記録の末尾 4MB を読んで行う（10 段の判定）。…`
変更後: 「末尾 4MB を読んで」の部分だけを「末尾から必要なだけ（最大 64MB）読んで」にする。ほかの文字は変えない。
その後 `node scripts/generate-adr-index.js` を流す。docs/adr/README.md に差分が出たら、それも commit に入れる。出なければ入れない。

### D2. design.md（4か所だけ）

- :26（§2 K5）: 判定の欄の「末尾 4MB に H か同意票が無い」を「末尾から必要なだけ（最大 64MB）読んでも H か同意票が無い」にする。検証の欄の最後の `、S5）` を `、S5。読み足しの例は §16-7 K77）` にする。
- :75（§4-2 の 3）: 行全体を次にする。
  `3. 記録の末尾から必要なだけ（最大 64MB）読む（読み足し方は §16-3(b)）。読み始めが 0 でなければ、最初の改行までを捨てる（段の間で切れた行はつないで戻す）。改行で終わっていない最後の1行は捨てる。JSON でない行は印として位置を残し、6 の text ブロックから末尾までに印があれば不可（それより前の印は判定に使わない）。`
- :80（§4-2 の 6）: 行の最後の「末尾 4MB の中に H かその text ブロックが無ければ不可。」を「末尾から必要なだけ（最大 64MB）読んでも H かその text ブロックが無ければ不可。」にする。
- :81（§4-2 の 7）: `7. H の timestamp から `now` までが30分以内。` の後ろに「H が 30 分より古ければ、6 の text ブロックを探す前に expired を返す（§16-3(b) 判定の順 3）。」を足す。

## 確かめ（クラウドで行う）

1. `python3 -I -B scripts/dev/consent-unit-tests.py docs/handoff/conversation-consent/hooks <一時フォルダ> "$PWD" > <scratchpad>/u.out 2>&1` を流し、出力全文を読む。
   - `^FAIL` の行が 0、`DONE` の行がある。
   - T5-x と K77-1〜K77-p（12 行）がすべて PASS。
   - `^PASS` の行数を報告する（便A の時点の 102 に、足した 12 本で 114 になるはず。違えば数と理由を書く）。
   - `TIME K78` の行の全文を報告する（クラウドの値は参考。判定は GitHub のログ）。
2. `python3 -I -B scripts/dev/permission-delegation-tests.py > <scratchpad>/p.out 2>&1` を流し、FAIL が 0 で最後まで走ること。
3. `grep -n "_read_tail_records\|末尾 4MB" docs/handoff/conversation-consent/hooks/consent_check.py` が 0 件。`grep -n "MAX_TAIL_BYTES" docs/handoff/conversation-consent/hooks/consent_check.py` が定義1件と使う所1件以上。
4. `git diff origin/main --stat` が触るファイルの一覧（README は差分が出たときだけ）に収まる。

## commit と push

- commit の文は Write でファイルに書き、`git commit -F <file>` で記録する。1 行目: `fix(consent): read transcript tail in steps up to 64MiB to find the typed "1"`。最後の行: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`。
- `git add` するのは触るファイルだけ（.claude-pipeline/active-work.d/ の登録ファイルは add しない）。
- `git push -u origin release/consent-k0-bin-b`。PR は作らない（Opus が作る）。
- git の命令は1回に1つ。

## 想定される分かれ道

- 変更前の行が上と違う（main が進んだ）→ 止めて `NEEDS_DECISION:` で違いを報告する。
- K77 の「境目の確かめ=False」が出る → 詰め物の作り方の誤り。カードの期待値は変えずに止め、`BLOCKED:` で行の全文を報告する。
- K77 のどれか、T5-x、または既存の試験が FAIL → 期待値を変えずに止め、FAIL の行の全文と実際の値を添えて `BLOCKED:`。
- 確かめ2で FAIL、または途中で例外 → 止めて `BLOCKED:`。
- PASS の行数が 114 でない → 止めずに、数と、増減した試験の名前を報告に書く。
- generate-adr-index.js が node の不足などで動かない → 止めて `BLOCKED:`（README を手で直さない）。

## 報告

最後の文は `DONE:` / `BLOCKED:` / `NEEDS_DECISION:` のどれかで始め、commit の SHA・push の結果・確かめ1〜4の結果（T5-x と K77 の13行の全文、`TIME K78` の行、PASS 行数、FAIL 行数、permission-delegation-tests の最後の10行、README の差分の有無）を書く。
