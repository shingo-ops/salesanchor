/**
 * 受注管理ページの状態管理フック。
 * OrdersPage の全 useState / useEffect / useMemo / handler を集約する。
 */

import { useEffect, useMemo, useRef, useState, FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { api, ApiError } from "../../lib/api";
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

  const [orders, setOrders] = useState<OrderListItem[]>([]);
  const [groupCounts, setGroupCounts] = useState<GroupCountsResponse | null>(null);
  const [companies, setCompanies] = useState<CompanyMini[]>([]);
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
  const [loading, setLoading] = useState(true);
  const [deleteTarget, setDeleteTarget] = useState<OrderListItem | null>(null);

  // ADR-021 Sprint 3: 発送情報（フェーズ判定 + 発送パネル）
  const [shippingTarget, setShippingTarget] = useState<OrderListItem | null>(null);
  const [shippings, setShippings] = useState<Record<number, ShippingDetailDto | null>>({});

  // ADR-021 Sprint 4: 仕入情報（フェーズ判定 + 仕入パネル）
  const [purchaseTarget, setPurchaseTarget] = useState<OrderListItem | null>(null);
  const [purchases, setPurchases] = useState<Record<number, PurchaseDetailDto | null>>({});

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

  const loadOrders = async () => {
    try {
      setLoading(true);
      const data = await api.get<OrderListItem[]>(
        `/orders${queryString ? `?${queryString}` : ""}`,
      );
      setOrders(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      setLoading(false);
    }
  };

  const loadGroupCounts = async () => {
    try {
      const data = await api.get<GroupCountsResponse>(
        `/orders/group-counts${groupCountsQueryString ? `?${groupCountsQueryString}` : ""}`,
      );
      setGroupCounts(data);
    } catch {
      setGroupCounts(null);
    }
  };

  const loadCompanies = async () => {
    try {
      const data = await api.get<CompanyMini[]>("/companies?per_page=100");
      setCompanies(
        data.map((c) => ({ id: c.id, company_code: c.company_code, name: c.name })),
      );
    } catch {
      /* ignore */
    }
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { loadOrders(); }, [queryString]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { loadGroupCounts(); }, [groupCountsQueryString]);
  useEffect(() => { loadCompanies(); }, []);

  // ADR-021 Sprint 3: 発送情報を並列取得（ステータスフロー判定 + 発送先列）
  useEffect(() => {
    if (orders.length === 0) { setShippings({}); return; }
    let cancelled = false;
    const fetchAll = async () => {
      const results = await Promise.all(
        orders.map(async (o) => {
          try {
            const data = await api.get<ShippingDetailDto>(`/orders/${o.id}/shipping`);
            return [o.id, data] as const;
          } catch (e) {
            if (e instanceof ApiError && e.status === 404) return [o.id, null] as const;
            return [o.id, null] as const;
          }
        }),
      );
      if (cancelled) return;
      const map: Record<number, ShippingDetailDto | null> = {};
      for (const [id, data] of results) map[id] = data;
      setShippings(map);
    };
    fetchAll();
    return () => { cancelled = true; };
  }, [orders]);

  // ADR-021 Sprint 4: 仕入情報を並列取得（ステータスフロー判定 + 仕入パネル）
  useEffect(() => {
    if (orders.length === 0) { setPurchases({}); return; }
    let cancelled = false;
    const fetchAll = async () => {
      const results = await Promise.all(
        orders.map(async (o) => {
          try {
            const data = await api.get<PurchaseDetailDto>(`/orders/${o.id}/purchase`);
            return [o.id, data] as const;
          } catch (e) {
            if (e instanceof ApiError && e.status === 404) return [o.id, null] as const;
            return [o.id, null] as const;
          }
        }),
      );
      if (cancelled) return;
      const map: Record<number, PurchaseDetailDto | null> = {};
      for (const [id, data] of results) map[id] = data;
      setPurchases(map);
    };
    fetchAll();
    return () => { cancelled = true; };
  }, [orders]);

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
      deal_id: form.deal_id ? Number(form.deal_id) : null,
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
      loadGroupCounts();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    }
  };

  const handleEdit = (o: OrderListItem) => {
    setEditId(o.id);
    setForm({
      deal_id: o.deal_id ? String(o.deal_id) : "",
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
      loadGroupCounts();
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
    error, loading,
    deleteTarget, setDeleteTarget,
    shippingTarget, setShippingTarget,
    shippings, setShippings,
    purchaseTarget, setPurchaseTarget,
    purchases, setPurchases,
    STATUS_LABELS, SORT_OPTIONS,
    loadOrders, loadGroupCounts,
    handleSubmit, handleEdit, performDelete,
    companyDisplay, resetSelector, setPaidOrder,
  };
}
