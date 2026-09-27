/**
 * EmojiPickerWrapper — プリセット絵文字グリッド
 *
 * CDN 依存の emoji-picker-react を廃止し、Unicode 絵文字を直接ボタンとして並べる。
 * 画像・CDN 不要のため本番環境での読み込み失敗が発生しない。
 */

import { useTranslation } from "react-i18next";
import { REACTION_EMOJI_PRESETS } from "./reactionEmojiPresets";

// ---------------------------------------------------------------------------
// 型定義
// ---------------------------------------------------------------------------

export interface CustomEmoji {
  id: string;
  names: string[];
  imgUrl: string;
  /** カテゴリ名（サーバー絵文字タブのグループ） */
  category?: string;
}

export interface SelectedEmoji {
  name: string;
  id?: string;
  unified?: string;
}

export interface EmojiPickerWrapperProps {
  onSelect: (emoji: SelectedEmoji) => void;
  customEmojis?: CustomEmoji[];
}

// ---------------------------------------------------------------------------
// コンポーネント
// ---------------------------------------------------------------------------

export function EmojiPickerWrapper({ onSelect, customEmojis }: EmojiPickerWrapperProps) {
  const { t } = useTranslation();

  return (
    <div
      className="emoji-preset-grid"
      role="group"
      aria-label={t("inbox.emojiPicker")}
    >
      {REACTION_EMOJI_PRESETS.map((emoji) => (
        <button
          key={emoji}
          type="button"
          className="emoji-preset-btn"
          aria-label={emoji}
          onClick={() => onSelect({ name: emoji })}
        >
          {emoji}
        </button>
      ))}
      {customEmojis && customEmojis.length > 0 && (
        <>
          <div className="emoji-preset-divider" role="separator" />
          {customEmojis.map((ce) => (
            <button
              key={ce.id}
              type="button"
              className="emoji-preset-btn"
              aria-label={ce.names[0] ?? ce.id}
              title={ce.names[0] ?? ce.id}
              onClick={() => onSelect({ name: ce.names[0] ?? ce.id, id: ce.id })}
            >
              <img
                src={ce.imgUrl}
                alt={ce.names[0] ?? ce.id}
                width={20}
                height={20}
                style={{ verticalAlign: "middle" }}
              />
            </button>
          ))}
        </>
      )}
    </div>
  );
}
