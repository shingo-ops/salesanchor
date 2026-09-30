/** Discord リアクション API のパス組み立て（純関数）。messageId は meta_messages.id（内部ID）。 */

export function buildReactionCreatePath(leadId: number, messageId: number): string {
  return `/leads/${leadId}/messages/${messageId}/reactions`;
}

/** 取消: emoji_name をパス、emoji_id（カスタム絵文字のみ）をクエリで渡す（backend の DELETE 仕様） */
export function buildReactionDeletePath(
  leadId: number,
  messageId: number,
  emojiName: string,
  emojiId?: string,
): string {
  const base = `${buildReactionCreatePath(leadId, messageId)}/${encodeURIComponent(emojiName)}`;
  return emojiId ? `${base}?emoji_id=${encodeURIComponent(emojiId)}` : base;
}
