/**
 * SoldOutWordsTab — 完売ルール 検索・除外ワードタブ（CRUD UI）
 *
 * ADR-027: 全UI文字列は t("key") 経由。
 * ADR-144: 金型コンポーネントのみ使用。生select/生input禁止。
 */
import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../../components/Button";
import { TextField } from "../../../components/TextField";
import { Select } from "../../../components/Select";
import { DataTable, type DataTableColumn } from "../../../components/DataTable";
import { Modal } from "../../../components/Modal";
import ConfirmModal from "../../../components/ConfirmModal";
import { api, ApiError } from "../../../lib/api";

// ---------------------------------------------------------------------------
// 型定義
// ---------------------------------------------------------------------------

export interface PolicyCurrentResponse {
  active_revision_id: string | null;
  draft_revision_id: string | null;
  current_suite_revision_id: string | null;
  lock_version: number;
  instruction?: string;
  draft_instruction?: string;
}

export interface RuleWordRow {
  rule_id: string;
  rule_version_id: string;
  title: string;
  word_id: string;
  word_kind: string;
  word_text: string;
  position: number;
  is_deleted: boolean;
}

interface WordsApiResponse {
  items: RuleWordRow[];
  has_next: boolean;
  next_cursor: string | null;
}

// ---------------------------------------------------------------------------
// 型定義（CSV）
// ---------------------------------------------------------------------------

interface ImportPreviewItem {
  rule_id: string;
  title: string;
  word_kind: string;
  text: string;
  before?: string;
}

interface ImportPreviewResult {
  add_count: number;
  update_count: number;
  delete_count: number;
  add: ImportPreviewItem[];
  update: ImportPreviewItem[];
  delete: ImportPreviewItem[];
}

// ---------------------------------------------------------------------------
// API ヘルパー
// ---------------------------------------------------------------------------

const POLICY_PATH = "/super-admin/analysis-policies/sold-out";

async function apiFetchWords(
  revisionId: string,
  q: string,
  wordKind: string
): Promise<WordsApiResponse> {
  const params = new URLSearchParams({ q, word_kind: wordKind });
  return api.get<WordsApiResponse>(
    `${POLICY_PATH}/revisions/${revisionId}/rules?${params.toString()}`
  );
}

async function apiPostDraftRevision(
  current: PolicyCurrentResponse,
  changes: object[]
): Promise<void> {
  await api.post<void>(`${POLICY_PATH}/draft-revisions`, {
    expected_draft_id: current.draft_revision_id,
    expected_active_id: current.active_revision_id,
    lock_version: current.lock_version,
    changes,
    request_key: crypto.randomUUID(),
  });
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface SoldOutWordsTabProps {
  current: PolicyCurrentResponse | null;
  loading: boolean;
  error: string | null;
  onCurrentChange: () => void;
}

// ---------------------------------------------------------------------------
// コンポーネント
// ---------------------------------------------------------------------------

export function SoldOutWordsTab({
  current,
  loading,
  error,
  onCurrentChange,
}: SoldOutWordsTabProps) {
  const { t } = useTranslation();

  // 一覧
  const [words, setWords] = useState<RuleWordRow[]>([]);
  const [wordsLoading, setWordsLoading] = useState(false);
  const [wordsError, setWordsError] = useState<string | null>(null);
  const [searchQ, setSearchQ] = useState("");
  const [wordKind, setWordKind] = useState("both");

  // 追加/編集モーダル
  const [modalOpen, setModalOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<RuleWordRow | null>(null);
  const [formKind, setFormKind] = useState<string>("search");
  const [formText, setFormText] = useState<string>("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // 削除確認モーダル
  const [deleteTarget, setDeleteTarget] = useState<RuleWordRow | null>(null);
  const [deleting, setDeleting] = useState(false);

  // CSV エクスポート/インポート
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState(false);
  const exportLock = useRef(false);
  const importInputRef = useRef<HTMLInputElement>(null);
  const [importPreview, setImportPreview] = useState<ImportPreviewResult | null>(null);
  const [importPreviewOpen, setImportPreviewOpen] = useState(false);
  const [importRaw, setImportRaw] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [importSuccess, setImportSuccess] = useState(false);

  async function loadWords() {
    if (!current?.draft_revision_id && !current?.active_revision_id) return;
    const revId = current.draft_revision_id ?? current.active_revision_id ?? "";
    setWordsLoading(true);
    setWordsError(null);
    try {
      const data = await apiFetchWords(revId, searchQ, wordKind);
      setWords(data.items);
    } catch {
      setWordsError(t("analysisRules.errors.unknown"));
    } finally {
      setWordsLoading(false);
    }
  }

  function openAddModal() {
    setEditTarget(null);
    setFormKind("search");
    setFormText("");
    setSaveError(null);
    setModalOpen(true);
  }

  function openEditModal(row: RuleWordRow) {
    setEditTarget(row);
    setFormKind(row.word_kind);
    setFormText(row.word_text);
    setSaveError(null);
    setModalOpen(true);
  }

  function closeModal() {
    setModalOpen(false);
    setSaveError(null);
  }

  async function handleSave() {
    if (!current) return;
    setSaving(true);
    setSaveError(null);
    try {
      if (editTarget) {
        // 編集: update_rule
        await apiPostDraftRevision(current, [
          {
            type: "update_rule",
            rule_id: editTarget.rule_id,
            title: editTarget.title || formText,
            words: [{ kind: formKind, text: formText }],
          },
        ]);
      } else {
        // 追加: add_rule
        await apiPostDraftRevision(current, [
          {
            type: "add_rule",
            title: formText,
            words: [{ kind: formKind, text: formText }],
          },
        ]);
      }
      setModalOpen(false);
      onCurrentChange();
      await loadWords();
    } catch (e) {
      const msg =
        e instanceof ApiError && e.status === 409
          ? t("analysisRules.errors.conflict")
          : t("analysisRules.errors.unknown");
      setSaveError(msg);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!current || !deleteTarget) return;
    setDeleting(true);
    try {
      await apiPostDraftRevision(current, [
        {
          type: "delete_rule",
          rule_id: deleteTarget.rule_id,
        },
      ]);
      setDeleteTarget(null);
      onCurrentChange();
      await loadWords();
    } catch {
      // 削除エラーは wordsError に表示
      setWordsError(t("analysisRules.errors.unknown"));
      setDeleteTarget(null);
    } finally {
      setDeleting(false);
    }
  }

  async function handleExportCsv() {
    if (exportLock.current) return;
    exportLock.current = true;
    setExporting(true);
    setExportError(false);
    let url: string | undefined;
    const anchor = document.createElement("a");
    try {
      const blob = await api.getBlob(`${POLICY_PATH}/export`);
      url = URL.createObjectURL(blob);
      anchor.href = url;
      anchor.download = "analysis-rules-sold-out.csv";
      document.body.appendChild(anchor);
      anchor.click();
    } catch {
      setExportError(true);
    } finally {
      anchor.remove();
      if (url) URL.revokeObjectURL(url);
      exportLock.current = false;
      setExporting(false);
    }
  }

  async function handleImportFileChange(e: { target: HTMLInputElement }) {
    const file = e.target.files?.[0];
    if (!e.target) return;
    // reset input so same file can be re-selected
    (e.target as HTMLInputElement).value = "";
    if (!file) return;
    setImportError(null);
    setImportSuccess(false);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const preview = await api.postForm<ImportPreviewResult>(`${POLICY_PATH}/import/preview`, formData);
      setImportRaw(file);
      setImportPreview(preview);
      setImportPreviewOpen(true);
    } catch {
      setImportError(t("analysisRules.errors.unknown"));
    }
  }

  async function handleImportCommit() {
    if (!importRaw || !current) return;
    setImporting(true);
    setImportError(null);
    try {
      const formData = new FormData();
      formData.append("file", importRaw);
      formData.append("lock_version", String(current.lock_version));
      if (current.draft_revision_id) formData.append("draft_revision_id", current.draft_revision_id);
      if (current.active_revision_id) formData.append("active_revision_id", current.active_revision_id);
      await api.postForm(`${POLICY_PATH}/import/commit`, formData);
      setImportPreviewOpen(false);
      setImportPreview(null);
      setImportRaw(null);
      setImportSuccess(true);
      onCurrentChange();
      await loadWords();
    } catch (e) {
      const msg =
        e instanceof ApiError && e.status === 409
          ? t("analysisRules.errors.conflict")
          : t("analysisRules.errors.unknown");
      setImportError(msg);
    } finally {
      setImporting(false);
    }
  }

  if (loading) return <p>{t("common.loading")}</p>;
  if (error) return <p style={{ color: "var(--color-error)" }}>{error}</p>;

  const wordKindOptions = [
    { value: "both", label: t("analysisRules.soldOut.wordKindAll") },
    { value: "search", label: t("analysisRules.soldOut.wordKindSearch") },
    { value: "exclude", label: t("analysisRules.soldOut.wordKindExclude") },
  ];

  const formKindOptions = [
    { value: "search", label: t("analysisRules.soldOut.words.search") },
    { value: "exclude", label: t("analysisRules.soldOut.words.exclude") },
  ];

  const columns: DataTableColumn<RuleWordRow>[] = [
    {
      key: "word_text",
      header: t("analysisRules.soldOut.words.textColumn"),
      width: "1fr",
    },
    {
      key: "word_kind",
      header: t("analysisRules.soldOut.words.kindColumn"),
      width: "120px",
      renderCell: (row) =>
        row.word_kind === "search"
          ? t("analysisRules.soldOut.words.search")
          : t("analysisRules.soldOut.words.exclude"),
    },
    {
      key: "actions",
      header: t("analysisRules.soldOut.words.actionsColumn"),
      width: "140px",
      renderCell: (row) => (
        <div style={{ display: "flex", gap: "var(--space-1)" }}>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => openEditModal(row)}
          >
            {t("common.edit")}
          </Button>
          <Button
            variant="danger"
            size="sm"
            onClick={() => setDeleteTarget(row)}
          >
            {t("analysisRules.soldOut.words.delete")}
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
      {/* フィルター行 */}
      <div
        style={{
          display: "flex",
          gap: "var(--space-2)",
          alignItems: "flex-end",
          flexWrap: "wrap",
        }}
      >
        <TextField
          label={t("analysisRules.soldOut.wordsTitle")}
          value={searchQ}
          onChange={(e) => setSearchQ(e.target.value)}
          placeholder={t("analysisRules.soldOut.wordSearchPlaceholder")}
        />
        <Select
          label=""
          value={wordKind}
          onChange={(e) => setWordKind(e.target.value)}
          options={wordKindOptions}
        />
        <Button variant="secondary" onClick={loadWords} loading={wordsLoading}>
          {t("common.search") ?? "Search"}
        </Button>
        <Button variant="primary" onClick={openAddModal}>
          {t("analysisRules.soldOut.words.addButton")}
        </Button>
        <Button variant="secondary" disabled={exporting} onClick={() => void handleExportCsv()}>
          {t(exporting ? "common.loading" : "analysisRules.soldOut.words.exportCsv")}
        </Button>
        <Button variant="secondary" onClick={() => importInputRef.current?.click()}>
          {t("analysisRules.soldOut.words.importCsv")}
        </Button>
        {/* hidden file input */}
        <input
          ref={importInputRef}
          type="file"
          accept=".csv"
          style={{ display: "none" }}
          onChange={(e) => void handleImportFileChange(e)}
        />
      </div>

      {wordsError && (
        <p style={{ color: "var(--color-error)", fontSize: "var(--font-sm)" }}>
          {wordsError}
        </p>
      )}
      {exportError && (
        <p role="alert" style={{ color: "var(--color-error)", fontSize: "var(--font-sm)" }}>
          {t("analysisRules.errors.unknown")}
        </p>
      )}
      {importError && (
        <p role="alert" style={{ color: "var(--color-error)", fontSize: "var(--font-sm)" }}>
          {importError}
        </p>
      )}
      {importSuccess && (
        <p role="status" style={{ color: "var(--color-success)", fontSize: "var(--font-sm)" }}>
          {t("analysisRules.soldOut.words.importSuccess")}
        </p>
      )}

      {/* データテーブル */}
      <DataTable<RuleWordRow>
        columns={columns}
        data={words}
        rowKey={(row) => row.word_id}
        emptyState={
          <p style={{ color: "var(--text-muted)", fontSize: "var(--font-sm)" }}>
            {t("common.noResults") ?? "No results"}
          </p>
        }
      />

      {/* 追加/編集モーダル */}
      <Modal
        open={modalOpen}
        onClose={closeModal}
        title={
          editTarget
            ? t("analysisRules.soldOut.words.editTitle")
            : t("analysisRules.soldOut.words.addTitle")
        }
        size="sm"
        footer={
          <div style={{ display: "flex", gap: "var(--space-2)", justifyContent: "flex-end" }}>
            <Button variant="secondary" onClick={closeModal}>
              {t("analysisRules.soldOut.words.cancel")}
            </Button>
            <Button variant="primary" onClick={handleSave} loading={saving}>
              {t("analysisRules.soldOut.words.save")}
            </Button>
          </div>
        }
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
          <Select
            label={t("analysisRules.soldOut.words.wordKind")}
            value={formKind}
            onChange={(e) => setFormKind(e.target.value)}
            options={formKindOptions}
          />
          <TextField
            label={t("analysisRules.soldOut.words.wordText")}
            value={formText}
            onChange={(e) => setFormText(e.target.value)}
          />
          {saveError && (
            <p style={{ color: "var(--color-error)", fontSize: "var(--font-sm)" }}>
              {saveError}
            </p>
          )}
        </div>
      </Modal>

      {/* 削除確認モーダル */}
      <ConfirmModal
        open={deleteTarget !== null}
        title={t("analysisRules.soldOut.words.confirmDeleteTitle")}
        message={t("analysisRules.soldOut.words.confirmDeleteMessage")}
        confirmLabel={t("analysisRules.soldOut.words.delete")}
        cancelLabel={t("analysisRules.soldOut.words.cancel")}
        danger
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />

      {/* CSV インポートプレビューモーダル */}
      <Modal
        open={importPreviewOpen}
        onClose={() => { setImportPreviewOpen(false); setImportError(null); }}
        title={t("analysisRules.soldOut.words.importPreviewTitle")}
        size="md"
        footer={
          <div style={{ display: "flex", gap: "var(--space-2)", justifyContent: "flex-end" }}>
            <Button variant="secondary" onClick={() => { setImportPreviewOpen(false); setImportError(null); }}>
              {t("analysisRules.soldOut.words.cancel")}
            </Button>
            <Button
              variant="primary"
              onClick={() => void handleImportCommit()}
              loading={importing}
              disabled={
                importPreview !== null &&
                importPreview.add_count === 0 &&
                importPreview.update_count === 0 &&
                importPreview.delete_count === 0
              }
            >
              {t("analysisRules.soldOut.words.importConfirm")}
            </Button>
          </div>
        }
      >
        {importPreview && (
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
            <div style={{ display: "flex", gap: "var(--space-4)" }}>
              <span>{t("analysisRules.soldOut.words.previewAdd")}: {importPreview.add_count}</span>
              <span>{t("analysisRules.soldOut.words.previewUpdate")}: {importPreview.update_count}</span>
              <span>{t("analysisRules.soldOut.words.previewDelete")}: {importPreview.delete_count}</span>
            </div>
            {importPreview.add_count === 0 && importPreview.update_count === 0 && importPreview.delete_count === 0 && (
              <p style={{ color: "var(--text-muted)", fontSize: "var(--font-sm)" }}>
                {t("analysisRules.soldOut.words.previewNoChanges")}
              </p>
            )}
            {importPreview.add.length > 0 && (
              <div>
                <p style={{ fontWeight: "bold", fontSize: "var(--font-sm)" }}>{t("analysisRules.soldOut.words.previewAdd")}</p>
                <ul style={{ fontSize: "var(--font-sm)", margin: 0, paddingLeft: "var(--space-4)" }}>
                  {importPreview.add.map((item, i) => (
                    <li key={i}>[{item.word_kind}] {item.text}</li>
                  ))}
                </ul>
              </div>
            )}
            {importPreview.update.length > 0 && (
              <div>
                <p style={{ fontWeight: "bold", fontSize: "var(--font-sm)" }}>{t("analysisRules.soldOut.words.previewUpdate")}</p>
                <ul style={{ fontSize: "var(--font-sm)", margin: 0, paddingLeft: "var(--space-4)" }}>
                  {importPreview.update.map((item, i) => (
                    <li key={i}>[{item.word_kind}] {item.before} → {item.text}</li>
                  ))}
                </ul>
              </div>
            )}
            {importPreview.delete.length > 0 && (
              <div>
                <p style={{ fontWeight: "bold", fontSize: "var(--font-sm)" }}>{t("analysisRules.soldOut.words.previewDelete")}</p>
                <ul style={{ fontSize: "var(--font-sm)", margin: 0, paddingLeft: "var(--space-4)" }}>
                  {importPreview.delete.map((item, i) => (
                    <li key={i}>[{item.word_kind}] {item.text}</li>
                  ))}
                </ul>
              </div>
            )}
            {importError && (
              <p style={{ color: "var(--color-error)", fontSize: "var(--font-sm)" }}>{importError}</p>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
