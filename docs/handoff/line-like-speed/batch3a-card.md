# 段 3 の 1 回目の実装カード（遅い順の 10 画面を「写しを先に出して裏で取り直す」形に変える）

- 対象: docs/handoff/line-like-speed/design.md §3-2（部品）・§3-3（触らない範囲）・§3-4 の段 3・§3-5 の K1・K2・K5・§3-7。ADR-1054（Accepted）。段 2 のカード（docs/handoff/line-like-speed/stage2-card.md）の部品と形をそのまま使う。
- 根拠の写し: S=origin/main d0de518e22a8adc542ae935c409cfc8c39b9d5bc。行番号はすべてこの sha。2026-11-02 に設計担当が `git diff --stat d0de518e2 origin/main -- frontend/src` が空であることを確かめた。実装の前に最新の origin/main で行を合わせ直す（§3(a)）。
- 読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md・guards/03-file.md・guards/04-worktree.md・guards/05-pr.md・guards/10-executor.md・scripts/agent-hooks/cloud/rules.md（段 2 カードと同じ節。照合も同じ: 全命令は cd <W> で始める・出力は tail/head で上限・新しいファイルは丸ごとの全文・作業場所は new-worktree.sh で作り出力をパイプに通さない・PR は実行役が作らない・出力をファイルに残す命令と tail で読む命令は別の行）。
- 実行役はクラウドの Sonnet。作業場所の作り方はクラウドの決まり（S scripts/agent-hooks/cloud/rules.md:15）を正とする。.pr-number・gh-pr-create-safe.sh は使わない。出力には上限を付ける。待つために sleep を使わない。
- 状態: 第 2 版（2026-11-02 クラウドの審査役 Claude Opus が APPROVE。カードを全部当てて試験 2042 件・tsc・eslint・build が通り、壊し方 3 つはすべて Q3 で落ちた。軽い所見 2 件は直さない: (a) 編集 3 画面で最初の読み込みが失敗した時、空のフォームに打っても変わらない（誤りの文は出る・保存しても意味がない形なので今回は直さない）・(b) D4 の「:71 は残す」と置き換える塊の :71 が二重だが、置き換えの結果は同じ）。第 1 版の審査（REVISE・指摘 9 件）を直した: 行番号 3 か所・手順3 の確かめの例外・J1-5 の置き場の食い違い・K5 の部品だけの試験（Q3）・編集 3 画面の保存後の取り直し・請求書の取り方の誤りの文・Q1 の 4 画面の追加・並べ替えの推測の記録。
- 受領確認: 実装役は着手の最初の報告に「段 3 の 1 回目のカード 第 2 版を受け取った・S=d0de518e2」と書く。

## 0. 設計からの直し・詳しくした点（V3a。設計の合格線は変えない）
- V3a-1 対象は、段 2 の受入の回（prod-ui-check run 41346462841）で戻った時の秒（K1）が遅い順の 10 画面（11 行。/crm/leads と /crm は同じ画面）。PO 選択「1」（遅い順に 10 画面ずつ、本番の測定まで進める）。

  | 行 | 画面のファイル | K1 の基準（秒） |
  |---|---|---|
  | /admin/products | pages/products/ProductsPage.tsx | 0.63 |
  | /crm/companies/:id | pages/company-detail/useCompanyDetail.ts・CompanyDetailPage.tsx | 0.37 |
  | /invoices/:id | pages/invoice-detail/InvoiceDetailPage.tsx | 0.37 |
  | /crm | pages/leads/LeadsPage.tsx | 0.36 |
  | /crm/leads/:id/edit | pages/leads/LeadEditPage.tsx | 0.34 |
  | /crm/leads | pages/leads/LeadsPage.tsx | 0.34 |
  | /management-center/bots | pages/bots/BotsPage.tsx | 0.26 |
  | /bots | pages/bots/BotsPage.tsx | 0.25 |
  | /management-center/note-master | pages/note-master/NoteMasterPage.tsx | 0.22 |
  | /contacts/:id/edit | pages/contacts/ContactEditPage.tsx | 0.22 |
  | /bots/:id/edit | pages/bots/BotEditPage.tsx | 0.22 |

- V3a-2 写しの置き場の部品（S frontend/src/lib/query/apiQuery.ts）は変えない。使うのは useApiQuery（keepPrevious つき）・useInvalidateApi・useApiCache の write だけ。QueryClient を足さない・staleTime を設定しない・写しをブラウザの保存に書かない。
- V3a-3 一覧と詳しい画面（商品・取引先の詳しい画面・請求書の詳しい画面・リード一覧・Bot 一覧・注記マスタ）は段 2 と同じ形にする: 写しがあればすぐ出す・読み込み中の印（LoadingBlock）は写しが無い初回（isPending）だけ・写しを出したまま裏で取り直している間は見出しの横に小さな回る印（金型 components/loading の Spinner・size "sm"・PageLayout の headerLeft・S PageLayout.tsx:46）・取れなかった時の文は `error || 取り方の誤り` の 1 か所（段 2 の shownError の形）。条件（ページ・並び・絞り込み・検索）を変えた時は前の行を出したまま取る（keepPrevious）。前の行を出している間は「次へ」を押せなくする（段 2 の V2-3 と同じ理由）。
- V3a-4 編集の画面（Bot・担当者・リードの編集）は、新しい小さな部品 useSeededForm（frontend/src/lib/query/useSeededForm.ts・§4-A 全文）でフォームの初めの値を写しから作る。
  - フォームの初めの値は、写しが届いた時（または写しの名前が変わった時）に作る。名前には今の人の uid を入れる。人が変わった最初の描画では新しい名前の写しが無いので、フォームは空・読み込み中になる（K5）。
  - 人がまだ何も直していない時だけ、取り直した写しでフォームを作り直す。直し始めた後は作り直さない（打った文字を消さない）。
  - 保存は今と同じ（api.patch の後に一覧へ戻る）。保存した中身を写しに書き込まない。理由: 書き込むと、patch の返事の形が画面の形と違う時に壊れる。代わりに、一覧へ戻る直前にその 1 件の写しを古い印にする（useInvalidateApi・§4-C6・D6・E7）。画面がまだ開いているので裏で取り直しが始まり、次に編集を開いた時に保存前の古い中身を出さない。
- V3a-5 取引先の詳しい画面は、フォームが 3 つ（基本・販売チャネル・Discord）あり、書いた後に読み直す（S useCompanyDetail.ts:105・:124・:147・:160・:191・:224 の `await load()`）。load は「2 つの写しを取り直し、取れたら 3 つのフォームを作り直す」にする。写しの中身が前と同じ時、TanStack は前と同じ物を返す（structural sharing）ので、描画の時に写しの変化だけを見る形では作り直せない。だから load の中で取り直した結果を直接使う（refetch の結果が status "success" の時だけ）。refetch は失敗しても投げない（結果の status が "error"）ので、失敗は取り方の誤りとして画面の誤りの文に出る。
- V3a-6 リード一覧の「失注理由」の取り方の path は、closeReasons.ts に closeReasonsPath を足して 1 か所で作る（getCloseReasons もそれを使う）。リード一覧とリード編集が同じ写しを使う。
- V3a-7 担当者の編集の「会社の選択肢」は、取引先一覧と同じ path（`/companies?per_page=100`）なので同じ写しを使う。
- V3a-8 商品一覧の並び替え（ドラッグ）は、今は表を先に書き換える（楽観的な書き換え・S ProductsPage.tsx:100 `setProducts(next)`）。これを写しへの書き込み（useApiCache の write）にする。失敗した時の読み直し（S :109 `load()`）は写しの取り直しにする。
- V3a-9 今ある画面の試験は、画面が同じ 1 個の写しの置き場を使うので、`cleanup();` の後に必ず `queryClient.clear();` を足す（段 2 の §4-G と同じ。試験の途中の cleanup の後も）。請求書の試験（AllLegacyButtonOperationMigration）は今は人が null（ログインしていない）で画面を描く。useApiQuery はログインしていない間は取りに行かないので、請求書の試験だけは人を入れる（§4-K）。
- V3a-10 受入（§5 B5）は、11 行すべてで K1 ≤0.1 秒・K2 ≤2 秒・403 と 5xx が 0 件。K5 は本物の Bot 編集の画面の試験（Q2）で確かめる（本番で 2 人のログインは使わない）。

## 1. 触るファイル（変更前→変更後）
| # | ファイル | 変更前 | 変更後 |
|---|---|---|---|
| 1 | frontend/src/lib/query/useSeededForm.ts | 無い | 新しく作る（§4-A 全文） |
| 2 | frontend/src/api/closeReasons.ts | getCloseReasons が path を中で作る | closeReasonsPath を足し、getCloseReasons がそれを使う（§4-B） |
| 3 | frontend/src/pages/bots/BotEditPage.tsx | useState と useEffect で読む（S :37-61） | useApiQuery＋useSeededForm（§4-C） |
| 4 | frontend/src/pages/contacts/ContactEditPage.tsx | 同上（S :67-97） | 同上（§4-D） |
| 5 | frontend/src/pages/leads/LeadEditPage.tsx | 同上（S :77-129） | 同上（§4-E） |
| 6 | frontend/src/pages/leads/LeadsPage.tsx | 同上（S :125・:134・:142・:149-182） | useApiQuery（§4-F） |
| 7 | frontend/src/pages/bots/BotsPage.tsx | 同上（S :86-87・:96・:105-120） | 同上（§4-G） |
| 8 | frontend/src/pages/note-master/NoteMasterPage.tsx | 同上（S :98・:117-119・:135-148） | 同上（§4-H） |
| 9 | frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx | 同上（S :118-142） | 同上（§4-I） |
| 10 | frontend/src/pages/products/ProductsPage.tsx | 同上（S :31・:39-41・:53・:57-62・:135-161） | 同上（§4-J1） |
| 11 | frontend/src/pages/company-detail/useCompanyDetail.ts | 同上（S :21-24・:58-79・:268-269・:282-283） | 同上（§4-J2） |
| 12 | frontend/src/pages/company-detail/CompanyDetailPage.tsx | 回る印なし | 見出しの横に回る印（§4-J3） |
| 13〜21 | frontend/src/components/AccountCompanySaveButtonMigration.test.tsx・AllLegacyButtonDynamicMigration.test.tsx・AllLegacyButtonOperationMigration.test.tsx・BotFormButtonMigration.test.tsx・CommerceNavigationButtonMigration.test.tsx・FullPageFormButtonMigration.test.tsx・LeadFormButtonMigration.test.tsx・OrderLeadButtonMigration.test.tsx・frontend/src/pages/leads/LeadsPage.temperature.test.tsx | cleanup の後に写しを消さない | cleanup の後に queryClient.clear()（§4-K） |
| 22 | frontend/src/lib/query/batch3aPages.test.tsx | 無い | 新しく作る。Q1・Q2（§4-L 全文） |
| 23 | frontend/src/lib/query/useSeededForm.test.tsx | 無い | 新しく作る。Q3（§4-L2 全文） |
| 24 | docs/handoff/line-like-speed/batch3a-card.md | 無い | このカード（設計担当が書いた。実装役は触らない） |
| 25 | docs/handoff/line-like-speed/design.md | §3-4-12-a まで | §3-4-13 にこのカードの場所を書き足し済み（設計担当。実装役は触らない） |
| 26 | .claude-pipeline/active-work.d/release-line-like-speed-batch3a.md | 無い | 作業の札（設計担当。実装役は触らない） |

## 2. 触らない範囲
- backend/・migrations/・.github/workflows/・scripts/・tests/prod-check/・frontend/viewer/ は触らない（design §3-3）。
- frontend/src/lib/api.ts・frontend/src/contexts/AuthContext.tsx・frontend/src/lib/auth/・frontend/src/lib/query/apiQuery.ts・frontend/src/lib/query/QueryAuthSync.tsx・frontend/src/App.tsx は触らない。
- frontend/src/components/（PageLayout・Spinner・LoadingBlock を含む。試験のファイルは §4-K の行だけ）・CSS・ja.json・en.json は触らない。新しい言葉・色・寸法を足さない。
- 10 画面の中の、書き方（post・patch・delete の path と中身）・書き出し・表の列・ボタン・モーダル・ドロワー・フォームの欄は変えない。変えるのは §4 に書いた行だけ。
- QueryClient を作らない（試験の中でも作らない）。staleTime を設定しない。写しをブラウザの保存に書かない。
- ほかの画面は変えない（次の 10 画面は次のカード）。

## 3. 実装役が先に確かめること（想定分岐つき）
- (a) 最新の origin/main で `git diff --stat d0de518e2 origin/main -- frontend/src` が空か。空でなければ、変わったファイルの名前と行数を報告に書く。§1 #2〜#21 のどれかが変わっていたら停止して報告する。ほかのファイルだけなら続ける。
- (b) `cd <W>/frontend && grep -n '"@tanstack/react-query"' package.json` が `"5.104.4"` の 1 行。違えば停止して報告する。
- (c) §4 の「変更前」の文が、書かれた行にそのままあること。1 か所でも無い・2 か所以上ある時は、直さずに停止して BLOCKED: で `grep -n` の出力を報告する。
- (d) 手順 2 で、変える前の 12 ファイル（§1 #2〜#12 と closeReasons.ts）の lint の警告の数を数えておく。変えた後は、その数より増えないこと（0 になってもよい）。増えたら直す。直せない時は停止する。
- (e) Q1・Q2・Q3・今ある画面の試験のどれかが落ちたら、試験を書き換えて通さない（§4-K の行を除く）。画面の §4 の写し違いを探し、写し違いが無ければ停止して NEEDS_DECISION: で生の出力を返す。とくに Q2・Q3（K5）は、落ちたら直し方を自分で考えずに停止する。
- (f) LeadFormButtonMigration.test.tsx の「保存を 2 回待たせた時に /leads を 2 回読む」の試験は、取り直しを 2 回頼むと TanStack が 1 本目を止めて 2 本目を取る（既定の cancelRefetch）ので、api.get が 2 回呼ばれる見込み。落ちたら試験を変えずに停止して NEEDS_DECISION: で生の出力を返す。
- (g) 編集の 3 画面（Bot・担当者・リード）の今ある試験が、保存の後の取り直し（§4-C6・D6・D7・E7 で 1 回 GET が増える）のせいで落ちた時（例: GET の回数を数える試験・想定外の GET で投げる mock）は、試験も画面も変えずに停止して NEEDS_DECISION: で生の出力を返す。

## 4-A. #1 frontend/src/lib/query/useSeededForm.ts（新しく作る・全文）
```ts
/**
 * ADR-1054 段 3: 編集の画面のフォームの初めの値を写しから作る（この 1 か所だけ）。
 * - 名前（key）に今の人の uid を入れる。人が変わった最初の描画では写しが無いので、フォームは空で ready は false（K5）。
 * - 人がまだ直していない時だけ、取り直した写しでフォームを作り直す。直し始めた後は作り直さない。
 */
import { useCallback, useState, type Dispatch, type SetStateAction } from "react";

import { useAuth } from "../../contexts/AuthContext";

export function useSeededForm<D, F>(
  key: string,
  data: D | undefined,
  toForm: (d: D) => F,
  empty: F,
): { form: F; setForm: Dispatch<SetStateAction<F>>; ready: boolean } {
  const { user } = useAuth();
  const fullKey = `${user?.uid ?? ""}\u0000${key}`;
  const [seed, setSeed] = useState<{ key: string; data: D; form: F; base: F } | null>(null);
  if (data !== undefined && (seed === null || seed.key !== fullKey || (data !== seed.data && seed.form === seed.base))) {
    const form = toForm(data);
    setSeed({ key: fullKey, data, form, base: form });
  }
  const setForm = useCallback(
    (next: SetStateAction<F>) =>
      setSeed((s) =>
        s === null ? s : { ...s, form: typeof next === "function" ? (next as (p: F) => F)(s.form) : next },
      ),
    [],
  );
  const ready = data !== undefined && seed !== null && seed.key === fullKey;
  return { form: seed !== null && ready ? seed.form : empty, setForm, ready };
}
```
- 描画の途中で setSeed を呼ぶのは React の公式の「前の値から state を直す」形（react.dev の useState「Storing information from previous renders」）。条件が成り立つのは写しか名前が変わった時だけなので、繰り返さない。

## 4-B. #2 frontend/src/api/closeReasons.ts
- 変更前（getCloseReasons の中）: `const params = new URLSearchParams({ type });` と `return api.get<CloseReasonResponse[]>(`/close-reasons?${params.toString()}`);`
- 変更後: getCloseReasons の前に次を足し、getCloseReasons の中身を `return api.get<CloseReasonResponse[]>(closeReasonsPath(type));` の 1 行にする（引数の型と既定値は今のまま）。
```ts
/** 失注・成約の理由の一覧の path（画面の写しの名前もここで決まる・ADR-1054） */
export function closeReasonsPath(type: "won" | "lost" = "lost") {
  return `/close-reasons?${new URLSearchParams({ type }).toString()}`;
}
```
- getCloseReasons の引数の型が "won" | "lost" でない時は、closeReasonsPath の引数の型を getCloseReasons と同じにする（`grep -n "export function getCloseReasons" frontend/src/api/closeReasons.ts` の出力を報告に書く）。

## 4-C. #3 frontend/src/pages/bots/BotEditPage.tsx
- C1 S :10 `import { useEffect, useState, type FormEvent } from "react";` → `import { useState, type FormEvent } from "react";`
- C2 S :15 `import { api } from "../../lib/api";` の次に足す:
  `import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";` と `import { useSeededForm } from "../../lib/query/useSeededForm";`
- C3 S :31 `};`（emptyForm の終わり）の次に、空行を 1 つ置いて足す:
```ts
const formFromBot = (bot: Bot): BotFormState => ({
  display_name: bot.display_name,
  purpose: bot.purpose,
  status: bot.status,
  owner_staff_id: String(bot.owner_staff_id),
  discord_user_id: bot.discord_user_id ?? "",
  sender_email: bot.sender_email ?? "",
});
```
- C4 S :37-61（`const [form, setForm] = ...` から useEffect の終わり `}, [id, t]);` まで）を次に置き換える:
```ts
  const botQ = useApiQuery<Bot>(`/bots/${id}`, { enabled: id !== undefined });
  const staffQ = useApiQuery<BotStaff[]>("/staff");
  const { form, setForm, ready } = useSeededForm(`bot/${id}`, botQ.data, formFromBot, emptyForm);
  const staff = staffQ.data ?? [];
  const [error, setError] = useState("");
  const loadError = botQ.error ?? staffQ.error;
  const loading = loadError === null && !(ready && staffQ.data !== undefined);
  const shownError = error || (loadError ? (loadError instanceof Error ? loadError.message : t("common.fetchError")) : "");
  const invalidate = useInvalidateApi();
```
- C5 S :83 `{error && <div className="error-message">{error}</div>}` → `{shownError && <div className="error-message">{shownError}</div>}`
- C6 handleSubmit の中の S :75 `      navigate("/bots");`（字下げ 6 つ。:93 の取り消しの `onClick={() => navigate("/bots")}` ではない）の前の行に、同じ字下げで `      void invalidate(["bots", id ?? ""]);` を足す。
- handleSubmit のほかの行・:84 の `{loading ? ...}`・フォームの欄は変えない。

## 4-D. #4 frontend/src/pages/contacts/ContactEditPage.tsx
- D1 S :9 `import { useEffect, useState, type FormEvent } from "react";` → `import { useState, type FormEvent } from "react";`
- D2 S :15 `import { api } from "../../lib/api";` の次に足す: `import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";` と `import { useSeededForm } from "../../lib/query/useSeededForm";`
- D3 emptyForm の終わり（S :61 `};`）の次に、空行を 1 つ置いて足す:
```ts
const formFromContact = (contact: Contact): FormState => ({
  company_id: String(contact.company_id),
  surname: contact.surname ?? "",
  given_name: contact.given_name ?? "",
  display_name: contact.display_name ?? "",
  job_title: contact.job_title ?? "",
  department: contact.department ?? "",
  is_primary_contact: contact.is_primary_contact,
  primary_email: contact.primary_email ?? "",
  primary_phone: contact.primary_phone ?? "",
  status: contact.status,
  notes: contact.notes ?? "",
});
```
- D4 S :67-97（`const [form, setForm] = ...` から useEffect の終わり `}, [id, t]);` まで）を次に置き換える（:71 の dedupSubmitting の行は残す）:
```ts
  const contactQ = useApiQuery<Contact>(`/contacts/${id}`, { enabled: id !== undefined });
  const companiesQ = useApiQuery<CompanyMini[]>("/companies?per_page=100");
  const { form, setForm, ready } = useSeededForm(`contact/${id}`, contactQ.data, formFromContact, emptyForm);
  const companies = companiesQ.data ?? [];
  const [error, setError] = useState("");
  const loadError = contactQ.error ?? companiesQ.error;
  const loading = loadError === null && !(ready && companiesQ.data !== undefined);
  const shownError = error || (loadError ? (loadError instanceof Error ? loadError.message : t("common.fetchError")) : "");
  const invalidate = useInvalidateApi();
  const [dedupSubmitting, setDedupSubmitting] = useState(false);
```
- D5 S :140 `{error && <div className="error-message">{error}</div>}` → `{shownError && <div className="error-message">{shownError}</div>}`
- D6 handleSubmit の中の S :119 `      navigate("/contacts");` の前の行に、同じ字下げで `      void invalidate(["contacts", id ?? ""]);` を足す（:215 の取り消しの navigate ではない）。
- D7 handleResolveAsDistinct の中の S :130 `      setForm((p) => ({ ...p, status: "active" }));` の次の行に、同じ字下げで `      void invalidate(["contacts", id ?? ""]);` を足す。
- handleSubmit と handleResolveAsDistinct のほかの行（:129 の patch・:130 の setForm を含む）は変えない。

## 4-E. #5 frontend/src/pages/leads/LeadEditPage.tsx
- E1 S :8 `import { useEffect, useState, type FormEvent } from "react";` → `import { useState, type FormEvent } from "react";`
- E2 S :16 `import { api } from "../../lib/api";` の次に足す: `import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";` と `import { useSeededForm } from "../../lib/query/useSeededForm";`
- E3 S :18 `import { getCloseReasons, type CloseReasonResponse } from "../../api/closeReasons";` → `import { closeReasonsPath, type CloseReasonResponse } from "../../api/closeReasons";`
- E4 S :71 `const LEAD_STATUSES: LeadStatusCode[] = [...LEAD_STATUS_CODES];` の次に、空行を 1 つ置いて足す:
```ts
const formFromLead = (lead: Lead): FormState => ({
  customer_name: lead.customer_name,
  company_name: lead.company_name || "",
  email: lead.email || "",
  phone: lead.phone || "",
  channel_type: lead.channel_type || "",
  initiative: lead.initiative || "",
  type: lead.type || "",
  status: lead.status,
  temperature: lead.temperature || "",
  estimated_scale: lead.estimated_scale || "",
  customer_type: lead.customer_type || "",
  response_speed: lead.response_speed || "",
  monthly_forecast: lead.monthly_forecast != null ? String(lead.monthly_forecast) : "",
  notes: lead.notes || "",
  country: lead.country || "",
  close_reason_id: "",
  close_reason_memo: "",
});
```
- E5 S :77-129（`const [form, setForm] = ...` から useEffect の終わり `}, [id, t]);` まで）を次に置き換える:
```ts
  const leadQ = useApiQuery<Lead>(`/leads/${id}`, { enabled: id !== undefined });
  const reasonsQ = useApiQuery<CloseReasonResponse[]>(closeReasonsPath("lost"));
  const { form, setForm, ready } = useSeededForm(`lead/${id}`, leadQ.data, formFromLead, emptyForm);
  const [error, setError] = useState("");
  const loading = leadQ.isError ? false : (!ready || reasonsQ.isPending);
  const closeReasonOptions = reasonsQ.data ?? [];
  const loadError = leadQ.error ?? reasonsQ.error;
  const shownError = error || (loadError ? (loadError instanceof Error ? loadError.message : t("common.fetchError")) : "");
  const invalidate = useInvalidateApi();
```
- E6 S :168 `{error && <div className="error-message">{error}</div>}` → `{shownError && <div className="error-message">{shownError}</div>}`
- E7 handleSubmit の中の S :160 `      navigate("/crm/leads");` の前の行に、同じ字下げで `      void invalidate(["leads", id ?? ""]);` を足す（:293 の取り消しの navigate ではない）。
- handleSubmit のほかの行・`setForm({ ...form, ... })` の欄（S :174-288）は変えない。

## 4-F. #6 frontend/src/pages/leads/LeadsPage.tsx
- F1 S :12 `import { useCallback, useEffect, useState, FormEvent } from "react";` → `import { useCallback, useState, FormEvent } from "react";`
- F2 S :36 `import { getCloseReasons, type CloseReasonResponse } from "../../api/closeReasons";` → `import { closeReasonsPath, type CloseReasonResponse } from "../../api/closeReasons";`
- F3 S :39 `import { LoadingBlock } from "../../components/loading";` → `import { LoadingBlock, Spinner } from "../../components/loading";` とし、その次に `import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";` を足す。
- F4 S :125 `const [leads, setLeads] = useState<Lead[]>([]);` を消す。
- F5 S :134 `const [loading, setLoading] = useState(true);` を消す。
- F6 S :142 `const [closeReasonOptions, setCloseReasonOptions] = useState<CloseReasonResponse[]>([]);` を消す。
- F7 S :149-182（loadLeads の useCallback と、その後の 2 つの useEffect）を次に置き換える:
```ts
  const leadsPath = `/leads${statusFilter ? `?status=${encodeURIComponent(statusFilter)}` : ""}`;
  const leadsQ = useApiQuery<Lead[]>(leadsPath, { keepPrevious: true });
  const leads = leadsQ.data ?? [];
  const reasonsQ = useApiQuery<CloseReasonResponse[]>(closeReasonsPath("lost"));
  const closeReasonOptions = reasonsQ.data ?? [];
  const invalidate = useInvalidateApi();
  const loadLeads = useCallback(() => invalidate(["leads"]), [invalidate]);
  const loadError = leadsQ.error ?? reasonsQ.error;
  const shownError = error || (loadError ? (loadError instanceof Error ? loadError.message : t("common.fetchError")) : "");
```
- F8 S :298-302 の `<PageLayout navKey="nav.leadsSection" subtitleKey="leads.subtitle">`（3 行に分かれている）の subtitleKey の次の行に足す:
  `      headerLeft={leadsQ.isFetching && !leadsQ.isPending ? <Spinner size="sm" /> : undefined}`
- F9 S :321 `{error && <div className="error-message">{error}</div>}` → `{shownError && <div className="error-message">{shownError}</div>}`
- F10 S :479 `{loading ? (` → `{leadsQ.isPending ? (`
- loadLeads の呼び出し（S :187 の useSSE・:215・:244・:256・:286・:556）・:521 `data={leads}`・:541 `closeReasonOptions={closeReasonOptions}` は変えない。

## 4-G. #7 frontend/src/pages/bots/BotsPage.tsx
- G1 S :10 `import { LoadingBlock } from "../../components/loading";` → `import { LoadingBlock, Spinner } from "../../components/loading";`
- G2 S :11 `import { useEffect, useState, FormEvent } from "react";` → `import { useState, FormEvent } from "react";`
- G3 S :18 `import { api } from "../../lib/api";` の次に `import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";` を足す。
- G4 S :86-87 の 2 行（bots と staff の useState）を次に置き換える:
```ts
  const botsQ = useApiQuery<Bot[]>("/bots", { keepPrevious: true });
  const staffQ = useApiQuery<BotStaff[]>("/staff");
  const bots = botsQ.data ?? [];
  const staff = staffQ.data ?? [];
  const invalidate = useInvalidateApi();
```
- G5 S :96 `const [loading, setLoading] = useState(true);` を消す。
- G6 S :105-120（loadAll・eslint-disable の行・useEffect）を次に置き換える:
```ts
  const loadAll = () => {
    void invalidate(["bots"]);
    void staffQ.refetch();
  };
  const loadError = botsQ.error ?? staffQ.error;
  const shownError = error || (loadError ? (loadError instanceof Error ? loadError.message : t("common.fetchError")) : "");
```
- G7 S :199-202 の PageLayout の `subtitleKey="bots.subtitle"` の次の行に足す:
  `      headerLeft={botsQ.isFetching && !botsQ.isPending ? <Spinner size="sm" /> : undefined}`
- G8 S :203 `{error && <div className="error-message">{error}</div>}` → `{shownError && <div className="error-message">{shownError}</div>}`
- G9 S :291 `{loading ? (` → `{botsQ.isPending ? (`
- loadAll の呼び出し（S :144・:167・:180・:192）・:253・:282 の staff・:324 `data={bots}` は変えない。

## 4-H. #8 frontend/src/pages/note-master/NoteMasterPage.tsx
- H1 S :8 `import { LoadingBlock } from "../../components/loading";` → `import { LoadingBlock, Spinner } from "../../components/loading";`
- H2 S :9 `import { useEffect, useMemo, useRef, useState, FormEvent } from "react";` → `import { useMemo, useRef, useState, FormEvent } from "react";`
- H3 S :12 `import { api } from "../../lib/api";` の次に `import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";` を足す。
- H4 S :98 `const [notes, setNotes] = useState<TcgNoteMaster[]>([]);` を消す（:99 の error は残す。書き出しも使う）。
- H5 S :117 `const [loading, setLoading] = useState(true);` を消す。:118 の page は残す。:119 `const [hasNext, setHasNext] = useState(false);` を消す。
- H6 S :118 の page の行の次に足す:
```ts
  const notesQ = useApiQuery<TcgNoteMaster[]>(
    `/note-master?${new URLSearchParams({ page: String(page), per_page: String(PER_PAGE) }).toString()}`,
    { keepPrevious: true },
  );
  const notes = notesQ.data ?? [];
  const invalidate = useInvalidateApi();
  const shownError = error || (notesQ.error ? (notesQ.error instanceof Error ? notesQ.error.message : t("common.fetchError")) : "");
```
- H7 S :135-148（load・eslint-disable の行・useEffect）を次に置き換える:
```ts
  const load = () => {
    void invalidate(["note-master"]);
  };
```
- H8 S :360-382 の PageLayout の `subtitleKey={`${f}.description`}` の次の行に足す:
  `      headerLeft={notesQ.isFetching && !notesQ.isPending ? <Spinner size="sm" /> : undefined}`
- H9 S :383 `{error && <div className="error-message">{error}</div>}` → `{shownError && <div className="error-message">{shownError}</div>}`
- H10 S :387 `{loading ? (` → `{notesQ.isPending ? (`
- H11 S :397 `hasNextPage={hasNext}` → `hasNextPage={notes.length === PER_PAGE && !notesQ.isPlaceholderData}`
- load の呼び出し（S :171・:199・:210）・:392 `data={notes}` は変えない。

## 4-I. #9 frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx
- I1 S :9 `import { useEffect, useState } from "react";` → `import { useState } from "react";`
- I2 S :12 `import { api } from "../../lib/api";` の次に `import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";` を足す。
- I3 S :20 `import { LoadingBlock } from "../../components/loading";` → `import { LoadingBlock, Spinner } from "../../components/loading";`
- I4 S :118-121（invoice・disputes・error・loading の useState の 4 行）を次に置き換える:
```ts
  const invoiceQ = useApiQuery<InvoiceDetail>(`/invoices/${id}`, { enabled: id !== undefined });
  // ADR-101改訂(2) Inc4: 紐づく PayPal ケース（失敗しても本体表示は妨げない）
  const disputesQ = useApiQuery<PaypalDispute[]>(`/invoices/${id}/paypal-disputes`, { enabled: id !== undefined });
  const invoice = invoiceQ.data ?? null;
  const disputes = disputesQ.data ?? [];
  const [error, setError] = useState("");
  const shownError = error || (invoiceQ.error ? (invoiceQ.error instanceof Error ? invoiceQ.error.message : t("common.fetchError")) : "");
  const invalidate = useInvalidateApi();
```
- I5 S :126-142（load・eslint-disable の行・useEffect）を次に置き換える:
```ts
  const load = () => {
    void invalidate(["invoices", id ?? ""]);
  };
```
- I6 S :192 `if (loading) return <div className="page"><LoadingBlock /></div>;` → `if (invoiceQ.isPending) return <div className="page"><LoadingBlock /></div>;`
- I7 S :193 の `{error || t("common.fetchError")}` → `{shownError || t("common.fetchError")}`
- I8 S :199-202 の PageLayout の `subtitleKey="invoices.detailSubtitle"` の次の行に足す:
  `      headerLeft={invoiceQ.isFetching && !invoiceQ.isPending ? <Spinner size="sm" /> : undefined}`
- I9 S :235 `      {error && <div className="error-message">{error}</div>}` → `      {shownError && <div className="error-message">{shownError}</div>}`（写しを出したまま取り直しに失敗した時も文を出す）
- doAction（S :144-151 の `load();`）・:262・:275 の disputes は変えない。ケースの取り方の誤りは今と同じく出さない。

## 4-J1. #10 frontend/src/pages/products/ProductsPage.tsx
- J1-1 S :25 `import { LoadingBlock } from "../../components/loading";` → `import { LoadingBlock, Spinner } from "../../components/loading";` とし、その次に `import { useApiCache, useApiQuery } from "../../lib/query/apiQuery";` を足す。:12 の useEffect は残す（S :156-158 の検索の時にページを戻す effect が使う）。
- J1-2 S :31 `const [products, setProducts] = useState<Product[]>([]);` を消す。
- J1-3 S :39-41 の hasNext と loading の useState（:39 `const [hasNext, setHasNext] = useState(false);`・:41 `const [loading, setLoading] = useState(true);`）を消す。:40 の error は残す。:36-38 の説明のコメントは残す。
- J1-4 S :53 `const [tcgTypes, setTcgTypes] = useState<{ code: string; name_ja: string }[]>([]);` と S :56-62（説明のコメントと tcg-types の useEffect）を次に置き換える:
```ts
  // TCG種別マスタ一覧を取得（絞り込みフィルタ + 「タイプ」列の表示名解決用。取れない時は空のまま）
  const tcgTypesQ = useApiQuery<{ code: string; name_ja: string }[]>("/products/tcg-types");
  const tcgTypes = tcgTypesQ.data ?? [];
```
  （:54 の navigate の行は残す。）
- J1-5 S :135-153（load）と S :160-161（eslint-disable の行と load の useEffect）は消すだけにする（:155-158 の検索の effect は残す）。次の塊を S :62 の後（J1-4 で置いた tcgTypes の行の次）に置く。理由: products を使う最初の関数（S :91 の onReorderDrop）より前に要る:
```ts
  const productsParams = new URLSearchParams();
  if (search) productsParams.set("search", search);
  if (sort) productsParams.set("sort", sort);
  if (tcgType) productsParams.set("work_code", tcgType);
  productsParams.set("page", String(page));
  productsParams.set("per_page", String(PER_PAGE));
  const productsPath = `/products?${productsParams.toString()}`;
  const productsQ = useApiQuery<Product[]>(productsPath, { keepPrevious: true });
  const products = productsQ.data ?? [];
  // 返ってきた件数が PER_PAGE と同じなら、次ページ存在の可能性あり
  const hasNext = products.length === PER_PAGE;
  const loading = productsQ.isPending;
  const cache = useApiCache();
  const load = () => {
    void productsQ.refetch();
  };
  const shownError = error || (productsQ.error ? (productsQ.error instanceof Error ? productsQ.error.message : t("common.fetchError")) : "");
```
- J1-6 S :100 `setProducts(next); // 楽観的更新` → `cache.write(productsPath, next); // 楽観的更新`
- J1-7 S :285 `{error && <div className="error-message">{error}</div>}` → `{shownError && <div className="error-message">{shownError}</div>}`
- J1-8 S :442 `disabled={!hasNext}` → `disabled={!hasNext || productsQ.isPlaceholderData}`
- J1-9 S :469 `<PageLayout navKey="nav.products" subtitleKey="products.subtitle">` → `<PageLayout navKey="nav.products" subtitleKey="products.subtitle" headerLeft={productsQ.isFetching && !productsQ.isPending ? <Spinner size="sm" /> : undefined}>`
- :109 `load(); // 失敗時はサーバ状態へ再同期`・:189 の `load();`・:287 `{loading ? (`・:408 `!loading && products.length > 0`・:429 `disabled={page <= 1}`・:463-467 の embedded は変えない。
- 記録だけ（直さない・まだ確かめていない）: 並べ替えの直後に、別の理由の裏の取り直しが返ると、並べた順が一瞬前に戻るかもしれない（第 1 版の審査の推測）。今の画面（setProducts の後に load）と同じ種類の動きで、この段では変えない。

## 4-J2. #11 frontend/src/pages/company-detail/useCompanyDetail.ts
- J2-1 S :6 `import { useEffect, useState, FormEvent } from "react";` → `import { useState, FormEvent } from "react";`
- J2-2 S :8 `import { api } from "../../lib/api";` の次に足す: `import { useAuth } from "../../contexts/AuthContext";` と `import { useApiQuery } from "../../lib/query/apiQuery";`
- J2-3 S :21-24（company・contacts・loading・error の useState の 4 行）を次に置き換える:
```ts
  const { user } = useAuth();
  const companyQ = useApiQuery<Company>(`/companies/${id}`, { enabled: id !== undefined });
  const contactsQ = useApiQuery<Contact[]>(`/companies/${id}/contacts`, { enabled: id !== undefined });
  const company = companyQ.data ?? null;
  const contacts = contactsQ.data ?? [];
  const loading = companyQ.isPending || contactsQ.isPending;
  const refreshing = (companyQ.isFetching || contactsQ.isFetching) && !loading;
  const [error, setError] = useState("");
  const loadError = companyQ.error ?? contactsQ.error;
  const shownError = error || (loadError ? (loadError instanceof Error ? loadError.message : t("common.fetchError")) : "");
  // 3 つのフォームの初めの値は、写しの人と id が変わった時に作る（K5: 名前に uid を入れる）
  const seedKey = `${user?.uid ?? ""}\u0000${id ?? ""}`;
  const [seeded, setSeeded] = useState<{ key: string; data: Company } | null>(null);
```
- J2-4 S :56 `const [mergeModalOpen, setMergeModalOpen] = useState(false);` の次に、空行を 1 つ置いて足す:
```ts
  // 写しが届いた時・人か id が変わった時にフォームを作る。取り直しで中身が変わった時は、直していないフォームだけ作り直す。
  if (companyQ.data !== undefined && (seeded === null || seeded.key !== seedKey || seeded.data !== companyQ.data)) {
    const c = companyQ.data;
    const fresh = seeded === null || seeded.key !== seedKey;
    if (fresh || !basicDirty) { setBasicForm(basicFromApi(c)); setBasicDirty(false); }
    if (fresh || !channelsDirty) { setChannelsText(c.sales_channels.join(", ")); setChannelsDirty(false); }
    if (fresh || !discordDirty) { setDiscordForm(c.discord ? discordFromApi(c.discord) : emptyDiscordForm()); setDiscordDirty(false); }
    setSeeded({ key: seedKey, data: c });
  }
```
- J2-5 S :58-79（load・eslint-disable の行・useEffect）を次に置き換える:
```ts
  // 書いた後の読み直し。2 つの写しを取り直し、取れたら 3 つのフォームを作り直す（中身が前と同じでも作り直す・V3a-5）。
  const load = async () => {
    if (!id) return;
    const [c] = await Promise.all([companyQ.refetch(), contactsQ.refetch()]);
    if (c.status === "success") {
      const d = c.data;
      setBasicForm(basicFromApi(d));
      setChannelsText(d.sales_channels.join(", "));
      setBasicDirty(false);
      setChannelsDirty(false);
      setDiscordForm(d.discord ? discordFromApi(d.discord) : emptyDiscordForm());
      setDiscordDirty(false);
      setSeeded({ key: seedKey, data: d });
    }
  };
```
- J2-6 S :268-269 の 2 行（`const list = await api.get<Contact[]>(`/companies/${company.id}/contacts`);` と `setContacts(list);`）→ `await contactsQ.refetch();`
- J2-7 S :282-283 の同じ 2 行 → `await contactsQ.refetch();`
- J2-8 S :305 の return の最初の行 `company, contacts, loading, error, setError,` → `company, contacts, loading, refreshing, error: shownError, setError,`
- `await load()`（S :105・:124・:147・:160・:191・:224）は変えない。

## 4-J3. #12 frontend/src/pages/company-detail/CompanyDetailPage.tsx
- J3-1 S :30 `import { LoadingBlock } from "../../components/loading";` → `import { LoadingBlock, Spinner } from "../../components/loading";`
- J3-2 S :42 `company, contacts, loading, error,` → `company, contacts, loading, refreshing, error,`
- J3-3 S :94 `subtitleKey="companies.detailSubtitle"` の次の行に足す:
  `        headerLeft={refreshing ? <Spinner size="sm" /> : undefined}`
- ほかの行は変えない。

## 4-K. #13〜#21 今ある画面の試験の後片付け（ほかの行は変えない）
- components の 8 本は `import { queryClient } from '../lib/query/apiQuery';`、pages/leads の 1 本は `import { queryClient } from '../../lib/query/apiQuery';` を足す。`cleanup();` の直後に `queryClient.clear();` を足す（同じ行の中なら `cleanup(); queryClient.clear();`、`cleanup();` だけの行なら次の行に同じ字下げで）。

  | ファイル | import を足す位置（その行の次） | clear を足す cleanup の行 |
  |---|---|---|
  | AccountCompanySaveButtonMigration.test.tsx | S :9 `import en from '../locales/en.json';` | S :31（afterEach）・S :78（試験の途中） |
  | AllLegacyButtonDynamicMigration.test.tsx | S :10 `import en from '../locales/en.json';` | S :25 |
  | AllLegacyButtonOperationMigration.test.tsx | S :9 `import en from '../locales/en.json';` | S :33 |
  | BotFormButtonMigration.test.tsx | S :9 `import en from '../locales/en.json';` | S :76 |
  | CommerceNavigationButtonMigration.test.tsx | S :13 `import en from '../locales/en.json';` | S :42（afterEach）・S :90（試験の途中） |
  | FullPageFormButtonMigration.test.tsx | S :6 `import SupplierEditPage from '../pages/suppliers/SupplierEditPage';` | S :88（`  cleanup();` だけの行。次の行に `  queryClient.clear();`） |
  | LeadFormButtonMigration.test.tsx | S :9 `import en from '../locales/en.json';` | S :88 |
  | OrderLeadButtonMigration.test.tsx | S :8 `import en from '../locales/en.json';` | S :44 |
  | pages/leads/LeadsPage.temperature.test.tsx | S :7 | S :23（`  cleanup();` だけの行。次の行に `  queryClient.clear();`） |

- K-op AllLegacyButtonOperationMigration.test.tsx の請求書の試験だけ人を入れる（V3a-9）:
  - S :12 → `const auth = vi.hoisted(() => ({ signIn: vi.fn(), signInWithPasskey: vi.fn(), sendPasswordReset: vi.fn(), user: null as { uid: string } | null }));`
  - S :15 `  useAuth: () => ({ ...auth, user: null, loading: false }),` → `  useAuth: () => ({ ...auth, loading: false }),`
  - beforeEach（S :29 の `vi.resetAllMocks(); instance = createInstance();`）の行末に ` auth.user = null;` を足す。
  - 請求書の試験（S :79 `it('opens invoice PDF boundaries exactly and performs no API write', async () => {`）の次の行の頭（S :80 の `const invoice = ...` の前）に `auth.user = { uid: 'fixture-user' };` の 1 行を足す。
- K-lt pages/leads/LeadsPage.temperature.test.tsx:
  - S :12 の closeReasons の mock → `vi.mock("../../api/closeReasons", () => ({ getCloseReasons: vi.fn(async () => []), closeReasonsPath: () => "/close-reasons?type=lost" }));`
  - S :37 の api.get の mock → `vi.mocked(api.get).mockImplementation(async (url: string) => url.startsWith("/close-reasons") ? [] : [row(1, "Hot"), row(2, null)]);`（mock の名前・row の引数は S の行のまま。S の行が `mockResolvedValue` の形でない時は、その行の生の文を報告に書いて停止する）
- 理由: 画面が同じ 1 個の写しの置き場を使うので、前の試験の写しが次の試験に残らないようにする。

## 4-L. #22 frontend/src/lib/query/batch3aPages.test.tsx（新しく作る・全文）
```tsx
/**
 * ADR-1054 段 3 の 1 回目: 本物の画面の試験（Q1・Q2）。
 * Q1 戻った時に写しを先に出す（読み込み中の印を出さない）・Q2 利用者が変わっても前の人のフォームを出さない（K5）。
 * QueryClient はアプリと同じ 1 個（apiQuery.ts の queryClient）を使い、毎回消す。
 */
import type { ComponentType } from "react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BotEditPage from "../../pages/bots/BotEditPage";
import BotsPage from "../../pages/bots/BotsPage";
import CompanyDetailPage from "../../pages/company-detail/CompanyDetailPage";
import ContactEditPage from "../../pages/contacts/ContactEditPage";
import InvoiceDetailPage from "../../pages/invoice-detail/InvoiceDetailPage";
import LeadEditPage from "../../pages/leads/LeadEditPage";
import LeadsPage from "../../pages/leads/LeadsPage";
import NoteMasterPage from "../../pages/note-master/NoteMasterPage";
import ProductsPage from "../../pages/products/ProductsPage";
import { api } from "../api";
import { QueryAuthSync } from "./QueryAuthSync";
import { queryClient } from "./apiQuery";

const auth = vi.hoisted(() => ({ user: { uid: "uid-A" } as { uid: string } | null }));

vi.mock("../../contexts/AuthContext", () => ({
  useAuth: () => ({ user: auth.user, loading: false }),
}));
vi.mock("../auth/provider", () => ({ isSelfAuth: () => false }));
vi.mock("../auth/selfAuth", () => ({
  getAccessToken: async () => "test-token",
  expireSession: vi.fn(),
  selfRefresh: vi.fn(),
}));
vi.mock("../../hooks/usePermissions", () => ({ usePermissions: () => ({ hasPermission: () => true }) }));
vi.mock("../../hooks/useSSE", () => ({ useSSE: vi.fn() }));
vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
  // api.ts が i18n.ts を読み、i18n.ts が initReactI18next を使う（同じ書き方: src/lib/query/stage2Pages.test.tsx）
  initReactI18next: { type: "3rdParty", init: () => {} },
}));

// 中身は今ある画面の試験の写し（BotFormButtonMigration.test.tsx:14-15・LeadFormButtonMigration.test.tsx:15-16・
// AccountCompanySaveButtonMigration.test.tsx:18・AllLegacyButtonOperationMigration.test.tsx:80・FullPageFormButtonMigration.test.tsx:14-18）。
// 商品と注記は型（pages/products/products.types.ts:6-51・NoteMasterPage.tsx:27-40）の欄から画面が使う物だけ
const bot = { id: 7, tenant_id: 1, bot_code: "FIXTURE", display_name: "Fixture Bot", purpose: "invoice", status: "active", discord_user_id: null, sender_email: null, owner_staff_id: 9, owner_staff_name: "Fixture Staff", last_executed_at: null, execution_count: 0, created_at: "", updated_at: "" };
const staff = [{ id: 9, user_id: 9, surname_jp: "Fixture", given_name_jp: "Staff" }, { id: 10, user_id: 10, surname_jp: "Other", given_name_jp: "Staff" }];
const lead = { customer_name: "Fixture Lead", email: null, phone: null, status: "lead", type: null, notes: null, country: null, company_name: null, channel_type: null, initiative: null, temperature: null, estimated_scale: null, customer_type: null, response_speed: null, monthly_forecast: null, id: 7, lead_code: "FIXTURE", created_at: "", updated_at: "", close_reason_memo: "Existing memo", close_reasons: [{ reason_id: 42, is_primary: true }] };
const company = { id: 41, tenant_id: 1, company_code: "CO-41", lead_id: 2, sales_rep_id: null, name: "Old Co", name_en: null, normalized_name: null, industry: null, website: null, priority_focus: null, per_order_amount: null, monthly_frequency: null, monthly_forecast: null, monthly_forecast_source: null, monthly_forecast_updated_at: null, billing_display_name: null, payment_recipient_name: null, fedex_account: null, shipping_note: null, status: "active", notes: null, addresses: [], sales_channels: ["old"], discord: null, created_at: "", updated_at: "", conversation_count: 0, last_conversation_at: null };
const contact = { id: 52, company_id: 41, contact_code: "C52", surname: "Fixture contact", given_name: null, display_name: null, job_title: null, department: null, is_primary_contact: false, primary_email: null, primary_phone: null, status: "active", notes: null };
const product = { id: 5, product_code: "P-5", name_ja: "Fixture Product", name_en: null, product_kind: null, category: null, mark: null, status: "active", unit_price: null, quantity: 0, weight: null, notes: null, release_date: null, created_at: "", updated_at: "", is_archived: false, archived_at: null, work_code: null, set_type: null, boxes_per_case: null, packs_per_box: null, item: null, display_order: null };
const note = { id: 1, label_ja: "Fixture Note", label_en: "Fixture Note EN", enabled: true, search_keywords: "", exclude_keywords: "", category: "", priority: 1, match_type: "contains", search_pattern: null, label_template: null, label_template_en: null };
const invoice = { id: 3, invoice_number: "INV-3", quote_id: null, company_id: 1, currency: "USD", subtotal: 1, shipping_fee: 0, tax_amount: 0, total_amount: 1, exchange_rate_jpy: null, exchange_rate_usd: null, amount_jpy: null, amount_usd: null, payment_method: null, status: "draft", branch_number: null, erp_key: null, issued_at: null, due_date: null, paid_at: null, voided_at: null, void_reason: null, notes: null, created_at: "", items: [], ship_to_snapshot: null, bill_to_snapshot: null, duty_amount: null, fx_rate_snapshot: null, paypal_order_id: null, paypal_approval_url: null, payment_fee: null, paypal_invoicer_view_url: null, paypal_copy_pdf_at: "2026-01-01" };

const fixtures: Record<string, unknown> = {
  "/bots": [bot],
  "/bots/7": bot,
  "/staff": staff,
  "/leads": [lead],
  "/close-reasons?type=lost": [],
  "/companies/41": company,
  "/companies/41/contacts": [],
  "/invoices/3": invoice,
  "/invoices/3/paypal-disputes": [],
  "/leads/7": lead,
  "/contacts/52": contact,
  "/products?sort=release_date_desc&page=1&per_page=100": [product],
  "/note-master?page=1&per_page=100": [note],
};
// 画面の中の部品が別に取る物（一覧の選択肢など）は空の一覧で返す
const answer = (path: string) => (path in fixtures ? fixtures[path] : []) as never;

type Case = { name: string; Page: ComponentType; route: string; at: string; path: string; text: string | RegExp; value: boolean; spinner: boolean };
const cases: Case[] = [
  { name: "bots", Page: BotsPage, route: "/bots", at: "/bots", path: "/bots", text: "Fixture Bot", value: false, spinner: true },
  { name: "bot edit", Page: BotEditPage, route: "/bots/:id/edit", at: "/bots/7/edit", path: "/bots/7", text: "Fixture Bot", value: true, spinner: false },
  { name: "leads", Page: LeadsPage, route: "/crm/leads", at: "/crm/leads", path: "/leads", text: "Fixture Lead", value: false, spinner: true },
  { name: "company detail", Page: CompanyDetailPage, route: "/crm/companies/:id", at: "/crm/companies/41", path: "/companies/41", text: "Old Co", value: false, spinner: true },
  { name: "invoice detail", Page: InvoiceDetailPage, route: "/invoices/:id", at: "/invoices/3", path: "/invoices/3", text: /INV-3/, value: false, spinner: true },
  { name: "lead edit", Page: LeadEditPage, route: "/crm/leads/:id/edit", at: "/crm/leads/7/edit", path: "/leads/7", text: "Fixture Lead", value: true, spinner: false },
  { name: "contact edit", Page: ContactEditPage, route: "/contacts/:id/edit", at: "/contacts/52/edit", path: "/contacts/52", text: "Fixture contact", value: true, spinner: false },
  { name: "products", Page: ProductsPage, route: "/admin/products", at: "/admin/products", path: "/products?sort=release_date_desc&page=1&per_page=100", text: "Fixture Product", value: false, spinner: true },
  { name: "note master", Page: NoteMasterPage, route: "/management-center/note-master", at: "/management-center/note-master", path: "/note-master?page=1&per_page=100", text: "Fixture Note", value: false, spinner: true },
];

function Tree({ c }: { c: Pick<Case, "Page" | "route" | "at"> }) {
  const Page = c.Page;
  return (
    <QueryClientProvider client={queryClient}>
      <QueryAuthSync />
      <MemoryRouter initialEntries={[c.at]}>
        <Routes><Route path={c.route} element={<Page />} /></Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

const shown = (c: Case) => (c.value ? screen.queryAllByDisplayValue(c.text) : screen.queryAllByText(c.text));
const found = (c: Case) => (c.value ? screen.findAllByDisplayValue(c.text) : screen.findAllByText(c.text));

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn(() => { throw new Error("Unexpected real network request"); }));
});

afterEach(() => {
  cleanup();
  queryClient.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  auth.user = { uid: "uid-A" };
});

describe("revisit shows the copy first (Q1)", () => {
  it.each(cases)("$name shows the previous content at once on revisit", async (c) => {
    const spy = vi.spyOn(api, "get").mockImplementation(async (path: string) => answer(path));
    const first = render(<Tree c={c} />);
    await found(c);
    first.unmount();

    spy.mockClear();
    spy.mockImplementation(() => new Promise<never>(() => {}));
    const { container } = render(<Tree c={c} />);
    expect(shown(c).length).toBeGreaterThan(0);
    expect(container.querySelector(".sa-loading-block")).toBeNull();
    if (c.spinner) {
      await waitFor(() => expect(container.querySelector(".page-layout-title-row .sa-spinner")).not.toBeNull());
    }
    await waitFor(() => expect(spy).toHaveBeenCalledWith(c.path));
  });
});

describe("K5 on the real bot edit screen (Q2)", () => {
  it("after the user changes, the previous user's form is never shown", async () => {
    const c = cases[1];
    const spy = vi.spyOn(api, "get").mockImplementation(async (path: string) =>
      (path === "/bots/7" ? { ...bot, display_name: "secret-uid-A" } : answer(path)) as never);
    const view = render(<Tree c={c} />);
    await screen.findByDisplayValue("secret-uid-A");

    spy.mockImplementation(() => new Promise<never>(() => {}));
    auth.user = { uid: "uid-B" };
    view.rerender(<Tree c={c} />);
    expect(screen.queryByDisplayValue("secret-uid-A")).toBeNull();
    expect(view.container.querySelector(".sa-loading-block")).not.toBeNull();
    await waitFor(() => expect(spy).toHaveBeenCalledWith("/bots/7"));
    expect(screen.queryByDisplayValue("secret-uid-A")).toBeNull();
  });
});
```
- LoadingBlock の見分けは `.sa-loading-block`、回る印の見分けは `.page-layout-title-row .sa-spinner`（段 2 カード §4-F と同じ）。編集の画面は回る印を出さない（見出しの横の印は一覧と詳しい画面だけ）。
- Q1 の画面の中の部品が、空の一覧で困って落ちた時（例: 選択肢を `.map` する所で undefined）は、§3(e) に従い停止する。
- Q1 は 9 画面（11 行のうち /crm と /crm/leads・/management-center/bots と /bots は同じ画面）。商品の path は、検索なし・並び release_date_desc（S ProductsPage.tsx:46）・種別なし・1 ページ目・100 件（S :35）の時に §4-J1 の J1-5 が作る文字列。注記の path は §4-H の H6 が page 1・PER_PAGE 100（S NoteMasterPage.tsx:86）で作る文字列。

## 4-L2. #23 frontend/src/lib/query/useSeededForm.test.tsx（新しく作る・全文）
- 理由: Q2 は画面を通すので、名前から uid を抜く・ready を `seed !== null` にする、という壊し方を見つけられない（第 1 版の審査で、その 2 つの壊し方でも Q2 が通った）。Q3 は部品だけを描き、この 2 つと「いつも作り直す」の壊し方で落ちる。
```tsx
/** ADR-1054 段 3: useSeededForm だけの試験（Q3）。K5 と打ちかけを消さないことを、画面を通さずに確かめる。 */
import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useSeededForm } from "./useSeededForm";

const auth = vi.hoisted(() => ({ user: { uid: "uid-A" } as { uid: string } | null }));
vi.mock("../../contexts/AuthContext", () => ({ useAuth: () => ({ user: auth.user, loading: false }) }));

type D = { name: string };
const toForm = (d: D) => ({ name: d.name });
const empty = { name: "" };
const hook = (data: D | undefined) =>
  renderHook((p: { data: D | undefined }) => useSeededForm("bot/7", p.data, toForm, empty), { initialProps: { data } });

afterEach(() => {
  auth.user = { uid: "uid-A" };
});

describe("useSeededForm (Q3)", () => {
  it("K5: after A edited, user B never sees A's form and gets B's data", () => {
    const view = hook({ name: "A-data" });
    expect(view.result.current.form).toEqual({ name: "A-data" });
    act(() => view.result.current.setForm({ name: "A-typed" }));
    expect(view.result.current.form).toEqual({ name: "A-typed" });
    auth.user = { uid: "uid-B" };
    view.rerender({ data: undefined });
    expect(view.result.current.ready).toBe(false);
    expect(view.result.current.form).toEqual(empty);
    view.rerender({ data: { name: "B-data" } });
    expect(view.result.current.ready).toBe(true);
    expect(view.result.current.form).toEqual({ name: "B-data" });
  });

  it("reseeds from a refetched copy only while untouched", () => {
    const view = hook({ name: "v1" });
    view.rerender({ data: { name: "v2" } });
    expect(view.result.current.form).toEqual({ name: "v2" });
    act(() => view.result.current.setForm((p) => ({ ...p, name: "typed" })));
    view.rerender({ data: { name: "v3" } });
    expect(view.result.current.form).toEqual({ name: "typed" });
  });

  it("is empty and not ready before the first copy arrives", () => {
    const view = hook(undefined);
    expect(view.result.current.ready).toBe(false);
    expect(view.result.current.form).toEqual(empty);
  });
});
```

## 4-M. 実装役の手順（1 手順 1 命令。<W> は手順1 で作られた作業場所の絶対パス）
手順1. クラウドの決まり（S scripts/agent-hooks/cloud/rules.md:15）どおり、作業場所を作り、push 済みの枝の先頭に合わせる（設計担当が §1 #24〜#26 を push 済み）。
  cd "$(git rev-parse --show-toplevel)" && bash scripts/new-worktree.sh release/line-like-speed-batch3a
  （出力に出た作業場所の絶対パスを <W> として報告に書く。）
  cd <W> && git fetch origin release/line-like-speed-batch3a
  cd <W> && git switch -C release/line-like-speed-batch3a origin/release/line-like-speed-batch3a
  cd <W> && git rev-parse HEAD origin/release/line-like-speed-batch3a
  （2 行が同じことを確かめる。違えば停止して BLOCKED: で報告する。main は取り込まない。reset・rebase・force・merge・pull は使わない）
  cd <W> && ./scripts/dev/executor-preflight.sh > /tmp/b3-preflight.txt 2>&1
  cd <W> && grep -n "FAIL" /tmp/b3-preflight.txt | head -20
  cd <W> && grep -n "origin/main は存在" /tmp/b3-preflight.txt | head -3
  （FAIL の行が次の 3 つのうちのどれかだけなら続ける: `GitHub API に到達不可` の 1 件・`gh auth switch --hostname github.com --user shingo-cc` の失敗の 1 件・その結果の `PREFLIGHT FAIL` の行。理由は段 2 カード §4-H 手順1 と同じ。続ける時は `[OK]   origin/main は存在` の行があることを 2 つ目の grep で確かめ、無ければ停止する。ほかの FAIL が 1 件でもあれば停止し、BLOCKED: で grep の出力を報告する。）
  cd <W> && git fetch origin main
  cd <W> && git diff --stat d0de518e22a8adc542ae935c409cfc8c39b9d5bc origin/main -- frontend/src | tail -5
  （§3(a) の確かめ。）
手順2. 依存を入れ、§3(b) を確かめ、変える前の lint の警告を数える。
  cd <W>/frontend && npm ci > /tmp/b3-ci.txt 2>&1
  cd <W> && tail -5 /tmp/b3-ci.txt
  cd <W>/frontend && grep -n '"@tanstack/react-query"' package.json
  cd <W>/frontend && grep -n "export function getCloseReasons" src/api/closeReasons.ts
  cd <W>/frontend && npx eslint src/api/closeReasons.ts src/pages/bots/BotEditPage.tsx src/pages/contacts/ContactEditPage.tsx src/pages/leads/LeadEditPage.tsx src/pages/leads/LeadsPage.tsx src/pages/bots/BotsPage.tsx src/pages/note-master/NoteMasterPage.tsx src/pages/invoice-detail/InvoiceDetailPage.tsx src/pages/products/ProductsPage.tsx src/pages/company-detail/useCompanyDetail.ts src/pages/company-detail/CompanyDetailPage.tsx > /tmp/b3-lint-before.txt 2>&1
  cd <W> && tail -5 /tmp/b3-lint-before.txt
手順3. §4-A・§4-L・§4-L2 の全文で #1・#22・#23 を作り、§4-B〜§4-K のとおり #2〜#21 を直す。各ファイルを直す前に、§4 の「変更前」の文を `grep -n` で確かめる（§3(c)）。終わったら残りが無いことを確かめる。
  cd <W> && grep -n "useEffect\|setLoading\|setLeads\|setBots\|setStaff\|setNotes\|setHasNext\|setInvoice\|setDisputes\|setProducts\|setTcgTypes\|setCompany\|setContacts\|setCloseReasonOptions\|getCloseReasons" frontend/src/pages/bots/BotEditPage.tsx frontend/src/pages/contacts/ContactEditPage.tsx frontend/src/pages/leads/LeadEditPage.tsx frontend/src/pages/leads/LeadsPage.tsx frontend/src/pages/bots/BotsPage.tsx frontend/src/pages/note-master/NoteMasterPage.tsx frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx frontend/src/pages/products/ProductsPage.tsx frontend/src/pages/company-detail/useCompanyDetail.ts | head -20
  （出てよいのは ProductsPage.tsx の useEffect の 2 行（import と検索の effect）と、useCompanyDetail.ts:3 の説明のコメント `CompanyDetailPage の全 useState / useEffect / handler を集約する。` の 1 行だけ。ほかが出たら §4 の写し違いを直す。）
手順4. 型を作ってから試験を流す（新しい試験・直した今ある試験 9 本・全部の試験・型・lint）。作る型（frontend/src/api/generated/）は .gitignore で除かれるので commit に入らない。
  cd <W>/frontend && npm run generate:api-types > /tmp/b3-gen.txt 2>&1
  cd <W> && tail -3 /tmp/b3-gen.txt
  cd <W>/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/lib/query > /tmp/b3-unit.txt 2>&1
  cd <W> && tail -30 /tmp/b3-unit.txt
  cd <W>/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/components/AccountCompanySaveButtonMigration.test.tsx src/components/AllLegacyButtonDynamicMigration.test.tsx src/components/AllLegacyButtonOperationMigration.test.tsx src/components/BotFormButtonMigration.test.tsx src/components/CommerceNavigationButtonMigration.test.tsx src/components/FullPageFormButtonMigration.test.tsx src/components/LeadFormButtonMigration.test.tsx src/components/OrderLeadButtonMigration.test.tsx src/pages/leads/LeadsPage.temperature.test.tsx > /tmp/b3-pages.txt 2>&1
  cd <W> && tail -30 /tmp/b3-pages.txt
  cd <W>/frontend && npm run test:unit > /tmp/b3-unit-all.txt 2>&1
  cd <W> && tail -15 /tmp/b3-unit-all.txt
  cd <W>/frontend && npx tsc --noEmit -p . > /tmp/b3-tsc.txt 2>&1
  cd <W> && tail -20 /tmp/b3-tsc.txt
  cd <W>/frontend && npx eslint src/lib/query src/api/closeReasons.ts src/pages/bots/BotEditPage.tsx src/pages/contacts/ContactEditPage.tsx src/pages/leads/LeadEditPage.tsx src/pages/leads/LeadsPage.tsx src/pages/bots/BotsPage.tsx src/pages/note-master/NoteMasterPage.tsx src/pages/invoice-detail/InvoiceDetailPage.tsx src/pages/products/ProductsPage.tsx src/pages/company-detail/useCompanyDetail.ts src/pages/company-detail/CompanyDetailPage.tsx > /tmp/b3-lint.txt 2>&1
  cd <W> && tail -20 /tmp/b3-lint.txt
  （lint の警告が手順2 の数より増えていないこと・誤りが 0 であること。§3(d)。）
手順5. 本番と同じ形で組み立てられるか確かめる。
  cd <W>/frontend && npm run build > /tmp/b3-build.txt 2>&1
  cd <W> && tail -15 /tmp/b3-build.txt
手順6. 変わったファイルが §1 の #1〜#23 だけか確かめ、画面の書く path と表・フォームの行が変わっていないことを見る。
  cd <W> && git status --short | head -30
  cd <W> && git diff -w --stat origin/release/line-like-speed-batch3a | tail -25
  cd <W> && git diff -w origin/release/line-like-speed-batch3a -- frontend/src/pages frontend/src/api | head -600
手順7. commit する。
  cd <W> && git add frontend/src/lib/query/useSeededForm.ts frontend/src/lib/query/batch3aPages.test.tsx frontend/src/lib/query/useSeededForm.test.tsx frontend/src/api/closeReasons.ts frontend/src/pages/bots/BotEditPage.tsx frontend/src/pages/contacts/ContactEditPage.tsx frontend/src/pages/leads/LeadEditPage.tsx frontend/src/pages/leads/LeadsPage.tsx frontend/src/pages/bots/BotsPage.tsx frontend/src/pages/note-master/NoteMasterPage.tsx frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx frontend/src/pages/products/ProductsPage.tsx frontend/src/pages/company-detail/useCompanyDetail.ts frontend/src/pages/company-detail/CompanyDetailPage.tsx frontend/src/components/AccountCompanySaveButtonMigration.test.tsx frontend/src/components/AllLegacyButtonDynamicMigration.test.tsx frontend/src/components/AllLegacyButtonOperationMigration.test.tsx frontend/src/components/BotFormButtonMigration.test.tsx frontend/src/components/CommerceNavigationButtonMigration.test.tsx frontend/src/components/FullPageFormButtonMigration.test.tsx frontend/src/components/LeadFormButtonMigration.test.tsx frontend/src/components/OrderLeadButtonMigration.test.tsx frontend/src/pages/leads/LeadsPage.temperature.test.tsx
  cd <W> && git commit -m "feat: 遅い順の10画面を写しを先に出して裏で取り直す形に（ADR-1054 段3の1回目）"
手順8. commit が在ることを確かめてから push する（--no-verify は使わない。push の前の検査が × なら直してから push。fast-forward でないと断られたら直さず BLOCKED:）。
  cd <W> && git log -3 --oneline
  cd <W> && git push -u origin release/line-like-speed-batch3a
手順9. 報告を返す。PR は作らない（設計担当が手元で作る）。報告の 1 つの発言は 600 文字以内にして、番号付きの発言に分ける。報告には手順ごとの tail の出力（生のまま）と、§3(a)〜(f) の結果を書く。

## 4. GO と承認・PO の操作
- PO の実装承認: 2026-11-02 PO 選択「1」（残りの遅い画面を遅い順に 10 画面ずつ、本番の測定まで直す）。ADR-1054 は Accepted。このカードの審査合格の後に、設計担当がクラウドの Sonnet へ渡す。
- 触るのは frontend の画面 10 個・小さな部品 1 つ・試験と書類だけで、migrations・deploy.yml・本番 scripts を含まない（番号付き GO の要る危ない PR ではない）。main へのマージで本番の画面に出る（deploy.yml が main への push で動く）。マージは PO の委任に基づき設計担当（Claude Opus）が、マージ前の審査役の APPROVE と必須の確認がすべて pass の後に行う。
- PO が操作することはない。

## 5. 受入（○×）
| # | 基準 | 検証方法 |
|---|---|---|
| B1 | Q1（9 画面とも戻った時に LoadingBlock 0 個で前の中身が出る・一覧と詳しい画面は見出しの横に回る印・裏で取り直す）と Q2（K5: 人を B に変えた後の描画に A のフォームの中身 0 件・読み込み中の印が出る）と Q3（K5 と打ちかけを消さないこと・部品だけ）がすべて合格 | /tmp/b3-unit.txt の最後（batch3aPages.test.tsx の 10 件・useSeededForm.test.tsx の 3 件が passed・apiQuery.test.tsx と stage2Pages.test.tsx も passed）と、PR の CI の unit-run が success |
| B2 | 今ある画面の試験 9 本・全部の試験・型・lint・組み立てが通る | /tmp/b3-pages.txt・b3-unit-all.txt・b3-tsc.txt・b3-lint.txt・b3-build.txt の最後と、PR の必須の確認がすべて pass |
| B3 | 変わったのは §1 の 26 ファイルだけ。画面の書く path と中身・表・フォームの欄は変わっていない | gh pr diff --name-only と git diff -w（§4-M 手順6） |
| B4 | QueryClient を作るのは apiQuery.ts の 1 か所だけ・staleTime を設定していない・写しをブラウザの保存に書かない | `git grep -n "new QueryClient" -- frontend/src` が 1 行、`git grep -n "staleTime:" -- frontend/src` が 0 行、`git grep -n -i "persist" -- frontend/src/lib/query frontend/package.json` が 0 行 |
| B5 | マージの後、毎朝の画面の記録を手で 1 回動かし、§0 V3a-1 の 11 行で K1（戻った時の秒）≤0.1 秒、K2（初めて開く秒）≤2 秒、403・5xx が 0 件。ほかの行は K2 の最大と 2 秒を超えた画面の数が段 2 の受入（run 41346462841）から悪化していない | prod-ui-check の実行の要約（設計担当。`gh workflow run prod-ui-check.yml --ref main` の後に要約の表を読む） |
| B6 | 取り直した後の中身が DB と一致（tenant 001）: Bot 一覧・リード一覧・注記マスタ（1 ページ目）の件数が、本番 DB の同じ条件の件数と同じ | 設計担当が本番の読むだけの道（ADR-1024）で tenant_001 の bots・leads・注記マスタの行を数える。画面の件数は prod-ui-check の記録か PO のログイン済みの Chrome で数える。数えられない時は「画面の件数はまだ確かめていない」と記録し、backend を変えていないこと（B3）と Q1 を根拠にする |
| B7 | マージの後、deploy が成功し、本番の画面が開く | deploy.yml の実行の結論 success と時刻。本番 https://app.salesanchor.jp/ が開き、ブラウザの誤りの記録に TanStack 由来の誤りが無い（設計担当） |
