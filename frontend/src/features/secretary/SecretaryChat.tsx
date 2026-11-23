/**
 * SecretaryChat — 画面の右下の印から開くチャットの窓（ADR-1056 段2・カード B2）
 *
 * 出す条件は backend の口と同じ 4 つ（feature・super admin・customers.view・invoices.create）。
 * 会話は useState だけ（保存しない。閉じたら消す）。
 * AI の文字は React の文字としてだけ出す（HTML・Markdown として描画しない）。
 * エラー表示（failed）は AI 側の吹き出しにだけ使う。利用者側の吹き出しには付けない。
 */

import { Fragment, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { ChatBubble } from "../../components/ChatBubble";
import { Drawer } from "../../components/Drawer";
import { FloatingActionButton } from "../../components/FloatingActionButton";
import { Textarea } from "../../components/Textarea";
import { IconToggleButton } from "../../components/IconToggleButton";
import { Toggle } from "../../components/Toggle";
import { LeadChatIcon, SECRETARY_ICONS } from "../../constants/icons";
import { useSecretaryAccess } from "./useSecretaryAccess";
import { useSecretaryListen } from "./useSecretaryListen";
import { useSecretaryVoice } from "./useSecretaryVoice";
import { SecretaryDraftEvent } from "./SecretaryDraftEvent";
import { SecretaryKarteAsk } from "./SecretaryKarteAsk";
import { SecretaryDraftInvoice } from "./SecretaryDraftInvoice";
import {
  SECRETARY_MAX_TEXT,
  classifySecretaryError,
  karteFromDraft,
  sendSecretaryMessage,
  type AssistantReply,
  type EventKarte,
} from "./secretaryApi";
import "./SecretaryChat.css";

type ChatMessage =
  | { id: number; side: "user"; kind: "text"; text: string }
  | { id: number; side: "assistant"; kind: "text"; text: string; status?: "sending" | "error" }
  | { id: number; side: "assistant"; kind: "invoice"; reply: Extract<AssistantReply, { kind: "invoice" }> }
  | { id: number; side: "assistant"; kind: "event"; reply: Extract<AssistantReply, { kind: "event" }> }
  | { id: number; side: "assistant"; kind: "ask"; reply: Extract<AssistantReply, { kind: "event" }> }
  | { id: number; side: "assistant"; kind: "created"; target: "invoice" | "event"; to: string };

interface InnerProps {
  isMobile: boolean;
  onForbidden: () => void;
}

function SecretaryChatInner({ isMobile, onForbidden }: InnerProps) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  // ADR-1078: 予定のカルテ（会話の間だけ持つ。保存しない。閉じたら消す）
  const [karte, setKarte] = useState<EventKarte | null>(null);
  // 声で返事（保存しない。窓を閉じたら切れに戻る）
  const [voiceOn, setVoiceOn] = useState(false);
  const [voiceNote, setVoiceNote] = useState<{ id: number; kind: "failed" | "cap" } | null>(null);
  const voice = useSecretaryVoice();
  // 声の聞き取り（確定した文を欄に足す。勝手に送らない）
  const [tooLong, setTooLong] = useState(false);
  const textRef = useRef("");
  textRef.current = text;
  const listenStopRef = useRef<() => void>(() => {});
  const listen = useSecretaryListen((heard) => {
    const next = textRef.current + heard;
    if (next.length >= SECRETARY_MAX_TEXT) {
      const capped = next.slice(0, SECRETARY_MAX_TEXT);
      textRef.current = capped;
      setText(capped);
      setTooLong(true);
      listenStopRef.current();
      return;
    }
    textRef.current = next;
    setText(next);
  });
  listenStopRef.current = listen.stop;
  const nextId = useRef(1);
  // 返事が届いた時点の値で決める（送った時点の値を使わない）
  const voiceOnRef = useRef(false);
  const session = useRef(0);

  const close = () => {
    // 閉じたら会話とカルテを消す
    listen.abort();
    setOpen(false);
    setMessages([]);
    setText("");
    setTooLong(false);
    setKarte(null);
    voice.disable();
    voiceOnRef.current = false;
    session.current += 1;
    setVoiceOn(false);
    setVoiceNote(null);
  };

  const onVoiceChange = (next: boolean) => {
    if (next) {
      voice.enable();
    } else {
      voice.disable();
      setVoiceNote(null);
    }
    voiceOnRef.current = next;
    setVoiceOn(next);
  };

  const speakFor = async (id: number, spoken: string) => {
    const r = await voice.speak(spoken);
    if (r !== "ok") setVoiceNote({ id, kind: r });
  };

  const replaceMessage = (id: number, next: ChatMessage) =>
    setMessages((prev) => prev.map((m) => (m.id === id ? next : m)));

  const send = async () => {
    const trimmed = text.trim();
    if (!trimmed || sending) return;
    voice.stop();
    listen.abort();
    setVoiceNote(null);
    const userId = nextId.current++;
    const pendingId = nextId.current++;
    setMessages((prev) => [
      ...prev,
      { id: userId, side: "user", kind: "text", text: trimmed },
      { id: pendingId, side: "assistant", kind: "text", text: t("secretary.thinking"), status: "sending" },
    ]);
    setText("");
    setTooLong(false);
    setSending(true);
    const sentIn = session.current;
    try {
      const reply = await sendSecretaryMessage(trimmed, karte);
      if (reply.kind === "event" && reply.draft.ask) {
        // まだ聞く欄がある: 埋まった欄と質問を出し、カルテを持ち続ける
        setKarte(karteFromDraft(reply.draft));
        replaceMessage(pendingId, { id: pendingId, side: "assistant", kind: "ask", reply });
        if (voiceOnRef.current && sentIn === session.current && reply.draft.ask) void speakFor(pendingId, t(`secretary.ask.${reply.draft.ask}`));
      } else {
        // 最後の確かめの欄・請求書・聞き返しではカルテを捨てる（失敗したときは捨てない）
        setKarte(null);
        if (reply.kind === "invoice") {
          replaceMessage(pendingId, { id: pendingId, side: "assistant", kind: "invoice", reply });
        } else if (reply.kind === "event") {
          replaceMessage(pendingId, { id: pendingId, side: "assistant", kind: "event", reply });
        } else {
          replaceMessage(pendingId, { id: pendingId, side: "assistant", kind: "text", text: reply.draft.reply });
          if (voiceOnRef.current && sentIn === session.current) void speakFor(pendingId, reply.draft.reply);
        }
      }
    } catch (err) {
      const kind = classifySecretaryError(err);
      if (kind === "forbidden") {
        onForbidden();
        return;
      }
      replaceMessage(pendingId, {
        id: pendingId,
        side: "assistant",
        kind: "text",
        text: t(`secretary.error.${kind}`),
        status: "error",
      });
    } finally {
      setSending(false);
    }
  };

  const markCreated = (id: number, target: "invoice" | "event", to: string) => {
    replaceMessage(id, { id, side: "assistant", kind: "created", target, to });
    if (voiceOnRef.current) void speakFor(id, t(target === "invoice" ? "secretary.created.invoice" : "secretary.created.event"));
  };
  const markCancelled = (id: number) =>
    replaceMessage(id, { id, side: "assistant", kind: "text", text: t("secretary.cancelled") });

  const renderMessage = (m: ChatMessage) => (
    <Fragment key={m.id}>
      {renderBubble(m)}
      {voiceNote?.id === m.id && (
        <p className="secretary-draft__error" role="status">
          {t(voiceNote.kind === "cap" ? "secretary.voiceCapReached" : "secretary.voiceFailed")}
        </p>
      )}
    </Fragment>
  );

  const renderBubble = (m: ChatMessage) => {
    if (m.side === "user") {
      return (
        <ChatBubble key={m.id} layout="panel" direction="outbound">
          {m.text}
        </ChatBubble>
      );
    }
    switch (m.kind) {
      case "text":
        return (
          <ChatBubble key={m.id} layout="panel" direction="inbound" pending={m.status === "sending"} failed={m.status === "error"}>
            {m.text}
          </ChatBubble>
        );
      case "invoice":
        return (
          <ChatBubble key={m.id} layout="panel" direction="inbound" wide>
            <SecretaryDraftInvoice
              draft={m.reply.draft}
              candidates={m.reply.candidates}
              onCreated={(invoiceId) => markCreated(m.id, "invoice", `/invoices/${invoiceId}`)}
              onCancel={() => markCancelled(m.id)}
            />
          </ChatBubble>
        );
      case "event":
        return (
          <ChatBubble key={m.id} layout="panel" direction="inbound" wide>
            <SecretaryDraftEvent
              draft={m.reply.draft}
              onCreated={() => markCreated(m.id, "event", "/schedule")}
              onCancel={() => markCancelled(m.id)}
            />
          </ChatBubble>
        );
      case "ask":
        return (
          <ChatBubble key={m.id} layout="panel" direction="inbound" wide>
            <SecretaryKarteAsk draft={m.reply.draft} />
          </ChatBubble>
        );
      case "created":
        return (
          <ChatBubble key={m.id} layout="panel" direction="inbound">
            {t(m.target === "invoice" ? "secretary.created.invoice" : "secretary.created.event")}{" "}
            <Link to={m.to} onClick={close}>
              {t(m.target === "invoice" ? "secretary.link.invoice" : "secretary.link.event")}
            </Link>
          </ChatBubble>
        );
    }
  };

  return (
    <>
      <FloatingActionButton
        icon={<LeadChatIcon />}
        label={t("secretary.open")}
        aboveTabbar={isMobile}
        onClick={() => setOpen(true)}
      />
      <Drawer
        open={open}
        onClose={close}
        title={t("secretary.title")}
        footer={
          <div className="secretary-chat__composer">
            <div className="secretary-chat__voice-row">
              <label htmlFor="secretary-voice-toggle">{t("secretary.voiceToggle")}</label>
              <Toggle id="secretary-voice-toggle" checked={voiceOn} onCheckedChange={onVoiceChange} />
            </div>
            <div className="secretary-chat__input-row">
              <Textarea
                fullWidth
                value={listen.listening ? text + listen.interim : text}
                maxLength={SECRETARY_MAX_TEXT}
                placeholder={t("secretary.placeholder")}
                aria-label={t("secretary.placeholder")}
                disabled={sending}
                readOnly={listen.listening}
                onChange={(e) => {
                  setTooLong(false);
                  setText(e.target.value);
                }}
              />
              <IconToggleButton
                  pressed={listen.listening}
                  iconOff={SECRETARY_ICONS.listen}
                  iconOn={SECRETARY_ICONS.listen}
                  size="md"
                  disabled={sending}
                  onClick={() => {
                    if (listen.listening) {
                      listen.stop();
                    } else {
                      setTooLong(false);
                      listen.start();
                    }
                  }}
                  aria-label={t(listen.listening ? "secretary.listen.stop" : "secretary.listen.start")}
                />
            </div>
            {(listen.listening || listen.error || tooLong) && (
              <p className="secretary-chat__listen-status" role="status">
                {listen.listening
                  ? t("secretary.listen.listening")
                  : tooLong
                    ? t("secretary.listen.tooLong", { max: SECRETARY_MAX_TEXT })
                    : t(`secretary.listen.error.${listen.error}`)}
              </p>
            )}
            <Button onClick={send} disabled={sending || listen.listening || text.trim() === ""} loading={sending}>
              {t("secretary.send")}
            </Button>
          </div>
        }
      >
        <div className="secretary-chat__messages">{messages.map(renderMessage)}</div>
      </Drawer>
    </>
  );
}

export function SecretaryChat({ isMobile }: { isMobile: boolean }) {
  const { allowed } = useSecretaryAccess();
  const [forbidden, setForbidden] = useState(false);

  const visible = allowed && !forbidden;

  if (!visible) return null;
  return <SecretaryChatInner isMobile={isMobile} onForbidden={() => setForbidden(true)} />;
}
