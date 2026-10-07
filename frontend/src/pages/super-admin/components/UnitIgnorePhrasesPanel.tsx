/**
 * UnitIgnorePhrasesPanel — 「単位にしない言い回し」マスタ（単位ルール画面の UnitMasterPanel の下に並べる）
 *
 * 例: ONE PIECE は単位の別名 PIECE を含むが単位ではない。
 * ADR-027: 全UI文字列は t("key") 経由。
 * ADR-144: 金型コンポーネントのみ使用。
 */
import { useCallback, useEffect, useRef, useState, FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../../lib/api";
import { ContentToolbar } from "../../../components/ContentToolbar";
import { HeaderButton } from "../../../components/HeaderButton";
import { DataTable, type DataTableColumn } from "../../../components/DataTable";
import { EmptyState } from "../../../components/EmptyState";
import { TextField } from "../../../components/TextField";
import { Drawer } from "../../../components/Drawer";
import ConfirmModal from "../../../components/ConfirmModal";
import { STATUS_ICONS } from "../../../constants/icons";
import { ICON } from "../../../constants/iconSizes";

interface IgnorePhrase {
  id: number;
  phrase: string;
  note: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

type FormState = { phrase: string; note: string; is_active: boolean };

const EMPTY_FORM: FormState = { phrase: "", note: "", is_active: true };
const API_PATH = "/super-admin/unit-ignore-phrases";
const I18N = "unitIgnorePhrases";

export function UnitIgnorePhrasesPanel() {
  const { t } = useTranslation();
  const [items, setItems] = useState<IgnorePhrase[]>([]);
  const [error, setError] = useState("");
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [editId, setEditId] = useState<number | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const formRef = useRef<HTMLFormElement>(null);

  const load = useCallback(async () => {
    try {
      setItems(await api.get<IgnorePhrase[]>(API_PATH));
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    }
  }, [t]);

  useEffect(() => { void load(); }, [load]);

  const openCreate = () => { setEditId(null); setForm(EMPTY_FORM); setShowForm(true); };
  const openEdit = (row: IgnorePhrase) => {
    setEditId(row.id);
    setForm({ phrase: row.phrase, note: row.note ?? "", is_active: row.is_active });
    setShowForm(true);
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    const payload = { phrase: form.phrase, note: form.note || null, is_active: form.is_active };
    try {
      if (editId !== null) {
        await api.patch(`${API_PATH}/${editId}`, payload);
      } else {
        await api.post(API_PATH, payload);
      }
      setShowForm(false);
      setForm(EMPTY_FORM);
      setEditId(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.saveError"));
    }
  };

  const bulkDelete = async () => {
    setConfirmDelete(false);
    const ids = Array.from(selectedKeys).map(Number);
    const results = await Promise.allSettled(ids.map((id) => api.delete(`${API_PATH}/${id}`)));
    if (results.some((r) => r.status === "rejected")) setError(t("common.deleteError"));
    setSelectedKeys(new Set());
    await load();
  };

  const columns: DataTableColumn<IgnorePhrase>[] = [
    { key: "phrase", header: t(`${I18N}.phrase`) },
    { key: "note", header: t(`${I18N}.note`), renderCell: row => row.note || "-" },
    {
      key: "is_active",
      header: t(`${I18N}.isActive`),
      renderCell: row => row.is_active ? <STATUS_ICONS.check size={ICON.sm} aria-hidden="true" /> : "-",
    },
  ];

  return (
    <>
      <ContentToolbar
        left={<strong>{t(`${I18N}.title`)}</strong>}
        right={
          <>
            <HeaderButton variant="primary" data-testid="unit-ignore-new" onClick={openCreate}>
              {t("common.create")}
            </HeaderButton>
            <HeaderButton
              variant="secondary"
              disabled={selectedKeys.size === 0}
              data-testid="unit-ignore-bulk-delete"
              onClick={() => setConfirmDelete(true)}
            >
              {t("common.delete")}
            </HeaderButton>
          </>
        }
      />
      <p>{t(`${I18N}.description`)}</p>
      {error && <p role="alert">{error}</p>}
      <DataTable
        columns={columns}
        data={items}
        rowKey={row => String(row.id)}
        selectable
        selectedKeys={selectedKeys}
        onSelectChange={setSelectedKeys}
        onRowClick={row => openEdit(row)}
        emptyState={<EmptyState title={t(`${I18N}.empty`)} size="compact" />}
      />

      <Drawer
        open={showForm}
        onClose={() => setShowForm(false)}
        title={editId !== null ? t(`${I18N}.editTitle`) : t(`${I18N}.createTitle`)}
        footer={
          <div style={{ marginLeft: "auto", display: "flex", gap: "var(--space-2)" }}>
            <HeaderButton variant="secondary" onClick={() => setShowForm(false)}>
              {t("common.back")}
            </HeaderButton>
            <HeaderButton
              variant="primary"
              data-testid="unit-ignore-submit"
              onClick={() => formRef.current?.requestSubmit()}
            >
              {editId !== null ? t("common.update") : t("common.create")}
            </HeaderButton>
          </div>
        }
      >
        <form ref={formRef} onSubmit={e => { void submit(e); }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "var(--space-3)" }}>
            <TextField
              label={`${t(`${I18N}.phrase`)} *`}
              value={form.phrase}
              onChange={e => setForm({ ...form, phrase: e.target.value })}
              required
            />
            <TextField
              label={t(`${I18N}.note`)}
              value={form.note}
              onChange={e => setForm({ ...form, note: e.target.value })}
            />
            <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
              {/* ui-allow: チェックボックスの金型が未登録のため（手本 UnitMasterPanel.tsx:332 と同じ書き方） (#4032) */}
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={e => setForm({ ...form, is_active: e.target.checked })}
              />
              {t(`${I18N}.isActive`)}
            </label>
          </div>
        </form>
      </Drawer>

      <ConfirmModal
        open={confirmDelete}
        title={t("common.delete")}
        message={t(`${I18N}.confirmDelete`)}
        confirmLabel={t("common.delete")}
        danger
        onConfirm={() => { void bulkDelete(); }}
        onCancel={() => setConfirmDelete(false)}
      />
    </>
  );
}
