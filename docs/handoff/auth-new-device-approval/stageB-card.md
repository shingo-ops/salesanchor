# 段B 実装カード（知らない機械からのログインに許可を求め始める・第1版）

- 対象: docs/handoff/auth-new-device-approval/design.md 第6.1版 §3 D4・D11・D12、§4 段B（B-0・B-1・B-2）、§6「点検が止まらない」、§7 の戻し方と「切替の日にログイン中の機械が無い人」。ADR-1055。合格の基準は kgi.md（PO 承認済 2026-11-01）。
- 中身の正本: 何をどう作るかは design.md §4 段B のとおり。このカードは「順番・形の細部・先に確かめること・止まる条件・受入」を足す。design.md とこのカードが食い違うときは止まって Opus へ返す（§0 の V で直したものはカードが正）。
- 根拠の写し: S=origin/main 22c4c221d64932bbd17ba71f292c2e89e18a5b75（段W #5013 の本番反映の後）。生の出力は docs/handoff/auth-new-device-approval/stageB-recon-raw.md。
- 前提: 段A・段W は本番反映済み（段W は W7〜W10 合格・PR #5013 のコメント）。本番の AUTH_DEVICE_APPROVAL は今 off。
- 実行役: B-0 は PO の手元（`!`）。B-1・B-2 はクラウドの Sonnet。PR は Opus が手元で作る。作業場所の作り方はクラウドの決まり（S scripts/agent-hooks/cloud/rules.md）を正とする。出力には上限を付ける。待つために sleep を使わない。
- 状態: 第1版（Opus 作成）。審査はこれから。
- 受領確認: 実装役は着手の最初の報告に「段B カード 第1版を受け取った・S=22c4c221d」と書く。

## 0. 設計からの直し（V）

- V-1 本番の入れ物の名前: 本番の backend は compose の組 astro-webapp の中にある。~/salesanchor で `docker compose exec backend` を流すと「service "backend" is not running」になる（段W W7 で実測・PR #5013 のコメント）。B-0 と数え直しは `docker exec astro-webapp-backend-1` で流す。
- V-2 印の値の改行: 管理用の命令は値の後に改行を1つ出す（S backend/app/cli/issue_trusted_device.py:127 `sys.stdout.write(raw + "\n")`）。サーバーは印の値を `^[A-Za-z0-9_-]{16,128}$` で受ける（S backend/app/auth/devices.py）。gh secret set が最後の改行を落とすかは【未確認】なので、`tr -d '\n'` で落としてから流す。
- V-3 reader 鍵では数えられない: 2026-11-02 に reader 鍵で public.users・auth_refresh_tokens・user_trusted_devices を読むと 42501（権限なし）だった（stageB-recon-raw.md の末尾）。design.md の「user87 の created_via='cli' を reader 鍵で確かめる」と「切替の日の人数を reader 鍵で数え直す」は、どちらも PO の手元の manual-only 鍵で、数だけを出す命令に変える（§4b）。reader 鍵の権限は広げない（このカードの範囲外）。
- V-4 deploy.yml の行番号: design.md の「:371 付近」「:318-320」は古い。S では、古い行の削除は :316-320（AUTH_*）、書き出しは :374-377（AUTH_*）。
- V-5 docker-compose.yml は直さない: backend の env の AUTH_DEVICE_APPROVAL・AUTH_DEVICE_BOOTSTRAP_CUTOFF は段A で入っている（S docker-compose.yml:150-151）。
- V-6 締切の値の決め方: 締切は「PR-B の本番反映を終える予定の時刻＋6時間」を UTC の固定値で書く（D4）。値は Opus が実装を頼む文で渡す（例 `2026-11-04T09:00:00Z`）。実装役は自分で時刻を決めない。渡されていなければ NEEDS_DECISION: で返す。
- V-7 機械の印は使っても作り直されない: いつもの機械でログインすると、サーバーは同じ印を Cookie に付け直す（S backend/app/routers/auth.py:419-424・:496）。GitHub の秘密に置いた値は、取り消すか180日使わないかまで有効（S backend/app/auth/devices.py:190）。点検は毎日動くので、180日の期限には当たらない。

## 1. 触るファイル（変更前→変更後）

| # | ファイル | 変更前（S） | 変更後 | 回 |
|---|---|---|---|---|
| 1 | tests/prod-check/login.ts | :36-53 の login()。最初に PublicKeyCredential を消し（:38-40）、合言葉の状態を差し替える（:42-44） | :36 の関数の最初（:37 の説明の前）に次を足す。`const deviceToken = process.env.SMOKE_E2E_DEVICE_TOKEN;` があれば `await page.context().addCookies([{ name: "sa_device", value: deviceToken, domain: new URL(BASE_URL).hostname, path: "/api/v1/auth", secure: true, httpOnly: true, sameSite: "Strict" }]);`。`url` では付けない（design.md B-1 の理由）。値をログに出さない。無いときは何もしない（今と同じ）。説明の1行に「ADR-1055 段B: 点検の人のいつもの機械の印（enforce で許可待ちにしない）」を書く | 1 |
| 2 | .github/workflows/prod-ui-check.yml | :104-105（画面点検の段）・:153-154（速さの記録の段）に SMOKE_E2E_EMAIL と SMOKE_E2E_PASSWORD | 2か所とも、SMOKE_E2E_PASSWORD の次の行に `SMOKE_E2E_DEVICE_TOKEN: ${{ secrets.SMOKE_E2E_DEVICE_TOKEN }}` を同じ字下げで足す | 1 |
| 3 | .github/workflows/deploy.yml | :316-320 古い AUTH_* 行の削除。:374-377 AUTH_* の書き出し | :320（`/^VITE_AUTH_PROVIDER=/d`）の次に `-e '/^AUTH_DEVICE_APPROVAL=/d' \` と `-e '/^AUTH_DEVICE_BOOTSTRAP_CUTOFF=/d' \` を同じ字下げで足す。:377（`VITE_AUTH_PROVIDER='self'`）の次に、説明の1行（`# ADR-1055 段B: 知らない機械は許可待ち。締切は PR-B の本番反映予定＋6時間の UTC 固定値（D4）。戻すときは off`）と `AUTH_DEVICE_APPROVAL='enforce'`・`AUTH_DEVICE_BOOTSTRAP_CUTOFF='<V-6 で渡された値>'` を足す。どちらも単一引用符で囲む（:391 の形の検査 `^[A-Z0-9_]+='[^']*'$` に合わせる） | 1 |

## 2. 触らない範囲

- backend・frontend・migrations・nginx・docker-compose.yml は一切触らない。
- prod-check の他のファイル（fixtures.ts・page-speed.spec.ts・prod-ui.spec.ts・playwright.config.ts）は触らない。呼び出し元の fixtures.ts:39 と page-speed.spec.ts:480 は login() を通るので、#1 だけで両方に効く。
- prod-ui.spec.ts の S7（:108-123・知らない人のログインが 401）は変えない。知らない人は機械の判定の前に 401 になる（S backend/app/routers/auth.py:403-410）。
- scripts/security_check.sh:191 は偽のアカウントで失敗を確かめるだけなので触らない。
- deploy.yml の他の行・secrets の追加の仕方・cutoff 以外の値は触らない。

## 3. 先に確かめること（想定分岐）

- (a) `git rev-parse origin/main` を記録する。S から tests/prod-check/login.ts・.github/workflows/prod-ui-check.yml・.github/workflows/deploy.yml が変わっていたら（`git diff --stat 22c4c221d origin/main -- <3ファイル>` が空でない）、行番号を読み直す。中身の意味が変わっていたら BLOCKED: で返す。
- (b) deploy.yml に AUTH_DEVICE_ の行がすでにあれば（`grep -n AUTH_DEVICE_ .github/workflows/deploy.yml` が1件以上）、二重に足さず BLOCKED: で返す。
- (c) V-6 の締切の値が UTC の `YYYY-MM-DDTHH:MM:SSZ` の形でなければ NEEDS_DECISION: で返す。
- (d) prod-ui-check.yml に SMOKE_E2E_PASSWORD が2か所でなければ（`grep -c 'SMOKE_E2E_PASSWORD:' .github/workflows/prod-ui-check.yml` が 2 でない）、BLOCKED: で返す。
- (e) tests/prod-check を型で確かめる仕組みが CI にあるか（`grep -rn "prod-check" .github/workflows/*.yml | grep -v prod-ui-check.yml | head -20`）を記録する。あればその命令を手元で流す。無ければ「型の確かめは CI に無い」と書く。

## 4. 手順（1段に命令1つ）

1. 作業場所を作る（クラウドの決まりどおり）。枝は release/new-device-approval-stage-b-impl。origin/main に docs/handoff/auth-new-device-approval/stageB-card.md が無ければ BLOCKED: で返す。
2. §3 の (a)〜(e) を流し、結果を報告に書く。
3. §1 #1 を直す。
4. §1 #2 を直す。
5. §1 #3 を直す。
6. `git diff --stat` が3ファイル・足しただけ（消した行0）であることを確かめる。
7. `python3 -c "import yaml,sys; [yaml.safe_load(open(f)) for f in sys.argv[1:]]" .github/workflows/deploy.yml .github/workflows/prod-ui-check.yml` が何も出さずに終わることを確かめる。
8. deploy.yml の書き出しの中身を取り出し、形の検査と同じ式で外れが0行であることを確かめる: `sed -n '/cat > .env.secrets.new <</,/^ *ENV_EOF$/p' .github/workflows/deploy.yml | sed '1d;$d' | sed 's/^ *//' | grep -v '^#' | grep -nvE "^[A-Z0-9_]+='[^']*'$|^COMPOSE_FILE="`（出力が空なら合格。heredoc の書き方が違って取り出せなければ、その事実を書いて目で2行を確かめる）。
9. tests/prod-check には型の確かめの設定（tsconfig）が無い（S の ls）。代わりに、本番に触らず読み込みだけを確かめる: `NODE_PATH=frontend/node_modules ./frontend/node_modules/.bin/playwright test --config tests/prod-check/playwright.config.ts --list 2>&1 | tail -20` が点検の一覧を出して終わること（読み込みの失敗が0）。§3(e) で型の確かめの命令が見つかれば、それも流す。
10. コミットして push する。コミットの文は `feat: enforce new-device approval in production (ADR-1055 stage B)`。
11. DONE: で返す（下の「停止と報告」）。PR は作らない。

## 4b. GO と承認・Opus と PO の操作

- B-0（PR より前・PO の `!`）: 値を画面に出さずに秘密へ流す。
  `ssh -i ~/.ssh/manual-only/id_ed25519 ubuntu@49.212.137.46 'docker exec astro-webapp-backend-1 python -m app.cli.issue_trusted_device --user-id 87 --label prod-ui-check' | tr -d '\n' | gh secret set SMOKE_E2E_DEVICE_TOKEN --repo shingo-ops/salesanchor`
  - off の間は印を見ないので、先に置いても今のログインは変わらない。
  - 確かめ1: `gh secret list --repo shingo-ops/salesanchor | grep -c SMOKE_E2E_DEVICE_TOKEN` が 1。
  - 確かめ2（数だけ・PO の `!`）: db の入れ物で `SELECT count(*) FROM public.user_trusted_devices WHERE user_id = 87 AND created_via = 'cli' AND revoked_at IS NULL` が 1。入れ物の名前は `docker ps --format '{{.Names}}'` で先に確かめる（db の名前は【未確認】）。2以上なら、古い行を取り消すかを PO に聞く。
- 切替の前の数え直し（PO の `!`・数だけ）: 「有効で、前にログインしたことがあり、いつもの機械も、生きている更新の組も無い人」の数。
  `SELECT count(*) FROM public.users u WHERE u.is_active AND u.last_login IS NOT NULL AND NOT EXISTS (SELECT 1 FROM public.user_trusted_devices d WHERE d.user_id = u.id AND d.revoked_at IS NULL) AND NOT EXISTS (SELECT 1 FROM public.auth_refresh_tokens t WHERE t.user_id = u.id AND t.revoked_at IS NULL AND t.expires_at > now())`
  - 2026-11-01 の見込みは1人（design.md §7）。この数を PO への完了報告に書く。
- GO: 危険 PR（deploy.yml を含む）。発行は「PO の委任に基づく Claude Opus 発行」。条件は全部そろうこと:
  - B-0 の確かめ1・2 が両方合格。
  - CI の必須 checks が緑。新しく起動した審査役（reviewer・model opus）の最後の行が `VERDICT: APPROVE on <sha40> PR #N`。
  - 締切まで3時間以上ある（反映は前回12分。残りが3時間未満なら、締切を直す依頼を出し直す）。
  - 直前のバックアップの確認（deploy.yml の Pre-deploy DB backup）。
- マージ後: デプロイの run が success で、終わった時刻が締切より前であることを確かめる。締切より後に終わったら、すぐ §6 で off に戻す（締切を過ぎた状態で enforce を続けない）。

## 5. 受入

| # | 基準 | 確かめ方 | 誰が |
|---|---|---|---|
| B1 | 3ファイルに足しただけ | 手順6 の git diff --stat | 実装役 |
| B2 | YAML が壊れていない・.env の形の検査に外れ0 | 手順7・8 | 実装役 |
| B3 | CI の必須 checks が緑 | gh pr checks | Opus |
| B4 | 本番の backend が enforce と締切を読んでいる | PO の `!`: `docker exec astro-webapp-backend-1 printenv AUTH_DEVICE_APPROVAL` が enforce。締切は `printenv AUTH_DEVICE_BOOTSTRAP_CUTOFF` が渡した値と同じ（どちらも秘密ではない） | Opus（PO の `!`） |
| B5 | 点検が止まらない | 反映後に prod-ui-check を手動で1回流し、画面点検と速さの記録の両方が緑 | Opus |
| B6 | 点検の人のログインで許可依頼が作られていない | PO の `!`（数だけ）: 反映後の auth_events の user87 の reason='device_approval_required' が0件 | Opus（PO の `!`） |
| B7 | 締切より前に反映が終わった | デプロイの run の終わった時刻 < 締切 | Opus |
| 段C | K1〜K9・W11 | design.md §6 の表。このカードの範囲外（段C のカードで行う） | — |

## 6. 戻し方

- 一番早い戻し方: deploy.yml の `AUTH_DEVICE_APPROVAL='enforce'` を `'off'` にする PR を出して反映する。off はログインの止め方が今と同じ（D11）。表と印は残るので、データは消えない。
- 急ぐとき（PO の判断）: 本番の .env の AUTH_DEVICE_APPROVAL を off にして backend を作り直す。次のデプロイで deploy.yml の値に戻るので、同じ日に上の PR も出す。
- 戻した後にもう一度 enforce にするときは、締切を新しい固定値にする PR を出す（design.md §7）。
- 点検だけが落ちるとき（B-0 の値の間違い）: B-0 をやり直して秘密を上書きする。古い印は管理画面の機械の一覧から取り消す。

## 停止と報告

- BLOCKED: <理由>（§3 の外れ・origin/main にカードが無い・想定外の差分）
- NEEDS_DECISION: <決めてほしいこと>（締切の値が無い・形が違う）
- DONE: 枝名・最後のコミットの sha40・§3 の (a)〜(e) の結果・手順6〜9 の出力（生のまま・上限付き）。秘密の値は出さない。

END OF CARD
