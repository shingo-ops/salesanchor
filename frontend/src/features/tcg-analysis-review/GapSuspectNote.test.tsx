import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import i18n from "../../i18n";
import { GapSuspectNote, gapSuspectOf } from "./GapSuspectNote";

beforeEach(async () => {
  await i18n.changeLanguage("en");
});
afterEach(cleanup);

describe("GapSuspectNote", () => {
  it("shows gap line numbers and candidate names", () => {
    render(
      <GapSuspectNote
        gapLines={[14, 15]}
        candidates={[{ product_id: "1001", name: "Product A" }, { product_id: "1002", name: "Product B" }]}
      />,
    );

    expect(screen.getByText(/Gap lines: L14.*L15/)).toBeTruthy();
    expect(screen.getByText(/Candidates: Product A.*Product B/)).toBeTruthy();
  });

  it("omits the candidates line when there is no candidate", () => {
    render(<GapSuspectNote gapLines={[14]} candidates={[]} />);

    expect(screen.getByText("Gap lines: L14")).toBeTruthy();
    expect(screen.queryByText(/Candidates/)).toBeNull();
  });

  it("falls back to the product id when the name is empty", () => {
    render(<GapSuspectNote gapLines={[3]} candidates={[{ product_id: "1001", name: "" }]} />);

    expect(screen.getByText("Candidates: 1001")).toBeTruthy();
  });
});

describe("gapSuspectOf", () => {
  const suspect = { gap_lines: [14], candidates: [] };
  const reason = (code: string) => [{ code, source: "system" as const, fix_stage: "extraction" as const }];

  it("returns the value only when the reason code is gemini_gap_suspect", () => {
    expect(gapSuspectOf({ review_reason_details: reason("gemini_gap_suspect"), gap_suspect: suspect })).toBe(suspect);
    expect(gapSuspectOf({ review_reason_details: reason("pid_unresolved"), gap_suspect: suspect })).toBeNull();
    expect(gapSuspectOf({ review_reason_details: reason("gemini_gap_suspect"), gap_suspect: null })).toBeNull();
    expect(gapSuspectOf({ gap_suspect: suspect })).toBeNull();
  });
});
