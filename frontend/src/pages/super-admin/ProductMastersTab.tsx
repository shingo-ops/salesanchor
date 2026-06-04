/**
 * /super-admin/masters — 「各種マスタ」タブ。
 *
 * 商品マスタの選択肢（プルダウン候補）を「名称（日本語）」「名称（英語）」のみで
 * 追加・編集・削除する。各区分とも UI は統一:
 *   検索窓 + 検索ボタン / 名称 ja・en の追加フォーム / 行ごとに編集・削除 /
 *   行のドラッグで並び替え（sort_order を更新）。
 *
 * データ源:
 *   - 8 区分（商品種類/セット種別/レアリティ/言語/単位/HSコード/品目/素材）
 *     → public.product_attribute_masters（/super-admin/product-masters）
 *   - TCGシリーズ → public.tcg_type_master（/super-admin/tcg/types）
 *     ※ 種別(ポケモンカード等)を名称のみで管理。code は内部自動採番で UI 非表示。
 */
import { useEffect, useRef, useState, FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";

interface MasterRow {
  id: number;
  name_ja: string;
  name_en: string | null;
}

/** 1 区分の CRUD + 並び替えを抽象化したデータ源。 */
interface MasterDataSource {
  list: () => Promise<MasterRow[]>;
  create: (nameJa: string, nameEn: string | null) => Promise<void>;
  update: (id: number, nameJa: string, nameEn: string | null) => Promise<void>;
  remove: (id: number) => Promise<void>;
  reorder: (orderedIds: number[]) => Promise<void>;
}

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

interface AttributeMasterApi {
  id: number;
  label_ja: string;
  label_en: string | null;
  sort_order: number;
}

/** public.product_attribute_masters を name_ja/name_en にマップしたデータ源。 */
function attributeSource(attribute: string): MasterDataSource {
  const base = "/super-admin/product-masters";
  return {
    list: async () => {
      const rows = await api.get<AttributeMasterApi[]>(
        `${base}?attribute=${encodeURIComponent(attribute)}`,
      );
      return rows.map((r) => ({ id: r.id, name_ja: r.label_ja, name_en: r.label_en }));
    },
    create: async (nameJa, nameEn) => {
      await api.post(base, { attribute, label_ja: nameJa, label_en: nameEn, sort_order: 1000 });
    },
    update: async (id, nameJa, nameEn) => {
      await api.patch(`${base}/${id}`, { label_ja: nameJa, label_en: nameEn });
    },
    remove: async (id) => {
      await api.delete(`${base}/${id}`);
    },
    reorder: async (orderedIds) => {
      await Promise.all(
        orderedIds.map((id, i) => api.patch(`${base}/${id}`, { sort_order: (i + 1) * 10 })),
      );
    },
  };
}

interface TcgTypeApi {
  id: number;
  name_ja: string;
  name_en: string | null;
  sort_order: number;
}

/** public.tcg_type_master（TCG 種別）を name_ja/name_en で管理するデータ源。 */
const tcgTypeSource: MasterDataSource = {
  list: async () => {
    const rows = await api.get<TcgTypeApi[]>("/super-admin/tcg/types");
    return rows.map((r) => ({ id: r.id, name_ja: r.name_ja, name_en: r.name_en }));
  },
  create: async (nameJa, nameEn) => {
    // code は backend が自動採番（UI 非入力）。
    await api.post("/super-admin/tcg/types", {
      name_ja: nameJa, name_en: nameEn, sort_order: 1000, is_active: true,
    });
  },
  update: async (id, nameJa, nameEn) => {
    await api.patch(`/super-admin/tcg/types/${id}`, { name_ja: nameJa, name_en: nameEn });
  },
  remove: async (id) => {
    await api.delete(`/super-admin/tcg/types/${id}`);
  },
  reorder: async (orderedIds) => {
    await Promise.all(
      orderedIds.map((id, i) => api.patch(`/super-admin/tcg/types/${id}`, { sort_order: (i + 1) * 10 })),
    );
  },
};

const emptyForm = { name_ja: "", name_en: "" };

/** 名称(ja/en)のみのマスタ一覧編集 UI（検索 + 追加 + 編集 + 削除 + ドラッグ並び替え）。 */
function MasterListEditor({ source }: { source: MasterDataSource }) {
  const { t } = useTranslation();
  const [rows, setRows] = useState<MasterRow[]>([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [editId, setEditId] = useState<number | null>(null);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const dragId = useRef<number | null>(null);

  const load = async () => {
    try {
      setRows(await source.list());
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    }
  };

  // 親が key={attr} で再マウントするため、マウント時に 1 回読み込めばよい。
  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    const nameJa = form.name_ja.trim();
    const nameEn = form.name_en.trim() || null;
    if (!nameJa) return;
    try {
      if (editId) await source.update(editId, nameJa, nameEn);
      else await source.create(nameJa, nameEn);
      setEditId(null);
      setForm(emptyForm);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.saveError"));
    }
  };

  const startEdit = (r: MasterRow) => {
    setEditId(r.id);
    setForm({ name_ja: r.name_ja, name_en: r.name_en || "" });
  };
  const cancelEdit = () => {
    setEditId(null);
    setForm(emptyForm);
  };
  const remove = async (id: number) => {
    setError("");
    try {
      await source.remove(id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.deleteError"));
    }
  };

  // 行ドラッグで並び替え → sort_order を一括更新。
  const onDrop = async (targetId: number) => {
    const from = dragId.current;
    dragId.current = null;
    if (from == null || from === targetId) return;
    const cur = [...rows];
    const fromIdx = cur.findIndex((r) => r.id === from);
    const toIdx = cur.findIndex((r) => r.id === targetId);
    if (fromIdx < 0 || toIdx < 0) return;
    const [moved] = cur.splice(fromIdx, 1);
    cur.splice(toIdx, 0, moved);
    setRows(cur); // 楽観的更新
    try {
      await source.reorder(cur.map((r) => r.id));
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
      await load();
    }
  };

  const q = search.toLowerCase();
  const filtered = q
    ? rows.filter(
        (r) =>
          r.name_ja.toLowerCase().includes(q) ||
          (r.name_en ?? "").toLowerCase().includes(q),
      )
    : rows;
  // 検索で部分表示中はドラッグ並び替えを無効化（順序が崩れるため）。
  const canDrag = !search;

  return (
    <div>
      {error && <div className="error-message">{error}</div>}

      {/* 検索 */}
      <form
        className="search-bar"
        style={{ display: "flex", gap: "var(--space-2)", alignItems: "center" }}
        onSubmit={(e) => {
          e.preventDefault();
          setSearch(searchInput.trim());
        }}
      >
        <input
          type="text"
          placeholder={t("superAdmin.attrMasters.searchPlaceholder")}
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
        />
        <button type="submit" className="btn-secondary">{t("common.search")}</button>
        {search && (
          <button type="button" className="btn-sm" onClick={() => { setSearch(""); setSearchInput(""); }}>
            {t("common.clear")}
          </button>
        )}
      </form>

      {/* 追加 / 編集フォーム（名称のみ） */}
      <form
        onSubmit={submit}
        style={{ display: "grid", gridTemplateColumns: "1fr 1fr auto auto", gap: "var(--space-2)", margin: "0.5rem 0" }}
      >
        <input
          placeholder={t("superAdmin.attrMasters.col.labelJa")}
          aria-label={t("superAdmin.attrMasters.col.labelJa")}
          value={form.name_ja}
          onChange={(e) => setForm({ ...form, name_ja: e.target.value })}
          required
        />
        <input
          placeholder={t("superAdmin.attrMasters.col.labelEn")}
          aria-label={t("superAdmin.attrMasters.col.labelEn")}
          value={form.name_en}
          onChange={(e) => setForm({ ...form, name_en: e.target.value })}
        />
        <button type="submit" className="btn-primary">
          {editId ? t("common.update") : t("superAdmin.attrMasters.addBtn")}
        </button>
        {editId ? (
          <button type="button" className="btn-secondary" onClick={cancelEdit}>{t("common.cancel")}</button>
        ) : (
          <span />
        )}
      </form>

      {/* 一覧 */}
      <table className="data-table">
        <thead>
          <tr>
            <th>{t("superAdmin.attrMasters.col.labelJa")}</th>
            <th>{t("superAdmin.attrMasters.col.labelEn")}</th>
            <th style={{ width: "1%", whiteSpace: "nowrap" }}>{t("common.edit")}</th>
            <th style={{ width: "1%", whiteSpace: "nowrap" }}>{t("common.delete")}</th>
          </tr>
        </thead>
        <tbody>
          {filtered.length === 0 ? (
            <tr>
              <td colSpan={4} className="empty">{t("superAdmin.attrMasters.empty")}</td>
            </tr>
          ) : (
            filtered.map((r) => (
              <tr
                key={r.id}
                data-testid={`master-row-${r.id}`}
                draggable={canDrag}
                onDragStart={canDrag ? () => { dragId.current = r.id; } : undefined}
                onDragOver={canDrag ? (e) => e.preventDefault() : undefined}
                onDrop={canDrag ? () => onDrop(r.id) : undefined}
                style={canDrag ? { cursor: "grab" } : undefined}
              >
                <td>{r.name_ja}</td>
                <td>{r.name_en}</td>
                <td>
                  <button className="btn-secondary btn-sm" onClick={() => startEdit(r)}>{t("common.edit")}</button>
                </td>
                <td>
                  <button className="btn-danger btn-sm" onClick={() => remove(r.id)}>{t("common.delete")}</button>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
      {canDrag && filtered.length > 1 && (
        <p style={{ color: "var(--text-muted)", fontSize: "var(--font-xs)", marginTop: "var(--space-1)" }}>
          {t("superAdmin.attrMasters.reorderHint")}
        </p>
      )}
    </div>
  );
}

export default function ProductMastersTab() {
  const { t } = useTranslation();
  const [attr, setAttr] = useState<string>(ATTRIBUTES[0].key);
  const source = attr === "tcg_series" ? tcgTypeSource : attributeSource(attr);

  return (
    <div className="product-masters-tab">
      <h3>{t("superAdmin.attrMasters.title")}</h3>
      <p style={{ color: "var(--text-secondary)", fontSize: "var(--font-sm)", marginTop: 0 }}>
        {t("superAdmin.attrMasters.desc")}
      </p>

      <div
        role="tablist"
        aria-label={t("superAdmin.attrMasters.title")}
        style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)", margin: "0.5rem 0 1rem" }}
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

      {/* key={attr} で区分切替時に内部 state をリセット（再マウント） */}
      <MasterListEditor key={attr} source={source} />
    </div>
  );
}
