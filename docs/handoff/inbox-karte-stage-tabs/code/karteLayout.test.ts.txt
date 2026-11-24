/* eslint-disable local/no-japanese-literal -- 試験の名前を日本語で書く */
/**
 * ADR-1089: カルテの段階ごとの見せ方（karteLayout.ts）の試験。
 * PO の表（docs/adr/ADR-1089-inbox-karte-stage-layout.md What 1）と1対1で照らす。
 */
import { describe, expect, it } from "vitest";
import { KARTE_SECTIONS, getKarteLayout, resolveKarteTab } from "./karteLayout";

describe("getKarteLayout", () => {
  it("リード: タブは 商談・連絡先、商談タブはリードの項目だけ", () => {
    const l = getKarteLayout("lead");
    expect(l.tabs).toEqual(["deal", "contact"]);
    expect(l.fields.deal).toEqual([
      "nickname", "country", "target_titles", "sales_form",
      "next_action", "response_speed", "temperature", "estimated_scale",
    ]);
    expect(l.fields.company).toBeUndefined();
  });

  it("商談中: タブは 商談・連絡先、実績サマリーと CS メモは出さない", () => {
    const l = getKarteLayout("negotiating");
    expect(l.tabs).toEqual(["deal", "contact"]);
    expect(l.fields.deal).toEqual([
      "nickname", "country", "customer_type", "target_titles", "sales_form",
      "next_action", "response_speed", "temperature", "challenge", "competitor_check",
      "estimated_scale", "amounts", "meeting_memo",
    ]);
    expect(l.fields.deal).not.toContain("performance");
    expect(l.fields.deal).not.toContain("cs_memo");
  });

  it.each(["existing_customer", "follow_up_short", "follow_up_long"])(
    "成約後（%s）: タブは 顧客・連絡先・商談、顧客タブと商談タブの項目は表のとおり",
    (status) => {
      const l = getKarteLayout(status);
      expect(l.tabs).toEqual(["company", "contact", "deal"]);
      expect(l.fields.company).toEqual([
        "nickname", "country", "customer_type", "target_titles", "sales_form",
        "next_action", "performance", "cs_memo",
      ]);
      expect(l.fields.deal).toEqual([
        "response_speed", "temperature", "challenge", "competitor_check",
        "estimated_scale", "amounts", "meeting_memo",
      ]);
    },
  );

  it.each(["lost", "out_of_scope", "", null, undefined])(
    "表に無い段階（%s）は今の見せ方のまま",
    (status) => {
      const l = getKarteLayout(status);
      expect(l.tabs).toEqual(["deal", "company", "contact"]);
      expect(l.fields.company).toEqual([
        "nickname", "country", "customer_type", "target_titles", "sales_form",
        "performance", "cs_memo",
      ]);
      expect(l.fields.deal).toEqual([
        "next_action", "response_speed", "temperature", "challenge", "competitor_check",
        "estimated_scale", "amounts", "meeting_memo",
      ]);
    },
  );

  it("どの段階でも、1つの項目は1つのタブにしか出ない", () => {
    for (const status of ["lead", "negotiating", "existing_customer", "lost"]) {
      const l = getKarteLayout(status);
      const all = [...(l.fields.deal ?? []), ...(l.fields.company ?? [])];
      expect(new Set(all).size).toBe(all.length);
    }
  });

  it("どの項目も、どれか1つの見出しに入っている", () => {
    const inSections = KARTE_SECTIONS.flatMap((s) => s.fields);
    expect(new Set(inSections).size).toBe(inSections.length);
    for (const status of ["lead", "negotiating", "existing_customer", "lost"]) {
      const l = getKarteLayout(status);
      for (const f of [...(l.fields.deal ?? []), ...(l.fields.company ?? [])]) {
        expect(inSections).toContain(f);
      }
    }
  });
});

describe("resolveKarteTab", () => {
  it("今のタブがその段階にあれば、そのまま", () => {
    expect(resolveKarteTab(getKarteLayout("existing_customer"), "deal")).toBe("deal");
    expect(resolveKarteTab(getKarteLayout("lead"), "contact")).toBe("contact");
  });

  it("今のタブがその段階に無ければ、その段階の最初のタブ", () => {
    expect(resolveKarteTab(getKarteLayout("lead"), "company")).toBe("deal");
    expect(resolveKarteTab(getKarteLayout("negotiating"), "company")).toBe("deal");
  });
});
