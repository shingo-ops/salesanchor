# 2つ目の作業（請求先フォーム）直し1 — 実装カード

- 対象 PR: #5137（ブランチ `release/viewer-billing-form-bin2`）
- 親カード: docs/handoff/viewer-customer-sheet/card-bin2.md（PO 実装承認 2026-11-04「1」）
- 起票: Claude Opus（設計担当）2026-11-05。直しは親カードの範囲内（新しい機能・表・API・画面の見た目は足さない）
- 理由: CI の確かめが1件止まった（§1-A）。審査（reviewer opus・HEAD c941421cc）も同じ点で REQUEST_CHANGES。あわせて審査の指摘 §1-B を直す。

読んだ節（docs/handoff/design-partner-card-ops/guards/）: 00-common.md・03-file.md・04-worktree.md・10-executor.md。

## §1 直す2件（観測事実）

| # | どこで見えたか | 観測 | 原因 |
|---|---|---|---|
| A | CI「Frontend lint & custom checks」（job 126777615449） | `❌ ページサイズチェック FAILED … frontend/src/pages/super-admin/ViewerAccountsPage.tsx: 1043 行 (上限: 1000 行)` | `frontend/scripts/check-page-size.js` の `ADMIN_LIMIT = 1000`。請求先の区切り（約130行）を足して上限を超えた |
| B | 審査役の指摘 | `backend/tests/test_viewer_billing_form_pg.py` の `test_billing_fields_live_in_one_table_only` が、親カード §3-6 の指す design §3-2 の数え方（4列すべてを持つ public の表が1つだけ／名簿と配信先に7列のどれも無い）と違う | 試験の書き方の食い違い。中身（請求先の列がこの表だけにある）は審査役が差分で確認済み |

Opus の決定（2026-11-05）:
- A は、請求先の区切りを新しい部品ファイルに切り出して直す。上限の数・ベースライン・除外の注記は変えない（決まりを緩めない）。部品の置き場は既存の `frontend/src/pages/super-admin/components/`（同じ形の部品が40本以上ある）。
- B は、試験を design §3-2 の数え方に書き直す。

## §2 触るファイル（これ以外は触らない）

| ファイル | 変えること |
|---|---|
| `frontend/src/pages/super-admin/components/ViewerBillingSection.tsx` | 新規。§3-A の部品 |
| `frontend/src/pages/super-admin/ViewerAccountsPage.tsx` | 請求先の区切りを部品の呼び出しに置き換える（§3-A） |
| `backend/tests/test_viewer_billing_form_pg.py` | `test_billing_fields_live_in_one_table_only` だけ書き直す（§3-B） |

触らない: `frontend/scripts/check-page-size.js`、各種ベースライン json、`ViewerAccountsPage.test.tsx`（期待値も差し替えも変えない）、locales（キーを足さない・消さない）、backend/app、migrations、そのほか全部。

## §3 変更前後

### A. 請求先の区切りを部品にする

変更前（ViewerAccountsPage.tsx。HEAD c941421cc）:
- 型 `BillingProfile`・`BillingFormSendResult`（`interface StatusChangeResult` の後ろ）
- 状態 `billingSendResult`・`billingSendError` と、`detailId` の useEffect の中の `setBillingSendResult(null); setBillingSendError("");`
- `billingQuery`・`billing`・`billingLoading`・`billingLoadError`（`useApiQuery<BillingProfile | null>` の塊）
- `sendBillingForm`（`/send-billing-form` を呼ぶ関数）
- 詳細の Drawer の中の `<div className="form-row" data-testid="viewers-detail-billing">` から、その閉じ `</div>` までの塊

変更後:
- 上の5つをすべて `components/ViewerBillingSection.tsx` に移す。中身（文・分かれ道・data-testid・使う部品・t() のキー・API の道）は一字も変えずに移す。
- 部品の受け取る値（props）は次の6つだけ:
  ```
  viewerId: number;            // detail.id
  active: boolean;             // detail.status === "active"
  running: boolean;            // ページの running
  setRunning: (v: boolean) => void;
  renderCopyButton: (key: string, value: string) => React.ReactNode;  // ページの copyButton
  formatDate: (value: string | null) => string | null;                // ページの formatDate
  ```
  （formatDate を渡すのは、ページの関数を部品から import すると部品とページが互いを読む形になるため）
- 部品の中では `const { t } = useTranslation();` と `const f = "superAdmin.viewers";` を使う（ページと同じ前置き）。`useApiQuery` の道は `` `/super-admin/viewers/${viewerId}/billing-profile` ``、`enabled: true`。
- ページ側は、元の塊があった場所に次の1つを置く:
  ```
  <ViewerBillingSection
    key={detail.id}
    viewerId={detail.id}
    active={detail.status === "active"}
    running={running}
    setRunning={setRunning}
    renderCopyButton={copyButton}
    formatDate={formatDate}
  />
  ```
  `key={detail.id}` で、開く人が変わると部品の状態（送った結果・エラー）が消える。これで useEffect の中の2行の初期化は要らなくなるので消す。
- `ApiError` など、移した後にページで使わなくなった import は lint の指摘に従って外す。ページで使い続けるものは残す。
- 切り出し後のページの行数が 1000 行以下であること（`wc -l`）。

### B. 「1か所だけ」の試験（design §3-2 の数え方）

変更後（関数名と `@needs_ci_pg`・`_prepare_billing` の使い方は今のまま）:
```
    # 請求先の4列をすべて持つ public の表は viewer_billing_profiles だけ
    cur.execute(
        "SELECT table_name FROM information_schema.columns "
        "WHERE table_schema = 'public' "
        "AND column_name IN ('bill_to_name', 'contact_name', 'invoice_email', 'party_type') "
        "GROUP BY table_name HAVING count(DISTINCT column_name) = 4"
    )
    assert {r[0] for r in cur.fetchall()} == {"viewer_billing_profiles"}
    # 名簿と配信先には請求先の7列のどれも無い
    cur.execute(
        "SELECT table_name, column_name FROM information_schema.columns "
        "WHERE table_schema = 'public' "
        "AND table_name IN ('viewer_accounts', 'tcg_distribution_targets') "
        "AND column_name IN ('party_type', 'bill_to_name', 'contact_name', 'postal_code', "
        "'address', 'phone', 'invoice_email')"
    )
    assert cur.fetchall() == []
```
- 先に、この試験の DB に `public.viewer_accounts` と `public.tcg_distribution_targets` があることを確かめる（`SELECT to_regclass('public.tcg_distribution_targets')` が NULL でない）。どちらかが無ければ、無い表の名前を書いて止まる（停止。表を作る行を足さない）。

## §4 手順

1. ブランチは既にある。`git fetch origin && git switch release/viewer-billing-form-bin2 && git pull --ff-only`。HEAD がこのカードのコミットを含むことを `git log --oneline -3` で確かめる。
2. `./scripts/dev/executor-preflight.sh || exit 1`。クラウドで gh の名義の確かめだけで落ちたときは、出力を報告に書いて続ける。ほかの理由で落ちたら止まる（停止）。
3. §3 の A と B を変える。ファイルは Write/Edit で書く。sleep で待たない。
4. 確かめ（生出力をファイルに残す）:
   - `cd frontend && node scripts/check-page-size.js` が exit 0、`wc -l src/pages/super-admin/ViewerAccountsPage.tsx` が 1000 以下
   - `cd frontend && npm run check:all` が exit 0（ページサイズで止まって流れなかった後続の確かめも含めて全部流す）
   - `cd frontend && npx tsc --noEmit -p .`
   - `cd frontend && npx vitest run src/pages/super-admin/ViewerAccountsPage.test.tsx src/pages/viewer/BillingForm.test.tsx src/pages/super-admin/ViewerTemplatesPage.test.tsx`
   - backend は scratchpad の下に `python3.12 -m venv` を作り `-r requirements.txt -r requirements-dev.txt` を入れて、PG のある環境なら `python -m pytest tests/test_viewer_billing_form_pg.py -q`。PG が無くて skip になったら「流せなかった（skip）」と書く（通ったと書かない）。
   - `git diff --stat` で §2 の3ファイル（とカード以外）だけが変わっていること
5. コミット1つ（文: `fix: split billing section out of viewer accounts page and align one-table test`）。`git log --oneline -1` で確かめる。push は `git push origin release/viewer-billing-form-bin2` 単独。
6. PR を作らない・マージしない・PR 本文を変えない。`scripts/dev/validate-pr-body.sh` は流さなくてよい（PR 本文は変えないため）。

## §5 想定分岐

- 移した後に vitest の既存の期待値が通らない → 試験名と出力を書いて止まる（期待値・差し替えを変えない）。
- `npm run check:all` が、ページサイズ以外の確かめで、今回の3ファイルが原因で落ちる → 直してよいのは §2 の3ファイルの中だけ。§2 の外を直さないと通らないなら止まる（停止）。
- `npm run check:all` が今回の3ファイルと関係ない所で落ちる（main にもある赤） → 出力を報告に書いて続ける。
- 切り出しても 1000 行を超える → 止まって行数を報告する（ほかの塊を勝手に移さない）。
- §2 以外のファイルを変えたくなった → 止まって報告。

## §6 受入条件

| 基準 | 検証方法 |
|---|---|
| ページの行数が上限以内 | `wc -l` が 1000 以下・check-page-size.js が exit 0・CI「Frontend lint & custom checks」pass |
| 見た目と動きが変わらない | ViewerAccountsPage.test.tsx の差分0行・vitest 失敗0 |
| 移した中身が同じ | 部品の中の data-testid・t() のキーの集合が、移す前の塊と同じ（レビューで照合） |
| 決まりを緩めていない | check-page-size.js・ベースライン json の差分0行 |
| 「1か所だけ」の試験が design §3-2 の数え方 | 試験の差分・PG のある CI（pytest）で pass |
| CI | #5137 の確かめが全件 pass（GO記録の検査は Opus が本文に書くまで赤のまま） |

## §7 報告

- 受領確認: 受け取ったら最初に「カード 便2 直し1 を受領」と1行書く。
- 報告は docs/handoff/viewer-customer-sheet/fix-bin2-report.md に書き、同じコミットに入れる。手順4の各命令の終了コードと最後の20行。流せなかった確かめは「流せなかった」と書く。
- 停止したときは、止まった手順・観測した出力・判断してほしいことの3点を書き、最後の行を `NEEDS_DECISION:` または `BLOCKED:` で終える。
- 終えたときの最後の行は 「DONE: 」の後に push した HEAD の40桁。

END OF CARD
