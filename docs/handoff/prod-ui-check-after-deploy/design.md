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
  - `tests/prod-check/fixtures.ts`・`login.ts`・`settle.ts`・`page-speed*.ts`
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
- 反映: 配備が `nginx/**` の変更を見て、`nginx -t` を通してから作り直す。通らなければ前の設定に自動で戻す（`deploy.yml:516-553`、recon §3）。

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
- `workflow_dispatch` の入力 `force_fail` は、`workflow_run` のときは空になる。今の参照 `PROD_CHECK_FORCE_FAIL: ${{ inputs.force_fail && '1' || '' }}`（`prod-ui-check.yml:107`）は空なら `''` になり、S9 は足されない（`prod-ui.spec.ts:134-135`）。変えない。
- 配備中の待ち（`prod-ui-check.yml:30-53`）・concurrency・timeout・permissions は変えない。

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
  - エラーの出方は画面ごとに違う（審査 2026-11-08 の指摘。生出力 `/tmp/CC報告ファイル/recon-produi-15.txt`）。在庫表は `.error-message`（`frontend/src/pages/inventory/InventoryPage.tsx:549`）、リードの詳細も `.error-message`（`frontend/src/pages/leads/LeadEditPage.tsx:147`）。S4 と同じく `.error-banner` と `.error-message` の両方が 0 件であることを見る。予定表は読み込み中が `.schedule-loading`（`SchedulePageImpl.tsx:876`）、失敗が `.schedule-error`（`SchedulePageImpl.tsx:1525`）なので、この 2 つが 0 件であることを見る。
  - 在庫表の読み込み中の表示は `LoadingBlock` ではなく、いつも置いてある `data-testid="inventory-loading"` の箱（`frontend/src/pages/inventory/InventoryPage.tsx:632-640`）。読み込み中だけ `visibility: visible`、終わると `hidden`。数は常に 1 なので、S10 は件数でなく `toBeHidden()` で読み込みの終わりを見る（審査 2 回目の指摘）。リードの詳細は `LoadingBlock`（class `sa-loading-block`、`frontend/src/components/loading/LoadingBlock.tsx:18`・`LeadEditPage.tsx:149`）なので S11 は件数 0 で見る。
  - 予定表は開くと `GET /api/v1/shifts` も呼ぶ（`SchedulePageImpl.tsx:961`）。`shifts.view` が要る（`backend/app/routers/shifts.py:55-56`）。点検用の人の役割「点検用（見るだけ）」は `shifts.view` を持つ（`/tmp/CC報告ファイル/checker-perms.txt:2`、本番の読み取り 2026-11-07）。403 の console.error で S12 が落ちることは無い。
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

- 点検が動いているかは、GitHub の実行一覧の event 列で `workflow_run` と `schedule` の両方の直近の成功を見る（ADR-1051「守り方」に足す）。
- 新しい画面の点検を足すときは `tests/prod-check/prod-ui.spec.ts` の S 番号を続けて足す。開くだけ・書き込まない・番号を文に出さない、の 3 つを守る。
- 週次の保守（agent-console 定期実行）で、直近 7 日の prod-ui-check の失敗件数を見る。0 でなければ原因を調べる。

## 8. 外部事例

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
