/**
 * /super-admin/masters — 「各種マスタ」タブ。
 *
 * 商品マスタの選択肢系マスタ（プルダウン候補）を UI から追加・編集・削除する。
 *   - 8 区分は public.product_attribute_masters (汎用マスタ) で管理:
 *       商品種類 / セット種別 / レアリティ / 言語 / 単位 / HSコード / 品目 / 素材
 *   - TCGシリーズは既存の TcgSeriesTab（public.tcg_type_master / tcg_series_master）を
 *     そのまま埋め込み、二重管理を避ける。
 *
 * API: /super-admin/product-masters (require_super_admin)
 */
import { useEffect, useState, FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import TcgSeriesTab from "./TcgSeriesTab";

interface AttributeMaster {
  id: number;
  attribute: string;
  code: string | null;
  label_ja: string;
  label_en: string | null;
  sort_order: number;
  is_active: boolean;
}

// 各種マスタの区分（表示順）。tcg_series のみ別コンポーネントに委譲する特別扱い。
const ATTRIBUTES = [
  { key: "product_kind", labelKey: "superAdmin.attrMasters.attr.productKind" },
  { key: "set_type", labelKey: "superAdmin.attrMasters.attr.setType" },
  { key: "tcg_series", labelKey: "superAdmin.attrMasters.attr.tcgSeries" },
  { key: "rarity", labelKey: "superAdmin.attrMasters.attr.rarity" },
  { key: "language", labelKey: "superAdmin.attrMasters.attr.language" },
  { key: "unit", labelKey: "superAdmin.attrMasters.attr.unit" },
  { key: "hs_code", labelKey: "superAdmin.attrMasters.attr.hsCode" },
  { key: "item", labelKey: "superAdmin.attrMasters.attr.item" },
  { key: "material", labelKey: "superAdmin.attrMasters.attr.material" },
] as const;

const emptyForm = { code: "", label_ja: "", label_en: "", sort_order: "100" };

/** 汎用マスタ（product_attribute_masters）1 区分の編集 UI。 */
function GenericAttributeEditor({ attribute }: { attribute: string }) {
  const { t } = useTranslation();
  const [items, setItems] = useState<AttributeMaster[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [editId, setEditId] = useState<number | null>(null);
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const data = await api.get<AttributeMaster[]>(
        `/super-admin/product-masters?attribute=${encodeURIComponent(attribute)}`,
      );
      setItems(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    }
  };

  useEffect(() => {
    setEditId(null);
    setForm(emptyForm);
    setError("");
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attribute]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    const payload = {
      attribute,
      code: form.code.trim() || null,
      label_ja: form.label_ja.trim(),
      label_en: form.label_en.trim() || null,
      sort_order: Number(form.sort_order) || 100,
      is_active: true,
    };
    try {
      if (editId) {
        await api.patch(`/super-admin/product-masters/${editId}`, {
          code: payload.code,
          label_ja: payload.label_ja,
          label_en: payload.label_en,
          sort_order: payload.sort_order,
        });
      } else {
        await api.post("/super-admin/product-masters", payload);
      }
      setEditId(null);
      setForm(emptyForm);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.saveError"));
    }
  };

  const startEdit = (m: AttributeMaster) => {
    setEditId(m.id);
    setForm({
      code: m.code || "",
      label_ja: m.label_ja,
      label_en: m.label_en || "",
      sort_order: String(m.sort_order),
    });
  };

  const cancelEdit = () => {
    setEditId(null);
    setForm(emptyForm);
  };

  const toggleActive = async (m: AttributeMaster) => {
    setError("");
    try {
      await api.patch(`/super-admin/product-masters/${m.id}`, {
        is_active: !m.is_active,
      });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    }
  };

  const remove = async (id: number) => {
    setError("");
    try {
      await api.delete(`/super-admin/product-masters/${id}`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.deleteError"));
    }
  };

  return (
    <div data-testid={`attr-editor-${attribute}`}>
      {error && <div className="error-message">{error}</div>}

      <form
        onSubmit={submit}
        style={{
          display: "grid",
          gridTemplateColumns: "1.5fr 1.5fr 1fr 0.7fr auto auto",
          gap: "var(--space-2)",
          alignItems: "center",
          margin: "0.5rem 0",
        }}
      >
        <input
          placeholder={t("superAdmin.attrMasters.col.labelJa")}
          aria-label={t("superAdmin.attrMasters.col.labelJa")}
          value={form.label_ja}
          onChange={(e) => setForm({ ...form, label_ja: e.target.value })}
          required
        />
        <input
          placeholder={t("superAdmin.attrMasters.col.labelEn")}
          aria-label={t("superAdmin.attrMasters.col.labelEn")}
          value={form.label_en}
          onChange={(e) => setForm({ ...form, label_en: e.target.value })}
        />
        <input
          placeholder={t("superAdmin.attrMasters.col.code")}
          aria-label={t("superAdmin.attrMasters.col.code")}
          value={form.code}
          onChange={(e) => setForm({ ...form, code: e.target.value })}
        />
        <input
          type="number"
          placeholder={t("superAdmin.attrMasters.col.sortOrder")}
          aria-label={t("superAdmin.attrMasters.col.sortOrder")}
          value={form.sort_order}
          onChange={(e) => setForm({ ...form, sort_order: e.target.value })}
        />
        <button type="submit" className="btn-primary">
          {editId ? t("common.update") : t("superAdmin.attrMasters.addBtn")}
        </button>
        {editId ? (
          <button type="button" className="btn-secondary" onClick={cancelEdit}>
            {t("common.cancel")}
          </button>
        ) : (
          <span />
        )}
      </form>

      <table className="data-table">
        <thead>
          <tr>
            <th>{t("superAdmin.attrMasters.col.labelJa")}</th>
            <th>{t("superAdmin.attrMasters.col.labelEn")}</th>
            <th>{t("superAdmin.attrMasters.col.code")}</th>
            <th style={{ width: "1%", whiteSpace: "nowrap", textAlign: "right" }}>
              {t("superAdmin.attrMasters.col.sortOrder")}
            </th>
            <th style={{ width: "1%", whiteSpace: "nowrap" }}>
              {t("superAdmin.attrMasters.col.active")}
            </th>
            <th style={{ width: "1%", whiteSpace: "nowrap" }}>{t("common.edit")}</th>
            <th style={{ width: "1%", whiteSpace: "nowrap" }}>{t("common.delete")}</th>
          </tr>
        </thead>
        <tbody>
          {items.length === 0 ? (
            <tr>
              <td colSpan={7} className="empty">
                {t("superAdmin.attrMasters.empty")}
              </td>
            </tr>
          ) : (
            items.map((m) => (
              <tr key={m.id} style={{ opacity: m.is_active ? 1 : 0.5 }}>
                <td>{m.label_ja}</td>
                <td>{m.label_en}</td>
                <td>
                  <code style={{ color: "var(--text-muted)" }}>{m.code || "-"}</code>
                </td>
                <td style={{ textAlign: "right" }}>{m.sort_order}</td>
                <td>
                  <button
                    type="button"
                    className="btn-secondary btn-sm"
                    onClick={() => toggleActive(m)}
                    aria-label={`${t("superAdmin.attrMasters.col.active")} ${m.label_ja}`}
                  >
                    {m.is_active
                      ? t("superAdmin.attrMasters.activeOn")
                      : t("superAdmin.attrMasters.activeOff")}
                  </button>
                </td>
                <td>
                  <button className="btn-secondary" onClick={() => startEdit(m)}>
                    {t("common.edit")}
                  </button>
                </td>
                <td>
                  <button className="btn-danger-link" onClick={() => remove(m.id)}>
                    {t("common.delete")}
                  </button>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export default function ProductMastersTab() {
  const { t } = useTranslation();
  const [attr, setAttr] = useState<string>(ATTRIBUTES[0].key);

  return (
    <div className="product-masters-tab">
      <h3>{t("superAdmin.attrMasters.title")}</h3>
      <p style={{ color: "var(--text-secondary)", fontSize: "var(--font-sm)", marginTop: 0 }}>
        {t("superAdmin.attrMasters.desc")}
      </p>

      {/* 区分セレクタ（商品種類 / セット種別 / TCGシリーズ / レアリティ / 言語 / 単位 / HSコード / 品目 / 素材） */}
      <div
        role="tablist"
        aria-label={t("superAdmin.attrMasters.title")}
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "var(--space-2)",
          margin: "0.5rem 0 1rem",
        }}
      >
        {ATTRIBUTES.map((a) => (
          <button
            key={a.key}
            role="tab"
            aria-selected={attr === a.key}
            className={attr === a.key ? "btn-primary" : "btn-secondary"}
            onClick={() => setAttr(a.key)}
            style={{ padding: "var(--space-1) var(--space-3)" }}
            data-testid={`attr-master-tab-${a.key}`}
          >
            {t(a.labelKey)}
          </button>
        ))}
      </div>

      <div role="tabpanel">
        {attr === "tcg_series" ? (
          <TcgSeriesTab />
        ) : (
          <GenericAttributeEditor attribute={attr} />
        )}
      </div>
    </div>
  );
}
