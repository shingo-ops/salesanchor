import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { LISTEN_MAX_IDLE_RESTARTS, classifyListenError, useSecretaryListen } from "./useSecretaryListen";

// 日本語の文字は文字列リテラルに書かず、コードで作る（useSecretaryVoice.test.ts と同じ）
const JP_TEXT = String.fromCharCode(0x3053, 0x3093, 0x306b, 0x3061, 0x306f);

type Handler = ((ev: never) => void) | null;

class FakeRecognition {
  static instances: FakeRecognition[] = [];
  static throwOnStart = false;
  lang = "";
  interimResults = false;
  continuous = true;
  maxAlternatives = 0;
  onresult: Handler = null;
  onerror: Handler = null;
  onend: Handler = null;
  start = vi.fn(() => {
    if (FakeRecognition.throwOnStart) throw new Error("boom");
  });
  stop = vi.fn();
  abort = vi.fn();
  constructor() {
    FakeRecognition.instances.push(this);
  }
  emitResult(transcript: string, isFinal: boolean) {
    const result = Object.assign([{ transcript }], { isFinal });
    const ev = { resultIndex: 0, results: [result] };
    (this.onresult as unknown as (e: typeof ev) => void)(ev);
  }
  emitError(code: string) {
    (this.onerror as unknown as (e: { error: string }) => void)({ error: code });
  }
  emitEnd() {
    (this.onend as unknown as () => void)();
  }
}

type W = { SpeechRecognition?: unknown; webkitSpeechRecognition?: unknown };
const w = window as unknown as W;
let savedSR: unknown;
let savedWebkit: unknown;

beforeEach(() => {
  savedSR = w.SpeechRecognition;
  savedWebkit = w.webkitSpeechRecognition;
  FakeRecognition.instances = [];
  FakeRecognition.throwOnStart = false;
  w.SpeechRecognition = FakeRecognition;
  delete w.webkitSpeechRecognition;
});
afterEach(() => {
  if (savedSR === undefined) delete w.SpeechRecognition;
  else w.SpeechRecognition = savedSR;
  if (savedWebkit === undefined) delete w.webkitSpeechRecognition;
  else w.webkitSpeechRecognition = savedWebkit;
});

describe("classifyListenError", () => {
  it.each([
    ["not-allowed", "notAllowed"],
    ["service-not-allowed", "serviceNotAllowed"],
    ["no-speech", "noSpeech"],
    ["audio-capture", "audioCapture"],
    ["network", "network"],
    ["language-not-supported", "language"],
    ["aborted", null],
    ["something-else", "other"],
  ])("maps %s to %s", (code, expected) => {
    expect(classifyListenError(code)).toBe(expected);
  });
});

describe("useSecretaryListen", () => {
  it("reports unsupported when no recognition class exists", () => {
    delete w.SpeechRecognition;
    const { result } = renderHook(() => useSecretaryListen(vi.fn()));
    expect(result.current.supported).toBe(false);
    act(() => result.current.start());
    expect(result.current.error).toBe("unsupported");
    expect(result.current.listening).toBe(false);
  });

  it("sets lang and options on start, and listening is true right after", () => {
    const { result } = renderHook(() => useSecretaryListen(vi.fn()));
    act(() => result.current.start());
    const rec = FakeRecognition.instances[0];
    expect(rec.lang).toBe("ja-JP");
    expect(rec.interimResults).toBe(true);
    expect(rec.continuous).toBe(true);
    expect(rec.maxAlternatives).toBe(1);
    expect(rec.start).toHaveBeenCalledTimes(1);
    expect(result.current.listening).toBe(true);
  });

  it("keeps interim text and calls onText once on a final result", () => {
    const onText = vi.fn();
    const { result } = renderHook(() => useSecretaryListen(onText));
    act(() => result.current.start());
    const rec = FakeRecognition.instances[0];
    act(() => rec.emitResult(JP_TEXT, false));
    expect(result.current.interim).toBe(JP_TEXT);
    expect(onText).not.toHaveBeenCalled();
    act(() => rec.emitResult(` ${JP_TEXT} `, true));
    expect(onText).toHaveBeenCalledTimes(1);
    expect(onText).toHaveBeenCalledWith(JP_TEXT);
  });

  it("does not call onText for an empty final result", () => {
    const onText = vi.fn();
    const { result } = renderHook(() => useSecretaryListen(onText));
    act(() => result.current.start());
    act(() => FakeRecognition.instances[0].emitResult("  ", true));
    expect(onText).not.toHaveBeenCalled();
  });

  it("always calls the latest onText", () => {
    const first = vi.fn();
    const second = vi.fn();
    const { result, rerender } = renderHook(({ cb }) => useSecretaryListen(cb), { initialProps: { cb: first } });
    act(() => result.current.start());
    rerender({ cb: second });
    act(() => FakeRecognition.instances[0].emitResult(JP_TEXT, true));
    expect(first).not.toHaveBeenCalled();
    expect(second).toHaveBeenCalledTimes(1);
  });

  it("aborts the recognition when unmounted", () => {
    const { result, unmount } = renderHook(() => useSecretaryListen(vi.fn()));
    act(() => result.current.start());
    const rec = FakeRecognition.instances[0];
    unmount();
    expect(rec.abort).toHaveBeenCalledTimes(1);
  });

  it("creates only one recognition when start is called twice in a row", () => {
    const { result } = renderHook(() => useSecretaryListen(vi.fn()));
    act(() => {
      result.current.start();
      result.current.start();
    });
    expect(FakeRecognition.instances.length).toBe(1);
  });

  it("clears the previous error on the next start", () => {
    const { result } = renderHook(() => useSecretaryListen(vi.fn()));
    act(() => result.current.start());
    act(() => FakeRecognition.instances[0].emitError("network"));
    act(() => FakeRecognition.instances[0].emitEnd());
    expect(result.current.error).toBe("network");
    act(() => result.current.start());
    expect(result.current.error).toBeNull();
  });

  it("sets error other when rec.start throws, and the next start makes a new recognition", () => {
    FakeRecognition.throwOnStart = true;
    const { result } = renderHook(() => useSecretaryListen(vi.fn()));
    act(() => result.current.start());
    expect(result.current.error).toBe("other");
    expect(result.current.listening).toBe(false);
    FakeRecognition.throwOnStart = false;
    act(() => result.current.start());
    expect(FakeRecognition.instances.length).toBe(2);
    expect(result.current.listening).toBe(true);
  });

  it("keeps the error after an end event that follows it", () => {
    const { result } = renderHook(() => useSecretaryListen(vi.fn()));
    act(() => result.current.start());
    const rec = FakeRecognition.instances[0];
    act(() => rec.emitError("network"));
    act(() => rec.emitEnd());
    expect(result.current.error).toBe("network");
    expect(result.current.listening).toBe(false);
    expect(FakeRecognition.instances.length).toBe(1);
  });

  it("shows nothing for an aborted error", () => {
    const { result } = renderHook(() => useSecretaryListen(vi.fn()));
    act(() => result.current.start());
    act(() => FakeRecognition.instances[0].emitError("aborted"));
    expect(result.current.error).toBeNull();
  });

  it("after abort, a new start makes a new recognition and the old end does not change listening", () => {
    const { result } = renderHook(() => useSecretaryListen(vi.fn()));
    act(() => result.current.start());
    const old = FakeRecognition.instances[0];
    act(() => result.current.abort());
    expect(old.abort).toHaveBeenCalledTimes(1);
    expect(result.current.listening).toBe(false);
    act(() => result.current.start());
    expect(FakeRecognition.instances.length).toBe(2);
    act(() => old.emitEnd());
    expect(result.current.listening).toBe(true);
  });

  it("ignores result and error from an aborted recognition", () => {
    const onText = vi.fn();
    const { result } = renderHook(() => useSecretaryListen(onText));
    act(() => result.current.start());
    const old = FakeRecognition.instances[0];
    act(() => result.current.abort());
    act(() => old.emitResult(JP_TEXT, true));
    act(() => old.emitError("network"));
    expect(onText).not.toHaveBeenCalled();
    expect(result.current.error).toBeNull();
  });

  it("stop only calls stop, and the following end turns listening off", () => {
    const { result } = renderHook(() => useSecretaryListen(vi.fn()));
    act(() => result.current.start());
    const rec = FakeRecognition.instances[0];
    act(() => result.current.stop());
    expect(rec.stop).toHaveBeenCalledTimes(1);
    expect(result.current.listening).toBe(true);
    act(() => rec.emitEnd());
    expect(result.current.listening).toBe(false);
  });
});

describe("useSecretaryListen keeps listening", () => {
  const last = () => FakeRecognition.instances[FakeRecognition.instances.length - 1];

  it("restarts with a new recognition when it ends by itself, and stays listening", () => {
    const { result } = renderHook(() => useSecretaryListen(vi.fn()));
    act(() => result.current.start());
    act(() => FakeRecognition.instances[0].emitEnd());
    expect(FakeRecognition.instances.length).toBe(2);
    expect(last().start).toHaveBeenCalledTimes(1);
    expect(result.current.listening).toBe(true);
  });

  it("does not restart after stop", () => {
    const { result } = renderHook(() => useSecretaryListen(vi.fn()));
    act(() => result.current.start());
    act(() => result.current.stop());
    act(() => FakeRecognition.instances[0].emitEnd());
    expect(FakeRecognition.instances.length).toBe(1);
    expect(result.current.listening).toBe(false);
  });

  it("does not restart after abort", () => {
    const { result } = renderHook(() => useSecretaryListen(vi.fn()));
    act(() => result.current.start());
    const old = FakeRecognition.instances[0];
    act(() => result.current.abort());
    act(() => old.emitEnd());
    expect(FakeRecognition.instances.length).toBe(1);
    expect(result.current.listening).toBe(false);
  });

  it("stops with noSpeech after the idle restart limit", () => {
    const { result } = renderHook(() => useSecretaryListen(vi.fn()));
    act(() => result.current.start());
    for (let i = 0; i < LISTEN_MAX_IDLE_RESTARTS; i += 1) {
      act(() => last().emitEnd());
      expect(result.current.listening).toBe(true);
    }
    expect(FakeRecognition.instances.length).toBe(LISTEN_MAX_IDLE_RESTARTS + 1);
    act(() => last().emitEnd());
    expect(FakeRecognition.instances.length).toBe(LISTEN_MAX_IDLE_RESTARTS + 1);
    expect(result.current.listening).toBe(false);
    expect(result.current.error).toBe("noSpeech");
  });

  it("resets the idle count on a final sentence and keeps restarting", () => {
    const { result } = renderHook(() => useSecretaryListen(vi.fn()));
    act(() => result.current.start());
    for (let i = 0; i < LISTEN_MAX_IDLE_RESTARTS - 1; i += 1) act(() => last().emitEnd());
    act(() => last().emitResult(JP_TEXT, true));
    for (let i = 0; i < LISTEN_MAX_IDLE_RESTARTS; i += 1) {
      act(() => last().emitEnd());
      expect(result.current.listening).toBe(true);
    }
    expect(result.current.error).toBeNull();
  });

  it("does not restart after notAllowed and keeps the error", () => {
    const { result } = renderHook(() => useSecretaryListen(vi.fn()));
    act(() => result.current.start());
    act(() => FakeRecognition.instances[0].emitError("not-allowed"));
    act(() => FakeRecognition.instances[0].emitEnd());
    expect(FakeRecognition.instances.length).toBe(1);
    expect(result.current.listening).toBe(false);
    expect(result.current.error).toBe("notAllowed");
  });

  it("hides a noSpeech error and restarts", () => {
    const { result } = renderHook(() => useSecretaryListen(vi.fn()));
    act(() => result.current.start());
    act(() => FakeRecognition.instances[0].emitError("no-speech"));
    expect(result.current.error).toBeNull();
    act(() => FakeRecognition.instances[0].emitEnd());
    expect(FakeRecognition.instances.length).toBe(2);
    expect(result.current.listening).toBe(true);
    expect(result.current.error).toBeNull();
  });

  it("does not pass the same final sentence twice across a restart", () => {
    const onText = vi.fn();
    const { result } = renderHook(() => useSecretaryListen(onText));
    act(() => result.current.start());
    const first = FakeRecognition.instances[0];
    act(() => first.emitResult(JP_TEXT, true));
    act(() => first.emitEnd());
    act(() => first.emitResult(JP_TEXT, true));
    expect(onText).toHaveBeenCalledTimes(1);
    act(() => last().emitResult(JP_TEXT + JP_TEXT, true));
    expect(onText).toHaveBeenCalledTimes(2);
  });
});
