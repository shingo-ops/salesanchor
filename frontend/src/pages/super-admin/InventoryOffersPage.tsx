/**
 * /super-admin/inventory-offers — 仕入元現在オファー一覧・編集画面 (F11 AC11.5 / ADR-093 改修)。
 *
 * ADR-093 改修 (2026-06-03):
 *   - 列順を在庫表 (/inventory) に合わせる:
 *     カテゴリー / 型番 / 商品 / 状態 / 形態 / 区分(発送日) / 数量 / 単価 / 仕入元(掲載時刻)
 *     ＋ admin 専用列: ステータス / ソース / 有効期限
 *   - 一覧は閲覧専用（インライン編集を撤去）。編集はポップアップで行う。
 *   - 「操作」列を撤去。最左にチェックボックス、ヘッダー(ツールバー)に一括「削除」。
 *
 * 既存仕様:
 *   - is_super_admin=true のみアクセス可 (false なら 403 メッセージ + 二重ガード)
 *   - admin は quantity / unit_price / status / notes / expires_at を編集可能
 *   - UNIQUE キー (supplier × product × condition × unit × offer_type × ship_timing) は
 *     PATCH 不可要素を含むため、変更は DELETE + POST する運用
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { ApiError, api } from "../../lib/api";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import { PageLayout } from "../../components/PageLayout";
import ConfirmModal from "../../components/ConfirmModal";

type InventoryStatus = "in_stock" | "out_of_stock" | "reserved" | "archived";

interface InventoryOffer {
  id: number;
  supplier_id: number;
  product_id: number;
  condition: string;
  // ADR-093 Phase 3b: 区分(在庫/予約)・発送日（key 要素のため表示専用。編集は削除→再作成）
  offer_type: string;
  ship_timing: string | null;
  unit: string | null;
  quantity: number;
  unit_price: number;
  status: InventoryStatus;
  notes_ja: string | null;
  notes_en: string | null;
  offered_at: string;
  expires_at: string | null;
  source: string;
  created_at: string;
  updated_at: string;
  supplier_name: string | null;
  product_code: string | null;
  product_name: string | null;
  // ADR-093: 在庫表と同じ列を出すための products 由来表示列（読取専用）
  name_en: string | null;
  category: string | null;
  mark: string | null;
  tcg_type: string | null;
}

interface InventoryOffersListResponse {
  items: InventoryOffer[];
  total: number;
  page: number;
  per_page: number;
}

interface EditDraft {
  quantity: string;
  unit_price: string;
  status: InventoryStatus;
  notes_ja: string;
  notes_en: string;
  expires_at: string;
}

const STATUS_OPTIONS: InventoryStatus[] = [
  "in_stock",
  "out_of_stock",
  "reserved",
  "archived",
];

function offerToDraft(o: InventoryOffer): EditDraft {
  return {
    quantity: String(o.quantity),
    unit_price: String(o.unit_price),
    status: o.status,
    notes_ja: o.notes_ja ?? "",
    notes_en: o.notes_en ?? "",
    expires_at: o.expires_at ? o.expires_at.slice(0, 10) : "",
  };
}

export default function InventoryOffersPage() {
  const { t } = useTranslation();
  const { isSuperAdmin, loading: superAdminLoading } = useSuperAdmin();

  const [items, setItems] = useState<InventoryOffer[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [perPage] = useState(50);
  const [searchQ, setSearchQ] = useState("");
  const [statusFilter, setStatusFilter] = useState<InventoryStatus | "">("");
  const [conditionFilter, setConditionFilter] = useState("");
  // 入力値の debounce 反映先。テキスト入力は 250ms 待ってから API を叩く。select は即時。
  const [debouncedSearchQ, setDebouncedSearchQ] = useState("");
  const [debouncedConditionFilter, setDebouncedConditionFilter] = useState("");
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [loading, setLoading] = useState(false);

  // 一括削除（チェックボックス選択）
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [confirmDelete, setConfirmDelete] = useState(false);

  // 編集ポップアップ
  const [editing, setEditing] = useState<InventoryOffer | null>(null);
  const [draft, setDraft] = useState<EditDraft | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // 種別マスタ（tcg_type コード → 日本語名）。カテゴリー列を在庫表と同じ日本語表示にするため。
  const [tcgTypes, setTcgTypes] = useState<{ code: string; name_ja: string }[]>([]);
  const tcgTypeName = useMemo(() => new Map(tcgTypes.map((tt) => [tt.code, tt.name_ja])), [tcgTypes]);
  const categoryLabel = useCallback(
    (o: InventoryOffer): string =>
      (o.tcg_type ? tcgTypeName.get(o.tcg_type) : null) ?? o.category ?? "-",
    [tcgTypeName],
  );

  const totalPages = useMemo(
    () => (total === 0 ? 1 : Math.ceil(total / perPage)),
    [total, perPage],
  );

  // 掲載時間: YYYY-MM-DD HH:mm
  const fmtOfferedAt = useCallback((iso: string): string => {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "-";
    const p = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchQ(searchQ);
      setDebouncedConditionFilter(conditionFilter);
    }, 250);
    return () => clearTimeout(timer);
  }, [searchQ, conditionFilter]);

  const load = useCallback(async () => {
    setError("");
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("per_page", String(perPage));
      if (debouncedSearchQ.trim()) params.set("q", debouncedSearchQ.trim());
      if (statusFilter) params.set("status", statusFilter);
      if (debouncedConditionFilter.trim())
        params.set("condition", debouncedConditionFilter.trim());

      const d = await api.get<InventoryOffersListResponse>(
        `/super-admin/inventory-offers?${params.toString()}`,
      );
      setItems(d.items);
      setTotal(d.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      setLoading(false);
    }
  }, [page, perPage, debouncedSearchQ, statusFilter, debouncedConditionFilter, t]);

  useEffect(() => {
    if (!isSuperAdmin) return;
    void load();
  }, [isSuperAdmin, load]);

  // 種別マスタを取得（カテゴリー列の日本語表示用）。
  useEffect(() => {
    if (!isSuperAdmin) return;
    let cancelled = false;
    api
      .get<{ code: string; name_ja: string }[]>("/products/tcg-types")
      .then((d) => { if (!cancelled) setTcgTypes(d); })
      .catch(() => { /* 取得失敗時は生の category 表示にフォールバック */ });
    return () => { cancelled = true; };
  }, [isSuperAdmin]);

  const toggleSelect = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const openEdit = (offer: InventoryOffer) => {
    setEditing(offer);
    setDraft(offerToDraft(offer));
    setError("");
    setInfo("");
  };
  const cancelEdit = () => {
    setEditing(null);
    setDraft(null);
  };

  const submitEdit = async () => {
    if (!editing || !draft) return;
    setSubmitting(true);
    setError("");
    setInfo("");
    try {
      const qty = draft.quantity.trim();
      const price = draft.unit_price.trim();
      const body: Record<string, unknown> = {
        quantity: qty ? Number.parseInt(qty, 10) : 0,
        unit_price: price ? Number.parseInt(price, 10) : 0,
        status: draft.status,
        notes_ja: draft.notes_ja || null,
        notes_en: draft.notes_en || null,
        expires_at: draft.expires_at ? `${draft.expires_at}T00:00:00Z` : null,
      };
      await api.patch(`/super-admin/inventory-offers/${editing.id}`, body);
      setInfo(t("superAdmin.inventoryOffers.updateSuccess"));
      setEditing(null);
      setDraft(null);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.operationError"));
    } finally {
      setSubmitting(false);
    }
  };

  const bulkDelete = async () => {
    setConfirmDelete(false);
    setError("");
    setInfo("");
    // 一部失敗しても残りは削除し、最後に必ず一覧を再取得して整合させる。
    const results = await Promise.allSettled(
      Array.from(selectedIds).map((id) => api.delete(`/super-admin/inventory-offers/${id}`)),
    );
    const failed = results.filter((r) => r.status === "rejected");
    if (failed.length === 0) {
      setInfo(t("superAdmin.inventoryOffers.deleteSuccess"));
    } else if (failed.every((r) => r.reason instanceof ApiError && r.reason.status === 404)) {
      setError(t("superAdmin.inventoryOffers.notFound"));
    } else {
      setError(t("common.operationError"));
    }
    setSelectedIds(new Set());
    await load();
  };

  const c = "superAdmin.inventoryOffers.col";

  if (superAdminLoading) {
    return (
      <PageLayout navKey="nav.superAdminInventoryOffers">
        <div>{t("common.loading")}</div>
      </PageLayout>
    );
  }

  if (!isSuperAdmin) {
    return (
      <PageLayout
        navKey="nav.superAdminInventoryOffers"
        subtitleKey="superAdmin.subtitle"
      >
        <div className="error-message" role="alert">
          {t("superAdmin.accessDenied")}
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout
      navKey="nav.superAdminInventoryOffers"
      subtitleKey="superAdmin.inventoryOffers.subtitle"
    >
      {error && (
        <div className="error-message" role="alert" data-testid="offers-error">
          {error}
        </div>
      )}
      {info && (
        <div className="info-message" role="status" data-testid="offers-info">
          {info}
        </div>
      )}

      <section
        className="offers-filter"
        style={{
          display: "flex",
          gap: "var(--space-2)",
          flexWrap: "wrap",
          alignItems: "center",
          marginBottom: "var(--space-4)",
          position: "sticky",
          top: 0,
          background: "var(--bg-base)",
          paddingTop: "var(--space-2)",
          paddingBottom: "var(--space-2)",
          zIndex: 1,
        }}
      >
        <input
          type="search"
          placeholder={t("superAdmin.inventoryOffers.searchPlaceholder")}
          data-testid="offers-search"
          value={searchQ}
          onChange={(e) => {
            setSearchQ(e.target.value);
            setPage(1);
          }}
          style={{ minWidth: "18rem" }}
        />
        <select
          data-testid="offers-status-filter"
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value as InventoryStatus | "");
            setPage(1);
          }}
        >
          <option value="">{t("superAdmin.inventoryOffers.statusAny")}</option>
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {t(`superAdmin.inventoryOffers.status.${s}`)}
            </option>
          ))}
        </select>
        <input
          type="text"
          placeholder={t("superAdmin.inventoryOffers.conditionPlaceholder")}
          data-testid="offers-condition-filter"
          value={conditionFilter}
          onChange={(e) => {
            setConditionFilter(e.target.value);
            setPage(1);
          }}
          style={{ width: "10rem" }}
        />
        {/* 一括削除: チェックした行をまとめて削除 */}
        <button
          type="button"
          className="btn-danger btn-sm"
          data-testid="offers-bulk-delete"
          disabled={selectedIds.size === 0}
          onClick={() => setConfirmDelete(true)}
          style={{ marginLeft: "auto" }}
        >
          {t("common.delete")}
        </button>
      </section>

      {/* レイアウトシフト防止: loading 中も DOM に残し、visibility だけ切り替える */}
      <div
        className="loading-indicator"
        data-testid="offers-loading"
        aria-live="polite"
        aria-hidden={!loading}
        style={{
          minHeight: "1.5rem",
          visibility: loading ? "visible" : "hidden",
        }}
      >
        {t("common.loading")}
      </div>

      <div style={{ overflowX: "auto" }}>
        <table
          className="data-table offers-table-styled"
          data-testid="offers-table"
          aria-busy={loading}
        >
          <thead>
            <tr>
              <th style={{ width: "var(--col-width-checkbox)", textAlign: "center" }} aria-label={t("common.select")}></th>
              <th>{t(`${c}.category`)}</th>
              <th>{t(`${c}.mark`)}</th>
              <th>{t(`${c}.product`)}</th>
              <th>{t(`${c}.condition`)}</th>
              <th>{t(`${c}.unit`)}</th>
              <th>{t(`${c}.offerType`)}</th>
              <th style={{ textAlign: "right" }}>{t(`${c}.quantity`)}</th>
              <th style={{ textAlign: "right" }}>{t(`${c}.unitPrice`)}</th>
              <th>{t(`${c}.supplier`)}</th>
              <th>{t(`${c}.status`)}</th>
              <th>{t(`${c}.source`)}</th>
              <th>{t(`${c}.expiresAt`)}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td colSpan={14} data-testid="offers-empty">
                  {t("superAdmin.inventoryOffers.noResults")}
                </td>
              </tr>
            ) : (
              items.map((o) => (
                <tr key={o.id} data-testid={`offers-row-${o.id}`}>
                  <td style={{ textAlign: "center" }}>
                    <input
                      type="checkbox"
                      checked={selectedIds.has(o.id)}
                      onChange={() => toggleSelect(o.id)}
                      aria-label={o.product_name ?? `#${o.product_id}`}
                      data-testid={`offers-row-${o.id}-select`}
                    />
                  </td>
                  <td>
                    {o.category || o.tcg_type ? (
                      <span className="badge">{categoryLabel(o)}</span>
                    ) : (
                      "-"
                    )}
                  </td>
                  <td>{o.mark ?? "-"}</td>
                  <td>
                    <div style={{ fontWeight: "var(--font-weight-semi)" }}>
                      {o.product_name ?? `#${o.product_id}`}
                    </div>
                    {o.name_en && (
                      <div style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>
                        {o.name_en}
                      </div>
                    )}
                  </td>
                  <td>{t(`inventory.condition.${o.condition}`, { defaultValue: o.condition })}</td>
                  <td>{o.unit ? t(`inventory.unit.${o.unit}`, { defaultValue: o.unit }) : "-"}</td>
                  <td>
                    {o.offer_type === "pre_order" ? (
                      <span className="badge badge-negotiating">{t("inventory.offerType.pre_order")}</span>
                    ) : (
                      t("inventory.offerType.in_stock")
                    )}
                    {o.offer_type === "pre_order" && o.ship_timing && (
                      <div style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>
                        {t(`inventory.shipTiming.${o.ship_timing}`, { defaultValue: o.ship_timing })}
                      </div>
                    )}
                  </td>
                  <td style={{ textAlign: "right" }}>{o.quantity}</td>
                  <td style={{ textAlign: "right" }}>{o.unit_price.toLocaleString()}</td>
                  <td>
                    <div>{o.supplier_name ?? `#${o.supplier_id}`}</div>
                    <div style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>
                      {fmtOfferedAt(o.offered_at)}
                    </div>
                  </td>
                  <td>{t(`superAdmin.inventoryOffers.status.${o.status}`)}</td>
                  <td>
                    <span data-testid={`offers-row-${o.id}-source`}>
                      {t(`superAdmin.inventoryOffers.source.${o.source}`, o.source)}
                    </span>
                  </td>
                  <td>{o.expires_at ? o.expires_at.slice(0, 10) : "—"}</td>
                  <td style={{ textAlign: "right" }}>
                    <button
                      type="button"
                      className="btn-sm"
                      onClick={() => openEdit(o)}
                      data-testid={`offers-row-${o.id}-edit`}
                    >
                      {t("common.edit")}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <section
        className="offers-pagination"
        style={{
          marginTop: "var(--space-4)",
          marginBottom: "var(--space-6)",
          display: "flex",
          gap: "var(--space-2)",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <button
          onClick={() => setPage(Math.max(1, page - 1))}
          disabled={page <= 1 || loading}
          data-testid="offers-prev"
          className="btn-secondary"
        >
          {t("common.previous")}
        </button>
        <span data-testid="offers-pagination-label">
          {t("superAdmin.inventoryOffers.pageOf", {
            page,
            total: totalPages,
            count: total,
          })}
        </span>
        <button
          onClick={() => setPage(Math.min(totalPages, page + 1))}
          disabled={page >= totalPages || loading}
          data-testid="offers-next"
          className="btn-secondary"
        >
          {t("common.next")}
        </button>
      </section>

      {/* 編集ポップアップ */}
      {editing && draft && (
        <div className="modal-overlay" onClick={cancelEdit}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "min(96vw, 560px)" }}>
            <h3>{t("common.edit")}</h3>
            <div style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)", marginBottom: "var(--space-3)" }}>
              {editing.product_name ?? `#${editing.product_id}`}
              {" / "}
              {editing.supplier_name ?? `#${editing.supplier_id}`}
            </div>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void submitEdit();
              }}
            >
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-3) var(--space-4)" }}>
                <div className="form-group">
                  <label>{t(`${c}.quantity`)}</label>
                  <input
                    type="number"
                    min="0"
                    data-testid="offers-edit-quantity"
                    value={draft.quantity}
                    onChange={(e) => setDraft({ ...draft, quantity: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>{t(`${c}.unitPrice`)}</label>
                  <input
                    type="number"
                    min="0"
                    data-testid="offers-edit-unit-price"
                    value={draft.unit_price}
                    onChange={(e) => setDraft({ ...draft, unit_price: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>{t(`${c}.status`)}</label>
                  <select
                    data-testid="offers-edit-status"
                    value={draft.status}
                    onChange={(e) => setDraft({ ...draft, status: e.target.value as InventoryStatus })}
                  >
                    {STATUS_OPTIONS.map((s) => (
                      <option key={s} value={s}>
                        {t(`superAdmin.inventoryOffers.status.${s}`)}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>{t(`${c}.expiresAt`)}</label>
                  <input
                    type="date"
                    data-testid="offers-edit-expires-at"
                    value={draft.expires_at}
                    onChange={(e) => setDraft({ ...draft, expires_at: e.target.value })}
                  />
                </div>
                <div className="form-group" style={{ gridColumn: "1 / -1" }}>
                  <label>{t("superAdmin.inventoryOffers.notesJa")}</label>
                  <input
                    type="text"
                    data-testid="offers-edit-notes-ja"
                    value={draft.notes_ja}
                    onChange={(e) => setDraft({ ...draft, notes_ja: e.target.value })}
                  />
                </div>
                <div className="form-group" style={{ gridColumn: "1 / -1" }}>
                  <label>{t("superAdmin.inventoryOffers.notesEn")}</label>
                  <input
                    type="text"
                    data-testid="offers-edit-notes-en"
                    value={draft.notes_en}
                    onChange={(e) => setDraft({ ...draft, notes_en: e.target.value })}
                  />
                </div>
              </div>
              <div className="form-actions">
                <button type="button" className="btn-secondary" onClick={cancelEdit}>
                  {t("common.cancel")}
                </button>
                <button type="submit" className="btn-primary" disabled={submitting} data-testid="offers-edit-save">
                  {t("common.save")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <ConfirmModal
        open={confirmDelete}
        title={t("common.delete")}
        message={t("superAdmin.inventoryOffers.bulkDeleteConfirm", { count: selectedIds.size })}
        confirmLabel={t("common.delete")}
        danger
        onConfirm={() => void bulkDelete()}
        onCancel={() => setConfirmDelete(false)}
      />
    </PageLayout>
  );
}
