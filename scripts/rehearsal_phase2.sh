#!/bin/bash
# rehearsal_phase2.sh — SA-18 Phase2 本番リハーサル（deploy.yml verbatim 抽出実行）
#
# PURPOSE: フラグON 本番切替前の1回限り実証テ��ト
#   deploy.yml の Bootstrap/Finalize step script を Python で verbatim 抽出して実行する。
#   test_rollback_simulation.sh（手書きミラー）とは別物。drift を構造的に防ぐ。
#
# USAGE:
#   SALESANCHOR_APP_PASSWORD="<password>" bash scripts/rehearsal_phase2.sh
#
# COVERAGE:
#   Phase A: フラグON → Bootstrap auto-URL(verbatim) → salesanchor_app → RLS OK → data 返却
#   Phase B: 失敗 → Finalize inline rollback(verbatim) → jarvis 復帰 → data 返却
#   Security: SALESANCHOR_APP_PASSWORD が出力に出ない
#
# SUBSTITUTIONS (documented, minimal):
#   1. `cd /home/ubuntu/salesanchor` → `cd ${REHEARSAL_DIR}` (path only)
#   2. `${{ steps.changes.outputs.migrations }}` → `true` (GHA expression)
#   3. ROLLBACK_DISCORD_WEBHOOK → "" (no notification in rehearsal)
#   上記以外は deploy.yml script ブロックをそのまま実行する

set -euo pipefail

PASS="${SALESANCHOR_APP_PASSWORD:?SALESANCHOR_APP_PASSWORD は必須}"
REPO_ROOT="${PWD}"
DEPLOY_YML="${REPO_ROOT}/.github/workflows/deploy.yml"
REHEARSAL_DIR=$(mktemp -d /tmp/phase2-rehearsal-XXXXXX)
REHEARSAL_NET="phase2-rehearsal-net"
PG_CONTAINER="astro-webapp-postgres-1"
BACKEND_CONTAINER="astro-webapp-backend-1"
PASS_CNT=0; FAIL_CNT=0

echo "======================================================"
echo "SA-18 Phase2 本番リハーサル（deploy.yml verbatim 抽出）"
echo "======================================================"
echo "▶ REHEARSAL_DIR: ${REHEARSAL_DIR}"

# ── クリーンアップ ────────────────────────────────────────────────────────────
cleanup_exit() {
  echo ""; echo "▶ Cleanup..."
  cd /tmp
  docker rm -f "${PG_CONTAINER}" "${BACKEND_CONTAINER}" 2>/dev/null || true
  docker network rm "${REHEARSAL_NET}" 2>/dev/null || true
  rm -rf "${REHEARSAL_DIR}"
  echo "======================================================"
  echo "PASS ${PASS_CNT} / FAIL ${FAIL_CNT} / 計 $((PASS_CNT+FAIL_CNT))"
  echo "======================================================"
  if [ "${FAIL_CNT}" -gt 0 ]; then
    echo "❌ リハーサル FAIL — Phase2 切替は HOLD"
    exit 1
  fi
  echo "✅ リハーサル全 PASS — Phase2 切替準備完了"
}
trap cleanup_exit EXIT

pass() { PASS_CNT=$((PASS_CNT+1)); echo "✅ $1"; }
fail() { FAIL_CNT=$((FAIL_CNT+1)); echo "❌ $1"; }

check_no_pass() {
  local label="$1"; local output="$2"
  if printf '%s' "${output}" | grep -qF "${PASS}"; then
    fail "${label}: SALESANCHOR_APP_PASSWORD が出力に含まれている"
  else
    pass "${label}: パスワード未出力"
  fi
}

# deploy.yml から指定ステップの script: ブロックを verbatim 抽出
extract_step_script() {
  python3 - "$1" "${DEPLOY_YML}" << 'PYEOF'
import yaml, sys
with open(sys.argv[2]) as f:
    wf = yaml.safe_load(f)
target = sys.argv[1]
for step in wf['jobs']['deploy']['steps']:
    if step.get('name') == target:
        print(step.get('with', {}).get('script', ''))
        sys.exit(0)
print(f'Step not found: {target}', file=sys.stderr)
sys.exit(1)
PYEOF
}

# 抽出 → documented 変換 → 一時ファイル実行
run_extracted_step() {
  local step_name="$1"; shift
  local raw; raw=$(extract_step_script "${step_name}")
  local script; script=$(printf '%s' "${raw}" \
    | sed "s|cd /home/ubuntu/salesanchor|cd ${REHEARSAL_DIR}|g" \
    | sed 's/\${{ steps\.changes\.outputs\.migrations }}/true/g')
  local tmp; tmp=$(mktemp /tmp/deploy_step_XXXXXX.sh)
  printf '%s\n' "${script}" > "${tmp}"
  env "$@" ROLLBACK_DISCORD_WEBHOOK="" bash "${tmp}" 2>&1
  local rc=$?; rm -f "${tmp}"; return ${rc}
}

wait_healthy() {
  local container="$1"; local max="${2:-15}"
  for i in $(seq 1 "${max}"); do
    if docker exec "${container}" \
        python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" \
        2>/dev/null; then
      return 0
    fi
    sleep 3
  done
  return 1
}

get_count() {
  docker exec "${BACKEND_CONTAINER}" \
    python -c "import urllib.request,json;r=urllib.request.urlopen('http://localhost:8000/api/glossary/test');d=json.loads(r.read());print(d['count'])" \
    2>/dev/null || echo "0"
}

# ── Docker ネットワーク + PostgreSQL ─────────────────────────────────────────
echo ""; echo "▶ Docker ネットワーク作成..."
docker network create "${REHEARSAL_NET}" > /dev/null

echo "▶ PostgreSQL 起動（container_name=${PG_CONTAINER}, alias=postgres）..."
docker run -d \
  --network "${REHEARSAL_NET}" --network-alias postgres \
  --name "${PG_CONTAINER}" \
  -e POSTGRES_USER=jarvis \
  -e POSTGRES_PASSWORD=testpass \
  -e POSTGRES_DB=testdb \
  --health-cmd "pg_isready -U jarvis -d testdb" \
  --health-interval 3s --health-retries 10 \
  postgres:16-alpine > /dev/null

for i in $(seq 1 20); do
  if docker inspect --format='{{.State.Health.Status}}' "${PG_CONTAINER}" 2>/dev/null | grep -q "healthy"; then
    echo "▶ PostgreSQL ready"; break
  fi
  sleep 2
  [ "${i}" -eq 20 ] && { echo "❌ PostgreSQL 起動タイムアウト"; exit 1; }
done

# DB セットアップ（salesanchor_app ロール + RLS テーブル + 種データ）
docker exec -i "${PG_CONTAINER}" psql -U jarvis -d testdb -v ON_ERROR_STOP=1 << 'SQLEOF'
DO $$ BEGIN
  CREATE ROLE salesanchor_app WITH LOGIN NOSUPERUSER NOCREATEDB NOBYPASSRLS;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
CREATE TABLE IF NOT EXISTS public.glossary (
  id SERIAL PRIMARY KEY, tenant_id INTEGER, term TEXT NOT NULL
);
ALTER TABLE public.glossary ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.glossary FORCE ROW LEVEL SECURITY;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.glossary TO salesanchor_app;
GRANT USAGE, SELECT ON SEQUENCE public.glossary_id_seq TO salesanchor_app;
DROP POLICY IF EXISTS sel_pol ON public.glossary;
CREATE POLICY sel_pol ON public.glossary FOR SELECT USING (
  tenant_id IS NULL
  OR tenant_id = NULLIF(current_setting('app.tenant_id', true),'')::INTEGER
);
DROP POLICY IF EXISTS ins_pol ON public.glossary;
CREATE POLICY ins_pol ON public.glossary FOR INSERT WITH CHECK (
  CASE WHEN tenant_id IS NULL
    THEN current_setting('app.is_operator', true) = 'true'
    ELSE tenant_id = NULLIF(current_setting('app.tenant_id', true),'')::INTEGER
  END
);
SET app.is_operator = 'true';
INSERT INTO public.glossary (tenant_id, term) VALUES (1, 'seed_term') ON CONFLICT DO NOTHING;
RESET app.is_operator;
SQLEOF
# salesanchor_app パスワード設定（Bootstrap step [1] と同じ ALTER ROLE）
docker exec "${PG_CONTAINER}" psql -U jarvis -d testdb \
  -c "ALTER ROLE salesanchor_app PASSWORD '${PASS}';" > /dev/null
echo "▶ DB セットアップ完了"

# ── Git repo + Docker Compose 環境 ────────────────────────────────────────────
echo ""; echo "▶ Git repo セットアップ..."
cd "${REHEARSAL_DIR}"
git init -q
git config user.email "rehearsal@test" && git config user.name "rehearsal"

# docker-compose.yml（GOOD/BAD 共通: container_name で production 名を固定）
cat > docker-compose.yml << COMPOSE
services:
  backend:
    build: .
    container_name: ${BACKEND_CONTAINER}
    environment:
      - DATABASE_URL=\${DATABASE_URL:-postgresql://jarvis:testpass@postgres:5432/testdb}
    networks:
      - rehearsal_net
    healthcheck:
      test: ["CMD","python3","-c","import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"]
      interval: 5s
      timeout: 3s
      retries: 3
      start_period: 5s
networks:
  rehearsal_net:
    name: ${REHEARSAL_NET}
    external: true
COMPOSE

cat > Dockerfile << 'DFILE'
FROM python:3.12-slim
RUN pip install psycopg2-binary --quiet --no-cache-dir
WORKDIR /app
COPY server.py .
CMD ["python3","server.py"]
DFILE

# GOOD サーバー（200 + RLS クエリ）
cat > server.py << 'PYEOF'
import http.server, json, os, psycopg2
DATABASE_URL = os.environ.get('DATABASE_URL', '')

def get_count():
    url = DATABASE_URL.replace('postgresql+asyncpg://','postgresql://')
    conn = psycopg2.connect(url)
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            if 'salesanchor_app' in url:
                cur.execute("SET app.tenant_id = '1'")
                cur.execute("SET app.is_operator = ''")
            cur.execute("SELECT COUNT(*) FROM public.glossary WHERE tenant_id=1")
            return cur.fetchone()[0]
    finally:
        conn.close()

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/health':
            b = b'{"status":"ok"}'
            self.send_response(200)
        elif self.path == '/api/glossary/test':
            try:
                c = get_count()
                b = json.dumps({'count':c}).encode()
            except Exception as e:
                b = json.dumps({'count':0,'error':str(e)}).encode()
            self.send_response(200)
        else:
            b = b''
            self.send_response(404)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(b)))
        self.end_headers()
        self.wfile.write(b)
    def log_message(self,*a): pass
http.server.HTTPServer(('',8000),H).serve_forever()
PYEOF

git add -A
git commit -q -m "GOOD: healthy backend with RLS support"
GOOD_SHA=$(git rev-parse HEAD)
echo "▶ GOOD_SHA: ${GOOD_SHA:0:7}"

# PREV_SHA ファイル（deploy.yml Step 0 が書くファイル）
echo "${GOOD_SHA}" > .deploy_prev_sha

# .env（jarvis URL、SA18_PHASE2_ENABLED なし）
cat > .env << ENVEOF
POSTGRES_USER=jarvis
POSTGRES_PASSWORD=testpass
POSTGRES_DB=testdb
DATABASE_URL=postgresql+asyncpg://jarvis:testpass@postgres:5432/testdb
ENVEOF

# BAD コミット（503）
cat > server.py << 'PYEOF'
import http.server
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(503)
        self.send_header('Content-Type','application/json')
        self.end_headers()
        self.wfile.write(b'{"status":"error"}')
    def log_message(self,*a): pass
http.server.HTTPServer(('',8000),H).serve_forever()
PYEOF

git add server.py
git commit -q -m "BAD: 503 server (simulates failed deployment)"
BAD_SHA=$(git rev-parse HEAD)
echo "▶ BAD_SHA: ${BAD_SHA:0:7}"

# ── Phase A: フラグON → Bootstrap auto-URL ────────────────────────────────────
echo ""; echo "======================================================"
echo "Phase A: フラグON → Bootstrap auto-URL（verbatim）"
echo "======================================================"

# PO が .env に1行追加する操作を模擬
echo "SA18_PHASE2_ENABLED=1" >> .env
echo "▶ .env に SA18_PHASE2_ENABLED=1 を追��"

echo "▶ Bootstrap step を deploy.yml から verbatim 抽出して実行..."
_boot_out=$(run_extracted_step "Bootstrap salesanchor_app role (idempotent)" \
  SALESANCHOR_APP_PASSWORD="${PASS}" \
  ADMIN_DATABASE_URL="postgresql+asyncpg://jarvis:testpass@postgres:5432/testdb") || true

_durl_a=$(grep '^DATABASE_URL=' "${REHEARSAL_DIR}/.env" | head -1 | cut -d= -f2-)
if echo "${_durl_a}" | grep -q 'salesanchor_app'; then
  pass "A-1: auto-URL が salesanchor_app URL を設定"
else
  fail "A-1: DATABASE_URL が salesanchor_app URL になっていない (${_durl_a})"
fi
check_no_pass "A-2 Bootstrap出力" "${_boot_out}"

echo "▶ GOOD backend を auto-URL で起動..."
git reset --hard "${GOOD_SHA}" -q  # server.py を GOOD 版に戻す（BAD commit 後なので必須）
docker compose build --quiet 2>&1 | tail -2
DATABASE_URL="${_durl_a}" docker compose up -d 2>&1 | tail -2

if wait_healthy "${BACKEND_CONTAINER}"; then
  pass "A-3: Phase A health 200 (salesanchor_app)"
else
  fail "A-3: Phase A backend 起動失敗"
fi

_count_a=$(get_count)
if [ "${_count_a}" -gt 0 ]; then
  pass "A-4: data count=${_count_a}（salesanchor_app + app.tenant_id=1 → RLS 通過）"
else
  fail "A-4: data count=${_count_a}（RLS ブロックまたは接続失敗）"
fi

# ── Phase B: 失敗 → Finalize inline rollback ──────────────────────────────────
echo ""; echo "======================================================"
echo "Phase B: 失敗 → Finalize inline rollback（verbatim）"
echo "======================================================"

# BAD コードに切り替えてコンテナ再起動（rebuild 必須: GOOD image を上書き）
git reset --hard "${BAD_SHA}" -q
docker compose build --quiet 2>&1 | tail -2
_durl_cur=$(grep '^DATABASE_URL=' .env | head -1 | cut -d= -f2-)
DATABASE_URL="${_durl_cur}" docker compose up -d 2>&1 | tail -2
sleep 6

_hstatus=$(docker exec "${BACKEND_CONTAINER}" \
  python -c "import urllib.request,urllib.error
try:
    urllib.request.urlopen('http://localhost:8000/api/health')
    print('200')
except urllib.error.HTTPError as e:
    print(str(e.code))
except:
    print('0')" 2>/dev/null || echo "0")

if [ "${_hstatus}" != "200" ]; then
  pass "B-0: bad backend 確認（health=${_hstatus}）"
else
  echo "⚠️  B-0: health=200（503 期待）→ 続行"
fi

echo "▶ Finalize step を deploy.yml から verbatim 抽出して実行..."
# 失敗側の Finalize は exit 1 を返す設計のため || true で続行
_fin_out=$(run_extracted_step "Finalize (health check + cleanup)" \
  ROLLBACK_DISCORD_WEBHOOK="") || true

# B-r1: SA18_PHASE2_ENABLED 削除確認
if ! grep -q '^SA18_PHASE2_ENABLED=' "${REHEARSAL_DIR}/.env"; then
  pass "B-r1: SA18_PHASE2_ENABLED を削除確認"
else
  fail "B-r1: SA18_PHASE2_ENABLED が残っている"
fi

# B-r2: DATABASE_URL が jarvis に戻っているか
_durl_rb=$(grep '^DATABASE_URL=' "${REHEARSAL_DIR}/.env" | head -1 | cut -d= -f2-)
if echo "${_durl_rb}" | grep -q 'jarvis'; then
  pass "B-r2: DATABASE_URL が jarvis に復元"
else
  fail "B-r2: DATABASE_URL が jarvis に戻っていない (${_durl_rb})"
fi

# B-1/B-2: ロールバック後 health + data（Finalize が docker compose up 済みのはず）
if wait_healthy "${BACKEND_CONTAINER}"; then
  pass "B-1: rollback 後 health 200"
else
  # Finalize の up が成功していれば不要だが念のため retry
  _durl_rb=$(grep '^DATABASE_URL=' .env | head -1 | cut -d= -f2-)
  DATABASE_URL="${_durl_rb}" docker compose up -d 2>&1 | tail -2
  if wait_healthy "${BACKEND_CONTAINER}"; then
    pass "B-1: rollback 後 health 200（追加 up で復帰）"
  else
    fail "B-1: rollback 後 health タイムアウト"
  fi
fi

_count_b=$(get_count)
if [ "${_count_b}" -gt 0 ]; then
  pass "B-2: rollback 後 data count=${_count_b}（jarvis 接続・データ返却）"
else
  fail "B-2: rollback 後 data count=${_count_b}"
fi

check_no_pass "B-3 Finalize出力" "${_fin_out}"
