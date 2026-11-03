# 段 3 の 6 回目の実装カード（会社の情報・会社の方針・Discord の設定の 3 画面と、チャネルの画面の Discord の欄を「写しを先に出して裏で取り直す」形に変える）

- 対象: docs/handoff/line-like-speed/design.md の §3-2（部品）・§3-3（触らない範囲）・§3-4 の段 3・§3-4-18-a（5 回目の受入で残った /channels）・§3-4-19・§3-5 の K1・K2・K5・§3-7。ADR-1054（Accepted）。段 3 の 1〜5 回目のカード（docs/handoff/line-like-speed/batch3a-card.md〜batch3e-card.md）の部品と形をそのまま使う。
- 根拠の写し: S=origin/main 43070f593baf30a9c85b7f441057f22ebf9c6554。行番号はすべてこの sha。2026-11-03 に設計担当が S の写しで行を読んだ。S と、行を読み始めた時の origin/main a0d58d3a7 の差は docs と台帳の 2 ファイルだけで、frontend/src の差は 0（設計担当が `git diff --name-only` で確かめた）。実装の前に最新の origin/main で行を合わせ直す（§3(a)）。
- 読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md・guards/03-file.md・guards/04-worktree.md・guards/05-pr.md・guards/10-executor.md・scripts/agent-hooks/cloud/rules.md（段 3 の 1〜5 回目のカードと同じ節。照合も同じ: 全命令は cd <W> で始める・出力は tail/head で上限・新しいファイルは丸ごとの全文・作業場所は new-worktree.sh で作り出力をパイプに通さない・PR は実行役が作らない・出力をファイルに残す命令と tail で読む命令は別の行）。
- 実行役はクラウドの Sonnet。作業場所の作り方はクラウドの決まり（S scripts/agent-hooks/cloud/rules.md:15）を正とする。.pr-number・gh-pr-create-safe.sh は使わない。出力には上限を付ける。待つために sleep を使わない。
- 状態: 第 4 版（2026-11-03 設計担当 Claude Opus）。第 1 版（d7c82910）の審査 REVISE の 3 点（§5 B4 の grep の期待に InboxKartePanel.tsx:115 が抜けていた・§4-D7 の 1 行目が S で 2 か所ある断りが無かった・§4-A3・B3・C6・C11 の行数の書き方が塊と合わなかった）を直した。第 3 版で、第 2 版（41e90142）の審査 REVISE の 2 点（§4-C3 の行数の書き方を第 2 版で誤って書き換えた・この状態の行に指摘されていない C3 を入れていた）を直した。第 4 版で、第 3 版（502764c0）の審査 REVISE の 1 点（この状態の行で第 2 版の指摘を 1 点と書いていた）を直した。コードの塊・試験・手順は第 1 版と同じ。
- 受領確認: 実装役は着手の最初の報告に「段 3 の 6 回目のカード 第 4 版を受け取った・S=43070f593」と書く。

## 0. 設計からの直し・詳しくした点（V3f。設計の合格線は変えない）
- V3f-1 対象は、5 回目の受入（design §3-4-18-a。prod-ui-check run 41614984342）で K1（戻った時の秒）が合格線 0.1 秒を超えた画面のうち、測る利用者に見る権限がある次の画面（毎朝の記録の 8 行）。

  | 行（毎朝の記録の画面） | 画面のファイル | 読む path | 基準の K1（秒） |
  |---|---|---|---|
  | /admin/tenant-profile・/management-center/tenant-profile・/admin → /admin/tenant-profile | pages/admin/TenantProfilePage.tsx | /admin/tenant-profile | 0.21・0.22・0.21 |
  | /admin/tenant-policy・/management-center/tenant-policy | pages/admin/TenantPolicyPage.tsx | /admin/tenant-policy | 0.21・0.21 |
  | /admin/discord-config・/management-center/discord-config | pages/admin/DiscordConfigPage.tsx | /admin/discord-config・/admin/discord-ticket-config | 0.25・0.24 |
  | /channels | pages/channels/ChannelsPage.tsx の Discord の欄 | /admin/discord-config | 0.24 |

  画面の道は S frontend/src/App.tsx:370・:372・:374・:376（/admin の下）と :401・:403・:404（/management-center の下）。/channels と /management-center/channels は 5 回目のカード（batch3e-card.md V3e-1）と同じ。
- V3f-2 対象から外す画面と理由:
  - /schedule（K1 0.29 秒）: 読む path が 3 本（/calendar/owners・/calendar/events?start&end・/shifts?date_from&date_to）で、見本の状態の分かれ道と、表示の期間で変わる path を持ち、基準の回で /shifts の 5xx が 1 件ある。1 度に 1 つを変える決まりにより、段 3 の 7 回目に分ける（design §3-4-19）。
  - /buyback-prices・/management-center/conditions・/management-center/product-categories: 測る利用者に見る権限が足りず 403 が出ている。権限を足すかは設計担当が PO に別に聞く。
  - /account/settings は K1 0.04 秒で合格線の内（変えない）。
- V3f-3 写しの置き場の部品（S frontend/src/lib/query/apiQuery.ts）と、フォームの初めの値を写しから作る部品（S frontend/src/lib/query/useSeededForm.ts）は変えない。使うのは useApiQuery・useInvalidateApi・useApiCache・useSeededForm だけ。QueryClient を足さない・staleTime を設定しない・写しをブラウザの保存に書かない。
- V3f-4 3 画面はどれも編集のフォームの画面なので、段 3 の 5 回目のスタッフの編集と同じ形にする: 写しがあればすぐ出す・読み込み中の印（LoadingBlock）は写しが無い初回（isPending）だけ・回る印は出さない・人がまだ直していない時だけ取り直した値でフォームを作り直す（useSeededForm）。
- V3f-5 同じ path は同じ写しを使う（同じ API の同じ答えを分けて持たない）: `/admin/discord-config` は Discord の設定の画面とチャネルの画面の 2 画面で 1 つの写し。チャネルの画面の権限の条件（S ChannelsPage.tsx:114 の canViewDiscord）は今のまま取りに行く条件にする。
- V3f-6 書いた後の写しの扱い（どれも書く path と中身は変えない）:
  - 会社の情報・会社の方針: 保存の返事は読む時と同じ形（S backend/app/routers/tenant_profile.py:85-87 と tenant_policy.py:80-82 の response_model が GET と同じ）なので、返事をそのまま写しに書く（useApiCache の write）。GET は増えない。
  - Discord の設定のサーバー ID の保存: 返事は guild_id だけが本物で、ほかの欄（接続した日時・接続した人）は既定の null になる（S backend/app/routers/discord_guild_config.py:37-42・:143）。返事を丸ごと書くとチャネルの画面の「接続した日時」が消えるので、写しは guild_id だけ書き換え（useApiCache の update）、その後に写しを古い印にして取り直す（useInvalidateApi）。GET が 1 回増える。
  - Discord の設定のチケットの設定の保存: 返事は読む時と同じ形（S DiscordConfigPage.tsx:228 の put の型）なので、返事を写しに書き、フォームも返事の値にする（今の applyTicketConfig と同じ）。
  - Discord の設定の自動セットアップの後: 今と同じく 2 本を取り直す（useApiCache の fetch で同じ写しに入れる）。今ある試験（S DiscordConfigPage.test.tsx:104-119）が数える「前に 1 回ずつ・後に 2 回ずつ」は変わらない。
  - チャネルの画面の Discord の切断の後: 今は表示を未接続に戻す（S ChannelsPage.tsx:243）。直した後は写しの guild_id・接続した日時・接続した人を null にして（update）、取り直す（invalidate）。GET が 1 回増える。
  - チャネルの画面の Bot の招待から戻った時（S :215-227）: 今と同じく 1 回取り直し、guild_id があればお知らせを出して見張りを外す（useApiCache の fetch で同じ写しに入れる）。
- V3f-7 見た目の変わる所（意図した変化）:
  - 3 画面とも、読めなかった時、今は空の値（既定の値）のフォームが出て保存できるので、押すと空の値で本物の設定を上書きしてしまう（S TenantProfilePage.tsx:91-95・:138-142、TenantPolicyPage.tsx:86-91・:151-159、DiscordConfigPage.tsx:154-167・:338-349）。直した後は、読めていない間（useSeededForm の ready が false）はフォームを出さず、誤りの文だけを出す（段 3 の 5 回目のスタッフの編集と同じ）。Q2 で確かめる。
  - 3 画面とも、2 回目に開いた時は前に読んだ値がすぐ出て、取り直した値が来たら（人がまだ直していなければ）作り直す。
  - チャネルの画面: 2 回目に開いた時は Discord の欄が前に読んだ接続の状態ですぐ出る（今は返事が来るまで未接続の形で出て、返事の後に描き直す。design §3-4-18-a の /channels が落ちた訳）。
  - チャネルの画面: Discord の接続の結果の URL（?discord_status=connected）で開いた時、今は Discord の設定を 2 回読む（S :129 と :178）。直した後は開いた時の 1 回だけ（写しの置き場が同じ写しの取りに行きを 1 本にまとめる）。
  - Discord の設定の画面: 写しの「サーバー ID」が別の画面（チャネルの画面の切断）で変わっても、この画面を開いている間に人がサーバー ID を直していれば作り直さない（useSeededForm）。開き直せば新しい値になる。
- V3f-8 取れなかった時の文は今の位置のまま 1 か所: 会社の情報・会社の方針は今の error の位置（shownError）。Discord の設定は今の loadError の位置（S :349）で、2 本のどちらかが取れなければ今と同じ文（discordConfig.loadError）。チャネルの画面の Discord の欄は今と同じく取れなかった時に文を出さない（S :180 のサイレント）。
- V3f-9 写しがある状態で裏の取り直しが失敗した時は、前の中身を出したまま誤りの文を出す（段 3 の 1〜5 回目と同じ）。
- V3f-10 今ある画面の試験のうち、4 画面を描く試験は 2 本（設計担当が S で `git grep -ln "TenantProfilePage\|TenantPolicyPage\|DiscordConfigPage\|ChannelsPage" -- "frontend/src/*.test.tsx"` で確かめた: frontend/src/lib/query/batch3ePages.test.tsx と frontend/src/pages/admin/DiscordConfigPage.test.tsx）。batch3ePages.test.tsx は既に写しを消している（S :116 の queryClient.clear）ので変えない。DiscordConfigPage.test.tsx は cleanup の後に写しを消していないので `queryClient.clear()` を足す（§4-K）。
- V3f-11 api.ts の GET の送り直し（S frontend/src/lib/api.ts）は変えない。
- V3f-12 受入（§5 B5）は、§0 V3f-1 の 8 行すべてで K1 ≤0.1 秒・K2 ≤2 秒・403 と 5xx が 0 件。/management-center/channels（5 回目の受入で 0.02 秒）が合格のままかも並べて見る。K5 は段 3 の 1 回目の Q2・Q3（Bot 編集と useSeededForm の試験）と、写しの名前に利用者が入る作りで確かめる（本番で 2 人のログインは使わない）。

## 1. 触るファイル（変更前→変更後）
| # | ファイル | 変更前 | 変更後 |
|---|---|---|---|
| 1 | frontend/src/pages/admin/TenantProfilePage.tsx | useState と useEffect で読む（S :66-67・:75-99） | useApiQuery＋useSeededForm（§4-A） |
| 2 | frontend/src/pages/admin/TenantPolicyPage.tsx | 同上（S :62-63・:71-99） | useApiQuery＋useSeededForm（§4-B） |
| 3 | frontend/src/pages/admin/DiscordConfigPage.tsx | 同上（S :96-99・:102・:109-118・:131-167） | useApiQuery＋useSeededForm 2 つ（§4-C） |
| 4 | frontend/src/pages/channels/ChannelsPage.tsx | Discord の設定を useState と api.get で読む（S :102-106・:129-131・:175-181・:216-218・:243） | useApiQuery の写し（§4-D） |
| 5 | frontend/src/pages/admin/DiscordConfigPage.test.tsx | cleanup の後に写しを消さない | cleanup の後に queryClient.clear()（§4-K） |
| 6 | frontend/src/lib/query/batch3fPages.test.tsx | 無い | 新しく作る。Q1・Q2・Q3（§4-L 全文） |
| 7 | docs/handoff/line-like-speed/batch3f-card.md | 無い | このカード（設計担当が書いた。実装役は触らない） |
| 8 | docs/handoff/line-like-speed/design.md | §3-4-18-a まで | §3-4-19 にこのカードの場所と基準を書き足し済み（設計担当。実装役は触らない） |
| 9 | .claude-pipeline/active-work.d/release-line-like-speed-batch3f.md | 無い | 作業の札（設計担当。実装役は触らない） |

## 2. 触らない範囲
- backend/・migrations/・.github/workflows/・scripts/・tests/prod-check/・frontend/viewer/ は触らない（design §3-3）。
- frontend/src/lib/api.ts・frontend/src/contexts/・frontend/src/lib/auth/・frontend/src/lib/query/apiQuery.ts・frontend/src/lib/query/useSeededForm.ts・frontend/src/lib/query/QueryAuthSync.tsx・frontend/src/lib/query/batch3ePages.test.tsx・frontend/src/App.tsx・frontend/src/hooks/・frontend/src/mocks/ は触らない。
- frontend/src/components/・CSS（discord-config.css を含む）・ja.json・en.json は触らない。新しい言葉・色・寸法を足さない。
- 4 画面の中の、書き方（post・put・delete の path と中身）・入力の確かめ（S DiscordConfigPage.tsx:200-216 の validateTicket）・Bot の招待（S ChannelsPage.tsx:192-211）・Meta の接続・チャネルの一覧（5 回目で直した所）・フォームの欄・ボタン・カードの並びは変えない。変えるのは §4 に書いた行だけ。
- QueryClient を作らない（試験の中でも作らない）。staleTime を設定しない。写しをブラウザの保存に書かない。
- ほかの画面（/schedule を含む）は変えない。

## 3. 実装役が先に確かめること（想定分岐つき）
- (a) 最新の origin/main で `git diff --stat 43070f593baf30a9c85b7f441057f22ebf9c6554 origin/main -- frontend/src | tail -12` が空か。§1 #1〜#5 のどれかが変わっていたら停止して報告する。ほかのファイルだけなら、変わったファイルの名前と行数を報告に書いて続ける。
- (b) `cd <W>/frontend && grep -n '"@tanstack/react-query"' package.json` が `"5.104.4"` の 1 行。違えば停止して報告する。
- (c) §4 の「変更前」の文が、書かれた行にそのままあること。1 か所でも無い・2 か所以上ある時は、直さずに停止して BLOCKED: で `grep -n` の出力を報告する（同じ文が 2 か所以上あるとカードに書いた所は除く）。
- (d) 手順 2 で、変える前の 4 ファイル（§1 #1〜#4）の lint の警告の数を数えておく。変えた後は、その数より増えないこと（0 になってもよい）。増えたら直す。直せない時は停止する。
- (e) Q1・Q2・Q3・今ある画面の試験のどれかが落ちたら、試験を書き換えて通さない（§4-K の行を除く）。画面の §4 の写し違いを探し、写し違いが無ければ停止して NEEDS_DECISION: で生の出力を返す。
- (f) 今ある試験との関係（変わらない見込み。違った時は試験を変えずに停止して NEEDS_DECISION: で生の出力を返す）:
  - DiscordConfigPage.test.tsx は AuthContext を差し替えずに描く。useAuth は開発の組み立て（vitest もこれ）で包みが無い時に仮の利用者（uid "e2e-test-user-uid"）を返す（S frontend/src/contexts/AuthContext.tsx:176-195）ので、useApiQuery は取りに行く。api は差し替え済み（S DiscordConfigPage.test.tsx:8-11）で、AuthContext が読む api も同じ差し替えになる。
  - 同じ試験の「自動セットアップの後に 2 本とも取り直す」（S :104-119）は、開いた時に 1 回ずつ（useApiQuery）、自動セットアップの後にもう 1 回ずつ（§4-C7 の cache.fetch）で、今と同じ数になる。
  - 同じ試験の「案内文を保存して投稿し直す」（S :137-151）は、保存の返事でフォームを作る（§4-C9）ので今と同じ。
  - batch3ePages.test.tsx のチャネルの Q1（S :19-24 の fixtures に /admin/discord-config がある）は、チャネルの画面が Discord の設定を写しで読むようになっても、同じ path を 1 回読むだけで変わらない。
- (g) api の import はどのファイルでも残す（書くのと cache.fetch の中で使う: TenantProfilePage.tsx の put、TenantPolicyPage.tsx の put、DiscordConfigPage.tsx の put・post と §4-C7 の get、ChannelsPage.tsx の post・delete と §4-D の get）。ChannelsPage.tsx の useEffect・useRef・ApiError は残す（S :121・:184 の useEffect、:110-111 の useRef、:232・:247 の ApiError）。

## 4-A. #1 frontend/src/pages/admin/TenantProfilePage.tsx
- A1 S :16 `import { useEffect, useState } from "react";` → `import { useState } from "react";`
- A2 S :18 `import { api } from "../../lib/api";` の次に 2 行足す:
```ts
import { useApiCache, useApiQuery } from "../../lib/query/apiQuery";
import { useSeededForm } from "../../lib/query/useSeededForm";
```
- A3 S :61 `};`（emptyForm の終わり）の次に、次の 12 行を足す（塊の 1 行目は空行）（:62 の空行と :63 の `export default function` はそのまま）:
```ts

const PROFILE_PATH = "/admin/tenant-profile";
const toForm = (data: TenantProfile): FormState => ({
  company_name: data.company_name ?? "",
  company_name_en: data.company_name_en ?? "",
  address: data.address ?? "",
  phone: data.phone ?? "",
  email: data.email ?? "",
  website: data.website ?? "",
  seal_image_url: data.seal_image_url ?? "",
  default_language: data.default_language ?? "ja",
});
```
  （中身は S :81-90 の setForm の中身と同じ。）
- A4 S :66-67（form と loading の useState の 2 行）を消す（:68 の saving から残す）。
- A5 S :73 `  const canEdit = hasPermission("tenant.profile.edit");` の次に 5 行足す:
```ts
  const profileQ = useApiQuery<TenantProfile>(PROFILE_PATH, { enabled: canView });
  const { form, setForm, ready } = useSeededForm(PROFILE_PATH, profileQ.data, toForm, emptyForm);
  const cache = useApiCache();
  const readError = profileQ.error ? (profileQ.error instanceof Error ? profileQ.error.message : t("common.fetchError")) : "";
  const shownError = error || readError;
```
- A6 S :75-100（useEffect の 25 行と、その後の空行 :100）を消す（:101 の handleChange から残す）。
- A7 S :119 `      await api.put("/admin/tenant-profile", payload);` を次の 2 行に置き換える:
```ts
      const saved = await api.put<TenantProfile>("/admin/tenant-profile", payload);
      cache.write(PROFILE_PATH, saved);
```
- A8 S :138 `      {loading ? (` → `      {profileQ.isPending ? (`
- A9 S :140 `      ) : (` を次の 3 行に置き換える:
```tsx
      ) : !ready ? (
        <div className="error-message">{shownError}</div>
      ) : (
```
- A10 S :142 `          {error && <div className="error-message">{error}</div>}` → `          {shownError && <div className="error-message">{shownError}</div>}`
- :101-105 の handleChange（setForm に関数を渡す。useSeededForm の setForm は関数を受け取る: S useSeededForm.ts:23-29）・:107-126 の保存の残り・:128-134 の権限の無い時の表示・:143 の info は変えない。

## 4-B. #2 frontend/src/pages/admin/TenantPolicyPage.tsx
- B1 S :15 `import { useEffect, useState } from "react";` → `import { useState } from "react";`
- B2 S :17 `import { api } from "../../lib/api";` の次に 2 行足す（§4-A2 と同じ 2 行）。
- B3 S :56 `};`（emptyForm の終わり）の次に、次の 12 行を足す（塊の 1 行目は空行）（:57 の空行と :58 の `export default function` はそのまま）:
```ts

const POLICY_PATH = "/admin/tenant-policy";
const toForm = (data: TenantPolicy): FormState => ({
  inventory_agg_filter: data.inventory_agg_filter,
  agg_price_threshold_jpy: String(data.agg_price_threshold_jpy),
  agg_qty_threshold: String(data.agg_qty_threshold),
  quote_validity_days: String(data.quote_validity_days),
  default_currency: data.default_currency,
  document_language: data.document_language,
  duty_incoterms: data.duty_incoterms,
  issue_mode: data.issue_mode,
});
```
  （中身は S :77-86 の setForm の中身と同じ。）
- B4 S :62-63（form と loading の useState の 2 行）を消す（:64 の saving から残す）。
- B5 S :69 `  const canEdit = hasPermission("tenant.profile.edit");` の次に 5 行足す:
```ts
  const policyQ = useApiQuery<TenantPolicy>(POLICY_PATH, { enabled: canView });
  const { form, setForm, ready } = useSeededForm(POLICY_PATH, policyQ.data, toForm, emptyForm);
  const cache = useApiCache();
  const readError = policyQ.error ? (policyQ.error instanceof Error ? policyQ.error.message : t("common.fetchError")) : "";
  const shownError = error || readError;
```
- B6 S :71-100（useEffect の 29 行と、その後の空行 :100）を消す（:101 の handleChange から残す）。
- B7 S :125 `      await api.put("/admin/tenant-policy", payload);` を次の 2 行に置き換える:
```ts
      const saved = await api.put<TenantPolicy>("/admin/tenant-policy", payload);
      cache.write(POLICY_PATH, saved);
```
- B8 S :151 `      {loading ? (` → `      {policyQ.isPending ? (`
- B9 S :153 `      ) : (` を §4-A9 と同じ 3 行に置き換える。
- B10 S :159 `          {error && <div className="error-message">{error}</div>}` → `          {shownError && <div className="error-message">{shownError}</div>}`
- :101-107 の handleChange・:108-134 の保存の残り・:136-144 の権限の無い時の表示・:160-164 の info は変えない。

## 4-C. #3 frontend/src/pages/admin/DiscordConfigPage.tsx
- C1 S :11 `import { useCallback, useEffect, useState } from "react";` → `import { useState } from "react";`
- C2 S :13 `import { api } from "../../lib/api";` の次に 2 行足す:
```ts
import { useApiCache, useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";
import { useSeededForm } from "../../lib/query/useSeededForm";
```
- C3 S :89 `type TicketMessage = { source: SaveSource; kind: "saved" | "error"; text: string } | null;` の次に、次の 27 行を足す（塊の 1 行目は空行。:90 の空行と :91 の `export default function` はそのまま）:
```ts

const CONFIG_PATH = "/admin/discord-config";
const TICKET_PATH = "/admin/discord-ticket-config";

/** チケット設定のフォーム（欄の名前は今の画面の値の名前のまま） */
interface TicketForm {
  ticketCategoryId: string;
  ticketButtonChannelId: string;
  staffRoleId: string;
  welcomeTemplate: string;
  smallChannelId: string;
  largeChannelId: string;
  smallRoleName: string;
  largeRoleName: string;
}

const toGuildId = (data: DiscordConfig): string => data.guild_id ?? "";
const toTicketForm = (data: DiscordTicketConfig): TicketForm => ({
  ticketCategoryId: data.ticket_category_id ?? "",
  ticketButtonChannelId: data.ticket_button_channel_id ?? "",
  staffRoleId: data.staff_role_id ?? "",
  welcomeTemplate: data.welcome_template,
  smallChannelId: data.small_channel_id ?? "",
  largeChannelId: data.large_channel_id ?? "",
  smallRoleName: data.small_role_name ?? "Member",
  largeRoleName: data.large_role_name ?? "Partner",
});
```
  （中身は S :133-140 の applyTicketConfig の中身と同じ。"Member"・"Partner" は S :117-118・:139-140 に今ある値で、新しい文字ではない。）
- C4 S :96-99（config・ticketConfig・loading・loadError の useState の 4 行）を次の 7 行に置き換える（:100 の空行は残す）:
```ts
  const configQ = useApiQuery<DiscordConfig>(CONFIG_PATH);
  const ticketQ = useApiQuery<DiscordTicketConfig>(TICKET_PATH);
  const config = configQ.data ?? null;
  const ticketConfig = ticketQ.data ?? null;
  const loadError = configQ.error || ticketQ.error ? t("discordConfig.loadError") : "";
  const cache = useApiCache();
  const invalidate = useInvalidateApi();
```
- C5 S :102 `  const [guildId, setGuildId] = useState("");` を次の 3 行に置き換える（:101 の説明の行と :103 の editingGuild は残す）:
```ts
  const { form: guildId, setForm: setGuildId, ready: guildReady } = useSeededForm(
    CONFIG_PATH, configQ.data, toGuildId, "",
  );
```
- C6 S :109-118（ticketCategoryId から largeRoleName までの useState。welcomeTemplate は :112-114 の 3 行）の 10 行を次の 22 行に置き換える（:108 の説明の行と :119 の ticketSavingSource は残す）:
```ts
  const emptyTicketForm: TicketForm = {
    ticketCategoryId: "", ticketButtonChannelId: "", staffRoleId: "",
    welcomeTemplate: t("discordTicketConfig.welcomeTemplateDefault"),
    smallChannelId: "", largeChannelId: "", smallRoleName: "Member", largeRoleName: "Partner",
  };
  const { form: ticketForm, setForm: setTicketForm, ready: ticketReady } = useSeededForm(
    TICKET_PATH, ticketQ.data, toTicketForm, emptyTicketForm,
  );
  const {
    ticketCategoryId, ticketButtonChannelId, staffRoleId, welcomeTemplate,
    smallChannelId, largeChannelId, smallRoleName, largeRoleName,
  } = ticketForm;
  const setTicketField = (field: keyof TicketForm) => (value: string) =>
    setTicketForm((prev) => ({ ...prev, [field]: value }));
  const setTicketCategoryId = setTicketField("ticketCategoryId");
  const setTicketButtonChannelId = setTicketField("ticketButtonChannelId");
  const setStaffRoleId = setTicketField("staffRoleId");
  const setWelcomeTemplate = setTicketField("welcomeTemplate");
  const setSmallChannelId = setTicketField("smallChannelId");
  const setLargeChannelId = setTicketField("largeChannelId");
  const setSmallRoleName = setTicketField("smallRoleName");
  const setLargeRoleName = setTicketField("largeRoleName");
```
  （emptyTicketForm は今の初めの値（S :109-118）と同じ。フォームを出すのは読めた後だけ（§4-C11）なので、画面には出ない。8 つの set の関数は、JSX の 8 か所（S :422・:471・:479・:487・:495・:503・:511・:519 の `onChange={(e) => setXxx(e.target.value)}`）がそのまま使う。）
- C7 S :131-167（applyTicketConfig の 11 行・空行・fetchAll の説明の行と 9 行・空行・useEffect の 14 行）を次の 9 行に置き換える（:130 と :168 の空行は残す）:
```ts
  /** サーバーの最新値を取り直して画面に反映する（自動セットアップの後。開いた時は useApiQuery が読む） */
  const fetchAll = async () => {
    const [data, ticketData] = await Promise.all([
      cache.fetch(CONFIG_PATH, () => api.get<DiscordConfig>(CONFIG_PATH)),
      cache.fetch(TICKET_PATH, () => api.get<DiscordTicketConfig>(TICKET_PATH)),
    ]);
    if (data) setGuildId(toGuildId(data));
    if (ticketData) setTicketForm(toTicketForm(ticketData));
  };
```
- C8 S :183-184 の 2 行
```ts
      setConfig(updated);
      setGuildId(updated.guild_id ?? "");
```
  を次の 4 行に置き換える（:182 の put の行は変えない）:
```ts
      // 保存の返事は guild_id だけが本物（ほかの欄は既定値）なので、写しは guild_id だけ書き換えて取り直す
      cache.update<DiscordConfig>(["admin", "discord-config"], (old) => ({ ...old, guild_id: updated.guild_id }));
      void invalidate(["admin", "discord-config"]);
      setGuildId(toGuildId(updated));
```
- C9 S :238 `      applyTicketConfig(updated);` を次の 2 行に置き換える:
```ts
      cache.write(TICKET_PATH, updated);
      setTicketForm(toTicketForm(updated));
```
- C10 S :338 `  if (permsLoading || loading) {` → `  if (permsLoading || configQ.isPending || ticketQ.isPending) {`
- C11 S :344 `  }`（読み込み中の return の終わり）の次に、次の 11 行を足す（塊の 1 行目は空行）（:345 の空行と :346 の `return (` はそのまま）:
```tsx

  // 読めなかった時は、空の値で上書きしないようにフォームを出さず、誤りの文だけを出す
  if (!guildReady || !ticketReady) {
    return (
      <PageLayout navKey="nav.discordConfig">
        <div className="dc-page">
          {loadError && <Badge variant="danger">{loadError}</Badge>}
        </div>
      </PageLayout>
    );
  }
```
- :169 の savedGuildId（config から）・:195-199 の handleGuildCancel（setGuildId(savedGuildId)）・:200-216 の validateTicket・:228-237 の put の中身・:263-279 の自動セットアップ（:272 の `await fetchAll();`）・:349 の loadError の Badge・:443 の ticketConfig の表示は変えない。
- 動き: サーバー ID を保存した後、写しの guild_id がすぐ新しい値になるので、今と同じくフォームが閉じて「接続済み」が出る（:170-171 の isConnected・isGuildFormOpen は config を見る）。その後の取り直しで、接続した日時と接続した人も写しに入る（チャネルの画面で使う）。

## 4-D. #4 frontend/src/pages/channels/ChannelsPage.tsx
- D1 S :26 `import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";` → `import { useApiCache, useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";`
- D2 S :90 `export default function ChannelsPage() {` の前（:89 の空行の後）に次の 7 行を足す（最後の空行を含む）:
```ts
/** Discord の設定（/admin/discord-config）のうち、この画面が使う欄。写しは Discord の設定の画面と 1 つ */
type DiscordGuildConfig = {
  guild_id: string | null;
  connected_at: string | null;
  connected_by_staff_name: string | null;
};

```
- D3 S :102-106（discordConfig の useState の 5 行）を消す（:107 の discordConnecting から残す）。
- D4 S :114 `  const canViewDiscord = hasPermission("tenant.profile.view");` の次に 3 行足す:
```ts
  const discordQ = useApiQuery<DiscordGuildConfig>("/admin/discord-config", { enabled: canViewDiscord });
  const discordConfig = discordQ.data ?? null;
  const cache = useApiCache();
```
- D5 S :129-131 の 3 行（api.get・.then(setDiscordConfig)・.catch）を次の 1 行に置き換える（:128 の setBanner は残す）:
```ts
        // 接続の結果は、開いた時の useApiQuery の読みで出る
```
- D6 S :175-182（Discord 設定取得の説明の行・useEffect の 6 行・その後の空行）を消す（:174 の空行と :183 のクリーンアップの説明の行から残す）。
- D7 S :216-218 の 3 行（1 行目と同じ文は S :129 にもあり 2 か所。:129 は §4-D5 で消えるので、D5 を先に当てた後は :216 の 1 か所だけになる。§3(c) の「2 か所以上あるとカードに書いた所」に当たる。D5 より先に当てない）
```ts
        api.get<{ guild_id: string | null; connected_at: string | null; connected_by_staff_name: string | null }>("/admin/discord-config")
          .then((d) => {
            setDiscordConfig(d);
```
  を次の 2 行に置き換える:
```ts
        cache.fetch("/admin/discord-config", () => api.get<DiscordGuildConfig>("/admin/discord-config"))
          .then((d) => {
```
- D8 S :219 `            if (d.guild_id) {` → `            if (d?.guild_id) {`
- D9 S :243 `      setDiscordConfig(null);` を次の 4 行に置き換える:
```ts
      cache.update<DiscordGuildConfig>(["admin", "discord-config"], (old) => ({
        ...old, guild_id: null, connected_at: null, connected_by_staff_name: null,
      }));
      void invalidate(["admin", "discord-config"]);
```
- :120-169 の URL の結果の扱い（D5 の 3 行のほか）・:172-173 の一覧の取り直し・:184-193 のクリーンアップ・:220-227 のお知らせと見張りを外す所・:242 の delete・:527-600 の Discord の欄の表示（`discordConfig?.guild_id` などを読む所）は変えない。`invalidate(["admin", "discord-config"])` は `/admin/discord-config` の写しだけに当たる（`/admin/discord-ticket-config` は頭の言葉が違う）。

## 4-K. #5 今ある試験の写しを消す（ほかの行は変えない）
- K1 frontend/src/pages/admin/DiscordConfigPage.test.tsx: S :6 `import i18n from "../../i18n";` の次に `import { queryClient } from "../../lib/query/apiQuery";` を足す。S :44 `afterEach(() => cleanup());` → `afterEach(() => { cleanup(); queryClient.clear(); });`
- 理由: 画面が同じ 1 個の写しの置き場を使うので、前の試験の写しが次の試験に残らないようにする（段 3 の 1〜5 回目の §4-K と同じ）。
- 実装役は K1 の前に `grep -n "afterEach\|^import i18n" frontend/src/pages/admin/DiscordConfigPage.test.tsx` で行を確かめる（§3(c)）。

## 4-L. #6 frontend/src/lib/query/batch3fPages.test.tsx（新しく作る・全文）
```tsx
/**
 * ADR-1054 段 3 の 6 回目: 本物の画面の試験。
 * Q1 戻った時に写しを先に出す（読み込み中の印を出さない）・裏で取り直す。
 * Q2 読めなかった時はフォームを出さない（空の値で上書きしない）。
 * Q3 Discord の設定はチャネルの画面と Discord の設定の画面で 1 つの写し。
 * QueryClient はアプリと同じ 1 個（apiQuery.ts の queryClient）を使い、毎回消す。
 */
import type { ComponentType } from "react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import DiscordConfigPage from "../../pages/admin/DiscordConfigPage";
import TenantPolicyPage from "../../pages/admin/TenantPolicyPage";
import TenantProfilePage from "../../pages/admin/TenantProfilePage";
import ChannelsPage from "../../pages/channels/ChannelsPage";
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
vi.mock("../../hooks/usePermissions", () => ({ usePermissions: () => ({ hasPermission: () => true, loading: false }) }));
vi.mock("../../hooks/useSSE", () => ({ useSSE: vi.fn() }));
vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
  // api.ts が i18n.ts を読み、i18n.ts が initReactI18next を使う（同じ書き方: src/lib/query/batch3ePages.test.tsx）
  initReactI18next: { type: "3rdParty", init: () => {} },
}));

// 中身は画面の型（TenantProfilePage.tsx:27-39・TenantPolicyPage.tsx:25-34・DiscordConfigPage.tsx:27-42・
// ChannelsPage.tsx の DiscordGuildConfig）と backend の返事（discord_guild_config.py:37-42）の欄
const GUILD = "1288437029213835356";
const profile = {
  id: 1, company_name: "Fixture Company", company_name_en: null, address: null, phone: null, email: null,
  website: null, seal_image_url: null, default_language: "ja", created_at: "", updated_at: "",
};
const policy = {
  inventory_agg_filter: "none", agg_price_threshold_jpy: 12345, agg_qty_threshold: 0, quote_validity_days: 7,
  default_currency: "JPY", document_language: "en", duty_incoterms: "DAP", issue_mode: "pdf",
};
const discordConfig = {
  guild_id: GUILD, connected_at: "2026-11-01T00:00:00Z", connected_by_staff_name: "Fixture Staff",
  role_member: "Member", role_partner: "Partner",
};
const ticket = {
  ticket_category_id: "1288437029213835357", ticket_button_channel_id: "1288437029213835358", staff_role_id: null,
  welcome_template: "Hello", small_channel_id: null, large_channel_id: null,
  small_role_name: "Member", large_role_name: "Partner",
};
const fixtures: Record<string, unknown> = {
  "/admin/tenant-profile": profile,
  "/admin/tenant-policy": policy,
  "/admin/discord-config": discordConfig,
  "/admin/discord-ticket-config": ticket,
  "/meta/channels": { channels: [] },
};
const answer = (path: string) => {
  if (!(path in fixtures)) throw new Error(`Unexpected GET ${path}`);
  return fixtures[path] as never;
};

type Case = {
  name: string; Page: ComponentType; route: string;
  path: string; text: string; value: boolean;
};
const cases: Case[] = [
  { name: "tenant profile", Page: TenantProfilePage, route: "/admin/tenant-profile", path: "/admin/tenant-profile", text: "Fixture Company", value: true },
  { name: "tenant policy", Page: TenantPolicyPage, route: "/admin/tenant-policy", path: "/admin/tenant-policy", text: "12345", value: true },
  { name: "discord config", Page: DiscordConfigPage, route: "/admin/discord-config", path: "/admin/discord-config", text: GUILD, value: false },
  { name: "channels discord section", Page: ChannelsPage, route: "/channels", path: "/admin/discord-config", text: GUILD, value: false },
];

function Tree({ c }: { c: Pick<Case, "Page" | "route"> }) {
  const Page = c.Page;
  return (
    <QueryClientProvider client={queryClient}>
      <QueryAuthSync />
      <MemoryRouter initialEntries={[c.route]}>
        <Routes><Route path={c.route} element={<Page />} /></Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

// フォームの画面は欄の中の値で、ほかは文字で見分ける
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
    if (c.Page !== ChannelsPage) {
      expect(container.querySelector(".sa-loading-block")).toBeNull();
    }
    await waitFor(() => expect(spy).toHaveBeenCalledWith(c.path));
  });
});

describe("forms wait until the record is read (Q2)", () => {
  it("does not show the tenant profile form when the profile could not be read", async () => {
    vi.spyOn(api, "get").mockImplementation(async (path: string) => {
      if (path === "/admin/tenant-profile") throw new Error("Fixture read failure");
      return answer(path);
    });
    const { container } = render(<Tree c={{ Page: TenantProfilePage, route: "/admin/tenant-profile" }} />);
    await screen.findByText("Fixture read failure");
    expect(container.querySelector("form")).toBeNull();
  });

  it("does not show the tenant policy form when the policy could not be read", async () => {
    vi.spyOn(api, "get").mockImplementation(async (path: string) => {
      if (path === "/admin/tenant-policy") throw new Error("Fixture read failure");
      return answer(path);
    });
    const { container } = render(<Tree c={{ Page: TenantPolicyPage, route: "/admin/tenant-policy" }} />);
    await screen.findByText("Fixture read failure");
    expect(container.querySelector("form")).toBeNull();
  });

  it("does not show the discord forms when the ticket settings could not be read", async () => {
    vi.spyOn(api, "get").mockImplementation(async (path: string) => {
      if (path === "/admin/discord-ticket-config") throw new Error("Fixture read failure");
      return answer(path);
    });
    render(<Tree c={{ Page: DiscordConfigPage, route: "/admin/discord-config" }} />);
    await screen.findByText("discordConfig.loadError");
    expect(screen.queryByText("discordConfig.connectionTitle")).toBeNull();
  });
});

describe("one copy of the discord settings (Q3)", () => {
  it("shows the server read on the discord settings page at once on the channels page", async () => {
    const spy = vi.spyOn(api, "get").mockImplementation(async (path: string) => answer(path));
    const first = render(<Tree c={{ Page: DiscordConfigPage, route: "/admin/discord-config" }} />);
    await screen.findAllByText(GUILD);
    first.unmount();
    spy.mockClear();
    spy.mockImplementation(() => new Promise<never>(() => {}));
    render(<Tree c={{ Page: ChannelsPage, route: "/channels" }} />);
    expect(screen.queryAllByText(GUILD).length).toBeGreaterThan(0);
    await waitFor(() => expect(spy).toHaveBeenCalledWith("/admin/discord-config"));
  });
});
```
- LoadingBlock の見分けは `.sa-loading-block`（段 3 の 1〜5 回目のカード §4-L と同じ）。チャネルの画面は、一覧（/meta/channels）を写しの無い所から読む時に LoadingBlock を出す（5 回目の §4-A6）が、Q1 の 2 回目は一覧の写しもあるので出ない。ただしこの試験が見るのは Discord の欄なので、チャネルの画面では LoadingBlock を数えない（`c.Page !== ChannelsPage`）。
- 「Fixture Company」は会社の情報の会社名の欄（S TenantProfilePage.tsx:151）、「12345」は会社の方針の価格のしきい値の欄（S TenantPolicyPage.tsx の tp-price-threshold の value）、GUILD は Discord の設定の画面の接続済みのサーバー ID（S DiscordConfigPage.tsx:386）とチャネルの画面の Discord の欄のサーバー ID（S ChannelsPage.tsx:579）に出る。
- Discord の欄はチャネルの一覧の読み込み中の印の外にある（S ChannelsPage.tsx:527 は :421-524 の一覧の分かれ道の後）ので、一覧を読めていなくても出る。
- 「discordConfig.connectionTitle」は Discord の設定の画面の 1 枚目のカードの見出し（S DiscordConfigPage.tsx の connectionTitle の t）。react-i18next を差し替えて t がキーをそのまま返すので、キーの文字で見分ける。
- 会社の情報と会社の方針は権限があるので読む（usePermissions の差し替えは全部 true）。Discord の設定の画面は自動セットアップなどを押さないので、ほかの path は読まない。

## 4-M. 実装役の手順（1 手順 1 命令。<W> は手順1 で作られた作業場所の絶対パス）
手順1. クラウドの決まり（S scripts/agent-hooks/cloud/rules.md:15）どおり、作業場所を作り、push 済みの枝の先頭に合わせる（設計担当が §1 #7〜#9 を push 済み）。
  cd "$(git rev-parse --show-toplevel)" && bash scripts/new-worktree.sh release/line-like-speed-batch3f
  （出力に出た作業場所の絶対パスを <W> として報告に書く。）
  cd <W> && git fetch origin release/line-like-speed-batch3f
  cd <W> && git switch -C release/line-like-speed-batch3f origin/release/line-like-speed-batch3f
  cd <W> && git rev-parse HEAD origin/release/line-like-speed-batch3f
  （2 行が同じことを確かめる。違えば停止して BLOCKED: で報告する。main は取り込まない。reset・rebase・force・merge・pull は使わない）
  cd <W> && ./scripts/dev/executor-preflight.sh > /tmp/b3f-preflight.txt 2>&1
  cd <W> && grep -n "FAIL" /tmp/b3f-preflight.txt | head -20
  cd <W> && grep -n "origin/main は存在" /tmp/b3f-preflight.txt | head -3
  （FAIL の行が次の 3 つのうちのどれかだけなら続ける: `GitHub API に到達不可` の 1 件・`gh auth switch --hostname github.com --user shingo-cc` の失敗の 1 件・その結果の `PREFLIGHT FAIL` の行。理由は段 3 の 1 回目のカード §4-M 手順1 と同じ。続ける時は `[OK]   origin/main は存在` の行があることを 2 つ目の grep で確かめ、無ければ停止する。ほかの FAIL が 1 件でもあれば停止し、BLOCKED: で grep の出力を報告する。）
  cd <W> && git fetch origin main
  cd <W> && git diff --stat 43070f593baf30a9c85b7f441057f22ebf9c6554 origin/main -- frontend/src | tail -12
  （§3(a) の確かめ。）
手順2. 依存を入れ、§3(b) を確かめ、変える前の lint の警告を数える。
  cd <W>/frontend && npm ci > /tmp/b3f-ci.txt 2>&1
  cd <W> && tail -5 /tmp/b3f-ci.txt
  cd <W>/frontend && grep -n '"@tanstack/react-query"' package.json
  cd <W>/frontend && npx eslint src/pages/admin/TenantProfilePage.tsx src/pages/admin/TenantPolicyPage.tsx src/pages/admin/DiscordConfigPage.tsx src/pages/channels/ChannelsPage.tsx > /tmp/b3f-lint-before.txt 2>&1
  cd <W> && tail -5 /tmp/b3f-lint-before.txt
手順3. §4-L の全文で #6 を作り、§4-A〜§4-K のとおり #1〜#5 を直す。各ファイルを直す前に、§4 の「変更前」の文を `grep -n` で確かめる（§3(c)）。終わったら残りが無いことを確かめる。
  cd <W> && grep -nw "setLoading\|setLoadError\|setConfig\|setTicketConfig\|applyTicketConfig\|setDiscordConfig\|useCallback\|useEffect" frontend/src/pages/admin/TenantProfilePage.tsx frontend/src/pages/admin/TenantPolicyPage.tsx frontend/src/pages/admin/DiscordConfigPage.tsx | head -20
  （0 行であること。出たら §4 の写し違いを直す。）
  cd <W> && grep -nw "setDiscordConfig" frontend/src/pages/channels/ChannelsPage.tsx | head -5
  （0 行であること。）
  cd <W> && grep -c "/admin/discord-config" frontend/src/pages/channels/ChannelsPage.tsx
  （5 であること。数えるのは行で、§4-D2 の説明の行・D4・D7（1 行に 2 か所）・S :242 の delete・S :592 の navigate。違えば数えた行を `grep -n` で報告に書いて停止する。）
  cd <W> && grep -c "api\." frontend/src/pages/admin/TenantProfilePage.tsx frontend/src/pages/admin/TenantPolicyPage.tsx frontend/src/pages/admin/DiscordConfigPage.tsx frontend/src/pages/channels/ChannelsPage.tsx
  （どのファイルも 1 以上であること。§3(g)。）
手順4. 型を作ってから試験を流す（新しい試験・直した今ある試験・全部の試験・型・lint）。作る型（frontend/src/api/generated/）は .gitignore で除かれるので commit に入らない。
  cd <W>/frontend && npm run generate:api-types > /tmp/b3f-gen.txt 2>&1
  cd <W> && tail -3 /tmp/b3f-gen.txt
  cd <W>/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/lib/query > /tmp/b3f-unit.txt 2>&1
  cd <W> && tail -30 /tmp/b3f-unit.txt
  cd <W>/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/pages/admin/DiscordConfigPage.test.tsx > /tmp/b3f-pages.txt 2>&1
  cd <W> && tail -30 /tmp/b3f-pages.txt
  cd <W>/frontend && npm run test:unit > /tmp/b3f-unit-all.txt 2>&1
  cd <W> && tail -15 /tmp/b3f-unit-all.txt
  cd <W>/frontend && npx tsc --noEmit -p . > /tmp/b3f-tsc.txt 2>&1
  cd <W> && tail -20 /tmp/b3f-tsc.txt
  cd <W>/frontend && npx eslint src/lib/query src/pages/admin/TenantProfilePage.tsx src/pages/admin/TenantPolicyPage.tsx src/pages/admin/DiscordConfigPage.tsx src/pages/admin/DiscordConfigPage.test.tsx src/pages/channels/ChannelsPage.tsx > /tmp/b3f-lint.txt 2>&1
  cd <W> && tail -20 /tmp/b3f-lint.txt
  （lint の警告が手順2 の数より増えていないこと・誤りが 0 であること。§3(d)。）
手順5. 本番と同じ形で組み立てられるか確かめる。
  cd <W>/frontend && npm run build > /tmp/b3f-build.txt 2>&1
  cd <W> && tail -15 /tmp/b3f-build.txt
手順6. 変わったファイルが §1 の #1〜#6 だけか確かめ、画面の書く path とフォームの行が変わっていないことを見る。
  cd <W> && git status --short | head -20
  cd <W> && git diff -w --stat origin/release/line-like-speed-batch3f | tail -12
  cd <W> && git diff -w origin/release/line-like-speed-batch3f -- frontend/src/pages | head -500
手順7. commit する。
  cd <W> && git add frontend/src/pages/admin/TenantProfilePage.tsx frontend/src/pages/admin/TenantPolicyPage.tsx frontend/src/pages/admin/DiscordConfigPage.tsx frontend/src/pages/channels/ChannelsPage.tsx frontend/src/pages/admin/DiscordConfigPage.test.tsx frontend/src/lib/query/batch3fPages.test.tsx
  cd <W> && git commit -m "feat: 会社の情報・方針・Discordの設定を写しを先に出して裏で取り直す形に（ADR-1054 段3の6回目）"
手順8. commit が在ることを確かめてから push する（--no-verify は使わない。push の前の検査が × なら直してから push。fast-forward でないと断られたら直さず BLOCKED:）。
  cd <W> && git log -3 --oneline
  cd <W> && git push -u origin release/line-like-speed-batch3f
手順9. 報告を返す。PR は作らない（設計担当が手元で作る）。報告の 1 つの発言は 600 文字以内にして、番号付きの発言に分ける。報告には手順ごとの tail の出力（生のまま）と、§3(a)〜(g) の結果を書く。

## 4. GO と承認・PO の操作
- PO の実装承認: 2026-11-03 PO「つぎを進める」（5 回目の受入の記録の後に、残りの遅い画面とチャネルの画面の Discord の欄を直す）。それまでの PO 選択「1」（権限の要る画面も測れるように権限を足し、同じ形で本番の測定まで直す）・「操作していいから足して」も同じ流れ。ADR-1054 は Accepted。このカードの審査合格の後に、設計担当がクラウドの Sonnet へ渡す。
- 触るのは frontend の画面 4 個・試験と書類だけで、migrations・deploy.yml・本番 scripts を含まない（番号付き GO の要る危ない PR ではない）。main へのマージで本番の画面に出る（deploy.yml が main への push で動く）。マージは PO の委任に基づき設計担当（Claude Opus）が、マージ前の審査役の APPROVE と確認がすべて pass の後に行う。
- PO が操作することはない。

## 5. 受入（○×）
| # | 基準 | 検証方法 |
|---|---|---|
| B1 | Q1（4 つとも戻った時に前の中身が出る・フォームの画面は LoadingBlock 0 個・裏で取り直す）と Q2（3 画面とも読めなかった時はフォームを出さない）と Q3（Discord の設定の画面で読んだサーバー ID がチャネルの画面にすぐ出る）が合格。段 3 の 1 回目の Q2・Q3（K5）と 2〜5 回目の Q1・Q2 も合格のまま | /tmp/b3f-unit.txt の最後（batch3fPages.test.tsx の 8 件が passed・batch3ePages.test.tsx・batch3dPages.test.tsx・batch3cPages.test.tsx・batch3bPages.test.tsx・batch3aPages.test.tsx・useSeededForm.test.tsx・apiQuery.test.tsx・stage2Pages.test.tsx も passed）と、PR の CI の unit-run が success |
| B2 | 今ある画面の試験（DiscordConfigPage.test.tsx の 9 件）・全部の試験・型・lint・組み立てが通る | /tmp/b3f-pages.txt・b3f-unit-all.txt・b3f-tsc.txt・b3f-lint.txt・b3f-build.txt の最後と、PR の確認がすべて pass |
| B3 | 変わったのは §1 の 9 ファイルだけ。画面の書く path と中身・フォームの欄は変わっていない | gh pr diff --name-only と git diff -w（§4-M 手順6） |
| B4 | QueryClient を作るのは apiQuery.ts の 1 か所だけ・staleTime を設定していない・写しをブラウザの保存に書かない・`/admin/discord-config` を api.get で直に読む所が画面に残っていない | `git grep -n "new QueryClient" -- frontend/src` が 1 行、`git grep -n "staleTime:" -- frontend/src` が 0 行、`git grep -n -i "persist" -- frontend/src/lib/query frontend/package.json` が 0 行、`git grep -n 'api.get<[^>]*>("/admin/discord-config")' -- frontend/src/pages` が 2 行だけ: ChannelsPage.tsx の §4-D7 の cache.fetch の中の 1 行と、§2 で触らない frontend/src/pages/inbox/InboxKartePanel.tsx の S :115 の 1 行（DiscordConfigPage.tsx は CONFIG_PATH で書くので 0 行） |
| B5 | マージの後、毎朝の画面の記録を手で 1 回動かし、§0 V3f-1 の 8 行で K1（戻った時の秒）≤0.1 秒、K2（初めて開く秒）≤2 秒、403・5xx が 0 件。/management-center/channels は 0.1 秒以下のまま。ほかの行は K2 の最大と 2 秒を超えた画面の数が、基準の回（prod-ui-check run 41614984342）から悪化していない | prod-ui-check の実行の要約（設計担当。`gh workflow run prod-ui-check.yml --ref main` の後に要約の表を読む）。基準の値は下の表と design §3-4-19 |
| B6 | 取り直した後の中身が DB と一致（tenant 001）: 会社の情報の会社名・会社の方針の価格のしきい値・Discord のサーバー ID が、本番 DB の tenant 001 の値と同じ | 設計担当が本番の読むだけの道（ADR-1024）で tenant 001 の行を読む。画面の値は PO のログイン済みの Chrome（設計担当が操作）で読む。読めない時は「画面の値はまだ確かめていない」と記録し、backend を変えていないこと（B3）と Q1 を根拠にする |
| B7 | マージの後、deploy が成功し、本番の画面が開く | deploy.yml の実行の結論 success と時刻。本番 https://app.salesanchor.jp/ の 3 画面とチャネルの画面が開き、ブラウザの誤りの記録に TanStack 由来の誤りが無い（設計担当） |

B5 の基準（prod-ui-check run 41614984342・測った日時 2026-11-03 18:59:48 JST・main 1eefb57。8 行とも 403 0 件・5xx 0 件）:

| 行 | K1（秒） |
|---|---|
| /admin/discord-config | 0.25 |
| /management-center/discord-config | 0.24 |
| /admin/tenant-policy | 0.21 |
| /management-center/tenant-policy | 0.21 |
| /admin/tenant-profile | 0.21 |
| /management-center/tenant-profile | 0.22 |
| /admin → /admin/tenant-profile | 0.21 |
| /channels | 0.24 |
