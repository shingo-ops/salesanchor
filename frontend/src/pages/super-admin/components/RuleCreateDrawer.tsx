/**
 * RuleCreateDrawer — ルール新規作成ドロワー
 *
 * tcg_status_master の新規ルールを作成する。
 * パターンマッチテスト機能を統合（SSOT: バックエンドの _match_status_pattern と同一ロジック）。
 *
 * ADR-027: 全UI文字列は t("key") 経由。
 * ADR-144: 金型クラスのみ使用。
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Drawer } from "../../../components/Drawer";
import { TextField } from "../../../components/TextField";
import { Select } from "../../../components/Select";
import { Button } from "../../../components/Button";
import { Badge } from "../../../components/Badge";
import { Card } from "../../../components/Card";
import { api } from "../../../lib/api";

interface RuleCreateDrawerProps {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}

interface PreviewResponse {
  matched: boolean;
  detail: string;
}

interface FormDraft {
  status_id: string;
  canonical: string;
  match_type: string;
  effect: string;
  search_pattern: string;
  exclude_pattern: string;
  priority: string;
  note: string;
}

const emptyDraft: FormDraft = {
  status_id: "",
  canonical: "",
  match_type: "LITERAL",
  effect: "OUTPUT",
  search_pattern: "",
  exclude_pattern: "",
  priority: "0",
  note: "",
};

export function RuleCreateDrawer({ open, onClose, onCreated }: RuleCreateDrawerProps) {
  const { t } = useTranslation();
  const f = "ruleManagement";
  const fc = `${f}.create`;

  const [draft, setDraft] = useState<FormDraft>(emptyDraft);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState("");
  const [testInput, setTestInput] = useState("");
  const [testResult, setTestResult] = useState<PreviewResponse | null>(null);
  const [testing, setTesting] = useState(false);

  const set = (key: keyof FormDraft, value: string) => {
    setDraft((prev: FormDraft) => ({ ...prev, [key]: value }));
    if (key === "match_type" || key === "search_pattern") {
      setTestResult(null);
    }
  };

  const handleTest = async () => {
    if (!testInput.trim()) return;
    setTesting(true);
    setTestResult(null);
    try {
      const result = await api.post<PreviewResponse>("/super-admin/status-master/preview", {
        match_type: draft.match_type,
        search_pattern: draft.search_pattern,
        input_text: testInput,
      });
      setTestResult(result);
    } catch (e) {
      setTestResult({
        matched: false,
        detail: e instanceof Error ? e.message : t("common.fetchError"),
      });
    } finally {
      setTesting(false);
    }
  };

  const handleCreate = async () => {
    setCreating(true);
    setCreateError("");
    try {
      await api.post("/super-admin/status-master", {
        status_id: draft.status_id,
        canonical: draft.canonical,
        match_type: draft.match_type,
        effect: draft.effect,
        search_pattern: draft.search_pattern,
        exclude_pattern: draft.exclude_pattern,
        priority: Number(draft.priority) || 0,
        note: draft.note,
        enabled: false,
      });
      setDraft(emptyDraft);
      setTestInput("");
      setTestResult(null);
      onCreated();
    } catch (e) {
      setCreateError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      setCreating(false);
    }
  };

  const handleClose = () => {
    setDraft(emptyDraft);
    setTestInput("");
    setTestResult(null);
    setCreateError("");
    onClose();
  };

  const isDefaultMatch = draft.match_type === "DEFAULT";
  const canCreate = draft.status_id.trim() !== "" && draft.canonical.trim() !== "";

  const matchTypeOptions = [
    { value: "LITERAL", label: t(`${fc}.matchTypeLiteral`) },
    { value: "REGEX", label: t(`${fc}.matchTypeRegex`) },
    { value: "DEFAULT", label: t(`${fc}.matchTypeDefault`) },
  ];

  const effectOptions = [
    { value: "OUTPUT", label: t(`${fc}.effectOutput`) },
    { value: "EXCLUDE", label: t(`${fc}.effectExclude`) },
  ];

  const footer = (
    <>
      <Button variant="secondary" onClick={handleClose} disabled={creating}>
        {t("common.cancel")}
      </Button>
      <Button
        variant="primary"
        onClick={() => { void handleCreate(); }}
        disabled={!canCreate || creating}
        loading={creating}
        loadingText={t(`${fc}.creating`)}
      >
        {t(`${f}.createRule`)}
      </Button>
    </>
  );

  return (
    <Drawer
      open={open}
      onClose={handleClose}
      title={t(`${fc}.title`)}
      footer={footer}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
        {/* Form fields */}
        <TextField
          label={t(`${fc}.statusId`)}
          value={draft.status_id}
          onChange={(e) => set("status_id", e.target.value)}
          required
          fullWidth
          data-testid="rule-create-status-id"
        />
        <TextField
          label={t(`${fc}.canonical`)}
          value={draft.canonical}
          onChange={(e) => set("canonical", e.target.value)}
          required
          fullWidth
          data-testid="rule-create-canonical"
        />
        <Select
          label={t(`${fc}.matchType`)}
          options={matchTypeOptions}
          value={draft.match_type}
          onChange={(e) => set("match_type", e.target.value)}
          fullWidth
          data-testid="rule-create-match-type"
        />
        <Select
          label={t(`${fc}.effect`)}
          options={effectOptions}
          value={draft.effect}
          onChange={(e) => set("effect", e.target.value)}
          fullWidth
          data-testid="rule-create-effect"
        />
        <TextField
          label={t(`${fc}.searchPattern`)}
          value={draft.search_pattern}
          onChange={(e) => set("search_pattern", e.target.value)}
          disabled={isDefaultMatch}
          fullWidth
          data-testid="rule-create-search-pattern"
        />
        <TextField
          label={t(`${fc}.excludePattern`)}
          value={draft.exclude_pattern}
          onChange={(e) => set("exclude_pattern", e.target.value)}
          fullWidth
          data-testid="rule-create-exclude-pattern"
        />
        <TextField
          label={t(`${fc}.priority`)}
          type="number"
          value={draft.priority}
          onChange={(e) => set("priority", e.target.value)}
          fullWidth
          data-testid="rule-create-priority"
        />
        <TextField
          label={t(`${fc}.note`)}
          value={draft.note}
          onChange={(e) => set("note", e.target.value)}
          fullWidth
          data-testid="rule-create-note"
        />

        {/* Pattern test section */}
        <Card variant="container" density="compact">
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
            <p style={{ margin: 0, fontSize: "var(--font-sm)", fontWeight: "var(--font-weight-medium)", color: "var(--text-primary)" }}>
              {t(`${fc}.testSection`)}
            </p>
            <TextField
              label={t(`${fc}.testInput`)}
              value={testInput}
              onChange={(e) => setTestInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") { void handleTest(); } }}
              fullWidth
              data-testid="rule-create-test-input"
            />
            <Button
              variant="secondary"
              onClick={() => { void handleTest(); }}
              loading={testing}
              disabled={!testInput.trim() || testing}
              data-testid="rule-create-test-button"
            >
              {t(`${fc}.testButton`)}
            </Button>
            {testResult !== null && (
              <div style={{ display: "flex", alignItems: "flex-start", gap: "var(--space-2)", flexWrap: "wrap" }}>
                <Badge variant={testResult.matched ? "success" : "danger"} data-testid="rule-create-test-result">
                  {testResult.matched ? t(`${fc}.matched`) : t(`${fc}.notMatched`)}
                </Badge>
                <span style={{ fontSize: "var(--font-sm)", color: "var(--text-muted)" }}>
                  {testResult.detail}
                </span>
              </div>
            )}
          </div>
        </Card>

        {createError && (
          <p role="alert" style={{ color: "var(--color-error)", fontSize: "var(--font-sm)", margin: 0 }}>
            {createError}
          </p>
        )}
      </div>
    </Drawer>
  );
}
