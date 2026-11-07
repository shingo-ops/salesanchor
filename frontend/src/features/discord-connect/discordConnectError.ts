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
