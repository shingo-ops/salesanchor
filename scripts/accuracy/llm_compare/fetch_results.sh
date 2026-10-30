#!/bin/bash
# VPS の /home/ubuntu/fhd-test/llmcmp から Mac へ取り寄せる（読むだけ）と、組み立てた文字列の照合（design.md §5-1, §5-5）。
# PO が ! で実行する台本。AI は実行しない。
# 使い方: bash fetch_results.sh <保存先フォルダ(Mac。リポジトリの外)> <test-id...>   例: ... llmcmp-g1 llmcmp-g2
# 保存先は ~/CC報告ファイル-keep/llm-compare-20261030/ など（仕入元の文字列を含むのでリポジトリに置かない）。
set -u
DEST=${1:?保存先}; shift
[ $# -ge 1 ] || { echo "ABORT: test-id が無い"; exit 1; }
K="-i $HOME/.ssh/manual-only/id_ed25519 ubuntu@49.212.137.46"
BASE=/home/ubuntu/fhd-test/llmcmp
case "$(cd "$DEST" 2>/dev/null && pwd -P || echo "$DEST")" in *salesanchor*|*worktrees*) echo "ABORT: 保存先がリポジトリの中に見える"; exit 1;; esac
mkdir -p "$DEST/prompts"
ssh $K "tar -C $BASE/out -cf - ." | tar -C "$DEST/prompts" -xf - || { echo "ABORT: 取り寄せ失敗"; exit 1; }
for f in no-health.yml; do ssh $K "cat $BASE/$f" > "$DEST/$f" 2>/dev/null || echo "無い: $f"; done
for t in "$@"; do
  for f in $t.out $t.health $t.composefiles; do ssh $K "cat $BASE/$f" > "$DEST/$f" 2>/dev/null || echo "無い: $f"; done
  mv "$DEST/prompts/$t.jsonl" "$DEST/$t.jsonl" 2>/dev/null || echo "無い: $t.jsonl"
done
( cd "$DEST" && shasum -a 256 *.jsonl *.out *.health *.composefiles no-health.yml prompts/* > SHA256SUMS 2>/dev/null )
# 照合: JSONL の成功行の数 = 保存した文字列の数。repeat 1 と 2・3 の文字列が投稿ごとに同じ。指示書の sha256 が全行同じ
python3 -I - "$DEST" "$@" <<'PY'
import hashlib, json, os, sys
dest, tids = sys.argv[1], sys.argv[2:]
bad = 0
by_job = {}
shas = set()
for t in tids:
    rows = [json.loads(l) for l in open(os.path.join(dest, t + ".jsonl"), encoding="utf-8") if l.strip()]
    ok = [r for r in rows if not r.get("error")]
    idx = [l.rstrip("\n").split("\t") for l in open(os.path.join(dest, "prompts", t + ".index.tsv"), encoding="utf-8")][1:]
    files = [f for f in os.listdir(os.path.join(dest, "prompts")) if f.startswith(t + "_") and f.endswith(".txt")]
    print("%s 成功行=%d 保存した文字列=%d index=%d エラー行=%d" % (t, len(ok), len(files), len(idx), len(rows) - len(ok)))
    if not (len(ok) == len(files) == len(idx)):
        bad += 1
    for r, (serial, sha, chars) in zip(ok, idx):
        p = os.path.join(dest, "prompts", "%s_%04d_%s.txt" % (t, int(serial), sha))
        if hashlib.sha256(open(p, "rb").read()).hexdigest() != sha:
            print("sha256 不一致:", os.path.basename(p)); bad += 1
        by_job.setdefault(r["job_id"], set()).add(sha)
        shas.add(r.get("prompt_sha256"))
diff = [j for j, s in by_job.items() if len(s) != 1]
print("投稿=%d  repeat 間で文字列が違う投稿=%d  指示書の sha256 の種類=%d" % (len(by_job), len(diff), len(shas)))
if diff or len(shas) != 1:
    bad += 1
print("照合:", "OK" if not bad else "NG")
sys.exit(1 if bad else 0)
PY
