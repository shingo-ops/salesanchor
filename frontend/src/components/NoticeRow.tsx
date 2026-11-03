/**
 * NoticeRow — 知らせ 1 件の押せる行（鈴の一覧用）。
 * 未読は太字＋左に丸。色・余白・角はトークンのみ（NoticeBell.css）。
 * 文言は呼び出し側が t() で作って渡す（この部品は文字を持たない）。
 */
import "./NoticeBell.css";

export interface NoticeRowProps {
  /** 1 行目（「{{actor}} さんが #{{channel}} に書き込みました」の完成形） */
  title: string;
  /** 2 行目（相対時刻） */
  meta: string;
  unread: boolean;
  onClick: () => void;
}

export function NoticeRow({ title, meta, unread, onClick }: NoticeRowProps) {
  return (
    <button
      type="button"
      className={`notice-row${unread ? " notice-row--unread" : ""}`}
      onClick={onClick}
    >
      <span className="notice-row-dot" aria-hidden="true" />
      <span className="notice-row-body">
        <span className="notice-row-title">{title}</span>
        <span className="notice-row-meta">{meta}</span>
      </span>
    </button>
  );
}
