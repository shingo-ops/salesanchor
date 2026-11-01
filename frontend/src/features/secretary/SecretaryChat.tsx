/**
 * SecretaryChat — 画面の右下の印から開くチャットの窓（ADR-1056 段2・カード B2）
 *
 * 出す条件は backend の口と同じ 4 つ（feature・super admin・customers.view・invoices.create）。
 * 会話は useState だけ（保存しない。閉じたら消す）。
 * AI の文字は React の文字としてだけ出す（HTML・Markdown として描画しない）。
 * エラー表示（status="error"）は AI 側の吹き出しにだけ使う。利用者側の吹き出しには付けない。
 */

import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { ChatBubble } from "../../components/ChatBubble";
import { Drawer } from "../../components/Drawer";
import { FloatingActionButton } from "../../components/FloatingActionButton";
import { Textarea } from "../../components/Textarea";
import { LeadChatIcon } from "../../constants/icons";
import { useFeatures } from "../../hooks/useFeatures";
import { usePermissions } from "../../hooks/usePermissions";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import { SecretaryDraftEvent } from "./SecretaryDraftEvent";
import { SecretaryDraftInvoice } from "./SecretaryDraftInvoice";
import {
  SECRETARY_MAX_TEXT,
  classifySecretaryError,
  sendSecretaryMessage,
  type AssistantReply,
} from "./secretaryApi";
import "./SecretaryChat.css";

type ChatMessage =
  | { id: number; side: "user"; kind: "text"; text: string }
  | { id: number; side: "assistant"; kind: "text"; text: string; status?: "sending" | "error" }
  | { id: number; side: "assistant"; kind: "invoice"; reply: Extract<AssistantReply, { kind: "invoice" }> }
  | { id: number; side: "assistant"; kind: "event"; reply: Extract<AssistantReply, { kind: "event" }> }
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
  const nextId = useRef(1);

  const close = () => {
    // 閉じたら会話を消す
    setOpen(false);
    setMessages([]);
    setText("");
  };

  const replaceMessage = (id: number, next: ChatMessage) =>
    setMessages((prev) => prev.map((m) => (m.id === id ? next : m)));

  const send = async () => {
    const trimmed = text.trim();
    if (!trimmed || sending) return;
    const userId = nextId.current++;
    const pendingId = nextId.current++;
    setMessages((prev) => [
      ...prev,
      { id: userId, side: "user", kind: "text", text: trimmed },
      { id: pendingId, side: "assistant", kind: "text", text: t("secretary.thinking"), status: "sending" },
    ]);
    setText("");
    setSending(true);
    try {
      const reply = await sendSecretaryMessage(trimmed);
      if (reply.kind === "invoice") {
        replaceMessage(pendingId, { id: pendingId, side: "assistant", kind: "invoice", reply });
      } else if (reply.kind === "event") {
        replaceMessage(pendingId, { id: pendingId, side: "assistant", kind: "event", reply });
      } else {
        replaceMessage(pendingId, { id: pendingId, side: "assistant", kind: "text", text: reply.draft.reply });
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

  const markCreated = (id: number, target: "invoice" | "event", to: string) =>
    replaceMessage(id, { id, side: "assistant", kind: "created", target, to });
  const markCancelled = (id: number) =>
    replaceMessage(id, { id, side: "assistant", kind: "text", text: t("secretary.cancelled") });

  const renderMessage = (m: ChatMessage) => {
    if (m.side === "user") {
      return (
        <ChatBubble key={m.id} side="user">
          {m.text}
        </ChatBubble>
      );
    }
    switch (m.kind) {
      case "text":
        return (
          <ChatBubble key={m.id} side="assistant" status={m.status}>
            {m.text}
          </ChatBubble>
        );
      case "invoice":
        return (
          <ChatBubble key={m.id} side="assistant" className="secretary-chat__draft-bubble">
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
          <ChatBubble key={m.id} side="assistant" className="secretary-chat__draft-bubble">
            <SecretaryDraftEvent
              draft={m.reply.draft}
              onCreated={() => markCreated(m.id, "event", "/schedule")}
              onCancel={() => markCancelled(m.id)}
            />
          </ChatBubble>
        );
      case "created":
        return (
          <ChatBubble key={m.id} side="assistant">
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
            <Textarea
              fullWidth
              value={text}
              maxLength={SECRETARY_MAX_TEXT}
              placeholder={t("secretary.placeholder")}
              aria-label={t("secretary.placeholder")}
              disabled={sending}
              onChange={(e) => setText(e.target.value)}
            />
            <Button onClick={send} disabled={sending || text.trim() === ""} loading={sending}>
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
  const features = useFeatures();
  const superAdmin = useSuperAdmin();
  const permissions = usePermissions();
  const [forbidden, setForbidden] = useState(false);

  const ready = !features.loading && !superAdmin.loading && !permissions.loading;
  const visible =
    ready &&
    !forbidden &&
    features.isEnabled("secretary_chat") &&
    superAdmin.isSuperAdmin &&
    permissions.hasPermission("customers.view") &&
    permissions.hasPermission("invoices.create");

  if (!visible) return null;
  return <SecretaryChatInner isMobile={isMobile} onForbidden={() => setForbidden(true)} />;
}
