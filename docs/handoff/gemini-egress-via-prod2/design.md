# design：Gemini の通信だけを prod2 経由にする

- 作成：2026-09-29（Opus 設計担当）
- 状態：設計案（方針は PO 合意済み：2026-09-29「合意」）。Architect の審査は §9 に記録。同じ AI による自己審査で、独立した第二者のレビューではない
- 事実の根拠：[recon.md](./recon.md)

## 1. 目的（KGI）

本番の LINE 抽出と翻訳が、Gemini を再び使えるようにする。Gemini 以外の通信の経路は変えない。

| KGI | 判定（○×） |
|---|---|
| 抽出が再び完了する | 反映後24時間で、新しく作られた抽出ジョブのうち API_ERROR（HTTP 400）が0件、done が1件以上 |
| 試運転も動く | 同じ期間に `extraction_shadow_runs` が1件以上 |
| Gemini 以外は経路が変わらない | 反映後の backend・celery-worker に `HTTPS_PROXY`・`HTTP_PROXY`・`ALL_PROXY` の環境変数が無い（`printenv`） |

## 2. 対象と対象外

**対象**
- prod2 に tinyproxy を置く。受け口は 127.0.0.1 だけ。中継する相手は `generativelanguage.googleapis.com:443` だけ
- prod2 から prod1 へ、`-R 172.17.0.1:18888:127.0.0.1:8888` の逆転送を張る
- 2026-09-30 の改訂：prod2 の sudo パスワードが記録（`~/.claude-access.env`）と合わず、使えなかった。そこで、上の2つは sudo を使わず、`ubuntu` ユーザーの docker コンテナとして動かす（§5-1）。既存の `monitoring-tunnel.service` は変えない
- アプリ：新 SDK は `_get_genai_client()` で中継先を渡す。旧 SDK は `grpc_proxy` 環境変数で渡す
- docker-compose.yml：backend と celery-worker に、中継先の環境変数と `extra_hosts: host-gateway` を足す
- prod2 の設定（unit と tinyproxy）の写しを、リポジトリの記録として残す

**対象外**
- 旧 SDK から新 SDK への移行（旧 SDK はサポート終了済みだが、別テーマとして扱う）
- ADR-080 と実物（トンネル方式）の食い違いの是正（PO に報告する）
- `backend/app/tasks/translation.py:235-238` の生ログの安全確認（新しいセッションで security-reviewer が行う）
- Vertex AI への切り替え

## 3. 変更前と変更後

```
変更前：prod1 のコンテナ ──(直接)──> generativelanguage.googleapis.com   ← US 判定で 400
変更後：prod1 のコンテナ ──> host-gateway(172.17.0.1):18888
          ──(prod2 から張っている既存の SSH の -R)──> prod2 127.0.0.1:8888 (tinyproxy)
          ──> generativelanguage.googleapis.com   ← JP 判定（実測 200）
```
- TLS は、コンテナと Google の間で終わる（CONNECT）。prod2 からは中身も鍵も見えない。

## 4. 代替案と選んだ理由

| 案 | 採否 | 理由 |
|---|---|---|
| A. tinyproxy と既存のトンネルに -R を足す | **採用** | 新しい外向きの入口がない。HTTP CONNECT なので、新 SDK（httpx）にも旧 SDK（gRPC）にも使える。宛先を1つに限れる |
| B. SSH の逆向き SOCKS（`-R` の宛先を省略） | 不採用 | gRPC が SOCKS に対応していないので、翻訳が救えない。新 SDK にも httpx[socks] の追加が要る |
| C. コンテナ全体に HTTPS_PROXY を設定 | 不採用 | Meta・Discord・FedEx・Google Drive まで prod2 経由になる（PO 合意の方針に反する） |
| D. Vertex AI | 保留 | 国判定を避けられるかの根拠が無い。料金も公式ページで確認できていない |
| E. Cloudflare 中継 | 不採用 | Cloudflare 経由でも同じエラーが出たという報告の方が多い |
| F. Google の訂正を待つ | 並行 | フォームは送信済み。1か月以上かかることがある |

## 5. 実装（実装カードの中身）

### 5-1. prod2（2026-09-30 改訂：sudo を使わないコンテナ方式。実行の直前に PO へ3行で報告し、GO を受ける）

**前提となる事実（prod2 で読み取って確認、2026-09-30）**
- `ubuntu` は docker グループに入っている（`id` の出力に `988(docker)`）。docker のバージョンは 29.5.2
- `/opt/salesanchor-monitoring/` の持ち主は ubuntu で、書き込める
- `secrets/tunnel-key` は ubuntu が読める。この鍵は、既存の `monitoring-tunnel.service` が prod1 に入るときに使っているもの（recon §3 の `systemctl cat`）
- 8888 番と 18888 番は、まだ使われていない
- prod1 の sshd は `GatewayPorts clientspecified`（recon §3）

**置くもの（正本はリポジトリの `monitoring/prod2/gemini-egress/`。prod2 には scp で `/opt/salesanchor-gemini-egress/` に写す）**
- `docker-compose.yml`
  - プロジェクト名は `gemini-egress`。監視スタックの compose とは別にし、監視スタックには触れない
  - 2つのサービスとも `network_mode: host`、`restart: unless-stopped`
  - `tinyproxy`：alpine に `apk add tinyproxy` を入れる自前の Dockerfile。他人が作ったイメージは使わない
  - `tunnel`：alpine に `apk add autossh openssh-client` を入れる自前の Dockerfile
    - `autossh -M 0 -N -o StrictHostKeyChecking=no -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes -i /run/secrets/tunnel-key -R 172.17.0.1:18888:127.0.0.1:8888 ubuntu@49.212.137.46`
    - 鍵は `/opt/salesanchor-monitoring/secrets/tunnel-key` を読み取り専用でマウントする
- `tinyproxy.conf`：`Port 8888`、`Listen 127.0.0.1`、`Allow 127.0.0.1`、`ConnectPort 443`、`FilterDefaultDeny Yes`、`Filter "/etc/tinyproxy/filter"`。FilterURLs は付けない（公式 docs：HTTPS では URL の絞り込みが効かない）
- `filter`：`^generativelanguage\.googleapis\.com$`
- alpine のバージョンは、実装するときに公式のリリースページで今の安定版を確かめて固定する

**手順（すべて ubuntu で行う。sudo は使わない）**
1. `scp -r monitoring/prod2/gemini-egress ubuntu@49.212.160.98:/opt/salesanchor-gemini-egress`
   - `/opt` 直下に ubuntu が書けない場合は、`/opt/salesanchor-monitoring/gemini-egress` に置く
2. `cd <置き場> && docker compose -p gemini-egress up -d --build`
3. 確かめる（§6 の V1〜V3）
- 元に戻す：`docker compose -p gemini-egress down`。既存の監視には触れていないので、戻す操作はこれだけ

**旧案（systemd の unit に -R を足し、apt で tinyproxy を入れる）をやめた理由**
- sudo のパスワードが記録と合わず、PO も分からなかった（2026-09-30）
- コンテナ方式なら、既存の監視トンネルを再起動しない。監視が途切れる心配もなくなる

### 5-2. アプリ（PR：release/gemini-egress-via-prod2）
1. `backend/app/services/gemini_extraction_svc.py` の `_get_genai_client()`（247-261行）
   - 環境変数 `GEMINI_PROXY_URL` に値があれば、`genai.Client(api_key=api_key, http_options=types.HttpOptions(client_args={"proxy": url}, async_client_args={"proxy": url}))` を返す
   - 値が無ければ、今までどおり `genai.Client(api_key=api_key)` を返す
   - 定数・関数を1つ増やすだけ。ほかの関数には触れない
2. `docker-compose.yml` の backend と celery-worker の environment に、次を足す
   - `- GEMINI_PROXY_URL=${GEMINI_PROXY_URL-http://host-gateway:18888}`
   - `- grpc_proxy=${GEMINI_GRPC_PROXY-http://host-gateway:18888}`
   - あわせて `extra_hosts: ["host-gateway:host-gateway"]` を足す（`docker-compose.exporters.yml:97-98` と同じ書き方）
   - 注：`-`（コロンなし）にするのは、`.env` に空文字を書けば、中継なしの直接接続に戻せるようにするため
3. `backend/tests/` に `_get_genai_client` のテストを足す（環境変数があるとき・ないとき）
4. prod2 用のファイル（§5-1）は `monitoring/prod2/gemini-egress/` を正本にする。README に「prod2 へは scp で写す。変えるときは、ここを直してから写し直す」と書く
- 触らないもの：`HTTPS_PROXY`・`HTTP_PROXY`・`ALL_PROXY`・`NO_PROXY` は設定しない。Meta・Discord・FedEx・Drive のコードにも触れない

### 5-3. 順番（この順を守る）
1. PR を作り、CI と Reviewer を通す（まだマージしない）
2. prod2 を設定し、V1〜V4 を確かめる
3. V1〜V4 がすべて合格したら、GO を出してマージし、デプロイする
   - GO は ADR-1003 の委任による
   - 先にデプロイすると、今動いているかもしれない翻訳まで止まるおそれがある（recon §5-4）ので、順番を逆にしない
4. V5〜V8 を確かめる

## 6. 基準と検証方法

| # | 基準 | 検証方法 |
|---|---|---|
| V1 | tinyproxy が 127.0.0.1:8888 だけで待ち受けている | prod2 で `ss -ltn \| grep 8888` |
| V2 | Gemini 以外の宛先は断られる | prod2 で `curl -x http://127.0.0.1:8888 -sI https://example.com` が 403 か接続拒否 |
| V3 | prod1 の 172.17.0.1:18888 が待ち受けていて、外からは届かない | prod1 で `ss -ltn \| grep 18888`。Mac と prod2 から `nc -zv -w5 49.212.137.46 18888` がタイムアウト |
| V4 | prod1 のコンテナから中継を通して Gemini が 200 を返す（http 形式の proxy で新 SDK が動く） | 反映前の celery-worker で、鍵を出さずに `python -c` の中で `genai.Client(..., http_options=…proxy=http://host-gateway:18888)` を使い、1回呼ぶ。今の celery-worker に extra_hosts が無ければ `http://172.17.0.1:18888` で代用する |
| V5 | 旧 SDK も中継を通る | 反映後、翻訳バッチのログ `[translation_task] batch done: ... failed=N` の N が0 |
| V6 | 抽出が戻る | 反映後24時間で、新しい抽出ジョブの API_ERROR が0件、done が1件以上（本番 DB の SELECT） |
| V7 | 試運転が動く | `extraction_shadow_runs` が1件以上 |
| V8 | Gemini 以外の経路は変わらない | backend・celery-worker で `printenv HTTPS_PROXY HTTP_PROXY ALL_PROXY` がどれも空 |

## 7. リスクと対処

| リスク | 対処 |
|---|---|
| prod2 かトンネルが止まると Gemini も止まる | コンテナは `restart: unless-stopped`、autossh は切れたらつなぎ直す。抽出の API_ERROR が続けば、今と同じ症状で気づける。専用の見張りは、次の便で抽出状態の表示を直すときに入れる |
| prod2 も US 判定に変わる | 案 D（Vertex）を検討する。V6 の見方で気づける |
| 監視トンネルと同じ鍵で、prod1 への SSH 接続が2本になる | 既存の監視トンネルには触れない。別の接続として張る。prod1 側の authorized_keys の制限（permitlisten など）で 18888 番が拒まれた場合は、V3 で分かる。そのときは止まって、設計を見直す |
| grpc_proxy が Gemini 以外の gRPC にも効く | backend で gRPC を使うのは Gemini だけ（recon §2）。gRPC を使うライブラリを増やすときは、この設計を見直す |
| prod2 の設定がリポジトリの外にあり、ずれる | §5-2 の 4 で写しを置く。見直すきっかけは、監視 VPS を変えるときの runbook |

## 8. 元に戻す方法

- アプリ：prod1 の `.env` に `GEMINI_PROXY_URL=` と `GEMINI_GRPC_PROXY=` を空で書くか、PR を revert する
- prod2：置き場で `docker compose -p gemini-egress down` を実行する（既存の監視には触れていない）
- どちらに戻しても、直接接続（今の止まった状態）に戻るだけ

## 9. 設計審査（Architect、同じ AI による自己審査）

- 判定：**APPROVE（条件つき）**
- 根拠：
  - 事実はすべて recon に根拠がある
  - 受入条件は ○× で判定できる
  - 触る範囲は 5-2 の3ファイルと記録2ファイル、それに prod2 だけ
  - 方針は PO の合意と一致している（Gemini だけ）
- 条件（満たすまで実装カードを出さない、または該当する手順に進まない）：
  1. recon §4-1 の ADR 検索の出力を貼り、この設計と食い違う ADR が無いこと
  2. tinyproxy の Filter の書式を公式 man で確かめてから、§5-1 の 3 を書く
  3. V4 が合格するまでマージしない
- 未解決（PO に報告済み、または報告する）：ADR-080 と実物の食い違い

## 10. 維持の仕組み

- 守り手：Opus 設計担当（監視 VPS を変えるときに見直す）／PO（Google の訂正が反映されたら、中継を外すかを判断する）
- 担当：監視 VPS（prod2）を変えるときは、`monitoring/prod2/` の写しと、この design の §3 を見直す
- 気づく仕組み：抽出ジョブの API_ERROR（V6 と同じ見方）
- 解除するきっかけ：Google の訂正が反映され、prod1 の `"GL"` が JP に戻った場合。中継を外すかは、そのとき PO が判断する

## 11. 外部・過去事例

- 同じ症状の報告（東京 IDC Frontier、2026-09-19〜、未解決）：recon §1
- Render/Singapore の利用者が同じエラーを報告し、数日後に直ったと書いている（2026-05-09〜17、原因は本人も不明）：https://discuss.ai.google.dev/t/getting-error-400-user-location-is-not-supported-for-the-api-use-failed-precondition/144164
- 我々への応用：Google の訂正はいつ直るか分からない。そのため「日本と判定される別の IP を通す」を本命にした。直接の実測（prod2 経由で 200）を根拠とし、外部の事例は成功の証明には使わない
