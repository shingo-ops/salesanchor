/**
 * ChatBubble — 会話の吹き出し金型（ADR-144・ADR-067）
 *
 * layout    : thread（受信箱の会話。並べ方はページの行が持つ）/ panel（秘書のチャット。左右に自分で寄る）
 * direction : inbound（相手・AI から）/ outbound（自分から）。時刻の寄せ方もこれで決まる
 * failed    : 送れなかった吹き出し。thread は赤の地と枠、panel は文字だけ赤
 * pending   : 返事を待っている間の回る印を出す
 * wide      : 吹き出しを横いっぱいにする（下書きの票などを入れるとき）
 * tail      : 続きの最初の吹き出し。スマホで尾を付ける（PC では何も変わらない）
 * inlineTime: 時刻を本文の最後の行の右下に入れる（スマホのみ。PC は今まで通り下の行）
 * time      : 吹き出しの下端に出す時刻の行の中身。渡さなければ行を出さない
 * children  : 本文・画像・訳など吹き出しの中身
 * そのほかの div の属性（role・title・長押しの手当て）はそのまま外側の div に付ける。
 *
 * 言葉は持たない。文言は呼ぶ側が children / time で渡す（ADR-027）。
 * 業務の意味（どの経路のメッセージか等）はこの金型に埋め込まない。
 */
import type { HTMLAttributes, ReactNode } from 'react';
import { Spinner } from './loading';
import './ChatBubble.css';

export type ChatBubbleDirection = 'inbound' | 'outbound';
export type ChatBubbleLayout = 'thread' | 'panel';

export interface ChatBubbleProps extends Omit<HTMLAttributes<HTMLDivElement>, 'className' | 'children'> {
  direction: ChatBubbleDirection;
  layout?: ChatBubbleLayout;
  failed?: boolean;
  pending?: boolean;
  wide?: boolean;
  tail?: boolean;
  inlineTime?: boolean;
  time?: ReactNode;
  children: ReactNode;
}

export function ChatBubble({
  direction,
  layout = 'thread',
  failed = false,
  pending = false,
  wide = false,
  tail = false,
  inlineTime = false,
  time,
  children,
  ...rest
}: ChatBubbleProps) {
  const outbound = direction === 'outbound';
  const panel = layout === 'panel';
  const classes = [
    'comp-chat-bubble',
    panel ? 'comp-chat-bubble--panel' : '',
    // thread の failed は色を丸ごと置き換える（送信・受信の色を付けない）。panel の failed は色を残して文字だけ赤くする
    panel || !failed ? `comp-chat-bubble--${direction}` : 'comp-chat-bubble--failed',
    panel && failed ? 'comp-chat-bubble--error' : '',
    wide ? 'comp-chat-bubble--wide' : '',
    tail && !panel && !failed ? 'comp-chat-bubble--tail' : '',
    inlineTime && !panel && !failed && time !== undefined ? 'comp-chat-bubble--inline-time' : '',
  ]
    .filter(Boolean)
    .join(' ');
  return (
    <div {...rest} className={classes}>
      {panel ? <div className="comp-chat-bubble__body">{children}</div> : children}
      {inlineTime && !panel && !failed && time !== undefined && (
        <span className="comp-chat-bubble__time-spacer" aria-hidden="true">
          {time}
        </span>
      )}
      {pending && <Spinner size="sm" tone="inherit" decorative />}
      {time !== undefined && (
        <div className={`comp-chat-bubble__time${outbound ? '' : ' comp-chat-bubble__time--inbound'}`}>{time}</div>
      )}
    </div>
  );
}
