import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import ja from "../locales/ja.json";
import en from "../locales/en.json";
import { API_ERROR_REASON_KEYS, apiErrorReasonKey } from "./apiErrorReason";

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

describe("apiErrorReasonKey", () => {
  it("maps table codes to locale keys and returns null otherwise", () => {
    expect(apiErrorReasonKey("no_fields_to_update")).toBe("apiError.noFieldsToUpdate");
    expect(apiErrorReasonKey("conflict_constraint")).toBe("apiError.conflictConstraint");
    expect(apiErrorReasonKey("role_not_assignable")).toBe("apiError.roleNotAssignable");
    expect(apiErrorReasonKey("viewer_already_linked")).toBeNull();
    expect(apiErrorReasonKey("toString")).toBeNull();
    expect(apiErrorReasonKey({ reason: "no_fields_to_update" })).toBeNull();
    expect(apiErrorReasonKey(null)).toBeNull();
  });
});

describe("i18n", () => {
  it("has a non-empty ja and en text for every key", () => {
    for (const key of Object.values(API_ERROR_REASON_KEYS)) {
      expect(lookup(ja as Dict, key), `ja:${key}`).toBeTruthy();
      expect(lookup(en as Dict, key), `en:${key}`).toBeTruthy();
    }
  });
});

describe("backend sync", () => {
  const sources = readPyFiles("../backend/app").join("\n");
  it("every table code is used in backend/app", () => {
    expect(Object.keys(API_ERROR_REASON_KEYS).length).toBe(8);
    for (const code of Object.keys(API_ERROR_REASON_KEYS)) {
      expect(sources.includes(`"${code}"`), code).toBe(true);
    }
  });
});
