/**
 * SecretaryChat — 画面の右下の印から開くチャットの窓（ADR-1056 段2・カード B2）
 *
 * 出す条件は backend の口と同じ 4 つ（feature・super admin・customers.view・invoices.create）。
 * 会話は useState だけ（保存しない。閉じたら消す）。
 * AI の文字は React の文字としてだけ出す（HTML・Markdown として描画しない）。
 * エラー表示（failed）は AI 側の吹き出しにだけ使う。利用者側の吹き出しには付けない。
 */

import { Fragment, useEffect, useRef, useState } from "react";
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
import { SecretaryDraftEvent, type SecretaryDraftEventHandle } from "./SecretaryDraftEvent";
import { judgeYesNo } from "./secretaryVoiceAnswer";
import { formatDateInput, formatDraftDateLine, formatTimeInput } from "../../pages/schedule/schedule-utils";
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

/** 声で会話: 話し終わってから自動で送るまでの静けさ（ミリ秒） */
const VOICE_SEND_SILENCE_MS = 1000;

interface InnerProps {
  isMobile: boolean;
  onForbidden: () => void;
}

function SecretaryChatInner({ isMobile, onForbidden }: InnerProps) {
  const { t, i18n } = useTranslation();
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
  // 声で会話: この回に聞き取った文があるか（手で打った文だけのときは自動で送らない）
  const heardRef = useRef(false);
  const listen = useSecretaryListen((heard) => {
    heardRef.current = true;
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
  // 読み上げ・送り・切り替え・閉じるのたびに 1 進める。古い読み上げの終わりでマイクを開かないための印
  const turnRef = useRef(0);
  // 予定の確かめ待ち（声で会話の間だけ持つ）
  const pendingConfirmRef = useRef<{ id: number; tries: number } | null>(null);
  const eventRefs = useRef(new Map<number, SecretaryDraftEventHandle>());

  const close = () => {
    // 閉じたら会話とカルテを消す
    listen.abort();
    turnRef.current += 1;
    heardRef.current = false;
    pendingConfirmRef.current = null;
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
    turnRef.current += 1;
    heardRef.current = false;
    voiceOnRef.current = next;
    if (next) {
      voice.enable();
      listen.start();
    } else {
      voice.disable();
      listen.abort();
      pendingConfirmRef.current = null;
      setVoiceNote(null);
    }
    setVoiceOn(next);
  };

  // 読み上げる前にマイクを止め、読み終わったらまた聞く（声で会話の間だけ呼ぶ）
  const speakThenListen = async (id: number, spoken: string) => {
    listen.abort();
    heardRef.current = false;
    const turn = ++turnRef.current;
    const r = await voice.speak(spoken);
    if (r !== "ok") {
      onVoiceChange(false);
      setVoiceNote({ id, kind: r });
      return;
    }
    if (voiceOnRef.current && turn === turnRef.current) listen.start();
  };

  const replaceMessage = (id: number, next: ChatMessage) =>
    setMessages((prev) => prev.map((m) => (m.id === id ? next : m)));

  const send = async () => {
    const trimmed = text.trim();
    if (!trimmed || sending) return;
    heardRef.current = false;
    turnRef.current += 1;
    voice.stop();
    listen.abort();
    setVoiceNote(null);
    const userId = nextId.current++;
    const confirm = voiceOnRef.current ? pendingConfirmRef.current : null;
    if (confirm) {
      // 予定の確かめ待ち: ChatGPT には送らず、はい／いいえだけ判定する（design §15-5）
      setMessages((prev) => [...prev, { id: userId, side: "user", kind: "text", text: trimmed }]);
      setText("");
      setTooLong(false);
      const answer = judgeYesNo(
        trimmed,
        t("secretary.voiceMode.yesWords").split("|"),
        t("secretary.voiceMode.noWords").split("|"),
      );
      if (answer === "yes") {
        pendingConfirmRef.current = null;
        if (!(eventRefs.current.get(confirm.id)?.submitByVoice() ?? false)) {
          void speakThenListen(confirm.id, t("secretary.voiceMode.checkScreen"));
        }
      } else if (answer === "no") {
        markCancelled(confirm.id);
        void speakThenListen(confirm.id, t("secretary.voiceMode.notCreated"));
      } else if (confirm.tries === 0) {
        pendingConfirmRef.current = { id: confirm.id, tries: 1 };
        void speakThenListen(confirm.id, t("secretary.voiceMode.askAgain"));
      } else {
        pendingConfirmRef.current = null;
        void speakThenListen(confirm.id, t("secretary.voiceMode.checkScreen"));
      }
      return;
    }
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
        if (voiceOnRef.current && sentIn === session.current && reply.draft.ask) {
          void speakThenListen(pendingId, t(`secretary.ask.${reply.draft.ask}`));
        }
      } else {
        // 最後の確かめの欄・請求書・聞き返しではカルテを捨てる（失敗したときは捨てない）
        setKarte(null);
        if (reply.kind === "invoice") {
          replaceMessage(pendingId, { id: pendingId, side: "assistant", kind: "invoice", reply });
          // 会社名・金額・品名は読まない（決まった文だけ）
          if (voiceOnRef.current && sentIn === session.current) {
            void speakThenListen(pendingId, t("secretary.voiceMode.invoiceReady"));
          }
        } else if (reply.kind === "event") {
          replaceMessage(pendingId, { id: pendingId, side: "assistant", kind: "event", reply });
          if (voiceOnRef.current && sentIn === session.current) {
            const d = reply.draft;
            if (!d.title || !d.start || !d.end) {
              void speakThenListen(pendingId, t("secretary.voiceMode.checkScreen"));
            } else {
              const s = new Date(d.start);
              const e = new Date(d.end);
              const when = formatDraftDateLine(
                {
                  startDate: formatDateInput(s),
                  startTime: formatTimeInput(s),
                  endDate: formatDateInput(e),
                  endTime: formatTimeInput(e),
                  allDay: d.is_all_day,
                },
                t,
                i18n.language,
              );
              pendingConfirmRef.current = { id: pendingId, tries: 0 };
              void speakThenListen(pendingId, t("secretary.voiceMode.confirmEvent", { title: d.title, when }));
            }
          }
        } else {
          replaceMessage(pendingId, { id: pendingId, side: "assistant", kind: "text", text: reply.draft.reply });
          if (voiceOnRef.current && sentIn === session.current) void speakThenListen(pendingId, reply.draft.reply);
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
      if (voiceOnRef.current && sentIn === session.current) {
        void speakThenListen(pendingId, t(`secretary.error.${kind}`));
      }
    } finally {
      setSending(false);
    }
  };
  const sendRef = useRef(send);
  sendRef.current = send;

  // 声で会話: 聞き取った文があり、途中の文字が空のまま一定時間たったら自動で送る
  useEffect(() => {
    if (!voiceOn || !listen.listening || !heardRef.current || text.trim() === "" || listen.interim !== "" || sending) {
      return;
    }
    const timer = setTimeout(() => void sendRef.current(), VOICE_SEND_SILENCE_MS);
    return () => clearTimeout(timer);
  }, [voiceOn, listen.listening, listen.interim, text, sending]);

  const markCreated = (id: number, target: "invoice" | "event", to: string) => {
    pendingConfirmRef.current = null;
    replaceMessage(id, { id, side: "assistant", kind: "created", target, to });
    if (voiceOnRef.current) {
      void speakThenListen(id, t(target === "invoice" ? "secretary.created.invoice" : "secretary.created.event"));
    }
  };
  const markCancelled = (id: number) => {
    pendingConfirmRef.current = null;
    replaceMessage(id, { id, side: "assistant", kind: "text", text: t("secretary.cancelled") });
  };

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
              ref={(h) => {
                if (h) eventRefs.current.set(m.id, h);
                else eventRefs.current.delete(m.id);
              }}
              draft={m.reply.draft}
              onCreated={() => markCreated(m.id, "event", "/schedule")}
              onCancel={() => markCancelled(m.id)}
              onVoiceFailed={() => {
                pendingConfirmRef.current = null;
                if (voiceOnRef.current) void speakThenListen(m.id, t("secretary.voiceMode.checkScreen"));
              }}
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
                    if (voiceOnRef.current) {
                      // 読み上げの途中に押しても秘書の声を拾わない
                      voice.stop();
                      turnRef.current += 1;
                    }
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
