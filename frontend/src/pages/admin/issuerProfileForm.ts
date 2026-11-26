/**
 * 書類に載せる会社情報（国内用・海外用）の型と、画面の欄 ⇔ API の値の変換
 * （ADR-1061 便2-2c2b。design.md §3-4・§3-4b）。
 * 決まりの正本は backend（app/services/issuer_rules.py と表の CHECK）。
 * 画面は返ってきた欄ごとの理由の番号を文言キーに直し、t() で文にする（ADR-027）。
 */
export type IssuerRegion = "domestic" | "overseas";

export const ISSUER_PROFILES_PATH = "/admin/issuer-profiles";
export const PREFECTURES_PATH = "/prefectures";
/** 日本の国の番号。backend の issuer_rules.py と表の CHECK が日本の決まりを当てる国 */
export const JAPAN_COUNTRY_CODE = "JP";

export interface IssuerProfile {
  region: IssuerRegion;
  company_name: string;
  email: string | null;
  website: string | null;
  country_code: string;
  postal_code: string | null;
  prefecture_code: string | null;
  state_region: string | null;
  city: string;
  address1: string;
  address2: string | null;
  phone: string | null;
  is_invoice_registered: boolean;
  registration_number: string | null;
  updated_at: string;
}

export interface LegacyIssuerValues {
  company_name: string | null;
  company_name_en: string | null;
  address: string | null;
  phone: string | null;
  email: string | null;
  website: string | null;
}

export interface IssuerProfiles {
  domestic: IssuerProfile | null;
  overseas: IssuerProfile | null;
  legacy: LegacyIssuerValues | null;
}

export interface Prefecture {
  code: string;
  name_ja: string;
  name_en: string;
  sort_order: number;
}

export interface RegionForm {
  company_name: string;
  email: string;
  website: string;
  country_code: string;
  postal_code: string;
  prefecture_code: string;
  state_region: string;
  city: string;
  address1: string;
  address2: string;
  phone: string;
  is_invoice_registered: boolean;
  registration_number: string;
}

export type IssuerForm = Record<IssuerRegion, RegionForm>;
export type FieldErrors = Partial<Record<keyof RegionForm, string>>;

export const emptyRegionForm: RegionForm = {
  company_name: "",
  email: "",
  website: "",
  country_code: "",
  postal_code: "",
  prefecture_code: "",
  state_region: "",
  city: "",
  address1: "",
  address2: "",
  phone: "",
  is_invoice_registered: false,
  registration_number: "",
};

export const emptyIssuerForm: IssuerForm = { domestic: emptyRegionForm, overseas: emptyRegionForm };

export function toRegionForm(p: IssuerProfile | null): RegionForm {
  if (!p) return emptyRegionForm;
  return {
    company_name: p.company_name ?? "",
    email: p.email ?? "",
    website: p.website ?? "",
    country_code: p.country_code ?? "",
    postal_code: p.postal_code ?? "",
    prefecture_code: p.prefecture_code ?? "",
    state_region: p.state_region ?? "",
    city: p.city ?? "",
    address1: p.address1 ?? "",
    address2: p.address2 ?? "",
    phone: p.phone ?? "",
    is_invoice_registered: Boolean(p.is_invoice_registered),
    registration_number: p.registration_number ?? "",
  };
}

export function toIssuerForm(d: IssuerProfiles): IssuerForm {
  return { domestic: toRegionForm(d.domestic), overseas: toRegionForm(d.overseas) };
}

export function isJapan(form: RegionForm): boolean {
  return form.country_code === JAPAN_COUNTRY_CODE;
}

const textOrNull = (v: string): string | null => (v.trim() === "" ? null : v.trim());

/** 保存で送る値。見えない欄（日本なら州・地域、日本以外なら都道府県、登録が無なら番号）は null */
export function toIssuerPayload(form: RegionForm): Record<string, string | boolean | null> {
  const jp = isJapan(form);
  return {
    company_name: textOrNull(form.company_name),
    email: textOrNull(form.email),
    website: textOrNull(form.website),
    country_code: textOrNull(form.country_code),
    postal_code: textOrNull(form.postal_code),
    prefecture_code: jp ? textOrNull(form.prefecture_code) : null,
    state_region: jp ? null : textOrNull(form.state_region),
    city: textOrNull(form.city),
    address1: textOrNull(form.address1),
    address2: textOrNull(form.address2),
    phone: textOrNull(form.phone),
    is_invoice_registered: form.is_invoice_registered,
    registration_number: form.is_invoice_registered ? textOrNull(form.registration_number) : null,
  };
}

const ERROR_KEYS: Record<string, string> = {
  required: "issuerProfile.errors.required",
  postal_jp: "issuerProfile.errors.postalJp",
  postal_foreign: "issuerProfile.errors.postalForeign",
  phone_jp: "issuerProfile.errors.phoneJp",
  phone_foreign: "issuerProfile.errors.phoneForeign",
  registration_number: "issuerProfile.errors.registrationNumber",
  unknown_code: "issuerProfile.errors.unknownCode",
  must_be_empty: "issuerProfile.errors.mustBeEmpty",
};

/** 422 の detail（{ fields: { 欄: 理由の番号 } }）を、欄 → 文言キーに直す。形が違えば null */
export function fieldErrorKeys(detail: unknown): FieldErrors | null {
  if (detail === null || typeof detail !== "object" || !("fields" in detail)) return null;
  const fields = (detail as { fields: unknown }).fields;
  if (fields === null || typeof fields !== "object") return null;
  const out: FieldErrors = {};
  for (const [field, code] of Object.entries(fields as Record<string, unknown>)) {
    if (typeof code === "string" && code in ERROR_KEYS) {
      out[field as keyof RegionForm] = ERROR_KEYS[code];
    }
  }
  return out;
}

/** 都道府県の選択肢。言語が日本語なら name_ja、それ以外は name_en（design.md §3-4「都道府県の一覧」） */
export function prefectureOptions(rows: Prefecture[], language: string): { value: string; label: string }[] {
  const ja = language.startsWith("ja");
  return rows.map((r) => ({ value: r.code, label: ja ? r.name_ja : r.name_en }));
}

/** 前の会社情報（古い6欄）を読むだけの欄に出す文。空の欄は飛ばす */
export function legacyText(v: LegacyIssuerValues): string {
  return [v.company_name, v.company_name_en, v.address, v.phone, v.email, v.website]
    .filter((x): x is string => typeof x === "string" && x.trim() !== "")
    .join("\n");
}
