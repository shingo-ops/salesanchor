# card: 便3 サーバーの設定から Firebase を外す（設定の値・鍵のファイルの差し込み・見張りの項目）

状態: カード発行（Opus、2026-11-05）。PO の開始の判断は 2026-11-05「1」（便3 を始める）。設計: [design.md](./design.md) §5-3（末尾の「カード作成時の直し」を含む）。根拠: [recon.md](./recon.md)。
担当: クラウドの Sonnet。触ってよいのは下の「1. 触るファイル」だけ。本番・GitHub の secret と Variables には触らない。本番の `.env` と本番の鍵のファイルは便5 まで残す（このカードでは触らない）。PR は作らない（Opus が作る）。
基準: origin/main `a7a66a2cc0a57d6b436445b54f0692e9bcc17ece`。下の行番号はすべてこの時点のもの。行がずれていたら、行番号ではなく「変更前」の文で場所を探す（同じ文が 2 か所あれば BLOCKED: で止まる）。
画面（`frontend/src`）と `backend/` には触らない。

## 読んだ節（docs/handoff/design-partner-card-ops/guards/）
- guards/00-common.md: 全コマンドを作業場所の cd から始める・出力に上限（tail）・sleep しない・プレースホルダを残さない。○
- guards/03-file.md・guards/05-pr.md: 触るファイルを §1 で全部挙げた。消すファイルも §1 に挙げ、`find … -delete` で消す。PR は Opus が手元で shingo-cc 名義で作る（Sonnet は push まで）。○
- guards/10-executor.md: 散文で組み立てを頼まない（§2 に変更前と変更後の文を書いた）。○

## 受領確認（最初の報告の 1 行目に書く）
RECEIVED firebase-removal-bin3 HEAD=（git rev-parse HEAD の 40 桁）

## 0. 実装前点検（外れたら実装せず BLOCKED: で止まる）
- P1 枝 `release/firebase-removal-bin3` を origin から取り直し、`docs/handoff/firebase-removal/card-3.md` が在ること。
- P2 `git diff --quiet a7a66a2cc0a57d6b436445b54f0692e9bcc17ece HEAD -- docker-compose.yml scripts frontend/Dockerfile frontend/.env.example .env.example nginx .github/workflows monitoring docs/external-state-contract.yml` が終了 0（基準から変わっていない）。
- P3 `sed -n '69p;161p;241p;298p' docker-compose.yml` が次の 4 行。
  - `      - GOOGLE_APPLICATION_CREDENTIALS=/app/firebase-credentials.json`
  - `      - ./firebase-credentials.json:/app/firebase-credentials.json:ro`
  - `      - GOOGLE_APPLICATION_CREDENTIALS=/app/firebase-credentials.json`
  - `      - ./firebase-credentials.json:/app/firebase-credentials.json:ro`
- P4 `sed -n '96p' nginx/nginx.conf` が §2-5 の「変更前」と同じ 1 行。
- P5 `sed -n '378p;380p' .github/workflows/deploy.yml` が `            AUTH_PROVIDER='self'` と `            VITE_AUTH_PROVIDER='self'` の 2 行。
- P6 `sed -n '124p' monitoring/grafana/provisioning/dashboards/json/uptime-kuma.json` が `      "title": "Firebase Auth",`。
- P7 `git grep -n "rotate-qa-firebase\|snapshot/firebase.sh\|external-firebase.sh" -- . ':!docs' ':!.claude-pipeline'` が `.github/workflows/external-state-snapshot.yml:88` の 1 件だけ（消す 3 ファイルを呼ぶ所が、このカードで消す段のほかに無い）。
- P8 `cd scripts/tests && node test-detect-external-api-change.js` の最後が「10 passed / 2 failed」に当たる数（今の main でもともと 2 件赤。§2-10 で直す）。

## 1. 触るファイル

書き換える:
1. `docker-compose.yml`（2-1）
2. `scripts/blue-green-cutover.sh`（2-2）
3. `frontend/Dockerfile`（2-3）
4. `.github/workflows/deploy.yml`（2-4）
5. `nginx/nginx.conf`（2-5）
6. `.github/workflows/external-state-snapshot.yml`（2-6）
7. `docs/external-state-contract.yml`（2-7）
8. `scripts/detect-external-api-change.js`（2-8）
9. `scripts/tests/test-detect-external-api-change.js`（2-9）
10. `monitoring/grafana/provisioning/dashboards/json/uptime-kuma.json`（2-10）
11. `.env.example`（2-11）
12. `frontend/.env.example`（2-12）
13. `.github/workflows/e2e.yml`（2-13 注記だけ）

消す（手順5、`find … -delete`）:
- `.github/workflows/rotate-qa-firebase.yml`
- `scripts/snapshot/firebase.sh`
- `scripts/smoke/external-firebase.sh`

触らない: 上に挙げた以外のすべて。特に `.gitleaks.toml`（design §5-3 の直しで残す）、`.gitignore`・`backend/.dockerignore`（鍵の守り）、`.github/workflows/frontend-check.yml`・`.github/workflows/test.yml`（Firebase が無いことを確かめる段）、`backend/`、`frontend/src`、`migrations/`、`docs/`（`docs/external-state-contract.yml` だけは触る）。上のファイルの中でも、書いていない行は 1 文字も変えない。`GCP_PROJECT_ID`（docker-compose.yml:68・:240）、`TCG_SHEETS_SA_KEY_FILE` の差し込み、`VITE_FUNNEL_DASHBOARD` は残す。

## 2. 変更の中身

### 2-1. `docker-compose.yml`
次の行を消す（ほかは変えない）:
- :69 `      - GOOGLE_APPLICATION_CREDENTIALS=/app/firebase-credentials.json`（backend）
- :134-136 の 3 行:
```
      # ADR-1013 便4b: 自社ログインへの切り替え。.env に AUTH_PROVIDER=self が入る。
      # 戻すときは deploy.yml の heredoc を firebase に変える前進 PR（revert はしない）
      - AUTH_PROVIDER=${AUTH_PROVIDER:-firebase}
```
- :161 `      - ./firebase-credentials.json:/app/firebase-credentials.json:ro`
- :201-203 の 3 行:
```
        VITE_FIREBASE_API_KEY: ${VITE_FIREBASE_API_KEY}
        VITE_FIREBASE_AUTH_DOMAIN: ${VITE_FIREBASE_AUTH_DOMAIN}
        VITE_GCP_PROJECT_ID: ${VITE_GCP_PROJECT_ID}
```
- :205 `        VITE_AUTH_PROVIDER: ${VITE_AUTH_PROVIDER:-firebase}`
- :241 `      - GOOGLE_APPLICATION_CREDENTIALS=/app/firebase-credentials.json`（celery-worker）
- :298 `      - ./firebase-credentials.json:/app/firebase-credentials.json:ro`（celery-worker）

変更後の frontend の args は次の 2 行になる:
```
      args:
        VITE_FUNNEL_DASHBOARD: ${VITE_FUNNEL_DASHBOARD}
```

### 2-2. `scripts/blue-green-cutover.sh`
次の 2 行を消す:
- :94 `  --volume "${REPO_DIR}/firebase-credentials.json:/app/firebase-credentials.json:ro" \`
- :99 `  --env GOOGLE_APPLICATION_CREDENTIALS=/app/firebase-credentials.json \`

### 2-3. `frontend/Dockerfile`
変更前（:6-16）:
```
# Vite がビルド時に埋め込む VITE_ 環境変数を受け取る
ARG VITE_FIREBASE_API_KEY
ARG VITE_FIREBASE_AUTH_DOMAIN
ARG VITE_GCP_PROJECT_ID
ARG VITE_FUNNEL_DASHBOARD
ARG VITE_AUTH_PROVIDER
ENV VITE_FIREBASE_API_KEY=$VITE_FIREBASE_API_KEY
ENV VITE_FIREBASE_AUTH_DOMAIN=$VITE_FIREBASE_AUTH_DOMAIN
ENV VITE_GCP_PROJECT_ID=$VITE_GCP_PROJECT_ID
ENV VITE_FUNNEL_DASHBOARD=$VITE_FUNNEL_DASHBOARD
ENV VITE_AUTH_PROVIDER=$VITE_AUTH_PROVIDER
```
変更後:
```
# Vite がビルド時に埋め込む VITE_ 環境変数を受け取る
ARG VITE_FUNNEL_DASHBOARD
ENV VITE_FUNNEL_DASHBOARD=$VITE_FUNNEL_DASHBOARD
```

### 2-4. `.github/workflows/deploy.yml`
次の 2 行を消す（:318・:320 の `sed -e '/^AUTH_PROVIDER=/d'`・`-e '/^VITE_AUTH_PROVIDER=/d'` は残す。本番の `.env` から古い行を消し続けるため）:
- :378 `            AUTH_PROVIDER='self'`
- :380 `            VITE_AUTH_PROVIDER='self'`

### 2-5. `nginx/nginx.conf`
変更前（:96）:
```
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' https://www.gstatic.com; connect-src 'self' https://*.googleapis.com https://*.firebaseio.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:" always;
```
変更後:
```
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; connect-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:" always;
```

### 2-6. `.github/workflows/external-state-snapshot.yml`
- :6 変更前 `#   6 外部システム（Meta / Firebase / GitHub / Cloudflare / Discord / GCP）の` → 変更後 `#   5 外部システム（Meta / GitHub / Cloudflare / Discord / GCP）の`
- :18 変更前 `#   - VPS 2GB 配慮: 6 system を直列実行 (concurrency: 1)` → 変更後 `#   - VPS 2GB 配慮: 5 system を直列実行 (concurrency: 1)`
- :28 `#   FIREBASE_API_KEY` を消す。
- :49 変更前 `    name: Snapshot 6 external systems` → 変更後 `    name: Snapshot 5 external systems`
- :82-90 の 9 行（Firebase の段とその後の空行）を消す:
```
      # --- 2. Firebase snapshot ---
      - name: Snapshot Firebase
        env:
          FIREBASE_API_KEY: ${{ secrets.FIREBASE_API_KEY }}
          GCP_PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
        run: |
          bash scripts/snapshot/firebase.sh
          sleep 5

```
- 番号の注記を 1 つずつ詰める: `      # --- 3. GitHub snapshot ---` → `      # --- 2. GitHub snapshot ---`、`      # --- 4. Cloudflare snapshot ---` → `      # --- 3. Cloudflare snapshot ---`、`      # --- 5. Discord snapshot ---` → `      # --- 4. Discord snapshot ---`、`      # --- 6. GCP snapshot ---` → `      # --- 5. GCP snapshot ---`
- :61-68（鍵の JSON をファイルに書き出す段）と GCP の段は残す。

### 2-7. `docs/external-state-contract.yml`
- :29-39 の 11 行（firebase の塊とその後の空行）を消す:
```
  firebase:
    project_id: sales-ops-with-claude
    auth_domain: auth.salesanchor.jp
    auth_providers: [google.com, password]
    authorized_domains:
      - salesanchor.jp
      - app.salesanchor.jp
      - auth.salesanchor.jp
    credentials_path_env: GOOGLE_APPLICATION_CREDENTIALS  # 実体: /app/firebase-credentials.json
    last_verified: 2026-05-16

```
- :95 変更前 `    project_id: sales-ops-with-claude  # 実体: .env.example:17` → 変更後 `    project_id: sales-ops-with-claude  # 実体: .env.example:18`（2-11 の後、`.env.example` の `GCP_PROJECT_ID` は 18 行目になる）
- :99 `    credentials_path_env: GOOGLE_APPLICATION_CREDENTIALS` は残す（GCP の写しで使う）。

### 2-8. `scripts/detect-external-api-change.js`
:83-91 の 9 行を消す（直前の `  },` と直後の `  {` はそのまま）:
```
  {
    api: 'firebase',
    patterns: [
      /firebase_admin/i,
      /firebase_auth/i,
      /identitytoolkit/i,
      /GOOGLE_APPLICATION_CREDENTIALS/,
    ],
  },
```

### 2-9. `scripts/tests/test-detect-external-api-change.js`
- :125-135 の 11 行（Firebase の試験とその後の空行）を消す:
```
test('既知の Firebase 呼び出しファイルを検出', () => {
  const cases = [
    ['backend/app/auth/dependencies.py', ['firebase']],
    ['backend/app/auth/utils.py', ['firebase']],
  ];
  assert.strictEqual(cases.length, 2);
  for (const [filePath, expectedApis] of cases) {
    expectClassified(filePath, expectedApis);
  }
});

```
- :181 変更前 `test('recon 既知ファイル 31 件をすべて個別検出する', () => {` → 変更後 `test('recon 既知ファイル 29 件をすべて個別検出する', () => {`
- :198-199 の 2 行を消す:
```
    ['backend/app/auth/dependencies.py', ['firebase']],
    ['backend/app/auth/utils.py', ['firebase']],
```
- :216 変更前 `  assert.strictEqual(cases.length, 31);` → 変更後 `  assert.strictEqual(cases.length, 29);`

### 2-10. `monitoring/grafana/provisioning/dashboards/json/uptime-kuma.json`
:54-137 の 84 行（`"title": "Firebase Auth"` の stat の枠 1 つ。:54 の `    {` から :137 の `    },` まで）を消す。消した後、:53 の `    },`（`"title": "外部サービス 死活監視"` の row の閉じ）の次の行が、`"title": "Meta Graph API"` の枠を開く `    {` になる。ほかの枠の `id`・`gridPos` は変えない。Uptime Kuma 自身の見張りの設定は画面で持つもので、このカードの外。

### 2-11. `.env.example`
- :17-31 の 15 行を次の 2 行に置き換える（:32 の空行と `# --- Redis ---` はそのまま）:
変更前:
```
# --- Firebase / Google Identity Platform ---
# AUTH_DOMAIN は ADR-032 によりカスタムドメイン auth.salesanchor.jp に切り替え。
# 切り戻し時は sales-ops-with-claude.firebaseapp.com に戻す（旧ドメインは並行維持）。
GCP_PROJECT_ID=sales-ops-with-claude
FIREBASE_API_KEY=（Firebase APIキーを設定）
FIREBASE_AUTH_DOMAIN=auth.salesanchor.jp
GOOGLE_APPLICATION_CREDENTIALS=/app/firebase-credentials.json

# --- Vite（frontend ビルド時に埋め込まれる値、必須） ---
# これらが未設定だと frontend コンテナが auth/invalid-api-key で画面真っ白になる
# VITE_FIREBASE_AUTH_DOMAIN: ADR-032 でカスタムドメインに切替。切り戻しは旧値
# sales-ops-with-claude.firebaseapp.com に戻すだけで可（再ビルド要）。
VITE_FIREBASE_API_KEY=（Firebase APIキーを設定、FIREBASE_API_KEY と同じ値）
VITE_FIREBASE_AUTH_DOMAIN=auth.salesanchor.jp
VITE_GCP_PROJECT_ID=sales-ops-with-claude
```
変更後:
```
# --- Google Cloud ---
GCP_PROJECT_ID=sales-ops-with-claude
```
- :57-58 の 2 行を消す:
```
# ログイン方式（ADR-1013 便4b）。self=自社ログイン / firebase=Firebase（既定）。deploy.yml が .env に書く
AUTH_PROVIDER=firebase
```
- :61-62 の 2 行を消す:
```
# 画面（ビルド時に埋め込み）のログイン方式。self のときだけ自社 API を使う
VITE_AUTH_PROVIDER=firebase
```
- :59-60（`AUTH_JWT_SECRET` の注記と行）は残す。
- :87 変更前 `# Firebase プロジェクト（sales-ops-with-claude）で作成した OAuth 2.0 クライアント（Web アプリケーション）` → 変更後 `# Google Cloud プロジェクト（sales-ops-with-claude）で作成した OAuth 2.0 クライアント（Web アプリケーション）`

### 2-12. `frontend/.env.example`
:2-6 の 5 行を消す（:1 の注記と :7 の空行はそのまま）:
```
# VITE_FIREBASE_AUTH_DOMAIN: ADR-032 でカスタムドメイン auth.salesanchor.jp に
# 切替。切り戻し時は sales-ops-with-claude.firebaseapp.com に戻して再ビルド。
VITE_GCP_PROJECT_ID=sales-ops-with-claude
VITE_FIREBASE_API_KEY=（Firebase APIキーを設定）
VITE_FIREBASE_AUTH_DOMAIN=auth.salesanchor.jp
```

### 2-13. `.github/workflows/e2e.yml`（注記だけ）
変更前（:9-11）:
```
# mock する設計（tests-e2e/utils/api-mock.ts）。Firebase Auth は
# tests-e2e/utils/auth.ts で IndexedDB persistence + identitytoolkit endpoint
# 経由で bypass する。
```
変更後:
```
# mock する設計（tests-e2e/utils/api-mock.ts）。ログインした状態は
# tests-e2e/utils/auth.ts で保存領域に利用者を先に入れて作る。
```

## 3. 手順

手順1 枝を取る
    cd ~ && git clone https://github.com/shingo-ops/salesanchor.git sa && cd sa && git checkout release/firebase-removal-bin3 && git log --oneline -1 | tail -1

手順2 実装前点検 P1〜P8 を流し、結果をそのまま報告に貼る
    cd ~/sa && ls docs/handoff/firebase-removal/card-3.md | tail -1
    cd ~/sa && git diff --quiet a7a66a2cc0a57d6b436445b54f0692e9bcc17ece HEAD -- docker-compose.yml scripts frontend/Dockerfile frontend/.env.example .env.example nginx .github/workflows monitoring docs/external-state-contract.yml; echo "P2 exit=$?"
    cd ~/sa && sed -n '69p;161p;241p;298p' docker-compose.yml | tail -4
    cd ~/sa && sed -n '96p' nginx/nginx.conf | tail -1
    cd ~/sa && sed -n '378p;380p' .github/workflows/deploy.yml | tail -2
    cd ~/sa && sed -n '124p' monitoring/grafana/provisioning/dashboards/json/uptime-kuma.json | tail -1
    cd ~/sa && git grep -n "rotate-qa-firebase\|snapshot/firebase.sh\|external-firebase.sh" -- . ':!docs' ':!.claude-pipeline' | tail -5
    cd ~/sa/scripts/tests && node test-detect-external-api-change.js 2>&1 | tail -4

手順3 §2 の変更をする（2-1 から 2-13 の順。ファイルごとに変更前の文で場所を探す。1 つのファイルの中は下の行から消すと行番号がずれない）

手順4 番号の注記を確かめる
    cd ~/sa && grep -n "# --- [0-9]\." .github/workflows/external-state-snapshot.yml | tail -8

手順5 3 つのファイルを消す
    cd ~/sa && find .github/workflows -maxdepth 1 -type f -name rotate-qa-firebase.yml -delete && find scripts/snapshot -maxdepth 1 -type f -name firebase.sh -delete && find scripts/smoke -maxdepth 1 -type f -name external-firebase.sh -delete && ls .github/workflows/rotate-qa-firebase.yml scripts/snapshot/firebase.sh scripts/smoke/external-firebase.sh 2>&1 | tail -3

手順6 形の確かめ
    cd ~/sa && node -e "JSON.parse(require('fs').readFileSync('monitoring/grafana/provisioning/dashboards/json/uptime-kuma.json','utf8')); console.log('JSON OK')" | tail -1
    cd ~/sa && python3 -c "import yaml,sys; [yaml.safe_load(open(p)) for p in ['docker-compose.yml','.github/workflows/deploy.yml','.github/workflows/external-state-snapshot.yml','.github/workflows/e2e.yml','docs/external-state-contract.yml']]; print('YAML OK')" 2>&1 | tail -3
    cd ~/sa && bash -n scripts/blue-green-cutover.sh && echo "bash OK" | tail -1
    cd ~/sa && (docker compose -f docker-compose.yml config -q 2>&1 || echo "compose config を流せない") | tail -5

手順7 試験を流す（12 件全部の合格になること）
    cd ~/sa/scripts/tests && node test-detect-external-api-change.js 2>&1 | tail -6

手順8 残りの文字の確かめ
    cd ~/sa && git grep -n -i "firebase\|gstatic\|googleapis\.com\|firebaseio" -- docker-compose.yml scripts/blue-green-cutover.sh frontend/Dockerfile .github/workflows/deploy.yml nginx/nginx.conf .github/workflows/external-state-snapshot.yml docs/external-state-contract.yml scripts/detect-external-api-change.js scripts/tests/test-detect-external-api-change.js monitoring .env.example frontend/.env.example .github/workflows/e2e.yml | tail -10
    cd ~/sa && git grep -n "AUTH_PROVIDER\|VITE_GCP_PROJECT_ID\|VITE_FIREBASE" -- . ':!docs' ':!.claude-pipeline' | tail -10
期待: 1 つめは 0 行。2 つめは `.github/workflows/deploy.yml:318` と `:320` の `sed -e '/^AUTH_PROVIDER=/d'`・`-e '/^VITE_AUTH_PROVIDER=/d'` の 2 行だけ。

手順9 変わったファイルを確かめる
    cd ~/sa && git status --short | tail -25 && git diff --stat | tail -3

手順10 記録して送る
    cd ~/sa && git add -A docker-compose.yml scripts frontend/Dockerfile frontend/.env.example .env.example nginx .github/workflows monitoring docs/external-state-contract.yml && git commit -q -m "chore(config): remove Firebase settings, key mounts and monitoring (firebase-removal bin3)" && git log --oneline -1 | tail -1
    cd ~/sa && git push origin release/firebase-removal-bin3 2>&1 | tail -3

## 4. 想定される分かれ道

BLOCKED: に入ったら、その場で作業を停止し、それまでの出力と §5 の形の報告を返して終わる（直さずに先へ進まない・別のやり方を試さない）。

- P1〜P7 のどれかが外れた → 実装せず `BLOCKED: P番号 と見えたもの`。
- P8 が「10 passed / 2 failed」でない → 数をそのまま報告して `BLOCKED: P8 と見えた数`。
- 手順6 で JSON・YAML・bash のどれかが失敗 → 失敗した出力を報告し、§2 の消し方で直せるなら直してもう一度流す。直らなければ `BLOCKED: 形が壊れた とファイル名`。
- 手順6 で `docker compose` が無い → 「compose config を流せない」と報告して先に進む（YAML の読み込みで代える）。compose が在って `.env` が無いことによる値の空の警告は先に進んでよい。それ以外の失敗は `BLOCKED: compose config と出力`。
- 手順7 で 12 件全部の合格にならない → 赤の試験名と最後の 15 行を報告して `BLOCKED: 試験名`。
- 手順8 で期待と違う行が出た → 行をそのまま報告し、§2 の書き漏れか、§1 の触らない所かを書いて `BLOCKED: 残り`。
- 変更前の文が見つからない・2 か所ある → `BLOCKED: ファイル名と行 変更前の文が一致しない`。
- push が拒まれた → 出力の最後の 3 行を報告して `BLOCKED: push`（force はしない）。

## 5. 報告の形

- 1 行目: 受領確認（`RECEIVED firebase-removal-bin3 HEAD=…`）。
- 手順2・4・5・6・7・8・9・10 の出力（tail の範囲）をそのまま貼る。
- §4 の分かれ道に入ったら、どれに入ったかと見えたもの。
- 秘密の値・鍵・パスワードは貼らない。
- 最後の行: `DONE` か `BLOCKED: 理由`。

END OF CARD
