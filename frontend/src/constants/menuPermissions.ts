/**
 * メニューと許可の対応の正本。
 *
 * 左の列（PC・スマホ）・管理センター・役割の画面の3か所が、ここだけを読む。
 * - MENUS: メニューを出す条件（許可のどれか1つを持てば出る）。
 * - ROLE_ROWS: 役割の画面で、同じ許可で一緒に出るメニューを1行にまとめた表。
 *
 * 各自の表示設定（prefs.show_sales_menu / prefs.show_chat_menu）・オーナー判定・
 * 行き先の選び分けは画面側に残す。ここは「許可で出す条件」だけを持つ。
 * 設計: docs/handoff/role-menu-permissions/design.md §5
 */

export type MenuId =
  | "dashboard"
  | "inventory"
  | "quotesInvoices"
  | "leads"
  | "orders"
  | "sales"
  | "commissions"
  | "commissionSettings"
  | "staff"
  | "roles"
  | "teams"
  | "shifts"
  | "tenantPolicy"
  | "tenantProfile"
  | "discordConfig"
  | "discordAnnounce"
  | "suppliers"
  | "statusMaster"
  | "units"
  | "noteMaster"
  | "conditionsMaster"
  | "productCategories"
  | "dataManagement"
  | "integrationGoogleDrive"
  | "integrationFedex"
  | "integrationDhl"
  | "integrationUps"
  | "integrationPaypal"
  | "channels"
  | "channelMasters"
  | "bots"
  | "notifications";

export interface MenuDef {
  /** 画面に出る名前の鍵（左の列・管理センターと同じ） */
  labelKey: string;
  /** どれか1つを持てば出る許可 */
  anyOf: readonly string[];
}

export const MENUS: Record<MenuId, MenuDef> = {
  dashboard: { labelKey: "nav.dashboard", anyOf: ["dashboard.view"] },
  inventory: { labelKey: "nav.inventory", anyOf: ["products.view"] },
  // 各自の設定 prefs.show_sales_menu は画面側に残す
  quotesInvoices: { labelKey: "nav.quotesInvoices", anyOf: ["quotes.view", "invoices.view"] },
  leads: { labelKey: "nav.leads", anyOf: ["leads.view", "customers.view"] },
  orders: { labelKey: "nav.orders", anyOf: ["orders.view"] },
  sales: { labelKey: "nav.sales", anyOf: ["orders.view"] },
  commissions: { labelKey: "nav.commissions", anyOf: ["orders.view"] },
  commissionSettings: { labelKey: "nav.commissionSettings", anyOf: ["orders.view"] },
  staff: { labelKey: "nav.staff", anyOf: ["staff.view"] },
  roles: { labelKey: "nav.roles", anyOf: ["roles.view", "roles.create"] },
  teams: { labelKey: "nav.teams", anyOf: ["teams.view"] },
  shifts: { labelKey: "nav.shifts", anyOf: ["shifts.view"] },
  tenantPolicy: { labelKey: "nav.tenantPolicy", anyOf: ["tenant.profile.edit", "tenant.profile.view"] },
  tenantProfile: { labelKey: "nav.tenantProfile", anyOf: ["tenant.profile.edit", "tenant.profile.view"] },
  discordConfig: { labelKey: "nav.discordConfig", anyOf: ["tenant.profile.edit", "tenant.profile.view"] },
  discordAnnounce: { labelKey: "nav.discordAnnounce", anyOf: ["tenant.profile.edit", "tenant.profile.view"] },
  suppliers: { labelKey: "nav.suppliers", anyOf: ["suppliers.view"] },
  statusMaster: { labelKey: "nav.statusMaster", anyOf: ["suppliers.view"] },
  units: { labelKey: "nav.units", anyOf: ["suppliers.view"] },
  noteMaster: { labelKey: "nav.noteMaster", anyOf: ["suppliers.view"] },
  conditionsMaster: { labelKey: "nav.conditionsMaster", anyOf: ["conditions.view"] },
  productCategories: { labelKey: "nav.productCategories", anyOf: ["product_categories.view"] },
  dataManagement: { labelKey: "nav.dataManagement", anyOf: ["erp.view"] },
  integrationGoogleDrive: { labelKey: "nav.integrationGoogleDrive", anyOf: ["erp.view"] },
  integrationFedex: { labelKey: "nav.integrationFedex", anyOf: ["erp.view"] },
  integrationDhl: { labelKey: "nav.integrationDhl", anyOf: ["erp.view"] },
  integrationUps: { labelKey: "nav.integrationUps", anyOf: ["erp.view"] },
  integrationPaypal: { labelKey: "nav.integrationPaypal", anyOf: ["erp.view"] },
  channels: { labelKey: "nav.channels", anyOf: ["channels.view"] },
  channelMasters: { labelKey: "nav.channelMasters", anyOf: ["tenant.profile.edit"] },
  bots: { labelKey: "nav.bots", anyOf: ["bots.view"] },
  notifications: { labelKey: "nav.notifications", anyOf: ["notifications.manage"] },
};

/** メニューを出してよいか（許可の条件だけ。各自の設定などは呼び出し側で足す） */
export function canSeeMenu(id: MenuId, hasAny: (...keys: string[]) => boolean): boolean {
  return hasAny(...MENUS[id].anyOf);
}

/**
 * 許可では出し分けないメニュー（役割の画面の行の名前にだけ使う）。
 * canSeeMenu の対象ではない。
 */
export type UngatedMenuId = "schedule" | "leadChat" | "reports" | "tenantLoginRequests";

export const UNGATED_MENU_LABELS: Record<UngatedMenuId, string> = {
  schedule: "nav.schedule",
  leadChat: "nav.leadChat",
  reports: "nav.reports",
  tenantLoginRequests: "nav.tenantLoginRequests",
};

export type RowMenuId = MenuId | UngatedMenuId;

/** 行に並ぶメニューの名前の鍵 */
export function rowMenuLabelKey(id: RowMenuId): string {
  return id in MENUS ? MENUS[id as MenuId].labelKey : UNGATED_MENU_LABELS[id as UngatedMenuId];
}

export type RoleRowSection = "sidebar" | "team" | "data" | "business";

export interface RoleRowDef {
  id: string;
  section: RoleRowSection;
  /** 一緒に出るメニュー。許可だけの行は null */
  menus: RowMenuId[] | null;
  /** 行の許可（DB の許可の鍵） */
  keys: readonly string[];
  /** 切替の代わりに固定の文を出す */
  fixed?: "always" | "ownerOnly";
  /** 行の下に出す注記の言葉の鍵 */
  noteKey?: string;
}

/** 役割の画面の行。区切りの順は 左の列 → チーム → データ → 事業 */
export const ROLE_ROWS: readonly RoleRowDef[] = [
  // ── 左の列 ──
  { id: "dashboard", section: "sidebar", menus: ["dashboard"], keys: ["dashboard.view"] },
  { id: "schedule", section: "sidebar", menus: ["schedule"], keys: [], fixed: "always" },
  {
    id: "chat", section: "sidebar", menus: ["leadChat"],
    keys: ["messaging.view", "messaging.send"], noteKey: "roles.noteChatPrefs",
  },
  {
    id: "inventory", section: "sidebar", menus: ["inventory"],
    keys: ["products.view", "products.create", "products.update", "products.delete"],
  },
  {
    id: "quotesInvoices", section: "sidebar", menus: ["quotesInvoices"],
    keys: [
      "quotes.view", "quotes.create", "quotes.update", "quotes.delete", "quotes.approve",
      "invoices.view", "invoices.create", "invoices.update", "invoices.void",
    ],
    noteKey: "roles.notePrefs",
  },
  {
    id: "crm", section: "sidebar", menus: ["leads"],
    keys: [
      "leads.view", "leads.create", "leads.update", "leads.delete", "leads.convert",
      "leads.discord_invite", "leads.discord_resync", "leads.discord_kick",
      "leads.discord_ban", "leads.discord_remove_channel",
      "customers.view", "customers.create", "customers.update", "customers.delete",
    ],
  },
  {
    id: "orders", section: "sidebar", menus: ["orders", "sales", "commissions", "commissionSettings"],
    keys: ["orders.view", "orders.create", "orders.update", "orders.delete"],
  },
  // ── チーム ──
  {
    id: "staff", section: "team", menus: ["staff"],
    keys: ["staff.view", "staff.create", "staff.update", "staff.delete"],
  },
  {
    id: "roles", section: "team", menus: ["roles"],
    keys: ["roles.view", "roles.create", "roles.update", "roles.delete", "roles.assign"],
  },
  {
    id: "teams", section: "team", menus: ["teams"],
    keys: ["teams.view", "teams.create", "teams.update", "teams.delete", "teams.manage_members"],
  },
  { id: "shifts", section: "team", menus: ["shifts"], keys: ["shifts.view", "shifts.manage"] },
  {
    id: "reports", section: "team", menus: ["reports"],
    keys: ["reports.view", "reports.export"], noteKey: "roles.noteReports",
  },
  // ── データ ──
  {
    id: "suppliers", section: "data", menus: ["suppliers", "statusMaster", "units", "noteMaster"],
    keys: ["suppliers.view", "suppliers.create", "suppliers.update", "suppliers.delete"],
  },
  {
    id: "conditions", section: "data", menus: ["conditionsMaster"],
    keys: ["conditions.view", "conditions.create", "conditions.update", "conditions.delete"],
  },
  {
    id: "productCategories", section: "data", menus: ["productCategories"],
    keys: ["product_categories.view", "product_categories.edit", "product_categories.delete"],
  },
  {
    id: "erp", section: "data",
    menus: [
      "dataManagement", "integrationGoogleDrive", "integrationFedex",
      "integrationDhl", "integrationUps", "integrationPaypal",
    ],
    keys: ["erp.view", "erp.sync"],
  },
  // ── 事業 ──
  {
    id: "tenant", section: "business",
    menus: ["tenantProfile", "tenantPolicy", "discordConfig", "discordAnnounce", "channelMasters"],
    keys: ["tenant.profile.view", "tenant.profile.edit"], noteKey: "roles.noteChannelMasters",
  },
  { id: "channels", section: "business", menus: ["channels"], keys: ["channels.view", "channels.manage"] },
  {
    id: "bots", section: "business", menus: ["bots"],
    keys: ["bots.view", "bots.create", "bots.update", "bots.delete"],
  },
  {
    id: "notifications", section: "business", menus: ["notifications"],
    keys: ["notifications.view", "notifications.manage"], noteKey: "roles.noteEditOnly",
  },
  { id: "loginRequests", section: "business", menus: ["tenantLoginRequests"], keys: [], fixed: "ownerOnly" },
];
