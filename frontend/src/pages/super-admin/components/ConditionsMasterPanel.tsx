/**
 * ConditionsMasterPanel — 状態マスタパネル v2（AnalysisRulesPage の hub-content 内で使用）
 *
 * ADR-027: 全UI文字列は t("key") 経由。
 * ADR-144: 金型クラスのみ使用。
 *
 * v2 変更点:
 *   - code は自動生成（非表示）
 *   - canonical は condition_def + unit の自動プレビューに置き換え
 *   - aliases ボタンを削除
 *   - フォームを質問形式ラベルに変更
 *   - condition_def_id / unit_id プルダウンを追加
 */
import { useCallback, useEffect, useRef, useState, FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../../../lib/api";
import { ContentToolbar } from "../../../components/ContentToolbar";
import { HeaderButton } from "../../../components/HeaderButton";
import { DataTable, type DataTableColumn } from "../../../components/DataTable";
import { EmptyState } from "../../../components/EmptyState";
import { TextField } from "../../../components/TextField";
import { Drawer } from "../../../components/Drawer";
import ConfirmModal from "../../../components/ConfirmModal";
import { Check } from "../../../constants/icons";

interface ConditionDef {
  id: number;
  name: string;
  name_en: string | null;
  is_active: boolean;
}

interface UnitItem {
  id: number;
  code: string;
  canonical: string;
  is_active: boolean;
}

interface CentralCondition {
  id: number;
  code: string;
  canonical: string;
  app_kubun: string | null;
  is_active: boolean;
  priority: number | null;
  search_kw: string;
  exclude_kw: string;
  match_type: string;
  effect: string;
  condition_def_id: number | null;
  unit_id: number | null;
  note: string;
}

type ConditionFormState = {
  condition_def_id: string;
  unit_id: string;
  app_kubun: string;
  is_active: boolean;
  priority: string;
  search_kw: string;
  exclude_kw: string;
  match_type: string;
  effect: string;
  note: string;
};

const emptyForm: ConditionFormState = {
  condition_def_id: "",
  unit_id: "",
  app_kubun: "",
  is_active: true,
  priority: "",
  search_kw: "",
  exclude_kw: "",
  match_type: "KEYWORD",
  effect: "OUTPUT",
  note: "",
};

const PER_PAGE = 50;

export function ConditionsMasterPanel() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const exportLock = useRef(false);
  const [exporting, setExporting] = useState(false);
  const [items, setItems] = useState<CentralCondition[]>([]);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());

  // 参照データ
  const [conditionDefs, setConditionDefs] = useState<ConditionDef[]>([]);
  const [units, setUnits] = useState<UnitItem[]>([]);

  async function downloadExport() {
    if (exportLock.current) return;
    exportLock.current = true; setExporting(true); setError("");
    let url: string | undefined;
    const anchor = document.createElement("a");
    try {
      const blob = await api.getBlob("/super-admin/conditions/export");
      url = URL.createObjectURL(blob); anchor.href = url;
      anchor.download = "conditions-export.csv";
      document.body.appendChild(anchor); anchor.click();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      anchor.remove(); if (url) URL.revokeObjectURL(url); exportLock.current = false; setExporting(false);
    }
  }

  // 編集/新規ドロワー
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<ConditionFormState>(emptyForm);
  const [editId, setEditId] = useState<number | null>(null);

  // 一括削除確認
  const [confirmDelete, setConfirmDelete] = useState(false);

  const conditionsFormRef = useRef<HTMLFormElement>(null);

  const loadReferenceData = useCallback(async () => {
    try {
      const [defs, unitList] = await Promise.all([
        api.get<ConditionDef[]>("/super-admin/condition-definitions"),
        api.get<UnitItem[]>("/super-admin/units"),
      ]);
      setConditionDefs(defs.filter((d: ConditionDef) => d.is_active));
      setUnits(unitList.filter((u: UnitItem) => u.is_active));
    } catch {
      // 参照データ取得失敗は致命的ではないので無視
    }
  }, []);

  const load = useCallback(async () => {
    try {
      const params = new URLSearchParams({ page: String(page), per_page: String(PER_PAGE) });
      const data = await api.get<CentralCondition[]>(`/super-admin/conditions?${params.toString()}`);
      setItems(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    }
  }, [page, t]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => { void loadReferenceData(); }, [loadReferenceData]);

  const openCreate = () => { setEditId(null); setForm(emptyForm); setShowForm(true); };
  const openEdit = (c: CentralCondition) => {
    setEditId(c.id);
    setForm({
      condition_def_id: c.condition_def_id != null ? String(c.condition_def_id) : "",
      unit_id: c.unit_id != null ? String(c.unit_id) : "",
      app_kubun: c.app_kubun ?? "",
      is_active: c.is_active,
      priority: c.priority != null ? String(c.priority) : "",
      search_kw: c.search_kw,
      exclude_kw: c.exclude_kw,
      match_type: c.match_type,
      effect: c.effect,
      note: c.note ?? "",
    });
    setShowForm(true);
  };

  const f = "superAdmin.conditionsAdmin.fields";

  // 出力プレビュー: 選択した condition_def 名 + unit 名の組み合わせ
  const outputPreview = (() => {
    const defName = conditionDefs.find((d: ConditionDef) => String(d.id) === form.condition_def_id)?.name ?? "";
    const unitName = units.find((u: UnitItem) => String(u.id) === form.unit_id)?.canonical ?? "";
    if (!defName) return t(`${f}.unset`);
    return unitName ? `${defName} ${unitName}` : defName;
  })();

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    const payload: Record<string, unknown> = {
      app_kubun: form.app_kubun || null,
      is_active: form.is_active,
      priority: form.priority !== "" ? parseInt(form.priority, 10) : null,
      search_kw: form.search_kw,
      exclude_kw: form.exclude_kw,
      match_type: form.match_type,
      effect: form.effect,
      condition_def_id: form.condition_def_id !== "" ? parseInt(form.condition_def_id, 10) : null,
      unit_id: form.unit_id !== "" ? parseInt(form.unit_id, 10) : null,
      note: form.note,
    };
    // 新規の場合は canonical をプレビュー値で送る（バックエンドが code を自動生成する）
    if (!editId) {
      payload.canonical = outputPreview;
      payload.code = "";  // バックエンド側で CN<timestamp> に自動変換
    }
    try {
      if (editId) {
        await api.patch(`/super-admin/conditions/${editId}`, payload);
      } else {
        await api.post("/super-admin/conditions", payload);
      }
      setShowForm(false);
      setForm(emptyForm);
      setEditId(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.saveError"));
    }
  };

  const bulkDelete = async () => {
    setConfirmDelete(false);
    const selectedIds = Array.from(selectedKeys).map(Number);
    const results = await Promise.allSettled(
      selectedIds.map((id) => api.delete(`/super-admin/conditions/${id}`)),
    );
    try {
      if (results.some((r) => r.status === "rejected")) {
        setError(t("common.deleteError"));
      }
      setSelectedKeys(new Set());
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.deleteError"));
    }
  };

  const MATCH_TYPE_OPTIONS = [
    { value: "KEYWORD", label: t(`${f}.matchTypeKeyword`) },
    { value: "REGEX",   label: t(`${f}.matchTypeRegex`) },
    { value: "LITERAL", label: t(`${f}.matchTypeLiteral`) },
    { value: "DEFAULT", label: t(`${f}.matchTypeDefault`) },
  ];

  const EFFECT_OPTIONS = [
    { value: "OUTPUT",  label: t(`${f}.effectOutput`) },
    { value: "EXCLUDE", label: t(`${f}.effectExclude`) },
  ];

  const columns: DataTableColumn<CentralCondition>[] = [
    {
      key: "canonical",
      header: t(`${f}.outputPreview`),
      renderCell: row => {
        const defName = conditionDefs.find((d: ConditionDef) => d.id === row.condition_def_id)?.name ?? row.canonical;
        const unitName = units.find((u: UnitItem) => u.id === row.unit_id)?.canonical ?? "";
        return unitName ? `${defName} ${unitName}` : defName;
      },
    },
    { key: "match_type", header: t(`${f}.matchType`) },
    { key: "app_kubun", header: t(`${f}.appKubun`), renderCell: row => row.app_kubun ?? "—" },
    { key: "priority", header: t(`${f}.priority`), renderCell: row => row.priority ?? "—" },
    {
      key: "is_active",
      header: t(`${f}.isActive`),
      renderCell: row => row.is_active ? <Check size={16} /> : "—",
    },
  ];

  return (
    <>
      <ContentToolbar
        right={
          <>
            <HeaderButton variant="secondary" disabled={exporting} data-testid="conditions-export" onClick={() => void downloadExport()}>
              {t(exporting ? "common.loading" : "conditionCsv.exportButton")}
            </HeaderButton>
            <HeaderButton variant="primary" data-testid="conditions-import" onClick={() => navigate("/super-admin/masters/conditions/import")}>
              {t("conditionCsv.importButton")}
            </HeaderButton>
            <HeaderButton variant="primary" data-testid="conditions-new" onClick={openCreate}>
              {t("superAdmin.conditionsAdmin.newCondition")}
            </HeaderButton>
            <HeaderButton variant="secondary" disabled={selectedKeys.size === 0} data-testid="conditions-bulk-delete" onClick={() => setConfirmDelete(true)}>
              {t("common.delete")}
            </HeaderButton>
          </>
        }
      />
      {error && <p role="alert">{error}</p>}
      <DataTable
        columns={columns}
        data={items}
        rowKey={row => String(row.id)}
        selectable
        selectedKeys={selectedKeys}
        onSelectChange={setSelectedKeys}
        onRowClick={row => openEdit(row)}
        emptyState={<EmptyState title={t("common.noData")} size="compact" />}
        page={page}
        hasNextPage={items.length >= PER_PAGE}
        onPageChange={setPage}
        prevPageLabel={t("common.prevPage")}
        nextPageLabel={t("common.nextPage")}
      />

      {/* 編集/新規 ドロワー */}
      <Drawer
        open={showForm}
        onClose={() => setShowForm(false)}
        title={editId ? t("common.edit") : t("common.create")}
        footer={
          <>
            <div style={{ marginLeft: "auto", display: "flex", gap: "var(--space-2)" }}>
              <HeaderButton variant="secondary" onClick={() => setShowForm(false)}>{t("common.back")}</HeaderButton>
              <HeaderButton variant="primary" onClick={() => conditionsFormRef.current?.requestSubmit()}>{editId ? t("common.update") : t("common.create")}</HeaderButton>
            </div>
          </>
        }
      >
        <form ref={conditionsFormRef} onSubmit={e => { void submit(e); }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-3) var(--space-4)" }}>

            {/* 1. どの状態ですか？ — condition_def_id */}
            <div className="form-group">
              <label className="field-label">{t(`${f}.conditionDefId`)}</label>
              {/* ui-allow: reference pulldown for condition_def_id; no SelectControl variant with dynamic option list (#3594) */}
              <select
                className="field field-h-md"
                value={form.condition_def_id}
                onChange={e => setForm({ ...form, condition_def_id: e.target.value })}
              >
                <option value="">{t(`${f}.unset`)}</option>
                {conditionDefs.map(d => (
                  <option key={d.id} value={String(d.id)}>{d.name}</option>
                ))}
              </select>
            </div>

            {/* 2. どの単位が対象ですか？ — unit_id */}
            <div className="form-group">
              <label className="field-label">{t(`${f}.unitId`)}</label>
              {/* ui-allow: reference pulldown for unit_id; no SelectControl variant with dynamic option list (#3594) */}
              <select
                className="field field-h-md"
                value={form.unit_id}
                onChange={e => setForm({ ...form, unit_id: e.target.value })}
              >
                <option value="">{t(`${f}.noUnit`)}</option>
                {units.map(u => (
                  <option key={u.id} value={String(u.id)}>{u.canonical}</option>
                ))}
              </select>
            </div>

            {/* 3. 出力プレビュー */}
            <div className="form-group" style={{ gridColumn: "1 / -1" }}>
              <label className="field-label">{t(`${f}.outputPreview`)}</label>
              <div style={{
                padding: "var(--space-2) var(--space-3)",
                background: "var(--color-surface-2, #f5f5f5)",
                borderRadius: "var(--radius-sm, 4px)",
                fontWeight: "bold",
              }}>
                {outputPreview}
              </div>
            </div>

            {/* 4. どの言葉が含まれていたらこの状態ですか？ */}
            <div className="form-group" style={{ gridColumn: "1 / -1" }}>
              <label style={{ display: "block", marginBottom: "var(--space-1)" }}>
                {t(`${f}.searchKw`)}
              </label>
              <textarea
                value={form.search_kw}
                onChange={e => setForm({ ...form, search_kw: e.target.value })}
                rows={3}
                style={{ width: "100%", resize: "vertical" }}
              />
            </div>

            {/* 5. この言葉が含まれていたら除外しますか？ */}
            <div className="form-group" style={{ gridColumn: "1 / -1" }}>
              <label style={{ display: "block", marginBottom: "var(--space-1)" }}>
                {t(`${f}.excludeKw`)}
              </label>
              <textarea
                value={form.exclude_kw}
                onChange={e => setForm({ ...form, exclude_kw: e.target.value })}
                rows={3}
                style={{ width: "100%", resize: "vertical" }}
              />
            </div>

            {/* 6. 言葉の探し方は？ — match_type */}
            <div className="form-group">
              <label className="field-label">{t(`${f}.matchType`)} *</label>
              {/* ui-allow: enum select for condition match_type; no SelectControl variant with option map (#3594) */}
              <select
                className="field field-h-md"
                value={form.match_type}
                onChange={e => setForm({ ...form, match_type: e.target.value })}
                required
              >
                {MATCH_TYPE_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>

            {/* 7. 見つけたらどうしますか？ — effect */}
            <div className="form-group">
              <label className="field-label">{t(`${f}.effect`)} *</label>
              {/* ui-allow: enum select for condition effect; no SelectControl variant with option map (#3594) */}
              <select
                className="field field-h-md"
                value={form.effect}
                onChange={e => setForm({ ...form, effect: e.target.value })}
                required
              >
                {EFFECT_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>

            {/* 8. どの商品タイプに適用しますか？ */}
            <div className="form-group">
              <TextField
                label={t(`${f}.appKubun`)}
                value={form.app_kubun}
                onChange={e => setForm({ ...form, app_kubun: e.target.value })}
              />
            </div>

            {/* 9. 優先順位 */}
            <div className="form-group">
              <TextField
                type="number"
                label={t(`${f}.priority`)}
                value={form.priority}
                onChange={e => setForm({ ...form, priority: e.target.value })}
              />
            </div>

            {/* 10. メモ */}
            <div className="form-group" style={{ gridColumn: "1 / -1" }}>
              <TextField
                label={t(`${f}.note`)}
                value={form.note}
                onChange={e => setForm({ ...form, note: e.target.value })}
              />
            </div>

            {/* 11. 有効にしますか？ */}
            <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
              <input type="checkbox" checked={form.is_active} onChange={e => setForm({ ...form, is_active: e.target.checked })} />
              {t(`${f}.isActive`)}
            </label>

          </div>
        </form>
      </Drawer>

      <ConfirmModal
        open={confirmDelete}
        title={t("common.delete")}
        message={t("superAdmin.conditionsAdmin.bulkDeleteConfirm")}
        confirmLabel={t("common.delete")}
        danger
        onConfirm={() => { void bulkDelete(); }}
        onCancel={() => setConfirmDelete(false)}
      />
    </>
  );
}
