# design: 全画面を LINE のような使い心地にする

作成: 2026-10-31 Claude Opus（設計担当）。
**状態**: KGI は PO 承認済み（2026-10-31 選択「1」）。§3 以降は設計案（第 6 版・設計の審査 6 回目 APPROVE（2026-10-31 クラウドの Claude Opus。同じ AI による審査で、独立した第二者の審査ではない）・注記 2 点を書き足し済み。7 回目の評価（クラウドの Claude Fable 5.1）REVISE の 5 点を直し済み）。§3 以降と ADR-1054 は PO 承認済み（2026-10-31 21:55 JST 選択「1」＝30 分のまま採用し、作り始める）。
現在地: docs/handoff/line-like-speed/recon.md

## 1. KGI（PO 承認済み 2026-10-31「1」）

PO の言葉: 「LINEみたいな使い心地は出来る？」（意味は「押した瞬間に開く速さ」）。承認時の条件（原文）:「推測は禁止して事実確認を怠らずに確実性を重視して最も効果があり、現状把握の粒度が細く、精度が高いエビデンスを確立して安全に進めてくれ。また配線とDBのSSOTは遵守してデータを分散させることは禁止。フロントエンドのパーツもデザイントークンとデザインシステム を遵守して、金型登録のないハードコードを禁止する。」

| # | 基準 | 合格の線 | 検証方法 |
|---|---|---|---|
| K1 | 前に開いた画面に戻ったとき、前の中身が出るまで | 0.1 秒以内（135 画面。同じログインの中で 30 分以内に戻った時。30 分を過ぎたら K2 で判定） | 毎朝の記録（prod-ui-check の速さの段）に「戻ったときの秒」を足して測る |
| K2 | 初めて開く画面で、中身が出るまで | 2 秒以内（PO 2026-10-31「3」） | 毎朝の記録の今の秒 |
| K3 | 押してから、画面に何か変化が出るまで | 0.1 秒以内 | 毎朝の記録に「押してから最初の変化までの秒」を足して測る |
| K4 | ほかの人が変えた中身が、開いている画面に出るまで | 5 秒以内（在庫表も含む・§5 の PO 決定 2026-11-02「1」。在庫表は 1.5 秒＋0〜1 秒のずれ＋読み込み 最大 1.8 秒で 約 4.3 秒）。合図のある画面の内訳は、まとめて待つ 1.5 秒（useRealtimeRefresh.ts:13 の REALTIME_DEBOUNCE_MS）＋取り直しの通信 最大 1.4 秒（初めて開いた時のいちばん遅い秒＝recon §3 を当てはめた値。取り直しの秒そのものは段 5 で測る。api.ts の送り直しが起きた時は含まない）。合図の無い画面は、段 5 で合図を足すまで、開いたままでは変更が出ない（開き直す・タブに戻ると出る） | tenant 001 で別の人として変更し、開いている画面に出るまでを測る |
| K5 | ログアウト後・別の会社で、前の人の中身が見える | 0 件 | ログアウト→別の人でログイン、会社切替のあとに前の中身が出ないかを試験で確かめる |
| K6 | PO のスマホで触って「LINEみたい」と感じる | ○ | PO が 3 画面を触って判定 |

## 2. 守ること（PO 条件の言い換え）
- データの正本はサーバーの DB だけ。画面が手元に残す中身は「表示のための写し」で、合図（ADR-1016）と時間で必ず取り直す。写しを正本として書き戻したり、別の保存先に持ったりしない。
- 画面の部品はデザイントークンと金型（components/）だけで作る。新しい見た目の部品は金型に登録してから使う（ADR-067・ADR-144）。
- 分からないことは推測で埋めず、recon の未確認に書いて確かめるか PO に聞く。

## 3. 作り方（PO 承認済み・2026-10-31 21:55 JST 選択「1」）

### 3-1. 今と変えた後
| | 今（recon §2・§4 U1） | 変えた後 |
|---|---|---|
| 画面を開く | 毎回 useEffect で api.get、終わるまで中身を消して LoadingBlock（96 本中 62 本・recon §4 U1） | 前に取った写しがあれば**すぐ出し**、裏で必ず取り直して差し替える。写しが無い初回だけ LoadingBlock |
| 取り直す時 | 中身を消す | 中身を残したまま、既存の金型 Spinner（sm）を小さく出す |
| ほかの人の変更 | 合図を受ける画面は 3 か所 | 合図（ADR-1016）で写しを取り直す。合図の無い画面は、開いた時・タブに戻った時に必ず取り直す（開いたままでは段 5 まで出ない） |
| ログアウト | メモリの session を消すだけ（selfAuth.ts:67） | 同じ時に写しも全部消す |

### 3-2. 部品
- 写しの置き場: TanStack Query（@tanstack/react-query 5 系）を 1 つ入れる。新しい部品の追加なので ADR を起こす。起案は設計担当（Claude Opus）で、下書きを本件 PR に同梱し（docs/adr/ADR-1054-screen-data-cache.md）、PO の採用（2026-10-31 21:55 JST 選択「1」）で Accepted にした。選んだ理由と比べたもの → §3-6。
- 置き場は 1 つだけ: frontend/src/lib/query/ に QueryClient を 1 個作り、App.tsx の AuthProvider の内側・BrowserRouter の外側に QueryClientProvider を置く（App.tsx:151-152 の間）。ほかの場所で QueryClient を作らない。
- 取り方は 1 つだけ: 同じ場所に `useApiQuery(path)` を作り、中で今の `api.get`（frontend/src/lib/api.ts:241）を呼ぶ。通信・再送・401 の扱いは api.ts のまま（二重にしない）。TanStack 側の再送は 0 にする（api.ts が既に 3 回送り直すため。既定 retry 3 のままだと最大 16 回になる）。
- 写しの名前（key）: `["api", user.uid, ...segments, { query }]`。useApiQuery が path を最初の「?」で分け、「?」より前を「/」で区切った言葉を 1 つずつ並べ、最後に「?」より後ろ（無ければ空文字）を `{ query }` の形で置く。例: `/companies?status=a` → `["api", uid, "companies", { query: "status=a" }]`、`/companies/5` → `["api", uid, "companies", "5", { query: "" }]`。path が動く画面が 2 種類あるため（審査 4 回目・5 回目。`git grep -lE 'api\.get(<[^>]*>)?\(\s*`[^`]*\$\{' origin/main -- frontend/src/pages` で 42 ファイル。うち「?」で条件を足す形 22 ファイル＝例 frontend/src/pages/companies/CompaniesPage.tsx:211、path の途中に id が入る形 20 ファイル＝例 frontend/src/pages/company-detail/useCompanyDetail.ts:61 `/companies/${id}`）。user は useAuth()（AuthContext.tsx:167）、uid は AuthUser.uid（AuthContext.tsx:30）。自社ログインでは同じ人なら同じ user を返す（AuthContext.tsx:53）ので、同じ人のまま写しが消えることはない。user が null の間は取りに行かない（enabled: false）。人が変われば別の写しになる（X3 対策の二重目）。
- 写しを正本にしない: staleTime 0（既定のまま）＝写しは「出すだけ」で、画面を開くたび・タブに戻るたびに必ずサーバーから取り直す。写しはメモリだけに持ち、ブラウザの保存に書かない（persist の追加はしない）。使われない写しは 30 分で捨てる（gcTime を 30 分に設定。既定の 5 分だと、5 分を過ぎて戻った画面が初回と同じ形になるため）。10 分へ下げる線は §3-7 のメモリの行に書く。下げた時は K1 の「30 分以内に戻った時」も「10 分以内」に変わる。useQuery の結果を useState に写し替えない（X5）。
- 取り直す写しの決め方（審査 3 回目の指摘）: 各画面は、自分が読むデータの頭の言葉（例 `["companies"]`。id も条件も含まない）を画面のファイルの中の 1 つの定数に置き、useApiQuery に渡す path もその定数から組み立てる。取り直しは lib/query の `invalidateApi(uid, ["companies"])`（中身は `queryClient.invalidateQueries({ queryKey: ["api", uid, "companies"] })`）を呼ぶ。TanStack の先頭一致は配列の要素ごとに比べるので、`/companies?…` の一覧も `/companies/5` の詳細も、条件や id が何であっても全部取り直される。id 1 件だけを取り直したい時も、同じ関数に `["companies", "5"]` を渡せば足りる。path を区切る関数は lib/query に 1 つだけ置き、useApiQuery と invalidateApi の両方がそれを使う（先頭や途中の「/」でできる空の言葉は捨てる）。頭の言葉を 2 つ以上読む画面（例: ダッシュボード）は、定数を言葉の数だけ持ってよい（審査 6 回目の注記）。段 1 の試験で「条件つきの写し 2 つと id 入りの写し 2 つが、1 回の取り直しで 4 つとも取り直される」「別の頭の言葉（例 `contacts`）の写しは取り直されない」を確かめる。合図の名前と path の対応を集めた新しい表は作らない（写しの決め方が 2 か所に分かれるため）。
- 書き込みの後: 今の api.post/patch/delete はそのまま。成功したら、上の決め方でその画面の写しを取り直す（自分の変更は SSE の合図では来ないため・useRealtimeRefresh.ts:56 の origin 判定）。
- 合図: useRealtimeRefresh(topics, reload) の reload に、上の取り直しを渡す（ADR-1016 決定7 の形のまま）。合図の名前の表は今のまま backend/app/realtime/topics.py が正本で、画面側の frontend/src/lib/realtime/topics.ts は手書きの写し（backend/tests/test_realtime_topics.py:129-133 が同じ集合かを確かめる）。
- ログアウト・人の入れ替わり: QueryClientProvider は AuthProvider の内側なので、AuthProvider（AuthContext.tsx:90・:105）の中からは写しに触れない。そこで frontend/src/lib/query/ に小さな部品 QueryAuthSync を作り、QueryClientProvider の直下に置く（画面は描かない）。この部品が useAuth().user?.uid を見て、前の uid と今の uid が違ったら（null になった時を含む）、cancelQueries → 各写しの Query.reset()（開いている画面に知らせる・取り直さない）→ queryClient.clear() → getMutationCache().clear() の順に消す（X4 の順。resetQueries は active の写しを前の人の key のままその場で取り直すので使わない。段 1 カード審査 v1 項目 3・stage1-card.md V1-5）。user の変化は 3 つの道すべてから届く: Firebase の onAuthStateChanged（:90）、自社ログインの subscribeSession（:105）、api.ts の 401 → expireSession → notify（selfAuth.ts:67-71）→ :105 の道。
- 見た目: 新しい金型は作らない（金型の新規登録＝ADR-144 §4 の PO 許可は不要）。初回は今の LoadingBlock 金型（class sa-loading-block）。取り直し中は中身を残し、既存の金型 Spinner（components/loading/Spinner.tsx・size "sm"・class sa-spinner。部品の説明に「while a table refetches」と書かれた用途そのもの）を、各画面の既存の見出し・道具欄の中に置く。新しい CSS は書かない。置き場に新しい CSS が要ると分かった画面は、その便を止めて PO に聞く（ADR-144 §4）。
- Spinner は測る道具の「読み込み中の印」の目印（settle.ts の LOADING_SELECTOR）に入っていないので、K1 の「前の中身が出た」を邪魔しない。目印の一覧は変えない。
- 在庫表の生の印（InventoryPage.tsx:631-639 の文字だけの div）は、在庫表を移す便で Spinner に置き換える（今は金型違反・recon §4 U1）。

### 3-3. 触らない範囲
- backend・DB・migrations・deploy.yml・本番 scripts は触らない。
- 段 5 の境目（審査 3 回目の指摘）: 段 5 は画面のまとまりごとに別便・別審査。1 便の中身は (1) backend/app/realtime/topics.py で、そのまとまりの書き込みルートを NO_SIGNAL_ROUTES から WRITE_ROUTE_TOPICS へ移す（新しい合図の名前を足すときは同じ便で frontend/src/lib/realtime/topics.ts にも足し、test_realtime_topics.py:129-133 を緑にする）、(2) その画面に useRealtimeRefresh を足す、の 2 つだけ。DB・migrations・deploy.yml・本番 scripts は段 5 でも触らない。段 5 の各便の設計は、段 4 までが終わってから別に書いて審査に出す。
- api.ts の通信の中身・ログインの仕組み・閲覧ページ（viewer/）は触らない。
- 画面の見た目・文言は変えない（i18n キーも増やさない。印の金型に文言が要るときは ja/en 同時に足す）。

### 3-4. 段階（1 便 1 PR・変更→反映→測定→次）
| 段 | 中身 | 合格の線 |
|---|---|---|
| 0 | 測る仕組みだけ足す（§3-5 の画面の中の記録係）。U1 の数は段 0 の前に u1-count.py を流し直して確かめる。「135 画面とファイルの対応表」を作る（毎朝の記録の画面の一覧 × App.tsx のルート → 画面のファイル。部品の中の画面はその親のファイル）。今の値を基準として 1 回記録 | 135 画面の K1 と、道すじが固定の 94 画面の K3 の基準値が記録に出る（K3 は横のメニューにある画面は押して、無い画面はアプリの中の切り替えの命令から測る・stage0-card.md V0-3）。対応表の 135 行すべてにファイルがある。本番に繋がない試しのページで、記録係の時刻と書き換えた時刻の差が 4 件すべて 0.05 秒以内（動画は作らない・ADR-1051:25。stage0-card.md V0-1）。「A の画面の部品が描かれた」の見分け方は stage0-card.md V0-2 に書き、その版が審査に通った。段 0 は 0a（記録係と基準）と 0b（対応表と u1-count.py の流し直し）に分け、両方の受入が合格してから段 2 へ進む |
| 1 | 置き場・取り方・ログアウトで消す、の土台だけ（画面はまだ変えない）＋ K5 の試験 | 試験: A でログイン→画面を開く→ログアウト→B でログイン→A の中身が 0 件。単体試験で retry が 1 回の失敗で 4 回以内。単体試験で `invalidateApi(uid, ["companies"])` 1 回で、条件つき 2 つ・id 入り 2 つの写しが 4 つとも取り直され、`contacts` の写しは取り直されない |
| 2 | 試しに 3 画面だけ変える（ChannelMastersPage・CompaniesPage・ほか 1 つ。使う頻度は PO に聞かず、中身を消す形の代表を選ぶ） | 3 画面で K1 ≤0.1 秒、K2 ≤2 秒、取り直した後の中身が DB と一致（tenant 001） |
| 3 | 残りを 10 画面ずつ。直す相手は段 0 の対応表に出たファイルだけ（ルートの無い BadgesPage・BuddyPage は対応表に出なければ直さない・recon §4 U1）。u1-count.py の分け方は 中身を消す 62・このファイルで取らない 24・ほかの印 7・印なし 3。三項 58 本は便ごとに 1 本ずつ形を確かめてから変える | 毎便の後に毎朝の記録で K1・K2 が悪化していない |
| 4 | 見張り: 「読み込み中に中身を消す形」の数を数える検査を CI に足し、数が増えたら赤（減るのは可）。段 3 の最後で 0 にして固定 | CI に検査があり、わざと 1 本足すと赤 |
| 5 | K4: 合図の無い画面の書き込みに合図を足す（画面のまとまりごと・backend 便） | tenant 001 で別の人として変更→開いている画面に 5 秒以内（内訳: まとめて待つ 1.5 秒＋通信 最大 1.4 秒） |

#### 3-4-1. 段 0a の基準値（stage0-card.md の A5〜A10 の回）
出どころ: prod-ui-check の手動の回（2026-11-01 00:52:38 JST に測定・main d6568972a）の要約の表 135 行を、設計担当が表から数えた（2026-11-01 Claude Opus）。
- A5〜A10 の受入はすべて合格。A5 は試しのページで 4 件中 4 件合格・いちばん大きい差 3.8 ms。A6 は「測れた」135 行が、戻った時の秒に数 128・訳 7 を持つ。kind "" の 94 行は、押した秒に数 92（メニューを押した 5・命令で切り替え 87）と訳 2（/design-preview・/design-system の「5 秒で変化なし」）を持ち、欠けは 0。A7 は「時間切れで未測定」0 行で、速さの段は 9.6 分。K1 の 10 秒切れは 1（/inventory）。A8 は、要約に道すじと数だけがあり、画面の文字は無い。A9 はメモリ 18 MB。A10 は、戻った時・押した時を測るあいだの API の数 496。
- K1 の基準（403 なし 94 画面）: 中央 0.17 秒・9 割 0.25 秒・最大 0.87 秒（?section=condition-defs-master）。0.1 秒以内は 8 画面。403 ありの 34 画面（断りの画面が戻る秒）は中央 0.20 秒・最大 0.35 秒。訳の 7 画面の内訳: /inventory「10 秒で見分けられず」、/admin/products/:id/edit と /templates「行き先と同じ形」、/design-system と carrier 3 画面「中身の場所が無い」。→ K1 は今は不合格。段 1〜3 で直す相手。
- K3 の基準: 測れた 92 画面すべて 0.1 秒以内で、最大 0.02 秒。メニューを押した 5 画面（/inventory・/・/lead-chat・/quotes・/schedule）はすべて 0.02 秒。→ K3 は今の時点で合格。段 1〜3 で悪くしないことを毎朝の記録で見る。
- メモリと読み取りの量の基準: JS ヒープ 18 MB（測り終えた時）。戻った時・押した時を測るあいだの API の数は 496。段 2 以降でこの 2 つを並べて書き、写しを持つことで増えた分を見る（§3-7）。
- V0-1 の記録係の重さ（今の秒）: 記録係を入れる前の回（2026-10-31 13:37:34 JST・main 55be483a6）は 135 画面の中央 0.2 秒・最大 1.4 秒（/inventory）・2 秒超 0。入れた後の上の回は中央 0.2 秒・最大 1.1 秒（/inventory）・2 秒超 0。2 回は時刻が違う（昼と深夜）ため、差の 0.3 秒を記録係のせいとは決めない。悪化は見えない、とだけ記録する。

#### 3-4-2. 段 0b の対応表と u1-count.py の流し直し
- 対応表は docs/handoff/line-like-speed/screen-file-map.md（作り方 docs/handoff/line-like-speed/screen-map.py・基準 origin/main 1896879cb）。135 行すべてにファイルがある。ファイルの列に出る画面のファイルは 87 本。ルートの無い BuybackByProductPage は /buyback-prices の中身として表に出るので、段 3 で /buyback-prices と一緒に直す。BadgesPage・BuddyPage は表に出ないので、段 3 で直さない。
- u1-count.py の流し直しは 中身を消す 62・このファイルで取らない 24・ほかの印 7・印なし 3 で、recon §4 U1 と同じ。

#### 3-4-3. 段 1 の作業指示書
- 段 1（写しの置き場・取り方・利用者が変わったら消す、の土台と K5 の試験）の作業指示書は docs/handoff/line-like-speed/stage1-card.md。段 1 は画面を変えない。本物の画面での K5 は段 2 の受入で確かめる（stage1-card.md V1-1）。

#### 3-4-4. 段 1 の本番の受入（stage1-card.md §5 の A7・A8・2026-11-01 Claude Opus が確かめた）
- A7 は合格。段 1 は 2026-11-01 03:55:41 JST に main へ入った（merge e77c3a436）。本番への反映（Deploy to VPS run 41231757253）は 04:03 JST に success。本番の app.salesanchor.jp は HTTP 200 を返した。本番の中身 /assets/main-BJmK6VJ2.js には TanStack Query の文字列 "No QueryClient set" が 1 件ある。本番を Playwright で開くとログイン画面が出た。ブラウザの誤りの記録は /api/v1/auth/refresh の 401 の 1 件だけで、これはログイン前の正常な返事。TanStack 由来の誤りは 0 件。
- A8 は合格。今回の回は prod-ui-check run 41232464221（main 8a2baf838・2026-11-01 04:18:19 JST に測定）。基準は §3-4-1 の回（run 41215836246）。
  - 同じだった値: 画面の点検 8 passed、測った画面 135（403 なし 100・403 あり 35・未測定 0）、K2 の最大 1.1 秒（/inventory）、2 秒を超えた画面 0、戻った時の秒を測れた画面 128、押した秒を測れた画面 92（メニュー 5・命令 87）、K3 の最大 0.02 秒、JS ヒープ 18 MB。
  - 下がった値: K1 の最大（403 なし）は 0.87 秒から 0.63 秒（/admin/products）。?section=condition-defs-master は 0.17 秒。測るあいだの API の数は 496 から 489。
  - 記録係の精度は 4 件中 4 件合格で、いちばん大きい差は 4.9 ms（線は 50 ms）。
  - 0.1〜0.2 秒増えた行: /crm → /crm/leads 0.3→0.5、/admin/products 0.5→0.6、me/permissions だけを読む画面の多くが 0.1→0.2。同じ行の「いちばん遅い API」の秒も同じだけ増えた（/api/v1/countries 0.3→0.5 など）。段 1 は画面のコードの通信を変えていない（e77c3a436 で useApiQuery を使う画面は 0）。増えた分は、同じ行のいちばん遅い API の秒の増えと同じ。原因は 1 回の比べでは決めない（表は 0.1 秒刻み）。悪化は 2 秒の線と K2 の最大では見えない、とだけ記録する。段 2 の受入のときに毎朝の記録と並べてもう一度見る。
- 段 2 の作業指示書は、この受入の後に別の PR で出す。

#### 3-4-5. 段 2 の作業指示書
- 段 2（連絡手段・取引先・仕入先の 3 画面を、写しを先に出して裏で取り直す形に変える）の作業指示書は docs/handoff/line-like-speed/stage2-card.md。3 つ目の画面を仕入先にした理由と、本番の 5 行の基準値は stage2-card.md V2-1・V2-2。本物の画面での K5 は stage2-card.md の P2 と T12 で確かめる（本番で 2 人のログインは使わない・V2-8）。

#### 3-4-6. 段 2 の本番の受入（stage2-card.md §5 の B5〜B7・2026-11-01 Claude Opus が確かめた）
- B7 は合格。段 2 は 2026-11-01 14:39 JST に main へ入った（merge 755a8d9ec）。本番への反映（Deploy to VPS run 41277770162）は 14:46 JST に success。続く main c88f09846 の反映（run 41277926057）も 14:51 JST に success。本番 https://app.salesanchor.jp/ は開き、ブラウザの誤りの記録に TanStack 由来の誤りは 0 件。
- B6 は合格。本番の読むだけの道（ADR-1024）で tenant_001（tenants.id 1・test-corp）を数えた。仕入先は is_active が true の行が 1 件（SP-26070 点検用仕入先）。取引先は 1 件（QA入金日テスト株式会社）。連絡手段は is_active が true の行が 6 件。生の出力は /tmp/CC報告ファイル/stage2-b6/（設計担当の手元・リポジトリには入れない）。画面の件数はまだ確かめていない。P3（書いた後に取り直した行が出る）と B3（backend を変えていない）を根拠にする。
- B5 は不合格（5 行中 4 行で K1 が 0.1 秒を超えた）。今回の回は prod-ui-check run 41278215691（main c88f09846・反映中の待ち 10 分の後、14:56 JST から測定）。基準は stage2-card.md V2-2（run 41232464221）。
  | 行 | 初めて開く秒（K2） | 戻った時の秒（K1）基準→今回 | 判定 |
  |---|---|---|---|
  | /suppliers | 0.2 以下 | 0.20→0.15 | × |
  | /management-center/suppliers | 0.2 以下 | 0.23→0.27 | × |
  | /crm/companies | 0.2 以下 | 0.25→0.22 | × |
  | /admin/channel-masters | 0.2 以下 | 0.19→0.01 | ○ |
  | /management-center/channel-masters | 0.2 以下 | 0.22→0.25 | × |
  - 5 行の 403・5xx は 0 件。K2 は 5 行とも 2 秒以下。
  - ほかの 130 行: K2 の最大は 1.1 秒（/inventory）・2 秒を超えた画面 0 件で、段 1 の受入（§3-4-4）と同じ。悪化なし。
  - 測るあいだの API の数は 489（段 1）から 574 に増えた。理由はまだ確かめていない。測定の最中の 15:07 JST に、別の変更（main b3193f11a）の本番反映（run 41279538190）が始まっていた。これが数に響いたかもまだ確かめていない。
- B5 の 4 行が遅い理由（観測した事実と、まだ確かめていない仮説を分ける）:
  - 事実: 権限を読む部品 usePermissions（frontend/src/hooks/usePermissions.ts）は、写しの置き場を使わず、画面を開くたびに useState と useEffect で /me/permissions を取り直す。
  - 事実: 遅かった 4 行は、どれも権限で出し分ける部分を描く。仕入先の画面はボタン（SuppliersPage.tsx:134・:139・:144・:240・:241）。取引先の画面はボタン（CompaniesPage.tsx:362・:414・:417）。外側の枠では、管理センターの横の項目（ManagementCenterPage.tsx:30・:37-54）と顧客の枠のタブ（CustomerHubPage.tsx:27・:33-44）。
  - 事実: 速かった /admin/channel-masters は、画面（ChannelMastersPage.tsx）も外側の枠（AdminHubPage.tsx）も usePermissions を使わない。同じ画面でも管理センターの中の行は遅い。5 行中 5 行がこの分け方に合う。
  - 仮説（まだ確かめていない）: /me/permissions が返るまで権限で出す部分が無いので、記録係の構造の印が最初の時と合わない。このため K1 は /me/permissions の通信の秒になる。確かめ方: usePermissions を写しの置き場に載せた後に同じ 4 行を測り、0.1 秒以下になるか見る。
  - usePermissions を使う画面のファイルは 53 本ある（`git grep -l 'usePermissions()' origin/main -- frontend/src ':!*.test.*'`）。段 2 のカードの範囲（3 画面）の外なので、直すには新しい作業指示書と PO の判断が要る。

#### 3-4-7. 権限の写しの作業指示書
- 段 2 の受入で K1 が 0.1 秒を超えた 4 行（§3-4-6）の理由の仮説を確かめるため、権限を読む部品 usePermissions を写しの置き場に載せる。作業指示書は docs/handoff/line-like-speed/perm-cache-card.md。ほかの使い手は変えない理由と、ログインの前に描かれない根拠は perm-cache-card.md §0 P5・P6。K5 は perm-cache-card.md §4-B の 12 本目で確かめる。PO 選択「1」（2026-11-01）。
- 第 1 版の審査は REVISE（2026-11-01 クラウドの Opus）。試験の共通の準備（test-setup.ts）で写しを消す形は、ほかの 8 ファイル 52 本を落とした。このため第 2 版では、写しを消すのを usePermissions.test.ts の中だけにした。
- 次の段の課題: useApiQuery を使うほかの部品の試験ファイルでも、写しが同じファイルの次の試験に残り得る。試験の共通の準備で消す形は、api.ts が i18n を読み込む点を解いてから考える。

#### 3-4-8. 権限の写しの本番の受入（2026-11-01 Claude Opus が確かめた）
- 反映は合格。権限の写しは 2026-11-01 19:15 JST に main へ入った（merge c527abcdd）。本番への反映（Deploy to VPS run 41296672823）は 19:22 JST に success。本番 https://app.salesanchor.jp/ は 200 で開いた。
- 測定は prod-ui-check run 41297663070（main f8910e949・c527abcdd を含む）。19:32 JST に測った。測定の前に、ほかの本番反映が走っていないことを確かめた。
- §3-4-6 の 5 行は、5 行とも K1 が 0.1 秒以内になった。§3-4-6 の仮説（/me/permissions が返るまで構造の印が合わない）と合う。
  | 行 | 初めて開く秒（K2） | 戻った時の秒（K1）§3-4-6→今回 | 判定 |
  |---|---|---|---|
  | /suppliers | 0.2 | 0.15→0.02 | ○ |
  | /management-center/suppliers | 0.2 | 0.27→0.01 | ○ |
  | /crm/companies | 0.2 | 0.22→0.01 | ○ |
  | /admin/channel-masters | 0.2 | 0.01→0.01 | ○ |
  | /management-center/channel-masters | 0.2 | 0.25→0.01 | ○ |
  - 5 行の 403・5xx は 0 件。
  - 135 画面すべて測れた（403 なし 100・403 あり 35・測れなかった 0）。K2 の最大は 1.2 秒（/inventory）で、2 秒を超えた画面は 0 件。
  - 戻った時の秒を測れた画面は 128。測るあいだの API の数は 574（§3-4-6）から 462。減った理由はまだ確かめていない。
  - 生の要約は設計担当の手元の /tmp/CC報告ファイル/perm-cache/measure-5rows.txt（リポジトリには入れない）。
- 残り: この 5 行のほかには、K1 が 0.1 秒を超える画面が残る（例: / 0.63 秒・/admin/products 0.65 秒・/lead-chat 0.75 秒）。段 3 で直す相手。

#### 3-4-9. 運営者の判定を写しの置き場に載せる（2026-11-01 Claude Opus が設計）
- なぜ: §3-4-8 の後も、運営者の画面（/super-admin/ で始まる画面 14 行と、分析の決まりの画面の区切りの行）で、戻った時の秒（K1）が 0.16〜0.20 秒残る。これらの画面は、運営者かを確かめる部品が /me/permissions を毎回取り直し、返るまで読み込み中の印を出す。
- 何を: その部品を権限の写し（§3-4-7）と同じ写しの置き場に載せる。写しは 1 つのままで、データを 2 か所に持たない。
- 作業指示書: docs/handoff/line-like-speed/superadmin-cache-card.md。
- 受入: カードの §5 C1〜C5。/super-admin/ で始まる行すべての K1 が 0.1 秒以下になるかを、マージの後の毎朝の画面の記録で確かめる。

#### 3-4-10. 運営者の判定の写しの本番の受入（2026-11-01 Claude Opus が確かめた）
- C5 は合格。PR #4992 は 2026-11-01 23:16 JST に main へ入った（merge 21a141641）。本番への反映（Deploy to VPS run 41315373669）は 23:24 JST に success。本番 https://app.salesanchor.jp/ は 200 で開いた。
- 測定は prod-ui-check run 41316493378（main 8c3333a9b・21a141641 を含む）。23:33 JST に測った。先に始めた run 41316027273 は、台帳だけの本番反映（8c3333a9b）と重なったので止めた。その反映が 23:29 JST に success で終わった後に測り直した。
- C4 は合格。/super-admin/ で始まる行は 39 行（画面ごとの行 14・分析の決まりの区切りの行 25）。39 行すべてで K1 は 0.01〜0.02 秒になった（§3-4-8 の後は 0.16〜0.20 秒）。39 行の 403・5xx は 0 件。§0 P4 の仮説と合う。
  - §0 P4b で心配した「判定の後に自分の API を取る画面」も、K1 は 0.01〜0.02 秒だった（例: /super-admin/fx-rate 0.01・/super-admin/tcg-line-import 0.01）。
  - ほかの行は悪化していない。135 画面すべて測れた（403 なし 100・403 あり 35・測れなかった 0）。K2 の最大は 1.2 秒（/inventory）で §3-4-8 と同じ。2 秒を超えた画面は 0 件で §3-4-8 と同じ。
  - 戻った時の秒を測れた画面は 128。測るあいだの API の数は 462（§3-4-8）から 481。増えた理由はまだ確かめていない。
  - 生の行は設計担当の手元の /tmp/CC報告ファイル/superadmin-cache/measure-superadmin-rows.txt（リポジトリには入れない）。
- K5 は本番で 2 人のログインでは確かめていない（本番でパスワードを打たない決まり）。カードの C1 の 8 本目と、写しの名前に利用者が入り利用者が変わると消える作りで確かめた。
- 残り: K1 が 0.1 秒を超える画面がまだある（例: /lead-chat 0.72 秒・/ 0.59 秒・/admin/products 0.56 秒・/crm/leads 0.35 秒）。段 3 で直す相手。

#### 3-4-11. 最初の画面（/）の写し（2026-11-02 設計担当 Claude Opus）
- 2026-11-01 PO 選択「1」で、遅い 2 画面（最初の画面・会話の画面）を直して本番まで進める。変更は一度に 1 つにするため、最初の画面を先にする。会話の画面は別のカードにする。
- 原因（コードを読んで確かめた）: 最初の画面と 4 つの欄（数字の漏斗・優先の見込み客・今週の助言・成約の要因）は、写しの置き場を使わずに毎回取りに行く。そのため戻った時も 16 本が返るまで読み込み中の印が出る。
- 作業指示書: docs/handoff/line-like-speed/dashboard-cache-card.md（第 2 版。第 1 版のクラウド審査は REVISE で、試験の見本の path・1 本目の「7」を注文の数に・lint の警告 1 件・行番号 6 か所・保存後の取り直しが失敗した時の動き（P7 (5)）の 5 つを直した。第 2 版のクラウド審査は APPROVE on 25c6c9b68（2026-11-02 01:57 JST・カードどおりに変えて新しい試験 6/6 を 3 回・全部の試験 2017 passed・tsc 0・lint の警告 0→0・build 成功））。5 か所を写しの置き場に載せ、写しの置き場に数が変わる並びの取り方（useApiQueries）を 1 つ足す。受入はカードの §5 C1〜C5。結果はこの節の後に書き足す。

#### 3-4-11-a. 最初の画面の写しの本番の受入（2026-11-02 Claude Opus が確かめた）
- C5 は合格。PR #5000 は 2026-11-02 02:24 JST に main へ入った（merge 8c242f653）。本番への反映は 02:31 JST に success。
- C4 は 2 回とも合格。1 回目 prod-ui-check run 41332039643・2 回目 run 41334197486（測った日時 2026-11-02 03:01:58 JST）。
  - / の K1（戻った時の秒）は 1 回目 0.04 秒・2 回目 0.05 秒（§3-4-10 の後は 0.59 秒）。/ の 403・5xx は 2 回とも 0 件。2 回目の / は K2 0.7 秒・API の数 16・押した時の反応 0.03 秒。
  - ほかの行は悪化していない。2 回目は 135 画面すべて測れた（測れなかった 0）。K2 の最大は 1.2 秒（/inventory。1 回目は 1.3 秒）で、2 秒を超えた画面は 0 件。戻った時の秒を測れた画面は 128。測るあいだの API の数は 465（2 回とも）。
  - 生の行は設計担当の手元の /tmp/CC報告ファイル/dashboard-cache/measure-run41332039643.txt と measure-run41334197486.txt（リポジトリには入れない）。
- K5 は本番で 2 人のログインでは確かめていない（本番でパスワードを打たない決まり）。カードの C1 の試験と、写しの名前に利用者が入り利用者が変わると消える作りで確かめた。
- 残り: 2 回目で K1 が 0.1 秒を超える画面の例は /lead-chat 0.83 秒・/admin/products 0.74 秒・/crm/leads 0.39 秒・/crm/leads/:id/edit 0.38 秒。次は /lead-chat（§3-4-12）。

#### 3-4-12. 会話の画面（/lead-chat）の写し（2026-11-02 設計担当 Claude Opus）
- 2026-11-01 PO 選択「1」の 2 つ目。原因（コードを読んで確かめた）: 会話の画面は 1 つのフックが 4 つの取り方（会話の一覧・送り元のページの選び肢・選んだ会話のメッセージ・右のカルテ）を写しの置き場を使わずに持つ。そのため戻った時も返るまで読み込み中の印が出る。
- 作業指示書: docs/handoff/line-like-speed/lead-chat-cache-card.md（第 5 版）。4 つを写しの置き場に載せ、写しの置き場に写しを読み書きする道具（useApiCache）を 1 つ足す。取りに行く時と回数は今と同じ。受入はカードの §5 C1〜C5。結果はこの節の後に書き足す。

#### 3-4-12-a. 会話の画面の写しの本番の受入（2026-11-02 Claude Opus が確かめた）
- C1・C2 は合格。実装はクラウドの Sonnet（765cd26c8）。2 つの試験ファイル 17 passed を 3 回・全部の試験 182 ファイル 2029 passed / 0 failed・tsc 0・lint の警告 0・build 成功。PR #5002 の必須の確認 47 件 pass（落ち 0）。
- C3 は合格。PR #5002 の変更は §1 の 8 ファイルだけ（migrations/・deploy.yml・scripts/・backend は 0）。審査役（Claude Opus）が HEAD 765cd26c8 に APPROVE。
- C5 は合格。PR #5002 は 2026-11-02 05:11 JST に main へ入った（merge e05a64a60）。本番への反映は 05:17 JST に success。続く台帳の PR #5003（71f6b60df）の反映も 05:23 JST に success。
- C4 は合格。prod-ui-check run 41346462841（71f6b60df。e05a64a60 を含む。測った日時 2026-11-02 05:34:49 JST）。
  - /lead-chat の K1（戻った時の秒）は 0.04 秒（§3-4-11-a の 2 回目は 0.83 秒）。§0 P4 の仮説と合う。/lead-chat の 403・5xx は 0 件。API の数 6（7 以下）。K2 は 0.7 秒（前は 0.9 秒）・押した時の反応 0.03 秒。
  - ほかの行は悪化していない。135 画面すべて測れた（測れなかった 0）。K2 の最大は 1.2 秒（/inventory。§3-4-11-a と同じ）で、2 秒を超えた画面は 0 件。/ の K1 は 0.04 秒のまま。戻った時の秒を測れた画面は 128。測るあいだの API の数は 464（前は 465）。ログイン関係の 429 は 0 件。
  - 生の行は設計担当の手元の /tmp/CC報告ファイル/lead-chat-cache/measure-run41346462841.txt（リポジトリには入れない）。
- K5 は本番で 2 人のログインでは確かめていない（本番でパスワードを打たない決まり）。C1 の 4 本目・6 本目の試験と、写しの名前に利用者が入り利用者が変わると消える作りで確かめた。
- 審査役の止めない指摘（記録・次の見直しの候補）: カルテの保存の終わりで失敗の印を条件なしに消すため、会話 A の保存が会話 B のカルテ取得の失敗の後に返ると B の失敗の印が消える（審査役の推測・まれ。作業指示書どおりの動き）。
- 残り: K1 が 0.1 秒を超える画面の例は /admin/products 0.63 秒・/crm/companies/:id 0.37 秒・/invoices/:id 0.37 秒・/crm/leads/:id/edit 0.34 秒・/crm/leads 0.34 秒。

#### 3-4-13. 段 3 の 1 回目: 遅い順の 10 画面（2026-11-02 設計担当 Claude Opus）
- 2026-11-02 PO 選択「1」（残りの遅い画面を遅い順に 10 画面ずつ、本番の測定まで直す）の 1 回目。対象は §3-4-12-a の測定で K1 が遅い順の 10 画面（11 行）。
- 作業指示書: docs/handoff/line-like-speed/batch3a-card.md（第 1 版）。一覧と詳しい画面は段 2 と同じ形、編集の画面はフォームの初めの値を写しから作る小さな部品を 1 つ足す（batch3a-card.md §0 V3a-4）。受入はカードの §5 B1〜B7。結果はこの節の後に書き足す。

#### 3-4-13-a. 段 3 の 1 回目の本番の受入（2026-11-02 Claude Opus が確かめた）
- B1・B2 は合格。PR #5008 の必須の確認 50 件 pass・9 件 skipping（落ち 0）。Frontend unit tests は pass。
- B3 は合格。PR #5008 の変更は 26 ファイル。migrations/・backend/・scripts/・.github/ は 0。
- B4 は合格（本線 71030e87b で確かめた）。`new QueryClient` は frontend/src/lib/query/apiQuery.ts:23 の 1 行だけ。`staleTime:` は 0 行。persist は 0 行。
- B7 は合格。PR #5008 は 2026-11-02 11:15 JST に main へ入った（merge 17e60b589）。本番への反映は 11:21 JST に success。
- B5 は 1 回目の測定で止めた。prod-ui-check run 41377463601（11:37:02 JST）で /management-center/note-master の 5xx が 1 件・K1 0.20 秒だった。
  - 原因は画面ではなかった。注記マスタの 1 行の照合の種類 STATE_LITERAL を、一覧の返事の形が受け付けず 500 になっていた（本番 DB で 99 行中 1 行）。
  - 直しは PR #5014（note-master-fix-card.md）。照合の種類の 4 つを 1 か所に置き、入力・取り込み・画面の選び肢をそこにそろえた。2026-11-02 13:22 JST に main へ入った（merge 08be73708）。本番への反映は 13:32 JST に success。
- B5 は直しの後に合格。prod-ui-check run 41389073263（測った日時 13:46:26 JST）。
  - 11 行すべて K1 0.04 秒以下・403 と 5xx は 0 件。/management-center/note-master は 5xx 1→0・K1 0.20→0.04 秒。
  - ほかの行は悪化していない。135 画面すべて測れた（測れなかった 0）。全行の 5xx 0。2 秒を超えた画面は 0 件。
  - K2 の最大は 1.3 秒（/inventory）。基準の run 41346462841 は 1.2 秒。run 41332039643 と run 41377463601 も 1.3 秒で、/inventory はこの幅で動いている。
  - 生の行は設計担当の手元の /tmp/CC報告ファイル/batch3a/b8/measure-run41389073263.txt（リポジトリには入れない）。
- B6 は DB の件数だけ確かめた。本番の読むだけの道（ADR-1024）で tenant 001 の Bot 3 件・リード 472 件・注記マスタ 99 件。画面の件数はまだ確かめていない。根拠は backend を変えていないこと（B3）と B1。
- K5 は本番で 2 人のログインでは確かめていない（本番でパスワードを打たない決まり）。カードの Q2 の試験と、写しの名前に利用者が入り利用者が変わると消える作りで確かめた。
- 残り: K1 が 0.1 秒を超える画面（403 なし）は /dashboard/leads 0.20 秒・/management-center/units 0.19 秒・/crm/contacts 0.19 秒・/schedule/settings 0.19 秒・/quotes 0.19 秒・/management-center/status-master 0.19 秒など。設計担当の抜き書きでは全部で 18 画面。/inventory は 10 秒で見分けられなかった。次はこの遅い順の 10 画面。

#### 3-4-14. 段 3 の 2 回目: 遅い順の 10 画面（2026-11-02 設計担当 Claude Opus）
- 2026-11-02 PO 選択「1」の 2 回目。対象は §3-4-13-a の測定（run 41389073263）で K1 が遅い順の 10 行（9 画面。/teams と /management-center/teams は同じ画面）。
- 作業指示書: docs/handoff/line-like-speed/batch3b-card.md（第 2 版。第 1 版のクラウド審査は REVISE で、試験の見本・lint の警告 1 件・手順3 の確かめの 3 つを直した。第 2 版のクラウド審査は APPROVE on 37abec0b4（2026-11-02 15:07 JST・カードどおりに当てて tsc 0・lint の警告 0→0・src/lib/query 48 件・今ある画面の試験 6 本 93 件すべて合格）。）。受入はカードの §5 B1〜B7。結果はこの節の後に書き足す。

#### 3-4-14-a. 段 3 の 2 回目の本番の受入（2026-11-02 Claude Opus が確かめた）
- B1・B2 は合格。PR #5019 の必須の確認 16 件すべて pass。画面検査（内部）は 1 回目が 15 分の時間切れ（816 件中 792 件 pass・失敗 0）で、やり直しで pass。
- B3 は合格。merge e01286b2d の変更は 15 ファイル（855 行足し・221 行消し）。migrations/・backend/・scripts/・.github/ は 0。
- B4 は合格（本線 dd6d131cd で確かめた）。`new QueryClient` は frontend/src/lib/query/apiQuery.ts:23 の 1 行だけ。`staleTime:` は 0 行。persist は 0 行。
- B7 は合格。PR #5019 は 2026-11-02 16:39 JST に main へ入った（merge e01286b2d）。deploy.yml run 41407698440 は 16:46 JST に success。本番の /management-center/units・/crm/contacts・/management-center/teams・/quotes が開き、ブラウザの誤りの記録は 0 件（設計担当の Chrome）。
- 合流のときの止まり: 承認が 1 件要ると読み違え、POの名義で承認を付けた（PO 選択「1」）。本当の止まりは、本文を直した時に動いた process-artifacts gate の最新の実行が cancelled のままだったこと（GitHub の画面の「1 failing check」で確かめた）。その実行をやり直して success になり、合流できた。
- B5 は合格。prod-ui-check run 41409815435（測った日時 17:03:00 JST）。
  - 10 行すべて K1 0.02 秒以下（基準 run 41389073263 では 0.17〜0.20 秒）。K2 は 0.2〜0.4 秒。403 と 5xx は 0 件。
  - 135 画面すべて測れた（測れなかった 0）。全行の 5xx 0。2 秒を超えた画面は 0 件。K2 の最大は 1.4 秒（/inventory。前回まで 1.2〜1.3 秒の幅）。
  - 生の行の抜き書きは設計担当の手元の /tmp/CC報告ファイル/batch3b/measure-run41409815435-extract.txt（リポジトリには入れない）。
- B6 は DB の件数だけ確かめた。本番の読むだけの道（ADR-1024）で tenant 001 の単位 0 件・担当者 1 件・チーム 1 件・見積 1 件。状態マスタは読むだけの道に表が無く、まだ確かめていない。画面の件数はまだ確かめていない。根拠は backend を変えていないこと（B3）と B1。
- K5 は本番で 2 人のログインでは確かめていない（本番でパスワードを打たない決まり）。カードの試験と、写しの名前に利用者が入る作りで確かめた。
- 残り: K1 が 0.1 秒を超える画面（403 なし）は 8 画面。/suppliers/:id/edit 0.17 秒・/own-inventory・/dashboard/follow-ups・/invoices/new・/invoices・/teams/:id/edit・/dashboard/revenue・/dashboard/reasons が 0.16 秒。/inventory は 10 秒で見分けられなかった。

#### 3-4-15. 段 3 の 3 回目: 残りの 8 画面（2026-11-02 設計担当 Claude Opus）
- 2026-11-02 PO 選択「1」（残りの 8 画面も同じ形で、本番の測定まで直す）。対象は §3-4-14-a の測定（run 41409815435）で K1 が 0.1 秒を超えた残りの 8 画面。
- 作業指示書: docs/handoff/line-like-speed/batch3c-card.md（第 1 版）。受入はカードの §5 B1〜B7。結果はこの節の後に書き足す。
- 審査: クラウドの審査役（Opus・routine batch3c card review v1・2026-11-02 10:24Z）が e09e6a620 で APPROVE。S の写しで §4 の変更前の行がすべて一致（ALL OLD LINES MATCH）。当てた後の tsc・eslint は出力 0・exit 0。vitest は全部で 188 files / 2081 tests passed。新しい試験の 8 件は、画面を S に戻すと 8 件とも落ちた（空振りでない）。

#### 3-4-15-a. 段 3 の 3 回目の本番の受入（2026-11-02 Claude Opus が確かめた）
- B1・B2 は合格。PR #5028 の必須の確認 16 件すべて pass。process-artifacts gate の最新の実行が cancelled のままで合流が止まり、やり直して success になった。
- B3 は合格。merge 5ac6f1c85 の変更は 14 ファイル（757 行足し・147 行消し）。migrations/・backend/・scripts/・.github/ は 0。
- B4 は合格（本線 9fd25171a で確かめた）。`new QueryClient` は frontend/src/lib/query/apiQuery.ts:23 の 1 行だけ。`staleTime:` は 0 行。persist は 0 行。
- B7 は合格。PR #5028 は 2026-11-02 19:59 JST に main へ入った（merge 5ac6f1c85）。deploy.yml run 41433211553 は 20:06 JST に success。本番の /invoices と /management-center/tenant-profile が開き、ブラウザの誤りの記録は 0 件（設計担当の Chrome）。
- B5 は合格。prod-ui-check を 2 回動かした。
  - 1 回目 run 41434498398（測った日時 20:13:10 JST）。8 行すべて K1 0.01 秒・K2 0.1〜0.2 秒・403 と 5xx は 0 件。ただし対象外の /inventory が K2 2.1 秒（いちばん遅い API /api/v1/inventory が 1.8 秒）で、ほかの行の条件（K2 の最大と 2 秒超えの数が悪化しない）に当たらなかった。/inventory は今回触っていない（B3）。
  - 一度だけの揺れかを見るため、何も変えずに 2 回目 run 41436620985（測った日時 20:28:04 JST）を動かした。8 行すべて K1 0.01〜0.02 秒・K2 0.2 秒・403 と 5xx は 0 件。/inventory は K2 1.4 秒（API 1.0 秒）で、基準 run 41409815435 の最大 1.4 秒と同じ。2 秒を超えた画面は 0 件。135 画面すべて測れた。全行の 5xx 0。受入は 2 回目で判定した。
  - 対象の 8 行の K1 は、基準 run 41409815435 で 0.16〜0.17 秒だった。
  - 生の行の抜き書きは設計担当の手元の /tmp/CC報告ファイル/batch3c/measure-run41434498398-extract.txt と measure-run41436620985-extract.txt（リポジトリには入れない）。
- B6 は DB の件数だけ確かめた。本番の読むだけの道（ADR-1024）で tenant 001 の仕入先（public.suppliers の tenant_id=1）1 件・チーム 1 件・自社在庫 0 件・請求書 1 件（入金済・取消なし）・承認済みの見積 0 件。
  - 設計担当の Chrome の /invoices は「請求書が登録されていません」だった。この Chrome がどのテナントでログインしているかは、まだ確かめていない。そのため画面の件数はまだ確かめていない。一覧の API（backend/app/routers/invoices.py:185）は状態の指定が無い時に行を絞らない。backend は変えていない（B3）。
- K5 は本番で 2 人のログインでは確かめていない（本番でパスワードを打たない決まり）。カードの試験と、写しの名前に利用者が入る作りで確かめた。
- 残り: 2 回目で K1 を測れた画面（403 なし）のうち、0.1 秒を超えた画面は 0 画面（最大は /lead-chat 0.04 秒）。戻った時の秒を見分けられなかった画面は /inventory と /account/settings（10 秒で見分けられず）と /admin/products/:id/edit（2 回目は「行き先と同じ形」・1 回目は 0.19 秒）。

#### 3-4-16. 在庫表の待ちの決め直しに使った数（2026-11-02 22:12 JST 設計担当 Claude Opus が数えた）
- 在庫表の読み込み: Loki（prod2 の Grafana・Viewer の鍵）で `{job="containerlogs"} |= "HTTP/2.0" |= "GET /api/v1/inventory?"` を 7 日分取った。残っていたのは 2026-10-27〜11-02 の 180 行。読み込みのあった 47 時間で 1 時間の中央 3 回・最大 21 回（10-29 16 時台）。10 秒以内に別々の接続元から読んだ数の最大は 2（10-27 23:03）。この 180 行は毎朝の画面の記録などの機械の読み込みも含む。
- 合図のもと: 在庫表の合図は解析 1 件の完了ごとに出る（tcg_extraction.py:724-731 の _publish_review_changed）。public__extraction_jobs.extracted_at で 7 日 682 回、動きのあった 125 時間で 1 時間の中央 5 回・最大 20 回・1 分の最大 6 回。
- 読み込みの数（180）が合図の数（682）より少ない。合図が来た時の多くは、在庫表を開いている人がいなかった。
- 読み込みの記録は DB には無い（public__data_access_events は data_write と bulk_read_alert だけ）。合図の送り出しにも数える記録は無い（realtime/hub.py・publisher.py は失敗の時だけ書く）。
- サーバー（claude-monitor の docker stats・22:12）: backend CPU 0.14%・メモリ 278MB / 512MB。load average 0.67。API は uvicorn workers=1（backend/Dockerfile:39）。
- 待ちの仕組み: useRealtimeRefresh.ts:38-41 は最初の合図で時計を 1 つ置き、鳴るまでの合図は数えない。だから 1 画面の読み直しは待ちの秒に 1 回まで。
- 生の数: /tmp/CC報告ファイル/inventory-k4/（summary.txt・lines.txt・hourly.json・stats.txt）。

#### 3-4-16-a. 在庫表の待ちを縮めた後の受入（2026-11-03 01:50 JST 設計担当 Claude Opus が測った）
- 反映: PR #5035（HEAD 75608f3eb）を 2026-11-03 00:37 JST に本線へ。deploy run 41473422539 が success（00:44 JST）。本番の画面の部品（/assets/main-Dcv7l6Ej.js）に、待ち 1500・ずれの幅 1e3・行が外れる時刻のずれ 3e3 が入っていることを読んで確かめた。
- W4 合格: prod-ui-check run 41474609602（測った時刻 00:58 JST）で /inventory は 1.4 秒（K2 の 2 秒以内）・API 4 本・403 0 件・5xx 0 件。135 画面すべて測れた（403 なし 100・403 あり 35）。/inventory の戻った時の秒は、前の回と同じく「10 秒で見分けられず」。
- W5 合格（63 回以下）: §3-4-16 と同じ Loki の数え方で 2026-11-02 15:45〜16:50 UTC（00:45〜01:50 JST）を取った。在庫表の読み込みは 3 行（どの 60 分でも最大 3 回）。backend CPU 0.14%・メモリ 277MB / 512MB・postgres メモリ 170MB / 1GB・load average 0.10（claude-monitor の docker stats・01:50 JST）。§3-4-16 の基準（1 時間の最大 21 回・CPU 0.14%・メモリ 278MB）と並べて、増えていない。
- この数の限り: 測った 1 時間は真夜中で、使う人がほとんどいない時間。人の多い昼の時間帯の数はまだ取っていない。
- K4（ほかの人の変更が 5 秒以内に出る）を本番の 2 つのブラウザで確かめるのは、段 5 で行う。待ちの秒は InventoryPage.autorefresh.test.tsx の試験で固定した（最大のずれでも 2.5 秒で 1 回読み直す）。
- 生の数: /tmp/CC報告ファイル/inventory-k4/（w5-result.txt・w5-lines.txt・w5-stats.txt）。

#### 3-4-17. 段 3 の 4 回目（権限の要る 8 画面）の場所と基準（2026-11-03 設計担当 Claude Opus）
- カード: docs/handoff/line-like-speed/batch3d-card.md。対象は保管・ERP の記録・シフト・スタッフの報告・通知の宛先・売上・報酬・報酬の設定の 8 画面（毎朝の記録の 13 行）。残りの権限の要る 8 画面（チャネル・ロール・スタッフ・スタッフの編集・受注・在庫の見え方・状態・商品区分）は段 3 の 5 回目で扱う。
- 測る利用者（tenant 001）への見る権限は 2026-11-03 に PO 選択「1」で足した。権限を足す前の回（prod-ui-check run 41474609602）では 13 行とも 403 が 1〜2 件で、秒は断りの画面の秒（0.01〜0.91 秒）だった。報酬の設定の 2 行は 5xx も 1 件（/api/v1/commissions/monthly）。
- 権限を足した後の基準: prod-ui-check run 41579361752（測った時刻 2026-11-03 13:43 JST・main 1f7bcde）。13 行とも 403 0 件・5xx 0 件。K2（初めて開く秒）は 0.2〜0.3 秒。K1（戻った時の秒）は /management-center/commission の 0.03 秒を除き 0.20〜0.26 秒（K1 の合格線 0.1 秒を超える）。止めた送信は報酬の設定の 2 行（/commission-settings・/management-center/commission）で 1 件ずつ、ほかの 11 行は 0 件。
- 測りの決まりとの関係: 毎朝の記録は GET /api/v1/tenant-commission-settings を「読むだけで書き込みの起きる通信」として止めている（tests/prod-check/page-speed.spec.ts:421-422 の writesOnRead。この回 2 件。報酬の設定の 2 行）。だから本番の記録では、報酬の設定の画面は設定を読めない状態で測られる。直した後は V3d-9 のとおり保存のボタンが押せないまま、月の集計の写しで K1 を測る形になる。
- 生の数: /tmp/CC報告ファイル/inventory-k4/run41474609602-403rows.txt（権限を足す前）・run41579361752-batch3d-rows.txt（権限を足した後）。

#### 3-4-17-a. 段 3 の 4 回目の本番の受入（2026-11-03 Claude Opus が確かめた）
- B1・B2 は合格。PR #5066 の必須の確認はすべて pass または skipping（失敗 0・待ち 0）。審査役（Claude Opus）が HEAD 37c7058e8 に APPROVE。
- B3 は合格。merge fa6775815 の変更は 14 ファイル（840 行足し・198 行消し）で、カード §1 の 14 ファイルと同じ。migrations/・backend/・scripts/・.github/ は 0。
- B4 は合格（本線 b492b3f1c で確かめた）。`new QueryClient` は frontend/src/lib/query/apiQuery.ts:23 の 1 行だけ。`staleTime:` は 0 行。persist は 0 行。
- B7 は合格。PR #5066 は 2026-11-03 14:49 JST に main へ入った（merge fa6775815）。deploy.yml run 41586165249 は 14:57 JST に success。本番 https://app.salesanchor.jp/ は HTTP 200 を返して開き、ブラウザの誤りの記録は 0 件（設計担当の Chrome・15:40 JST ごろ）。この Chrome はログインしていない状態で、見たのは入口の画面だけ（段 1 の A7 と同じ見方）。
- B5 は合格。prod-ui-check を 3 回動かし、3 回目で判定した。
  - 1 回目 run 41586941178（15:11:51 JST）。13 行すべて K1 0.01〜0.04 秒・K2 0.2〜0.3 秒・403 と 5xx は 0 件。ただし対象外の /management-center/status-master/import が 11.2 秒・5xx 1 件だった。Loki で見ると 06:17:24Z の GET /api/v1/me/permissions が 504（nginx の upstream timed out）。同じ時刻に別のマージの deploy（run 41588810768・06:16:05Z〜06:19:18Z）で backend を入れ替えていた。
  - 2 回目 run 41589579501（15:27:27 JST・測定中に deploy なし）。13 行すべて K1 0.01〜0.04 秒・K2 0.1〜0.2 秒・403 と 5xx は 0 件。2 秒を超えた画面は 0 件。ただし対象外の /inventory が K2 2.0 秒で、基準の最大 1.4 秒を超えた。/inventory は今回触っていない（B3）。
  - 一度だけの揺れかを見るため、何も変えずに 3 回目 run 41591179240（15:42:42 JST・main b492b3f・測定中に deploy なし）を動かした。13 行すべて K1 0.01〜0.02 秒・K2 0.2 秒・403 と 5xx は 0 件。いちばん遅い画面は /inventory の 1.3 秒で、基準の最大 1.4 秒以下。2 秒を超えた画面は 0 件。135 画面すべて測れた。
  - 対象外の行で基準の回にもあるもの: /schedule の 5xx 1 件（GET /api/v1/shifts?date_from&date_to の 500）。止めた送信 3 件と 403 7 件の内訳は、基準の回と同じ。
  - 対象の 13 行の K1 は、基準 run 41579361752 で 0.20〜0.26 秒だった（/management-center/commission だけ 0.03 秒）。
  - 生の行の抜き書きは設計担当の手元の /tmp/CC報告ファイル/batch3d-accept/ の run41586941178-batch3d-rows.txt・run41589579501-batch3d-rows.txt・run41591179240-batch3d-rows.txt（リポジトリには入れない）。
- B6 は DB の件数だけ確かめた。本番の読むだけの道（ADR-1024）で tenant 001 を数えると、保管（ai_ro.tenant_001__archives）0 件・シフト（tenant_001__shifts）0 件・スタッフの報告（tenant_001__staff_reports）0 件・通知の宛先（tenant_001__notification_channels）0 件（15:44 JST）。
  - 設計担当の Chrome はログインしていない。そのため、画面の件数はまだ確かめていない。backend は変えていない（B3）。根拠は Q1 の試験。
- K5 は本番で 2 人のログインでは確かめていない（本番でパスワードを打たない決まり）。段 3 の 1 回目の Q2・Q3 の試験と、写しの名前に利用者が入る作りで確かめた。

#### 3-4-18. 段 3 の 5 回目（権限の要る 5 画面）の場所と基準（2026-11-03 設計担当 Claude Opus）
- カード: docs/handoff/line-like-speed/batch3e-card.md。対象はチャネル・ロール・スタッフ・スタッフの編集・受注の 5 画面（毎朝の記録の 9 行）。§3-4-17 で 5 回目に回した 8 画面のうち、在庫の見え方・状態・商品区分の 3 画面は、測る利用者（tenant 001）に見る権限が足りていないので、このカードの対象から外した（PO に別に聞く）。
- 基準: prod-ui-check run 41591179240（測った時刻 2026-11-03 15:42:42 JST・main b492b3f）。9 行とも 403 0 件・5xx 0 件。K1（戻った時の秒）は /channels 0.24・/management-center/channels 0.20・/roles 0.33・/management-center/roles 0.36・/staff 0.23・/management-center/staff 0.24・management-center→staff 0.22・/staff/:id/edit 0.19・/orders 0.19 秒（9 行とも K1 の合格線 0.1 秒を超える）。この回の K2 の最大は /inventory の 1.3 秒、2 秒を超えた画面は 0 件。
- 生の数: /tmp/CC報告ファイル/batch3d-accept/run41591179240-batch3d-rows.txt（設計担当の手元。リポジトリには入れない）。

#### 3-4-18-a. 段 3 の 5 回目の本番の受入（2026-11-03 Claude Opus が確かめた）
- B1・B2 は合格。PR #5077 の必須の確認はすべて pass または skipping（失敗 0・待ち 0）。審査役（Claude Opus）が実装 67b846855 と、main を取り込んだ HEAD 3add24309 に APPROVE。
- B3 は合格。merge 069190790 の変更は 13 ファイル（909 行足し・238 行消し）で、カード §1 の 13 ファイルと同じ。migrations/・backend/・scripts/・.github/ は 0。
- B4 は合格（本線 a0d58d3a7 で確かめた）。`new QueryClient` は frontend/src/lib/query/apiQuery.ts:23 の 1 行だけ（試験のファイルも含めて数えた）。`staleTime:` は 0 行。persist は 0 行。
- B7 は合格。PR #5077 は 2026-11-03 18:22 JST に main へ入った（merge 069190790）。deploy.yml run 41610451127 は 18:29 JST に success。設計担当の Chrome（21:50 JST ごろ・ログイン済み）で本番のチャネル・ロール・スタッフ・受注を開き、4 画面とも中身が出た。ブラウザの誤りの記録は 0 件。
- B5 は 9 行のうち 8 行が合格。/channels の 1 行だけ K1 が合格線を超えた。
  - 1 回目 run 41611528904（18:44:01 JST・main e29f9e1）。測っている間に別のマージの deploy が 2 回終わった（09:34:44Z・09:37:10Z）。/channels の K1 が 0.22 秒、ほかの 8 行は 0.01〜0.02 秒。
  - 2 回目 run 41614984342（18:59:48 JST・main 1eefb57・測定中に deploy なし）。K1 は /channels 0.24・/management-center/channels 0.02・/roles 0.03・/management-center/roles 0.03・/staff 0.01・/management-center/staff 0.02・management-center→staff 0.02・/staff/:id/edit 0.01・/orders 0.01 秒。K2 は 9 行とも 0.2〜0.5 秒。9 行とも 403 と 5xx は 0 件。
  - 全体: いちばん遅い画面は対象外の /inventory の 1.4 秒（基準 1.3 秒・2 秒以内）。2 秒を超えた画面は 0 件。403 は基準の回と同じ見る権限の無い 6 画面だけで、403 7 件と止めた送信 3 件の内訳は基準の回と同じ。/schedule の 5xx 1 件も基準の回と同じ（対象外）。
  - /channels が落ちた訳（設計の入れ忘れ）: チャネルの画面は Discord の設定（GET /admin/discord-config）を、写しの置き場を通さずに開くたびに読んでいる（frontend/src/pages/channels/ChannelsPage.tsx の useEffect で api.get）。カードはこの読みを対象に入れていなかった。戻った時はこの返事を待つ間、Discord の欄が「未接続」の形で出て、返事が来ると「接続済み」に描き直す。だから K1 の「A の画面の部品が描かれた」に届くのが返事の後になる。
  - 直し方: 段 3 の 6 回目に、この読みを写しの置き場（useApiQuery）へ移すことを足す。6 回目はもともと Discord の設定の画面を含む。
  - まだ分からないこと: /management-center/channels は同じ部品を使うのに 0.02 秒だった。理由はまだ確かめていない。6 回目の受入で /channels と並べて確かめる。
  - 生の行の抜き書きは設計担当の手元の /tmp/CC報告ファイル/batch3e-accept/ の run41611528904-batch3e-rows.txt・run41614984342-batch3e-rows.txt（リポジトリには入れない）。
- B6 は合格。本番の読むだけの道（ADR-1024）で tenant 001 を数えると、接続中の Facebook ページ（ai_ro.tenant_001__tenant_meta_config で is_active）0 件・ロール（tenant_001__roles）8 件・スタッフ（tenant_001__staff）2 件・受注（tenant_001__orders）0 件（21:45 JST）。設計担当の Chrome で見た画面は、ロール 8 個・スタッフ 2 人・受注 0 件・「接続済みチャンネルがありません」で、DB と同じ。
- K5 は本番で 2 人のログインでは確かめていない（本番でパスワードを打たない決まり）。段 3 の 1 回目の Q2・Q3 の試験と、写しの名前に利用者が入る作りで確かめた。

#### 3-4-19. 段 3 の 6 回目（会社の情報・会社の方針・Discord の設定とチャネルの画面の Discord の欄）の場所と基準（2026-11-03 設計担当 Claude Opus）
- カード: docs/handoff/line-like-speed/batch3f-card.md。対象は会社の情報・会社の方針・Discord の設定の 3 画面と、§3-4-18-a で残ったチャネルの画面の Discord の欄（毎朝の記録の 8 行）。Discord の設定（/admin/discord-config）は、Discord の設定の画面とチャネルの画面で 1 つの写しにする（同じ答えを分けて持たない）。
- 予定表（/schedule・K1 0.29 秒）は、読む path が 3 本で表示の期間で path が変わり、基準の回で /shifts の 5xx が 1 件あるので、1 度に 1 つを変える決まりにより段 3 の 7 回目に分けた。買取価格・状態・商品区分の 3 画面は、測る利用者に見る権限が足りず 403 なので対象外（PO に別に聞く）。
- 基準: prod-ui-check run 41614984342（測った時刻 2026-11-03 18:59:48 JST・main 1eefb57）。8 行とも 403 0 件・5xx 0 件。K1 は /admin/discord-config 0.25・/management-center/discord-config 0.24・/admin/tenant-policy 0.21・/management-center/tenant-policy 0.21・/admin/tenant-profile 0.21・/management-center/tenant-profile 0.22・/admin→/admin/tenant-profile 0.21・/channels 0.24 秒。
- §3-4-18-a の「まだ分からないこと」（/management-center/channels が 0.02 秒）は、6 回目の受入で /channels と並べて確かめる。
- 生の数: /tmp/CC報告ファイル/batch3f/run41614984342-k1-over.txt（設計担当の手元。リポジトリには入れない）。

#### 3-4-19-a. 段 3 の 6 回目の本番の受入（2026-11-03 Claude Opus が確かめた）
- B1・B2 は合格。PR #5087 の確認は 47 件 pass・8 件 skipping・失敗 0（必須の確認はすべて pass）。審査役（Claude Opus）が実装 d39d856dd と、main を取り込んだ HEAD b295a09e9 の両方に APPROVE。main の取り込みは、必須の確認 guard-authoring/evaluation が「枝の元が main の最新でない」で error になったため（scripts/run-guard-evaluation.js:25 の merge-base --is-ancestor）。
- B3 は合格。PR の変更は 9 ファイルで、カード §1 と同じ。書く道の path とフォームの欄は S と同じ（審査役が git diff -w で確かめた）。migrations/・backend/・scripts/・.github/ は 0。
- B4 は合格。`new QueryClient` は apiQuery.ts:23 の 1 行・`staleTime:` 0 行・persist 0 行・`/admin/discord-config` を api.get で直に読む所は ChannelsPage.tsx:211（cache.fetch の中）と触らない範囲の InboxKartePanel.tsx:115 の 2 行。
- B7 は合格。PR #5087 は 2026-11-03 23:18 JST に main へ入った（merge 85cc2e528）。deploy.yml run 41652377760 は 23:25 JST に success。
- B5 は 8 行すべて合格。run 41653642044（測った日時 23:39:43 JST・main 9159ad5。#5087 の後に入ったのは台帳の自動 DONE #5089 だけ・測定前に deploy 済み）。
  - K1（基準 run 41614984342 → 今回）: /admin/discord-config 0.25→0.01・/management-center/discord-config 0.24→0.01・/admin/tenant-policy 0.21→0.01・/management-center/tenant-policy 0.21→0.01・/admin/tenant-profile 0.21→0.01・/management-center/tenant-profile 0.22→0.01・/admin→/admin/tenant-profile 0.21→0.01・/channels 0.24→0.01 秒。/management-center/channels は 0.02→0.01 秒で 0.1 秒以下のまま。
  - K2 は 9 行とも 0.2〜0.3 秒。9 行とも 403 と 5xx は 0 件。
  - 全体: 135 行。いちばん遅い画面は対象外の /inventory の 1.3 秒（基準 1.4 秒）。2 秒を超えた画面は 0 件。403 は基準の回と同じ見る権限の無い 6 画面だけ。/schedule の 5xx 1 件も基準の回と同じ（対象外・7 回目で扱う）。
  - K1 が 0.1 秒を超えた行は基準の 12 行から 5 行に減った: /schedule 0.28（7 回目）・/buyback-prices 0.17・/management-center/conditions 0.21・/management-center/product-categories 0.22（3 つとも 403 で対象外）・/admin/products/:id/edit 0.22。
  - /admin/products/:id/edit は、基準の回では「戻: 見分けられず（行き先と同じ形）」で K1 が測れていなかった。今回初めて測れた値で、悪化ではない。今回触っていない画面で、段 3 の残りに足すかは 7 回目の設計で決める。
  - §3-4-18-a の「まだ分からないこと」: 今回は /channels と /management-center/channels がどちらも 0.01 秒で揃った。前回だけ /management-center/channels が速かった理由は、まだ確かめていない（Discord の欄を写しに載せた後は差が無くなったので、追わない）。
  - 生の行の抜き書きは設計担当の手元の /tmp/CC報告ファイル/batch3f-accept/run41653642044-rows.txt（リポジトリには入れない）。
- B6 は合格。本番の読むだけの道（ADR-1024）で tenant 001 を読むと、会社の情報（ai_ro.tenant_001__tenant_profile）1 行で会社名は空（null）・会社の方針（ai_ro.public__tenant_settings の tenant_id 1）の集計価格閾値 0・Discord の設定（ai_ro.public__tenant_discord_config の tenant_id 1）のサーバー ID あり（末尾 7393）。設計担当の Chrome（23:3x JST・ログイン済み）で見た画面は、会社名が空・集計価格閾値 0・「接続済み」でサーバー ID の末尾 7393 で、DB と同じ。生の出力は /tmp/CC報告ファイル/batch3f-accept/（b6.tsv・b6-profile.tsv・b6-screen.txt）。
- K5 は本番で 2 人のログインでは確かめていない（本番でパスワードを打たない決まり）。カード §4-L の試験（人が変わった時に前の人の写しを出さない）と、写しの名前に利用者が入る作りで確かめた。

### 3-5. 測り方（|基準|検証方法|）
| 基準 | 検証方法 |
|---|---|
| K1 戻った時 0.1 秒以内 | 段 0 で足す測定。今の waitSettled（100 ms ごと・最短 500 ms）では 0.1 秒を測れない（recon §4）。また staleTime 0 なので「通信が全部終わるまで」の今の秒は取り直しの終わりの秒になり K1 にならない。→ 画面の中に記録係（requestAnimationFrame で毎フレーム見る小さな script を page.addInitScript で入れる）を置き、goInApp（page-speed.spec.ts:72-79）で A→B→A と移った時刻から、中身の場所（DesktopShell.tsx:400 main.app-content／MobileShell.tsx:201 main.mobile-content）に「読み込み中の印の目印（LOADING_SELECTOR）が 0 個」かつ「A の画面の部品が描かれた」最初のフレームまでの秒。「A の画面の部品が描かれた」= 中身の場所の要素のタグ名とクラス名だけを数に縮めた構造の印が、A を最初に開き終えた時と同じになったコマ（文字・値は読まない。決め方と測れない時の訳は stage0-card.md V0-2） |
| K2 初回 2 秒以内 | 今の毎朝の記録（page-speed.spec.ts:311 の秒）をそのまま |
| K3 押して 0.1 秒以内 | 段 0 で足す測定。K1 と同じ記録係で、横のメニューにある画面はその項目を本当に押し（page.click）、押した時刻（pointerdown を capture で記録）から中身の場所の DOM が最初に変わった時刻（MutationObserver）まで。横のメニューに無い画面（今の PC の横のメニューで押せる道すじが固定の画面は最大 7 件・DesktopShell.tsx:227-378）は、アプリの中で切り替える命令（goInApp）の直前の時刻から同じ変化まで。メニューを開く操作と指を乗せる動きは数えず、道すじが固定の画面だけを測る（stage0-card.md V0-3） |
| K4 5 秒以内 | 段 5。tenant 001 で 2 つのブラウザ、片方で変更しもう片方に出るまで。在庫表も判定に入れる（§5 の PO 決定 2026-11-02「1」。待ちの秒は inventory-wait-card.md §5 の W1 の試験でも固定する） |
| K5 0 件 | 段 1 の試験（単体＋画面の試験）。A→ログアウト→B で A の中身が DOM に無い |
| K6 ○ | 段 3 の後、PO がスマホで 3 画面を触る（その時に、よく使う画面も聞く＝recon U2） |

### 3-6. ほかの案と選んだ理由
- 案 A（選ぶ）TanStack Query: 開いた時に写しを出し裏で取り直す・合図で取り直す・人が変わった時に消す、が部品に揃っている。X1 で画面移動時の追加通信 0 の実測がある。危ない点（X3・X4）は消し方の順で避けられる。
- 案 B SWR: 同じ形だが、ログアウト時に全部を消す・開いている画面に知らせる手順を自分で書く量が多い（公式資料の確認は ADR 審査で行う・未確認）。
- 案 C 自前の写し置き場: 新しい部品を入れずに済むが、取り直し・重複の束ね・消し方を全部自作することになり、X3・X4 と同じ失敗を自分で踏む危険がある。
- 案 D 先読みだけ（押す前に取る）: 初回は速くなるが、戻った時の写しが無いので K1 を満たせない。

### 3-7. 弊害と対処
- 古い中身が一瞬見える: 写しを出した直後に取り直すので、取り直しの間（今の秒＝最大 1.4 秒）は前の中身。→ 取り直し中は Spinner を出して分かるようにする。お金・在庫の数を確定する画面（送信ボタンのある画面）では、送る前にサーバーの値で確かめる今の作りを変えない。
- 前の人の中身が見える（X3）: key に人の id＋ログアウトで消す、の二重。段 1 の試験で 0 件を確かめる。
- 再送が増える: TanStack の retry を 0 にして api.ts の 3 回だけにする。単体試験で数を固定。
- 一括移行の衝突（X1 で rebase の直しが要った）: 10 画面ずつ・1 便 1 PR。
- メモリ: 写しは 30 分で捨てる。段 3 の途中で 1 回、ブラウザのメモリの量を測る（基準は段 0 で取る）。10 分へ下げる線: 段 3 の測定で、写しの分（段 0 の基準との差）が 1 つのタブで 50 MB を超えたら、gcTime を 10 分に下げる便を出す。下げた時は K1（§1）の範囲も「10 分以内に戻った時」に変わり、PO に知らせる。50 MB は設計担当の仮の線で、段 0 の基準の値を見て PO に確かめる。

### 3-8. 戻し方
- 段 1: PR を戻す（画面はまだ使っていないので影響なし）。
- 段 2・3: 便ごとに PR を戻せば、その画面だけ今の useEffect の形に戻る（画面ごとに独立）。
- 段 4: 検査を外す PR。

### 3-9. 維持の仕組み
守り手: CI の検査（段 4）と毎朝の速さの記録（段 0）。仕組みの持ち主は設計担当（Claude Opus）。
- 段 4 の CI の検査（中身を消す形の数を増やさない）。
- 段 0 の毎朝の記録に K1・K3 を足し、2 秒・0.1 秒を超えた画面を知らせる（知らせの作りは別便）。
- 新しい画面は useApiQuery を使う、を frontend/CLAUDE.md ではなく CI の検査で強制する（CLAUDE.md の追加判定 1 に従う）。

## 4. 外部・過去事例の参照と我々への応用（原文の確認記録: docs/handoff/line-like-speed/sources.md B）
| # | 何 | 5W2H の要点 | 数値 | 本件への使い方 |
|---|---|---|---|---|
| X1 成功 | ShipSecAI/studio PR #298（2026-02-17〜18） | 開発チームが 13 領域を Zustand から TanStack Query へ・11 store 削除 | API 呼び出し 10→8（-20%）・DOM 2,091→1,444（-31%）・画面移動時の追加通信 0・CLS 0.00 | 画面移動で取り直しが消える根拠。規模が違うので数は本件の約束にしない |
| X2 型 | tkdodo「Using WebSockets with React Query」（2021-06-06） | 合図で invalidate する形 | なし | ADR-1016 の合図の受け方の形。成功の証明には使わない |
| X3 失敗 | TanStack/query #28（2019-11-09） | 別の人のログイン後、一瞬前の人の中身が見えた | 0.3.7 で消す関数を追加（2 日後） | K5 の危険。key に人の id＋消す |
| X4 失敗 | TanStack/query #2157（2021-04-20） | clear() が開いている画面に知らせない | なし | 消す順を cancel→reset→clear にする |
| X5 指針 | tkdodo「Practical React Query」（2023-10-21 更新） | staleTime 既定 0・結果を手元の状態に写さない | なし | 写しを二重に持たない（PO 条件と同じ向き） |

## 5. 未決（PO に聞くこと・審査で詰めること）
- 段 2 の試しの 3 画面目: 中身を消す形の代表から選ぶ（PO に聞く事業判断ではない）。
- K4 の範囲（PO 決定 2026-10-31「1」）: 全部の画面で、ほかの人の変更を数秒で出す。段 5 で画面のまとまりごとに合図を足す（backend 便・まとまりの数だけ便が増える）。打っている途中が見える同時編集は対象外（PO が選ばなかった案 3）。
- K4 と在庫表の食い違い（審査 1 回目の指摘）: 在庫表は、合図を受けてから 5 秒＋0〜3 秒のずれを置いて読み直す（InventoryPage.tsx:110-121）。これは ADR-1016 改訂 2026-10-18 の PO 決定で、在庫表の合図は全部の会社の画面に一斉に届くため、読み直しが同じ瞬間に集まらないよう散らしている。読み直しの通信（最大 1.4 秒）を足すと、在庫表は最大で約 9.4 秒になり、K4 の 5 秒を超える。PO 決定 2026-10-31「3」: 在庫表の時間は、全部の画面を直し終わってから決め直す。それまでは在庫表の 5 秒＋0〜3 秒のずれ（ADR-1016 改訂 2026-10-18）を変えず、K4 の 5 秒の判定から在庫表を外す。段 5 の最後に、在庫表の時間を PO に相談し直す（このとき、ずれの幅を縮めた場合のサーバーの混み具合を測った数を添える）。
- 在庫表の時間の決め直し（PO 決定 2026-11-02「1」）: 段 5 の前に前倒しで決めた。PO はまず混み具合を数えることを選び（「1」）、§3-4-16 の数を見て、ほかの画面と同じ 1.5 秒＋0〜1 秒のずれにすることを選んだ（「1」）。在庫表を K4 の 5 秒の判定に戻す。行が外れる時刻のずれ 0〜3 秒は変えない。ADR-1016 改訂 2026-11-02。実装は inventory-wait-card.md。
  - 選ばなかった案: 今の 5〜8 秒のまま（K4 を満たさない）、2.5 秒＋0〜1.5 秒（最大 約 5.8 秒で 5 秒に届かない）。
  - 数えていないこと: 待ちを縮めた状態で同時に読ませる試しはしていない。縮めた後に §3-4-16 と同じ数え方で測る（カード W5）。
- K1 の「戻ったとき」の範囲（審査 2 回目の指摘 A3(e)）: 写しは 30 分使われないと捨てるので、K1 は「同じログインの中で 30 分以内に戻った時」に限る。30 分を過ぎた時とログインし直した後は K2（2 秒）で判定する。これは承認済みの K1 に範囲を書き足すもの。PO は 2026-10-31 21:55 JST に「30 分のまま採用し、作り始める」（選択「1」）を選び、この範囲もその時に採用された。30 分の外部の根拠と未確認の点は docs/handoff/line-like-speed/sources.md D。
