# 1つ目の作業（シートのひも付け）直し1 — 実装カード

- 対象 PR: #5131（ブランチ `release/viewer-sheet-link-bin1`）
- 親カード: docs/handoff/viewer-customer-sheet/card-bin1.md（PO 実装承認 2026-11-04「１」）
- 起票: Claude Opus（設計担当）。直しは親カードの範囲内（新しい機能・表・API は足さない）
- 理由: CI の確かめで3件止まった（下の §1）。審査（reviewer opus）も同じ3件で REQUEST_CHANGES
- 改訂: 2026-11-05 Opus。1回目の実行（2026-11-04 15:27 UTC）が §5 の分岐で NEEDS_DECISION 停止した（vitest 5件 `sheetQuery.data?.find is not a function`）。Opus が §3-D2 で決めた。あわせて card-lint の形式（読んだ節・受領確認・停止・END OF CARD）を足した。

読んだ節（docs/handoff/design-partner-card-ops/guards/）: 00-common.md・03-file.md・04-worktree.md・10-executor.md。

## §1 止まった3件（観測事実）

| # | 止まった確かめ | 観測（CI の記録） | 原因 |
|---|---|---|---|
| A | マイグレーションSQL 実行テスト（実DB） | `relation "public.viewer_accounts" does not exist`（20261104_220000_add_tcg_distribution_targets_viewer_account_id.sql 21行目） | `.github/workflows/migration-test.yml` の最小の土台（PUBLIC_SQL）に viewer_accounts が無い |
| B | pytest（SQLite + PostgreSQL RLS） | backend/tests/test_tcg_review_sheet_svc.py の5件が `KeyError: 'deliverable'` | 試験の `_target()`（197〜199行目）が、配信判定で足した `deliverable`・`reason` を持たない |
| C | Lint & Dark Mode Check / Frontend lint | frontend/scripts/check-loading-clear.js が `setSheetLoading(true)` の増加を検出 | ADR-1054: 読み込みは `useApiQuery` を使う決まり |

## §2 触るファイル（これ以外は触らない）

| ファイル | 変えること |
|---|---|
| `.github/workflows/migration-test.yml` | PUBLIC_SQL の `public.tcg_distribution_targets` の最小定義（919〜934行目付近）の直前に `public.viewer_accounts` の最小定義を足す |
| `backend/tests/test_tcg_review_sheet_svc.py` | `_target()` の dict に `"deliverable": True, "reason": None` を足す |
| `frontend/src/pages/super-admin/ViewerAccountsPage.tsx` | シートの読み込みを `useApiQuery` に置き換える |
| `frontend/src/pages/super-admin/ViewerAccountsPage.test.tsx` | `useAuth` の差し替えと `queryClient.clear()` を足す（標準部品が動くため） |
| `docs/handoff/viewer-customer-sheet/review-opus.md` | 触らない（Opus が書く） |

触らない: `frontend/scripts/loading-clear-baseline.json`（数を増やさない）、`loading-clear-exempt` の注記（使わない）、`.github/workflows/workflow-lint.yml`、migrations/、backend/app/、そのほか全部。

## §3 変更前後

### A. migration-test.yml

変更前（抜粋）:
```
          -- public.tcg_distribution_targets: 20260921_110000_pipeline_tables_public.sql で本番作成済み。
          ...
          CREATE TABLE IF NOT EXISTS public.tcg_distribution_targets (
```

変更後（直前に足す。字下げは周りと同じ空白10個）:
```
          -- public.viewer_accounts: 20261016_150000_add_viewer_accounts.sql で本番作成済み。
          --   20261104_220000_add_tcg_distribution_targets_viewer_account_id.sql が外部キーで参照するため、
          --   前提として最小定義を登録する（id の型は本物と同じ BIGSERIAL）。
          CREATE TABLE IF NOT EXISTS public.viewer_accounts (
              id         BIGSERIAL   PRIMARY KEY,
              email      TEXT        NOT NULL,
              line_name  TEXT        NOT NULL,
              status     TEXT        NOT NULL,
              created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
              updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
          );
          -- public.tcg_distribution_targets: 20260921_110000_pipeline_tables_public.sql で本番作成済み。
```
足す前に、変更対象の migration が viewer_accounts のどの列を参照するかを `grep -n viewer_accounts migrations/20261104_220000_add_tcg_distribution_targets_viewer_account_id.sql` で読む。上の列で足りなければ止まって報告する（推測で列を足さない）。

### B. test_tcg_review_sheet_svc.py

変更前:
```
    return {"id": f"id-{name}", "name": name, "spreadsheet_id": "sid", "sheet_name": "在庫集計",
            "review_sheet_name": review_sheet_name, "is_active": True}
```
変更後:
```
    return {"id": f"id-{name}", "name": name, "spreadsheet_id": "sid", "sheet_name": "在庫集計",
            "review_sheet_name": review_sheet_name, "is_active": True,
            "deliverable": True, "reason": None}
```
根拠: backend/app/services/tcg_distribution_svc.py の `_target_select()`（`SELECT x.*, (x.reason IS NULL) AS deliverable`）。

### C. ViewerAccountsPage.tsx

変更前（203〜222行目と 252行目付近）:
- `useState` の `sheet`・`sheetLoading`・`sheetLoadError` と `loadSheet`（useCallback）、`detailId` が変わると `loadSheet` を呼ぶ useEffect、保存後の `await loadSheet(detail.id)`。

変更後:
```
import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";
...
  const sheetQuery = useApiQuery<SheetItem[]>("/tcg/distribution/targets", { enabled: detailId !== null });
  const invalidateApi = useInvalidateApi();
  const sheet = detailId === null ? null : (sheetQuery.data?.find(r => r.viewer_account_id === detailId) ?? null);
  const sheetLoading = detailId !== null && sheetQuery.isPending;
  const sheetLoadError = sheetQuery.isError;

  useEffect(() => {
    setSheetModalOpen(false);
    setSheetFormError("");
  }, [detailId]);
```
保存の後:
```
      setSheetModalOpen(false);
      await invalidateApi(["tcg", "distribution", "targets"]);
```
- `useState` の `sheet`・`sheetLoading`・`sheetLoadError` と `loadSheet` は消す。`setSheet(`・`setSheetLoading(`・`setSheetLoadError(` が0件になること。
- 表示部分（`{sheetLoading ? <LoadingBlock /> : sheetLoadError ? ... : sheet ? ...}`）は変えない。
- `useCallback` を他で使っていなければ import から外す（lint の指摘に従う）。

### D. ViewerAccountsPage.test.tsx

手本: frontend/src/pages/schedule/SchedulePageCache.test.tsx の 14〜19行目と 82行目。
- `vi.mock("../../contexts/AuthContext", () => ({ useAuth: () => ({ user: { uid: "user-a" } }) }));` を足す。
- `import { queryClient } from "../../lib/query/apiQuery";` を足し、`beforeEach` の先頭で `queryClient.clear();` を呼ぶ。
- 既存の試験の期待値は変えない。保存後にシートが出直す試験は、`api.get` が2回目に保存後の中身を返すようにしてあればそのまま通るはず。通らなければ、通らない試験名と出力を報告して止まる（期待値を緩めない）。

### D2. 試験の差し替えの返す形を本物に合わせる（Opus 決定 2026-11-05）

観測事実:
- 本物の一覧は配列を返す。`backend/app/routers/tcg_distribution.py` の `list_distribution_targets` が `svc.list_targets(db)` を返し、`backend/app/services/tcg_distribution_svc.py` の `list_targets` は `-> list[dict]`。
- ViewerAccountsPage.test.tsx の `api.get` 差し替えのうち、`/tcg/distribution/targets` の分かれ道を持たないものは、最後の `return { items: [] };` を配列の代わりに返している。旧コードは try/catch で読み込み失敗の表示に落ちていたので、試験は通っていた。

決めたこと:
- 直すのは試験の差し替えの方。`/tcg/distribution/targets` の分かれ道を持たない差し替えすべてに、`return { items: [] };` の直前へ `if (path === "/tcg/distribution/targets") return [];` を1行足す。
- 画面に `Array.isArray` の防御は足さない。本物が返さない形への防御になり、本物と違う形の差し替えを隠すため。
- 期待値（expect）は1つも変えない。足すのは差し替えの分かれ道だけ。
- 足した後も落ちる試験があれば、試験名と出力を書いて止まる（停止）。

## §4 手順

1. `bash scripts/new-worktree.sh release/viewer-sheet-link-bin1 --claude` は使わない（ブランチは既にある）。`git fetch origin && git switch release/viewer-sheet-link-bin1 && git pull --ff-only` で最新にする。HEAD が 2ea3b2fe1 以降で、このカードのコミットを含むことを確かめる。
2. `./scripts/dev/executor-preflight.sh || exit 1`。クラウドでは gh の認証が無いため、gh の名義の確かめだけで落ちることがある。その1点だけで落ちたときは、出力を報告に書いて続ける。ほかの理由で落ちたら止まる（停止）。
3. §3 の A〜D と D2 を変える。
4. 確かめの準備: backend は `python3.12 -m venv` で作業用の場所（scratchpad の下）に作り、その pip で `-r requirements.txt -r requirements-dev.txt` を入れる（pytest は requirements-dev.txt にある）。
5. 確かめ（全部の生出力をファイルに残す）:
   - `cd backend && python -m pytest tests/test_tcg_review_sheet_svc.py tests/test_tcg_distribution_viewer_link_pg.py tests/test_line_import_admin.py tests/test_distribution_rows_builder.py tests/test_tcg_distribution.py -q`
   - `cd frontend && npx vitest run src/pages/super-admin/ViewerAccountsPage.test.tsx`
   - `cd frontend && node scripts/check-loading-clear.js` が exit 0
   - `cd frontend && npx tsc --noEmit -p .` と `npx eslint src/pages/super-admin/ViewerAccountsPage.tsx src/pages/super-admin/ViewerAccountsPage.test.tsx`
   - `grep -n "setSheetLoading(\|setSheet(\|loadSheet" frontend/src/pages/super-admin/ViewerAccountsPage.tsx` が0件
6. コミット1つ（文: `fix: viewer sheet link CI (migration base, test fixture, useApiQuery)`）。`git log --oneline -1` でコミットがあることを確かめる。push は `git push origin release/viewer-sheet-link-bin1` 単独。
7. PR を作らない・マージしない・PR 本文を変えない。

## §5 想定分岐

- §3-A で migration が viewer_accounts の別の列を参照している → 止まって報告。
- vitest で既存の期待値が通らない → 止まって報告（試験名と出力）。
- check-loading-clear.js が ViewerAccountsPage 以外で落ちる → このカードの範囲外。止まって報告。
- §2 以外のファイルを変えたくなった → 止まって報告。

## §6 受入条件

| 基準 | 検証方法 |
|---|---|
| 土台に viewer_accounts がある | migration-test.yml の差分に `CREATE TABLE IF NOT EXISTS public.viewer_accounts` が1件 |
| 5件の KeyError が消える | 手順5の pytest が失敗0 |
| 読み込み表示が標準部品になる | `setSheetLoading(` が0件・check-loading-clear.js が exit 0・baseline の差分0 |
| 画面の試験が通る | vitest 失敗0 |
| CI | #5131 の確かめが全件 pass（GO記録の検査は Opus が本文に書くまで赤のまま） |
| 期待値を変えていない | 試験ファイルの差分で `expect(` を含む行の増減が0 |

## §7 報告

- 受領確認: 受け取ったら最初に「カード 便1 直し1 を受領」と1行書く。
- 報告は docs/handoff/viewer-customer-sheet/fix1-report.md に書く。手順5の各命令の終了コードと最後の20行。流せなかった確かめは「流せなかった」と書く（推測で通ったと書かない）。
- 停止したときは、止まった手順・観測した出力・判断してほしいことの3点を書き、最後の行を `NEEDS_DECISION:` または `BLOCKED:` で終える。
- 終えたときの最後の行は 「DONE: 」の後に push した HEAD の40桁。

END OF CARD
