/**
 * ProductFormatsMasterPanel — 商品形態マスタパネル（AnalysisRulesPage の hub-content 内で使用）
 *
 * ADR-027: 全UI文字列は t("key") 経由。
 * ADR-144: 金型クラスのみ使用。
 */
import { useCallback, useEffect, useRef, useState, FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { api, ApiError } from "../../../lib/api";
import { ContentToolbar } from "../../../components/ContentToolbar";
import { Checkbox } from "../../../components/Checkbox";
import { HeaderButton } from "../../../components/HeaderButton";
import { DataTable, type DataTableColumn } from "../../../components/DataTable";
import { EmptyState } from "../../../components/EmptyState";
import { TextField } from "../../../components/TextField";
import { Drawer } from "../../../components/Drawer";
import ConfirmModal from "../../../components/ConfirmModal";
import { Callout } from "../../../components/Callout";
import { SelectControl } from "../../../components/Select";
import { STATUS_ICONS } from "../../../constants/icons";
import { ICON } from "../../../constants/iconSizes";

interface ProductLine {
  id: number;
  code: string;
  name: string;
}

interface TcgType {
  id: number;
  code: string;
  name_ja: string;
  name_en: string | null;
  is_active: boolean;
}

interface ProductFormat {
  id: number;
  code: string;
  name: string;
  name_en: string | null;
  line_id: number | null;
  display_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  game_ids: number[];
}

type FormatFormState = {
  code: string;
  name: string;
  name_en: string;
  line_id: number | null;
  display_order: number;
  is_active: boolean;
  game_ids: string[];
};

const emptyForm: FormatFormState = {
  code: "",
  name: "",
  name_en: "",
  line_id: null,
  display_order: 100,
  is_active: true,
  game_ids: [],
};

const PER_PAGE = 200;
// 一覧の「使えるゲーム」列で名前を出す件数と区切り
const GAME_PREVIEW_COUNT = 3;
const GAME_SEPARATOR = ", ";

export function ProductFormatsMasterPanel() {
  const { t } = useTranslation();
  const f = "productFormatsMaster";

  const [items, setItems] = useState<ProductFormat[]>([]);
  const [lines, setLines] = useState<ProductLine[]>([]);
  const [tcgTypes, setTcgTypes] = useState<TcgType[]>([]);
  const [error, setError] = useState("");
  const [gameFilter, setGameFilter] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<FormatFormState>(emptyForm);
  const [editId, setEditId] = useState<number | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);
  // ADR-1020: 開いたときの「使えるゲーム」（変わったときだけ PUT するため）
  const [savedGameIds, setSavedGameIds] = useState<string[]>([]);

  const formRef = useRef<HTMLFormElement>(null);

  const load = useCallback(async () => {
    try {
      const data = await api.get<ProductFormat[]>("/super-admin/product-formats");
      setItems(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    }
  }, [t]);

  const loadLines = useCallback(async () => {
    try {
      const data = await api.get<ProductLine[]>("/super-admin/product-lines");
      setLines(data);
    } catch {
      // 選択肢取得失敗は無視（空選択肢として表示）
    }
  }, []);

  const loadTcgTypes = useCallback(async () => {
    try {
      const data = await api.get<TcgType[]>("/super-admin/tcg/types");
      setTcgTypes(data);
    } catch {
      // 選択肢取得失敗は無視（空選択肢として表示）
    }
  }, []);

  useEffect(() => {
    void load();
    void loadLines();
    void loadTcgTypes();
  }, [load, loadLines, loadTcgTypes]);

  const openCreate = () => { setEditId(null); setForm(emptyForm); setSavedGameIds([]); setError(""); setShowForm(true); };
  const openEdit = (item: ProductFormat) => {
    setEditId(item.id);
    setForm({
      code: item.code,
      name: item.name,
      name_en: item.name_en || "",
      line_id: item.line_id,
      display_order: item.display_order,
      is_active: item.is_active,
      game_ids: item.game_ids.map(String),
    });
    setSavedGameIds(item.game_ids.map(String).sort());
    setError("");
    setShowForm(true);
  };

  // ADR-1020: 使えるゲームの置き換えで返る理由を、分かる文言にする
  const errorMessage = (err: unknown, fallback: string) => {
    if (err instanceof ApiError && err.status === 409 && err.message === "PRODUCT_FORMAT_GAME_IN_USE") return t(`${f}.gamesInUse`);
    if (err instanceof ApiError && err.status === 422 && err.message === "PRODUCT_FORMAT_GAME_UNKNOWN") return t(`${f}.gamesUnknown`);
    return err instanceof Error ? err.message : fallback;
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    const payload = {
      code: form.code,
      name: form.name,
      name_en: form.name_en || null,
      line_id: form.line_id,
      display_order: form.display_order,
      is_active: form.is_active,
    };
    const wanted = [...form.game_ids].sort();
    let targetId = editId;
    try {
      if (targetId) {
        await api.patch(`/super-admin/product-formats/${targetId}`, payload);
      } else {
        const created = await api.post<ProductFormat>("/super-admin/product-formats", payload);
        targetId = created.id;
        setEditId(created.id);
        setSavedGameIds([]);
      }
      const before = editId ? savedGameIds : [];
      if (wanted.join(",") !== before.join(",")) {
        await api.put(`/super-admin/product-formats/${targetId}/games`, {
          game_ids: wanted.map(Number).sort((a, b) => a - b),
        });
      }
      setShowForm(false);
      setForm(emptyForm);
      setEditId(null);
      setSavedGameIds([]);
      await load();
    } catch (err) {
      setError(errorMessage(err, t("common.saveError")));
      await load();
    }
  };

  const confirmDelete = async () => {
    if (confirmDeleteId === null) return;
    setError("");
    try {
      await api.delete(`/super-admin/product-formats/${confirmDeleteId}`);
      setConfirmDeleteId(null);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.deleteError"));
      setConfirmDeleteId(null);
    }
  };

  const getLineName = (id: number | null) => {
    if (id === null) return "-";
    return lines.find(l => l.id === id)?.name ?? String(id);
  };

  const getGameName = (id: number | null) => {
    if (id === null) return "-";
    const found = tcgTypes.find(t => t.id === id);
    return found ? found.name_ja : String(id);
  };

  // tcgTypes（API は sort_order 順）の並びに揃える。tcgTypes に無い id は末尾
  const sortGameIds = (ids: number[]) => {
    const rank = (id: number) => {
      const i = tcgTypes.findIndex(g => g.id === id);
      return i === -1 ? tcgTypes.length : i;
    };
    return [...ids].sort((a, b) => rank(a) - rank(b));
  };

  const renderGames = (ids: number[]) => {
    if (ids.length === 0) return "-";
    const sorted = sortGameIds(ids);
    const preview = sorted.slice(0, GAME_PREVIEW_COUNT).map(id => getGameName(id)).join(GAME_SEPARATOR);
    const rest = sorted.length - GAME_PREVIEW_COUNT;
    const all = sorted.map(id => getGameName(id)).join(GAME_SEPARATOR);
    return (
      <span title={all}>
        {rest > 0 ? `${preview}${GAME_SEPARATOR}${t(`${f}.gamesMore`, { count: rest })}` : preview}
      </span>
    );
  };

  const filterOptions = [
    { value: "", label: t(`${f}.filterAllGames`) },
    ...tcgTypes.filter(g => g.is_active).map(g => ({ value: String(g.id), label: g.name_ja })),
  ];
  const visibleItems = gameFilter === ""
    ? items
    : items.filter(row => row.game_ids.includes(Number(gameFilter)));
  const gameOptions = tcgTypes
    .filter(g => g.is_active || form.game_ids.includes(String(g.id)))
    .map(g => ({ value: String(g.id), label: g.name_ja }));

  const columns: DataTableColumn<ProductFormat>[] = [
    { key: "name", header: t(`${f}.name`) },
    { key: "game_ids", header: t(`${f}.gameIds`), renderCell: row => renderGames(row.game_ids) },
    { key: "line_id", header: t(`${f}.lineId`), renderCell: row => getLineName(row.line_id) },
    { key: "display_order", header: t(`${f}.displayOrder`) },
    {
      key: "is_active",
      header: t(`${f}.isActive`),
      renderCell: row => row.is_active
        ? <STATUS_ICONS.check size={ICON.sm} aria-hidden="true" />
        : "-",
    },
  ];

  return (
    <>
      <ContentToolbar
        left={
          <SelectControl
            size="sm"
            className="field-h-md"
            data-testid="product-formats-game-filter"
            aria-label={t(`${f}.filterByGame`)}
            value={gameFilter}
            onChange={e => setGameFilter(e.target.value)}
            options={filterOptions}
          />
        }
        right={
          <HeaderButton
            variant="primary"
            data-testid="product-formats-new"
            onClick={openCreate}
          >
            {t(`${f}.addNew`)}
          </HeaderButton>
        }
      />
      {error && !showForm && <p role="alert">{error}</p>}
      <DataTable
        columns={columns}
        data={visibleItems}
        rowKey={row => String(row.id)}
        onRowClick={row => openEdit(row)}
        emptyState={<EmptyState title={t(`${f}.noData`)} size="compact" />}
        page={1}
        hasNextPage={items.length >= PER_PAGE}
        onPageChange={() => undefined}
        prevPageLabel={t("common.prevPage")}
        nextPageLabel={t("common.nextPage")}
      />

      {/* 編集/新規 ドロワー */}
      <Drawer
        open={showForm}
        onClose={() => setShowForm(false)}
        title={editId ? t(`${f}.editTitle`) : t(`${f}.createTitle`)}
        footer={
          <>
            {editId && (
              <HeaderButton variant="secondary" onClick={() => { setShowForm(false); setConfirmDeleteId(editId); }}>
                {t("common.delete")}
              </HeaderButton>
            )}
            <div style={{ marginLeft: "auto", display: "flex", gap: "var(--space-2)" }}>
              <HeaderButton variant="secondary" onClick={() => setShowForm(false)}>
                {t("common.back")}
              </HeaderButton>
              <HeaderButton
                variant="primary"
                onClick={() => formRef.current?.requestSubmit()}
              >
                {editId ? t("common.update") : t("common.create")}
              </HeaderButton>
            </div>
          </>
        }
      >
        <form ref={formRef} onSubmit={e => { void submit(e); }}>
          {error && <Callout variant="warning" title={t(`${f}.saveFailed`)}>{error}</Callout>}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-3) var(--space-4)" }}>
            <div className="form-group">
              <TextField
                label={`${t(`${f}.code`)} *`}
                value={form.code}
                onChange={e => setForm({ ...form, code: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <TextField
                label={`${t(`${f}.name`)} *`}
                value={form.name}
                onChange={e => setForm({ ...form, name: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <TextField
                label={t(`${f}.nameEn`)}
                value={form.name_en}
                onChange={e => setForm({ ...form, name_en: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label style={{ display: "block", fontSize: "var(--font-sm)", marginBottom: "var(--space-1)" }}>
                {t(`${f}.lineId`)}
              </label>
              <SelectControl
                options={[
                  { value: "", label: "—" },
                  ...lines.map(l => ({ value: String(l.id), label: l.name })),
                ]}
                value={form.line_id != null ? String(form.line_id) : ""}
                onChange={e => setForm({ ...form, line_id: e.target.value ? Number(e.target.value) : null })}
                fullWidth
              />
            </div>
            <div className="form-group" style={{ gridColumn: "1 / -1" }}>
              <div style={{ fontSize: "var(--font-sm)", marginBottom: "var(--space-1)" }}>
                {t(`${f}.gameIds`)}
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)" }}>
                {gameOptions.map(o => (
                  <Checkbox
                    key={o.value}
                    size="sm"
                    label={o.label}
                    data-testid={`product-format-games-option-${o.value}`}
                    checked={form.game_ids.includes(o.value)}
                    onChange={() => setForm({
                      ...form,
                      game_ids: form.game_ids.includes(o.value)
                        ? form.game_ids.filter(v => v !== o.value)
                        : [...form.game_ids, o.value],
                    })}
                  />
                ))}
              </div>
            </div>
            <div className="form-group">
              <TextField
                type="number"
                label={t(`${f}.displayOrder`)}
                value={String(form.display_order)}
                onChange={e => setForm({ ...form, display_order: Number(e.target.value) })}
              />
            </div>
            <Checkbox
              label={t(`${f}.isActive`)}
              checked={form.is_active}
              onChange={e => setForm({ ...form, is_active: e.target.checked })}
            />
          </div>
        </form>
      </Drawer>

      <ConfirmModal
        open={confirmDeleteId !== null}
        title={t("common.delete")}
        message={t(`${f}.confirmDelete`)}
        confirmLabel={t("common.delete")}
        danger
        onConfirm={() => { void confirmDelete(); }}
        onCancel={() => setConfirmDeleteId(null)}
      />
    </>
  );
}
