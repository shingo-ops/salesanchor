/**
 * EmojiPickerWrapper — emoji-picker-react を遅延ロードするラッパー
 *
 * React.lazy で遅延ロードすることでバンドルサイズを抑制する。
 * 金型 Popover が完成するまでは EmojiPickerWrapper 単体で動作する。
 */

import { Suspense, lazy } from "react";
import { useTranslation } from "react-i18next";
import type { EmojiClickData } from "emoji-picker-react";

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
// 遅延ロード
// ---------------------------------------------------------------------------

const EmojiPicker = lazy(() => import("emoji-picker-react"));

// ---------------------------------------------------------------------------
// コンポーネント
// ---------------------------------------------------------------------------

export function EmojiPickerWrapper({ onSelect, customEmojis }: EmojiPickerWrapperProps) {
  const { t } = useTranslation();

  const handleEmojiClick = (emojiData: EmojiClickData) => {
    onSelect({
      name: emojiData.emoji,
      unified: emojiData.unified,
    });
  };

  return (
    <Suspense
      fallback={
        <div
          className="emoji-picker-loading"
          role="status"
          aria-label={t("common.loading")}
          style={{
            /* ui-allow: emoji-picker-react の標準表示サイズに合わせた固定幅・高さ。デザイントークンに相当値なし (#discord-reaction) */
            width: "var(--emoji-picker-width, 320px)",
            height: "var(--emoji-picker-height, 400px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "var(--text-secondary)",
            fontSize: "var(--font-sm)",
            background: "var(--bg-surface)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-md)",
          }}
        >
          {t("common.loading")}
        </div>
      }
    >
      <EmojiPicker
        onEmojiClick={handleEmojiClick}
        customEmojis={(customEmojis as unknown as never[]) ?? []}
        searchPlaceholder={t("inbox.emojiPicker")}
        categories={
          customEmojis && customEmojis.length > 0
            ? [
                { category: "custom" as never, name: t("inbox.customEmojis") },
                { category: "smileys_people" as never, name: t("inbox.emojiPicker") },
              ]
            : undefined
        }
      />
    </Suspense>
  );
}
