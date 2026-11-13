import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import i18n from "../i18n";
import ja from "../locales/ja.json";
import en from "../locales/en.json";
import {
  API_ERROR_REASON_KEYS,
  NOT_FOUND_TARGET_KEYS,
  apiErrorReasonKey,
  apiErrorReasonMessage,
  notFoundMessage,
} from "./apiErrorReason";

type Dict = Record<string, unknown>;
const lookup = (d: Dict, key: string): unknown =>
  key.split(".").reduce<unknown>((cur, k) => (cur && typeof cur === "object" ? (cur as Dict)[k] : undefined), d);

// CI checks out the whole repo and runs from frontend (precedent: src/features/discord-connect/discordConnectError.test.ts)
function readPyFiles(dir: string): string[] {
  const out: string[] = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) out.push(...readPyFiles(p));
    else if (name.endsWith(".py")) out.push(readFileSync(p, "utf8"));
  }
  return out;
}

const sources = readPyFiles("../backend/app").join("\n");
const hasOwn = (o: object, k: string) => Object.prototype.hasOwnProperty.call(o, k);

describe("apiErrorReasonKey", () => {
  it("maps table codes to locale keys and returns null otherwise", () => {
    expect(apiErrorReasonKey("no_fields_to_update")).toBe("apiError.noFieldsToUpdate");
    expect(apiErrorReasonKey("conflict_constraint")).toBe("apiError.conflictConstraint");
    expect(apiErrorReasonKey("role_not_assignable")).toBe("apiError.roleNotAssignable");
    expect(apiErrorReasonKey("merge_target_archived")).toBe("apiError.mergeTargetArchived");
    expect(apiErrorReasonKey("viewer_already_linked")).toBeNull();
    expect(apiErrorReasonKey("toString")).toBeNull();
    expect(apiErrorReasonKey({ reason: "no_fields_to_update" })).toBeNull();
    expect(apiErrorReasonKey(null)).toBeNull();
  });
});

describe("i18n", () => {
  it("has a non-empty ja and en text for every key", () => {
    for (const key of [...Object.values(API_ERROR_REASON_KEYS), ...Object.values(NOT_FOUND_TARGET_KEYS)]) {
      expect(lookup(ja as Dict, key), `ja:${key}`).toBeTruthy();
      expect(lookup(en as Dict, key), `en:${key}`).toBeTruthy();
    }
    for (const key of ["apiError.notFound", "apiError.notFoundUnknown"]) {
      expect(lookup(ja as Dict, key), `ja:${key}`).toBeTruthy();
      expect(lookup(en as Dict, key), `en:${key}`).toBeTruthy();
    }
  });
});

describe("merge_target_archived", () => {
  afterEach(async () => {
    await i18n.changeLanguage("ja");
  });

  for (const lang of ["ja", "en"]) {
    it(`has no internal wording in the ${lang} text`, async () => {
      await i18n.changeLanguage(lang);
      const msg = apiErrorReasonMessage("merge_target_archived");
      expect(msg).toBeTruthy();
      expect(msg).not.toMatch(/master|archived|active|merge_target/);
    });
  }
});

describe("backend sync", () => {
  it("every table code is used in backend/app", () => {
    expect(Object.keys(API_ERROR_REASON_KEYS).length).toBe(18);
    for (const code of Object.keys(API_ERROR_REASON_KEYS)) {
      expect(sources.includes(`"${code}"`), code).toBe(true);
    }
  });
});

describe("not_found:<target> (ADR-1071 bin3)", () => {
  afterEach(async () => {
    await i18n.changeLanguage("ja");
  });

  it("has 66 targets, each key named after its target", () => {
    expect(Object.keys(NOT_FOUND_TARGET_KEYS).length).toBe(66);
    for (const [target, key] of Object.entries(NOT_FOUND_TARGET_KEYS)) {
      expect(key).toBe(`apiError.notFoundTarget.${target}`);
    }
  });

  for (const lang of ["ja", "en"] as const) {
    const dict = (lang === "ja" ? ja : en) as Dict;

    it(`builds the ${lang} text for every target`, async () => {
      await i18n.changeLanguage(lang);
      const template = lookup(dict, "apiError.notFound") as string;
      expect(template).toContain("{{target}}");
      for (const [target, key] of Object.entries(NOT_FOUND_TARGET_KEYS)) {
        const name = lookup(dict, key) as string;
        const text = notFoundMessage(`not_found:${target}`);
        expect(text, `${lang}:${target}`).toBe(template.replace("{{target}}", name));
        expect(text).not.toContain("{{");
        expect(text).not.toContain("not_found");
      }
    });

    it(`uses the ${lang} text without a name for an unknown target`, async () => {
      await i18n.changeLanguage(lang);
      const unknown = lookup(dict, "apiError.notFoundUnknown");
      expect(notFoundMessage("not_found:zzz")).toBe(unknown);
      expect(notFoundMessage("not_found:toString")).toBe(unknown);
      expect(notFoundMessage("not_found:")).toBe(unknown);
    });
  }

  it("builds the en sentence for lead and an unknown target", async () => {
    await i18n.changeLanguage("en");
    expect(notFoundMessage("not_found:lead")).toBe("The lead could not be found. Reload the page and try again.");
    expect(notFoundMessage("not_found:zzz")).toBe(
      "What you were looking for could not be found. Reload the page and try again.",
    );
  });

  it("leaves other details to the caller", () => {
    for (const d of ["not_found", "company_not_found", "viewer_already_linked", "", null, 404, { detail: "x" }]) {
      expect(notFoundMessage(d)).toBeNull();
    }
    expect(apiErrorReasonMessage("viewer_already_linked")).toBeNull();
    expect(apiErrorReasonMessage("no_fields_to_update")).toBe(lookup(ja as Dict, "apiError.noFieldsToUpdate"));
    expect(apiErrorReasonMessage("not_found:lead")).toBe(notFoundMessage("not_found:lead"));
  });
});

describe("backend sync (bin3)", () => {
  const used = new Set(Array.from(sources.matchAll(/"not_found:([a-z0-9_]+)"/g), (m) => m[1]));

  it("every not_found target used in backend/app is in the table", () => {
    expect(Array.from(used).filter((t) => !hasOwn(NOT_FOUND_TARGET_KEYS, t))).toEqual([]);
  });

  it("every table target is used in backend/app", () => {
    expect(Object.keys(NOT_FOUND_TARGET_KEYS).filter((t) => !used.has(t))).toEqual([]);
  });
});
