# Claude Code 監視アクセス Runbook (ADR-079)

Claude Code（AI エージェント）が VPS メトリクスを読み取るための
SSH アクセスと Grafana トークンの初期セットアップ・ローテーション手順書。

**対象 ADR**: ADR-079  
**所要時間（初回）**: 約 20 分  
**実施者**: しんごさん（PO）

---

## 初回セットアップ

### Step 1: ローカルで SSH 鍵ペアを生成

```bash
# Mac のターミナルで実行
ssh-keygen -t ed25519 -f ~/.ssh/salesanchor-claude -N "" -C "claude-code-reader"

# 公開鍵を確認（次の Step で使用）
cat ~/.ssh/salesanchor-claude.pub
```

### Step 2: VPS に専用ユーザーを作成

```bash
# 1. 公開鍵をコピーしておく（上記の cat 結果）

# 2. VPS に SSH（既存の鍵で）
ssh ubuntu@49.212.137.46

# 3. セットアップスクリプトを実行
bash /path/to/scripts/setup-claude-monitor-user.sh "ssh-ed25519 AAAA... claude-code-reader"

# 4. 接続テスト
exit
ssh -i ~/.ssh/salesanchor-claude claude-monitor@49.212.137.46
# → docker stats / free -h / df -h / uptime の結果が表示されれば OK

# 5. 破壊的コマンドが拒否されることを確認
ssh -i ~/.ssh/salesanchor-claude claude-monitor@49.212.137.46 'rm /etc/passwd'
# → Permission denied が返れば OK
```

### Step 3: Grafana Service Account Token を発行

1. `https://app.salesanchor.jp/grafana/` にログイン
2. 左下 **Administration → Service accounts**
3. **Add service account** → 名前: `claude-code-reader` / Role: **Viewer**
4. **Add service account token** → Token name: `claude-code-token` / Expiration: **90 days**
5. 表示されたトークン（`glsa_...`）を安全な場所に保管

### Step 4: トークンをローカルに保管

```bash
# ~/.claude-access.env に保存（リポジトリ外・Claude が参照する）
cat > ~/.claude-access.env << 'EOF'
GRAFANA_TOKEN=glsa_xxxxxxxxxxxxxxxxxxxxxxxxxx
GRAFANA_URL=https://app.salesanchor.jp/grafana
VPS_MONITOR_USER=claude-monitor
VPS_HOST=49.212.137.46
VPS_SSH_KEY=~/.ssh/salesanchor-claude
EOF
chmod 600 ~/.claude-access.env
```

### Step 5: Claude Code への接続情報登録

このステップは Claude Code が自動で行います（メモリへの保存）。

---

## Claude Code からの使用方法

### コンテナ別メモリ確認（SSH）

```bash
ssh -i ~/.ssh/salesanchor-claude claude-monitor@49.212.137.46
# → docker stats --no-stream; free -h; df -h; uptime の結果が返る
```

### Grafana PromQL クエリ

```bash
# ホスト全体のメモリ使用量
curl -s -H "Authorization: Bearer $(grep GRAFANA_TOKEN ~/.claude-access.env | cut -d= -f2)" \
  "https://app.salesanchor.jp/grafana/api/datasources/proxy/uid/prometheus/api/v1/query" \
  --data-urlencode 'query=node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes'

# コンテナ別メモリ（cAdvisor 導入後）
# query=container_memory_usage_bytes{name=~".+"}
```

---

## ローテーション（90日ごと）

### SSH 鍵のローテーション

```bash
# 1. ローカルで新しい鍵を生成
ssh-keygen -t ed25519 -f ~/.ssh/salesanchor-claude-new -N "" -C "claude-code-reader"

# 2. VPS で新しい鍵を追加（既存鍵が有効なうちに）
ssh ubuntu@49.212.137.46
bash scripts/setup-claude-monitor-user.sh "$(cat ~/.ssh/salesanchor-claude-new.pub)"

# 3. 新しい鍵で接続確認
ssh -i ~/.ssh/salesanchor-claude-new claude-monitor@49.212.137.46

# 4. 古い鍵を authorized_keys から削除
ssh ubuntu@49.212.137.46
nano /home/claude-monitor/.ssh/authorized_keys
# → 古い鍵の行を削除

# 5. ローカルの鍵を入れ替え
mv ~/.ssh/salesanchor-claude-new ~/.ssh/salesanchor-claude
mv ~/.ssh/salesanchor-claude-new.pub ~/.ssh/salesanchor-claude.pub
```

### Grafana トークンのローテーション

```bash
# 1. Grafana UI → Administration → Service accounts → claude-code-reader
# 2. 既存トークン「claude-code-token」の右端 → Delete（即時無効化）
# 3. Add service account token → 新しいトークンを発行
# 4. ~/.claude-access.env の GRAFANA_TOKEN を更新
```

### Grafana トークンの失効予定日（記録）

| 項目 | 値 |
|---|---|
| 最終再発行日 | 2026-10-10 |
| service account | `claude-code-reader`（id=2、login `sa-1-claude-code-reader`、Viewer） |
| token 名 / token_id | `claude-code-reader-202610100727` / 2 |
| 有効期間 | 7776000 秒（90 日） |
| 失効予定日 | 2027-01-08 |

次回の再発行は失効日の前（目安 2026-12-25）に行い、再発行したらこの表を更新する。トークン値・パスワード値は書かない。

確認方法（200 が返れば有効。期限切れは 401 で `api-key.expired`）:

```bash
curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $GRAFANA_TOKEN" https://app.salesanchor.jp/grafana/api/datasources
```

### API による再発行の手順（2026-10-10 実施）

1. `GET /api/serviceaccounts/search` で `claude-code-reader` の id を取得する。
2. `POST /api/serviceaccounts/:id/tokens` で新トークンを発行する（`secondsToLive` を 7776000 にする）。
3. admin の資格情報は prod2 のコンテナ（salesanchor-monitoring-grafana-1）の env から読む。値は画面に出さない。
4. 新トークンを `~/.claude-access.env` の `GRAFANA_TOKEN` に入れ、上の確認方法で 200 を確かめる。
5. admin パスワードが env とずれているときは、コンテナ内で `grafana cli admin reset-admin-password "$GF_SECURITY_ADMIN_PASSWORD"` を実行して env の値に合わせる（2026-10-10 は実行後 `after_reset_auth=200`）。

PO が `!` で実行する場合の注意: 書き込みを含む処理は、スクリプトにして短い 1 行で渡す。長い行は貼り付け時に改行が入り、リダイレクトだけが走ってファイルが 0 バイトになった（2026-10-10 の事故）。

---

## 即時無効化（インシデント発生時）

### SSH アクセスを停止

```bash
# VPS で即時実行
ssh ubuntu@49.212.137.46
nano /home/claude-monitor/.ssh/authorized_keys
# → 全行を削除して保存（空ファイルにする）

# または authorized_keys ファイルごと削除
rm /home/claude-monitor/.ssh/authorized_keys
```

### Grafana トークンを無効化

```bash
# API で即時無効化（トークン ID は Grafana UI で確認）
curl -X DELETE \
  -H "Authorization: Bearer <管理者トークン>" \
  "https://app.salesanchor.jp/grafana/api/serviceaccounts/<account_id>/tokens/<token_id>"

# または Grafana UI → Administration → Service accounts → claude-code-reader → Delete token
```

---

## 月次棚卸し確認事項（B-10 連携）

毎月第1月曜日、B-10 チェックリストに加えて以下を確認:

```bash
# VPS で実行
ssh ubuntu@49.212.137.46

# claude-monitor の authorized_keys を確認
cat /home/claude-monitor/.ssh/authorized_keys
# → 鍵が1件のみ（古い鍵が残っていないか）

# 最終ログイン日時
last claude-monitor | head -5
# → 直近90日以内にアクセスがあるか確認（なければ鍵を見直す）
```

---

## 参照ドキュメント

- ADR-079: `docs/adr/ADR-079-claude-code-monitoring-access.md`
- ADR-075: `docs/adr/ADR-075-github-secrets-only-policy.md`
- ADR-070: `docs/adr/ADR-070-grafana-monitoring-integration.md`
- B-10（月次棚卸し）: `docs/B-10_access_review_procedure.md`
- B-11（認証情報ポリシー）: `docs/B-11_credential_management_policy.md`
- B-12（オフボーディング）: `docs/B-12_offboarding_procedure.md`
