/* eslint-disable local/no-japanese-literal -- テスト: PO 指定の日本語文言・テスト名を検証する（ADR-159） */
import { describe, expect, it } from "vitest";
import {
  ACCOUNT_SETTINGS_PATH,
  DISCORD_CONFIG_PATH,
  DISCORD_SEND_ERROR_REASONS,
  getDiscordSendErrorGuide,
  isDiscordSendErrorReason,
} from "./discordSendError";
import ja from "../../locales/ja.json";
import en from "../../locales/en.json";

type Dict = { [key: string]: string | Dict };

function lookup(dict: Dict, dotted: string): string | undefined {
  const value = dotted.split(".").reduce<string | Dict | undefined>(
    (acc, key) => (acc && typeof acc === "object" ? acc[key] : undefined),
    dict,
  );
  return typeof value === "string" ? value : undefined;
}

describe("getDiscordSendErrorGuide", () => {
  it("STAFF_EN_NAME_REQUIRED は アカウント設定へ遷移する CTA を返す", () => {
    const guide = getDiscordSendErrorGuide("STAFF_EN_NAME_REQUIRED", false);
    expect(guide?.messageKey).toBe("inbox.sendError.discordEnNameRequired");
    expect(guide?.cta).toEqual({
      kind: "navigate",
      labelKey: "inbox.sendError.ctaOpenAccountSettings",
      to: ACCOUNT_SETTINGS_PATH,
    });
    expect(ACCOUNT_SETTINGS_PATH).toBe("/account/settings");
  });

  it("STAFF_EN_NAME_INVALID は アカウント設定へ遷移する CTA を返す", () => {
    const guide = getDiscordSendErrorGuide("STAFF_EN_NAME_INVALID", true);
    expect(guide?.messageKey).toBe("inbox.sendError.discordEnNameInvalid");
    expect(guide?.cta).toMatchObject({ kind: "navigate", to: ACCOUNT_SETTINGS_PATH });
  });

  it("DISCORD_SEND_FAILED は 再送 CTA を返す", () => {
    const guide = getDiscordSendErrorGuide("DISCORD_SEND_FAILED", false);
    expect(guide?.messageKey).toBe("inbox.sendError.discordSendFailed");
    expect(guide?.cta).toEqual({ kind: "retry", labelKey: "inbox.sendError.ctaRetry" });
  });

  it("DISCORD_WEBHOOK_PERMISSION は 管理者なら Discord 設定へ遷移する CTA を返す", () => {
    const guide = getDiscordSendErrorGuide("DISCORD_WEBHOOK_PERMISSION", true);
    expect(guide?.messageKey).toBe("inbox.sendError.discordWebhookPermissionAdmin");
    expect(guide?.cta).toEqual({
      kind: "navigate",
      labelKey: "inbox.sendError.ctaOpenDiscordConfig",
      to: DISCORD_CONFIG_PATH,
    });
    expect(DISCORD_CONFIG_PATH).toBe("/admin/discord-config");
  });

  it("DISCORD_WEBHOOK_PERMISSION は 管理者以外なら CTA 無しで管理者への連絡を案内する", () => {
    const guide = getDiscordSendErrorGuide("DISCORD_WEBHOOK_PERMISSION", false);
    expect(guide?.messageKey).toBe("inbox.sendError.discordWebhookPermissionStaff");
    expect(guide?.cta).toBeNull();
  });

  it("既存の送信エラー reason と未知の値は null（従来表示にフォールバック）", () => {
    for (const reason of ["generic", "window_closed", "rate_limited", "", "UNKNOWN"]) {
      expect(getDiscordSendErrorGuide(reason, true)).toBeNull();
      expect(isDiscordSendErrorReason(reason)).toBe(false);
    }
  });

  it("全コードが i18n ja / en に文言キーと CTA ラベルを持つ（空でない）", () => {
    for (const reason of DISCORD_SEND_ERROR_REASONS) {
      for (const admin of [true, false]) {
        const guide = getDiscordSendErrorGuide(reason, admin);
        expect(guide).not.toBeNull();
        const keys = [guide!.messageKey, ...(guide!.cta ? [guide!.cta.labelKey] : [])];
        for (const key of keys) {
          expect(lookup(ja as Dict, key), `ja:${key}`).toBeTruthy();
          expect(lookup(en as Dict, key), `en:${key}`).toBeTruthy();
        }
      }
    }
  });

  it("PO 指定の日本語文言が一致する", () => {
    const j = ja as Dict;
    expect(lookup(j, "inbox.sendError.discordEnNameRequired")).toBe("Discordで返信するには、英語の名前の登録が必要です。");
    expect(lookup(j, "inbox.sendError.discordEnNameInvalid")).toBe("英語の名前に使えない言葉（discord など）が含まれています。");
    expect(lookup(j, "inbox.sendError.discordSendFailed")).toBe("送信できませんでした。入力した文は残っています。");
    expect(lookup(j, "inbox.sendError.discordWebhookPermissionAdmin")).toBe("Discordの設定が足りないため送れません。");
    expect(lookup(j, "inbox.sendError.discordWebhookPermissionStaff")).toBe("Discordの設定が足りないため送れません。管理者に連絡してください。");
    expect(lookup(j, "inbox.sendError.ctaOpenAccountSettings")).toBe("アカウント設定を開く");
    expect(lookup(j, "inbox.sendError.ctaRetry")).toBe("もう一度送る");
    expect(lookup(j, "inbox.sendError.ctaOpenDiscordConfig")).toBe("Discord設定を開く");
  });
});
