# 設計の審査記録: 全画面を LINE のような使い心地にする

審査役: クラウドの Claude Opus（claude-opus-5-5・読むだけ）。設計者も同じ Claude Opus なので、独立した第二者の審査ではない。
対象: docs/handoff/line-like-speed/design.md・recon.md・sources.md・u1-count.py・docs/adr/ADR-1054-screen-data-cache.md

| 回 | 対象 | 判定 | 主な指摘 | 直した commit |
|---|---|---|---|---|
| 1〜2 | 初版〜第 3 版 | REVISE | 行番号のずれ、数え方を誰でも流し直せる形にする（u1-count.py） | 1b42a24ef より前 |
| 3 | 第 3 版 | REVISE | recon の古い行 2 つ、ルートに無い画面 2 本、リポジトリに無い資料への参照、段 5 の境目、合図と取り直す写しの決め方、ADR の起案者 | 1b42a24ef |
| 4 | 1b42a24ef | REVISE | 検索の条件を path に足す画面で取り直しが当たらない、ADR の下書きが無い、sources.md が無い資料を指す | 5783c4ff9 |
| 5 | 5783c4ff9 | REVISE | path の途中に id が入る画面 20 ファイルで取り直しが当たらない（数え直しの命令は 42 ファイル） | c86332062 |
| 6 | c86332062 | APPROVE | 直さなくても進められる注記 2 点（区切り関数を 1 つにする・頭の言葉を複数持てる） | cc60aab61 で書き足し |

## 6 回目で確かめられたこと
- TanStack Query の先頭一致（query-core/src/utils.ts の partialMatchKey）は配列を要素ごと、object を部分一致で比べる。invalidateApi(uid, ["companies"]) は「?」つきの path（CompaniesPage.tsx:211）にも、id 入りの path（useCompanyDetail.ts:61）にも当たる。
- 行番号（App.tsx:151-152・api.ts:241・AuthContext.tsx:30/53/90/105/167・selfAuth.ts:67・useRealtimeRefresh.ts:56）は origin/main と一致。
- K1 の「30 分以内に戻った時」は、ADR-1054 の採用の時に PO が確かめる点として残す。

## 残っていること
- PO による ADR-1054 の採用（Proposed → Accepted）と実装の承認。どちらも未。
