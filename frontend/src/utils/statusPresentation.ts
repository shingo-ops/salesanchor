/**
 * ステータス → 見た目の SSoT（決定レイヤー①）
 *
 * 全 11 ステータスドメインを (domain, status) → { bucket, badgeVariant, labelKey }
 * の形式で一元管理する。ページ側は自前で色・クラスを決定しないこと。
 *
 * 参照: docs/handoff/decision-layer-01/design.md
 *       docs/adr/ADR-120-status-presentation-ssot.md
 */

/** 意味バケット（5種）— 最小語彙 */
export type BadgeBucket = "success" | "danger" | "warning" | "info" | "neutral";

/**
 * ステータス → 見た目のプレゼンテーション
 * - bucket:       意味バケット（5種）
 * - badgeVariant: badge CSS クラスのサフィックス（例: "won" → .badge-won）
 * - labelKey:     i18n キー（省略可。ページがラベル表示に使う）
 */
export interface StatusPresentation {
  bucket: BadgeBucket;
  badgeVariant: string;
  labelKey?: string;
}

/** 11 ステータスドメイン */
export type StatusDomain =
  | "lead"
  | "quote"
  | "invoice"
  | "deal"
  | "order"
  | "purchaseOrder"
  | "parseStatus"
  | "staff"
  | "bot"
  | "prospectRank"
  | "erpJobStatus";

const NEUTRAL_FALLBACK: StatusPresentation = {
  bucket: "neutral",
  badgeVariant: "neutral",
};

/**
 * 中央対応表（SSoT）
 *
 * バケット割当ルール（設計§3）:
 *   success  = 完了 / 成功 / 入金済み / 有効 / 受注
 *   danger   = 失敗 / エラー / 期限超過 / 失注 / 拒否
 *   warning  = 要対応 / 保留 / 期限間近
 *   info     = 進行中 / 交渉中 / 処理中 / 送信済み
 *   neutral  = 新規 / 下書き / 未着手 / 不明（フォールバック）
 *
 * ⚠️ PO 確認中の値:
 *   purchaseOrder.error — DB 値の存在確認中（Pydantic Enum 未定義・フロント暫定対応）
 *   staff.pending       — 現行フロントは active/else の 2分岐（pending が danger になっている）
 *   bot.maintenance     — 現行フロントは active/else の 2分岐（maintenance が danger になっている）
 */
export const STATUS_PRESENTATION_MAP: Record<StatusDomain, Record<string, StatusPresentation>> = {
  lead: {
    lead:              { bucket: "neutral", badgeVariant: "neutral",     labelKey: "leads.statusCode.lead" },
    negotiating:       { bucket: "info",    badgeVariant: "negotiating", labelKey: "leads.statusCode.negotiating" },
    existing_customer: { bucket: "success", badgeVariant: "won",         labelKey: "leads.statusCode.existing_customer" },
    follow_up_short:   { bucket: "warning", badgeVariant: "pending",     labelKey: "leads.statusCode.follow_up_short" },
    follow_up_long:    { bucket: "warning", badgeVariant: "pending",     labelKey: "leads.statusCode.follow_up_long" },
    lost:              { bucket: "danger",  badgeVariant: "lost",        labelKey: "leads.statusCode.lost" },
    out_of_scope:      { bucket: "danger",  badgeVariant: "lost",        labelKey: "leads.statusCode.out_of_scope" },
  },

  quote: {
    draft:    { bucket: "neutral", badgeVariant: "neutral",     labelKey: "quotes.status_draft" },
    sent:     { bucket: "info",    badgeVariant: "negotiating", labelKey: "quotes.status_sent" },
    approved: { bucket: "success", badgeVariant: "won",         labelKey: "quotes.status_approved" },
    rejected: { bucket: "danger",  badgeVariant: "lost",        labelKey: "quotes.status_rejected" },
    expired:  { bucket: "danger",  badgeVariant: "cancelled",   labelKey: "quotes.status_expired" },
  },

  invoice: {
    draft:   { bucket: "neutral", badgeVariant: "neutral",     labelKey: "invoices.status_draft" },
    sent:    { bucket: "info",    badgeVariant: "negotiating", labelKey: "invoices.status_sent" },
    issued:  { bucket: "info",    badgeVariant: "negotiating", labelKey: "invoices.status_issued" },
    paid:    { bucket: "success", badgeVariant: "won",         labelKey: "invoices.status_paid" },
    overdue: { bucket: "danger",  badgeVariant: "cancelled",   labelKey: "invoices.status_overdue" },
    voided:  { bucket: "danger",  badgeVariant: "lost",        labelKey: "invoices.status_voided" },
  },

  deal: {
    open:        { bucket: "neutral", badgeVariant: "neutral",     labelKey: "deals.status_open" },
    negotiating: { bucket: "info",    badgeVariant: "negotiating", labelKey: "deals.status_negotiating" },
    won:         { bucket: "success", badgeVariant: "won",         labelKey: "deals.status_won" },
    lost:        { bucket: "danger",  badgeVariant: "lost",        labelKey: "deals.status_lost" },
    on_hold:     { bucket: "warning", badgeVariant: "on_hold",     labelKey: "deals.status_on_hold" },
  },

  order: {
    awaiting_payment:  { bucket: "warning", badgeVariant: "awaiting_payment",  labelKey: "orders.status_awaiting_payment" },
    sourcing:          { bucket: "info",    badgeVariant: "sourcing",           labelKey: "orders.status_sourcing" },
    awaiting_shipping: { bucket: "warning", badgeVariant: "awaiting_shipping",  labelKey: "orders.status_awaiting_shipping" },
    completed:         { bucket: "success", badgeVariant: "completed",          labelKey: "orders.status_completed" },
    trouble:           { bucket: "danger",  badgeVariant: "trouble",            labelKey: "orders.status_trouble" },
    cancelled:         { bucket: "danger",  badgeVariant: "cancelled",          labelKey: "orders.status_cancelled" },
  },

  purchaseOrder: {
    draft:     { bucket: "neutral", badgeVariant: "neutral",     labelKey: "purchaseOrders.status_draft" },
    ordered:   { bucket: "info",    badgeVariant: "negotiating", labelKey: "purchaseOrders.status_ordered" },
    received:  { bucket: "success", badgeVariant: "won",         labelKey: "purchaseOrders.status_received" },
    cancelled: { bucket: "danger",  badgeVariant: "lost",        labelKey: "purchaseOrders.status_cancelled" },
    // DB 確認済み: purchase_orders.py:449 で status='error' を SET する実処理が存在する。
    // Pydantic Enum に未追加（スキーマ側の todo）だが DB 値としては実在する。
    error:     { bucket: "danger",  badgeVariant: "lost",        labelKey: "purchaseOrders.status_error" },
  },

  parseStatus: {
    pending:          { bucket: "neutral", badgeVariant: "neutral",     labelKey: "discord.parseStatus_pending" },
    parsing:          { bucket: "info",    badgeVariant: "negotiating", labelKey: "discord.parseStatus_parsing" },
    parsed:           { bucket: "success", badgeVariant: "won",         labelKey: "discord.parseStatus_parsed" },
    parsed_rule_only: { bucket: "success", badgeVariant: "won",         labelKey: "discord.parseStatus_parsed_rule_only" },
    parsed_llm:       { bucket: "success", badgeVariant: "won",         labelKey: "discord.parseStatus_parsed_llm" },
    approved:         { bucket: "success", badgeVariant: "won",         labelKey: "discord.parseStatus_approved" },
    rejected:         { bucket: "danger",  badgeVariant: "lost",        labelKey: "discord.parseStatus_rejected" },
    unparsed:         { bucket: "danger",  badgeVariant: "lost",        labelKey: "discord.parseStatus_unparsed" },
    budget_exhausted: { bucket: "warning", badgeVariant: "pending",     labelKey: "discord.parseStatus_budget_exhausted" },
    ignored_routing:  { bucket: "warning", badgeVariant: "pending",     labelKey: "discord.parseStatus_ignored_routing" },
  },

  staff: {
    active:   { bucket: "success", badgeVariant: "won",     labelKey: "staff.status_active" },
    inactive: { bucket: "neutral", badgeVariant: "neutral", labelKey: "staff.status_inactive" },
    // 現行フロントは active/else の2分岐のため danger（badge-lost）になっている。
    // 現状維持: danger に合わせる。将来 warning にする場合は bucket:"warning", badgeVariant:"pending" に変更可。
    pending:  { bucket: "danger", badgeVariant: "lost", labelKey: "staff.status_pending" },
  },

  bot: {
    active:   { bucket: "success", badgeVariant: "won",     labelKey: "bots.status_active" },
    inactive: { bucket: "neutral", badgeVariant: "neutral", labelKey: "bots.status_inactive" },
    // 現行フロントは active/else の2分岐のため danger（badge-lost）になっている。
    // 現状維持: danger に合わせる。将来 warning にする場合は bucket:"warning", badgeVariant:"pending" に変更可。
    maintenance: { bucket: "danger", badgeVariant: "lost", labelKey: "bots.status_maintenance" },
  },

  prospectRank: {
    "A":    { bucket: "success", badgeVariant: "won",         labelKey: "leads.prospectRank_A" },
    "B+":   { bucket: "success", badgeVariant: "confirmed",   labelKey: "leads.prospectRank_Bplus" },
    "B":    { bucket: "info",    badgeVariant: "negotiating", labelKey: "leads.prospectRank_B" },
    "B-":   { bucket: "warning", badgeVariant: "on_hold",     labelKey: "leads.prospectRank_Bminus" },
    /* eslint-disable-next-line local/no-japanese-literal -- DB 定義の商談ランクコード */
    "仮C":  { bucket: "neutral", badgeVariant: "pending",     labelKey: "leads.prospectRank_tentativeC" },
    /* eslint-disable-next-line local/no-japanese-literal -- DB 定義の商談ランクコード */
    "確定C": { bucket: "danger",  badgeVariant: "lost",        labelKey: "leads.prospectRank_confirmedC" },
  },

  erpJobStatus: {
    completed: { bucket: "success", badgeVariant: "won",  labelKey: "erp.jobStatus_completed" },
    failed:    { bucket: "danger",  badgeVariant: "lost", labelKey: "erp.jobStatus_failed" },
    running:   { bucket: "info",    badgeVariant: "negotiating", labelKey: "erp.jobStatus_running" },
    pending:   { bucket: "neutral", badgeVariant: "neutral",     labelKey: "erp.jobStatus_pending" },
  },
};

/**
 * ステータス値を見た目情報に変換する（SSoT エントリポイント）。
 *
 * @param domain - ステータスドメイン（例: "lead", "invoice"）
 * @param status - ステータス値（例: "negotiating", "paid"）
 * @returns StatusPresentation。未知の値は neutral で安全にフォールバックする。
 *
 * @example
 *   const p = getStatusPresentation("lead", lead.status);
 *   <span className={`badge badge-${p.badgeVariant}`}>{t(p.labelKey ?? lead.status)}</span>
 */
export function getStatusPresentation(
  domain: StatusDomain,
  status: string,
): StatusPresentation {
  const presentation = STATUS_PRESENTATION_MAP[domain]?.[status];

  if (!presentation) {
    if (import.meta.env.DEV) {
      // eslint-disable-next-line local/no-japanese-literal
      console.warn(`[getStatusPresentation] 未知のステータス "${status}" (domain: "${domain}") → neutral にフォールバックします`);
    }
    return NEUTRAL_FALLBACK;
  }

  return presentation;
}
