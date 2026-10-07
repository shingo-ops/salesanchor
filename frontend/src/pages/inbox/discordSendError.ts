/**
 * Discord 担当者名義送信（ADR-159 便B）のエラーコード → 文言キーと行動ボタン（CTA）の対応表。
 *
 * バックエンド（leads.py の DISCORD_ERR_*）が detail.reason に入れる安定コードを受け取る。
 * 文言は i18n（inbox.sendError.*）。画面側はこの表を見て表示するだけにする。
 */

export const DISCORD_SEND_ERROR_REASONS = [
  "STAFF_EN_NAME_REQUIRED",
  "STAFF_EN_NAME_INVALID",
  "DISCORD_SEND_FAILED",
  "DISCORD_WEBHOOK_PERMISSION",
] as const;

export type DiscordSendErrorReason = (typeof DISCORD_SEND_ERROR_REASONS)[number];

/** CTA の動作: 遷移（navigate）または再送（retry） */
export type DiscordSendCta =
  | { kind: "navigate"; labelKey: string; to: string }
  | { kind: "retry"; labelKey: string };

export interface DiscordSendErrorGuide {
  messageKey: string;
  /** 管理者以外は押せる行動が無い場合は null（文言で管理者への連絡を案内する） */
  cta: DiscordSendCta | null;
}

export const ACCOUNT_SETTINGS_PATH = "/account/settings";
export const DISCORD_CONFIG_PATH = "/admin/discord-config";
/** Discord 設定ページを編集できる権限（DiscordConfigPage.tsx と同一） */
export const DISCORD_CONFIG_PERMISSION = "tenant.profile.edit";

export function isDiscordSendErrorReason(reason: string): reason is DiscordSendErrorReason {
  return (DISCORD_SEND_ERROR_REASONS as readonly string[]).includes(reason);
}

export function getDiscordSendErrorGuide(
  reason: string,
  canManageDiscord: boolean,
): DiscordSendErrorGuide | null {
  switch (reason) {
    case "STAFF_EN_NAME_REQUIRED":
      return {
        messageKey: "inbox.sendError.discordEnNameRequired",
        cta: { kind: "navigate", labelKey: "inbox.sendError.ctaOpenAccountSettings", to: ACCOUNT_SETTINGS_PATH },
      };
    case "STAFF_EN_NAME_INVALID":
      return {
        messageKey: "inbox.sendError.discordEnNameInvalid",
        cta: { kind: "navigate", labelKey: "inbox.sendError.ctaOpenAccountSettings", to: ACCOUNT_SETTINGS_PATH },
      };
    case "DISCORD_SEND_FAILED":
      return {
        messageKey: "inbox.sendError.discordSendFailed",
        cta: { kind: "retry", labelKey: "inbox.sendError.ctaRetry" },
      };
    case "DISCORD_WEBHOOK_PERMISSION":
      return canManageDiscord
        ? {
            messageKey: "inbox.sendError.discordWebhookPermissionAdmin",
            cta: { kind: "navigate", labelKey: "inbox.sendError.ctaOpenDiscordConfig", to: DISCORD_CONFIG_PATH },
          }
        : { messageKey: "inbox.sendError.discordWebhookPermissionStaff", cta: null };
    default:
      return null;
  }
}
