/**
 * 関税の額の決まりの形（invoice-create-portfolio 便B・design.md §3-3・§3-6）。
 * 正本はサーバーの schemas/duty_rules.py。数は文字のまま受け取り、文字のまま送る（小数の丸めを画面でしない）。
 */
export interface DutyComponent {
  id: number;
  sort_order: number;
  label: string;
  base: string;
  rate_pct: string;
  min_amount: string | null;
  max_amount: string | null;
  amount_currency: string | null;
}

export interface DutyRule {
  id: number;
  destination_country_code: string;
  carrier: string | null;
  label: string;
  effective_from: string;
  effective_to: string | null;
  source_url: string;
  note: string | null;
  is_active: boolean;
  components: DutyComponent[];
}

export interface DutyRuleOptions {
  duty_incoterms: string;
  currencies: string[];
  bases: string[];
}

/** 書いた後に取り直す写しの頭（ADR-1054）。一覧と選択肢の両方を含む */
export const DUTY_RULES_HEAD = ["admin", "duty-rules"] as const;
