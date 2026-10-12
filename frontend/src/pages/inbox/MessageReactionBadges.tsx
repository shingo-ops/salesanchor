/**
 * MessageReactionBadges — 吹き出し下端のリアクション表示（受信箱・Discord）
 *
 * - ❤️ グループがあれば IconToggleButton badge（常に赤の塗りハート＋件数・is_mine は枠で区別）。クリックで送信/取消
 * - ❤️ 以外のリアクションは表示専用バッジ（受信箱からは付けられない）
 * - リアクションした人は Tooltip 金型で表示
 */
import { useTranslation } from "react-i18next";
import { Tooltip } from "../../components/Tooltip";
import { IconToggleButton } from "../../components/IconToggleButton";
import { INBOX_ACTION_ICONS } from "../../constants/icons";
import { ICON } from "../../constants/iconSizes";
import type { MessageReaction } from "../../lib/messages";
import { reactorNames, splitReactions } from "./reactionHeart";

interface Props {
  /** meta_messages.id（内部ID） */
  messageId: number;
  reactions: MessageReaction[] | undefined;
  onToggleHeart: (messageId: number, isMine: boolean) => void;
}

export function MessageReactionBadges({ messageId, reactions, onToggleHeart }: Props) {
  const { t } = useTranslation();
  const { heart, others } = splitReactions(reactions);
  if (!heart && others.length === 0) return null;

  const tooltipFor = (reaction: MessageReaction): string => {
    const names = reactorNames(reaction);
    return names ? `${t("inbox.reactedBy")}: ${names}` : t("inbox.reactedBy");
  };

  return (
    <div className="msg-reactions" role="group" aria-label={t("inbox.reactedBy")}>
      {heart && (
        <Tooltip content={tooltipFor(heart)}>
          <IconToggleButton
            variant="badge"
            pressed={heart.is_mine}
            iconOff={INBOX_ACTION_ICONS.heart}
            iconOn={INBOX_ACTION_ICONS.heartFilled}
            aria-label={heart.is_mine ? t("inbox.removeReaction") : t("inbox.addReaction")}
            count={heart.count}
            onClick={() => onToggleHeart(messageId, heart.is_mine)}
          />
        </Tooltip>
      )}
      {others.map((reaction) => (
        <Tooltip key={`${reaction.emoji_name}:${reaction.emoji_id ?? ""}`} content={tooltipFor(reaction)}>
          <span className="msg-reaction-badge">
            {reaction.emoji_id ? (
              <img
                className="msg-reaction-emoji-img"
                src={`https://cdn.discordapp.com/emojis/${reaction.emoji_id}.${reaction.emoji_animated ? "gif" : "png"}?size=32`}
                alt={reaction.emoji_name}
                width={ICON.md}
                height={ICON.md}
              />
            ) : (
              <span>{reaction.emoji_name}</span>
            )}
            <span className="msg-reaction-count">{reaction.count}</span>
          </span>
        </Tooltip>
      ))}
    </div>
  );
}
