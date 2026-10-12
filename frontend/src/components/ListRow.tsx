/**
 * ListRow — 一覧の1行金型（ADR-144 §4 / card-mobile-molds.md §1）
 *
 * スマホで一覧を見せるときの1行。行全体が押せる場所になり、
 * 左に丸い画像、右上に補助情報（日時など）、右下に印（未読の数など）を置く。
 * 受信箱の会話一覧で使い、将来は在庫表・受注管理の一覧でも使える。
 *
 * この部品が決めないもの（渡す側が決める）: 文字の内容、画像の中身、押したときの処理。
 * この部品が決めるもの（渡す側が上書きしない）: 行の高さ、余白、画像の大きさと丸み、文字の強弱、押せる範囲。
 *
 * onClick を渡すと <button type="button"> になり行全体が押せる。渡さないときは <div>。
 */

import type { ReactNode } from "react";
import "./ListRow.css";

interface ListRowProps {
  /** 行の左に出す丸い画像。省略すると画像の場所を空けない */
  avatar?: ReactNode;
  /** 1行目の主役（会話相手の名前・商品名など）。太字で出る */
  title: ReactNode;
  /** 1行目の右端に出る補助（日時など）。title より小さい文字で出る */
  titleAside?: ReactNode;
  /** 2行目の説明（メッセージの冒頭・型番など）。1行で切る */
  subtitle?: ReactNode;
  /** 2行目の右端に出る印（未読の数など） */
  subtitleAside?: ReactNode;
  /** 2行目の文字の前に出す小さな印（既読・音声などの種類） */
  subtitleIcon?: ReactNode;
  /** 押したときの行き先。渡すと行全体が押せる場所になる */
  onClick?: () => void;
  /** 今開いている行であることを示す（PCの3列表示で使う） */
  selected?: boolean;
}

export function ListRow({
  avatar,
  title,
  titleAside,
  subtitle,
  subtitleAside,
  subtitleIcon,
  onClick,
  selected = false,
}: ListRowProps) {
  const classes = [
    "comp-list-row",
    selected ? "comp-list-row--selected" : "",
  ].filter(Boolean).join(" ");

  const hasSubtitleRow = Boolean(subtitle || subtitleAside || subtitleIcon);

  const content = (
    <>
      {avatar && <div className="comp-list-row__avatar">{avatar}</div>}
      <div className="comp-list-row__body">
        <div className="comp-list-row__title-row">
          <span className="comp-list-row__title">{title}</span>
          {titleAside && (
            <span className="comp-list-row__title-aside">{titleAside}</span>
          )}
        </div>
        {hasSubtitleRow && (
          <div className="comp-list-row__subtitle-row">
            {subtitleIcon && (
              <span className="comp-list-row__subtitle-icon">{subtitleIcon}</span>
            )}
            {subtitle && (
              <span className="comp-list-row__subtitle">{subtitle}</span>
            )}
            {subtitleAside && (
              <span className="comp-list-row__subtitle-aside">{subtitleAside}</span>
            )}
          </div>
        )}
      </div>
    </>
  );

  if (onClick) {
    return (
      <button type="button" className={classes} onClick={onClick}>
        {content}
      </button>
    );
  }

  return <div className={classes}>{content}</div>;
}
