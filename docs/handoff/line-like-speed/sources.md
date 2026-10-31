# 根拠の写し（審査 3 回目の指摘で /tmp から本線へ移した・2026-10-31）

## A. 部品の公式説明書（元 lib-docs.md）
Context7: 今月の回数切れ（"Monthly quota exceeded"）→ 起動指示の代替手順で公式文書を直接読んだ。

## TanStack Query（tanstack.com/query/latest）
- guides/caching: staleTime 既定 0（すぐ古い扱い）・gcTime 既定 5 分。新しく開いた画面は「手元の中身をすぐ返し、裏で取り直す」（"immediately returns the available cached data while ... being run in the background"）。
- guides/important-defaults: 古い中身は「画面を開いた・窓に戻った・回線が戻った」ときに取り直す。失敗は 3 回まで間を空けて送り直す。中身が同じなら同じ参照を保つ（structural sharing）。
- reference/QueryClient: clear() は一時保存を全部消す。invalidateQueries() は古い印を付け、開いている画面は取り直す。removeQueries() は消す。resetQueries() は初期状態へ戻す。
## npm（npm view, 生の値は下の C）
- @tanstack/react-query 5.105.0（最終更新 2026-10-26・peer react ^18||^19）
- swr 2.5.1（peer react ^16.11〜^19）

## B. 外部事例（元 external-cases-cache.md）

クラウドの調べ2本の結果:
- 画面の作り調べ（cse_01W47tdgY3KhiNJUGR9J6FFJ）: DONE。ただし get_run_log の報告が途中で切れ、分類は Sonnet 自身が「おおよそ」と書いた → 同じ基準 8c6f52813 で手元の script で数え直した（r2-raw.txt）。
- 外部事例（cse_01W47tdeQtQiCizm6mAy5ZAP）: BLOCKED。クラウドの通信の許可リストで dev.to・basedash.com・upd.dev などが止まった → 手元で WebSearch・WebFetch で確かめた（下）。

## X1 成功・数値あり: ShipSecAI/studio PR #298
- URL: https://github.com/ShipSecAI/studio/pull/298（開 2026-02-17・マージ 2026-02-18）
- Who: ShipSecAI studio の開発チーム / What: Zustand の画面ごとの取得を TanStack Query へ（13 領域・11 store 削除・-2,444 行）
- Why: 画面に入るたびの取り直しと重複通信 / How: useQuery に集約、キャッシュを画面間で共有
- How much（PR 本文の実測）: Execute タブの API 呼び出し「10 (3 duplicate pairs)」→「8 (1 duplicate)」-20%、DOM「2,091」→「1,444」-31%、画面移動時「None (refetch on every mount)」→「0 extra requests on navigation」、CLS 0.00 維持
- 適用限界: 規模・計測環境が違う。後から rebase の直しが要った（一括移行は衝突しやすい）。

## X2 型（数値なし）: tkdodo「Using WebSockets with React Query」
- URL: https://tkdodo.eu/blog/using-web-sockets-with-react-query（2021-06-06）
- 要点: 合図を受けたら invalidateQueries で取り直す形を推す。合図で必ず取り直す前提なら staleTime を大きく（Infinity）してよい。
- 適用: ADR-1016 の SSE 合図と同じ形。数値は無いので成功の証明には使わない。

## X3 失敗: TanStack/query issue #28
- URL: https://github.com/TanStack/query/issues/28（2019-11-09）
- 何が: 「different user logs in and for a moment sees previous user's data」（別の人がログインすると一瞬前の人の中身が見える）
- 対処: 0.3.7（2019-11-11）でキャッシュを消す関数を追加。コメントで「staleTime が 0 でないと消すだけでは取り直さない」指摘。
- 適用: K5 の危険そのもの。ログアウト・ログイン切替で必ず消す。

## X4 失敗: TanStack/query issue #2157
- URL: https://github.com/TanStack/query/issues/2157（2021-04-20）
- 何が: clear() が「doesn't inform active observers」（開いている画面に知らせない）→ 画面に古い中身が残る
- 回避: cancelQueries() → resetQueries() → mutation の写しも消す、の順。
- 適用: ログアウト時の消し方をこの順にする。

## X5 指針: tkdodo「Practical React Query」
- URL: https://tkdodo.eu/blog/practical-react-query（2020-11-16・2023-10-21 更新）
- 要点: staleTime の既定は 0。v5 の refetchOnWindowFocus は visibilitychange で動く。useQuery の結果を画面の手元の状態に写し替えない（写しを二重に持たない）。
- 適用: PO 条件「データを分散させない」と同じ向き。

## C. npm view の生の値（元 npm-libs.txt）
```
{
  "version": "5.105.0",
  "time.modified": "2026-10-26T09:31:29.532Z",
  "peerDependencies": {
    "react": "^18 || ^19",
    "@types/react": "^18 || ^19"
  }
}
{
  "version": "2.5.1",
  "peerDependencies": {
    "react": "^16.11.0 || ^17.0.0 || ^18.0.0 || ^19.0.0"
  }
}
```
