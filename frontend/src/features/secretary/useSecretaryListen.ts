/**
 * useSecretaryListen — 声 → 文字だけを受け持つ（ブラウザの聞き取り・Web Speech API）
 *
 * 秘書への送り・会話の扱いは持たない（便T・design.md §14-2（３））。
 * 部品は 1 つだけ recRef に持つ。受け口は「自分が今の部品か」を見てから動く。
 */

import { useCallback, useEffect, useRef, useState } from "react";

export type ListenError =
  | "notAllowed"
  | "serviceNotAllowed"
  | "noSpeech"
  | "audioCapture"
  | "network"
  | "language"
  | "other";

// lib.dom に無い前提の最小の型
interface SpeechRecognitionAlternativeLike {
  transcript: string;
}
interface SpeechRecognitionResultLike {
  isFinal: boolean;
  length: number;
  [index: number]: SpeechRecognitionAlternativeLike;
}
interface SpeechRecognitionResultListLike {
  length: number;
  [index: number]: SpeechRecognitionResultLike;
}
interface SpeechRecognitionResultEventLike {
  resultIndex: number;
  results: SpeechRecognitionResultListLike;
}
interface SpeechRecognitionErrorEventLike {
  error: string;
}
interface SpeechRecognitionLike {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  maxAlternatives: number;
  onresult: ((ev: SpeechRecognitionResultEventLike) => void) | null;
  onerror: ((ev: SpeechRecognitionErrorEventLike) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
}
type SpeechRecognitionCtor = new () => SpeechRecognitionLike;

interface SpeechWindow {
  SpeechRecognition?: SpeechRecognitionCtor;
  webkitSpeechRecognition?: SpeechRecognitionCtor;
}

export function getSpeechRecognition(): SpeechRecognitionCtor | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as SpeechWindow;
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

/** 1 か所の対応表。null は「何も出さない」 */
export function classifyListenError(code: string): ListenError | null {
  switch (code) {
    case "not-allowed":
      return "notAllowed";
    case "service-not-allowed":
      return "serviceNotAllowed";
    case "no-speech":
      return "noSpeech";
    case "audio-capture":
      return "audioCapture";
    case "network":
      return "network";
    case "language-not-supported":
      return "language";
    case "aborted":
      return null;
    default:
      return "other";
  }
}

/** 何も聞き取れないまま聞き直す回数の上限 */
export const LISTEN_MAX_IDLE_RESTARTS = 5;

export interface SecretaryListen {
  supported: boolean;
  listening: boolean;
  interim: string;
  error: ListenError | "unsupported" | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
}

export function useSecretaryListen(onText: (text: string) => void): SecretaryListen {
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState("");
  const [error, setError] = useState<ListenError | "unsupported" | null>(null);
  const recRef = useRef<SpeechRecognitionLike | null>(null);
  const wantRef = useRef(false);
  const idleRestartsRef = useRef(0);
  const onTextRef = useRef(onText);
  onTextRef.current = onText;

  const begin = useCallback(function beginListen() {
    const Ctor = getSpeechRecognition();
    if (!Ctor) {
      wantRef.current = false;
      setError("unsupported");
      return;
    }
    const rec = new Ctor();
    recRef.current = rec;
    rec.lang = "ja-JP";
    rec.interimResults = true;
    rec.continuous = true;
    rec.maxAlternatives = 1;
    rec.onresult = (ev) => {
      if (recRef.current !== rec) return;
      let interimText = "";
      for (let i = ev.resultIndex; i < ev.results.length; i += 1) {
        const result = ev.results[i];
        const transcript = result[0]?.transcript ?? "";
        if (result.isFinal) {
          const finalText = transcript.trim();
          if (finalText !== "") {
            idleRestartsRef.current = 0;
            onTextRef.current(finalText);
          }
        } else {
          interimText += transcript;
        }
      }
      setInterim(interimText);
    };
    rec.onerror = (ev) => {
      if (recRef.current !== rec) return;
      const kind = classifyListenError(ev.error);
      if (kind === null || kind === "noSpeech") return;
      wantRef.current = false;
      setError(kind);
    };
    rec.onend = () => {
      if (recRef.current !== rec) return;
      recRef.current = null;
      setInterim("");
      if (wantRef.current && idleRestartsRef.current < LISTEN_MAX_IDLE_RESTARTS) {
        idleRestartsRef.current += 1;
        beginListen();
        return;
      }
      const hitLimit = wantRef.current;
      wantRef.current = false;
      setListening(false);
      if (hitLimit) setError("noSpeech");
    };
    try {
      rec.start();
      setListening(true);
    } catch {
      recRef.current = null;
      wantRef.current = false;
      setListening(false);
      setError("other");
    }
  }, []);

  const start = useCallback(() => {
    if (recRef.current) return;
    wantRef.current = true;
    idleRestartsRef.current = 0;
    setError(null);
    setInterim("");
    begin();
  }, [begin]);

  const stop = useCallback(() => {
    wantRef.current = false;
    recRef.current?.stop();
  }, []);

  const abort = useCallback(() => {
    wantRef.current = false;
    const rec = recRef.current;
    if (!rec) return;
    recRef.current = null;
    setListening(false);
    setInterim("");
    try {
      rec.abort();
    } catch {
      // 止める途中の失敗は無視（すでに片付け済み）
    }
  }, []);

  useEffect(() => abort, [abort]);

  return { supported: getSpeechRecognition() !== null, listening, interim, error, start, stop, abort };
}
