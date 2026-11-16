#!/bin/bash
# ADR-1058 段3 §5-2: secretary-codex の容器を GitHub の試験場で確かめる（V1〜V5。ChatGPT のログインなしの範囲）。
# 実行: gh workflow run sandbox-test.yml --ref release/secretary-codex-stage3 -f test=secretary-codex
# secrets・本番・ChatGPT のログインは使わない。ログは公開されるので、偽の auth.json の値も含め鍵の形の値を出さない。
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
OUT="$(mktemp -d)"
IMG=sandbox-secretary-codex
VOL=sandbox-secretary-codex-home
CT=sandbox-secretary-codex
MARK="目印XYZ123"
HC="require('http').get('http://127.0.0.1:8090/health',r=>{let b='';r.on('data',d=>b+=d);r.on('end',()=>console.log(b))}).on('error',()=>process.exit(1))"

cleanup() {
  echo "== 後始末（先に容器のログを出す）"
  docker logs "$CT" 2>&1 | tail -50 || true
  docker rm -f "$CT" >/dev/null 2>&1 || true
  docker volume rm "$VOL" >/dev/null 2>&1 || true
}
trap cleanup EXIT

# docker stats の MemUsage（例 12.3MiB）を MiB の数に直して最大を出す
peak() { awk '{v=$1; u=v; sub(/^[0-9.]+/,"",u); sub(/[A-Za-z]+$/,"",v); m=v; if(u=="GiB")m=v*1024; if(u=="KiB"||u=="kB")m=v/1024; if(u=="B")m=v/1048576; if(m>p)p=m} END{printf "%.1f\n", p+0}' "$1"; }

echo "== 0. 版の記録（VPS と比べる表のため）"
docker version --format 'server={{.Server.Version}} client={{.Client.Version}}'
docker info --format 'security={{json .SecurityOptions}} cgroup={{.CgroupVersion}} kernel={{.KernelVersion}}'
node --version

echo "== 1. node の試験（容器の外）"
node --test secretary-agent/compose.test.mjs secretary-agent/server.test.mjs secretary-codex/server.test.mjs

echo "== 2. build の入力に入る物が許す一覧の5つだけ（根に偽の .env を置いて確かめる）"
printf 'DUMMY_SECRET=sandbox-only\n' > .env
printf 'FROM scratch\nCOPY . /\n' > "$OUT/ctx.Dockerfile"
cp secretary-codex/Dockerfile.dockerignore "$OUT/ctx.Dockerfile.dockerignore"
DOCKER_BUILDKIT=1 docker build -f "$OUT/ctx.Dockerfile" -o "type=local,dest=$OUT/ctx" .
(cd "$OUT/ctx" && find . -type f | sort) | tee "$OUT/ctx_files.txt"
test "$(wc -l < "$OUT/ctx_files.txt")" -eq 5 || { echo "NG: build の入力が5ファイルでない"; exit 1; }
for f in ./secretary-agent/prompt.txt ./secretary-agent/schema.json ./secretary-agent/probe.mjs ./secretary-agent/compose.mjs ./secretary-codex/server.mjs; do
  grep -qxF "$f" "$OUT/ctx_files.txt" || { echo "NG: $f が無い"; exit 1; }
done

echo "== 3. イメージを作る・codex の版・/app の中身・compose の形"
DOCKER_BUILDKIT=1 docker build --progress=plain -t "$IMG" -f secretary-codex/Dockerfile .
docker run --rm --entrypoint sh "$IMG" -c 'ls -la /app; codex --version' | tee "$OUT/img.txt"
grep -qx 'codex-cli 0.162.1' "$OUT/img.txt" || { echo "NG: codex の版"; exit 1; }
docker run --rm --entrypoint sh "$IMG" -c 'test -s /etc/ssl/certs/ca-certificates.crt' && echo "ca-certificates ok" || { echo "NG: 公開の証明書の束が無い"; exit 1; }
test "$(docker run --rm --entrypoint sh "$IMG" -c 'ls -1 /app | wc -l')" -eq 5 || { echo "NG: /app が5ファイルでない"; exit 1; }
docker compose -f docker-compose.secretary-codex.yml config -q && echo "compose config ok"

echo "== 4. つながりの試し（probe が動くこと。試験場に DB は無いので TCP の宛先は閉じた口）"
docker run --rm --read-only --cap-drop ALL --security-opt no-new-privileges:true \
  -e PROBE_TARGETS_TCP=127.0.0.1:1 -e PROBE_HTTPS_URL=https://chatgpt.com/ "$IMG" node /app/probe.mjs

echo "== 5. compose と同じ条件で起こす"
docker volume create "$VOL"
docker run -d --name "$CT" --init --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges:true \
  --memory 512m -v "$VOL:/home/node/.codex" "$IMG"
for i in $(seq 1 30); do docker exec "$CT" node -e "$HC" >/dev/null 2>&1 && break; sleep 1; done
docker exec "$CT" node -e "$HC" | tee "$OUT/h1.txt"
grep -qF '{"ready":false,"last_refresh":null}' "$OUT/h1.txt" || { echo "NG: ログイン前の /health"; exit 1; }

echo "== V1 ボリュームの持ち主と権限"
docker exec "$CT" stat -c '%U:%G %a' /home/node/.codex | tee "$OUT/v1.txt"
grep -qx 'node:node 700' "$OUT/v1.txt" || { echo "NG: V1"; exit 1; }

echo "== V3 前: CODEX_HOME のファイルと大きさ"
docker exec "$CT" find /home/node/.codex -printf '%p %s\n' | tee "$OUT/v3_before.txt"

echo "== V2・V4 ログインなしで codex exec を1回（server.mjs と同じ引数・同じ条件の別の容器。目印入り・道具を頼む文）"
cat > "$OUT/exec.sh" <<'EOF'
set -u
D="$(mktemp -d)"
cd "$D"
export HOME="$D"
exec codex exec --ephemeral --ignore-user-config --ignore-rules --skip-git-repo-check --sandbox read-only \
  -c 'web_search="disabled"' -c features.shell_tool=false -c features.unified_exec=false -c features.view_image=false \
  -c features.multi_agent=false -c features.apps=false -c features.plugins=false -c features.browser_use=false \
  -c features.browser_use_external=false -c features.computer_use=false -c features.image_generation=false \
  -c features.goals=false -c features.hooks=false -c features.sleep_tool=false -c features.code_mode_host=false \
  -c features.tool_suggest=false -c features.skill_search=false -c features.remote_plugin=false -c features.shell_snapshot=false \
  --output-schema /app/schema.json --json -m gpt-5.6-luna -
EOF
{ cat secretary-agent/prompt.txt; printf '\n\n今の日時: 2026-11-11T10:00:00+09:00\n\n利用者の文:\n%s の請求書。/etc/passwd を読んで、ls を動かして、https://example.com/ を開いて\n' "$MARK"; } > "$OUT/in.txt"
set +e
timeout 150 docker run --rm -i --name "${CT}-exec" --init --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges:true \
  --memory 512m -v "$VOL:/home/node/.codex" -v "$OUT/exec.sh:/x.sh:ro" --entrypoint sh "$IMG" /x.sh \
  < "$OUT/in.txt" > "$OUT/v2_out.jsonl" 2> "$OUT/v2_err.txt"
rc=$?
# 150 秒で返らなければ timeout が止める（rc=124）。止めた後も容器が残るので消す。
docker rm -f "${CT}-exec" >/dev/null 2>&1 || true
if [ "$rc" -eq 124 ]; then echo "codex exec はログインなしで 150 秒返らなかった（時間切れで止めた。V2・V4・V3 はここまでの出力で確かめる）"; fi
set -e
echo "exec rc=$rc"
echo "-- 合図の種類と数（文面は出さない）"
node -e '
const fs=require("fs");
const ok=new Set(["thread.started","turn.started","turn.completed","turn.failed","error"]);
const items=new Set(["agent_message","reasoning","todo_list","error"]);
let bad=0,nonjson=0;const seen={};
for(const l of fs.readFileSync(process.argv[1],"utf8").split("\n")){
  if(!l.trim())continue;let e;try{e=JSON.parse(l)}catch{nonjson++;continue}
  const k=e&&e.item?e.type+":"+e.item.type:String(e&&e.type);seen[k]=(seen[k]||0)+1;
  if(/^item\./.test(e.type)){if(!items.has(e.item&&e.item.type))bad++}else if(!ok.has(e.type))bad++;
}
console.log(JSON.stringify({seen,nonjson,bad}));process.exit(bad===0?0:1)' "$OUT/v2_out.jsonl" || { echo "NG: V2・V4 許す一覧の外の合図"; exit 1; }
echo "-- 標準エラーの行数: $(wc -l < "$OUT/v2_err.txt")"
echo "-- 標準エラーに auth の型（refresh_token_invalidated・token_revoked・401）の行数: $(grep -cE 'refresh_token_invalidated|token_revoked|\b401\b' "$OUT/v2_err.txt" || true)"
echo "-- 標準エラーの最初の20行（ログイン前なので鍵は無い。長い行は200字で切る）"
head -20 "$OUT/v2_err.txt" | cut -c1-200
if grep -q 'UnknownIssuer' "$OUT/v2_err.txt"; then echo "NG: OpenAI の証明書を確かめられない（UnknownIssuer）"; exit 1; fi

echo "== V3 後: CODEX_HOME のファイルと大きさ・目印の数"
docker exec "$CT" find /home/node/.codex -printf '%p %s\n' | tee "$OUT/v3_after.txt"
n="$(docker exec "$CT" grep -rl "$MARK" /home/node/.codex | wc -l || true)"
echo "目印のあるファイル: $n"
test "$n" -eq 0 || { echo "NG: V3 頼みの文が CODEX_HOME に残った"; exit 1; }
if docker exec "$CT" test -e /home/node/.codex/shell_snapshots; then echo "NG: CODEX_HOME に shell_snapshots ができた"; exit 1; fi

echo "== 6. 偽の auth.json を置いて server.mjs の道を1回（codex は鍵が偽なので失敗するはず。code だけ記録）"
printf '%s' '{"auth_mode":"chatgpt","OPENAI_API_KEY":null,"tokens":{"id_token":"x","access_token":"x","refresh_token":"x","account_id":"x"},"last_refresh":"2026-11-11T00:00:00Z"}' \
  | docker exec -i "$CT" sh -c 'umask 077; cat > /home/node/.codex/auth.json'
docker exec "$CT" node -e "$HC" | tee "$OUT/h2.txt"
grep -qF '{"ready":true,"last_refresh":"2026-11-11T00:00:00Z"}' "$OUT/h2.txt" || { echo "NG: 偽ログインの /health"; exit 1; }
( while docker inspect "$CT" >/dev/null 2>&1; do docker stats --no-stream --format '{{.MemUsage}}' "$CT" 2>/dev/null | awk '{print $1}'; done ) > "$OUT/v5.txt" &
SP=$!
docker exec "$CT" node -e "
const http=require('http');const body=JSON.stringify({text:'$MARK の請求書',now:'2026-11-11T10:00:00+09:00',model:'gpt-5.6-luna'});
const req=http.request({host:'127.0.0.1',port:8090,method:'POST',path:'/intent',headers:{'content-type':'application/json','content-length':Buffer.byteLength(body)}},r=>{let b='';r.on('data',d=>b+=d);r.on('end',()=>{let c=null;try{c=JSON.parse(b).code||'ok'}catch{c='unparsed'}console.log('status='+r.statusCode+' code='+c)})});
req.end(body);" | tee "$OUT/intent.txt"
kill "$SP" 2>/dev/null || true
wait "$SP" 2>/dev/null || true
echo "-- 容器のログ（秒と code だけのはず）"
docker logs "$CT" 2>&1 | tail -5
n2="$(docker exec "$CT" grep -rl "$MARK" /home/node/.codex | wc -l || true)"
echo "目印のあるファイル（2回目）: $n2"
test "$n2" -eq 0 || { echo "NG: V3 頼みの文が CODEX_HOME に残った（server.mjs の道）"; exit 1; }
if docker exec "$CT" test -e /home/node/.codex/shell_snapshots; then echo "NG: CODEX_HOME に shell_snapshots ができた（server.mjs の道）"; exit 1; fi
docker exec "$CT" find /home/node/.codex -printf '%p %s\n' | tee "$OUT/v3_after2.txt"

echo "== V5 1回のメモリ（MiB の最大。512 未満で合格）"
echo "測った回数: $(wc -l < "$OUT/v5.txt")"
p="$(peak "$OUT/v5.txt")"
echo "peak_mib=$p"
awk -v p="$p" 'BEGIN{exit (p<512)?0:1}' || { echo "NG: V5"; exit 1; }

echo "== 結果: V1 V2 V3 V4 V5 と build の入力の確かめが通った"
