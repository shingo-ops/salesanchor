# 直し1（2回目）報告 — viewer sheet link bin1

カード 便1 直し1 を受領。実行: 2026-11-04（クラウド）。HEAD 開始点 ca8087dec（一致を確認）。

## 変えたもの（カード §2 の4ファイルのみ）

- `.github/workflows/migration-test.yml`: PUBLIC_SQL に `public.viewer_accounts` の最小定義を足した（migration が参照するのは `id` のみ＝外部キー。列は足りた）
- `backend/tests/test_tcg_review_sheet_svc.py`: `_target()` に `deliverable: True, reason: None`
- `ViewerAccountsPage.tsx`: シート読み込みを `useApiQuery` / `useInvalidateApi` に置換
- `ViewerAccountsPage.test.tsx`: `useAuth` 差し替え・`queryClient.clear()`・§3-D2 のとおり `/tcg/distribution/targets` の分かれ道（`return [];`）を分かれ道の無かった6か所の差し替えに追加。`expect(` の増減は0

`loading-clear-baseline.json` 変更なし・`loading-clear-exempt` 不使用・active-work.d は commit していない。

## preflight

`./scripts/dev/executor-preflight.sh`: 終了コード 1（FAIL）。落ちた点は gh 関連のみ（クラウドで想定）:
- [1/3] api.github.com に到達不可
- [2/3] gh active account が shingo-cc でなく、`gh auth switch` も失敗
- [3/3][4/4] は OK
カード §4-2 の許容どおり、出力をここに書いて続行。

## 確かめ（終了コードと最後の出力）

| 命令 | 終了コード | 結果 |
|---|---|---|
| pytest 5ファイル（`-q`） | 1 | **106 passed, 6 skipped**。失敗0。終了コード1の理由はカバレッジ下限の判定のみ（`FAIL Required test coverage of 60% not reached. Total coverage: 30.37%`。5ファイルだけを流したため） |
| vitest ViewerAccountsPage.test.tsx | 0 | Test Files 1 passed / Tests 37 passed (37) |
| `node scripts/check-loading-clear.js` | 0 | `✅ loading-clear: 基準どおり（51 ファイル・69 行）` |
| `npx tsc --noEmit -p .` | 2 | 4件のエラー、いずれも触っていないファイル（下記）。ViewerAccountsPage 系のエラーは0 |
| eslint（対象2ファイル） | 0 | 出力なし |
| `grep "setSheetLoading(\|setSheet(\|loadSheet"` | 1（0件） | 一致なし＝期待どおり |

tsc の4件（最後の出力そのまま）:
```
src/features/tcg-sold-out/soldOutApi.ts(3,45): error TS2307: Cannot find module '../../api/generated/schema' ...
src/pages/inventory/OwnInventoryPage.tsx(11,33): error TS2307: Cannot find module '../../api/generated/schema' ...
src/pages/super-admin/components/SoldOutResultsPanel.tsx(34,27): error TS7006: Parameter 'line' implicitly has an 'any' type.
src/pages/super-admin/components/SoldOutResultsPanel.tsx(34,33): error TS7006: Parameter 'index' implicitly has an 'any' type.
```
原因は生成ファイル `src/api/generated/schema` がこの環境に無いこと（推測。生成手順は流していない）。このカードの範囲外のため触っていない。

## 流せなかった確かめ

- `tests/test_tcg_distribution_viewer_link_pg.py` の6件は SKIPPED（理由: `Disposable CI PostgreSQL service required`）。使い捨て PostgreSQL をこの環境で立てていないため**流せなかった**。通ったとは言えない。CI で確かめること。
- migration-test.yml の実DB実行（§1-A）も流せなかった（CI 側）。

END
