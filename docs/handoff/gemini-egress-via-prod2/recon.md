# recon：Gemini の国判定エラー（prod1 が US 判定）と prod2 経由の通り道

- 作成：2026-09-29（Opus 設計担当。調査は Sonnet 担当と PO の手元実行）
- 基準：origin/main `ed7e1f92d`（worktree 作成時点）
- 表記：【事実】根拠つき／【未確認】

## 1. 障害の事実

| 事実 | 根拠 |
|---|---|
| 2026-09-29 00:25:53 UTC から、prod1 の LINE 抽出ジョブが API_ERROR（HTTP 400）で失敗している | 本番 DB の抽出ジョブの読み取り（2026-09-29、Opus セッション） |
| prod1 のコンテナから直接 Gemini を呼ぶと `400 FAILED_PRECONDITION "User location is not supported for the API use."` | 2026-09-29 検証：celery-worker から urllib で1回呼んだ |
| 同じ鍵・同じモデル（gemini-3.1-flash-lite）・同じ本文で、prod2 経由（SOCKS）なら `HTTP 200`、応答は "OK" | 2026-09-29 検証：Mac から prod2 へ `ssh -D` を張って1回呼んだ |
| Google の判定：prod1 = `"GL":"US"`、prod2 = `"GL":"JP"`。ipinfo はどちらも JP / Osaka / AS9371 | 両サーバーで `curl -s https://www.youtube.com/` を実行（2026-09-29） |
| 両サーバーとも IPv6 の外向き通信はない（`curl -6` exit=7） | 同上 |
| さくら VPS は IP の追加・変更ができない | https://manual.sakura.ad.jp/vps/support/technical/ip-address.html |
| Google への位置訂正は、公式フォームで PO が送信済み。返事はなく、反映に1か月以上かかることがある | https://support.google.com/websearch/workflow/9308722?hl=ja（2026-09-29 送信） |
| 同じ症状が東京の別業者でも起きている（未解決） | https://discuss.ai.google.dev/t/paid-gemini-api-customer-blocked-by-incorrect-ip-geolocation-user-location-is-not-supported-from-a-tokyo-japan-datacenter-ip/183984 |

## 2. アプリ側の Gemini 呼び出し（origin/main）

| 箇所 | SDK / 通信 | 根拠 |
|---|---|---|
| 抽出：`_get_genai_client()` が `genai.Client(api_key=api_key)` を返す。http_options は渡していない | 新 SDK google-genai（httpx） | `backend/app/services/gemini_extraction_svc.py:247-261` |
| 抽出の呼び出し元 | 同上 | `backend/app/services/gemini_extraction_svc.py:408`、`:492` |
| 作品比較：同じ `_get_genai_client()` を使う | 同上 | `backend/app/services/tcg_work_comparison_svc.py:98` |
| 翻訳：`import google.generativeai as genai`、`genai.configure(api_key=...)`（transport の指定なし） | 旧 SDK google-generativeai | `backend/app/services/message_translator.py:99`、`:403` |
| 在庫解析：同上 | 旧 SDK | `backend/app/services/inventory_parser_llm.py:197`、`:253` |
| 使用中の版（prod1 celery-worker）：google-generativeai 0.8.6、google-genai 2.8.0、grpcio 1.84.0、httpx 0.28.1、requests 2.34.2 | — | PO 手元実行 prod1_read_check.sh（Opus の scratchpad にあるリポジトリ外のスクリプト、2026-09-29） |
| 旧 SDK は transport=None のとき gRPC になる（`_transport_registry` の先頭が grpc） | google-ai-generativelanguage 0.6.15 | PyPI の sdist（リポジトリ外）：google/ai/generativelanguage_v1beta/services/generative_service/transports/__init__.py と、同じパッケージの client.py にある get_transport_class |
| backend で gRPC や google.cloud を使うのは Gemini の SDK だけ | — | `git grep -n -E "grpc\|google\.cloud" origin/main -- backend` の結果が0件。requirements は `backend/requirements.txt:27`、`:29` |
| Gemini 以外の外向き HTTP：Meta・Discord・FedEx は httpx。Google Drive は requests。IMAP は imaplib | — | `backend/app/services/meta_graph.py:38`、`backend/app/services/discord_rest.py:15`、`backend/app/services/fedex_etd.py:18`、`backend/app/services/google_drive_oauth.py:291`、`backend/app/services/review_mail_notifier.py:23` |
| docker-compose.yml には HTTPS_PROXY / HTTP_PROXY / NO_PROXY が無い | — | `git grep -n PROXY origin/main -- docker-compose.yml` の結果が0件 |
| エラーの文言はログで伏せられる：HTTP コードが取れると「リクエストエラー (HTTP 400)」だけが残る | — | `backend/app/services/gemini_extraction_svc.py` の `_safe_error_message`（197行付近） |

**公式の資料**
- google-genai：プロキシは環境変数（httpx / aiohttp が `urllib.request.getproxies` を使う）か、`HttpOptions(client_args={'proxy': ...}, async_client_args={...})` で指定できる。SOCKS の場合は httpx[socks] が必要。出典：googleapis/python-genai の README（Context7 `/googleapis/python-genai`）。
  - 【未確認】README に載っている例は socks5 だけで、`http://` 形式の例はない。httpx 自体は HTTP CONNECT プロキシに対応している。
- gRPC は `grpc_proxy` → `https_proxy` → `http_proxy` の順に環境変数を読み、HTTP CONNECT で中継する。
  - 【未確認】grpc.io の該当ページは直接取得できなかった（`/docs/guides/proxy/` が 404）。本番で実際に呼んで確かめる。
- httpx が読む環境変数は `HTTP_PROXY`・`HTTPS_PROXY`・`ALL_PROXY`・`NO_PROXY` だけ（https://www.python-httpx.org/environment_variables/）。requests は `http_proxy`・`https_proxy`・`no_proxy`・`all_proxy`（https://requests.readthedocs.io/en/latest/user/advanced/）。どちらも `grpc_proxy` は読まない。

## 3. サーバー側

| 事実 | 根拠 |
|---|---|
| prod2 の `monitoring-tunnel.service`（`/etc/systemd/system/`）が、autossh で prod2 から prod1 へ常時つないでいる。`-L 0.0.0.0:19100/19187/19113/19121` と `-R 0.0.0.0:13100:127.0.0.1:3100`。`Restart=always`、`RestartSec=10` | prod2 で `systemctl cat monitoring-tunnel.service` |
| この unit はリポジトリに無い（`autossh`・`tunnel-key`・`ExitOnForwardFailure` で grep すると0件） | `git grep` origin/main |
| prod1 の promtail は `http://host-gateway:13100` で Loki に送っている | `docker-compose.exporters.yml:85-98` |
| prod1 の `host-gateway` は `172.17.0.1`（docker0）に解決される | PO 手元実行 prod1_read_check2.sh（リポジトリ外）：promtail の中で `getent hosts host-gateway` |
| prod1 の sshd は `GatewayPorts clientspecified` なので、`-R` の待ち受けアドレスを指定できる | 同上：sshd の設定ファイル |
| prod1 の 13100 は `0.0.0.0` で待ち受けているが、Mac からも prod2 からも接続がタイムアウトする。つまり外から届かない | 同上：`ss -ltn`、`nc -zv -w 5`（2026-09-29） |
| prod1・prod2 とも `sudo` にはパスワードが要るため、ufw の状態は読めない。さくらのパケットフィルタも画面側の設定なので未確認 | 同上 |
| prod2：Ubuntu 24.04.4、OpenSSH 9.6p1、使えるメモリ 2,581MB。tinyproxy 1.11.1 と squid 6.14 は apt で入れられるが、まだ入っていない。8888 番・3128 番の待ち受けはない | prod2 で `cat /etc/os-release`、`ssh -V`、`free -m`、`apt-cache policy`、`ss -ltnp` |
| prod1 から prod2 の 22 番に届く | PO 手元実行 prod1_read_check.sh（リポジトリ外） |

## 4. 既存の ADR（検索した結果）

- 検索したキーワード：proxy、egress、Gemini、tunnel、監視VPS。対象は `docs/adr/` と `docs/adr/FEATURE-INDEX.md`。
- 結果は、コミットする担当が `git grep` の出力を §4-1 に貼る。
- 関係する ADR：
  - ADR-080（監視 VPS の分離）：「exporter ポートは管理室 VPS の IP からのみ許可」とあり、トンネルの記述はない（`git grep -n -i tunnel` で0件）。実物はトンネルなので、**文書と実物が食い違っている**。今回の変更範囲の外として、PO に報告する。
  - ADR-1003（GO の委任）。
  - ADR-136（危険な PR の GO）。

### 4-1. ADR 検索の出力（コミットする担当が貼る）

実行コマンドと出力（2026-09-29、実装担当実行）：

```
$ git grep -n -i -E "proxy|egress|tinyproxy|grpc_proxy|monitoring-tunnel|autossh" -- docs/adr/
（Opus 注：ここにあった ADR-018 の2行と ADR-026 の5行は、「regression」の文字列が「egress」に一致しただけで、今回とは関係がないため省略した。行番号は ADR-018:66-67、ADR-026:54,63,81,91,117）
docs/adr/ADR-081-monitoring-vps-final-operational-design.md:1:# ADR-081: 監視VPS分離の最終運用設計 — パケットフィルタ、UFW、proxy 経路、backend worker 数の固定
docs/adr/ADR-081-monitoring-vps-final-operational-design.md:13:監視スタックの管理室VPS分離を継続し、**外部公開の入口制御・VPS内 firewall・nginx proxy・backend worker 数**をひとつの最終運用設計として固定する。
docs/adr/ADR-081-monitoring-vps-final-operational-design.md:25:| nginx | `/grafana` / `/monitor` 系の proxy を維持 |
docs/adr/ADR-081-monitoring-vps-final-operational-design.md:79:### B. nginx の proxy は監視VPSの疎通確認後にのみ本番固定とする
docs/adr/ADR-081-monitoring-vps-final-operational-design.md:81:`/grafana` や `/monitor` 系の reverse proxy は、監視VPS への direct access が確認できてから final とする。
docs/adr/ADR-081-monitoring-vps-final-operational-design.md:82:途中状態で proxy だけ切り替えると、画面は表示されても内部 API が `504` になる。
docs/adr/ADR-081-monitoring-vps-final-operational-design.md:103:- `app.salesanchor.jp/grafana/` の proxy を監視VPSへ固定する
docs/adr/ADR-130-nginx-reload-policy.md:24:- **案A（resolver + 変数化）は別ADRで後日実施**。9箇所の proxy_pass 書き換えと SSE 動作確認が必要なため今回は見送る
docs/adr/ADR-133-nginx-resolver-proxy-pass-variable.md:1:# ADR-133: nginx resolver + proxy_pass 変数化による IP 固着 502 恒久解
docs/adr/ADR-133-nginx-resolver-proxy-pass-variable.md:41:3. backend 向け **9 箇所**・frontend 向け **1 箇所**、合計 **10 箇所**の `proxy_pass` を
docs/adr/ADR-133-nginx-resolver-proxy-pass-variable.md:46:| # | file:line | location | 変換前 proxy_pass | 変換後 |
docs/adr/ADR-133-nginx-resolver-proxy-pass-variable.md:61:nginx は `proxy_pass` に変数を含む場合、location prefix → URI suffix の置換を行わず `$request_uri` をそのまま転送する。全 10 箇所で `location prefix == proxy_pass URI suffix` が成立しているため、URI 部を除去しても転送先パスは等価（recon.md §1-A 参照）。
docs/adr/ADR-133-nginx-resolver-proxy-pass-variable.md:67:- 外部 IP 直指定の proxy_pass（`49.212.160.98:3000` grafana / `49.212.160.98:3001` status/monitor）: IP は DNS 解決しないため本件の問題を持たない。変更なし。
docs/adr/ADR-133-nginx-resolver-proxy-pass-variable.md:68:- `jarvis-claude.uk` / `salesanchor.jp` / `monitor.salesanchor.jp` サーバーブロック: proxy_pass なし or 外部 IP のみ。変更なし。
docs/adr/ADR-133-nginx-resolver-proxy-pass-variable.md:87:`resolver 127.0.0.11 valid=5s` + `set $var hostname; proxy_pass http://$var;` は Docker ブリッジネットワーク上での nginx 動的 DNS 解決の業界標準手法。nginx-plus の `resolve` フラグ相当の効果を OSS で実現する唯一の方法として広く採用されている。
docs/adr/ADR-137-nginx-config-deploy-reliability.md:31:nginx は起動時に `proxy_pass http://backend:8000` を DNS 解決し、
docs/adr/ADR-137-nginx-config-deploy-reliability.md:38:全 proxy_pass（10 箇所）が `$backend` / `$frontend` 変数経由。literal `http://backend:8000` なし。
docs/adr/ADR-137-nginx-config-deploy-reliability.md:61:- 全 proxy_pass が `$backend` / `$frontend` 変数経由（10 箇所）
docs/adr/ADR-137-nginx-config-deploy-reliability.md:63:  `nginx/nginx.conf:292-309`, `nginx/nginx.conf:312-329`）は `proxy_buffering off` 維持済み
docs/adr/ADR-137-nginx-config-deploy-reliability.md:102:- [x] 全 proxy_pass が `$backend` / `$frontend` 変数経由（literal なし・10 箇所）
docs/adr/ADR-137-nginx-config-deploy-reliability.md:103:- [x] SSE 4 location の `proxy_buffering off` 維持済み
docs/adr/FEATURE-INDEX.md:50:| 502 / resolver / backend IP / proxy_pass | **ADR-137** ／ ADR-133 | PR-B 相当は ADR-137 で解消済みとして統合記録 |
docs/adr/README.md:91:| [ADR-081](./ADR-081-monitoring-vps-final-operational-design.md) | ADR-081: 監視VPS分離の最終運用設計 — パケットフィルタ、UFW、proxy 経路、backend worker 数の固定 | Accepted | — | — |
docs/adr/README.md:148:| [ADR-133](./ADR-133-nginx-resolver-proxy-pass-variable.md) | ADR-133: nginx resolver + proxy_pass 変数化による IP 固着 502 恒久解 | Accepted | — | 2026-06-11 |

$ git grep -n -i -E "gemini" -- docs/adr/FEATURE-INDEX.md
（該当なし。exit code 1）
```

判定：ヒットした「proxy」はすべて nginx の reverse proxy（Grafana/監視画面表示、`/backend` `/frontend` へのルーティング、502対策）に関するもので、アプリのアウトバウンド通信（Gemini 等への egress）とは別の話。`tinyproxy`・`grpc_proxy`・`monitoring-tunnel`・`autossh`・`egress` はヒット0件。この設計（Gemini の通信だけを prod2 の tinyproxy 経由にする）と食い違う ADR は見つからなかった。

ADR-081 は「監視VPS `49.212.160.98`」についての ADR で、recon §3 の `monitoring-tunnel.service`（prod2→prod1 の autossh、`-R 0.0.0.0:13100:127.0.0.1:3100` 等）はリポジトリの ADR に記述がない（recon §4 に既出の「ADR-080 と実物の食い違い」）。この食い違いは対象外として PO に報告済み（design.md §2, §9）。今回追加で見つかった別の食い違いはない。

## 5. 未確認（実装の途中で確かめる）

1. google-genai 2.8.0 に `client_args={'proxy': 'http://…'}` を渡したとき、HTTP CONNECT プロキシで動くか → 本番の手前で確かめる（design §6 の V4）
2. gRPC の `grpc_proxy` が本番で効くか → V5
3. tinyproxy 1.11 の設定で、CONNECT の宛先を1つのホストに限れるか（Filter の書き方）→ 公式 man で確かめてから設定する（design §5-1）
4. 翻訳（旧 SDK）が今止まっているか → `docker compose logs` の `[translation_task] batch done: ... failed=N` で確かめる
