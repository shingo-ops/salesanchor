/** リアクション一覧をハート（受信箱から押せる唯一の絵文字）とそれ以外に分ける（純関数）。 */
import type { MessageReaction } from "../../lib/messages";
import { HEART_REACTION_EMOJI } from "./reactionEmojiPresets";

export interface SplitReactions {
  /** ❤️（Unicode）のグループ。無ければ null */
  heart: MessageReaction | null;
  /** ❤️ 以外（表示専用）。順序は入力どおり */
  others: MessageReaction[];
}

export function isHeartReaction(reaction: MessageReaction): boolean {
  return reaction.emoji_name === HEART_REACTION_EMOJI && !reaction.emoji_id;
}

export function splitReactions(reactions: MessageReaction[] | undefined): SplitReactions {
  const list = reactions ?? [];
  return {
    heart: list.find(isHeartReaction) ?? null,
    others: list.filter((r) => !isHeartReaction(r)),
  };
}

/** リアクションした人の表示名一覧（表示名なしは user_id）。カンマ区切り。 */
export function reactorNames(reaction: MessageReaction): string {
  return reaction.reactors.map((r) => r.display_name ?? r.user_id).join(", ");
}
