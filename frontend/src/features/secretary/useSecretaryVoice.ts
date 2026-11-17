/**
 * 秘書の返事を読み上げる部品（文の分け方・順に取る・順に鳴らす・止める）。
 * 鳴らし方は AudioContext だけ（<audio> と blob: の URL は使わない。画面の安全設定を広げないため）。
 */

import { useCallback, useEffect, useRef } from "react";
import { SPEECH_MAX_CHARS, fetchSecretarySpeech, isSpeechCapError } from "./secretaryApi";

/** 文の区切り（。！？!? と改行）で分け、300 字を超える片はさらに 300 字ごとに切る */
export function splitForSpeech(text: string): string[] {
  const pieces: string[] = [];
  for (const rough of text.split(/(?<=[。！？!?])|\n/)) {
    const piece = rough.trim();
    if (!piece) continue;
    const chars = Array.from(piece);
    for (let i = 0; i < chars.length; i += SPEECH_MAX_CHARS) {
      pieces.push(chars.slice(i, i + SPEECH_MAX_CHARS).join(""));
    }
  }
  return pieces;
}

export type SpeakResult = "ok" | "failed" | "cap";

export function useSecretaryVoice(): {
  enable: () => void;
  disable: () => void;
  speak: (text: string) => Promise<SpeakResult>;
  stop: () => void;
} {
  const ctxRef = useRef<AudioContext | null>(null);
  const sourceRef = useRef<AudioBufferSourceNode | null>(null);
  const generation = useRef(0);

  const stop = useCallback(() => {
    generation.current += 1;
    const source = sourceRef.current;
    sourceRef.current = null;
    if (source) {
      try {
        source.stop();
      } catch {
        // すでに止まっている
      }
    }
  }, []);

  const enable = useCallback(() => {
    if (ctxRef.current || typeof window === "undefined" || !window.AudioContext) return;
    const ctx = new window.AudioContext();
    ctxRef.current = ctx;
    void ctx.resume();
  }, []);

  const disable = useCallback(() => {
    stop();
    const ctx = ctxRef.current;
    ctxRef.current = null;
    if (ctx) void ctx.close();
  }, [stop]);

  const speak = useCallback(
    async (text: string): Promise<SpeakResult> => {
      stop();
      const ctx = ctxRef.current;
      if (!ctx) return "failed";
      const gen = generation.current;
      const pieces = splitForSpeech(text);
      if (pieces.length === 0) return "ok";

      const load = async (piece: string): Promise<AudioBuffer> => {
        const blob = await fetchSecretarySpeech(piece);
        return ctx.decodeAudioData(await blob.arrayBuffer());
      };

      try {
        let next: Promise<AudioBuffer> = load(pieces[0]);
        for (let i = 0; i < pieces.length; i++) {
          const current = next;
          // 先取りは 1 つだけ（鳴らしている間に次の片を取りに行く）
          next = i + 1 < pieces.length ? load(pieces[i + 1]) : current;
          if (i + 1 < pieces.length) next.catch(() => undefined);
          const buffer = await current;
          if (gen !== generation.current) return "ok";
          await new Promise<void>((resolve) => {
            const source = ctx.createBufferSource();
            source.buffer = buffer;
            source.connect(ctx.destination);
            source.onended = () => {
              if (sourceRef.current === source) sourceRef.current = null;
              resolve();
            };
            sourceRef.current = source;
            source.start();
          });
          if (gen !== generation.current) return "ok";
        }
        return "ok";
      } catch (err) {
        if (gen !== generation.current) return "ok";
        return isSpeechCapError(err) ? "cap" : "failed";
      }
    },
    [stop],
  );

  useEffect(() => disable, [disable]);

  return { enable, disable, speak, stop };
}
