/**
 * ChatComposer — 会話の入力欄の行の金型（ピル＋送信の丸）
 *
 * leading  : ピルの左に置く物（送信者のアバター等）。任意
 * input    : ピルの中の入力欄（TextareaControl 等）と、隠しのファイル入力など
 * attach   : ピルの中の右端のアイコンボタン。任意
 * trailing : ピルと送信の丸の間に置く物（英訳ボタン等）。任意
 * send     : 送信の丸。label は画面には出さず読み上げ用（sr-only）に入る
 *
 * 業務の意味（どこへ送るか等）はこの金型に埋め込まない。
 */
import type { ReactNode } from 'react';
import type { Icon } from '../constants/icons';
import { ICON } from '../constants/iconSizes';
import './ChatComposer.css';

export interface ChatComposerAttach {
  icon: Icon;
  /** aria-label と title の両方に使う */
  label: string;
  onClick: () => void;
  disabled?: boolean;
}

export interface ChatComposerSend {
  icon: Icon;
  /** 読み上げ用の名前（sr-only） */
  label: string;
  title: string;
  onClick: () => void;
  disabled?: boolean;
}

export interface ChatComposerProps {
  leading?: ReactNode;
  input: ReactNode;
  attach?: ChatComposerAttach;
  trailing?: ReactNode;
  send: ChatComposerSend;
}

export function ChatComposer({ leading, input, attach, trailing, send }: ChatComposerProps) {
  const AttachIcon = attach?.icon;
  const SendIcon = send.icon;
  return (
    <div className="send-top-row">
      {leading && <span className="comp-chat-composer__leading">{leading}</span>}
      <div className="send-input-wrap">
        {input}
        {/* クリップボタン（Meta と同配置: ピル内右端） */}
        {attach && AttachIcon && (
          <button
            type="button"
            className="send-attach-btn"
            onClick={attach.onClick}
            disabled={attach.disabled}
            aria-label={attach.label}
            title={attach.label}
          >
            <AttachIcon size={ICON.md} aria-hidden="true" />
          </button>
        )}
      </div>
      {trailing}
      <button
        type="button"
        className="inbox-send-btn"
        onClick={send.onClick}
        disabled={send.disabled}
        title={send.title}
      >
        <SendIcon size={ICON.base} aria-hidden="true" />
        <span className="sr-only">{send.label}</span>
      </button>
    </div>
  );
}
