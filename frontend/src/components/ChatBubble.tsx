/**
 * ChatBubble — 会話の吹き出し金型（本文と時刻の入れ物）
 *
 * direction : inbound（相手から）/ outbound（自分から）。時刻の寄せ方もこれで決まる
 * failed    : 送れなかった吹き出し（赤の枠）。direction より優先して色を決める
 * time      : 吹き出しの下端に出す時刻の行の中身
 * children  : 本文・画像・訳など吹き出しの中身
 * そのほかの div の属性（role・title・長押しの手当て）はそのまま外側の div に付ける。
 *
 * 業務の意味（どの経路のメッセージか等）はこの金型に埋め込まない。
 */
import type { HTMLAttributes, ReactNode } from 'react';
import './ChatBubble.css';

export type ChatBubbleDirection = 'inbound' | 'outbound';

export interface ChatBubbleProps extends Omit<HTMLAttributes<HTMLDivElement>, 'className' | 'children'> {
  direction: ChatBubbleDirection;
  failed?: boolean;
  time: ReactNode;
  children: ReactNode;
}

export function ChatBubble({ direction, failed = false, time, children, ...rest }: ChatBubbleProps) {
  const outbound = direction === 'outbound';
  return (
    <div {...rest} className={`msg-bubble${failed ? ' failed' : outbound ? ' outbound' : ' inbound'}`}>
      {children}
      <div className={`msg-time${outbound ? '' : ' inbound'}`}>{time}</div>
    </div>
  );
}
