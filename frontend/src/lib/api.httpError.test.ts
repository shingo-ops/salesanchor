import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../i18n";
import ja from "../locales/ja.json";
import { api, ApiError } from "./api";
import { registerTestDevSession } from "../test-utils/devSession";

beforeEach(() => {
  registerTestDevSession({ getAccessToken: async () => "t", hasSession: () => true });
});

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

async function catchApiError(run: () => Promise<unknown>): Promise<ApiError> {
  let caught: unknown;
  try {
    await run();
  } catch (e) {
    caught = e;
  }
  expect(caught).toBeInstanceOf(ApiError);
  return caught as ApiError;
}

function stubDetail(status: number, detail: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail }), { status, headers: { "Content-Type": "application/json" } }),
    ),
  );
}

describe("common reason code texts (ADR-1071 bin2)", () => {
  afterEach(async () => {
    await i18n.changeLanguage("ja");
  });

  const cases = [
    {
      status: 400,
      code: "no_fields_to_update",
      ja: ja.apiError.noFieldsToUpdate,
      en: "Nothing was saved because no fields were changed. Change something, then save again.",
    },
    {
      status: 409,
      code: "conflict_constraint",
      ja: ja.apiError.conflictConstraint,
      en: "This could not be saved because the same item already exists or it does not match related data. Check what you entered and try again.",
    },
  ];

  for (const c of cases) {
    for (const lang of ["ja", "en"] as const) {
      it(`request: ${c.code} becomes the ${lang} text`, async () => {
        await i18n.changeLanguage(lang);
        stubDetail(c.status, c.code);
        const err = await catchApiError(() => api.patch("/dummy", {}));
        expect(err.status).toBe(c.status);
        expect(err.message).toBe(c[lang]);
        expect(err.responseDetail).toBe(c.code);
      });
      it(`requestForm: ${c.code} becomes the ${lang} text`, async () => {
        await i18n.changeLanguage(lang);
        stubDetail(c.status, c.code);
        const err = await catchApiError(() => api.postForm("/dummy", new FormData()));
        expect(err.message).toBe(c[lang]);
        expect(err.responseDetail).toBe(c.code);
      });
    }
  }

  it("passes an unknown code through unchanged", async () => {
    stubDetail(409, "viewer_already_linked");
    const err = await catchApiError(() => api.post("/dummy", {}));
    expect(err.message).toBe("viewer_already_linked");
  });

  it("keeps the detail field of a dict detail", async () => {
    stubDetail(409, { detail: "x", id: 1 });
    const err = await catchApiError(() => api.post("/dummy", {}));
    expect(err.message).toBe("x");
  });
});

describe("not_found:<target> texts (ADR-1071 bin3)", () => {
  afterEach(async () => {
    await i18n.changeLanguage("ja");
  });

  const expected = {
    ja: ja.apiError.notFound.replace("{{target}}", ja.apiError.notFoundTarget.lead),
    en: "The lead could not be found. Reload the page and try again.",
  };

  for (const lang of ["ja", "en"] as const) {
    it(`request: not_found:lead becomes the ${lang} text and keeps 404`, async () => {
      await i18n.changeLanguage(lang);
      stubDetail(404, "not_found:lead");
      const err = await catchApiError(() => api.get("/dummy"));
      expect(err.status).toBe(404);
      expect(err.message).toBe(expected[lang]);
      expect(err.responseDetail).toBe("not_found:lead");
    });
    it(`requestForm: not_found:lead becomes the ${lang} text and keeps 404`, async () => {
      await i18n.changeLanguage(lang);
      stubDetail(404, "not_found:lead");
      const err = await catchApiError(() => api.postForm("/dummy", new FormData()));
      expect(err.status).toBe(404);
      expect(err.message).toBe(expected[lang]);
      expect(err.responseDetail).toBe("not_found:lead");
    });
  }

  it("uses the text without a name for an unknown target", async () => {
    stubDetail(404, "not_found:zzz");
    const err = await catchApiError(() => api.get("/dummy"));
    expect(err.message).toBe(ja.apiError.notFoundUnknown);
    expect(err.responseDetail).toBe("not_found:zzz");
  });

  it("passes the old not-found codes through unchanged", async () => {
    for (const code of ["not_found", "company_not_found"]) {
      stubDetail(404, code);
      const err = await catchApiError(() => api.get("/dummy"));
      expect(err.message).toBe(code);
    }
  });
});
