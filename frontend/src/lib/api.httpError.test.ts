import { afterEach, describe, expect, it, vi } from "vitest";
import i18n from "../i18n";
import { api, ApiError } from "./api";

vi.mock("./firebase", () => ({ auth: { currentUser: { getIdToken: async () => "t" } } }));

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api HTTP error text", () => {
  it("uses the dictionary text with the status when detail is empty", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("{}", { status: 409, headers: { "Content-Type": "application/json" } }),
      ),
    );
    let caught: unknown;
    try {
      await api.get("/dummy");
    } catch (e) {
      caught = e;
    }
    expect(caught).toBeInstanceOf(ApiError);
    const err = caught as ApiError;
    expect(err.status).toBe(409);
    expect(err.message).toBe(i18n.t("common.httpError", { status: 409 }));
    expect(err.message).toContain("409");
  });
});
