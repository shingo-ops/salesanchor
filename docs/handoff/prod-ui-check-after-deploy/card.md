# 実装カード: 本番の画面点検を配備の後にも回す（2026-11-08）

- 設計: `docs/handoff/prod-ui-check-after-deploy/design.md`（§4 が変更の正本）・recon.md
- 承認: PO の選択「1. この進め方で設計を始める」（2026-11-07）と委任「PRマージ、デプロイまで完走させてくれ」。設計の審査の結果は §6 に記録する。
- 実装役: クラウドの Sonnet。発行: Claude Opus。

## 1. やること（これだけ）

1. `nginx/nginx.conf:96` を design §4-1 のとおり 1 行だけ変える。
2. `.github/workflows/prod-ui-check.yml` を design §4-2 (1)〜(5) のとおり変える。
3. `tests/prod-check/prod-ui.spec.ts` を design §4-3 のとおり変える。
4. `.claude-pipeline/active-work.d/release-prod-ui-check-after-deploy-design.md` の備考に「実装 push 済み」を足す。

ADR-1051・ADR-1053 の改訂と recon・design は Opus が済ませた。触らない。

## 2. 触らないもの

- `.github/workflows/deploy.yml`・`.github/workflows/workflow-lint.yml`・`tests/prod-check/` の spec 以外（fixtures.ts・login.ts・settle.ts・page-speed*）・`nginx/nginx.conf` の 96 行以外・`frontend/src/` の全部・`docs/adr/`。

## 3. 手順（1 手順 1 コマンド）

1. `git fetch origin main release/prod-ui-check-after-deploy-design`
2. `git rev-parse origin/release/prod-ui-check-after-deploy-design` が指示の 40 桁と同じこと（違えば BLOCKED:）
3. `bash scripts/new-worktree.sh release/prod-ui-check-after-deploy-design`（--claude なし。origin/main から作られる）。失敗したら BLOCKED:
4. 作られた worktree で `git switch -C release/prod-ui-check-after-deploy-design origin/release/prod-ui-check-after-deploy-design`（手元の枝を設計の枝の先へ合わせる。クラウドでは merge が使えないため）。続けて `git rev-parse HEAD` が手順 2 の 40 桁と同じこと（違えば BLOCKED:）
5. 実装前の確かめ（design §4-2 末尾・§4-3 末尾の各項目）を実物で行い、結果を返事に書く。食い違いがあれば実装せず NEEDS_DECISION:
   - Context7 で GitHub Actions の `workflow_run`（workflows は名前・types completed・branches・conclusion）を確かめる。使えなければ公式資料 docs.github.com を直接読む。
   - `frontend` で `npm ci` の後、`node_modules/@fullcalendar/core/package.json` の版と `internal-common.js` の `injectStyles(` と `fcicons` の行を示す。
6. 変更 1〜4 を Edit で行う。
7. 確かめ（Mac ではなくクラウドで流す）:
   - `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/prod-ui-check.yml'))"` が通る
   - `cd frontend && npx tsc --noEmit -p ../tests/prod-check/tsconfig.json` があればそれ、無ければ `npx playwright test --config tests/prod-check/playwright.config.ts --list`（リポジトリの根で `./frontend/node_modules/.bin/playwright`）で S10・S11・S12 が一覧に出る（本番には繋がない。--list だけ）
   - `grep -n -i -E "psql|sqlalchemy|DATABASE_URL" tests/prod-check/prod-ui.spec.ts` が 0 件
   - `git diff origin/main --stat` が design §3 の対象ファイルだけ
8. commit（1 つ）: `feat(prod-check): run prod UI check after each deploy and add inventory, lead detail, schedule checks`。最後の行は `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`。
9. `git push origin release/prod-ui-check-after-deploy-design`（早送りだけ。force は禁止）

## 4. 禁止

- PR 作成・マージ・本番 URL へのアクセス・本番や DB への接続・通知の送信。rebase・force・reset・stash・pull・checkout -B・merge。`git switch -C` は手順 4 の 1 回だけ許す（それ以外は禁止）。
- 設計に無い変更・提案。見張りに止められたら言い換えず BLOCKED:。迷ったら NEEDS_DECISION:。

## 5. 返事

1 行目 `DONE <push した 40 桁>` か `BLOCKED: 理由` か `NEEDS_DECISION: 理由`。2 行目から手順 5 と 7 の結果（コマンドと出力の要点）。全体 1200 字以内。

## 6. 設計の審査の記録

- 1 回目（クラウド・claude-opus-5-5、HEAD b7673c396、2026-11-07T23:54Z）: REVISE。(1) workflow_run の書き方○ (2) 6.1.22 でも字形を差し込む○（`internal-common.js:113-114`） (3)× (4) CSP の影響○ (5)×。
  - 指摘 1（必須）: 予定表は `/shifts` を呼び `shifts.view` が要る → 点検用の人は持っている（`checker-perms.txt:2`）。design §4-3 に事実として追記。コードの変更なし。
  - 指摘 2（必須）: 在庫表・リード詳細のエラーは `.error-message` → S10・S11 に `.error-message` 0 件を追加。
  - 指摘 3（推奨）: 予定表は `.schedule-loading`・`.schedule-error` → S12 をこの 2 つに替えた。
  - 指摘 4（推奨）: workflow_run の GITHUB_SHA は main の最後 → design §6 のリスクに 1 行追加。
- 2 回目（クラウド・claude-opus-5-5、HEAD b804766e8、2026-11-08）: REVISE。(1)× (2)○ (3)○ (4)○ (5)× (6)○ (7)△。
  - 指摘 1（必須）: shifts の行は `shifts.py:55-56`（83-84 は誤り）→ design §4-3 を直した（手元の Read で 55-56 を確認）。
  - 指摘 2（推奨）: 在庫表に `sa-loading-block` は無く、S10 の件数 0 は何も見ていない → `InventoryPage.tsx:634` の `data-testid="inventory-loading"` を確かめ、S10 を `toBeHidden()` に替えた。design §4-3 に理由を追記。
  - 指摘 3（推奨）: クラウドの決まりで merge は使えない → 手順 4 を `git switch -C` ＋ 40 桁の照合に替え、§4 の禁止と揃えた。
- 3 回目: （再審査の結果をここに書く）

END OF CARD
