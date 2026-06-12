# Stage 0 GO申請 — SA設計図書サイト配信インフラ

| 項目 | 内容 |
|------|------|
| 日付 | 2026-06-12 |
| 申請者 | Hikky-dev（Terminal CC） |
| 承認者 | Shingo（PO） |
| 根拠 | `docs/handoff/design-site/design.md` §6 Stage 0 GO条件 |
| 状態 | **⬜ 承認待ち** |

---

## 申請内容（実行前にShingoの明示GOが必要）

以下の3点を本番に適用します。**このドキュメントを確認し、差分に問題がなければ「GO」の一言をいただければ実行します。**

1. **nginx.conf に `/design/` location を追加**（既存ブロックの変更なし）
2. **docker-compose.yml の nginx volumes に2行追加**（htpasswdディレクトリ・コンテンツディレクトリ）
3. **deploy.yml に2ステップ追加**（進捗JSON変換 + 設計図書同期）

htpasswdの作成は別途VPS上で手動実行（コマンドは §4 参照）。

---

## §1 nginx.conf 追加差分

**挿入位置**: `nginx/nginx.conf` の `/status/` ブロック（:187）と `/` catch-allブロック（:200）の間

```diff
     location /status/ {
         proxy_pass http://49.212.160.98:3001/;
         ...
     }

+    # ================================================================
+    # SA設計図書サイト（ADR-134）— Basic認証付き静的配信
+    # デフォルトdeny: htpasswdファイルが読めない/消えた場合nginxは500を返す
+    # （401が出ない = 認証設定が外れたわけではない構造）
+    # ================================================================
+    location /design/ {
+        alias /var/www/design-site/;
+        auth_basic "SA Design Site";
+        auth_basic_user_file /etc/nginx/htpasswd.d/design-site;
+        try_files $uri $uri/ =404;
+
+        add_header X-Frame-Options "DENY" always;
+        add_header X-Content-Type-Options "nosniff" always;
+        add_header Cache-Control "no-store, no-cache" always;
+    }

     location = /metrics {
```

**影響確認**: `/design/` は既存の `/api/`, `/grafana/`, `/status/`, `/metrics/`, `/` のどれとも
URI プレフィックスが重複しない（recon.md §8で確認済み）。
`/` catch-all の前に配置するため nginx の first-match ルールに適合。

---

## §2 docker-compose.yml 追加差分

**対象**: `docker-compose.yml` の nginx サービスの `volumes` セクション（:10〜15付近）

```diff
     volumes:
       - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
       - ./certbot/www:/var/www/certbot:ro
       - ./www/salesanchor:/var/www/salesanchor:ro
+      - ./www/design-site:/var/www/design-site:ro
+      - ./nginx/htpasswd.d:/etc/nginx/htpasswd.d:ro
       - ./certbot/conf:/etc/letsencrypt:ro
```

**`www/design-site/`**: deploy.yml が rsync で同期するディレクトリ（下記参照）。
**`nginx/htpasswd.d/`**: VPS上に手動作成・git追跡禁止。`--force-recreate` を含むデプロイで消えない
（bind mountのため、コンテナ再作成はホストのファイルを削除しない）。

---

## §3 deploy.yml 追加差分

**挿入位置**: 既存の「Rsync LP build to VPS」ステップの直後

```yaml
      # ============================================================
      # SA設計図書サイト デプロイ（ADR-134）
      # ① 進捗表 → progress.json 変換（失敗=デプロイ停止）
      # ② docs/design-site/ を www/design-site/ に同期
      # ③ 毎デプロイ smoke で認証チェック・既存経路確認
      # ============================================================
      - name: Generate progress.json from SA-OVERVIEW
        run: |
          python3 scripts/design-site/generate-progress-json.py \
            docs/plans/sa-progress/00-SA-OVERVIEW.md \
            /tmp/design-site-progress.json

      - name: Rsync design-site to VPS
        run: |
          rsync -avz --delete \
            docs/design-site/ \
            ${{ secrets.VPS_USER }}@${{ secrets.VPS_HOST }}:/home/ubuntu/salesanchor/www/design-site/
          rsync -avz \
            /tmp/design-site-progress.json \
            ${{ secrets.VPS_USER }}@${{ secrets.VPS_HOST }}:/home/ubuntu/salesanchor/www/design-site/progress.json
```

**「Verify deployment」ステップに追記（smoke）**:

```bash
            # ── SA設計図書サイト smoke（ADR-134）────────────────────
            echo "Design-site smoke: 認証なし=401 チェック..."
            _ds_401=$(curl -s -o /dev/null -w "%{http_code}" \
              --max-time 10 https://app.salesanchor.jp/design/ 2>/dev/null || echo "FAIL")
            if [ "$_ds_401" != "401" ]; then
              echo "❌ Design-site smoke FAIL: expected 401 without auth, got ${_ds_401}"
              exit 1
            fi
            echo "✅ Design-site: 認証なし → 401 確認"
```

（smoke②③は `DESIGN_SITE_SMOKE_CRED` Secret登録済み・htpasswdセットアップ後に有効化。§4参照）

---

## §4 htpasswd 作成方法（CC責任・deploy.yml による自動セットアップ）

**Shingoの手動操作は不要です。** deploy.yml に以下のステップを追加し、デプロイ時に自動でhtpasswdを作成します。

2ユーザー構成:
- **viewer ユーザー** (`sa-design`): Shingoが設計図書サイトを閲覧するためのアカウント
- **smoke ユーザー** (`sa-smoke`): CI/CD smoke テスト専用アカウント（Shingo非公開）

**§3に追加するdeployステップ**（`Rsync design-site to VPS` の前に挿入）:

```yaml
      - name: Setup design-site htpasswd (idempotent)
        uses: appleboy/ssh-action@v1
        env:
          VIEWER_CRED: ${{ secrets.DESIGN_SITE_VIEWER_CRED }}
          SMOKE_CRED: ${{ secrets.DESIGN_SITE_SMOKE_CRED }}
        with:
          host: ${{ secrets.VPS_HOST }}
          username: ${{ secrets.VPS_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          envs: VIEWER_CRED,SMOKE_CRED
          script: |
            set -e
            HTPASSWD=/home/ubuntu/salesanchor/nginx/htpasswd.d/design-site
            mkdir -p "$(dirname "${HTPASSWD}")"
            which htpasswd || sudo apt-get install -y apache2-utils
            touch "${HTPASSWD}"
            IFS=: read -r v_user v_pass <<< "${VIEWER_CRED}"
            printf '%s\n' "${v_pass}" | htpasswd -Bi "${HTPASSWD}" "${v_user}"
            IFS=: read -r s_user s_pass <<< "${SMOKE_CRED}"
            printf '%s\n' "${s_pass}" | htpasswd -Bi "${HTPASSWD}" "${s_user}"
            echo "htpasswd users: $(cut -d: -f1 "${HTPASSWD}" | tr '\n' ' ')"
```

**htpasswd の耐久性**: bind mount（`nginx/htpasswd.d/:/etc/nginx/htpasswd.d:ro`）のため、`docker compose up --force-recreate` を含むデプロイでもホストのファイルは消えない。

**gitignore への追加も必要です**（Stage 0 PR に含めます）:

```
# nginx/htpasswd.d/ — Basic認証ファイル（B-11: git追跡禁止）
nginx/htpasswd.d/
```

---

## §5 GitHub Secrets（CC登録済み）

以下の2つの Secrets は CC が既に登録済みです（2026-06-12）:

| Secret名 | 用途 | 状態 |
|---------|------|------|
| `DESIGN_SITE_VIEWER_CRED` | viewer ユーザーの `user:password`（htpasswd自動セットアップ用） | ✅ 登録済み |
| `DESIGN_SITE_SMOKE_CRED` | smoke ユーザーの `user:password`（smoke②③テスト用） | ✅ 登録済み |

viewer の認証情報 (`sa-design`) はShingoに別途連絡済み。

---

## §6 適用手順（GO後の作業順序）

1. **[Hikky-dev] Stage 0変更PRを作成**（nginx.conf + docker-compose.yml + deploy.yml + .gitignore）
2. **[Shingo] PRレビュー → Approve → develop マージ**
3. **[Shingo] develop → main PR → マージ → 自動デプロイ**
4. **デプロイ時: htpasswd自動セットアップ → design-site rsync → smoke①②③ 自動実行**

---

## §7 ロールバック方法

nginx.conf と docker-compose.yml の変更は `git revert` で即座に戻せます。
htpasswdファイルは手動削除（`rm nginx/htpasswd.d/design-site`）。
www/design-site/ ディレクトリはVPS上で `rm -rf www/design-site/` で削除可能。

---

**GO確認欄**: ⬜ Shingo承認（日付: ）
