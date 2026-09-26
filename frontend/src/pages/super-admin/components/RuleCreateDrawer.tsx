/**
 * RuleCreateDrawer — ルール新規作成ドロワー（簡略版）
 *
 * 変更点:
 *  - status_id は backend で自動採番（フォームから除去）
 *  - match_type は LITERAL に固定（フォームから除去）
 *  - exclude_pattern は空文字に固定（フォームから除去）
 *  - canonical はDBから取得した Select に変更（effect を自動セット）
 *  - テストゲート: 判定合格後のみ作成ボタンが有効になる
 *
 * ADR-027: 全UI文字列は t("key") 経由。
 * ADR-144: 金型クラスのみ使用。
 */
import { useState, useEffect } from "react";
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

interface CanonicalOption {
  canonical: string;
  effect: string;
}

interface FormDraft {
  canonical: string;
  effect: string;
  searchPattern: string;
  priority: string;
  note: string;
}

const emptyDraft: FormDraft = {
  canonical: "",
  effect: "OUTPUT",
  searchPattern: "",
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
  const [testPassed, setTestPassed] = useState(false);
  const [canonicals, setCanonicals] = useState<CanonicalOption[]>([]);

  // Load canonical options from backend when drawer opens
  useEffect(() => {
    if (!open) return;
    api
      .get<CanonicalOption[]>("/super-admin/rule-tests/canonicals")
      .then((data) => setCanonicals(data))
      .catch(() => {
        /* best-effort — user can still select from empty list */
      });
  }, [open]);

  const resetTestState = () => {
    setTestResult(null);
    setTestPassed(false);
  };

  const set = (key: keyof FormDraft, value: string) => {
    setDraft((prev: FormDraft) => ({ ...prev, [key]: value }));
    resetTestState();
  };

  const handleCanonicalChange = (value: string) => {
    const found = canonicals.find((c) => c.canonical === value);
    setDraft((prev) => ({
      ...prev,
      canonical: value,
      effect: found ? found.effect : prev.effect,
    }));
    resetTestState();
  };

  const handleTest = async () => {
    if (!testInput.trim()) return;
    setTesting(true);
    setTestResult(null);
    setTestPassed(false);
    try {
      const result = await api.post<PreviewResponse>("/super-admin/status-master/preview", {
        match_type: "LITERAL",
        search_pattern: draft.searchPattern,
        input_text: testInput,
      });
      setTestResult(result);
      if (result.matched) {
        setTestPassed(true);
      }
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
        canonical: draft.canonical,
        search_pattern: draft.searchPattern,
        exclude_pattern: "",
        match_type: "LITERAL",
        effect: draft.effect,
        priority: Number(draft.priority) || 0,
        enabled: false,
        note: draft.note,
      });
      setDraft(emptyDraft);
      setTestInput("");
      setTestResult(null);
      setTestPassed(false);
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
    setTestPassed(false);
    setCreateError("");
    onClose();
  };

  const effectOptions = [
    { value: "OUTPUT", label: t(`${fc}.effectOutput`) },
    { value: "EXCLUDE", label: t(`${fc}.effectExclude`) },
  ];

  const canonicalOptions = canonicals.map((c) => ({
    value: c.canonical,
    label: c.canonical,
  }));

  const footer = (
    <>
      <Button variant="secondary" onClick={handleClose} disabled={creating}>
        {t("common.cancel")}
      </Button>
      <Button
        variant="primary"
        onClick={() => { void handleCreate(); }}
        disabled={!testPassed || creating}
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
        {/* 1. ステータス (canonical) */}
        <Select
          label={t(`${fc}.canonical`)}
          options={canonicalOptions}
          value={draft.canonical}
          onChange={(e) => handleCanonicalChange(e.target.value)}
          placeholder={t(`${f}.test.expectedCanonicalPlaceholder`)}
          fullWidth
          required
          data-testid="rule-create-canonical"
        />

        {/* 2. 除外 / 検索 (effect) */}
        <Select
          label={t(`${fc}.effect`)}
          options={effectOptions}
          value={draft.effect}
          onChange={(e) => set("effect", e.target.value)}
          fullWidth
          data-testid="rule-create-effect"
        />

        {/* 3. ワード (search_pattern) */}
        <TextField
          label={t(`${fc}.searchPattern`)}
          value={draft.searchPattern}
          onChange={(e) => set("searchPattern", e.target.value)}
          fullWidth
          data-testid="rule-create-search-pattern"
        />

        {/* 4. 優先度 (priority) */}
        <TextField
          label={t(`${fc}.priority`)}
          type="number"
          value={draft.priority}
          onChange={(e) => set("priority", e.target.value)}
          fullWidth
          data-testid="rule-create-priority"
        />

        {/* 5. メモ (note) */}
        <TextField
          label={t(`${fc}.note`)}
          value={draft.note}
          onChange={(e) => set("note", e.target.value)}
          fullWidth
          data-testid="rule-create-note"
        />

        {/* 6. パターンテスト section */}
        <Card variant="container" density="compact">
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
            <p style={{ margin: 0, fontSize: "var(--font-sm)", fontWeight: "var(--font-weight-medium)", color: "var(--text-primary)" }}>
              {t(`${fc}.testSection`)}
            </p>
            <TextField
              label={t(`${fc}.testInput`)}
              value={testInput}
              onChange={(e) => {
                setTestInput(e.target.value);
                resetTestState();
              }}
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

        {/* テストゲートメッセージ */}
        {!testPassed && (
          <p style={{ margin: 0, fontSize: "var(--font-sm)", color: "var(--text-muted)" }}>
            {t(`${fc}.testRequired`)}
          </p>
        )}
        {testPassed && (
          <p style={{ margin: 0, fontSize: "var(--font-sm)", color: "var(--color-success)" }}>
            {t(`${fc}.testPassed`)}
          </p>
        )}

        {createError && (
          <p role="alert" style={{ color: "var(--color-error)", fontSize: "var(--font-sm)", margin: 0 }}>
            {createError}
          </p>
        )}
      </div>
    </Drawer>
  );
}
