import { describe, expect, it } from "vitest";
import { splitForSpeech } from "./useSecretaryVoice";

// 全角の句点・疑問符（文字列リテラルに日本語を書かない決まりのため、コードで作る）
const MARU = String.fromCharCode(0x3002);
const FULLWIDTH_QUESTION = String.fromCharCode(0xff1f);

describe("splitForSpeech", () => {
  it("splits after sentence-ending marks and keeps the mark", () => {
    expect(splitForSpeech(`Hello${MARU}Tomorrow${FULLWIDTH_QUESTION}`)).toEqual([
      `Hello${MARU}`,
      `Tomorrow${FULLWIDTH_QUESTION}`,
    ]);
    expect(splitForSpeech("Hi! Ready?")).toEqual(["Hi!", "Ready?"]);
  });

  it("splits on line breaks", () => {
    expect(splitForSpeech("first\nsecond")).toEqual(["first", "second"]);
  });

  it("cuts a piece over 300 characters every 300 characters", () => {
    const pieces = splitForSpeech(String.fromCharCode(0x3042).repeat(650));
    expect(pieces.map((p) => Array.from(p).length)).toEqual([300, 300, 50]);
  });

  it("returns no pieces for whitespace only", () => {
    expect(splitForSpeech("  \n \t ")).toEqual([]);
  });
});
