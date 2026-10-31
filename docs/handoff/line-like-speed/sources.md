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
- 画面の作り調べ（cse_01W47tdgY3KhiNJUGR9J6FFJ）: DONE。ただし get_run_log の報告が途中で切れ、分類は Sonnet 自身が「おおよそ」と書いた → 同じ基準 8c6f52813 で数え直した。数え方はリポジトリの docs/handoff/line-like-speed/u1-count.py、結果は recon.md §4 U1（誰でも流し直せる）。
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

## D. 写しを捨てるまでの時間（30 分）の根拠の調べ（2026-10-31・PO「30分の根拠は？」への調べ）

調べ方: 手元の WebSearch・WebFetch で原文を開いて数字を確かめた。論文 PDF は文字に直して該当の文を読んだ。数字は原文のまま。原文で確かめられない数字は使わない。

### D1 人の行動（論文・数値あり）: Obendorf・Weinreich・Herder・Mayer「Web Page Revisitation Revisited」CHI 2007 pp.597-606
- 出典: https://vsis-www.informatik.uni-hamburg.de/getDoc.php/publications/280/chi2007-newformat.pdf
- 5W2H: 誰=25 人の利用者（ドイツ・オランダ中心、16 人が計算機科学の人）／何=ブラウザの操作を記録／いつ=1 人 52〜195 日（2007 年発表。記録した年はまだ確かめていない）／どこ=普段の仕事の環境／なぜ=同じページへ戻る行動を調べる／どうやって=記録ソフトで 137,272 回のページ表示を記録／どれだけ=下の数字
- 数字（原文）: 戻った回のうち「over 50% of all revisits occurred within 3 minutes」。1 時間以内が 72.6%（1 人ごとには 50.0%〜83.9%）。1 時間〜1 日が 12%。1 日〜1 週間が 7.8%。それより後が 7.6%。
- 数字（原文）: アクセス記録の分析では「a timeout of 30 minutes」を目安に使うことが多い。Catledge と Pitkow は、ページを開く間の平均 9.3 分に標準偏差の 1.5 倍を足して 25.5 分とした。
- 著者の注意（原文）: 間の時間は裾の長い分布なので「Any time-out value would have been an arbitrary point on this long tail」（どの時間で切っても恣意的になる）。
- 本件への使い方: 既定の 5 分では、3 分以内に戻る半分ほどしか拾えない。30 分は、アクセス記録で使われる目安の値と同じ長さ。30 分以内に戻る割合は、この論文の文章には載っていない（図からは読まない）。Sales Anchor の利用者で同じ割合になるかは、まだ確かめていない。

### D2 ブラウザ自身の作り（実物の値）: Chrome の「前のページをそのまま覚えておく仕組み」（back/forward cache）
- 出典: Chromium の content/browser/renderer_host/back_forward_cache_impl.cc（2025-09-05 の commit 24d9b663b774 の写し）: 「kDefaultTimeToLiveInBackForwardCacheInSeconds = 600」（10 分）。「Cache-Control: no-store」のページは「base::Minutes(3)」（3 分）。今の main の同じファイルは場所が変わって開けなかった（今の値はまだ確かめていない）。600 秒にした理由（crbug.com/1305878）はログインが要り、読めていない。
- 出典: web.dev「Back/forward cache」（2026-10-16 更新）: 「1 in 10 navigations on desktop and 1 in 5 on mobile are either back or forward」。覚えを捨てる理由は「to conserve memory」（記憶の節約）。
- 本件への使い方: ブラウザはページの全部（画面と動いている状態）を 10 分覚える。本件が覚えるのはデータだけなので、1 件あたりの記憶は小さい（量は段 3 で測る）。

### D3 成功・数値あり: Yahoo! JAPAN ニュース（web.dev 事例・2023-07-25 更新・Yuriko Hirota）
- 出典: https://web.dev/case-studies/yahoo-japan-news-bfcache
- 5W2H: 誰=Yahoo! JAPAN ニュースの開発チーム／何=前のページをブラウザが覚えておけるよう、邪魔していた 2 つ（unload の処理・no-store の指定）を外した／いつ=2023 年（2 週間の A/B 試験）／どこ=スマホとパソコンのウェブ／なぜ=戻ったときすぐ出すため／どうやって=直した組と直さない組に分けて比べた／どれだけ=下の数字
- 数字（原文）: 覚えが使われた割合 スマホ 0.04%→54.07%・パソコン 0.02%→47.30%。ページを見た数 スマホ +2.26%・パソコン +0.65%。広告の売上 スマホ +9.0%・パソコン +0.6%。人数は書かれていない。
- 成功要因: 戻った瞬間に前の画面が出るようになり、1 回の訪問で見るページが増えた（原文の説明）。
- 本件への使い方: 「戻った画面をすぐ出す」ことが使う量を増やした実測。覚える時間の長さを決める根拠にはならない。

### D4 失敗・数値あり: Next.js 13.4（vercel/next.js issue #42991）
- 出典: https://github.com/vercel/next.js/issues/42991 ・ https://nextjs.org/docs/app/api-reference/config/next-config-js/staleTimes
- 5W2H: 誰=Next.js を使う開発者／何=動くページを画面側で 30 秒覚え、その間はサーバーに聞かずに古い中身を出した／いつ=2022-11-16 起票・2023-08-16 閉じる／どこ=画面の移動／なぜ=速くするため／どうやって=画面側の覚え（Router Cache）／どれだけ=賛成 138・やり取り 280 件超。Next.js 15.0.0 で既定を 30 秒→0 秒に変えた（公式の版の表）
- 失敗要因: 覚えている間、取り直しをしなかった。覚える時間と「新しいかどうか」を同じ値で決めていた。
- 本件への使い方: 本件は覚えている間も、開くたびに必ず取り直す（staleTime 0）。覚える時間（30 分）は「新しさ」ではなく「捨てるまで」の時間だけに使う。

### D5 失敗・数値あり: ever-teams（ever-co/ever-teams PR #4790・2026-10-25）
- 出典: https://github.com/ever-co/ever-teams/pull/4790
- 5W2H: 誰=ever-teams の開発チーム／何=写しを捨てるまでの時間を 24 時間にした設定が、サーバー側の 1 回ごとの写しにも効いた／いつ=2026-10-25／どこ=本番のサーバー（画面を作る側）／なぜ=画面側で長く覚えるため／どうやって=全部の写しの既定を 24 時間にした／どれだけ=記憶が 1 時間に約 170 MiB 増え、約 18 時間で 110 Mi→3070 Mi（上限 3 GiB）。本番の 2 台が 12:56Z と 13:13Z に記憶切れで止まった。80 分で 24 時間の時計が 719 個残っていた。
- 失敗要因: 長い時間を、毎回新しく作る側（サーバー）にも当ててしまった。画面側の 24 時間は原因ではなく、そのまま残した（原文）。
- 本件への使い方: 本件はサーバーで画面を作らない（画面はブラウザだけで作る）。写しは 1 か所（QueryClient 1 個）だけ。それでも段 3 で画面側の記憶の量を測る。

### 使わなかったもの（数字の出どころが無い）
- Medium の記事「requests 60% fewer・initial load 44% faster」: 測り方と比べた元が書かれていない。
- 「gcTime を 5 分から 90 秒に下げる」記事（renderlog.in 2026-04-04）: 測った値が無く、本文と結論で 1 分と 90 秒が食い違う。
- Superhuman の「100ms の決まり」: 目標の値だけで、得られた成果の数字が無い（K1 の 0.1 秒と同じ向きの参考にとどめる）。

### まとめ（事実と未確認を分ける）
- 事実: 人が同じページへ戻るのは半分以上が 3 分以内、72.6% が 1 時間以内（D1・25 人）。ブラウザは前のページを 10 分覚える（D2）。アクセス記録では 30 分が目安の値（D1）。
- 事実: 長く覚えた失敗は、取り直さなかった（D4）か、サーバー側で覚えた（D5）ときに起きた。本件の作りはどちらでもない。
- 未確認: Sales Anchor の利用者が何分で戻るか。30 分覚えたときの画面側の記憶の量。
