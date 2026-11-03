/**
 * 受注管理ページの状態管理フック。
 * OrdersPage の全 useState / useEffect / useMemo / handler を集約する。
 */

import { useEffect, useMemo, useRef, useState, FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { useApiCache, useApiQueries, useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";
import type {
  OrderListItem, CompanyMini, GroupCountsResponse,
} from "./orders.types";
import { emptyForm } from "./orders.types";
import type {
  ShippingDetailDto,
} from "../../components/ShippingDetailPanel";
import type {
  PurchaseDetailDto,
} from "../../components/PurchaseDetailPanel";

/** 金額を日本円フォーマットで表示 */
export const fmt = (n: number) =>
  n.toLocaleString("ja-JP", { style: "currency", currency: "JPY" });

/**
 * 通貨付き金額フォーマット（区切り4）。
 * JPY は整数表示、他通貨は小数点第 2 位まで。currency 未指定は JPY 扱い。
 */
export const fmtCurrency = (n: number, currency: string | null | undefined) => {
  const cur = (currency || "JPY").toUpperCase();
  const fractionDigits = cur === "JPY" ? 0 : 2;
  try {
    return n.toLocaleString("ja-JP", {
      style: "currency",
      currency: cur,
      minimumFractionDigits: fractionDigits,
      maximumFractionDigits: fractionDigits,
    });
  } catch {
    // 未知の通貨コードは数値 + コード表記でフォールバック
    return `${n.toLocaleString("ja-JP", {
      minimumFractionDigits: fractionDigits,
      maximumFractionDigits: fractionDigits,
    })} ${cur}`;
  }
};

/** 粗利率を小数 1 桁 % 表示 */
export const fmtRate = (n: number | null | undefined) => {
  if (n === null || n === undefined) return "-";
  return `${(n * 100).toFixed(1)}%`;
};

/**
 * 受注のステータスフロー上のフェーズを判定する（区切り4 / ④）。
 *
 * 判定順（上から優先）:
 *   - cancelled / trouble       → orders.status をそのまま反映
 *   - completed                 → 発送ラベル発行済（label_issued_at）+ 追跡番号あり
 *   - awaiting_shipping（発送待ち）→ 仕入確定（purchase_status='confirmed'）
 *   - sourcing（仕入れ中）       → 支払済（paid_at あり）かつ仕入未確定
 *   - awaiting_payment（支払い待ち）→ 請求書発行済（invoice_id あり）かつ未払い
 *   - unknown                   → いずれにも該当しない（未着手）
 */
export const orderPhase = (
  o: OrderListItem,
  purchase: PurchaseDetailDto | null,
  shipping: ShippingDetailDto | null,
): string => {
  if (o.status === "cancelled") return "cancelled";
  if (o.status === "trouble") return "trouble";
  if (shipping && shipping.label_issued_at && shipping.tracking_number) {
    return "completed";
  }
  if (purchase && purchase.purchase_status === "confirmed") {
    return "awaiting_shipping";
  }
  if (o.paid_at) return "sourcing";
  if (o.invoice_id) return "awaiting_payment";
  return "unknown";
};

export function useOrdersState() {
  const { t } = useTranslation();

  const STATUS_LABELS: Record<string, string> = {
    awaiting_payment: t("orders.status_awaiting_payment"),
    sourcing: t("orders.status_sourcing"),
    awaiting_shipping: t("orders.status_awaiting_shipping"),
    completed: t("orders.status_completed"),
    trouble: t("orders.status_trouble"),
    cancelled: t("orders.status_cancelled"),
  };

  const SORT_OPTIONS = [
    { value: "updated_at", label: t("common.updatedAt") },
    { value: "created_at", label: t("common.createdAt") },
    { value: "total_amount", label: t("common.amount") },
    { value: "status", label: t("common.status") },
  ];

  const [statusFilter, setStatusFilter] = useState("");

  // ADR-021 Sprint 1: 検索 / ソート UI 状態
  const [searchInput, setSearchInput] = useState("");
  const [searchKeyword, setSearchKeyword] = useState("");
  const [sortBy, setSortBy] = useState("updated_at");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [companyId, setCompanyId] = useState<number | null>(null);
  const [contactId, setContactId] = useState<number | null>(null);
  const [selectorError, setSelectorError] = useState("");
  const [error, setError] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<OrderListItem | null>(null);

  // ADR-021 Sprint 3: 発送情報（フェーズ判定 + 発送パネル）
  const [shippingTarget, setShippingTarget] = useState<OrderListItem | null>(null);

  // ADR-021 Sprint 4: 仕入情報（フェーズ判定 + 仕入パネル）
  const [purchaseTarget, setPurchaseTarget] = useState<OrderListItem | null>(null);

  // 検索入力の debounce（300ms）
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    debounceTimer.current = setTimeout(() => {
      setSearchKeyword(searchInput.trim());
    }, 300);
    return () => {
      if (debounceTimer.current) clearTimeout(debounceTimer.current);
    };
  }, [searchInput]);

  const queryString = useMemo(() => {
    const p = new URLSearchParams();
    if (statusFilter) p.set("status", statusFilter);
    if (searchKeyword) p.set("search", searchKeyword);
    p.set("sort_by", sortBy);
    p.set("sort_order", sortOrder);
    return p.toString();
  }, [statusFilter, searchKeyword, sortBy, sortOrder]);

  const groupCountsQueryString = useMemo(() => {
    const p = new URLSearchParams();
    if (searchKeyword) p.set("search", searchKeyword);
    return p.toString();
  }, [searchKeyword]);

  const ordersQ = useApiQuery<OrderListItem[]>(`/orders${queryString ? `?${queryString}` : ""}`);
  const orders = ordersQ.data ?? [];
  const groupCountsQ = useApiQuery<GroupCountsResponse>(
    `/orders/group-counts${groupCountsQueryString ? `?${groupCountsQueryString}` : ""}`,
    { keepPrevious: true },
  );
  const groupCounts = groupCountsQ.data ?? null;
  const companiesQ = useApiQuery<CompanyMini[]>("/companies?per_page=100");
  const companies = useMemo<CompanyMini[]>(
    () => (companiesQ.data ?? []).map((c) => ({ id: c.id, company_code: c.company_code, name: c.name })),
    [companiesQ.data],
  );
  const loading = ordersQ.isPending;
  const refetching =
    (ordersQ.isFetching && !ordersQ.isPending) ||
    (groupCountsQ.isFetching && !groupCountsQ.isPending) ||
    (companiesQ.isFetching && !companiesQ.isPending);
  const shownError = error || (ordersQ.error ? (ordersQ.error instanceof Error ? ordersQ.error.message : t("common.fetchError")) : "");
  const invalidate = useInvalidateApi();
  const cache = useApiCache();

  const loadOrders = () => {
    void invalidate(["orders"]);
  };

  // ADR-021 Sprint 3・4: 発送と仕入を 1 件ずつ写しで取る（取れない・404 は null）
  const shippingQs = useApiQueries<ShippingDetailDto>(orders.map((o) => `/orders/${o.id}/shipping`));
  const purchaseQs = useApiQueries<PurchaseDetailDto>(orders.map((o) => `/orders/${o.id}/purchase`));
  const shippings: Record<number, ShippingDetailDto | null> = Object.fromEntries(
    orders.map((o, i) => [o.id, shippingQs[i]?.data ?? null]),
  );
  const purchases: Record<number, PurchaseDetailDto | null> = Object.fromEntries(
    orders.map((o, i) => [o.id, purchaseQs[i]?.data ?? null]),
  );
  const writeShipping = (saved: ShippingDetailDto) => cache.write(`/orders/${saved.order_id}/shipping`, saved);
  const writePurchase = (saved: PurchaseDetailDto) => cache.write(`/orders/${saved.order_id}/purchase`, saved);

  const resetSelector = () => {
    setCompanyId(null);
    setContactId(null);
    setSelectorError("");
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setSelectorError("");
    if (!editId && contactId === null) {
      setSelectorError(t("companyContactSelector.contactRequired"));
      return;
    }
    const basePayload = {
      order_number: form.order_number,
      total_amount: form.total_amount ? Number(form.total_amount) : null,
      status: form.status,
      notes: form.notes || null,
    };
    const payload = editId
      ? basePayload
      : { ...basePayload, company_id: companyId, contact_id: contactId };
    try {
      if (editId) {
        await api.patch(`/orders/${editId}`, payload);
      } else {
        await api.post("/orders", payload);
      }
      setShowForm(false);
      setEditId(null);
      setForm(emptyForm);
      resetSelector();
      loadOrders();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    }
  };

  const handleEdit = (o: OrderListItem) => {
    setEditId(o.id);
    setForm({
      order_number: o.order_number,
      total_amount: o.total_amount ? String(o.total_amount) : "",
      status: o.status,
      notes: o.notes || "",
    });
    setCompanyId(o.company_id);
    setContactId(o.contact_id);
    setSelectorError("");
    setShowForm(true);
  };

  const performDelete = async () => {
    if (!deleteTarget) return;
    const id = deleteTarget.id;
    setDeleteTarget(null);
    try {
      await api.delete(`/orders/${id}`);
      loadOrders();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.deleteError"));
    }
  };

  const companyDisplay = (o: OrderListItem) => {
    if (o.company_name) return o.company_name;
    const c = companies.find((c) => c.id === o.company_id);
    return c ? c.name : `#${o.company_id}`;
  };

  // 区切り4 / ④: 支払済フラグを切り替える（PATCH /orders/{id}/paid）。
  const setPaidOrder = async (o: OrderListItem, paid: boolean) => {
    setError("");
    try {
      await api.patch(`/orders/${o.id}/paid`, { paid });
      loadOrders();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    }
  };

  const toggleSortOrder = () => setSortOrder((prev) => (prev === "desc" ? "asc" : "desc"));

  return {
    orders, groupCounts, companies,
    statusFilter, setStatusFilter,
    searchInput, setSearchInput,
    sortBy, setSortBy,
    sortOrder, toggleSortOrder,
    showForm, setShowForm,
    editId, setEditId,
    form, setForm,
    companyId, setCompanyId,
    contactId, setContactId,
    selectorError,
    error: shownError, loading, refetching,
    deleteTarget, setDeleteTarget,
    shippingTarget, setShippingTarget,
    shippings, writeShipping,
    purchaseTarget, setPurchaseTarget,
    purchases, writePurchase,
    STATUS_LABELS, SORT_OPTIONS,
    loadOrders,
    handleSubmit, handleEdit, performDelete,
    companyDisplay, resetSelector, setPaidOrder,
  };
}
