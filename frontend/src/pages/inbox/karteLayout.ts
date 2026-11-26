/**
 * ADR-1089: 受信箱のカルテの段階ごとの見せ方（正本・ここ1か所だけ）。
 *
 * どの段階で、どのタブを、どの順に出し、どの項目をどのタブに置くかは、ここで決める。
 * 出し分けは見せ方だけ。データは消さない（保存は今もカルテの全部の値を送る）。
 * 段階の内部の名前は ADR-109（constants/leadStatus.ts）。
 */
import type { KarteTabKey } from "./inbox.types";

/** カルテの項目（連絡先タブの中身は段階で変えないので入れない）。 */
export type KarteFieldKey =
  | "nickname"
  | "country"
  | "customer_type"
  | "target_titles"
  | "sales_form"
  | "next_action" // 次回アクション＋次回アクション日
  | "response_speed"
  | "temperature"
  | "challenge"
  | "competitor_check"
  | "estimated_scale"
  | "amounts" // 月間見込み金額＋1件単価＋月間頻度
  | "meeting_memo"
  | "performance" // 実績サマリー（読むだけ）
  | "cs_memo";

export type KarteSectionKey =
  | "basic"
  | "dealProfile"
  | "nextAction"
  | "analysis"
  | "scale"
  | "memo"
  | "performance"
  | "handover";

/** 見出しの並び（この順で出す。中の項目が1つも無い見出しは出さない）。 */
export const KARTE_SECTIONS: readonly { key: KarteSectionKey; fields: readonly KarteFieldKey[] }[] = [
  { key: "basic", fields: ["nickname", "country", "customer_type"] },
  { key: "dealProfile", fields: ["target_titles", "sales_form"] },
  { key: "nextAction", fields: ["next_action"] },
  { key: "analysis", fields: ["response_speed", "temperature", "challenge", "competitor_check"] },
  { key: "scale", fields: ["estimated_scale", "amounts"] },
  { key: "memo", fields: ["meeting_memo"] },
  { key: "performance", fields: ["performance"] },
  { key: "handover", fields: ["cs_memo"] },
];

export type KarteStage = "lead" | "negotiating" | "customer" | "other";

export interface KarteLayout {
  stage: KarteStage;
  /** 出すタブ（左から順）。最初の1つが最初に開くタブ。 */
  tabs: readonly KarteTabKey[];
  /** タブごとに出す項目（連絡先タブは段階で変えないので書かない）。 */
  fields: Readonly<Partial<Record<KarteTabKey, readonly KarteFieldKey[]>>>;
}

const LEAD_LAYOUT: KarteLayout = {
  stage: "lead",
  tabs: ["deal", "contact"],
  fields: {
    deal: [
      "nickname", "country", "target_titles", "sales_form",
      "next_action", "response_speed", "temperature", "estimated_scale",
    ],
  },
};

const NEGOTIATING_LAYOUT: KarteLayout = {
  stage: "negotiating",
  tabs: ["deal", "contact"],
  fields: {
    deal: [
      "nickname", "country", "customer_type", "target_titles", "sales_form",
      "next_action", "response_speed", "temperature", "challenge", "competitor_check",
      "estimated_scale", "amounts", "meeting_memo",
    ],
  },
};

const CUSTOMER_LAYOUT: KarteLayout = {
  stage: "customer",
  tabs: ["company", "contact", "deal"],
  fields: {
    company: [
      "nickname", "country", "customer_type", "target_titles", "sales_form",
      "next_action", "performance", "cs_memo",
    ],
    deal: [
      "response_speed", "temperature", "challenge", "competitor_check",
      "estimated_scale", "amounts", "meeting_memo",
    ],
  },
};

/** PO の表に無い段階（失注・対象外など）は今の見せ方のまま（ADR-1089 What 3）。 */
const OTHER_LAYOUT: KarteLayout = {
  stage: "other",
  tabs: ["deal", "company", "contact"],
  fields: {
    company: [
      "nickname", "country", "customer_type", "target_titles", "sales_form",
      "performance", "cs_memo",
    ],
    deal: [
      "next_action", "response_speed", "temperature", "challenge", "competitor_check",
      "estimated_scale", "amounts", "meeting_memo",
    ],
  },
};

// ADR-1090: 成約後は既存顧客だけ。追客（短期・長期）は見込みのある新規顧客なので商談中と同じ見せ方
const CUSTOMER_STATUSES: readonly string[] = ["existing_customer"];
const NEGOTIATING_LIKE_STATUSES: readonly string[] = ["negotiating", "follow_up_short", "follow_up_long"];

/** 段階（leads.status の内部の名前）から、カルテの見せ方を返す。 */
export function getKarteLayout(status: string | null | undefined): KarteLayout {
  if (status === "lead") return LEAD_LAYOUT;
  if (status && NEGOTIATING_LIKE_STATUSES.includes(status)) return NEGOTIATING_LAYOUT;
  if (status && CUSTOMER_STATUSES.includes(status)) return CUSTOMER_LAYOUT;
  return OTHER_LAYOUT;
}

/** 今のタブがその段階に無ければ、その段階の最初のタブを返す（ADR-1089 What 6）。 */
export function resolveKarteTab(layout: KarteLayout, tab: KarteTabKey): KarteTabKey {
  return layout.tabs.includes(tab) ? tab : layout.tabs[0];
}
