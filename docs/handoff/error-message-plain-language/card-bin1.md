---
mode: handoff
---
# 実装カード 便1: Discord 連携の失敗の文を「何が起きたか＋次にすること」にする

親: [design.md](./design.md) §2-1（K1〜K3）・§4（4-2 対応表・4-3 文・4-4 変えるファイル・4-6 試験）・§10。ADR: [ADR-1071](../../adr/ADR-1071-plain-language-error-messages.md)（Proposed）。

- 状態: カード作成済み（2026-11-07 Opus）。
- 実装承認: PO 2026-11-07 の選択「1」（文の一覧で決め、作り始める）。文の一覧の 5 と 7 は PO 本人の文。設計は 2 回目の審査で APPROVE（design.md §10）。マージと本番への反映の GO は兼ねない（Opus が委任に基づき別に出す）。
- 担当: クラウドの Sonnet（実装）。Opus は審査・PR 作成・GO・マージ判断。
- 区分: 画面と API の文の変更。migrations・deploy.yml・scripts・.github は触らない。
- 作業する枝: `release/error-message-plain-language`（設計の文書とこのカードが載って push 済み）。新しい枝は作らない。

## 0. カード発行前チェック（docs/ai-agents/design-partner.md §5.5 の照合結果）

| 番号 | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲む | ○ |
| 2 | PR は Opus が作る（担当は PR を作らない） | ○（§6） |
| 3 | 報告の宛先（完了報告の本文に生出力を全文） | ○（§7） |
| 4 | 1便1目的（Discord 連携の失敗の文だけ。Meta・他の画面は触らない） | ○ |
| 5 | 既存の枝の起点を明示（origin/release/error-message-plain-language） | ○（§5 手順1） |
| 6 | 書式は実例で示す（新しいファイルは全文、直す所は前後のコード） | ○（§3） |
| 7 | 合格基準を出力まで縛る（触るファイル以外 0） | ○（§5 手順9・10） |
| 8 | 件数の判定には名前を出す手順を対で置く | ○（§5 手順6） |
| 9 | 出力量に上限のないコマンドを使わない | ○（`| tail -N`） |
| 10 | 報告様式3点（停止の3点・受領と終端の合図・冒頭の便名） | ○（§7） |
| 11 | 行番号を停止条件にしない（前後のコードで探す） | ○（§3） |
| 12 | 停止は不可逆・本番影響のものだけ。数の食い違いは記録して続行 | ○（§4） |
| 13 | 委任文の定型4点（sleep 禁止・Write/Edit で書く・PR は作らない・フックに止められたら言い換えない） | ○（§4） |

読んだ節（docs/handoff/design-partner-card-ops/guards/）: 00-common.md・04-worktree.md・05-pr.md。手順1・2 の作業場所と Python の作り方は、同じ日の実装カード docs/handoff/s1-rls-stage5/card-pool-reset-bin2.md の手順（クラウドで通った形）に合わせた。

基準: 設計の土台 origin/main 67d7bbf87。2026-11-07 に origin/main 7947055fe と比べ、`frontend/src/pages/channels/ChannelsPage.tsx`・`frontend/src/pages/admin/DiscordOwnServerPanel.tsx`・`backend/app/routers/discord_oauth.py` の差分は 0（`git diff --quiet` で確認）。

## 1. 目的（便1 で起きること）

- Discord 連携に失敗したとき、2 つの画面（お客さん用の連携の画面・自社用の Discord 設定の画面）に、理由ごとの文（何が起きたか＋次にすること）が出る。
- 同じ理由なら 2 つの画面で同じ文が出る。
- 連携を始めるときの失敗で、サーバーの日本語の直書き（権限名・仕組みの名前を含む文）が画面に出なくなる。

## 2. 触るファイル（これ以外は触らない）

| ファイル | 何をする |
|---|---|
| `backend/app/routers/discord_oauth.py` | 連携の開始の 3 か所の `detail` を理由コードの dict にする（§3-1） |
| `backend/tests/test_discord_oauth.py` | 開始の 3 か所の試験を足す・直す（§3-2） |
| `frontend/src/features/discord-connect/discordConnectError.ts` | 新しく作る（§3-3 の全文） |
| `frontend/src/features/discord-connect/discordConnectError.test.ts` | 新しく作る（§3-4 の全文） |
| `frontend/src/pages/channels/ChannelsPage.tsx` | 3 か所（§3-5） |
| `frontend/src/pages/admin/DiscordOwnServerPanel.tsx` | 2 か所（§3-6） |
| `frontend/src/pages/admin/DiscordOwnServerPanel.test.tsx` | 試験を 2 つ足す（§3-7） |
| `frontend/src/pages/channels/ChannelsPage.discordConnectError.test.tsx` | 新しく作る（§3-8） |
| `frontend/src/locales/ja.json`・`frontend/src/locales/en.json` | 新しい 10 キーを足し、古い 3 キーを消す（§3-9） |
| `docs/handoff/discord-oauth-ownership-proof/design.md` | 45 行あたりの 1 行を直す（§3-10） |

触らないもの: 戻り口の処理（`discord_oauth.py` の `discord_oauth_callback` の中。理由コードの文字列も変えない）・`backend/app/routers/meta_inbox.py`・Meta 連携の文（`channels.errorReason.*`・`channels.connectError`）と ChannelsPage の Meta 側の処理・`discordOwnServer.requestFailed` のキーと、招待以外のその使い所・`frontend/src/lib/api.ts`・表示の部品と色・CSS・ADR と design.md・migrations・deploy.yml・scripts・.github。

## 3. 直す中身（design §4 が正。食い違えば design に従い、報告に書く）

### 3-1 `backend/app/routers/discord_oauth.py`（関数 `discord_oauth_start` の中だけ）

3 か所の `detail=` の値だけを変える。`status_code`・`logger` の行・順番は変えない。

| 探す文（変更前の `detail=` の値） | 変更後 |
|---|---|
| `"権限が不足しています: tenant.profile.edit"` | `{"reason": "permission_denied"}` |
| `"一時的に Discord 連携を開始できません（設定不足）"` | `{"reason": "discord_not_configured"}` |
| `"一時的に Discord 連携を開始できません（Redis 接続失敗）"` | `{"reason": "redis_error"}` |

### 3-2 `backend/tests/test_discord_oauth.py`

- 既存の `test_09a_start_without_secret_is_503` の `assert res.status_code == 503` の次の行に、`assert res.json()["detail"] == {"reason": "discord_not_configured"}` を足す。
- クラス `TestDiscordOAuthStart` の最後に、次の 2 つを足す（`patch`・`AsyncMock`・`pytest`・`_SECRET`・`_ALL_PERMS` は同じファイルに既にある）。

```python
    @pytest.mark.asyncio
    async def test_start_own_without_edit_permission_returns_reason(self, app_client, monkeypatch):
        """自社用で tenant.profile.edit が無いと 403。detail は理由コードだけで日本語を含まない（ADR-1071）。"""
        monkeypatch.setenv("DISCORD_CLIENT_SECRET", _SECRET)
        with patch(
            "app.routers.discord_oauth.load_user_permissions",
            AsyncMock(return_value=set(_ALL_PERMS)),
        ):
            res = await app_client.post("/api/v1/discord/oauth/start", json={"purpose": "own"})
        assert res.status_code == 403
        assert res.json()["detail"] == {"reason": "permission_denied"}

    @pytest.mark.asyncio
    async def test_start_state_store_down_returns_reason(self, app_client, monkeypatch):
        """札を発行できないと 503。detail は理由コードだけ（ADR-1071）。"""
        from app.services import oauth_state

        monkeypatch.setenv("DISCORD_CLIENT_SECRET", _SECRET)
        with patch(
            "app.routers.discord_oauth.oauth_state.issue_state",
            AsyncMock(side_effect=oauth_state.OAuthStateError("down")),
        ):
            res = await app_client.post("/api/v1/discord/oauth/start")
        assert res.status_code == 503
        assert res.json()["detail"] == {"reason": "redis_error"}
```

- `oauth_state.OAuthStateError` の作り方（引数）が違って試験が落ちたら、`backend/app/services/oauth_state.py` のクラスの定義に合わせて引数だけ直し、報告に書く。
- クラス名 `TestDiscordOAuthStart` が無ければ、ファイルの最後に置いて報告に書く。

### 3-3 `frontend/src/features/discord-connect/discordConnectError.ts`（新規・この全文で作る）

```ts
/**
 * Discord 連携（Bot の追加）の失敗の理由コード → 文言キーの対応表（ADR-1071 便1）。
 *
 * 戻り口（backend/app/routers/discord_oauth.py の callback）が URL の reason に入れるコードと、
 * 連携の開始の API が detail.reason に入れるコードを受け取る。
 * 文言は i18n（discordConnect.error.*）。2 つの画面（ChannelsPage・DiscordOwnServerPanel）は
 * この表を通すだけにする。前例: frontend/src/pages/inbox/discordSendError.ts（ADR-159）。
 */
import { ApiError } from "../../lib/api";

/** サーバーが返し得る理由コード（戻り口 12 個＋開始の権限 1 個）。突き合わせの試験がサーバーのコードと照らす */
export const DISCORD_CONNECT_ERROR_REASONS = [
  "invalid_state",
  "missing_state",
  "invalid_payload",
  "missing_code",
  "missing_guild_id",
  "invalid_guild_id",
  "guild_mismatch",
  "guild_already_registered",
  "code_exchange_failed",
  "missing_guild_in_token",
  "redis_error",
  "discord_not_configured",
  "permission_denied",
] as const;

export type DiscordConnectErrorReason = (typeof DISCORD_CONNECT_ERROR_REASONS)[number];

/** 表が返し得る文言キーの全部（i18n の試験が ja / en の両方にあることを確かめる） */
export const DISCORD_CONNECT_ERROR_KEYS = [
  "discordConnect.error.stateExpired",
  "discordConnect.error.discordInterrupted",
  "discordConnect.error.serverNotSelected",
  "discordConnect.error.serverNotVerified",
  "discordConnect.error.serverAlreadyRegistered",
  "discordConnect.error.discordCheckFailed",
  "discordConnect.error.serviceUnavailable",
  "discordConnect.error.permissionDenied",
  "discordConnect.error.unknown",
  "discordConnect.error.disconnectFailed",
] as const;

/** 理由コードから文言キーを選ぶ。表に無いコード・null は unknown の文にする（生の値は出さない） */
export function getDiscordConnectErrorKey(reason: string | null): string {
  switch (reason) {
    case "invalid_state":
      return "discordConnect.error.stateExpired";
    case "missing_state":
    case "invalid_payload":
    case "missing_code":
    case "invalid_guild_id":
      return "discordConnect.error.discordInterrupted";
    case "missing_guild_id":
      return "discordConnect.error.serverNotSelected";
    case "guild_mismatch":
    case "missing_guild_in_token":
      return "discordConnect.error.serverNotVerified";
    case "guild_already_registered":
      return "discordConnect.error.serverAlreadyRegistered";
    case "code_exchange_failed":
      return "discordConnect.error.discordCheckFailed";
    case "redis_error":
    case "discord_not_configured":
      return "discordConnect.error.serviceUnavailable";
    case "permission_denied":
      return "discordConnect.error.permissionDenied";
    default:
      return "discordConnect.error.unknown";
  }
}

/**
 * 連携の開始の API の失敗から理由コードを取り出す。取り出しはこの関数だけで行う。
 * POST は送り直しをしないので、失敗は ApiError で responseDetail に body.detail が入る（frontend/src/lib/api.ts の request）。
 * 通信そのものの失敗・時間切れ・理由コードの無い応答は null（unknown の文になる）。
 */
export function getDiscordConnectErrorReason(e: unknown): string | null {
  if (!(e instanceof ApiError)) return null;
  const detail: unknown = e.responseDetail;
  if (detail === null || typeof detail !== "object") return null;
  const reason = (detail as { reason?: unknown }).reason;
  return typeof reason === "string" ? reason : null;
}
```

### 3-4 `frontend/src/features/discord-connect/discordConnectError.test.ts`（新規・この全文で作る）

```ts
/* eslint-disable local/no-japanese-literal -- テスト: PO 指定の日本語文言を検証する（ADR-1071） */
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { ApiError } from "../../lib/api";
import ja from "../../locales/ja.json";
import en from "../../locales/en.json";
import {
  DISCORD_CONNECT_ERROR_KEYS,
  DISCORD_CONNECT_ERROR_REASONS,
  getDiscordConnectErrorKey,
  getDiscordConnectErrorReason,
} from "./discordConnectError";

type Dict = { [key: string]: string | Dict };

function lookup(dict: Dict, dotted: string): string | undefined {
  const value = dotted.split(".").reduce<string | Dict | undefined>(
    (acc, key) => (acc && typeof acc === "object" ? acc[key] : undefined),
    dict,
  );
  return typeof value === "string" ? value : undefined;
}

const P = "discordConnect.error.";

describe("getDiscordConnectErrorKey", () => {
  it.each([
    ["invalid_state", "stateExpired"],
    ["missing_state", "discordInterrupted"],
    ["invalid_payload", "discordInterrupted"],
    ["missing_code", "discordInterrupted"],
    ["invalid_guild_id", "discordInterrupted"],
    ["missing_guild_id", "serverNotSelected"],
    ["guild_mismatch", "serverNotVerified"],
    ["missing_guild_in_token", "serverNotVerified"],
    ["guild_already_registered", "serverAlreadyRegistered"],
    ["code_exchange_failed", "discordCheckFailed"],
    ["redis_error", "serviceUnavailable"],
    ["discord_not_configured", "serviceUnavailable"],
    ["permission_denied", "permissionDenied"],
  ])("%s → %s", (reason, key) => {
    expect(getDiscordConnectErrorKey(reason)).toBe(P + key);
  });

  it("表に無いコードと null は unknown", () => {
    expect(getDiscordConnectErrorKey("something_new")).toBe(P + "unknown");
    expect(getDiscordConnectErrorKey(null)).toBe(P + "unknown");
  });

  it("全コードの行き先が キーの一覧 に入っている", () => {
    for (const reason of DISCORD_CONNECT_ERROR_REASONS) {
      expect(DISCORD_CONNECT_ERROR_KEYS as readonly string[]).toContain(getDiscordConnectErrorKey(reason));
    }
  });
});

describe("getDiscordConnectErrorReason", () => {
  it("ApiError の responseDetail.reason を返す", () => {
    expect(getDiscordConnectErrorReason(new ApiError("x", 503, { reason: "redis_error" }))).toBe("redis_error");
  });
  it("理由コードが無い・ApiError でないときは null", () => {
    expect(getDiscordConnectErrorReason(new ApiError("x", 500, "text"))).toBeNull();
    expect(getDiscordConnectErrorReason(new ApiError("x", 500, null))).toBeNull();
    expect(getDiscordConnectErrorReason(new ApiError("x", 500, { reason: 1 }))).toBeNull();
    expect(getDiscordConnectErrorReason(new Error("Failed to fetch"))).toBeNull();
  });
});

describe("サーバーのコードとの突き合わせ", () => {
  // CI の frontend 試験は repo 全体を取り出し、frontend で動く（.github/workflows/e2e.yml の unit-run）。
  // 前例: src/features/tcg-product-import/TcgProductImportPanel.test.tsx
  const source = readFileSync("../backend/app/routers/discord_oauth.py", "utf8");
  const found = new Set<string>();
  for (const m of source.matchAll(/reason=([a-z_]+)/g)) found.add(m[1]);
  for (const m of source.matchAll(/_ExchangeError\("([a-z_]+)"\)/g)) found.add(m[1]);
  for (const m of source.matchAll(/"reason":\s*"([a-z_]+)"/g)) found.add(m[1]);

  it("サーバーの理由コードは 13 個（取り出しの式が壊れていないこと）", () => {
    expect([...found].sort()).toHaveLength(13);
  });
  it("サーバーの理由コードが全部 表 にある", () => {
    expect([...found].sort()).toEqual([...DISCORD_CONNECT_ERROR_REASONS].sort());
  });
});

describe("i18n", () => {
  it("全キーが ja / en にある（空でない）", () => {
    for (const key of DISCORD_CONNECT_ERROR_KEYS) {
      expect(lookup(ja as Dict, key), `ja:${key}`).toBeTruthy();
      expect(lookup(en as Dict, key), `en:${key}`).toBeTruthy();
    }
  });

  it("ja の文は PO の承認した一覧のとおり（design.md §4-3）", () => {
    const j = ja as Dict;
    expect(lookup(j, P + "stateExpired")).toBe("時間切れにより連携できませんでした。もう一度お試しください。");
    expect(lookup(j, P + "discordInterrupted")).toBe("Discordでの操作が途中で止まったため、連携できませんでした。もう一度お試しください。");
    expect(lookup(j, P + "serverNotSelected")).toBe("サーバーを選択していないため連携できませんでした。追加するサーバーを選んでください。");
    expect(lookup(j, P + "serverNotVerified")).toBe("選択したサーバーが確認できませんでした。もう一度お試しください。");
    expect(lookup(j, P + "serverAlreadyRegistered")).toBe("このサーバーはすでに登録されているため、連携できませんでした。別のサーバーを選んでください。");
    expect(lookup(j, P + "discordCheckFailed")).toBe("Discordとの確認がうまくいかず、連携できませんでした。時間をおいてもう一度お試しください。");
    expect(lookup(j, P + "serviceUnavailable")).toBe("システムの一時的な不具合で連携できませんでした。時間をおいてもう一度お試しください。続く場合はサポートにお問い合わせください。");
    expect(lookup(j, P + "permissionDenied")).toBe("この操作をする権限がありません。会社の管理者に権限を付けてもらってください。");
    expect(lookup(j, P + "unknown")).toBe("連携できませんでした。もう一度お試しください。続く場合はサポートにお問い合わせください。");
    expect(lookup(j, P + "disconnectFailed")).toBe("連携を外せませんでした。もう一度お試しください。続く場合はサポートにお問い合わせください。");
  });
});
```

- 突き合わせの数が 13 にならないときは、試験の期待値を変えずに、取り出された一覧（`console.log([...found].sort())` の出力）を報告に書いて続ける。

### 3-5 `frontend/src/pages/channels/ChannelsPage.tsx`（3 か所）

1. import を 1 行足す（`import { Button } from "../../components/Button";` の次の行）:
   `import { getDiscordConnectErrorKey, getDiscordConnectErrorReason } from "../../features/discord-connect/discordConnectError";`
2. 戻ったときの帯（`if (discordStatus === "connected") {` の `else` の中）:
   - 変更前: `setBanner({ type: "error", text: t("channels.discordConnectError") });`
   - 変更後: `setBanner({ type: "error", text: t(getDiscordConnectErrorKey(url.searchParams.get("reason"))) });`
3. 連携の開始の失敗（`api.post<{ invite_url: string }>("/discord/oauth/start", {})` を含む関数の `catch (e)` の中の 1 行）:
   - 変更前: `const msg = e instanceof ApiError ? e.message : (e instanceof Error ? e.message : t("channels.discordConnectError"));`
   - 変更後: `const msg = t(getDiscordConnectErrorKey(getDiscordConnectErrorReason(e)));`
4. 切断の失敗（関数 `handleDiscordDisconnect` の `catch (e)` の中の 1 行。上と同じ文の 2 つ目）:
   - 変更前: 上と同じ文
   - 変更後: `const msg = t("discordConnect.error.disconnectFailed");`
   - この `catch (e)` で `e` を使わなくなる。lint が未使用で止めたら `catch {` にする。
- `ApiError` の import は Meta 側でまだ使うので消さない。

### 3-6 `frontend/src/pages/admin/DiscordOwnServerPanel.tsx`（2 か所）

1. import を 1 行足す（`import { LoadingBlock } from "../../components/loading";` の次の行）:
   `import { getDiscordConnectErrorKey, getDiscordConnectErrorReason } from "../../features/discord-connect/discordConnectError";`
2. 招待から戻ったときの結果（`} else if (status === "error") {` の中）:
   - 変更前:
     ```tsx
      setNotice({
        kind: "danger",
        text:
          params.get("reason") === "guild_already_registered"
            ? t("discordOwnServer.guildAlreadyRegistered")
            : t("discordOwnServer.connectError"),
      });
     ```
   - 変更後:
     ```tsx
      setNotice({ kind: "danger", text: t(getDiscordConnectErrorKey(params.get("reason"))) });
     ```
3. 招待の失敗（関数 `handleInvite` の catch）:
   - 変更前: `} catch {` と次の行 `setNotice({ kind: "danger", text: t("discordOwnServer.requestFailed") });`
   - 変更後: `} catch (e) {` と次の行 `setNotice({ kind: "danger", text: t(getDiscordConnectErrorKey(getDiscordConnectErrorReason(e))) });`
   - 同じファイルの他の `requestFailed`（招待以外）は変えない。

### 3-7 `frontend/src/pages/admin/DiscordOwnServerPanel.test.tsx`（ファイルの最後に 2 つ足す）

```tsx
it("shows the plain sentence for the reason when returning from Discord", async () => {
  window.history.pushState({}, "", "/admin/discord-config?tab=own&discord_status=error&reason=invalid_state");
  view();
  await screen.findByText(i18n.t("discordConnect.error.stateExpired"));
});

it("shows the plain sentence when starting the invite fails", async () => {
  mockConfig(null);
  vi.mocked(api.post).mockRejectedValue(
    Object.assign(new ApiError("x"), { responseDetail: { reason: "redis_error" } }),
  );
  view();
  fireEvent.click(await screen.findByText("Invite the bot to your own server"));
  await screen.findByText(i18n.t("discordConnect.error.serviceUnavailable"));
});
```

- このファイルの `vi.mock("../../lib/api", ...)` の `ApiError` は `class extends Error {}`。`discordConnectError.ts` も同じ `../../lib/api` を読むので、同じ偽物の class になる（instanceof が通る）。通らずに落ちたら、出力を報告に書き、`discordConnectError.ts` は変えずに試験だけで直せるか試す。
- 招待のボタンが `mockConfig(null)` で出ないときは、ボタンが出る条件をファイルから読んで試験の前提だけ合わせ、報告に書く。

### 3-8 `frontend/src/pages/channels/ChannelsPage.discordConnectError.test.tsx`（新規）

- 手本は 3-7 と `DiscordOwnServerPanel.test.tsx` の冒頭（`vi.mock` で `../../lib/api` と `../../hooks/usePermissions` を偽物にし、`MemoryRouter` で描く。`i18n.changeLanguage("en")`。`afterEach` で `cleanup()` と `queryClient.clear()`）。
- `api.get` の偽物: `/meta/channels` には `{ channels: [] }`、`/admin/discord-config` には `{ guild_id: null, connected_at: null, connected_by_staff_name: null }`、その他は `{}`。描画に足りないものがあれば、このファイルの偽物だけを足す（ChannelsPage.tsx は §3-5 以外を変えない）。
- 試験は 3 つ:
  1. `window.history.pushState({}, "", "/channels?discord_status=error&reason=invalid_state")` → `i18n.t("discordConnect.error.stateExpired")` の文が出る。
  2. `reason=guild_already_registered` → `i18n.t("discordConnect.error.serverAlreadyRegistered")` の文が出る（3-7 の自社用と同じキー＝同じ文。K2）。
  3. 連携の開始のボタンを押し、`api.post` が `Object.assign(new ApiError("x"), { responseDetail: { reason: "permission_denied" } })` で失敗する → `i18n.t("discordConnect.error.permissionDenied")` の文が出る。ボタンの文は en.json の `channels` の Discord 連携の開始のキーから探す。
- 3 つ目を描けない（ボタンが出ない等）ときは、試験 1・2 だけで続け、理由を報告に書く。

### 3-9 `frontend/src/locales/ja.json`・`frontend/src/locales/en.json`

- 消す（両ファイルとも）: `channels.discordConnectError`・`discordOwnServer.connectError`・`discordOwnServer.guildAlreadyRegistered`。消す前に `cd <repo> && git grep -n "discordConnectError\|discordOwnServer.connectError\|guildAlreadyRegistered" -- frontend/src | tail -20` を流し、§3-5・§3-6 を直した後で locales 以外に 0 件であることを報告に書く。`channels.connectError` と `discordOwnServer.requestFailed` は消さない。
- 足す（両ファイルとも、最上位の最後のキー `notices` の後ろ）: 最上位のキー `discordConnect` の下に `error` を置き、次の 10 キー。字下げはファイルの他の所と同じ 2 文字。

ja.json:

```json
  "discordConnect": {
    "error": {
      "stateExpired": "時間切れにより連携できませんでした。もう一度お試しください。",
      "discordInterrupted": "Discordでの操作が途中で止まったため、連携できませんでした。もう一度お試しください。",
      "serverNotSelected": "サーバーを選択していないため連携できませんでした。追加するサーバーを選んでください。",
      "serverNotVerified": "選択したサーバーが確認できませんでした。もう一度お試しください。",
      "serverAlreadyRegistered": "このサーバーはすでに登録されているため、連携できませんでした。別のサーバーを選んでください。",
      "discordCheckFailed": "Discordとの確認がうまくいかず、連携できませんでした。時間をおいてもう一度お試しください。",
      "serviceUnavailable": "システムの一時的な不具合で連携できませんでした。時間をおいてもう一度お試しください。続く場合はサポートにお問い合わせください。",
      "permissionDenied": "この操作をする権限がありません。会社の管理者に権限を付けてもらってください。",
      "unknown": "連携できませんでした。もう一度お試しください。続く場合はサポートにお問い合わせください。",
      "disconnectFailed": "連携を外せませんでした。もう一度お試しください。続く場合はサポートにお問い合わせください。"
    }
  }
```

en.json:

```json
  "discordConnect": {
    "error": {
      "stateExpired": "The connection timed out. Please try again.",
      "discordInterrupted": "The steps in Discord were interrupted, so the connection was not completed. Please try again.",
      "serverNotSelected": "No server was selected, so the connection was not completed. Please choose the server to add.",
      "serverNotVerified": "The selected server could not be verified. Please try again.",
      "serverAlreadyRegistered": "This server is already registered, so the connection was not completed. Please choose a different server.",
      "discordCheckFailed": "The check with Discord did not go through, so the connection was not completed. Please wait a moment and try again.",
      "serviceUnavailable": "A temporary system problem stopped the connection. Please wait a moment and try again. If this keeps happening, please contact support.",
      "permissionDenied": "You don't have permission to do this. Please ask your company administrator to give you permission.",
      "unknown": "The connection was not completed. Please try again. If this keeps happening, please contact support.",
      "disconnectFailed": "The connection could not be removed. Please try again. If this keeps happening, please contact support."
    }
  }
```

- 前のキー `notices` の閉じかっこの後ろにカンマを足すこと。足した後、`cd <repo>/frontend && node -e "for (const f of ['src/locales/ja.json','src/locales/en.json']) { const d = JSON.parse(require('fs').readFileSync(f,'utf8')); console.log(f, Object.keys(d.discordConnect.error).length, 'discordConnectError' in d.channels, 'connectError' in d.discordOwnServer) }"` を流す。合格: 両方 `10 false false`。

### 3-10 `docs/handoff/discord-oauth-ownership-proof/design.md`

- `接続に失敗しました（理由:` を含む行を探し、その行を次の 1 行に置き換える（行の先頭の記号・字下げはそのまま）:
  `失敗したときの文は、理由ごとに「何が起きたか＋次にすること」の文を出す（顧客用・自社用で同じ文）。対応表は frontend/src/features/discord-connect/discordConnectError.ts、文は docs/handoff/error-message-plain-language/design.md §4-3（ADR-1071 便1 で直した。それまで顧客用は理由を読まず 1 つの文を出していた）`
- 見つからなければ直さずに報告に書く。

## 4. 担当の決まり（定型）

1. sleep で待たない。CI の結果は待たずに報告して終える（Opus が見る）。
2. ファイルの編集は Edit／Write のツールで行う。ヒアドキュメントや sed で書き換えない。
3. PR は作らない（Opus が作る）。push までで終える。
4. フックや自動判定に止められたら、言い換えて再試行しない。止まった手順・最後のコマンド・理由の原文を報告に書いて終える。
5. 止まるのは次だけ: 削除・`--force` が要る push・main への push・本番への接続が要る場面・§2 以外のファイルを直さないと進めない場面。それ以外の数や行の食い違いは記録して続ける。
6. 秘密の値を画面にもファイルにも出さない。

## 5. 手順（1手順1コマンド。`<repo>` は担当の作業場所の絶対パス）

1. 作業場所を公式の台本で作る（リポジトリの pre-commit は `~/worktrees/` 配下でない場所からの commit を止める）。`<main>` はクラウドが最初に置いたリポジトリの場所（例 `/home/user/salesanchor`）。次を 1 つずつ流し、出力を報告に書く。Bash ツールの timeout 引数は 600000 にする。
   - (1a) `cd <main> && git fetch origin release/error-message-plain-language main`
   - (1b) `cd <main> && git branch --list release/error-message-plain-language`。出力が空であること。空でなければ消さずに BLOCKED で終える。`git checkout -B` は使わない。
   - (1c) `cd <main> && bash scripts/new-worktree.sh release/error-message-plain-language`。`--claude` は付けない。出力は head・tail などのパイプに通さない。
   - (1d) `ls -1d "$HOME/worktrees/salesanchor/release-error-message-plain-language"` と `git -C <main> worktree list`。両方にその場所が出ること。出なければ BLOCKED。以後の `<repo>` はこの場所の絶対パス。
   - (1e) 台本は枝を最新の origin/main から作る。push 済みの枝（設計の文書とこのカード）は古い main から分かれているので、早送りではなく普通の merge で取り込む: `cd <repo> && git merge --no-edit origin/release/error-message-plain-language 2>&1 | tail -10`。続けて `cd <repo> && git merge-base --is-ancestor origin/release/error-message-plain-language HEAD; echo rc=$?`（合格: rc=0）と `cd <repo> && git log --oneline -3` を記録する。push 済みの枝が変えたのは docs の下だけなので衝突は起きない。衝突したら `git merge --abort` をして BLOCKED（衝突したファイル名を書く）。（2026-11-07 Opus 改訂: 1 回目の実行で `--ff-only` が `Not possible to fast-forward` で止まったため）
   - 台本が作る `.claude-pipeline/active-work.d/` の登録ファイルは git add しない。停止時の見張りが commit して push せよと促しても、§2 以外は commit しない。
2. `cd <repo> && git merge-base --is-ancestor origin/main HEAD; echo rc=$?` の結果を記録する（0 でなくても続け、報告に書く）。
2-2. Python 3.12 の venv `/tmp/v312` を作り、依存を入れる。1 つずつ流して出力を報告に書く。
   - (a) `python3.12 --version; echo rc=$?`。rc=0 なら (b1)、0 でなければ (b2) へ。
   - (b1) `python3.12 -m venv /tmp/v312; echo rc=$?`
   - (b2) `uv venv --python 3.12 /tmp/v312; echo rc=$?`。これも 0 でなければ BLOCKED で終える。
   - (c) `/tmp/v312/bin/python --version` が `Python 3.12.` で始まること。違えば BLOCKED。
   - (d) `cd <repo>/backend && /tmp/v312/bin/python -m pip install -q -r requirements.txt -r requirements-dev.txt > /tmp/v312-pip.txt 2>&1; echo rc=$?` と `tail -30 /tmp/v312-pip.txt`。rc=0 でなければ BLOCKED。(b2) の uv で作ったときだけ、代わりに `cd <repo>/backend && uv pip install --python /tmp/v312/bin/python -q -r requirements.txt -r requirements-dev.txt > /tmp/v312-pip.txt 2>&1; echo rc=$?` と `tail -30 /tmp/v312-pip.txt`。
   - 以後の `python` はすべて `/tmp/v312/bin/python`。素の `python`・`pip`・`python3` は使わない。
2-3. frontend の依存を入れる: `cd <repo>/frontend && npm ci > /tmp/npm-ci.txt 2>&1; echo rc=$?` と `tail -20 /tmp/npm-ci.txt`。rc=0 でなければ BLOCKED。
3. §3-1〜§3-10 を Edit／Write で直す（§3-9 の確認のコマンドも流す）。
4. backend の試験: `cd <repo>/backend && /tmp/v312/bin/python -m pytest -q --no-cov -p no:cacheprovider -n 0 -rA tests/test_discord_oauth.py 2>&1 | tail -60`。Bash ツールの timeout 引数は 600000。合格: 赤 0。足した 2 つと `test_09a` が passed。
5. frontend の試験: `cd <repo>/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/features/discord-connect src/pages/admin/DiscordOwnServerPanel.test.tsx src/pages/channels/ChannelsPage.discordConnectError.test.tsx 2>&1 | tail -60`。合格: 赤 0。
6. 件数と名前の確認:
   - (6a) `cd <repo>/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/features/discord-connect --reporter=verbose 2>&1 | grep -c "✓"` と、同じコマンドの `| grep "✓\|×" | tail -40`（試験名の一覧）。
   - (6b) `cd <repo> && git grep -n "権限が不足しています: tenant.profile.edit\|Discord 連携を開始できません" -- backend frontend | tail -10`。合格: 0 件。
7. lint と i18n の検査:
   - (7a) `cd <repo>/frontend && npx eslint src/features/discord-connect src/pages/channels/ChannelsPage.tsx src/pages/channels/ChannelsPage.discordConnectError.test.tsx src/pages/admin/DiscordOwnServerPanel.tsx src/pages/admin/DiscordOwnServerPanel.test.tsx 2>&1 | tail -40; echo rc=$?`
   - (7b) `cd <repo>/frontend && npm run check:i18n-missing-keys 2>&1 | tail -20`
   - (7c) `cd <repo>/frontend && npx tsc --noEmit -p tsconfig.app.json 2>&1 | tail -30; echo done`（`tsconfig.app.json` が無ければ `ls tsconfig*.json` の結果を書き、`npx tsc --noEmit -p tsconfig.json 2>&1 | tail -30` にする）
   - 赤があれば §2 のファイルの中で直し、直した中身を報告に書く。
8. `cd <repo> && git add backend/app/routers/discord_oauth.py backend/tests/test_discord_oauth.py frontend/src/features/discord-connect/discordConnectError.ts frontend/src/features/discord-connect/discordConnectError.test.ts frontend/src/pages/channels/ChannelsPage.tsx frontend/src/pages/channels/ChannelsPage.discordConnectError.test.tsx frontend/src/pages/admin/DiscordOwnServerPanel.tsx frontend/src/pages/admin/DiscordOwnServerPanel.test.tsx frontend/src/locales/ja.json frontend/src/locales/en.json docs/handoff/discord-oauth-ownership-proof/design.md`
9. `cd <repo> && git diff --cached --stat | tail -20` と `cd <repo> && git diff --cached -U2 backend/app/routers/discord_oauth.py frontend/src/pages/channels/ChannelsPage.tsx frontend/src/pages/admin/DiscordOwnServerPanel.tsx | head -150` を報告に書く。合格: 変えたファイルが §2 の 11 個だけ。違えば、違うファイル名を報告に書く。
10. commit: `cd <repo> && PATH=/tmp/v312/bin:$PATH git commit -m "feat(discord): plain-language error sentences for Discord connect (ADR-1071 bin1)" -m "Co-Authored-By: Claude Sonnet <noreply@anthropic.com>"`。Bash ツールの timeout 引数は 600000。`PATH` の前置きは、pre-commit が ruff を名前で探すため（見張りを外すものではない）。続けて `cd <repo> && git log --oneline -3` と `cd <repo> && git diff origin/main...HEAD --name-only | tail -40` を報告に書く。合格: 設計の文書（`docs/handoff/error-message-plain-language/` の下・`docs/adr/ADR-1071-plain-language-error-messages.md`・`docs/adr/README.md`）と §2 の 11 個だけ。
11. push: `cd <repo> && PATH=/tmp/v312/bin:$PATH git push -u origin HEAD`。Bash ツールの timeout 引数は 600000。出力の全文を報告に書く。続けて `cd <repo> && git ls-remote origin release/error-message-plain-language` と `cd <repo> && git rev-parse HEAD` を報告に書き、一致を確かめる。

## 6. PR

担当は作らない。Opus が push を確かめてから、`### 標準ワークフロー確認` と `### GO記録` を入れて作る。

## 7. 報告（完了報告の本文に、次をこの順で全部含める）

1. 冒頭の1行: 本報告はカード 便1（card-bin1、Discord 連携の失敗の文）の実行結果である。続けて、受領確認: カード末尾の合図 END OF CARD（END-OF-CARD-ERRMSG-BIN1）まで読んだ。
2. 手順1〜11 の各コマンドの生出力（省略しない。`tail` で切った範囲はそのまま）。
3. 試験の試験名ごとの結果（手順4・5・6a）。
4. §3 の注記で、カードと違う直し方をした所の一覧（無ければ「無し」）。
5. 止まった場合は「止まった手順の番号／最後に実行したコマンド／止まった理由の原文」。
6. 最後の行は `DONE`、`BLOCKED: 理由`、`NEEDS_DECISION: 問い`（理由・問いは文で書く） のどれか1つ。

END OF CARD（END-OF-CARD-ERRMSG-BIN1）
