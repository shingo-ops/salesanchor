#!/bin/bash
# 3種の答え（Gemini の JSONL・Claude 2種の JSONL）を、1回の起動でまとめて採点用の形（14列 TSV）にする（design.md §5-3, §5-5）。
# 読み取りのみ（fhd_snapshot.py は READ ONLY 取引で最後に rollback）。PO が ! で実行する台本。AI は実行しない。
# 使い方: bash vps_convert.sh <出力フォルダ(Mac)> <jsonl...>   例: Gemini の llmcmp-g1.jsonl llmcmp-g2.jsonl(あれば結合済み) と claude-haiku.jsonl claude-sonnet.jsonl
# JSONL の名前（拡張子を除く）が tag になる。Gemini は repeat 1〜3 が1本に入っている。
set -u
OUT=${1:?出力フォルダ}; shift
[ $# -ge 1 ] || { echo "ABORT: jsonl が無い"; exit 1; }
HERE=$(cd "$(dirname "$0")" && pwd)
K="-i $HOME/.ssh/manual-only/id_ed25519 ubuntu@49.212.137.46"
W=astro-webapp-celery-worker-1
mkdir -p "$OUT"
[ ! -e "$OUT/snap_all.tsv" ] || { echo "ABORT: $OUT/snap_all.tsv がもうある（上書きしない）"; exit 1; }
PATHS=""
for f in "$@"; do
  b=$(basename "$f")
  ssh $K "docker exec -i $W sh -c 'cat > /tmp/$b'" < "$f" || { echo "ABORT: $b を置けない"; exit 1; }
  PATHS="$PATHS /tmp/$b"
done
# 1回の起動で全部まとめて（同じ読み取り・同じマスタ。fhd_snapshot.py:236-277）
ssh $K "docker exec -i -w /app $W python - convert $PATHS" < "$HERE/fhd_snapshot.py" > "$OUT/snap_all.tsv" 2> "$OUT/convert_stderr.txt"
echo "convert rc=$?"
for f in "$@"; do ssh $K "docker exec $W rm -f /tmp/$(basename "$f")"; done
grep -c '^SKIP' "$OUT/convert_stderr.txt"; grep -E '^CONVERT|^TX|ABORT' "$OUT/convert_stderr.txt"
wc -l "$OUT/snap_all.tsv"
