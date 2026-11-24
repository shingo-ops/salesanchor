import { describe, expect, it } from "vitest";
import ja from "../../locales/ja.json";
import en from "../../locales/en.json";
import { judgeYesNo } from "./secretaryVoiceAnswer";

const c = (...codes: number[]) => String.fromCharCode(...codes);
const split = (s: string) => s.split("|");

const JA_YES = split(ja.secretary.voiceMode.yesWords);
const JA_NO = split(ja.secretary.voiceMode.noWords);
const EN_YES = split(en.secretary.voiceMode.yesWords);
const EN_NO = split(en.secretary.voiceMode.noWords);

// はい・いいえ・いや・違う
const HAI = c(0x306f, 0x3044);
const IIE = c(0x3044, 0x3044, 0x3048);
const IYA = c(0x3044, 0x3084);
const CHIGAU = c(0x9055, 0x3046);
// えーと・ええと（ええ で始まるが肯定ではない）
const ETO_LONG = c(0x3048, 0x30fc, 0x3068);
const ETO = c(0x3048, 0x3048, 0x3068);
// 全角 ＯＫ
const FULL_OK = c(0xff2f, 0xff2b);

describe("judgeYesNo", () => {
  it("judges yes", () => {
    expect(judgeYesNo(HAI, JA_YES, JA_NO)).toBe("yes");
  });
  it("judges no", () => {
    expect(judgeYesNo(IIE, JA_YES, JA_NO)).toBe("no");
  });
  it("looks at denial first", () => {
    expect(judgeYesNo(`${HAI}、${IYA}${CHIGAU}`, JA_YES, JA_NO)).toBe("no");
  });
  it("does not treat fillers as yes", () => {
    expect(judgeYesNo(ETO_LONG, JA_YES, JA_NO)).toBe("unknown");
    expect(judgeYesNo(ETO, JA_YES, JA_NO)).toBe("unknown");
  });
  it("folds full-width letters", () => {
    expect(judgeYesNo(FULL_OK, JA_YES, JA_NO)).toBe("yes");
  });
  it("matches English on word boundaries", () => {
    expect(judgeYesNo("let me look", EN_YES, EN_NO)).toBe("unknown");
    expect(judgeYesNo("I know", EN_YES, EN_NO)).toBe("unknown");
    expect(judgeYesNo("Yes, please.", EN_YES, EN_NO)).toBe("yes");
    expect(judgeYesNo("No.", EN_YES, EN_NO)).toBe("no");
    expect(judgeYesNo("yes please don't", EN_YES, EN_NO)).toBe("no");
  });
  it("ignores empty words", () => {
    expect(judgeYesNo("anything", ["", " "], [""])).toBe("unknown");
    expect(judgeYesNo("yes", ["", "yes"], [""])).toBe("yes");
  });
});
