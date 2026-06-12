/**
 * ファネルダッシュボード モック fixtures
 * API contract: docs/handoff/funnel-dashboard-stage1/api-contract.md
 * 実APIへの切替: frontend/src/api/funnel.ts の MOCK_MODE を false に変更するだけ
 */

export const MOCK_FUNNEL = {
  month: "2026-06",
  month_elapsed_pct: 40,
  leads: { target: 30, actual: 22 },
  conversion: { target_rate: 50, actual_rate: 41, converted: 9 },
  active: { count: 18, amount: 8400000, coverage_pct_of_remaining_target: 175 },
  closed: { won_target: 10, won: 6, won_rate: 35, lost: 4 },
};

export const MOCK_REVENUE_SUMMARY = {
  revenue: { target: 8000000, actual: 3200000, pace: "on_track" as const },
  split: { new: 1100000, repeat: 2100000 },
  new_customers: { target: 8, actual: 4 },
  active_existing_customers: 26,
  gross_margin: { amount: 960000, uncosted_orders: 0 },
};

export const MOCK_FOLLOW_UPS = {
  items: [
    {
      customer_id: 1,
      name: "Card Haven LLC",
      segment: "order_stopped" as const,
      days: 62,
      last_order_at: "2026-04-11",
      last_contact_at: "2026-05-05",
      assignee: "佐藤",
    },
    {
      customer_id: 2,
      name: "Tokyo Trading Co.",
      segment: "no_repeat_after_first" as const,
      days: 47,
      last_order_at: "2026-04-27",
      last_contact_at: "2026-05-15",
      assignee: "田中",
    },
    {
      customer_id: 3,
      name: "Pacific Goods Inc.",
      segment: "won_no_order" as const,
      days: 35,
      last_order_at: null,
      last_contact_at: "2026-05-08",
      assignee: "鈴木",
    },
    {
      customer_id: 4,
      name: "Sunrise Retail",
      segment: "order_stopped" as const,
      days: 45,
      last_order_at: "2026-04-29",
      last_contact_at: "2026-05-20",
      assignee: "佐藤",
    },
    {
      customer_id: 5,
      name: "Blue Ocean Co.",
      segment: "order_stopped" as const,
      days: 31,
      last_order_at: "2026-05-13",
      last_contact_at: null,
      assignee: "田中",
    },
    {
      customer_id: 6,
      name: "Maple Store",
      segment: "no_repeat_after_first" as const,
      days: 52,
      last_order_at: "2026-04-22",
      last_contact_at: "2026-05-01",
      assignee: "鈴木",
    },
    {
      customer_id: 7,
      name: "Ember Shop",
      segment: "won_no_order" as const,
      days: 38,
      last_order_at: null,
      last_contact_at: "2026-05-06",
      assignee: "佐藤",
    },
  ],
};

export const MOCK_CHANNELS = {
  rows: [
    {
      initiative: "inbound",
      channel: "instagram",
      leads: 8,
      conversion_rate: 50,
      win_rate: 40,
      avg_order_value: 240000,
      gross_margin: 64000,
    },
    {
      initiative: "inbound",
      channel: "web_form",
      leads: 5,
      conversion_rate: 40,
      win_rate: 50,
      avg_order_value: 180000,
      gross_margin: 45000,
    },
    {
      initiative: "outbound",
      channel: "referral",
      leads: 6,
      conversion_rate: 67,
      win_rate: 75,
      avg_order_value: 320000,
      gross_margin: 96000,
    },
    {
      initiative: "inbound",
      channel: "messenger",
      leads: 3,
      conversion_rate: 33,
      win_rate: 100,
      avg_order_value: 150000,
      gross_margin: 30000,
    },
  ],
};

export const MOCK_REASONS_WON = {
  reasons: [
    { label: "在庫・品揃え", primary_count: 3, secondary_count: 2 },
    { label: "価格", primary_count: 1, secondary_count: 1 },
    { label: "スピード", primary_count: 1, secondary_count: 0 },
    { label: "安心感", primary_count: 1, secondary_count: 1 },
  ],
  memos: [
    {
      deal_id: 12,
      primary_label: "在庫・品揃え",
      memo: "探していたBOXが揃っていた",
      closed_at: "2026-06-05",
    },
    {
      deal_id: 15,
      primary_label: "スピード",
      memo: "翌日発送が決め手だった",
      closed_at: "2026-06-08",
    },
  ],
};

export const MOCK_REASONS_LOST = {
  reasons: [
    { label: "価格が合わなかった", primary_count: 2, secondary_count: 1 },
    { label: "対応が遅れた", primary_count: 1, secondary_count: 0 },
    { label: "お客様側の事情", primary_count: 1, secondary_count: 0 },
  ],
  memos: [
    {
      deal_id: 8,
      primary_label: "価格が合わなかった",
      memo: "他社が5%安かった",
      closed_at: "2026-06-03",
    },
  ],
};
