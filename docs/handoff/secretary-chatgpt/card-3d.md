# 実装カード 3d: 一時 VM の確かめで、ログインなしの codex exec に時間の上限を付ける（ADR-1058 段3）

## 受領確認
- 作業場所: release/secretary-codex-stage3。着手時の先頭は 0. の確かめのとおり。
- 触るファイルは `tests/sandbox/secretary-codex.sh` の1つだけ。

## なぜ
GitHub の一時 VM での確かめ（run 42970885998・2026-11-11）が「V2・V4 ログインなしで codex exec を1回」の段で 06:14:01 から返らず、07:13:27 に 60 分の上限で取り消された（記録: 段の見出しの次の行が `##[error]The operation was canceled.`）。
V1 までは合格していた（`node:node 700`・`{"ready":false,"last_refresh":null}`）。
台本のこの段だけ時間の上限が無かった。設計者（Opus）の入れ忘れ。
本番の道は変わらない。容器はログイン前（auth.json が無い）なら codex を動かさず 503 not_ready を返す（secretary-codex/server.mjs 228 行）。ログイン後の道には 80 秒の上限がある（同 15 行 CODEX_TIMEOUT_MS・160〜167 行）。

## 禁止
- 下の 1. の置き換え以外は変えない（並び・空白・ほかの段も）。
- server.mjs・Dockerfile・ほかのファイルは触らない。

## 0. 着手前の確かめ
- 0-1 `git log -1 --format=%H` を記録する。
- 0-2 `grep -n '^rc=\$?$' tests/sandbox/secretary-codex.sh` が1行（89 行目）。違えば停止して NEEDS_DECISION。
- 0-3 `grep -c 'timeout 150' tests/sandbox/secretary-codex.sh` が 0。違えば停止して NEEDS_DECISION。

## 1. 置き換え
86〜89 行目のこの 4 行:

```
docker run --rm -i --name "${CT}-exec" --init --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges:true \
  --memory 512m -v "$VOL:/home/node/.codex" -v "$OUT/exec.sh:/x.sh:ro" --entrypoint sh "$IMG" /x.sh \
  < "$OUT/in.txt" > "$OUT/v2_out.jsonl" 2> "$OUT/v2_err.txt"
rc=$?
```

を、次の 7 行にする（1 行目の先頭に `timeout 150 ` を足し、後ろに 3 行を足すだけ）:

```
timeout 150 docker run --rm -i --name "${CT}-exec" --init --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges:true \
  --memory 512m -v "$VOL:/home/node/.codex" -v "$OUT/exec.sh:/x.sh:ro" --entrypoint sh "$IMG" /x.sh \
  < "$OUT/in.txt" > "$OUT/v2_out.jsonl" 2> "$OUT/v2_err.txt"
rc=$?
# 150 秒で返らなければ timeout が止める（rc=124）。止めた後も容器が残るので消す。
docker rm -f "${CT}-exec" >/dev/null 2>&1 || true
if [ "$rc" -eq 124 ]; then echo "codex exec はログインなしで 150 秒返らなかった（時間切れで止めた。V2・V4・V3 はここまでの出力で確かめる）"; fi
```

## 2. 確かめ方
- 2-1 `git diff --stat` が `tests/sandbox/secretary-codex.sh | 5 ++++-` の 1 ファイルだけ（足した行 4・消した行 1）。
- 2-2 `bash -n tests/sandbox/secretary-codex.sh && echo syntax ok` が `syntax ok`。
- 2-3 `grep -c 'timeout 150' tests/sandbox/secretary-codex.sh` が 1。

## 分岐
- 2-1〜2-3 のどれかが違う → 停止して NEEDS_DECISION（生の出力を添える）。別の書き方にしない。
- push が見張りに止められた → 言い換えず停止して BLOCKED:。

## 合格の基準
2-1〜2-3 がすべて書いたとおり。push 後の `git log origin/release/secretary-codex-stage3 -1` が自分の commit。

## 報告の型
commit id・`git diff HEAD~1` の全文・2-1〜2-3 の生出力・最後に DONE / BLOCKED: / NEEDS_DECISION: のどれか。

commit 文: `test(sandbox): cap the no-login codex exec at 150s (ADR-1058 stage 3)`、空行、`Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`。

END OF CARD
