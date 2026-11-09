# design: 本番の画面点検を配備のたびに自動で回し、在庫表・リードの詳細・予定表も見る（2026-11-08）

- 状態: 設計案（Claude Opus 作成）。PO の選択「1. この進め方で設計を始める」（2026-11-07）と、同日の委任「PRマージ、デプロイまで完走させてくれ」に基づく。
- recon: `docs/handoff/prod-ui-check-after-deploy/recon.md`（以下 recon §n）
- 関連 ADR: ADR-1051（改訂する）、ADR-1053（改訂する）、ADR-1065（CSP の注意。recon §0）、ADR-136（deploy.yml は触らない）

## 1. 目的（PO の言葉）

「事務的、定常作業は任せたい」。配備のあとに画面が壊れていないかを、人も AI も手で確かめなくてよい状態にする。ログイン情報は今どおり GitHub にだけ置く（ADR-1051）。

## 2. 成功条件（KGI・KPI）

KGI: main への配備が成功するたびに、本番の画面点検が人の操作なしで動き、全部の点検が合格する。落ちたときだけ Discord に知らせが来る。

| # | 基準 | 検証方法 | ○× |
|---|---|---|---|
| K1 | 配備（Deploy to VPS）が成功して終わると、prod-ui-check が `workflow_run` で自動で始まる | 本 PR の合流後の配備の後、`gh run list --workflow prod-ui-check.yml` に event=`workflow_run` の実行が 1 件以上ある | 有れば○ |
| K2 | その自動実行で S1〜S8・S10〜S12 が全部合格（S9 は飛ばし） | その実行の記録の「本番の画面点検を実行」の段で failed 0。S10・S11・S12 は passed（skipped は×） | 全部合格で○ |
| K3 | ダッシュボードの点検（S3）が合格する（字形の CSP の誤りが消える） | K2 と同じ実行で S3 passed | ○× |
| K4 | 配備の後の実行では速さの記録の段が動かない | その実行で「画面の速さを記録（判定なし）」が skipped | ○× |
| K5 | 本番の応答の CSP に `font-src 'self' data:` が入っている | `curl -sI https://app.salesanchor.jp/ ｜ grep -i content-security-policy` | 入っていれば○ |
| K6 | 配備が失敗したときは点検を動かさない | job の `if:` の式を審査で確認（わざと配備を落とす試験はしない） | 式が §4-2 のとおりで○ |
| K7 | 毎朝の実行（schedule）と手動実行は今までどおり（速さの記録も含む） | 合流の翌朝 22:00Z の実行で、点検の段と速さの記録の段が両方動く | ○× |

## 3. 対象と対象外

- 対象（3 ファイル＋文書）
  - `nginx/nginx.conf:96`（app.salesanchor.jp の CSP に `font-src 'self' data:` を足す）
  - `.github/workflows/prod-ui-check.yml`（配備の後に動く入口・速さの記録は毎朝だけ・知らせに「いつの点検か」）
  - `tests/prod-check/prod-ui.spec.ts`（S10 在庫表・S11 リードの詳細・S12 予定表を足す）
  - `docs/adr/ADR-1051-prod-ui-black-box-check.md`・`docs/adr/ADR-1053-prod-page-speed-record.md` の改訂、`docs/adr/README.md` の作り直し（`node scripts/generate-adr-index.js`）
- 対象外（触らない）
  - `.github/workflows/deploy.yml`（危険パス。ADR-136）、`.github/workflows/workflow-lint.yml`
  - `tests/prod-check/fixtures.ts`・`tests/prod-check/login.ts`・`tests/prod-check/settle.ts`・`tests/prod-check/page-speed.spec.ts`・`tests/prod-check/page-speed.config.ts`・`tests/prod-check/page-speed-targets.ts`
  - S4 の 1 回目の 20 秒切れ（recon §5。2 回目で合格している。別件）
  - `nginx/nginx.conf` の他の CSP（jarvis-claude.uk・`/grafana/`・api.salesanchor.jp）
  - `frontend/src/App.tsx:63` の SchedulePage を遅延読み込みにすること（字形の読み込みは予定表を開けば結局起きるので、CSP の直しが要る。読み込みの速さの話は別件）
  - 秒数の合格ライン（ADR-1053 D1）・403 の画面の測り方（ADR-1053 D2）

## 4. 変更の中身（実装役は書いてあるとおりに変える）

### 4-1. `nginx/nginx.conf:96`

変更前:
```
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; connect-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:" always;
```
変更後:
```
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; connect-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:" always;
```
- 1 行の右端に `; font-src 'self' data:` を足すだけ。他の行は変えない。
- 理由: FullCalendar が読み込み時に差し込む `fcicons` の字形は `data:` で来る（recon §2）。`/grafana/` の CSP（`nginx/nginx.conf:320`）と同じ書き方にそろえる。
- 反映: 配備が `nginx/**` の変更を見て、`nginx -t` を通してから作り直す。通らなければ前の設定に自動で戻す（`.github/workflows/deploy.yml:516-553`、recon §3）。

### 4-2. `.github/workflows/prod-ui-check.yml`

(1) `on:` に足す（schedule・workflow_dispatch はそのまま）:
```yaml
  # 配備が成功して終わったら点検する（ADR-1051 改訂 2026-11-08）。deploy.yml は変えない
  workflow_run:
    workflows: ["Deploy to VPS"]
    types: [completed]
    branches: [main]
```
(2) `jobs.check` に足す（`runs-on` の前の行）:
```yaml
    # 配備が失敗・取り消しで終わったときは点検しない
    if: github.event_name != 'workflow_run' || github.event.workflow_run.conclusion == 'success'
```
(3) 「画面の速さを記録（判定なし）」の段の `if:` を変える:
- 変更前: `if: always() && steps.gate.outputs.skip != 'true'`
- 変更後: `if: always() && steps.gate.outputs.skip != 'true' && github.event_name != 'workflow_run'`
- 理由: 速さの記録は最大 46 分。配備のたびに回さず、毎朝と手動だけにする（K4・K7）。

(4) 「不合格を Discord に知らせる」の段で、いつの点検かを文に入れる:
- `env:` に `EVENT_NAME: ${{ github.event_name }}` を足す。
- python の中で `kind = {"workflow_run": "配備の後", "schedule": "毎朝", "workflow_dispatch": "手動"}.get(os.environ.get("EVENT_NAME", ""), "")` を作る。
- 文を `"🚨 本番の画面点検（%s）が不合格: %s。%s" % (kind, label, RUN_URL)` にする。kind が空なら `（）` を出さず今の文のまま。
- 合格は今どおり知らせない（ADR-1051）。

(5) ファイル先頭のコメントに、配備の後にも動くことを 1 行書く。

- 実装の前に Context7 で GitHub Actions の `workflow_run` を確かめる（recon §3 の 4 点）。食い違えば実装せず止まって報告する。
- `workflow_dispatch` の入力 `force_fail` は、`workflow_run` のときは空になる。今の参照 `PROD_CHECK_FORCE_FAIL: ${{ inputs.force_fail && '1' || '' }}`（`.github/workflows/prod-ui-check.yml:107`）は空なら `''` になり、S9 は足されない（`tests/prod-check/prod-ui.spec.ts:134-135`）。変えない。
- 配備中の待ち（`.github/workflows/prod-ui-check.yml:30-53`）・concurrency・timeout・permissions は変えない。

### 4-3. `tests/prod-check/prod-ui.spec.ts`

- 先頭のコメント `S1〜S8` を `S1〜S12（S9 は通知の試験）` に変える。
- 定数を足す（`COMPANY_DETAIL_API` の下）:
```ts
const INVENTORY_API = /^\/api\/v1\/inventory$/;
const LEAD_DETAIL_API = /^\/api\/v1\/leads\/\d+$/;
const CALENDAR_EVENTS_API = /^\/api\/v1\/calendar\/events$/;
```
- S8 の後（S9 の `describe` より前）に 3 つ足す。押す・入力する操作はしない（開くだけ）:
```ts
  test("S10 在庫表が開く", async ({ authedPage: page }) => {
    const inv = apiOk(page, INVENTORY_API);
    await page.goto("/inventory");
    expect((await inv).status(), "在庫表の API の応答").toBeLessThan(400);
    await expect(page.locator("main")).toBeVisible();
    await expect(page.locator("main [data-testid=inventory-loading]")).toBeHidden();
    await expect(page.locator(NO_ERROR_BANNER)).toHaveCount(0);
    await expect(page.locator(".error-message")).toHaveCount(0);
  });

  test("S11 リードの詳細が開く", async ({ authedPage: page }) => {
    const list = apiOk(page, LEADS_API);
    await page.goto("/crm/leads");
    const listRes = await list;
    expect(listRes.status(), "リード一覧の API の応答").toBeLessThan(400);
    const rows = (await listRes.json()) as Array<{ id: number }>;
    test.skip(!Array.isArray(rows) || rows.length === 0, "リード 0 件");
    const detail = apiOk(page, LEAD_DETAIL_API);
    await page.goto(`/crm/leads/${rows[0].id}/edit`);
    expect((await detail).status(), "リード詳細の API の応答").toBeLessThan(400);
    await expect(page.locator("main")).toBeVisible();
    await expect(page.locator("main .sa-loading-block")).toHaveCount(0);
    await expect(page.locator(NO_ERROR_BANNER)).toHaveCount(0);
    await expect(page.locator(".error-message")).toHaveCount(0);
  });

  test("S12 予定表が開きエラーが出ない", async ({ authedPage: page }) => {
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });
    const events = apiOk(page, CALENDAR_EVENTS_API);
    await page.goto("/schedule");
    expect((await events).status(), "予定の API の応答").toBeLessThan(400);
    await expect(page.locator("main .comp-calendar")).toBeVisible();
    await expect(page.locator("main .schedule-loading")).toHaveCount(0);
    await expect(page.locator("main .schedule-error")).toHaveCount(0);
    await page.waitForTimeout(5_000);
    expect(errors, `console.error が ${errors.length} 件`).toHaveLength(0);
  });
```
- 実装の前に実物で確かめること（違えば止まって報告。推測で直さない）:
  - 予定表の目印は金型 CalendarView の外枠の class `comp-calendar`（`frontend/src/components/CalendarView.tsx:159-160,232`。FullCalendar の名前は金型の外に出さない ADR-1065 に合わせる）。SchedulePage の中にあることを実物で確かめる。
  - `GET /api/v1/leads` の返事が配列であること（`backend/app/routers/leads.py:214-217` の `list[LeadResponse]`）。
  - InventoryPage・LeadEditPage・SchedulePage が開いただけで GET 以外を送らないこと。
  - エラーの出方は画面ごとに違う（審査 2026-11-08 の指摘。生出力 `/tmp/CC報告ファイル/recon-produi-15.txt`）。在庫表は `.error-message`（`frontend/src/pages/inventory/InventoryPage.tsx:549`）、リードの詳細も `.error-message`（`frontend/src/pages/leads/LeadEditPage.tsx:147`）。S4 と同じく `.error-banner` と `.error-message` の両方が 0 件であることを見る。予定表は読み込み中が `.schedule-loading`（`frontend/src/pages/schedule/SchedulePageImpl.tsx:876`）、失敗が `.schedule-error`（`frontend/src/pages/schedule/SchedulePageImpl.tsx:1525`）なので、この 2 つが 0 件であることを見る。
  - 在庫表の読み込み中の表示は `LoadingBlock` ではなく、いつも置いてある `data-testid="inventory-loading"` の箱（`frontend/src/pages/inventory/InventoryPage.tsx:632-640`）。読み込み中だけ `visibility: visible`、終わると `hidden`。数は常に 1 なので、S10 は件数でなく `toBeHidden()` で読み込みの終わりを見る（審査 2 回目の指摘）。リードの詳細は `LoadingBlock`（class `sa-loading-block`、`frontend/src/components/loading/LoadingBlock.tsx:18`・`frontend/src/pages/leads/LeadEditPage.tsx:149`）なので S11 は件数 0 で見る。
  - 予定表は開くと `GET /api/v1/shifts` も呼ぶ（`frontend/src/pages/schedule/SchedulePageImpl.tsx:961`）。`shifts.view` が要る（`backend/app/routers/shifts.py:55-56`）。点検用の人の役割「点検用（見るだけ）」は `shifts.view` を持つ（`/tmp/CC報告ファイル/checker-perms.txt:2`、本番の読み取り 2026-11-07）。403 の console.error で S12 が落ちることは無い。
  - リードの番号は失敗の文に出さない（公開リポジトリの実行記録に残るため。ADR-1053 と同じ考え）。上のコードは道すじの形と状態の番号だけを出す。

## 5. 選ばなかった案

| 案 | 選ばなかった理由 |
|---|---|
| deploy.yml の最後に「prod-ui-check を起動する」段を足す | deploy.yml は危険パス（ADR-136）。`workflow_run` なら deploy.yml を変えずに同じことができる |
| 点検用のログイン情報を Mac に置き、手元の確かめ役が開く | ADR-1051 が認証情報を GitHub secrets だけに置くと決めている。置き場所が増えると漏れる道が増える |
| CSP を直さず、S3 で字形の誤りだけを数えないようにする | 予定表の矢印などの字形が本番で出ないまま隠れる。直すべき誤りを点検から外すことになる |
| SchedulePage を遅延読み込みにして `/` では字形を読まない | 予定表を開けば同じ誤りが出る。CSP の直しは結局要る（§3 対象外） |

## 6. 影響とリスク

| リスク | 対処 |
|---|---|
| CSP を緩めすぎる | 足すのは字形の `self` と `data:` だけ。字形は命令を実行しない。`/grafana/` で同じ設定を 2026-05 から使っている |
| nginx の設定の誤りで画面が全部止まる | 配備が `nginx -t` を通してから作り直し、だめなら自動で前に戻す（deploy.yml:516-553）。K5 で応答の頭書きを確かめる |
| 配備のたびにログインが 1 回増え、ログインの絞り（10r/m・burst 5、ADR-1051 Why）に当たる | 1 回の点検でログインは 1 回。配備が続いても concurrency で点検は 1 本ずつ。絞りは送り元ごとで、GitHub の機械とお客さんは別 |
| 配備のたびに知らせが鳴りすぎる | 合格は知らせない。落ちたときだけ。今まで毎朝落ちていた S3 は本件で直る |
| 配備の直後はまだ切替の途中で落ちる | `workflow_run` は配備の仕事が終わってから動く。配備は切替と確認を終えてから終わる（deploy.yml の blue-green と nginx の確認）。それでも落ちた場合は retries 1 で 1 回だけ試し直す |
| `workflow_run` で動くとき、取り出す版（GITHUB_SHA）は main の最後の commit で、配備した commit と違うことがある（GitHub 公式資料 events-that-trigger-workflows の表） | 点検は本番の URL を外から開くだけで、取り出した版は点検の台本にしか使わない。続けて合流があれば、その配備の後にもう一度点検が動く |
| 文書だけの合流でも配備が動き、点検も動く | GitHub の公開リポジトリの機械で、費用は 0。1 回 5〜6 分。困るほど多ければ、件数を数えてから絞り方を決める（勝手に絞らない） |

戻し方: 本 PR を revert する PR を出して合流する（nginx は配備が前の設定へ作り直す。点検の入口は消える）。

## 7. 維持の仕組み

- 守り手: `.github/workflows/prod-ui-check.yml`（配備の後と毎朝の実行）・Claude Opus（週次の保守で失敗件数を見る）

- 点検が動いているかは、GitHub の実行一覧の event 列で `workflow_run` と `schedule` の両方の直近の成功を見る（ADR-1051「守り方」に足す）。
- 新しい画面の点検を足すときは `tests/prod-check/prod-ui.spec.ts` の S 番号を続けて足す。開くだけ・書き込まない・番号を文に出さない、の 3 つを守る。
- 週次の保守（agent-console 定期実行）で、直近 7 日の prod-ui-check の失敗件数を見る。0 でなければ原因を調べる。

## 8. 外部・過去事例の参照と我々への応用

- 配備の後に画面の自動点検を回す形（post-deploy smoke test）は一般的な作り方。GitHub の公式資料は `workflow_run` を「別の仕事の完了で動かす」入口として説明している（実装時に Context7 で版と書き方を確かめる）。
- 数値で効果を示した直接の事例は使わない。本件の成否は §2 の K1〜K7 の実測で判断する。

## 9. 手順（担当）

1. 設計の審査（クラウド）。REVISE なら直して再審査。
2. 実装（クラウドの Sonnet）。§4 のとおり。ADR 2 本の改訂は Opus が設計と一緒に済ませた（実装役は触らない）。CI を緑にする。
3. マージ前の審査役（reviewer・opus）が最新の HEAD で APPROVE。
4. GO 記録（PO の委任に基づく Claude Opus 発行）→ 合流 → 配備。
5. K1〜K6 を配備の後の自動実行で確かめる。K7 は翌朝の実行で確かめる。

## 10. 未決事項

- なし（PO の判断が要る点は無い）。実装時の確かめ（§4-2・§4-3 の「止まって報告」）で食い違いが出たら止める。
- K7 の判定は §11 の時刻の扱いで行う。別件 1・2 を直すかは、§11 のとおり後続で決める。

## 11. 合流後の結果と、見つかった別件（2026-11-09 追記・Opus）

### K1〜K7 の結果

| # | 結果 | 根拠 |
|---|---|---|
| K1 | ○ | 合流（2026-11-09 01:21:44Z）の後、`gh run list --workflow prod-ui-check.yml` に event=`workflow_run` の実行が 6 件（成功 4・取り消し 2）。取り消しは下の別件 3 |
| K2 | ○ | 01:34:42Z 開始の `workflow_run` の実行で S1〜S8・S10〜S12 の 11 件が passed・failed 0。その後の 3 件（02:23Z・02:44Z・03:22Z 開始）も success |
| K3 | ○ | K2 と同じ実行で S3 passed |
| K4 | ○ | 同じ実行で速さの記録の段が skipped（`if:` に `github.event_name != 'workflow_run'`。prod-ui-check.yml:158） |
| K5 | ○ | `curl -sI https://app.salesanchor.jp/` の応答の CSP に `font-src 'self' data:`（2026-11-09 Opus 実測） |
| K6 | ○ | job の `if:` が `github.event_name != 'workflow_run' \|\| github.event.workflow_run.conclusion == 'success'`（prod-ui-check.yml:33）。合流前の審査で確認済み |
| K7 | 未判定 | 合流の翌朝の schedule の実行を待つ。cron は `0 22 * * *`（prod-ui-check.yml:9）だが、直近 2 回の schedule の実行は 01:00Z（11/8）と 01:21Z（11/9）に始まっている。GitHub の schedule は遅れて始まることがあるので、判定は「22:00Z 以後で最初の schedule の実行」で行う |

### 別件 1: nginx の作り直しの間、本番に約 17 秒つながらない

- 観測: #5280 の配備の記録（Deploy to VPS・「Recreate nginx」の段）で、`Container astro-webapp-nginx-1 Recreate` が 01:24:57.316Z、`Recreated` が 01:25:14.149Z、確認の 200 が 01:25:14.594Z。止まっていたのは約 17 秒。
- deploy.yml の注記は「nginx 再起動中（~2-3s）に brief な 502 窓」（deploy.yml:506）で、実測と合わない。
- 影響: nginx の設定が変わる配備のたびに、お客さんの画面が約 17 秒つながらない（502 でなく接続の拒否）。
- 扱い: deploy.yml は危険パス（ADR-136）なので本書では直さない。直すなら別の設計（例: 作り直しでなく `nginx -s reload` で足りる場合を分ける）として起案する。注記の数字の訂正も同じ便で行う。

### 別件 2: 配備中かどうかを、点検が始まったときにしか見ていない

- 観測: 11/9 の毎朝の実行（schedule・01:21:37Z 作成）は、「配備中の確認」の段（prod-ui-check.yml:38-61）で配備中 0 件と判定して点検へ進んだ。#5280 の配備はその直後に始まり、上の別件 1 の 17 秒の間（01:24:57〜01:25:14Z）に点検が重なった。結果は「4 failed・1 flaky・3 passed」。落ちたのは S3（字形の CSP。まだ直す前の本番を点検したため）と、S6・S7・S8（`net::ERR_CONNECTION_REFUSED`）。S4 は 1 回目に同じ接続の拒否で落ち、試し直しで合格した（生出力 `/tmp/CC報告ファイル/ui-check-42545158421.txt` の要約の行）。落ちた知らせも送られた。
- 原因: 確認は始まったときの 1 回（配備中なら 10 分待ってもう 1 回）だけで、点検の途中で配備が始まることは見ていない。
- 影響: 毎朝の実行と合流が重なると、本番は正常でも落ちた知らせが来る（誤った知らせ）。
- 扱い: 本書の範囲外の後続。直し方の候補は「落ちたときに、点検の間に配備が動いていたかを見て、動いていたら配備の後にもう 1 回だけ確かめ直す」。週次の保守で誤った知らせの件数を数えてから決める（勝手に足さない）。

### 別件 3: 配備の後の実行が取り消される

- 観測: 01:26:49Z と 01:31:02Z 開始の `workflow_run` の実行が cancelled。どちらも次の配備の後の実行が入ってきた時点で、待っていた方が取り消された。
- 仕組み: concurrency（prod-ui-check.yml:26-28、`cancel-in-progress: false`）でも、待っている実行は 1 本までで、新しい実行が入ると待っていた方は取り消される（GitHub 公式 control-workflow-concurrency「By default, any existing pending job or workflow in the same concurrency group will be canceled」。Context7 で 2026-11-09 確認）。
- 影響: 続けて合流したとき、途中の配備の後の点検は飛ぶ。最後の配備の後の点検は必ず動くので、本番の最新の状態は見られる。§6 の「続けて合流があれば、その配備の後にもう一度点検が動く」と合っている。
- 扱い: 直さない（設計どおり）。取り消しの件数を失敗として数えないことだけ、週次の保守で守る。

### 別件 4: 在庫表は、絞り込みの読み込みが失敗したときだけ書き込みを送る

- 観測: 在庫表は開くと `GET /me/inventory-filters` を読み、成功したときだけ「最後に保存した値」を覚える（frontend/src/pages/inventory/InventoryPage.tsx:333）。失敗したときは覚えないまま読み込み済みにするので（同 :350-351）、保存の処理（同 :358-383）が既定の絞り込みを `PATCH /me/inventory-filters` で送る。
- §4-3 の「開いただけで GET 以外を送らない」は、読み込みが成功したときだけ成り立つ。
- 影響: 点検用の人の絞り込みの保存が既定に戻るだけ。お客さんのデータには触らない。
- 扱い: 点検の前提の注記として残す。在庫表の直しは本書の範囲外。
