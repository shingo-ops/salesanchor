import { describe, expect, it } from "vitest";
import { resolveAuthProvider } from "./provider";

describe("resolveAuthProvider", () => {
  it.each([undefined, null, "", "firebase", "SELF", "Self", " self", "self ", "true", 1])(
    "%j resolves to firebase",
    (value) => {
      expect(resolveAuthProvider(value)).toBe("firebase");
    },
  );

  it("only self resolves to self", () => {
    expect(resolveAuthProvider("self")).toBe("self");
  });
});
