# 会話の画面の写しカード（会話の画面 /lead-chat の 4 つの取り方を写しの置き場に載せる）

- 対象: docs/handoff/line-like-speed/design.md §3-2（部品）・§3-4-11（最初の画面の写しの受入）・§3-4-12（このカード）・§3-5 の K1・K5。ADR-1054（Accepted）。
- 根拠の写し: S=origin/main a6ef43ca7。行番号はすべてこの sha。実装の前に最新の origin/main で行を合わせ直す（§3(a)）。
- 書き方の決まりは最初の画面の写しカード（docs/handoff/line-like-speed/dashboard-cache-card.md）と同じ。全命令は cd <W> で始める・出力は tail/head で上限・PR は実行役が作らない・出力をファイルに残す命令と tail で読む命令は別の行。
- 実行役はクラウドの Sonnet。作業場所の作り方はクラウドの決まり（S scripts/agent-hooks/cloud/rules.md:15）を正とする。.pr-number・gh-pr-create-safe.sh は使わない。待つために sleep を使わない。
- 状態: 第 1 版（設計担当 Claude Opus・2026-11-02）。
- 受領確認: 実装役は着手の最初の報告に「会話の画面の写しカード 第 1 版を受け取った・S=a6ef43ca7」と書く。

## 0. 何のための変更か（設計の合格線は変えない）
- P1 最初の画面の写しの受入（prod-ui-check run 41332039643 と 41334197486・2026-11-02）で、/ の戻った時の秒（K1）は 0.04 秒と 0.05 秒になった。同じ 2 回で /lead-chat の K1 は 0.68 秒と 0.83 秒、開く秒（K2）は 0.9 秒（2 回目）。2 回目の /lead-chat の行は API の数 7・いちばん遅い API は /api/v1/conversations 0.5 秒。設計担当の手元の写しは /tmp/CC報告ファイル/dashboard-cache/measure-run41332039643.txt と measure-run41334197486.txt（リポジトリには入れない）。
- P2 会話の画面の中身は、1 つのフック（S frontend/src/pages/inbox/useInboxState.ts）が 4 つの取り方を useState に持つ。(1) 会話の一覧 S :218-219・:332-361（listConversations）。(2) 送り元のページの選び肢 S :239・:364-378（listConversations({}) の page_id）。(3) 選んだ会話のメッセージ S :243・:380-409（getMessages）。(4) 右のカルテ S :249・:411-430（api.get('/leads/:id')）。どれも写しの置き場を使わない。画面を出すたびに空から始まる。
- P3 戻った時に読み込み中の印が出る所（S のコードを読んで確かめた）: 会話の一覧は convLoading が true の間 LoadingBlock（S frontend/src/pages/inbox/InboxConversationRows.tsx:60-61）。メッセージは `msgLoading && !messagesData` の間 LoadingBlock（S frontend/src/pages/inbox/InboxMessageThread.tsx:525）。カルテは会話を選んでいて leadDetail が無い間 LoadingBlock（S frontend/src/pages/inbox/InboxKartePanel.tsx:134-138・:322-325）。PC では一覧が来た後に先頭の会話を自動で選ぶ（S useInboxState.ts:735-744）。送り元のページの選び肢は、ページが 2 つ以上ある時だけ出る（S frontend/src/pages/inbox/InboxConversationList.tsx:168）。K1 の測り方（S tests/prod-check/page-speed.spec.ts の measureReturn）は、中身の場所の形（タグとクラス名）が開き終えた時と同じで、読み込み中の印が 0 個になった最初のコマを取る。このため K1 には (1)〜(4) の 4 つ全部が戻った時の最初の描画に要る。
- P4 仮説（まだ確かめていない）: (1)〜(4) を写しの置き場に載せると、戻った時の最初の描画に前の一覧・メッセージ・カルテ・選び肢が出て、/lead-chat の K1 が 0.1 秒以下になる。確かめ方は §5 C4。下がらなければ仮説は誤りと記録して止まる。残る心配: 顔写真が読めない時の差し替え（S :244 avatarErrors は画面を出すたびに空から始まる）で形が変わると、K1 が遅れることがある。C4 で分かる。
- P5 送る path は今と 1 文字も変えない。今の文字の作り方（S frontend/src/lib/messages.ts:165-189・:192-194）を conversationsPath・messagesPath に外へ出し、listConversations と getMessages もそれを使う（§4-B）。写しの名前は今までと同じ形（["api", uid, …path の言葉, { query }]・S frontend/src/lib/query/apiQuery.ts:42-46）。カルテの /leads/:id は最初の画面の優先の見込み客（S frontend/src/pages/dashboard/PriorityProspectsSection.tsx:132）と同じ写しの名前になり、同じ 1 つを読む。データを 2 か所に持たない。/leads/:id の取得と保存はどちらも同じ形（LeadResponse）を返す（S backend/app/routers/leads.py:377-381・:494-498）。保存の後の中身はその写しに書く。利用者が変わると QueryAuthSync が写しを全部消す（S frontend/src/lib/query/QueryAuthSync.tsx:18-28）。写しの名前に uid が入るので、前の人の写しは名前が違い読まれない（K5）。
- P6 取りに行く時と回数は今と同じにする。写しの置き場の見張り（useApiQuery）は enabled:false で置き、自分では取りに行かない。取りに行くのは今と同じ所（一覧は filter が変わった時・SSE・30 秒ごと・送信の後、メッセージは会話を選んだ時・SSE・30 秒ごと・送信とリアクションの後、カルテは会話を選んだ時）だけ。そのため写しの置き場に、写しを読み書きする useApiCache を 1 つ足す（§4-A）。中身は TanStack Query 5.104.4 の fetchQuery・getQueryData・setQueryData・setQueriesData（Context7 の /tanstack/query で確かめた。setQueryData と setQueriesData は、書き換えが undefined を返すと写しを変えない。fetchQuery は同じ写しを取りに行っている途中なら、その途中の 1 本を待つ）。同じ path を同時に 2 回取りに行く時は 1 本になる（例: 絞り込みなしの一覧と選び肢の一覧が同じ "/conversations" の時）。
- P7 変わることは 4 つだけ。(1) まだ写しの無い会話へ切り替えた時、前の会話のメッセージとカルテを出したままにせず、読み込み中の印を出す（今は前の会話の中身が新しい中身の届くまで残る）。写しのある会話へ切り替えた時は、写しをすぐ出して裏で取り直す。(2) 送り元のページの選び肢は、絞り込みなしの一覧を取り直すたびに新しくなる（今は画面を出した時の 1 回だけ）。会話を消す・除外する操作で、そのページの会話が一覧から 1 件も無くなると、そのページは選び肢から消える。(3) 同じ path を同時に取りに行く時は 1 本になる（P6）。(4) 一覧の中を手元で書き換える操作（既読・未読・除外・削除・まとめる・成約へ進める）は、条件の違う一覧の写しにも同じ書き換えをする（条件を切り替えた時に、消した会話が一瞬出ないため）。
- P8 メッセージの欄の下までの自動スクロールは、今は中身が届くたびに必ず動く（S :686-691 の依存は messagesData で、届くたびに新しい物になる）。写しの置き場は中身が同じなら前と同じ物を返すので、届いた回数の数（msgLoadCount）を依存に足し、今と同じく届くたびに動かす（§4-C (9)）。
- P9 前の試験の写しが次の試験に残らないよう、試験の beforeEach で写しの置き場（queryClient）を消す（§4-D・§4-E）。試験の共通の準備（S frontend/src/test-setup.ts）は変えない。今 useInboxState を使う試験は 1 つだけ（`git grep -l useInboxState -- 'frontend/src/**/*.test.*'` が useInboxState.autoSelectBadge.test.tsx の 1 行）。lib/messages を偽物にする試験は 6 つ（DesktopShell・MobileShell・MessageReactionBadges・reactionHeart・useInboxState.autoSelectBadge・SoldOutResultsPanel）。useInboxState を通らない 5 つは conversationsPath・messagesPath を使わないので変えない。

## 1. 触るファイル（変更前→変更後）
| # | ファイル | 変更前 | 変更後 |
|---|---|---|---|
| 1 | frontend/src/lib/query/apiQuery.ts | useApiQuery・useApiQueries・invalidateApi・useInvalidateApi | useApiCache を 1 つ足す（§4-A） |
| 2 | frontend/src/lib/messages.ts | listConversations と getMessages の中で path を作る | path の作り方を conversationsPath・messagesPath に出す（§4-B） |
| 3 | frontend/src/pages/inbox/useInboxState.ts | 4 つの取り方を useState に持つ | 写しの置き場に載せる（§4-C） |
| 4 | frontend/src/pages/inbox/useInboxState.autoSelectBadge.test.tsx | 写しの置き場を消さない | 偽物に 2 つ足し、写しを毎回消す（§4-D） |
| 5 | frontend/src/pages/inbox/useInboxState.cache.test.tsx | 無い | 5 本の試験（§4-E 全文） |
| 6 | docs/handoff/line-like-speed/lead-chat-cache-card.md | 無い | このカード（設計担当が書いた。実装役は触らない） |
| 7 | docs/handoff/line-like-speed/design.md | §3-4-10 まで | §3-4-11 に最初の画面の受入、§3-4-12 にこのカードの場所を書き足し済み（設計担当。実装役は触らない） |
| 8 | .claude-pipeline/active-work.d/release-line-like-speed-lead-chat-card.md | 無い | 作業の札（設計担当。実装役は触らない） |

## 2. 触らない範囲
- backend/・migrations/・.github/workflows/・scripts/・tests/prod-check/・frontend/viewer/・frontend/tests-e2e/ は触らない。
- frontend/src/test-setup.ts・frontend/src/lib/api.ts・frontend/src/lib/query/QueryAuthSync.tsx・frontend/src/contexts/AuthContext.tsx・frontend/src/App.tsx は触らない。apiQuery.ts は §4-A の足し算だけ。messages.ts は §4-B の 3 か所だけ（型の定義・ほかの関数は 1 行も変えない）。
- InboxPage.tsx・InboxConversationList.tsx・InboxConversationRows.tsx・InboxMessageThread.tsx・InboxKartePanel.tsx・inbox.types.ts・CSS・ja.json・en.json・components/ は触らない。新しい言葉・色・寸法・回る印を足さない。useInboxState の返す物の名前と型（S :43-205 の型）は変えない。
- DesktopShell.tsx・MobileShell.tsx の listConversations({unread_only:true})（未読の数）は変えない（変更は一度に 1 つ）。
- QueryClient を作らない。staleTime を設定しない。写しをブラウザの保存に書かない。取りに行く時と回数を増やさない（P6）。

## 3. 実装役が先に確かめること（想定分岐つき）
- (a) 最新の origin/main で、§1 #1〜#4・frontend/src/test-setup.ts が S と同じか（`git diff --stat a6ef43ca7 origin/main -- frontend/src/lib/query frontend/src/lib/messages.ts frontend/src/pages/inbox frontend/src/test-setup.ts` が空か）。違えば停止して、その出力を付けて BLOCKED: で報告する。
- (b) `cd <W>/frontend && grep -n '"@tanstack/react-query"' package.json` が `"5.104.4"` の 1 行。違えば停止して報告する。
- (c) `cd <W> && git grep -n -E "setConversations|setLeadDetail|setMessagesData|setAvailablePageIds" -- frontend/src | head -30` の行が、useInboxState.ts の中だけ（S で :218・:239・:243・:249・:340・:375・:385・:405・:414・:427・:441・:506・:629・:638・:651・:652・:945・:962・:986・:996・:1008・:1043・:1052・:1061 の 24 行）。ほかのファイルに 1 行でもあれば停止して NEEDS_DECISION: で返す。:945・:962・:986・:996・:1008・:1043・:1052・:1061 はどれも `setConversations((prev) =>` の形（関数を渡す形）であること。1 つでも関数でない物を渡していれば停止して NEEDS_DECISION: で返す。
- (d) 手順 4 の全部の試験で、§1 #4・#5 のほかの試験ファイルが落ちたら、試験もコードも直さずに停止し、NEEDS_DECISION: で落ちた試験の名前と生の出力（tail）を返す。
- (e) §1 #4 の 5 本・§4-E の 5 本のどれかが落ちたら、試験を書き換えて通さない。§4-A〜§4-E の写し違いを探し、写し違いが無ければ停止して NEEDS_DECISION: で生の出力を返す。とくに K5 の試験（§4-E の 4 本目）は、落ちたら直し方を自分で考えずに停止する。§4-E の見本の値（fixture）が型や描画に足りずに落ちた時だけ、見本の値に足りない項目を足してよい（画面のコードは変えない）。足した項目は報告に書く。
- (f) 手順 2 で、変える前の lint の警告の数を数えておく（§1 #1〜#4）。変えた後は、#1〜#5 を合わせてその数より増えないこと。増えたら直す。直せない時は停止する。eslint の react-hooks/exhaustive-deps を disable の注釈で黙らせない（S :683 にある 1 か所はそのまま残す）。
- (g) tsc が §4-A の型（とくに update の書き換えの型）で誤りを出したら、型を as で曲げずに停止し、NEEDS_DECISION: で tsc の出力を返す。§4-C の中の `as` は書いてある所だけ。

## 4-A. #1 frontend/src/lib/query/apiQuery.ts（1 か所を足す）
S の末尾（useInvalidateApi の閉じ括弧の後）に、次をそのまま足す。import は S :8 の `useCallback` に `useMemo` を足して `import { useCallback, useMemo } from "react";` にする。ほかの import は変えない。
```ts

/**
 * 写しを読み書きする道具（ADR-1054）。取りに行く時を画面が決める所（会話の画面）で使う。
 * 見張り（useApiQuery）は enabled:false で置き、取りに行くのはここの fetch だけにする。
 * 写しの名前は useApiQuery と同じ。ログインしていない時は取りに行かず、書きもしない。
 */
export interface ApiCache {
  /** 取りに行き、写しに書いて返す。同じ写しを取りに行っている途中なら、その 1 本を待つ。 */
  fetch<T>(path: string, fetcher: () => Promise<T>): Promise<T | undefined>;
  /** 今の写しを読む（無ければ undefined）。 */
  read<T>(path: string): T | undefined;
  /** 頭の言葉が同じ写しを全部書き換える。写しの無い物は書き換えない。 */
  update<T>(head: readonly string[], change: (old: T) => T): void;
  /** 1 つの写しに書く。 */
  write<T>(path: string, data: T): void;
}

export function useApiCache(): ApiCache {
  const { user } = useAuth();
  const uid = user?.uid ?? null;
  return useMemo<ApiCache>(
    () => ({
      fetch: <T,>(path: string, fetcher: () => Promise<T>) =>
        uid === null
          ? Promise.resolve(undefined)
          : queryClient.fetchQuery<T>({ queryKey: apiQueryKey(uid, path), queryFn: fetcher }),
      read: <T,>(path: string) =>
        uid === null ? undefined : queryClient.getQueryData<T>(apiQueryKey(uid, path)),
      update: <T,>(head: readonly string[], change: (old: T) => T) => {
        if (uid === null) return;
        const { words } = splitApiPath(head.join("/"));
        queryClient.setQueriesData<T>({ queryKey: ["api", uid, ...words] }, (old) =>
          old === undefined ? undefined : change(old),
        );
      },
      write: <T,>(path: string, data: T) => {
        if (uid === null) return;
        queryClient.setQueryData<T>(apiQueryKey(uid, path), data);
      },
    }),
    [uid],
  );
}
```

## 4-B. #2 frontend/src/lib/messages.ts（3 か所を変える）
(1) S :165-189 の listConversations の上に、次を足す（filter の型は listConversations の引数の型と同じ）。
```ts
/** 会話の一覧の path（listConversations と写しの名前が同じ文字を使う。ADR-1054） */
export function conversationsPath(
  filter: {
    platform?: PlatformFilter;
    unread_only?: boolean;
    page_id?: string;
  } = {},
): string {
  const params = new URLSearchParams();
  if (filter.platform && filter.platform !== "all") {
    params.set("platform", filter.platform);
  }
  if (filter.unread_only) {
    params.set("unread_only", "true");
  }
  if (filter.page_id) {
    params.set("page_id", filter.page_id);
  }
  const qs = params.toString();
  return `/conversations${qs ? `?${qs}` : ""}`;
}

/** 1 つの会話のメッセージの path（getMessages と写しの名前が同じ文字を使う。ADR-1054） */
export function messagesPath(leadId: number): string {
  return `/leads/${leadId}/messages`;
}
```
(2) listConversations の中身（S :174-188 の `const params = new URLSearchParams();` から `return api.get<ConversationsResponse>(…);` まで）を、次の 1 行にする。引数の型と JSDoc は変えない。
```ts
  return api.get<ConversationsResponse>(conversationsPath(filter));
```
(3) getMessages の中身（S :193）を、次の 1 行にする。
```ts
  return api.get<MessagesResponse>(messagesPath(leadId));
```

## 4-C. #3 frontend/src/pages/inbox/useInboxState.ts（14 か所を変える）
(1) import。S :13-28 の `../../lib/messages` の import に `ConversationsResponse`・`conversationsPath`・`messagesPath` を足す（並びは今の並びに合わせ、型は型の並び・関数は関数の並びに入れる）。S :14 の次に `import { useApiCache, useApiQuery } from "../../lib/query/apiQuery";` を足す。

(2) S :218 を消し、S :219 は次にする（S :220 の convError は変えない）。
```ts
  // 取りに行っている間 true。画面に出す読み込み中の印は、写しが無い時だけ（下の convShowLoading）。
  const [convLoading, setConvLoading] = useState(true);
```
(3) S :239 の `const [availablePageIds, setAvailablePageIds] = useState<string[]>([]);` を消す。
(4) S :243 の `const [messagesData, setMessagesData] = useState<MessagesResponse | null>(null);` を、次の 2 行にする。
```ts
  const [msgFailed, setMsgFailed] = useState(false);
  const [msgLoadCount, setMsgLoadCount] = useState(0);
```
(5) S :249 の `const [leadDetail, setLeadDetail] = useState<LeadDetail | null>(null);` を、次の 1 行にする。
```ts
  const [leadFailed, setLeadFailed] = useState(false);
```
(6) S :325（handleAvatarError の `}, []);`）と S :327 の `// ----` の間（S :326 の空行の所）に、次を足す。
```ts

  // ---------------------------------------------------------------------------
  // 写しの置き場（ADR-1054）: 戻った時は前の中身を先に出す。取りに行くのは下の load* だけ
  // ---------------------------------------------------------------------------

  const cache = useApiCache();
  const conversationsFilter = useMemo(() => ({
    platform: platformFilter === "all" ? undefined : platformFilter,
    unread_only: unreadOnly,
    page_id: pageIdFilter || undefined,
  }), [platformFilter, unreadOnly, pageIdFilter]);
  const conversationsQuery = useApiQuery<ConversationsResponse>(conversationsPath(conversationsFilter), { enabled: false });
  const conversations = conversationsQuery.data?.conversations ?? NO_CONVERSATIONS;
  const convShowLoading = convLoading && conversationsQuery.data === undefined;
  // 一覧の中を手元で書き換える。条件の違う一覧の写しにも同じ書き換えをする。
  const setConversations = useCallback((change: (prev: Conversation[]) => Conversation[]) => {
    cache.update<ConversationsResponse>(["conversations"], (old) =>
      Array.isArray(old.conversations) ? { ...old, conversations: change(old.conversations) } : old,
    );
  }, [cache]);

  // 送り元のページの選び肢（絞り込みなしの一覧から作る）
  const allConversationsQuery = useApiQuery<ConversationsResponse>(conversationsPath({}), { enabled: false });
  const availablePageIds = useMemo(() => Array.from(
    new Set(
      (allConversationsQuery.data?.conversations || [])
        .map((c) => c.page_id)
        .filter((p): p is string => !!p),
    ),
  ).sort(), [allConversationsQuery.data]);

  // 選んだ会話のメッセージとカルテ（会話を選んでいない時は null。番号 0 の写しは取りに行かない見張りだけ）
  const messagesQuery = useApiQuery<MessagesResponse>(messagesPath(selectedLeadId ?? 0), { enabled: false });
  const messagesData = selectedLeadId === null || msgFailed ? null : messagesQuery.data ?? null;
  const leadDetailQuery = useApiQuery<LeadDetail>(`/leads/${selectedLeadId ?? 0}`, { enabled: false });
  const leadDetail = selectedLeadId === null || leadFailed ? null : leadDetailQuery.data ?? null;
```
あわせて、ファイルの上の方の定数の並び（関数 useInboxState の外・import の後）に、次の 1 行を足す。置く位置は、S で関数 useInboxState の宣言（`export function useInboxState`）の直前の空行の上。
```ts
/** 会話が無い時の一覧（描画ごとに新しい配列を作らないため） */
const NO_CONVERSATIONS: Conversation[] = [];
```
(7) loadConversations（S :332-361）。S :334-339 の
```ts
      const data = await listConversations({
        platform: platformFilter === "all" ? undefined : platformFilter,
        unread_only: unreadOnly,
        page_id: pageIdFilter || undefined,
      });
      setConversations(data.conversations || []);
```
を、次にする。
```ts
      await cache.fetch(conversationsPath(conversationsFilter), () => listConversations(conversationsFilter));
```
S :361 の依存 `[platformFilter, unreadOnly, pageIdFilter, t]` を `[cache, conversationsFilter, t]` にする。ほかの行（setAvatarErrors・transientErrorCountRef・catch・finally）は変えない。

(8) 送り元のページの選び肢（S :363-378 の注釈と useEffect の全部）を、次にする。
```ts
  // Page ID ドロップダウン用（フィルタなしの一覧を初回取得。選び肢は上の availablePageIds が写しから作る）
  useEffect(() => {
    cache.fetch(conversationsPath({}), () => listConversations({})).catch(() => {});
  }, [cache]);
```
(9) loadMessages（S :380-409）。S :384-385 の
```ts
      const data = await getMessages(leadId);
      setMessagesData(data);
```
を、次にする。
```ts
      await cache.fetch(messagesPath(leadId), () => getMessages(leadId));
      setMsgFailed(false);
      setMsgLoadCount((n) => n + 1);
```
S :405 の `setMessagesData(null);` を `setMsgFailed(true);` にする。S :409 の依存 `[t]` を `[cache, t]` にする。
自動スクロール（S :686-691）の依存 `[messagesData]` を `[messagesData, msgLoadCount]` にし、S :686 の注釈を次にする。
```ts
  // メッセージリスト末尾へ自動スクロール（中身が届くたび。写しは中身が同じなら同じ物を返すので、届いた回数も見る）
```
(10) loadLeadDetail（S :411-430）を、次の全部にする。
```ts
  const loadLeadDetail = useCallback(async (leadId: number) => {
    const path = `/leads/${leadId}`;
    // 入力欄の中身は、下書き（localStorage）があればそれを上に重ねる
    const formFrom = (data: LeadDetail): Partial<LeadDetail> => {
      try {
        const raw = localStorage.getItem(DRAFT_KEY(leadId));
        if (raw) {
          const savedDraft = JSON.parse(raw) as Partial<LeadDetail>;
          return { ...data, ...savedDraft };
        }
      } catch {
        // 下書きが読めない時は写しだけで作る
      }
      return { ...data };
    };
    // 写しがあれば、取りに行く前に入力欄を写しで埋める（戻った時に空の欄を出さない）
    const cached = cache.read<LeadDetail>(path);
    if (cached) setCardForm(formFrom(cached));
    try {
      const data = await cache.fetch(path, () => api.get<LeadDetail>(path));
      setLeadFailed(false);
      if (data) setCardForm(formFrom(data));
    } catch {
      setLeadFailed(true);
      setCardForm({});
    }
  }, [cache]);
```
(11) markRead（S :437-456）の依存 `[]`（S :456）を `[setConversations]` にする。中身は変えない。
(12) handleCardFieldBlur（S :495-515）。S :506 の `setLeadDetail(updated);` を、次の 2 行にする。S :515 の依存 `[leadDetail, cardForm, t]` を `[leadDetail, cardForm, cache, t]` にする。
```ts
      cache.write(`/leads/${leadDetail.id}`, updated);
      setLeadFailed(false);
```
(13) S :629（backToList）と S :638（onPageFilterChange）の `setLeadDetail(null);` の 2 行を消す（会話を選んでいない時は leadDetail が null になる・(6)）。S :650-653 の
```ts
    if (selectedLeadId === null) {
      setMessagesData(null);
      setLeadDetail(null);
      return;
    }
```
を、次にする（会話を選んでいない時は messagesData と leadDetail が null になる・(6)）。
```ts
    if (selectedLeadId === null) return;
```
(14) PC の自動選択（S :738 と S :744）の `convLoading` を `convShowLoading` にする（2 か所）。返す物の S :1075 の `    convLoading,` を `    convLoading: convShowLoading,` にする。
- ほかの setConversations の呼び出し（S :441・:945・:962・:986・:996・:1008・:1043・:1052・:1061）は 1 文字も変えない（(6) の setConversations が同じ形で受ける）。これらを含む useCallback の依存に setConversations が無くても、setConversations は uid が同じ間は同じ物なので、依存に足さない。eslint が足すよう警告した時だけ、その依存に setConversations を足す（§3(f)）。

## 4-D. #4 frontend/src/pages/inbox/useInboxState.autoSelectBadge.test.tsx（4 か所を変える）
(1) S :28 の次に、次の 1 行を足す。
```ts
import { queryClient } from "../../lib/query/apiQuery";
```
(2) S :55（useInboxSSE の偽物）の次に、次を足す（写しの置き場は useAuth で uid を読む。本物の AuthContext を読まないため）。
```ts
vi.mock("../../contexts/AuthContext", () => ({
  useAuth: () => ({ user: { uid: "uid-test" }, loading: false }),
}));
```
(3) S :67 の `vi.mock("../../lib/messages", () => ({` を、次の 4 行にする（path の作り方は本物を使う）。S :68-75 の中身と S :76 の閉じ `}));` は変えない。
```ts
vi.mock("../../lib/messages", async (importOriginal) => ({
  conversationsPath: (await importOriginal<typeof import("../../lib/messages")>()).conversationsPath,
  messagesPath: (await importOriginal<typeof import("../../lib/messages")>()).messagesPath,
```
（S :67 の 1 行を上の 3 行に置き換える。続く S :68 の `listConversations: …` からは今のまま。）
(4) S :100 の `beforeEach(() => {` の次の行に、次の 1 行を足す。
```ts
    queryClient.clear();
```

## 4-E. #5 frontend/src/pages/inbox/useInboxState.cache.test.tsx（新しいファイル・全文）
```tsx
/**
 * ADR-1054 会話の画面の写し（lead-chat-cache-card.md）の試験。
 * 1 本目 送る path が今と同じ・2 本目 戻った時に一覧・選び肢・メッセージ・カルテを写しから先に出す（K1）・
 * 3 本目 手元の書き換えが写しに残る・4 本目 利用者が変わると前の人の写しを出さない（K5）・
 * 5 本目 カルテの保存の後の中身を写しに書く。
 * QueryClient はアプリと同じ 1 個（apiQuery.ts の queryClient）を使い、毎回消す。
 */
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const auth = vi.hoisted(() => ({ user: { uid: "uid-A" } as { uid: string } | null }));
const listConversationsMock = vi.fn();
const getMessagesMock = vi.fn();
const markReadMock = vi.fn((_leadId: number, _opened?: boolean) => Promise.resolve({ marked_count: 0 }));
const apiGetMock = vi.fn();
const apiPatchMock = vi.fn();

vi.mock("react-router-dom", () => ({
  useNavigate: () => vi.fn(),
  useSearchParams: () => [new URLSearchParams(), vi.fn()],
}));
const stableT = (key: string) => key;
vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: stableT }),
}));
vi.mock("../../hooks/useIsMobile", () => ({ useIsMobile: () => false }));
vi.mock("../../hooks/useInboxSSE", () => ({ useInboxSSE: () => undefined }));
vi.mock("../../contexts/AuthContext", () => ({
  useAuth: () => ({ user: auth.user, loading: false }),
}));
vi.mock("../../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => apiGetMock(...args),
    post: vi.fn(() => Promise.resolve({})),
    patch: (...args: unknown[]) => apiPatchMock(...args),
    delete: vi.fn(() => Promise.resolve({})),
  },
  ApiError: class ApiError extends Error {
    status?: number;
  },
}));
vi.mock("../../lib/messages", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../lib/messages")>();
  return {
    conversationsPath: actual.conversationsPath,
    messagesPath: actual.messagesPath,
    listConversations: (...args: unknown[]) => listConversationsMock(...args),
    markRead: (...args: [number, boolean?]) => markReadMock(...args),
    markUnread: vi.fn(() => Promise.resolve({ unmarked_count: 0 })),
    getMessages: (...args: unknown[]) => getMessagesMock(...args),
    sendMessage: vi.fn(),
    sendImageMessage: vi.fn(),
    inferPlatform: vi.fn(() => "messenger"),
  };
});

import { conversationsPath, messagesPath } from "../../lib/messages";
import { queryClient } from "../../lib/query/apiQuery";
import { useInboxState } from "./useInboxState";

const conv = (leadId: number, name: string, pageId: string) => ({
  lead_id: leadId,
  lead_code: `LD-0000${leadId}`,
  customer_name: name,
  lead_status: null,
  platform: "messenger",
  page_id: pageId,
  last_message_text: "hi",
  last_message_at: "2026-11-01T00:00:00Z",
  last_message_direction: "inbound",
  unread_count: 1,
  messaging_window_expires_at: null,
  is_new_assignment: false,
});
const CONVS = { conversations: [conv(1, "Alice", "page-1"), conv(2, "Bob", "page-2")], next_cursor: null };
const MESSAGES = { lead: { id: 1, platform: "messenger" }, messages: [{ id: 10, text: "hello" }] };
const LEAD = { id: 1, customer_name: "Alice", status: "new" };
const never = () => new Promise<never>(() => {});

/** 1 回目に開いて、一覧・メッセージ・カルテが揃うまで待ち、閉じる */
async function openOnce() {
  const first = renderHook(() => useInboxState());
  await waitFor(() => expect(first.result.current.selectedLeadId).toBe(1));
  await waitFor(() => expect(first.result.current.messagesData).not.toBeNull());
  await waitFor(() => expect(first.result.current.leadDetail).not.toBeNull());
  await waitFor(() => expect(first.result.current.availablePageIds).toEqual(["page-1", "page-2"]));
  return first;
}

describe("useInboxState - 写しの置き場（ADR-1054 会話の画面）", () => {
  beforeEach(() => {
    queryClient.clear();
    localStorage.clear();
    auth.user = { uid: "uid-A" };
    listConversationsMock.mockReset().mockResolvedValue(CONVS);
    getMessagesMock.mockReset().mockResolvedValue(MESSAGES);
    markReadMock.mockClear();
    apiGetMock.mockReset().mockImplementation((path: string) =>
      path === "/leads/1" ? Promise.resolve(LEAD) : Promise.reject(new Error(`not used: ${path}`)),
    );
    apiPatchMock.mockReset();
  });

  it("送る path は今と同じ文字", () => {
    expect(conversationsPath({})).toBe("/conversations");
    expect(conversationsPath({ unread_only: false })).toBe("/conversations");
    expect(conversationsPath({ platform: "all", unread_only: true })).toBe("/conversations?unread_only=true");
    expect(conversationsPath({ platform: "instagram", unread_only: true, page_id: "page-1" })).toBe(
      "/conversations?platform=instagram&unread_only=true&page_id=page-1",
    );
    expect(messagesPath(5)).toBe("/leads/5/messages");
  });

  it("戻った時は、取りに行った物が返る前に、一覧・選び肢・メッセージ・カルテを写しから出す（K1）", async () => {
    const first = await openOnce();
    expect(apiGetMock.mock.calls.map((call) => call[0])).toContain("/leads/1");
    first.unmount();

    // 2 回目は、どの取り方も返らない
    listConversationsMock.mockImplementation(never);
    getMessagesMock.mockImplementation(never);
    apiGetMock.mockImplementation(never);

    const second = renderHook(() => useInboxState());
    // 最初の描画で、一覧と選び肢が出ていて、読み込み中ではない
    expect(second.result.current.conversations.map((c) => c.customer_name)).toEqual(["Alice", "Bob"]);
    expect(second.result.current.convLoading).toBe(false);
    expect(second.result.current.availablePageIds).toEqual(["page-1", "page-2"]);
    // 先頭の自動選択の後、メッセージとカルテが写しから出る
    await waitFor(() => expect(second.result.current.selectedLeadId).toBe(1));
    expect(second.result.current.messagesData?.messages).toHaveLength(1);
    expect(second.result.current.leadDetail?.customer_name).toBe("Alice");
    expect(second.result.current.cardForm.customer_name).toBe("Alice");
    second.unmount();
  });

  it("既読にした書き換えは写しに残り、戻った時もそのまま出る", async () => {
    markReadMock.mockImplementation(() => Promise.resolve({ marked_count: 1 }));
    const first = await openOnce();
    await waitFor(() =>
      expect(first.result.current.conversations.find((c) => c.lead_id === 1)?.unread_count).toBe(0),
    );
    first.unmount();

    listConversationsMock.mockImplementation(never);
    getMessagesMock.mockImplementation(never);
    apiGetMock.mockImplementation(never);
    const second = renderHook(() => useInboxState());
    expect(second.result.current.conversations.find((c) => c.lead_id === 1)?.unread_count).toBe(0);
    expect(second.result.current.conversations.find((c) => c.lead_id === 2)?.unread_count).toBe(1);
    second.unmount();
  });

  it("利用者が変わると、前の人の写しを出さない（K5）", async () => {
    const first = await openOnce();
    first.unmount();

    auth.user = { uid: "uid-B" };
    listConversationsMock.mockImplementation(never);
    getMessagesMock.mockImplementation(never);
    apiGetMock.mockImplementation(never);
    const second = renderHook(() => useInboxState());
    expect(second.result.current.conversations).toEqual([]);
    expect(second.result.current.convLoading).toBe(true);
    expect(second.result.current.availablePageIds).toEqual([]);
    expect(second.result.current.selectedLeadId).toBeNull();
    expect(second.result.current.messagesData).toBeNull();
    expect(second.result.current.leadDetail).toBeNull();
    second.unmount();
  });

  it("カルテを保存した後の中身を写しに書き、戻った時もそれを出す", async () => {
    apiPatchMock.mockResolvedValue({ ...LEAD, customer_name: "Alice renamed" });
    const first = await openOnce();
    act(() => {
      first.result.current.handleCardFieldChange("customer_name", "Alice renamed");
    });
    await act(async () => {
      await first.result.current.handleCardFieldBlur();
    });
    expect(apiPatchMock).toHaveBeenCalledTimes(1);
    expect(apiPatchMock.mock.calls[0][0]).toBe("/leads/1");
    expect(first.result.current.leadDetail?.customer_name).toBe("Alice renamed");
    first.unmount();

    listConversationsMock.mockImplementation(never);
    getMessagesMock.mockImplementation(never);
    apiGetMock.mockImplementation(never);
    const second = renderHook(() => useInboxState());
    await waitFor(() => expect(second.result.current.selectedLeadId).toBe(1));
    expect(second.result.current.leadDetail?.customer_name).toBe("Alice renamed");
    second.unmount();
  });
});
```
- 2 本目の「最初の描画」の確かめは、renderHook が返った直後（effect の後・取りに行った物が返る前）の値を見る。取り方はどれも返らない（never）ので、出ている中身は写しから来た物だけ。
- 5 本目の handleCardFieldChange・handleCardFieldBlur は S の useInboxState の返す物の名前（S :111 付近の型）。名前が違って落ちた時は §3(e) に従う。
- 試験の中の「Alice」などの英字は試験の見本の値で、画面の言葉ではない（i18n の決まりの外）。

## 4-F. 実装役の手順（1 手順 1 命令。<W> は手順1 で作られた作業場所の絶対パス）
手順1. クラウドの決まり（S scripts/agent-hooks/cloud/rules.md:15）どおり、作業場所を作り、push 済みの枝の先頭に合わせる（設計担当が §1 #6〜#8 を push 済み）。
  cd "$(git rev-parse --show-toplevel)" && bash scripts/new-worktree.sh release/line-like-speed-lead-chat-card
  （出力に出た作業場所の絶対パスを <W> として報告に書く。）
  cd <W> && git fetch origin release/line-like-speed-lead-chat-card
  cd <W> && git switch -C release/line-like-speed-lead-chat-card origin/release/line-like-speed-lead-chat-card
  cd <W> && git rev-parse HEAD origin/release/line-like-speed-lead-chat-card
  （2 行が同じことを確かめる。違えば停止して BLOCKED: で報告する。main は取り込まない。reset・rebase・force・merge・pull は使わない）
  cd <W> && ./scripts/dev/executor-preflight.sh > /tmp/lc-preflight.txt 2>&1
  cd <W> && grep -n "FAIL" /tmp/lc-preflight.txt | head -20
  cd <W> && grep -n "origin/main は存在" /tmp/lc-preflight.txt | head -3
  （FAIL の行の扱いは dashboard-cache-card.md §4-I 手順1 と同じ。`GitHub API に到達不可` の 1 件・`gh auth switch --hostname github.com --user shingo-cc` の失敗の 1 件・その結果の `PREFLIGHT FAIL` の行だけなら、`[OK]   origin/main は存在` の行があることを確かめて続ける。ほかの FAIL が 1 件でもあれば停止し、BLOCKED: で grep の出力を報告する。）
  cd <W> && git fetch origin main
  cd <W> && git diff --stat a6ef43ca7 origin/main -- frontend/src/lib/query frontend/src/lib/messages.ts frontend/src/pages/inbox frontend/src/test-setup.ts | tail -5
  （§3(a) の確かめ。空が正しい。）
手順2. 依存を入れ、§3(b)(c) を確かめ、変える前の lint の警告を数える。
  cd <W>/frontend && npm ci > /tmp/lc-ci.txt 2>&1
  cd <W> && tail -5 /tmp/lc-ci.txt
  cd <W>/frontend && grep -n '"@tanstack/react-query"' package.json
  cd <W> && git grep -n -E "setConversations|setLeadDetail|setMessagesData|setAvailablePageIds" -- frontend/src | head -30
  cd <W>/frontend && npx eslint src/lib/query/apiQuery.ts src/lib/messages.ts src/pages/inbox/useInboxState.ts src/pages/inbox/useInboxState.autoSelectBadge.test.tsx > /tmp/lc-lint-before.txt 2>&1
  cd <W> && tail -8 /tmp/lc-lint-before.txt
手順3. §4-A〜§4-D のとおり #1〜#4 を変え、§4-E の全文で #5 を作る。frontend/src/test-setup.ts は変えない。
手順4. 型を作ってから試験を流す（この 2 つの試験・全部の試験・型・lint）。作る型（frontend/src/api/generated/）は .gitignore で除かれるので commit に入らない。
  cd <W>/frontend && npm run generate:api-types > /tmp/lc-gen.txt 2>&1
  cd <W> && tail -3 /tmp/lc-gen.txt
  cd <W>/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/pages/inbox/useInboxState.cache.test.tsx src/pages/inbox/useInboxState.autoSelectBadge.test.tsx > /tmp/lc-unit.txt 2>&1
  cd <W> && tail -30 /tmp/lc-unit.txt
  cd <W>/frontend && npm run test:unit > /tmp/lc-unit-all.txt 2>&1
  cd <W> && tail -15 /tmp/lc-unit-all.txt
  （落ちた試験があれば、次の命令の出力で名前を見て §3(d) に従う。）
  cd <W> && grep -n -E "FAIL|✗|×" /tmp/lc-unit-all.txt | head -40
  cd <W>/frontend && npx tsc --noEmit -p . > /tmp/lc-tsc.txt 2>&1
  cd <W> && tail -20 /tmp/lc-tsc.txt
  cd <W>/frontend && npx eslint src/lib/query/apiQuery.ts src/lib/messages.ts src/pages/inbox/useInboxState.ts src/pages/inbox/useInboxState.autoSelectBadge.test.tsx src/pages/inbox/useInboxState.cache.test.tsx > /tmp/lc-lint.txt 2>&1
  cd <W> && tail -20 /tmp/lc-lint.txt
  （lint の警告が手順2 の数より増えていないこと・誤りが 0 であること。§3(f)。）
手順5. 本番と同じ形で組み立てられるか確かめる。
  cd <W>/frontend && npm run build > /tmp/lc-build.txt 2>&1
  cd <W> && tail -15 /tmp/lc-build.txt
手順6. 変わったファイルが §1 の #1〜#5 だけか確かめる。
  cd <W> && git status --short | head -20
  （#1〜#4 は M、#5 は ?? で出る。ほかが出たら停止して BLOCKED: で報告する。）
手順7. commit する。
  cd <W> && git add frontend/src/lib/query/apiQuery.ts frontend/src/lib/messages.ts frontend/src/pages/inbox/useInboxState.ts frontend/src/pages/inbox/useInboxState.autoSelectBadge.test.tsx frontend/src/pages/inbox/useInboxState.cache.test.tsx
  cd <W> && git commit -m "perf: 会話の画面の取り方を写しの置き場に載せる（ADR-1054）"
手順8. commit が在ることを確かめてから push する（--no-verify は使わない。push の前の検査が × なら直してから push。fast-forward でないと断られたら直さず BLOCKED:）。
  cd <W> && git log -3 --oneline
  cd <W> && git push -u origin release/line-like-speed-lead-chat-card
手順9. 報告を返す。PR は作らない（設計担当が手元で作る）。報告の 1 つの発言は 600 文字以内にして、番号付きの発言に分ける。

## 4-G. GO と承認・PO の操作
- PO の実装承認: 2026-11-01 PO 選択「1」（会話の画面と最初の画面が遅い理由を調べて、直して本番まで進める）。ADR-1054 は Accepted。このカードの審査合格の後に、設計担当がクラウドの Sonnet へ渡す。
- 触るのは frontend の会話の画面のフック・写しの置き場の足し算・path の作り方・その試験と書類だけで、migrations・deploy.yml・本番 scripts を含まない（番号付き GO の要る危ない PR ではない）。main へのマージで本番の画面に出る。マージは PO の委任に基づき設計担当（Claude Opus）が、マージ前の審査役の APPROVE と必須の確認すべての pass の後に行う。
- PO が操作することはない。

## 5. 受入（○×）
| # | 基準 | 検証方法 |
|---|---|---|
| C1 | §4-E の 5 本と §1 #4 の 5 本がすべて合格（送る path が今と同じ: §4-E 1 本目／K1: 2 本目で戻った時の最初の描画に一覧 2 件・選び肢 2 つ・読み込み中 false、自動選択の後にメッセージとカルテ／書き換えが写しに残る: 3・5 本目／K5: 4 本目で利用者を変えた後に前の人の一覧 0 件） | /tmp/lc-unit.txt の最後（2 files・10 passed）と、PR の CI の unit-run が success |
| C2 | 全部の試験・型・lint・組み立てが通る | /tmp/lc-unit-all.txt・lc-tsc.txt・lc-lint.txt・lc-build.txt の最後と、PR の必須の確認すべてが pass |
| C3 | 変わったのは §1 の 8 ファイルだけ | gh pr diff --name-only |
| C4 | マージの後、毎朝の画面の記録を手で 1 回動かし、/lead-chat の行で K1（戻った時の秒）≤0.1 秒、403・5xx が 0 件、API の数が 7 以下。ほかの行は K2 の最大と 2 秒を超えた画面の数が §3-4-11 から悪化していない。/lead-chat の K1 が下がらなければ §0 P4 の仮説は誤りと記録して止まる | prod-ui-check の実行の要約（設計担当。`gh workflow run prod-ui-check.yml --ref main` の後に要約の表を読む）。測る前に、その時の本番の反映が終わっていることを確かめる |
| C5 | マージの後、deploy が成功し、本番の画面が開く | deploy.yml の実行の結論 success と時刻。本番 https://app.salesanchor.jp/lead-chat が開く（設計担当） |

- C4・C5 の結果は docs/handoff/line-like-speed/design.md §3-4 に設計担当が書き足す。
- K5 を本番で 2 人のログインで確かめることはしない（本番でパスワードを打たない決まり）。K5 は C1 の 4 本目と、P5（写しの名前に uid が入る・利用者が変わると消える）で確かめたと記録に書く。

## 6. 戻し方
- マージの commit を git revert する PR を 1 つ出す。4 つの取り方は今の読み方（useState）に戻る。写しはメモリだけなので、戻した後に残る物は無い。DB には何も入っていない。

## 停止と報告
- §3 で「停止」とした時、試験が全部合格にならない時、§2 の触らない範囲を変えないと進めない時は、そこで停止する。
- 停止したら、何を実行し何が返ったかの生の出力（/tmp の報告ファイルの tail）を付けて、BLOCKED: か NEEDS_DECISION: で始まる報告を返す。推測で直さない。
- 終わったら DONE: で始まる報告に、§3 の確かめた結果、手順2・4・5 の tail、手順6 の git status、push した sha を書く。

END OF CARD
