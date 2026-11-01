/**
 * ChatBubble — チャットの吹き出し金型（ADR-144・ADR-067）
 *
 * 利用者は右寄せ、AI は左寄せ。色・角丸は受信箱の吹き出しと同じトークン。
 * 言葉は持たない。エラーの文言などは呼ぶ側が children で渡す（ADR-027）。
 */

import type { ReactNode } from "react";
import { Spinner } from "./loading";
import "./ChatBubble.css";

export interface ChatBubbleProps {
  side: "user" | "assistant";
  children: ReactNode;
  status?: "sending" | "error";
  className?: string;
}

export function ChatBubble({ side, children, status, className }: ChatBubbleProps) {
  const classes = [
    "comp-chat-bubble",
    `comp-chat-bubble--${side}`,
    status ? `comp-chat-bubble--${status}` : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <div className={classes}>
      <div className="comp-chat-bubble__body">{children}</div>
      {status === "sending" && <Spinner size="sm" tone="inherit" decorative />}
    </div>
  );
}
