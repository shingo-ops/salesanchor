<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。 -->
# Phase 2 recon — realtime-standard（即時反映をアプリ全体の標準にする）

**基準**: origin/main 0b9d970c3（worktree release-realtime-standard-design）  
**日付**: 2026-10-15  
**担当**: 調査 Sonnet（生出力 /tmp/CC報告ファイル/realtime-standard-recon/）、確認と整理 Opus

## 0. 既存 ADR の検索

- `git grep -il "SSE\|リアルタイム\|realtime\|Server-Sent" docs/adr/` の結果（生出力 F3.txt）
  - 即時通知そのものを決めた ADR は無い。
  - SSE に触れているのは、中継の設定に関する次の2件だけ。
    - `docs/adr/ADR-133-nginx-resolver-proxy-pass-variable.md`:49-56（SSE の location の proxy_pass を変数化）
    - `docs/adr/ADR-137-nginx-config-deploy-reliability.md`:62,103（SSE の location 4か所で proxy_buffering off を保つ）
- docs/adr/FEATURE-INDEX.md には SSE・即時・リアルタイムの行が無い。
- ワーカー数1の根拠: `backend/Dockerfile`:35-37（ADR-081 C項）。

## 1. 既存の即時通知（受信箱・リード）

- `backend/app/services/sse_pubsub.py`
  - Redis の DB3 を使う（:20-21）。
  - チャンネルは inbox:{tenant_id} と leads:{tenant_id} の2つだけ（:61-66）。
  - 送るのは固定の文字列 "update" だけ（:74）。
  - publish のたびに Redis へ接続し直している（from_url → publish → aclose、:72-76）。
  - 購読も、画面とつないだ通り道1本ごとに Redis へ接続している（:85）。
  - 接続数の上限は会社×種類ごとに10（:23）。数はプロセスの中の dict で数えている（:25）。
  - Redis が落ちてもログを残すだけで、処理は止めない（:77-80）。
- 通り道（SSE）を返すところ
  - `backend/app/routers/leads.py`:2871-2926
  - `backend/app/routers/meta_inbox.py`:1034-1090
  - どちらも30秒ごとに生存の合図（ハートビート）を送る（leads.py:2868）。上限を超えたら 503 を返す（leads.py:2890-2894）。
- 合図（publish）を送っているのは次の5か所だけ。生出力 A2.txt。
  - webhook.py:915
  - leads.py:482, 702, 765
  - tasks/translation.py:96
  - discord_gateway/reaction_writer.py:199
- 画面側（`frontend/src/hooks/useSSE.ts`）
  - fetch でつなぎ、Firebase の ID トークンを Authorization に付ける（:33-52）。
  - update を受けたら onUpdate を呼ぶ（:81-83）。
  - 切れたら 2秒→4秒→…最大300秒の間隔でつなぎ直す（:12-14, 94-101）。
- 画面側の呼び出し元は次の4か所で、フックを1回呼ぶごとに通り道が1本開く。
  - DesktopShell.tsx:136
  - MobileShell.tsx:107
  - pages/inbox/useInboxState.ts:498
  - pages/leads/LeadsPage.tsx:184

## 2. 基盤

- uvicorn はワーカー1つで動く（`backend/Dockerfile`:37）。プロセスの中で接続数を数える今の作りは、ワーカーが1つだから成り立っている。
- `nginx/nginx.conf`
  - app 側の SSE 用 location は :112, :132、api 側は :308, :328。
  - これらは proxy_buffering off、proxy_read_timeout 3600s。
  - それ以外の /api/ は read_timeout 120s（:151-163）。
  - app 側は `http2 on`（:70）。HTTP/2 は1本の接続の上で複数の通信を流せるので、ブラウザの「同じ相手には同時6本まで」という制限は受けない。
- Redis は `docker-compose.yml`:412-426 の redis:7-alpine（maxmemory 256mb）。DB0 はアプリ、DB1・DB2 は Celery、DB3 は SSE が使う。
- Cloudflare: docs/B-06_cloudflare_setup.md にプロキシ ON の手順が書いてある。【未確認】本番が実際に Cloudflare を経由しているかは、実機で確かめていない。ただし既存の SSE 2本は本番で動いている。

## 3. データを書き換える入口

- backend/app 配下で書き込みの API（post/put/patch/delete）を定義している箇所は360件、routers は99ファイル（生出力 C2-write-decorators-raw.txt、C2-write-counts-all.txt）。
- 裏の処理で書き換える入口は43行（生出力 C6）。主なものは次のとおり。
  - 解析のやり直し（tasks/tcg_extraction.py:696-720）
  - 自動配信（tasks/tcg_extraction.py:628-636, 688）
  - LINE 取り込み（services/tcg_line_import_svc.py:761）
- 書き込みを横断して見ている既存のミドルウェアがある。`backend/app/middleware/audit.py`:106-139 は、POST/PUT/PATCH/DELETE で状態コードが500未満のものを記録している。
- request.state に会社 ID を入れている箇所は無い（grep 0件）。会社 ID は依存関数 get_current_tenant（`backend/app/auth/dependencies.py`:242）が決める。
- 要確認一覧の API（`backend/app/routers/tcg_analysis_review.py`:116-135）は super admin 専用で、会社をまたぐ共用データ（public スキーマ）を返す。

## 4. 画面

- ルーティングは `frontend/src/App.tsx` で、Route は107行。画面ファイルは *Page.tsx と *Panel.tsx を合わせて118（生出力 D1-pages.txt）。
- データの取得は `frontend/src/lib/api.ts`:194-207 の api.get などだけを使っている。react-query・swr は使っていない。api.get を使うファイルは114ある。
- 一定間隔で読み直す（ポーリング）作りが別にある。
  - useImportWorkflow.ts:61（5秒ごと）
  - GoogleCalendarStatusBar.tsx:86（30秒ごと）
  - 受信箱（useInboxState.ts:500 付近）
- 要確認ページの読み直し（`frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx`:67-110）
  - reloadKey だけが変わったときは表を消さずに取り直す（:82）。
  - 古い結果は捨てる（:78, :107-109）。

## 5. 速度の基準

- `docs/handoff/review-speed/design.md`:6
  - 要確認タブの最初の20件を出す SQL の合計を、本番で3.0秒以下にする（変更前は7.7〜7.9秒）。
  - 全500件は5.35秒から4.2秒になった（:53）。
- 要確認一覧の読み直しは1回数秒かかる重い処理である。合図のたびに読み直すと、サーバーに負担がかかる。

## 6. 試験

- `backend/tests/test_sse_pubsub.py`: 5本。
- SSE の通り道そのものの試験と、useSSE の試験は無い。
- DesktopShell と MobileShell の試験は useSSE をモックで止めている。
