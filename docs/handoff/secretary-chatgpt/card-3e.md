# 実装カード 3e: 容器に公開の証明書の束を入れ、codex の shell_snapshot を止める（ADR-1058 段3）

## 受領確認
- 作業場所: release/secretary-codex-stage3。着手時の先頭は 0. の確かめのとおり。
- 触るファイルは次の 4 つだけ: `secretary-codex/Dockerfile`・`secretary-codex/server.mjs`・`secretary-codex/server.test.mjs`・`tests/sandbox/secretary-codex.sh`。

## なぜ
GitHub の一時 VM での確かめ（run 42981257700・2026-11-11・b2805f8e3）で次の 2 つを観測した。
1. ログインなしの codex exec の標準エラー: `failed to connect to websocket: IO error: invalid peer certificate: UnknownIssuer, url: wss://api.openai.com/v1/responses`（7 行）。codex は 150 秒返らず時間切れ（rc=124）。
   - Dockerfile は `FROM node:22-bookworm-slim` に codex を npm で入れるだけで、OS の公開の証明書の束（ca-certificates）を入れていない（Dockerfile 5〜6 行）。
   - Context7（openai/codex）: Linux の codex は OS の証明書置き場から根の証明書を読む（rustls-native-certs）。node の probe.mjs は node 内蔵の束を使うので chatgpt.com に 200 で届いた。codex（Rust）だけが届かない。
   - このままでは、本番で ChatGPT に切り替えた時、毎回 80 秒の時間切れになる。設計者（Opus）の入れ忘れ。
2. 実行のたびに CODEX_HOME（ログインの鍵のボリューム）に `/home/node/.codex/shell_snapshots/<id>.sh`（約 1.7KB）ができた。
   - Context7（openai/codex）: `features.shell_snapshot=false` で作らない。置き場は `{codex_home}/shell_snapshots/`。
   - 鍵のボリュームには auth.json 以外を貯めない方針（design.md §5-1・§9）なので止める。

## 禁止
- 下の 1〜4 の変更以外は変えない（並び・空白・ほかの段も）。上の 4 ファイル以外は触らない。
- ca-certificates 以外の apt の物を入れない。codex の版（0.162.1）を変えない。

## 0. 着手前の確かめ
- 0-1 `git log -1 --format=%H` を記録する。
- 0-2 `grep -c 'shell_snapshot' secretary-codex/server.mjs secretary-codex/server.test.mjs tests/sandbox/secretary-codex.sh` が 3 行とも `:0`。
- 0-3 `grep -c 'ca-certificates' secretary-codex/Dockerfile` が 0。
- 0-4 `grep -n 'toBe18\|length, 18)' secretary-codex/server.test.mjs` が `292:  assert.equal(a.filter((x) => x === "-c").length, 18);` の 1 行。
- どれかが違えば停止して NEEDS_DECISION。

## 1. secretary-codex/Dockerfile
`FROM node:22-bookworm-slim` の行の直後（`RUN npm install -g ...` の前）に次の 2 行を足す:

```
# codex（Rust）は OS の証明書置き場から根の証明書を読む。slim には無いので入れる（card-3e・一時 VM で UnknownIssuer を観測）
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*
```

## 2. secretary-codex/server.mjs
- 2-1 次の 1 行:
  `// 止め設定（recon §5-2 の手元の試しと同じ18組）。web_search の値は引用符ごと渡す（手元の試しと同じ形）。`
  を次の 1 行にする:
  `// 止め設定（recon §5-2 の手元の試しの18組に、一時 VM で見つけた shell_snapshot を足した19組。card-3e）。web_search の値は引用符ごと渡す（手元の試しと同じ形）。`
- 2-2 次の 1 行:
  `  "hooks", "sleep_tool", "code_mode_host", "tool_suggest", "skill_search", "remote_plugin",`
  の直後に次の 1 行を足す:
  `  "shell_snapshot",`

## 3. secretary-codex/server.test.mjs
- 3-1 `test("(9) 引数: 止め設定18組・` の `18組` を `19組` にする（その行の他は変えない）。
- 3-2 `  assert.equal(a.filter((x) => x === "-c").length, 18);` の `18` を `19` にする。
- 3-3 `  assert.ok(a.includes("features.remote_plugin=false"));` の直後に次の 1 行を足す:
  `  assert.ok(a.includes("features.shell_snapshot=false"));`

## 4. tests/sandbox/secretary-codex.sh
- 4-1 次の 1 行:
  `grep -qx 'codex-cli 0.162.1' "$OUT/img.txt" || { echo "NG: codex の版"; exit 1; }`
  の直後に次の 1 行を足す:
  `docker run --rm --entrypoint sh "$IMG" -c 'test -s /etc/ssl/certs/ca-certificates.crt' && echo "ca-certificates ok" || { echo "NG: 公開の証明書の束が無い"; exit 1; }`
- 4-2 exec.sh の中の次の 1 行:
  `  -c features.tool_suggest=false -c features.skill_search=false -c features.remote_plugin=false \`
  を次の 1 行にする:
  `  -c features.tool_suggest=false -c features.skill_search=false -c features.remote_plugin=false -c features.shell_snapshot=false \`
- 4-3 次の 1 行:
  `head -20 "$OUT/v2_err.txt" | cut -c1-200`
  の直後に次の 1 行を足す:
  `if grep -q 'UnknownIssuer' "$OUT/v2_err.txt"; then echo "NG: OpenAI の証明書を確かめられない（UnknownIssuer）"; exit 1; fi`
- 4-4 次の 1 行:
  `test "$n" -eq 0 || { echo "NG: V3 頼みの文が CODEX_HOME に残った"; exit 1; }`
  の直後に次の 1 行を足す:
  `if docker exec "$CT" test -e /home/node/.codex/shell_snapshots; then echo "NG: CODEX_HOME に shell_snapshots ができた"; exit 1; fi`
- 4-5 次の 1 行:
  `test "$n2" -eq 0 || { echo "NG: V3 頼みの文が CODEX_HOME に残った（server.mjs の道）"; exit 1; }`
  の直後に次の 1 行を足す:
  `if docker exec "$CT" test -e /home/node/.codex/shell_snapshots; then echo "NG: CODEX_HOME に shell_snapshots ができた（server.mjs の道）"; exit 1; fi`

## 5. 確かめ方
- 5-1 `git diff --stat` が次の 4 ファイルだけ（足した行・消した行）:
  - `secretary-codex/Dockerfile` 足す 2・消す 0
  - `secretary-codex/server.mjs` 足す 2・消す 1
  - `secretary-codex/server.test.mjs` 足す 3・消す 2
  - `tests/sandbox/secretary-codex.sh` 足す 5・消す 1
  （`git diff --numstat` で数を確かめる）
- 5-2 `bash -n tests/sandbox/secretary-codex.sh && echo syntax ok` が `syntax ok`。
- 5-3 `node --check secretary-codex/server.mjs && echo mjs ok` が `mjs ok`。
- 5-4 `cd secretary-codex && node --test server.test.mjs` が fail 0。（node が無ければ「node 無し」と書いて次へ。CI と一時 VM で確かめる）
- 5-5 `grep -c 'shell_snapshot' secretary-codex/server.mjs secretary-codex/server.test.mjs tests/sandbox/secretary-codex.sh` が `:2`・`:1`・`:3`。
- 5-6 `grep -c 'ca-certificates' secretary-codex/Dockerfile` が 1。

## 分岐
- 5-1〜5-6 のどれかが違う → 停止して NEEDS_DECISION（生の出力を添える）。別の書き方にしない。
- push が見張りに止められた → 言い換えず停止して BLOCKED:。

## 合格の基準
5-1〜5-6 がすべて書いたとおり。push 後の `git log origin/release/secretary-codex-stage3 -1` が自分の commit。

## 報告の型
commit id・`git diff HEAD~1` の全文・5-1〜5-6 の生出力・最後に DONE / BLOCKED: / NEEDS_DECISION: のどれか。

commit 文: `fix(secretary-codex): add OS CA bundle and disable shell_snapshot (ADR-1058 stage 3)`、空行、`Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`。

END OF CARD
