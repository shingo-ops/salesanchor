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
