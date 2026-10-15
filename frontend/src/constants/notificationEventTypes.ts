/**
 * 通知の種類の「表示名キー」対応表。
 * 種類の一覧そのものは SSOT ではない（正は backend の NotificationEventType）。
 * 画面は GET /notification-event-types が返すコードを並べ、本表で表示名を引く。
 * 表に無いコードが来たらコードをそのまま表示する（黙って消さない）。
 */
export const NOTIFICATION_EVENT_LABEL_KEYS: Record<string, string> = {
  lead_assigned: "notifications.eventType.leadAssigned",
  meta_message_received: "notifications.eventType.metaMessageReceived",
  tcg_distribution_error: "notifications.eventType.tcgDistributionError",
};
