/**
 * MasterListEditor — 名称(ja/en)のみのマスタ一覧編集 UI。
 *
 * 検索 + 追加 + 編集 + 削除 + ドラッグ並び替えを統一金型として提供する。
 * データ源は `MasterDataSource` インターフェース経由で差し替え可能。
 */
import { useEffect, useRef, useState, FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { ContentToolbar } from "../ContentToolbar";

export interface MasterRow {
  id: number;
  name_ja: string;
  name_en: string | null;
}

/** 1 区分の CRUD + 並び替えを抽象化したデータ源。 */
export interface MasterDataSource {
  list: () => Promise<MasterRow[]>;
  create: (nameJa: string, nameEn: string | null) => Promise<void>;
  update: (id: number, nameJa: string, nameEn: string | null) => Promise<void>;
  remove: (id: number) => Promise<void>;
  reorder: (orderedIds: number[]) => Promise<void>;
}

const emptyForm = { name_ja: "", name_en: "" };

/** 名称(ja/en)のみのマスタ一覧編集 UI（検索 + 追加 + 編集 + 削除 + ドラッグ並び替え）。 */
export function MasterListEditor({ source }: { source: MasterDataSource }) {
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
      <ContentToolbar
        left={
          <form
            className="search-bar"
            style={{ display: "flex", gap: "var(--space-2)", alignItems: "center" }}
            onSubmit={(e) => {
              e.preventDefault();
              setSearch(searchInput.trim());
            }}
          >
            <input
              className="field-h-md field-w-sm"
              type="text"
              placeholder={t("superAdmin.attrMasters.searchPlaceholder")}
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
            />
            <button type="submit" className="btn-secondary field-h-md">{t("common.search")}</button>
            {search && (
              <button type="button" className="btn-sm" onClick={() => { setSearch(""); setSearchInput(""); }}>
                {t("common.clear")}
              </button>
            )}
          </form>
        }
      />

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
