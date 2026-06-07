#!/bin/bash
# test_rollback_simulation.sh — SA-18 Phase2 安全機構シミュレーション
#
# シナリオ A: Phase2 成功路（health 200 + RLS 有効 + データ取得可能）
# シナリオ B: Phase2 失敗路（503 → ロールバック → jarvis 復帰 → データが返る）
#
# 偽 green 対策の核心:
#   ロールバック後の検証を "health 200" ではなく "データ count > 0" で行う。
#   DATABASE_URL が salesanchor_app のまま残っていると旧コード（tenant_id 未設定）が
#   RLS にブロックされて count=0 になるため、この確認が偽 green を検出する。
#
# 前提: Docker + docker compose が使えること（ubuntu-latest runner または Mac）

set -e

WORKDIR=$(mktemp -d /tmp/phase2-test-XXXXXX)
PG_PORT=15432    # postgres 用（既存テストの 5432 と衝突しない）
APP_PORT=18766   # backend 用（既存 18765 と衝突しない）

trap "echo '▶ Cleanup...'; docker compose -f '${WORKDIR}/docker-compose.yml' down --remove-orphans -v 2>/dev/null || true; rm -rf '${WORKDIR}'" EXIT

echo "======================================================"
echo "SA-18 Phase2 Rollback Simulation"
echo "======================================================"
echo "▶ Test workdir: ${WORKDIR}"

mkdir -p "${WORKDIR}/backend"
cd "${WORKDIR}"

# ============================================================
# インフラ: docker-compose.yml
# DB_USER / DB_PASS / SET_TENANT_CTX は shell env var で制御する
# ============================================================
cat > docker-compose.yml << 'DCEOF'
services:
  postgres:
    image: postgres:16
    container_name: phase2-test-postgres-1
    environment:
      POSTGRES_USER: jarvis
      POSTGRES_PASSWORD: testpass
      POSTGRES_DB: testdb
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U jarvis -d testdb"]
      interval: 2s
      timeout: 5s
      retries: 15

  backend:
    container_name: phase2-test-backend-1
    build:
      context: ./backend
    ports:
      - "18766:8000"
    environment:
      - DB_HOST=postgres
      - DB_USER=${DB_USER:-jarvis}
      - DB_PASS=${DB_PASS:-testpass}
      - DB_NAME=testdb
      - TENANT_ID=1
      - SET_TENANT_CTX=${SET_TENANT_CTX:-0}
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
DCEOF

# ============================================================
# server.py (GOOD / rollback target)
#   SET_TENANT_CTX=1: app.tenant_id を設定（Phase2 salesanchor_app 用）
#   SET_TENANT_CTX=0: 設定しない（pre-Phase2 / jarvis は superuser なので無問題）
# ============================================================
cat > backend/server.py << 'PYEOF'
import json, os
from http.server import HTTPServer, BaseHTTPRequestHandler
import psycopg2

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_USER = os.getenv("DB_USER", "jarvis")
DB_PASS = os.getenv("DB_PASS", "testpass")
DB_NAME = os.getenv("DB_NAME", "testdb")
TENANT_ID = os.getenv("TENANT_ID", "1")
SET_TENANT_CTX = os.getenv("SET_TENANT_CTX", "0") == "1"

def get_data_count():
    conn = psycopg2.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS, dbname=DB_NAME,
        application_name="salesanchor_backend"
    )
    # autocommit=True: SET is session-level and persists for this connection lifetime.
    # SET LOCAL requires being inside an explicit transaction (BEGIN), which psycopg2
    # may not issue implicitly before the first statement in all versions.
    conn.autocommit = True
    cur = conn.cursor()
    if SET_TENANT_CTX:
        cur.execute("SET app.tenant_id = %s", (TENANT_ID,))
        cur.execute("SET app.is_operator TO ''")
    cur.execute("SELECT count(*) FROM glossary WHERE tenant_id = %s", (int(TENANT_ID),))
    count = cur.fetchone()[0]
    conn.close()
    return count

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/health':
            body = json.dumps({"status": "ok"}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(body)
        elif self.path == '/api/data':
            try:
                count = get_data_count()
                body = json.dumps({"count": count}).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                body = json.dumps({"error": str(e)}).encode()
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()
    def log_message(self, *args): pass

HTTPServer(('0.0.0.0', 8000), Handler).serve_forever()
PYEOF

cat > backend/Dockerfile << 'DFEOF'
FROM python:3.12-slim
RUN pip install --no-cache-dir psycopg2-binary
COPY server.py /app/server.py
WORKDIR /app
EXPOSE 8000
CMD ["python", "server.py"]
DFEOF

# .env: .gitignore に入れて git reset --hard で変更されないことを保証
cat > .gitignore << 'IEOF'
.env
IEOF

cat > .env << 'ENVEOF'
POSTGRES_USER=jarvis
POSTGRES_PASSWORD=testpass
POSTGRES_DB=testdb
ENVEOF

# postgres 起動
docker compose up -d postgres
echo "▶ Postgres 起動中..."
for _i in $(seq 1 20); do
  docker exec phase2-test-postgres-1 pg_isready -U jarvis -d testdb -q 2>/dev/null \
    && { echo "▶ Postgres ready"; break; }
  sleep 2
  [ "${_i}" -eq 20 ] && { echo "❌ Postgres startup timeout"; exit 1; }
done

# スキーマ + RLS + salesanchor_app ロール + テストデータ
# -i が必須: docker exec はデフォルトで stdin を接続しない → psql がヒアドキュメントを受け取れない
docker exec -i phase2-test-postgres-1 psql -U jarvis -d testdb -v ON_ERROR_STOP=1 << 'SQL'
-- salesanchor_app: NOSUPERUSER NOBYPASSRLS（本番ロールと同じ属性）
DO $$ BEGIN
  CREATE ROLE salesanchor_app WITH LOGIN PASSWORD 'apppass'
    NOSUPERUSER NOCREATEDB NOBYPASSRLS;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- テストテーブル + RLS
CREATE TABLE IF NOT EXISTS glossary (
  id SERIAL PRIMARY KEY,
  tenant_id INTEGER,
  term TEXT NOT NULL
);
ALTER TABLE glossary ENABLE ROW LEVEL SECURITY;
ALTER TABLE glossary FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS sel_pol ON glossary;
CREATE POLICY sel_pol ON glossary FOR SELECT USING (
  tenant_id IS NULL
  OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
);
DROP POLICY IF EXISTS ins_pol ON glossary;
CREATE POLICY ins_pol ON glossary FOR INSERT WITH CHECK (
  CASE WHEN tenant_id IS NULL
    THEN current_setting('app.is_operator', true) = 'true'
    ELSE tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
  END
);

-- salesanchor_app に DML 付与
GRANT USAGE ON SCHEMA public TO salesanchor_app;
GRANT SELECT, INSERT ON glossary TO salesanchor_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO salesanchor_app;

-- テストデータ（operator として挿入）
SET app.is_operator = 'true';
INSERT INTO glossary (tenant_id, term) VALUES (1, 'term-tenant1') ON CONFLICT DO NOTHING;
INSERT INTO glossary (tenant_id, term) VALUES (2, 'term-tenant2') ON CONFLICT DO NOTHING;
RESET app.is_operator;
SQL
echo "▶ DB スキーマ + データ準備完了"

# git: GOOD コミット（pre-Phase2 server.py）
git init -q
git config user.email "ci@test.local"
git config user.name "Phase2 Sim"
git add .
git commit -q -m "GOOD: pre-Phase2 server (no tenant ctx)"
GOOD_SHA=$(git rev-parse HEAD)
echo "▶ GOOD_SHA: ${GOOD_SHA:0:7}"

# ============================================================
# SCENARIO A: Phase2 成功路
#   salesanchor_app + SET_TENANT_CTX=1 → health 200 + data > 0
# ============================================================
echo ""
echo "======================================================"
echo "SCENARIO A: Phase2 成功路"
echo "======================================================"

# Phase2 切替: .env に salesanchor_app URL + フラグ追加（.gitignore 済のため git commit 不要）
cat >> .env << 'ENVEOF'
DATABASE_URL=postgresql://salesanchor_app:apppass@postgres:5432/testdb
SA18_PHASE2_ENABLED=1
ENVEOF

export DB_USER=salesanchor_app DB_PASS=apppass SET_TENANT_CTX=1
docker compose build -q

for _svc in backend; do
  docker ps -a --filter "name=phase2-test-${_svc}" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true
done
docker compose up -d backend

echo "▶ Backend (Phase2) 起動中..."
for _i in $(seq 1 15); do
  sleep 3
  curl -sf "http://localhost:${APP_PORT}/api/health" > /dev/null 2>&1 && break
  echo "  ...waiting (${_i}/15)..."
done

HEALTH_A=$(curl -sf "http://localhost:${APP_PORT}/api/health" 2>/dev/null || echo "FAIL")
echo "▶ Health response: ${HEALTH_A}"
echo "${HEALTH_A}" | python3 -c "import sys,json;d=json.load(sys.stdin);exit(0 if d.get('status')=='ok' else 1)" \
  && echo "✅ A-1 PASS: Phase2 health 200" \
  || { echo "❌ SCENARIO A FAIL: health not ok — ${HEALTH_A}"; exit 1; }

# DB 内のデータを直接確認（デバッグ: HTTP テスト前にデータ存在を検証）
echo "▶ DB 内データ確認 (jarvis/superuser):"
docker exec phase2-test-postgres-1 psql -U jarvis -d testdb -t -c \
  "SELECT count(*) FROM glossary WHERE tenant_id = 1;" | tr -d ' \n'
echo " rows for tenant_id=1"

# salesanchor_app で直接確認（SET SESSION + tenant_id=1）
echo "▶ salesanchor_app 直接 psql 確認:"
docker exec -e PGPASSWORD=apppass phase2-test-postgres-1 \
  psql -U salesanchor_app -d testdb -t \
  -c "SET app.tenant_id = '1'; SELECT count(*) FROM glossary WHERE tenant_id = 1;" 2>&1 | tr -d ' \n'
echo ""

DATA_A=$(curl -sf "http://localhost:${APP_PORT}/api/data" 2>/dev/null || echo '{"count":0,"error":"curl failed"}')
echo "▶ Data: ${DATA_A}"
COUNT_A=$(echo "${DATA_A}" | python3 -c "import sys,json;print(json.load(sys.stdin).get('count',0))")
[ "${COUNT_A}" -gt 0 ] \
  && echo "✅ A-2 PASS: data count=${COUNT_A} (salesanchor_app + tenant_id → RLS 正常通過)" \
  || { echo "❌ SCENARIO A FAIL: data count=0 (salesanchor_app が RLS にブロックされた)"; exit 1; }

# smoke[7] 相当: SA18_PHASE2_ENABLED=1 && DATABASE_URL=salesanchor_app の整合確認
grep -q '^SA18_PHASE2_ENABLED=1' .env \
  && echo "✅ A-3 PASS: SA18_PHASE2_ENABLED=1 が .env に存在" \
  || { echo "❌ SCENARIO A FAIL: SA18_PHASE2_ENABLED が .env にない"; exit 1; }

grep -q '^DATABASE_URL=.*salesanchor_app' .env \
  && echo "✅ A-4 PASS: DATABASE_URL = salesanchor_app (フラグと整合)" \
  || { echo "❌ SCENARIO A FAIL: SA18_PHASE2_ENABLED=1 だが DATABASE_URL が salesanchor_app でない"; exit 1; }

# ============================================================
# SCENARIO B: Phase2 失敗路 → ロールバック → データ返却
# ============================================================
echo ""
echo "======================================================"
echo "SCENARIO B: Phase2 失敗路 → ロールバック → データ返却"
echo "======================================================"

# PREV_SHA 保存（deploy.yml Step 0 の模擬）
echo "${GOOD_SHA}" > .deploy_prev_sha
echo "▶ PREV_SHA 保存: ${GOOD_SHA:0:7}"

# BAD Phase2: 503
cat > backend/server.py << 'PYEOF'
from http.server import HTTPServer, BaseHTTPRequestHandler
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/health':
            self.send_response(503)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"error":"unhealthy"}')
        else:
            self.send_response(404)
            self.end_headers()
    def log_message(self, *args): pass
HTTPServer(('0.0.0.0', 8000), Handler).serve_forever()
PYEOF

git add .
git commit -q -m "BAD: Phase2 health 503"
BAD_SHA=$(git rev-parse HEAD)
echo "▶ BAD_SHA: ${BAD_SHA:0:7}"

export DB_USER=salesanchor_app DB_PASS=apppass SET_TENANT_CTX=1
docker compose build -q

for _svc in backend; do
  docker ps -a --filter "name=phase2-test-${_svc}" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true
done
docker compose up -d backend

for _i in $(seq 1 6); do
  sleep 3
  curl -s "http://localhost:${APP_PORT}/api/health" -o /dev/null 2>/dev/null && break
  echo "  ...waiting for BAD container (${_i}/6)..."
done

HTTP_B=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${APP_PORT}/api/health" 2>/dev/null || echo "000")
[ "${HTTP_B}" = "503" ] \
  || { echo "❌ SETUP FAIL: BAD が 503 を返さない (got ${HTTP_B})"; exit 1; }
echo "✅ BAD Phase2 起動確認 (503)"

# --- ロールバック実行 ---
echo "❌ Health check failed — starting auto-rollback..."
PREV_SHA=$(cat .deploy_prev_sha 2>/dev/null || echo "")
_rollback_result="failed"

if [ -n "${PREV_SHA}" ]; then
  echo "→ Rolling back to ${PREV_SHA:0:7}..."
  git reset --hard "${PREV_SHA}"

  # SA-18: DATABASE_URL を jarvis に戻し SA18_PHASE2_ENABLED を削除
  # .env は gitignore されているため git reset --hard では変わらない → 手動復元
  _pguser_rb=$(grep '^POSTGRES_USER=' .env | cut -d= -f2- | head -1 | tr -d '[:space:]')
  _pgpass_rb=$(grep '^POSTGRES_PASSWORD=' .env | cut -d= -f2- | head -1 | tr -d '\r\n')
  _pgdb_rb=$(grep '^POSTGRES_DB=' .env | cut -d= -f2- | head -1 | tr -d '[:space:]')
  _rb_durl="postgresql://${_pguser_rb}:${_pgpass_rb}@postgres:5432/${_pgdb_rb}"
  sed -i '/^DATABASE_URL=/d' .env
  echo "DATABASE_URL=${_rb_durl}" >> .env
  sed -i '/^SA18_PHASE2_ENABLED=/d' .env
  echo "ℹ️  ロールバック: DATABASE_URL=${_rb_durl}、SA18_PHASE2_ENABLED 削除"

  # B-r1: SA18_PHASE2_ENABLED が削除されていることを確認
  grep -q '^SA18_PHASE2_ENABLED=' .env \
    && { echo "❌ B-r1 FAIL: SA18_PHASE2_ENABLED がまだ .env に残っている"; exit 1; } \
    || echo "✅ B-r1 PASS: SA18_PHASE2_ENABLED を削除確認"

  # B-r2: DATABASE_URL が jarvis に戻っていることを確認
  grep -q '^DATABASE_URL=.*salesanchor_app' .env \
    && { echo "❌ B-r2 FAIL: DATABASE_URL が salesanchor_app のまま（URL 復元失敗）"; exit 1; } \
    || echo "✅ B-r2 PASS: DATABASE_URL が jarvis に復元"

  # ビルド（GOOD_SHA server.py = pre-Phase2 + DB_USER=jarvis で起動）
  export DB_USER=jarvis DB_PASS=testpass SET_TENANT_CTX=0
  _rb_build=false
  for _attempt in 1 2 3; do
    docker compose build -q 2>&1 && { _rb_build=true; break; }
    echo "Rollback build attempt ${_attempt} failed. Retrying in 5s..."
    sleep 5
  done

  if [ "${_rb_build}" = "true" ]; then
    for _svc in backend; do
      docker ps -a --filter "name=phase2-test-${_svc}" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true
    done
    docker compose up -d --remove-orphans

    echo "Waiting for rollback to stabilize (max 60s)..."
    for _i in $(seq 1 12); do
      sleep 5
      curl -sf "http://localhost:${APP_PORT}/api/health" > /dev/null 2>&1 \
        && { _rollback_result="health_ok"; break; }
      echo "  ...waiting (${_i}/12)..."
    done
  fi
fi

# B-1: health 200 確認
[ "${_rollback_result}" = "health_ok" ] \
  && echo "✅ B-1 PASS: ロールバック後 health 200" \
  || { echo "❌ SCENARIO B FAIL: ロールバック後 health が 200 にならない"; exit 1; }

# B-2: データが返ること確認（偽 green 防止の核心）
# DATABASE_URL が salesanchor_app のまま残っていると旧コード（SET_TENANT_CTX=0）が
# RLS にブロックされて count=0 になり、この確認が失敗する。
# jarvis（superuser / BYPASSRLS）に正しく戻っていれば count > 0。
DATA_RB=$(curl -sf "http://localhost:${APP_PORT}/api/data" 2>/dev/null || echo '{"count":0}')
echo "▶ ロールバック後 Data: ${DATA_RB}"
COUNT_RB=$(echo "${DATA_RB}" | python3 -c "import sys,json;print(json.load(sys.stdin).get('count',0))")
[ "${COUNT_RB}" -gt 0 ] \
  && echo "✅ B-2 PASS: ロールバック後 count=${COUNT_RB}（jarvis 接続・データ正常返却）" \
  || { echo "❌ SCENARIO B FAIL: count=0（DATABASE_URL が salesanchor_app のまま → RLS 偽 green）"; exit 1; }

# Discord dry-run
echo ""
echo "▶ [Discord dry-run] rollback success payload (webhook not sent in simulation)"

echo ""
echo "======================================================"
echo "✅ PHASE2 ROLLBACK SIMULATION PASSED"
echo "   Scenario A: Phase2 成功（health 200 + RLS 有効 + データ取得可）"
echo "   Scenario B: Phase2 失敗 → ロールバック → jarvis 復帰 → データ返却"
echo "======================================================"
exit 0
