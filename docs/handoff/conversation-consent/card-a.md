# 実装カード 便A: 週の点検の K0 で 30 分を過ぎた「1」を外し、K79 と --audit --until を足す

正本: docs/handoff/conversation-consent/design.md §16-3(a)・§16-7 K75・K76・K79・§16-8 便A。PO 実装承認 2026-11-20（返事「1」。便C → 便A → 便B の順）。
ブランチ: release/consent-k0-bin-a（origin/main から新しく作る）。行番号は origin/main d4bea69c1 の値（便C は .github/workflows/agent-hooks-test.yml だけを変えるので、この2ファイルの行番号は変わらない）。
このカード自身も、同じ commit で docs/handoff/conversation-consent/card-a.md として足す（下の「作業場所の作り方」の 3）。

## 作業場所の作り方（クラウド）

1. `git fetch origin`
2. `bash scripts/new-worktree.sh release/consent-k0-bin-a`
3. worktree の中で `git show origin/release/consent-k0-card-a:docs/handoff/conversation-consent/card-a.md > docs/handoff/conversation-consent/card-a.md`
4. 以後の作業はすべてこの worktree の中。clone のまま commit しない。

## 触るファイル（これ以外は触らない）

1. scripts/dev/consent-audit.py
2. scripts/dev/consent-unit-tests.py
3. docs/handoff/conversation-consent/card-a.md（このカードの写し。中身は変えない）

触らない: docs/handoff/conversation-consent/hooks/ の中身（consent_check.py は便B）、scripts/dev/permission-delegation-tests.py、ワークフロー、ADR、design.md、~/.claude 配下すべて。

## 手順 consent-audit.py

### A1. 定数を2つ足す（:32 の K0_SKIP_REASONS の行の直後）

変更前（:30-32）:

```python
K0_TARGET = 20
K0_SKIP_REASONS = ("agent_id", "transcript_path", "transcript_unparsable")  # consent_check.py が H を読む前に返す理由（design §15-3）。見張りの理由名を変えるときはここも直す
```

変更後（:32 の次に2行足す。:30-32 は変えない）:

```python
K0_TARGET = 20
K0_SKIP_REASONS = ("agent_id", "transcript_path", "transcript_unparsable")  # consent_check.py が H を読む前に返す理由（design §15-3）。見張りの理由名を変えるときはここも直す
K0_WINDOW_SEC = 30 * 60  # consent_check.py の WINDOW（30 分）と同じ秒数（design §16-3(a)）。見張りの WINDOW を変えるときはここも直す
TZ_RE = re.compile(r"(?:Z|[+-]\d{2}:?\d{2})$")  # 時差の付いた時刻か（--prod-logins と --audit --until で共有。design §16-7 K76）
```

### A2. k0_delays を置き換え、関数を3つ足す（:346〜:405 の `def k0_delays` から `return total, delays, skipped, delays_no_h` まで）

この範囲を、次の全文で置き換える（ほかの行は触らない）。

```python
def _k0_true_prevs(home, events):
    """K0・K79 で共通: probe ごとに本当の直前の人の入力 (uuid, typed_one, timestamp) を選ぶ（design §2・§16-3(a)）。

    tool_use_id があれば、記録の中のその行より前で最も近い人の入力を本当の直前とする（timestamp は読めなければ None）。
    無ければ、probe の now より前の timestamp を持つ最後の人の入力を本当の直前とする。
    返り値は [(probe, 本当の直前 または None)]。記録の見つからない session の probe は含めない。
    """
    probes = [e for e in events if e.get("type") == "consent_probe"]
    by_session = {}
    for p in probes:
        by_session.setdefault(p.get("session"), []).append(p)
    result = []
    for sid, plist in by_session.items():
        tp = find_transcript(home, sid) if isinstance(sid, str) else None
        if not tp:
            continue
        ids = {p["tool_use_id"] for p in plist if p.get("tool_use_id")}
        id_re = re.compile("|".join(re.escape(i) for i in ids).encode("utf-8")) if ids else None
        humans = []          # (timestamp, uuid, typed_one)
        prev_for_tool = {}   # tool_use_id -> (uuid, typed_one, timestamp または None)
        last = None
        with open(tp, "rb") as f:
            for raw in f:
                if b'"human"' in raw:
                    try:
                        r = json.loads(raw.decode("utf-8"))
                    except Exception:
                        r = None
                    if r is not None and is_human(r):
                        ts = parse_ts(r.get("timestamp"))
                        last = (r.get("uuid"), is_typed_one(r), ts)
                        if ts:
                            humans.append((ts, r.get("uuid"), is_typed_one(r)))
                        continue
                if id_re is not None and b'"tool_use"' in raw:
                    m = id_re.search(raw)
                    if m:
                        tid = m.group(0).decode("utf-8")
                        prev_for_tool.setdefault(tid, last)
        for p in plist:
            true_prev = None
            tid = p.get("tool_use_id")
            if tid and tid in prev_for_tool:
                true_prev = prev_for_tool[tid]
            else:
                now = parse_ts(p.get("now"))
                cands = [h for h in humans if now and h[0] < now]
                if cands:
                    c = max(cands, key=lambda h: h[0])
                    true_prev = (c[1], c[2], c[0])
            result.append((p, true_prev))
    return result


def _k0_age_sec(true_prev, p):
    """本当の直前の入力の timestamp から probe の now までの秒数。どちらかが読めなければ None。"""
    now = parse_ts(p.get("now"))
    if now is None or true_prev[2] is None:
        return None
    return (now - true_prev[2]).total_seconds()


def k0_delays(home, events):
    """K0（design §2・§16-3(a)）: 後から見て直前の人の入力が typed の「1」だった呼び出しの数と、そのうち遅れの数。

    本当の直前の選び方は _k0_true_prevs。本当の直前の uuid が probe の h_uuid と違えば遅れ1件。
    reason が K0_SKIP_REASONS の probe は数えず skipped に入れる。h_uuid が null の遅れは delays_no_h にも入れる。
    「1」の timestamp から probe の now までが K0_WINDOW_SEC を超えるものは数えず expired に入れる（ちょうどは数える）。
    どちらかの時刻が読めないものは今どおり数える。
    """
    total = delays = skipped = delays_no_h = expired = 0
    for p, true_prev in _k0_true_prevs(home, events):
        if p.get("reason") in K0_SKIP_REASONS:
            skipped += 1
            continue
        if true_prev and true_prev[1]:
            age = _k0_age_sec(true_prev, p)
            if age is not None and age > K0_WINDOW_SEC:
                expired += 1
                continue
            total += 1
            if true_prev[0] != p.get("h_uuid"):
                delays += 1
                if p.get("h_uuid") is None:
                    delays_no_h += 1
    return total, delays, skipped, delays_no_h, expired


def k79_counts(home, events):
    """K79（design §16-7）: 読む範囲を広げた後（probe に read_bytes がある）の呼び出しのうち、
    本当の直前が 30 分以内の typed の「1」だったもの（target）と、そのうち見張りが見つけられなかったもの（missed）。

    「1」の timestamp か probe の now が読めないものは target に入れない（30 分以内と言えないため）。
    missed は reason が no_human_input か no_assistant_text のもの。
    """
    target = missed = 0
    for p, true_prev in _k0_true_prevs(home, events):
        if "read_bytes" not in p:
            continue
        if not (true_prev and true_prev[1]):
            continue
        age = _k0_age_sec(true_prev, p)
        if age is None or age > K0_WINDOW_SEC:
            continue
        target += 1
        if p.get("reason") in ("no_human_input", "no_assistant_text"):
            missed += 1
    return target, missed


def filter_probes_until(events, until):
    """--audit --until（design §16-7 K76）: consent_probe は now ≦ until のものだけ残す。
    now の読めない probe は until 以前と言えないので外す。consent_probe 以外の行はそのまま残す。"""
    kept = []
    for e in events:
        if e.get("type") == "consent_probe":
            now = parse_ts(e.get("now"))
            if now is None or now > until:
                continue
        kept.append(e)
    return kept
```

- 置き換えた後、`_k0_true_prevs` の中の読み方（for raw in f から prev_for_tool.setdefault まで）は、元の k0_delays と同じであること。違いは last と prev_for_tool の値に timestamp を3つ目として足したことと、時刻の道の true_prev に c[0] を足したことだけ。

### A3. tz_re を外へ出した定数に置き換える（run_prod_logins_cli の中）

変更前（:1869）: `    tz_re = re.compile(r"(?:Z|[+-]\d{2}:?\d{2})$")` → この1行を消す（前後の空行は1つ残す）。

変更前（:1883）: `        if not tz_re.search(raw) or "T" not in raw:`
変更後: `        if not TZ_RE.search(raw) or "T" not in raw:`

`tz_re` がファイルの中に残っていないこと（grep で 0 件）。

### A4. run_audit に until を足す（:1898・:1907・:1918-1923）

変更前（:1898）: `def run_audit(home, now, with_permissions, out, commit=False, gh_view=None, git_run=None):`
変更後: `def run_audit(home, now, with_permissions, out, commit=False, gh_view=None, git_run=None, until=None):`

（until は最後に足し、既定は None。permission-delegation-tests.py:192 と consent-unit-tests.py:330 の呼び出しはそのまま動く。）

変更前（:1907）:

```python
    total, delays, k0_skipped, k0_delays_no_h = k0_delays(home, events)
```

変更後:

```python
    k_events = events if until is None else filter_probes_until(events, until)  # --until は K0・K79 の数えだけに効く（design §16-7 K76）
    total, delays, k0_skipped, k0_delays_no_h, k0_expired = k0_delays(home, k_events)
    k79_target, k79_missed = k79_counts(home, k_events)
```

変更前（:1918-1923）:

```python
    out("K0: 直前の人の入力が typed の「1」だった呼び出し %d 件のうち、遅れ %d 件（うち見張りが入力を見つけられなかった %d 件）（目標: %d 件たまった時点で遅れ0）／H を読む前に止めた呼び出しで除外 %d 件"
        % (total, delays, k0_delays_no_h, K0_TARGET, k0_skipped))
    if total >= K0_TARGET:
        out("K0 判定: %s" % ("○" if delays == 0 else "×（案 F に切り替える設計に戻す）"))
    else:
        out("K0 判定: 対象が %d 件に届くまで保留" % K0_TARGET)
```

変更後:

```python
    out("K0: 直前の人の入力が typed の「1」だった呼び出し %d 件のうち、遅れ %d 件（うち見張りが入力を見つけられなかった %d 件）（目標: %d 件たまった時点で遅れ0）／H を読む前に止めた呼び出しで除外 %d 件／30分を過ぎて外した %d 件"
        % (total, delays, k0_delays_no_h, K0_TARGET, k0_skipped, k0_expired))
    if total >= K0_TARGET:
        out("K0 判定: %s" % ("○" if delays == 0 else "×（案 F に切り替える設計に戻す）"))
    else:
        out("K0 判定: 対象が %d 件に届くまで保留" % K0_TARGET)
    out("K79: 読む範囲を広げた後の呼び出しで、30分以内の『1』があったのに見張りが見つけられなかった %d 件（対象 %d 件）"
        % (k79_missed, k79_target))
```

### A5. main の --audit で --until を使う（:1956-1958）

変更前:

```python
    if args.audit:
        run_audit(home, now, args.permissions, print, args.commit_snapshot)
        return 0
```

変更後:

```python
    if args.audit:
        until = None
        if args.until:
            if not TZ_RE.search(args.until) or "T" not in args.until:
                print("STOP: --until に時差が無い（例 2026-11-20T15:00+09:00）")
                return 2
            until = parse_ts(args.until)
            if until is None:
                print("STOP: --until が読めない")
                return 2
        run_audit(home, now, args.permissions, print, args.commit_snapshot, until=until)
        return 0
```

add_argument は足さない・変えない（:1944 の --until をそのまま使う）。

## 手順 consent-unit-tests.py

### U1. T0-a の受け取りを5つの組にする（:280-281）

変更前:

```python
total, delays, _, _ = audit.k0_delays(h, probes)
rep("T0-a", "K0: 対象%d件のうち遅れ%d件（期待 5 と 2）" % (total, delays), total == 5 and delays == 2)
```

変更後:

```python
r_a = audit.k0_delays(h, probes)
rep("T0-a", "K0: 対象5件のうち遅れ2件（期待 (5, 2, 0, 0, 0)、実際 %s）" % (r_a,), r_a == (5, 2, 0, 0, 0))
```

### U2. T0-b の期待を5つの組にする（:289）

変更前: `rep("T0-b", "K0: 外す4件・数える遅れ1件（期待 total=6 delays=3 skipped=4 delays_no_h=1、実際 %s）" % (r_b,), r_b == (6, 3, 4, 1))`
変更後: `rep("T0-b", "K0: 外す4件・数える遅れ1件（期待 total=6 delays=3 skipped=4 delays_no_h=1 expired=0、実際 %s）" % (r_b,), r_b == (6, 3, 4, 1, 0))`

### U3. T0-c・T0-u・T0-u2・T0-d を足す（:289 の次、空行の後、`# T0-w` の行の前）

```python
# T0-c: 30 分を過ぎた「1」を外す（design §16-3(a)、K75）
def tool_with_id(ts, tid):
    t = atool({"command": tid}, ts)
    t["message"]["content"][0]["id"] = tid
    return t

def no_ts(rec):
    del rec["timestamp"]
    return rec

M = 60
# 呼び出し1: tool_use_id の道
hc = newhome()
hc1 = human("1", T0, "typed")
hc_nots = no_ts(human("1", T0 + td(201 * M), "typed"))
write_tr(hc, [hc1,
              tool_with_id(T0 + td(29 * M), "toolu_c29"), tool_with_id(T0 + td(30 * M), "toolu_c30"),
              tool_with_id(T0 + td(31 * M), "toolu_c31"), tool_with_id(T0 + td(200 * M), "toolu_c200"),
              tool_with_id(T0 + td(10 * M), "toolu_cnonow"),
              hc_nots, tool_with_id(T0 + td(202 * M), "toolu_cnots")])
probes_c1 = [
    {"type": "consent_probe", "session": "s1", "h_uuid": hc1["uuid"], "now": (T0 + td(29 * M)).isoformat(), "tool_use_id": "toolu_c29"},
    {"type": "consent_probe", "session": "s1", "h_uuid": hc1["uuid"], "now": (T0 + td(30 * M)).isoformat(), "tool_use_id": "toolu_c30"},
    {"type": "consent_probe", "session": "s1", "h_uuid": hc1["uuid"], "now": (T0 + td(31 * M)).isoformat(), "tool_use_id": "toolu_c31"},
    {"type": "consent_probe", "session": "s1", "h_uuid": hc1["uuid"], "now": (T0 + td(200 * M)).isoformat(), "tool_use_id": "toolu_c200"},
    {"type": "consent_probe", "session": "s1", "h_uuid": hc1["uuid"], "tool_use_id": "toolu_cnonow"},
    {"type": "consent_probe", "session": "s1", "h_uuid": hc_nots["uuid"], "now": (T0 + td(202 * M)).isoformat(), "tool_use_id": "toolu_cnots"},
]
r_c1 = audit.k0_delays(hc, probes_c1)
# 呼び出し2: 時刻の道（tool_use_id を持たない probe）
hc2h = newhome()
hc2 = human("1", T0, "typed")
write_tr(hc2h, [hc2])
probes_c2 = [{"type": "consent_probe", "session": "s1", "h_uuid": hc2["uuid"], "now": (T0 + td(m * M)).isoformat()} for m in (29, 30, 31, 200)]
r_c2 = audit.k0_delays(hc2h, probes_c2)
same_window = cc.WINDOW.total_seconds() == audit.K0_WINDOW_SEC
rep("T0-c", "K0: 30分を過ぎた「1」を外す（期待 呼び出し1 (4, 0, 0, 0, 2)・呼び出し2 (2, 0, 0, 0, 2)・WINDOW と K0_WINDOW_SEC が同じ、実際 %s %s %s）" % (r_c1, r_c2, same_window),
    r_c1 == (4, 0, 0, 0, 2) and r_c2 == (2, 0, 0, 0, 2) and same_window)

# T0-u: --audit --until の絞り（design §16-7 K76）
r_u = audit.k0_delays(h, audit.filter_probes_until(probes, T0 + td(100)))
rep("T0-u", "K0: T0+100秒までの probe だけを数える（期待 (1, 0, 0, 0, 0)、実際 %s）" % (r_u,), r_u == (1, 0, 0, 0, 0))

# T0-u2: --until に時差が無い・読めないときは STOP で終了コード 2
rc_u1 = audit.main(["--audit", "--until", "2026-11-20T15:00:00"])
rc_u2 = audit.main(["--audit", "--until", "2026-13-40T99:00:00+09:00"])
rep("T0-u2", "K76: --until の時差なし・読めない値で止まる（期待 2 と 2、実際 %s と %s）" % (rc_u1, rc_u2), rc_u1 == 2 and rc_u2 == 2)

# T0-d: K79 の数え（design §16-7 K79）
hd = newhome()
hd1 = human("1", T0, "typed")
hd_ok = human("ok", T0 + td(32 * M), "typed")
hd_nots = no_ts(human("1", T0 + td(34 * M), "typed"))
write_tr(hd, [hd1] + [tool_with_id(T0 + td(29 * M), "toolu_d" + k) for k in "abcde"]
         + [tool_with_id(T0 + td(31 * M), "toolu_df"), hd_ok, tool_with_id(T0 + td(33 * M), "toolu_dg"),
            hd_nots, tool_with_id(T0 + td(35 * M), "toolu_dh")])
def pd(k, minute, reason, read_bytes=True, h_uuid=None):
    p = {"type": "consent_probe", "session": "s1", "h_uuid": h_uuid, "now": (T0 + td(minute * M)).isoformat(), "tool_use_id": "toolu_d" + k}
    if reason is not None:
        p["reason"] = reason
    if read_bytes:
        p["read_bytes"] = 4 * 1024 * 1024
    return p
probes_d = [
    pd("a", 29, "no_human_input", read_bytes=False),   # (a) read_bytes なし → 対象外
    pd("b", 29, "no_human_input"),                     # (b) 対象・missed
    pd("c", 29, "no_assistant_text"),                  # (c) 対象・missed
    pd("d", 29, None, h_uuid=hd1["uuid"]),             # (d) result=true → 対象・missed でない
    pd("e", 29, "ticket_format", h_uuid=hd1["uuid"]),  # (e) 対象・missed でない
    pd("f", 31, "no_human_input"),                     # (f) 31 分 → 対象外
    pd("g", 33, "no_human_input"),                     # (g) 本当の直前が「1」でない → 対象外
    pd("h", 35, "no_human_input"),                     # (h) 「1」に timestamp が無い → 対象外
]
probes_d[3]["result"] = True
r_d = audit.k79_counts(hd, probes_d)
rep("T0-d", "K79: 対象と見つけられなかった件数（期待 (4, 2)、実際 %s）" % (r_d,), r_d == (4, 2))
```

- 書く場所は :289 の次の空行の後、`# T0-w: 試験の区間の除外（design §9）` の行の前。前後に空行を1つずつ置く。
- T0-u2 は `audit.main` を呼ぶ。STOP の行が標準出力に出るが、行頭が PASS/FAIL ではないので判定には効かない。real_home() はホームの場所を返すだけで、STOP は記録を読む前に返る。

## 確かめ（クラウドで行う）

1. `python3 -I -B scripts/dev/consent-unit-tests.py docs/handoff/conversation-consent/hooks <一時フォルダ> "$PWD" > <scratchpad>/u.out 2>&1` を流し、出力全文を読む。
   - `^FAIL` の行が 0、`DONE` の行がある。
   - T0-a・T0-b・T0-c・T0-u・T0-u2・T0-d の行がすべて PASS。
   - `^PASS` の行数を報告する（便C の時点の 98 に、足した 4 本で 102 になるはず。違えば数と理由を書く）。
2. `python3 -I -B scripts/dev/permission-delegation-tests.py > <scratchpad>/p.out 2>&1` を流し、出力全文を読む。FAIL の行が 0 で、最後まで走ること（run_audit の引数を足したことの影響を見る）。
3. `grep -n "tz_re" scripts/dev/consent-audit.py` が 0 件。`grep -n "TZ_RE" scripts/dev/consent-audit.py` が3件（定義1・run_prod_logins_cli 1・main 1）。
4. `git diff origin/main --stat` が触るファイルの3つだけ。

## commit と push

- commit の文は Write でファイルに書き、`git commit -F <file>` で記録する。1 行目: `fix(consent): drop expired typed "1" from K0, add K79 count and --audit --until`。最後の行: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`。
- `git add` するのは触るファイルの3つだけ（.claude-pipeline/active-work.d/ の登録ファイルは add しない）。
- `git push -u origin release/consent-k0-bin-a`。PR は作らない（Opus が作る）。
- git の命令は1回に1つ。

## 想定される分かれ道

- 変更前の行が上と違う（main が進んだ）→ 止めて `NEEDS_DECISION:` で違いを報告する。
- 確かめ1で T0-a〜T0-d のどれかが FAIL → カードの期待値を変えずに止め、FAIL の行の全文と実際の値を添えて `BLOCKED:` で報告する。
- 確かめ1で既存の試験（T1〜T9 など）が FAIL → 止めて `BLOCKED:`。見張りの中身は触らない。
- 確かめ2で FAIL、または途中で例外 → 止めて `BLOCKED:`。
- PASS の行数が 102 でない → 止めずに、数と、増減した試験の名前を報告に書く。

## 報告

最後の文は `DONE:` / `BLOCKED:` / `NEEDS_DECISION:` のどれかで始め、commit の SHA・push の結果・確かめ1〜4の結果（T0-a〜T0-d の6行の全文、PASS 行数、FAIL 行数、permission-delegation-tests の最後の10行）を書く。
