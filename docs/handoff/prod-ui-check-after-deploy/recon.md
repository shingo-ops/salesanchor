# recon: 本番の画面点検を配備のたびに自動で回す（2026-11-08）

PO 依頼（2026-11-07）:「恒久的に対策できる？事務的、定常作業は任せたい」→ 選択「1. この進め方で設計を始める」。
基準: `origin/main` 5a531586a9c0b98151e651d8793d058f2814a54f（worktree `release/prod-ui-check-after-deploy-design`）。
生出力: `/tmp/CC報告ファイル/recon-produi-1.txt`〜`recon-produi-14.txt`、`k6-perm-recon.txt`、`checker-perms.txt`、`prod-ui-after-bin2.txt`、`prod-ui-1107-fail.txt`。

## 0. 既存 ADR の検索結果

- ADR-1051（本番の画面点検。Accepted 2026-10-30）: `docs/adr/ADR-1051-prod-ui-black-box-check.md`。毎日 JST 07:00 と手動。認証情報は GitHub secrets だけ。不合格のときだけ Discord。artifact を作らない。
- ADR-1053（全画面の速さの記録。Accepted 2026-10-31）: `docs/adr/ADR-1053-prod-page-speed-record.md`。点検の後に 135 画面を測る段（最大 46 分・判定なし）。
- ADR-1065（予定表の金型 CalendarView）: `docs/adr/ADR-1065*.md:38`「v6 は実行時に `<style>` を差し込む。CSP で inline style を止める変更をするときは、この金型が崩れないかを先に確かめる」。
- ADR-136（危険 PR の GO 手順）: 危険パスは `migrations/`・`deploy.yml`・本番 `scripts/`。本件は deploy.yml を変えない設計にする（§3）。

## 1. 困りごと（観測事実）

- 2026-11-07 の確かめ（K6）で、点検用の人のログイン情報が GitHub secrets にしかなく、手元の確かめ役は画面を開けなかった（evaluator が BLOCKED を返した）。
- 点検は 1 日 1 回（`.github/workflows/prod-ui-check.yml` の schedule `0 22 * * *`）。配備の直後には動かない。
- `.github/workflows/deploy.yml:1-7`: 名前は `Deploy to VPS`、`on: push: branches: [main]`。prod-ui-check を呼ぶ記述は無い（`git grep workflow_run .github/workflows` は deploy.yml:72 の API 文字列 1 件のみ。recon-produi-10.txt）。
- 実行の記録（k6-perm-recon.txt:118-124）: 11/6 01:57Z 成功、11/7 01:30Z 失敗。11/7 の手動実行（prod-ui-after-bin2.txt）も同じ失敗。

## 2. 今の失敗の原因（S3 ダッシュボード）

- 失敗した点検: `tests/prod-check/prod-ui.spec.ts:41-53` S3。`/` を開いて 5 秒の間の console.error を数え、0 件でなければ不合格。
- 出ていた文（prod-ui-1107-fail.txt）: `Loading the font 'data:application/x-font-ttf;…' (fcicons) violates the following Content Security Policy directive: "default-src 'self'". Note that 'font-src' was not explicitly set…`
- 本番の CSP: `nginx/nginx.conf:96` = `default-src 'self'; script-src 'self'; connect-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:`。`font-src` が無いので `default-src 'self'` が効き、`data:` の字形が止まる。
  - 同じファイルの `/grafana/` は `font-src 'self' data:` を持つ（`nginx/nginx.conf:320`）。
  - 96 行の最後の変更は 317bfb653（11/5、Firebase の記述の削除だけ）。その前から `font-src` は無かった（recon-produi-3.txt:108-113）。
- なぜダッシュボードで出るか:
  - `frontend/src/App.tsx:63` は `import SchedulePage from "./pages/schedule/SchedulePage";`（遅延読み込みではない）。SchedulePage → SchedulePageImpl → `frontend/src/components/CalendarView.tsx:49-53` が `@fullcalendar/*` を読む。
  - FullCalendar の core は、読み込まれた時点で `injectStyles(css_248z)` を呼び、`fcicons` の `@font-face`（data: の字形）を入れた `<style>` を差し込む（`frontend/node_modules/@fullcalendar/core/internal-common.js:7,85-86`。手元の写しは 6.1.20。本番は ADR-1065 の 6.1.22。6.1.22 でも同じことは実装時に確かめる）。
  - よって、どの画面を開いても字形の読み込みが起き、CSP に止められて console.error が出る。S3 だけが console.error を数えるので S3 だけが落ちる。
- 入った時期: 予定表を CalendarView に載せた #5226・#5232（11/6 23:06Z）が 11/6 成功と 11/7 失敗の間にある。【推測】これが始まり。確かめ方: 直す後に S3 が合格すること（§受入）。

## 3. 配備の後に点検を動かす方法

- GitHub Actions の `workflow_run`（別の仕事が終わったら動く）で、prod-ui-check.yml 側だけを変えれば足りる。deploy.yml（危険パス）は触らない。
  - 仕様の確認は実装時に Context7（GitHub Actions）で行う。押さえる点: `workflows:` は仕事の名前（`Deploy to VPS`）で書く／`types: [completed]`／結果は `github.event.workflow_run.conclusion` で `success` を見る／既定のブランチ（main）の prod-ui-check.yml が使われる。
- 今の配備中の待ち（`prod-ui-check.yml:30-53`）: 動いている deploy.yml を数えて 600 秒待ち、まだ動いていれば見送る。配備の後に動く場合、呼んだ配備は終わっているので待たない。次の配備が並んでいれば今の待ちがそのまま効く。
- 同時実行: `concurrency: group: prod-ui-check, cancel-in-progress: false`（`prod-ui-check.yml:20-22`）。続けて配備されても、待ちは 1 本にまとまる。
- 速さの記録の段（`prod-ui-check.yml:146-150`、最大 46 分）は毎朝だけでよい。配備のたびに回すと 1 回 50 分になる。
- `workflow-lint.yml` の検査対象（recon-produi-10.txt:88-117・recon-produi-11.txt:1-12）に prod-ui-check.yml は無い。変えても lint の規則には触れない。`workflow-lint.yml` 自身は変えない。
- nginx の変更は配備で自動で反映される（`deploy.yml:44-45` で `nginx/**` の変更を見て、`deploy.yml:516-553` で `nginx -t` を通してから作り直し、だめなら前の設定へ自動で戻す）。

## 4. 足す 3 画面（点検用の人で見られるか）

点検用の人の役割は「点検用（見るだけ）」（checker-perms.txt）。`products.view`・`leads.view` を持つ。

| 画面 | 道すじ | 画面の部品 | 呼ぶ API | 必要な権限 | 点検用の人 |
|---|---|---|---|---|---|
| 在庫表 | `/inventory`（`App.tsx:233`） | InventoryPage | `GET /api/v1/inventory`（`backend/app/routers/inventory_offers.py:350-354`、`backend/app/main.py:678` で前置き `/api/v1`） | `products.view` | 持つ |
| リードの詳細 | `/crm/leads/:id/edit`（`App.tsx:206`） | LeadEditPage（`useApiQuery('/leads/${id}')` `LeadEditPage.tsx:99`。保存は押したときだけ `:120`） | `GET /api/v1/leads/{lead_id}`（`backend/app/routers/leads.py:367-370`） | `leads.view` | 持つ |
| 予定表 | `/schedule`（`App.tsx:290`） | SchedulePage → CalendarView | `GET /api/v1/calendar/events`（`backend/app/routers/calendar.py:142`、権限の条件なし・ログインと会社だけ） | なし | 見られる |

- リードの一覧 `GET /api/v1/leads` は `list[LeadResponse]`（`leads.py:214-217`）。`LeadResponse.id` は int（recon-produi-14.txt）。一覧の返事の 1 件目の id で詳細を開ける。`/leads/sales-form-options`（`leads.py:302`）と混ざらないよう、詳細の判定は数字だけの形にする。
- 予定表の書き込み（`SchedulePageImpl.tsx:1114,1116,1292`）は保存の操作のときだけ。点検は押さない。そもそも見るだけの人なので書き込みは 403。
- 11/7 の配備後の本番の記録で `GET /api/v1/calendar/events` は 200 が 4 回（k6-access-after-bin2.txt）。在庫表とリードの詳細は通信が無く、まだ見ていない。

## 5. 今の点検の作り（そろえる形）

- `tests/prod-check/prod-ui.spec.ts:13-21` `apiOk(page, pathRe)`（GET の返事を 20 秒待つ）、`:92-108` S6（一覧→詳細の形）、`:41-53` S3（console.error を数える形）。
- `tests/prod-check/playwright.config.ts:23-26`: retries 1・workers 1・timeout 60 秒・expect 10 秒。
- S4 は 11/7 の手動実行で 1 回目が 20 秒切れ、2 回目に 2.4 秒で合格（prod-ui-after-bin2.txt）。本件では変えない（§design 対象外）。
- 不合格の知らせ（`prod-ui-check.yml:110-144`）: 落ちた点検の名前と実行の URL を送る。毎朝か配備の後かは書いていない。

## 6. 未確認

- FullCalendar 6.1.22 でも読み込み時に字形を差し込むか（`frontend/package-lock.json:11` は 6.1.22、手元の node_modules は 6.1.20）。→ 実装時に 6.1.22 の node_modules で確かめる。
- `/` 以外の画面でも同じ console.error が出ているか（S3 だけが数えるので、出ていても気づかない）。→ §design の S12 で予定表でも数える。
