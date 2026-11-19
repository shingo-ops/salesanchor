# 実装カード 便K0: K0「同意の遅れ」の数え方から、H を読む前に止めた呼び出しを外す

正本: docs/handoff/conversation-consent/design.md §15（改訂3）。PO 実装承認 2026-11-19（設計 PR #5608 の報告への返事「1」）。
ブランチ: release/consent-k0-count-fix（PR #5608 に積む）。行番号は origin/main fd72a7b01 の値。

## 作業場所の作り方（クラウド）

1. `bash scripts/new-worktree.sh release/consent-k0-count-fix`（origin/main から同名のブランチを作る）
2. `git -C ~/worktrees/salesanchor/release-consent-k0-count-fix merge --ff-only origin/release/consent-k0-count-fix`（設計のコミットを取り込む。ff できなければ BLOCKED:）
3. 以後の作業はすべてこの worktree の中。clone のまま commit しない。

## 触るファイル（これ以外は触らない）

1. scripts/dev/consent-audit.py
2. scripts/dev/consent-unit-tests.py

触らない: ~/.claude 配下すべて、consent_check.py、フック、settings.json、design.md、ADR。

## 手順

### 1. consent-audit.py

(a) :31 `K0_TARGET = 20` の直後に1行足す:

```python
K0_SKIP_REASONS = ("agent_id", "transcript_path", "transcript_unparsable")  # consent_check.py が H を読む前に返す理由（design §15-3）。見張りの理由名を変えるときはここも直す
```

(b) k0_delays（:345-399）を次のとおり直す。ほかの行は変えない。
- docstring の最後に1行足す: 「reason が K0_SKIP_REASONS の probe は数えず skipped に入れる。h_uuid が null の遅れは delays_no_h にも入れる。」
- :356 `total = delays = 0` → `total = delays = skipped = delays_no_h = 0`
- :384 `for p in plist:` の直後に足す:

```python
            if p.get("reason") in K0_SKIP_REASONS:
                skipped += 1
                continue
```

- :397-398 の遅れの数えを次にする:

```python
                if true_prev[0] != p.get("h_uuid"):
                    delays += 1
                    if p.get("h_uuid") is None:
                        delays_no_h += 1
```

- :399 `return total, delays` → `return total, delays, skipped, delays_no_h`
- 記録が見つからない会話（:358-359 の continue）の probe は、今までどおり数えない（skipped にも入れない）。

(c) run_audit（:1900・:1911-1912）:

```python
    total, delays, k0_skipped, k0_delays_no_h = k0_delays(home, events)
```

```python
    out("K0: 直前の人の入力が typed の「1」だった呼び出し %d 件のうち、遅れ %d 件（うち見張りが入力を見つけられなかった %d 件）（目標: %d 件たまった時点で遅れ0）／H を読む前に止めた呼び出しで除外 %d 件"
        % (total, delays, k0_delays_no_h, K0_TARGET, k0_skipped))
```

判定の行（:1913-1916）は変えない。

### 2. consent-unit-tests.py

(a) :280 を `total, delays, _, _ = audit.k0_delays(h, probes)` にする（T0-a の期待 5・2 は変えない）。

(b) :281 の T0-a の直後に T0-b を足す。T0-a の h・hu1・hu2 と記録をそのまま使う:

```python
# T0-b: H を読む前に止めた probe を外す（design §15、K72）
probes_b = list(probes)
for rs in ("agent_id", "agent_id", "transcript_path", "transcript_unparsable"):
    probes_b.append({"type": "consent_probe", "session": "s1", "h_uuid": None, "reason": rs, "now": (T0 + td(150)).isoformat()})
probes_b.append({"type": "consent_probe", "session": "s1", "h_uuid": None, "reason": "no_human_input", "now": (T0 + td(150)).isoformat()})
r_b = audit.k0_delays(h, probes_b)
rep("T0-b", "K0: 外す4件・数える遅れ1件（期待 total=6 delays=3 skipped=4 delays_no_h=1、実際 %s）" % (r_b,), r_b == (6, 3, 4, 1))
```

### 3. 確かめ

- `python3 scripts/dev/consent-unit-tests.py > /tmp/CC報告ファイル/k0-unit.txt 2>&1; echo rc=$?` が rc=0 で、FAIL 0 件、T0-a と T0-b が PASS。
- `git diff origin/main --stat` が触るファイル2つと、設計のコミットの2ファイル（design.md・active-work）・本カードだけ。

### 4. commit と push

- commit 1つ: `feat(consent): K0 excludes pre-H probes (design §15)`（末尾に Co-Authored-By 行）。
- push は単独で: `git -C ~/worktrees/salesanchor/release-consent-k0-count-fix push origin release/consent-k0-count-fix`。
- PR は作らない（#5608 に積む）。

## 想定される分岐

- 行番号がずれている → 関数名と文で場所を探す。中身が本カードの「前」と違えば BLOCKED:（違う箇所の生の行を添える）。
- T0-a が FAIL になる → 直しの誤り。直して再試験。2回直して通らなければ BLOCKED:。
- T0-b の実際の値が (6,3,4,1) と違う → 実際の値と probes_b を添えて BLOCKED:（期待を書き換えない）。
- 見張りに止められた → 言い換えずに BLOCKED:（止めた文をそのまま添える）。

## 報告

最後の行に DONE / BLOCKED: <理由> / NEEDS_DECISION: <問い> のどれか。DONE のときはコミットの sha、試験の結果の最後の10行を生のまま添える。
