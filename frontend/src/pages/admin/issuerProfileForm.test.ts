import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import {
  emptyRegionForm,
  fieldErrorKeys,
  legacyText,
  prefectureOptions,
  toIssuerForm,
  toIssuerPayload,
  type RegionForm,
} from "./issuerProfileForm";

const SRC_ROOT = join(__dirname, "..", "..");

function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    if (name === "node_modules") continue;
    const path = join(dir, name);
    if (statSync(path).isDirectory()) walk(path, out);
    else if (/\.(ts|tsx|json)$/.test(name)) out.push(path);
  }
  return out;
}

const form = (over: Partial<RegionForm>): RegionForm => ({ ...emptyRegionForm, ...over });

describe("toIssuerPayload", () => {
  it("sends prefecture and drops state for Japan, trimming and nulling empties", () => {
    const p = toIssuerPayload(form({
      company_name: "  A Co  ", country_code: "JP", prefecture_code: "13", state_region: "X",
      postal_code: "1000001", city: "C", address1: "1-1", email: "",
    }));
    expect(p.company_name).toBe("A Co");
    expect(p.prefecture_code).toBe("13");
    expect(p.state_region).toBeNull();
    expect(p.email).toBeNull();
  });

  it("sends state and drops prefecture outside Japan", () => {
    const p = toIssuerPayload(form({ country_code: "US", prefecture_code: "13", state_region: "CA" }));
    expect(p.prefecture_code).toBeNull();
    expect(p.state_region).toBe("CA");
  });

  it("drops the registration number when not registered", () => {
    expect(toIssuerPayload(form({ is_invoice_registered: false, registration_number: "T1234567890123" })).registration_number).toBeNull();
    expect(toIssuerPayload(form({ is_invoice_registered: true, registration_number: "T1234567890123" })).registration_number).toBe("T1234567890123");
  });
});

describe("fieldErrorKeys", () => {
  it("maps reason codes to message keys", () => {
    expect(fieldErrorKeys({ fields: { postal_code: "postal_jp", phone: "phone_foreign", city: "required" } })).toEqual({
      postal_code: "issuerProfile.errors.postalJp",
      phone: "issuerProfile.errors.phoneForeign",
      city: "issuerProfile.errors.required",
    });
  });

  it("returns null for other shapes", () => {
    expect(fieldErrorKeys("bad")).toBeNull();
    expect(fieldErrorKeys([{ loc: ["body"], msg: "x" }])).toBeNull();
    expect(fieldErrorKeys(null)).toBeNull();
  });
});

describe("prefectureOptions and forms", () => {
  const rows = [{ code: "13", name_ja: "JA-13", name_en: "EN-13", sort_order: 13 }];
  it("uses name_ja for Japanese and name_en otherwise", () => {
    expect(prefectureOptions(rows, "ja")).toEqual([{ value: "13", label: "JA-13" }]);
    expect(prefectureOptions(rows, "en")).toEqual([{ value: "13", label: "EN-13" }]);
  });

  it("starts empty when a region has no row and has no default country", () => {
    const f = toIssuerForm({ domestic: null, overseas: null, legacy: null });
    expect(f.domestic).toEqual(emptyRegionForm);
    expect(f.overseas.country_code).toBe("");
  });

  it("joins legacy values skipping empties", () => {
    expect(legacyText({ company_name: "Old", company_name_en: null, address: " ", phone: "1", email: null, website: null })).toBe("Old\n1");
  });
});

describe("prefecture names live only in the DB seed", () => {
  it("no source file under src contains a prefecture name", () => {
    // この試験ファイル自身も src の下にある。名前を直接書くと自分に当たるので、文字の番号から組み立てる（都道府県コード 01 の名前）
    const name = String.fromCodePoint(0x5317, 0x6d77, 0x9053);
    const hits = walk(SRC_ROOT).filter((path) => readFileSync(path, "utf-8").includes(name));
    expect(hits).toEqual([]);
  });
});
