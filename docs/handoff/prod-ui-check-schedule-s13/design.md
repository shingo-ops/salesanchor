# design: 本番の画面点検に予定表の作る小窓と全画面の編集を足す（S13）（2026-11-11）

- 状態: 設計案（Claude Opus 作成）。PO の選択「1. 毎日の本番の自動点検に、この画面の動きを足す」（2026-11-11）と、同セッションの委任「PRマージ、デプロイまで完走させてくれ」に基づく。
- recon: `docs/handoff/prod-ui-check-schedule-s13/recon.md`（以下 recon §n）
- 関連 ADR: ADR-1051（改訂する）、ADR-1060（Meet は Google をつないだ本人だけ）、ADR-144（金型 FullScreenDialog）、ADR-136（deploy.yml は触らない）

## 1. 目的（PO の言葉）

予定表の新しい動き（作る小窓・全画面の編集）が、次の配備で壊れたら「その日のうちに分かる」ようにする。今は手作業の確かめだけで、人が見るまで気づけない（recon §3）。

## 2. 成功条件（KGI・KPI）

KGI: 毎朝と配備の後の本番の画面点検で、予定表の作る小窓と全画面の編集が自動で確かめられ、本番に何も書き込まずに合格する。壊れたら Discord に知らせが来る。

| # | 基準 | 検証方法 | ○× |
|---|---|---|---|
| K1 | 本 PR の合流後の配備の後の点検（event=workflow_run）で S13 が passed（skipped・failed・flaky〔再試行で通った〕は×） | `gh run view <run> --log` の「本番の画面点検を実行」の段で `S13` の行が ✓ | ○× |
| K2 | 同じ実行で S1〜S8・S10〜S12 も全部合格のまま | 同じ段で failed 0 | ○× |
| K3 | S13 は本番に書き込みを送らない | ①コードで GET 以外（ログインの札の更新 `/api/v1/auth/refresh` だけを除く）を全部止め、止めた件数 0 を最後に確かめる（§4-1）②審査で S13 に `.click()` されるのが「その他のオプション」と Meet の行（出たときだけ）だけで、「保存」を押す行が 0 件であることを `grep` で確かめる | ①② 両方で○ |
| K4 | 壊したら落ちる（点検が空振りしない） | 審査で、§3 の「○」の各行に S13 の expect が 1 つ以上あり、その expect は壊れたときに落ちる形（見えること・値・件数の一致）であることを確かめる。本番でわざと落とす試験はしない | 審査で○ |
| K5 | 毎朝の実行（22:00Z）でも S13 が passed | 合流の翌朝の schedule の実行で同じく ✓（skipped・failed・flaky は×） | ○× |

## 3. S13 が確かめる点（手作業の G51〜G57 との対応）

| 確かめる点 | 手作業の条件 | 点検用の人で確かめられるか |
|---|---|---|
| キー `c` で作る小窓が開き、題名が入れられる | G53 の前段 | ○ |
| Google Meet の名前の付いた切り替えスイッチが 0 個 | G51 | ○ |
| Meet の行を押すと「保存すると参加用のリンクができます」、× で元に戻る | G51 | × 点検用の人は管理者でないため行が出ない（recon §2）。出たときだけ確かめ、出ないときは注記を残す。守りは単体試験 |
| 「その他のオプション」で窓いっぱいの編集画面（予定の編集）が開く | G53 | ○ |
| 題名が編集画面に引き継がれる | G53 | ○ |
| 編集画面で `m` を押しても表示が切り替わらない | G56 | ○（注: 全画面の止め SchedulePageImpl.tsx:1250 と小窓の止め :1266 の二重に守られている。:1250 だけが壊れたときはこの行では落ちない。単体試験 SchedulePageImpl.test.tsx:866 も同じ二重の状態で確かめている。:1250 は重ねの守りで、単独の壊れは今どこでも検出しない。利用者に見える動きは :1266 が守るため変わらない） |
| Tab を 25 回押してもフォーカスが編集画面の外に出ない | G56 | ○ |
| Esc で編集画面が閉じ、作る小窓と題名が残る | G54 | ○ |
| もう一度 Esc で作る小窓も閉じる | 後片付け | ○ |
| その間 console.error 0 件 | S12 と同じ | ○ |
| 保存（G55）・色（G57） | G55・G57 | 対象外。保存は書き込みになる。色は CI の Lint & Dark Mode Check が守る |

## 4. 変更の中身（実装役は書いてあるとおりに変える）

### 4-1. `tests/prod-check/prod-ui.spec.ts`

(a) 2 行目の見出しを変える。

変更前:
```
 * 本番の画面点検 S1〜S12（S9 は通知の試験）（見るだけ。書き込み操作はしない）
```
変更後:
```
 * 本番の画面点検 S1〜S13（S9 は通知の試験）（見るだけ。書き込み操作はしない）
```

(b) S12 の test の閉じ `  });`（今の 176 行目）の直後、空行をはさんで `  // 通知の試験用。` の行（今の 178 行目）の前に、次をそのまま足す。

```ts
  test("S13 予定表の作る小窓と全画面の編集が開いて閉じる（保存しない）", async ({ authedPage: page }) => {
    // 書き込みは送らせない。ログインの札の更新（/api/v1/auth/refresh）以外の GET でない通信は止めて数える
    const blockedWrites: string[] = [];
    await page.route("**/api/**", (route) => {
      const req = route.request();
      const path = new URL(req.url()).pathname;
      if (req.method() !== "GET" && path !== "/api/v1/auth/refresh") {
        blockedWrites.push(`${req.method()} ${path}`);
        return route.abort();
      }
      return route.continue();
    });
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });

    const events = apiOk(page, CALENDAR_EVENTS_API);
    await page.goto("/schedule");
    expect((await events).status(), "予定の API の応答").toBeLessThan(400);
    await expect(page.locator("main .comp-calendar")).toBeVisible();
    await expect(page.locator("main .schedule-loading")).toHaveCount(0);
    const viewButton = page.locator('main button[aria-haspopup="menu"]').first();
    const viewBefore = (await viewButton.innerText()).trim();

    // 1. キー c で作る小窓を開き、題名を入れる
    await page.keyboard.press("c");
    const popover = page.locator(".schedule-popover--create");
    await expect(popover, "キー c で作る小窓が開く").toBeVisible();
    const popoverTitle = popover.getByRole("textbox", { name: "タイトル", exact: true });
    await popoverTitle.fill("prod-ui-check-s13");

    // 2. Google Meet の名前の付いた切り替えスイッチは無い
    await expect(page.getByRole("switch", { name: /Google Meet/ }), "Meet のスイッチは 0 個").toHaveCount(0);

    // 3. Meet の行（Google をつないだ管理者だけに出る）。出たときだけ押して外す
    const addMeet = popover.getByRole("button", { name: "Google Meet のビデオ会議を追加", exact: true });
    if ((await addMeet.count()) > 0) {
      await addMeet.click();
      await expect(popover.getByText("Google Meet のビデオ会議（保存すると参加用のリンクができます）", { exact: true })).toBeVisible();
      await popover.getByRole("button", { name: "Google Meet を外す", exact: true }).click();
      await expect(addMeet).toBeVisible();
    } else {
      test.info().annotations.push({ type: "note", description: "Meet の行は出ない（点検用の人は管理者でない）" });
    }

    // 4. その他のオプションで窓いっぱいの編集画面が開き、題名が引き継がれる
    await popover.getByRole("button", { name: "その他のオプション", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: "予定の編集", exact: true });
    await expect(dialog, "全画面の編集が開く").toBeVisible();
    const box = await dialog.boundingBox();
    // 比べる相手はスクロール帯を除いた窓の中の大きさ（審査の指摘 2）
    const viewport = await page.evaluate(() => ({ width: document.documentElement.clientWidth, height: window.innerHeight }));
    expect(box, "全画面の編集の大きさ").not.toBeNull();
    expect(Math.abs(box!.x), "左端").toBeLessThanOrEqual(1);
    expect(Math.abs(box!.y), "上端").toBeLessThanOrEqual(1);
    expect(Math.abs(box!.width - viewport.width), "幅が窓と同じ").toBeLessThanOrEqual(1);
    expect(Math.abs(box!.height - viewport.height), "高さが窓と同じ").toBeLessThanOrEqual(1);
    await expect(dialog.getByRole("textbox", { name: "タイトル", exact: true }), "題名の引き継ぎ").toHaveValue("prod-ui-check-s13");

    // 5. 編集画面では近道のキーが効かない（入力欄の外で m を押す）
    const closeButton = dialog.getByRole("button", { name: "閉じる", exact: true });
    await closeButton.focus();
    await page.keyboard.press("m");
    await expect(dialog, "m を押しても編集画面は開いたまま").toBeVisible();
    await expect(viewButton, "m を押しても表示は変わらない").toHaveText(viewBefore);

    // 6. Tab を 25 回押してもフォーカスは編集画面の中
    for (let i = 0; i < 25; i += 1) {
      await page.keyboard.press("Tab");
    }
    await expect(dialog.locator(":focus"), "フォーカスは編集画面の中").toHaveCount(1);

    // 7. Esc で編集画面が閉じ、作る小窓と題名が残る
    await page.keyboard.press("Escape");
    await expect(dialog, "Esc で編集画面が閉じる").toHaveCount(0);
    await expect(popover, "作る小窓は残る").toBeVisible();
    await expect(popoverTitle, "題名は残る").toHaveValue("prod-ui-check-s13");

    // 8. もう一度 Esc で作る小窓も閉じる（保存はしない）
    await page.keyboard.press("Escape");
    await expect(popover, "Esc で作る小窓も閉じる").toHaveCount(0);

    expect(blockedWrites, `止めた書き込み ${blockedWrites.length} 件`).toHaveLength(0);
    expect(errors, `console.error が ${errors.length} 件`).toHaveLength(0);
  });
```

- 新しい import・定数は足さない（`apiOk`・`CALENDAR_EVENTS_API`・`test`・`expect` は今のファイルに在る。recon §1）。
- 画面の文字は ja.json の今の値（recon §2）。i18n の決まり（ADR-027）は画面の部品の話で、点検の期待値に日本語を書くのは今の S1〜S12 と同じ。

### 4-2. `docs/adr/ADR-1051-prod-ui-black-box-check.md`

- 備考の行の最後（`…docs/handoff/prod-ui-check-after-deploy/design.md）` の後）に次を足す: `。改訂 2026-11-11（予定表の作る小窓と全画面の編集を見る S13 を足す）は PO の選択 2026-11-11「1」と委任「PRマージ、デプロイまで完走させてくれ」に基づき Claude Opus が決めた（設計 docs/handoff/prod-ui-check-schedule-s13/design.md）`
- What の「2026-11-08 改訂で、在庫表…を足した。」の文の後に次を足す: ` 2026-11-11 改訂で、予定表の作る小窓と全画面の編集が開いて閉じること（S13。保存しない。ログインの札の更新以外の書き込みは点検の中で止めて 0 件を確かめる）を足した。Meet の行は点検用の人には出ない（管理者でないため）ので、本番の点検では確かめない。`
- `node scripts/generate-adr-index.js` を実行し、`docs/adr/README.md` に差分が出たらコミットに含める。

### 4-3. 触らない範囲

- `.github/workflows/prod-ui-check.yml`（S13 は今の段でそのまま動く。変えない）・`.github/workflows/deploy.yml`・`.github/workflows/workflow-lint.yml`
- `tests/prod-check/` の他のファイル（fixtures.ts・login.ts・playwright.config.ts・settle.ts・page-speed*・device-*）
- `frontend/` の全部（製品コードは変えない）
- 点検用の人の役割・権限（管理者にしない。ADR-1051:19）

## 5. 影響範囲

- 点検の実行時間: S13 の前に 20 秒の待ち（fixtures.ts）＋本体 10 秒前後。仕事の上限 60 分（prod-ui-check.yml）に対し十分小さい。
- ログインの道の回数: S13 は goto 1 回＝refresh 1 件。fixtures.ts の想定（1 test あたり最大 3 件）の中。
- 本番データ: 書き込みは route で止めるので届かない（K3）。予定の小窓を開くだけの画面の状態は保存されない（`openCreate` は画面の中の状態だけ。recon §2）。
- 不合格の知らせ: test 名が知らせにそのまま出る（prod-ui-check.yml の知らせの段）。名前で何が壊れたか分かる。

## 6. 代替案

| 案 | 採否 | 理由 |
|---|---|---|
| A. 今の点検（prod-ui-check）に S13 を足す | 採用 | 毎朝と配備の後の両方で動く道・知らせの道がすでにある。足すのは 1 ファイルの 1 test だけ |
| B. 点検用の人を管理者にして Meet の行も確かめる | 不採用 | ADR-1051:19 が見るだけの役割と決めている。管理者は二段階ログインが要り機械は入れない（ADR-1048） |
| C. 保存まで行い、あとで消す | 不採用 | ADR-1051:24「本番のデータを作らない・変えない・消さない」に反する。Google 側にも予定と Meet の部屋が作られる |
| D. frontend/e2e（CI の画面試験）に足す | 不採用 | CI の試験は本番を見ない。今回の穴は「本番で壊れても気づけない」こと。単体試験はすでに 86 件ある |

## 7. リスクと対処

| リスク | 対処 |
|---|---|
| 点検用の人の画面の言葉が日本語でない | 今の S1〜S12 が同じ日本語の名前で合格している（recon §1）。変わったら S1 から落ちて分かる |
| 表示の初期値が「週」以外（人ごとの設定） | 押す前の表示を読んでから比べる（固定の「週」と比べない） |
| 編集画面の閉じるボタンにフォーカスを当てると、Esc の前にフォーカスの位置が変わる | Esc は document で受ける（FullScreenDialog.tsx:72-78）。フォーカスの位置に関わらず閉じる |
| 点検が落ちたとき、作る小窓が開いたまま | 画面の中の状態だけで、page は test ごとに閉じる（fixtures.ts）。データは残らない |
| route で止めた書き込みが、画面の別の動き（既読の印など）だった | 止めた件数が 1 以上なら S13 が落ち、知らせの名前で分かる。本番の手作業の確かめでは同じ操作で書き込み 0 件だった（recon §3） |

## 8. 外部事例

不要。理由: 新しい仕組みを入れるのではなく、既に毎日動いている点検（ADR-1051）に 1 件足すだけ。点検の書き方は同じファイルの S1〜S12 と、手作業の本番の確かめ（recon §3）を根拠にする。

## 9. 維持する担当と仕組み

- 毎朝 JST 07:00 と配備の後に自動で動く（prod-ui-check.yml）。落ちたら Discord の api の部屋に test 名つきで知らせる。合格は知らせない。
- 予定表の画面の文字や作りを変える PR は、この点検の期待値（ボタンの名前）も一緒に直す。直し忘れは配備の後の点検が落ちて分かる。
- 点検が動いていること自体は、GitHub の実行一覧で直近の成功を見る（ADR-1051 守り方）。

## 10. 実装カード（クラウドの Sonnet が行う）

- ブランチ: `release/prod-ui-check-schedule-s13`（origin に push 済みのものを使う。新しく作らない）
- 変えるファイル: §4-1 と §4-2 の 2 ファイル（＋ README.md に差分が出たら 3 ファイル）。他は触らない（§4-3）。
- 手順
  1. `./scripts/dev/executor-preflight.sh || exit 1`
  2. §4-1 を書いてあるとおりに足す（言い換え・付け足し禁止）。
  3. §4-2 を足し、`node scripts/generate-adr-index.js` を実行。
  4. 確かめ（生出力をそのまま報告に貼る）
     - `cd frontend && npm ci` の後、`NODE_PATH=$PWD/node_modules ./node_modules/.bin/playwright test --config ../tests/prod-check/playwright.config.ts --list`（本番には流さない。S13 が一覧に出ること）
     - `grep -n "click()" tests/prod-check/prod-ui.spec.ts` の S13 の範囲の行（保存を押す行が無いこと）
     - `grep -nE "psql|SELECT |INSERT |DATABASE_URL" tests/prod-check/prod-ui.spec.ts`（0 件）
     - `git diff --stat origin/main...HEAD`
  5. commit（本文の最後に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）→ push。PR は作らない（Opus が作る）。
- 止まる条件: §4-1 の挿入位置が recon の行番号と合わない／`--list` が読み込みで失敗する／触らない範囲に差分が出る → 何も直さず BLOCKED: と生出力を返す。
- 本番の点検を手で流さない（workflow_dispatch しない）。それは合流後に Opus が配備の後の実行で見る。

## 11. 設計の審査（2026-11-11・クラウドの Claude Opus・同一AIの審査）

- 判定 APPROVE（止める指摘なし）。軽い指摘 4 件を本版で反映: ① m の行の二重の守りを §3 に注記 ② 大きさの比較をスクロール帯を除いた幅（clientWidth）と innerHeight に変更 ③ K1・K5 で flaky も×と明記 ④ 書き込みの除外を `/api/v1/auth/refresh` だけに絞った（根拠 frontend/src/lib/auth/selfAuth.ts:11・:181）。
- 確かめて合っていた点: キー c は window の keydown に届く・画面の名前は ja.json と一致・表示切替ボタンの探し方は一意・Esc の順・Tab の閉じ込め・API の基点は同じ host の /api/v1（api.ts:32）・ログインの道の回数は想定内。
