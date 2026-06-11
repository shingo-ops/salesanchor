# recon: nginx 502 再発防止 + migration TOTAL自動カウント

> 調査日: 2026-06-11（Terminal CC）。実コード調査のみ。実装なし。

## nginx backend参照の現状（file:line）

| 調査観点 | 現状（file:line） | 備考 |
|----------|-----------------|------|
| proxy_pass 形式 | `nginx/nginx.conf:150` — `proxy_pass http://backend:8000/api/;`（コンテナ名直書き） | 全9箇所で同パターン（95, 108, 128, 150, 192, 255, 268, 288, 310） |
| resolver 指令 | **なし** | Docker デフォルト DNS（127.0.0.11）に依存 |
| `set $upstream` 変数化 | **なし** | 動的再解決なし |
| nginx IP キャッシュ挙動 | nginx worker 起動時に DNS 解決しワーカー存続中は再解決しない | `nginx -s reload` = worker 再起動 = DNS 再解決 ✅ |
| Docker network | `docker-compose.yml:379` — `frontnet: {}` (driver: bridge, IPAMなし) | IP は Docker が動的割り当て |
| blue-green nginx reload | `scripts/blue-green-cutover.sh:139-141` — `docker exec nginx nginx -s reload` | CI/CD経由の backend 再起動はすべてここで網羅 |
| deploy.yml step 4b | `.github/workflows/deploy.yml:276` — "nginx reload already done inside blue-green-cutover.sh." | 明示的なコメント記載済み |
| Bootstrap SA18 path | `.github/workflows/deploy.yml:328` — `BG_HEALTH_TIMEOUT=90 bash scripts/blue-green-cutover.sh` | SA18 経由も blue-green で nginx reload 済み |

**今回の502の真因（調査結果）**:
- SA-02 Stage 4 デプロイ（04:38 JST）後、`nginx -s reload` は正常実行
- 14:38 JST ごろ backend コンテナが **CI/CD 外で再起動**（手動またはシステム要因）
- この再起動は nginx reload を伴わなかったため、旧IP（172.20.0.9）参照 → 502
- `docker inspect astro-webapp-backend-1` で現在IP `172.20.0.5` を確認 → nginx の旧IP と不一致を確認

**残存ギャップ**:
- CI/CD deploy ではすべて nginx reload 済み ✅
- **手動 `docker compose restart backend`** などの CI/CD 外再起動は非カバー ❌（これが今回の原因）
- 恒久解は案A（resolver + 変数化）= 別ADR予定

## migration TOTAL 自動カウントの現状（file:line）

| 調査観点 | 現状（file:line） | 備考 |
|----------|-----------------|------|
| TOTAL 定義 | `scripts/run_all_migrations.sh:47` — `TOTAL=130`（ハードコード） | migration 追加時に手動更新必須 |
| 実際の run_sql/run_py 件数 | `scripts/run_all_migrations.sh:47` を参照 = **130** | 現在は一致しているが手動管理 |
| TOTAL 用途 | `scripts/run_all_migrations.sh:53` — `echo ">>> [${STEP}/${TOTAL}]"` | 進捗表示のみ。不一致でも機能的影響なし |
| 自動カウント手法 | `grep -cE '^run_(sql|py)[[:space:]]' "$0"` で self-referential カウント可能 | コメント行（`#`）は対象外 |
