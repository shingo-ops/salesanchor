/**
 * DateRulesPanel — 日付ルール 4サブタブパネル
 *
 * サブタブ: 指示文 / フォーマット / テスト / 変更履歴
 * API: /api/v1/super-admin/analysis-policies/date-format
 *
 * ADR-027: 全UI文字列は t("key") 経由。
 * ADR-144: 金型コンポーネント（Tabs / Button / TextField / Textarea）のみ使用。
 * 設計§5 C88/C89/C91 準拠。
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Tabs } from "../../../components/Tabs";
import type { TabItem } from "../../../components/Tabs";
import { Button } from "../../../components/Button";
import { TextField } from "../../../components/TextField";
import { Textarea } from "../../../components/Textarea";
import { api, ApiError } from "../../../lib/api";

// ---------------------------------------------------------------------------
// 型定義
// ---------------------------------------------------------------------------

type DateRuleTab = "instruction" | "formats" | "test" | "history";

interface PolicyCurrentResponse {
  active_revision_id: string | null;
  draft_revision_id: string | null;
  current_suite_revision_id: string | null;
  lock_version: number;
  instruction?: string;
  draft_instruction?: string;
}

interface FormatRule {
  id: string;
  format_template: string;
  apply_condition?: string;
  invalidated_at: string | null;
}

interface TestCase {
  id: string;
  source_text: string;
  expected_result: string;
  actual_result?: string;
  is_match?: boolean | null;
  status: "not_run" | "running" | "done" | "error";
}

interface HistoryEntry {
  id: string;
  changed_by: string;
  changed_at: string;
  operation: string;
}

interface TestRunResult {
  run_id: string;
  all_passed: boolean;
  cases: TestCase[];
}

// ---------------------------------------------------------------------------
// API フェッチヘルパー
// ---------------------------------------------------------------------------

const POLICY_PATH = "/super-admin/analysis-policies/date-format";

async function fetchCurrent(): Promise<PolicyCurrentResponse> {
  return api.get<PolicyCurrentResponse>(`${POLICY_PATH}/current`);
}

async function fetchFormats(revisionId: string): Promise<FormatRule[]> {
  return api.get<FormatRule[]>(`${POLICY_PATH}/revisions/${revisionId}/rules?word_kind=format_template`);
}

async function fetchHistory(): Promise<HistoryEntry[]> {
  return api.get<HistoryEntry[]>(`${POLICY_PATH}/history`);
}

async function postTestRun(revisionId: string, suiteRevisionId: string): Promise<{ run_id: string }> {
  return api.post<{ run_id: string }>(`${POLICY_PATH}/test-runs`, {
    revision_id: revisionId,
    suite_revision_id: suiteRevisionId,
    request_key: crypto.randomUUID(),
  });
}

async function fetchTestRun(runId: string): Promise<TestRunResult> {
  return api.get<TestRunResult>(`${POLICY_PATH}/test-runs/${runId}`);
}

async function postActivate(revisionId: string, runId: string, current: PolicyCurrentResponse): Promise<void> {
  await api.post<void>(`${POLICY_PATH}/activate`, {
    revision_id: revisionId,
    run_id: runId,
    expected_active_id: current.active_revision_id,
    lock_version: current.lock_version,
    request_key: crypto.randomUUID(),
  });
}

async function postDraftRevision(current: PolicyCurrentResponse, instruction: string): Promise<void> {
  await api.post<void>(`${POLICY_PATH}/draft-revisions`, {
    expected_draft_id: current.draft_revision_id,
    expected_active_id: current.active_revision_id,
    lock_version: current.lock_version,
    changes: [{ type: "instruction", value: instruction }],
    request_key: crypto.randomUUID(),
  });
}

// ---------------------------------------------------------------------------
// サブコンポーネント: 指示文タブ
// ---------------------------------------------------------------------------

interface InstructionTabProps {
  current: PolicyCurrentResponse | null;
  loading: boolean;
  error: string | null;
  onReload: () => void;
}

function InstructionTab({ current, loading, error, onReload }: InstructionTabProps) {
  const { t } = useTranslation();
  const [draft, setDraft] = useState<string>("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  if (loading) return <p>{t("common.loading")}</p>;
  if (error) return <p style={{ color: "var(--color-error)" }}>{error}</p>;
  if (!current) return null;

  async function handleSaveDraft() {
    if (!current) return;
    setSaving(true);
    setSaveError(null);
    try {
      await postDraftRevision(current, draft);
      onReload();
    } catch (e) {
      const msg = e instanceof ApiError && e.status === 409
        ? t("analysisRules.errors.conflict")
        : t("analysisRules.errors.unknown");
      setSaveError(msg);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
      <div style={{ display: "flex", gap: "var(--space-2)", alignItems: "center" }}>
        {current.active_revision_id && (
          <span style={{ fontSize: "var(--font-xs)", color: "var(--text-muted)", background: "var(--bg-subtle)", padding: "2px var(--space-2)", borderRadius: "var(--radius-sm)" }}>
            {t("analysisRules.dateRule.activeBadge")}
          </span>
        )}
        {current.draft_revision_id && (
          <span style={{ fontSize: "var(--font-xs)", color: "var(--accent)", background: "var(--sidebar-item-active-bg)", padding: "2px var(--space-2)", borderRadius: "var(--radius-sm)" }}>
            {t("analysisRules.dateRule.draftBadge")}
          </span>
        )}
      </div>

      <Textarea
        label={t("analysisRules.dateRule.instructionLabel")}
        value={draft || current.draft_instruction || current.instruction || ""}
        onChange={(e) => setDraft(e.target.value)}
        rows={8}
      />

      {saveError && (
        <p style={{ color: "var(--color-error)", fontSize: "var(--font-sm)" }}>{saveError}</p>
      )}

      <div style={{ display: "flex", gap: "var(--space-2)" }}>
        <Button variant="secondary" onClick={handleSaveDraft} loading={saving}>
          {t("analysisRules.dateRule.saveDraft")}
        </Button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// サブコンポーネント: フォーマットタブ（C88）
// ---------------------------------------------------------------------------

interface FormatsTabProps {
  current: PolicyCurrentResponse | null;
  loading: boolean;
  error: string | null;
}

function FormatsTab({ current, loading, error }: FormatsTabProps) {
  const { t } = useTranslation();
  const [formats, setFormats] = useState<FormatRule[]>([]);
  const [fmtLoading, setFmtLoading] = useState(false);
  const [fmtError, setFmtError] = useState<string | null>(null);
  const [newTemplate, setNewTemplate] = useState("");

  async function loadFormats() {
    if (!current?.draft_revision_id && !current?.active_revision_id) return;
    const revId = current.draft_revision_id ?? current.active_revision_id ?? "";
    setFmtLoading(true);
    setFmtError(null);
    try {
      const data = await fetchFormats(revId);
      setFormats(data);
    } catch {
      setFmtError(t("analysisRules.errors.unknown"));
    } finally {
      setFmtLoading(false);
    }
  }

  if (loading) return <p>{t("common.loading")}</p>;
  if (error) return <p style={{ color: "var(--color-error)" }}>{error}</p>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
      <div style={{ display: "flex", gap: "var(--space-2)", alignItems: "flex-end" }}>
        <TextField
          label={t("analysisRules.dateRule.formatsTitle")}
          value={newTemplate}
          onChange={(e) => setNewTemplate(e.target.value)}
          placeholder={t("analysisRules.dateRule.formatTemplatePlaceholder")}
        />
        <Button variant="secondary" onClick={loadFormats} loading={fmtLoading}>
          {t("common.search") ?? "Search"}
        </Button>
      </div>

      {fmtError && (
        <p style={{ color: "var(--color-error)", fontSize: "var(--font-sm)" }}>{fmtError}</p>
      )}

      {formats.length === 0 && !fmtLoading && (
        <p style={{ color: "var(--text-muted)", fontSize: "var(--font-sm)" }}>
          {t("common.noResults") ?? "No results"}
        </p>
      )}

      <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
        {formats.map((f) => (
          <li
            key={f.id}
            style={{
              display: "flex",
              gap: "var(--space-4)",
              padding: "var(--space-2) var(--space-3)",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border)",
              opacity: f.invalidated_at ? 0.5 : 1,
              background: "var(--bg-card)",
            }}
          >
            <span style={{ flex: 1, fontSize: "var(--font-sm)", color: "var(--text-primary)" }}>
              {f.format_template}
            </span>
            <span style={{ flex: 1, fontSize: "var(--font-sm)", color: "var(--text-muted)" }}>
              {f.apply_condition ?? "—"}
            </span>
            {f.invalidated_at && (
              <span style={{ fontSize: "var(--font-xs)", color: "var(--text-muted)" }}>
                {t("analysisRules.dateRule.invalidatedLabel")}
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

// ---------------------------------------------------------------------------
// サブコンポーネント: テストタブ（C91: テスト未合格版は本番適用不可）
// ---------------------------------------------------------------------------

interface TestTabProps {
  current: PolicyCurrentResponse | null;
  loading: boolean;
  error: string | null;
  onTestRunComplete: (runId: string, allPassed: boolean) => void;
}

function TestTab({ current, loading, error, onTestRunComplete }: TestTabProps) {
  const { t } = useTranslation();
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);

  if (loading) return <p>{t("common.loading")}</p>;
  if (error) return <p style={{ color: "var(--color-error)" }}>{error}</p>;

  async function handleRunAll() {
    if (!current?.draft_revision_id && !current?.active_revision_id) return;
    if (!current?.current_suite_revision_id) return;
    const revId = current.draft_revision_id ?? current.active_revision_id ?? "";
    setRunning(true);
    setRunError(null);
    try {
      const { run_id } = await postTestRun(revId, current.current_suite_revision_id);
      const result = await fetchTestRun(run_id);
      setTestCases(result.cases);
      onTestRunComplete(run_id, result.all_passed);
    } catch {
      setRunError(t("analysisRules.errors.unknown"));
    } finally {
      setRunning(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
      <div style={{ display: "flex", gap: "var(--space-2)" }}>
        <Button variant="primary" onClick={handleRunAll} loading={running}>
          {t("analysisRules.dateRule.testRunAll")}
        </Button>
      </div>

      {runError && (
        <p style={{ color: "var(--color-error)", fontSize: "var(--font-sm)" }}>{runError}</p>
      )}

      {running && (
        <p style={{ color: "var(--text-muted)", fontSize: "var(--font-sm)" }}>
          {t("analysisRules.dateRule.testStatusRunning")}
        </p>
      )}

      {testCases.length > 0 && (
        <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
          {testCases.map((tc) => (
            <li
              key={tc.id}
              style={{
                padding: "var(--space-3)",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border)",
                background: "var(--bg-card)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "var(--space-1)" }}>
                <span style={{ fontSize: "var(--font-sm)", fontWeight: "var(--font-weight-bold)", color: "var(--text-primary)" }}>
                  {tc.source_text}
                </span>
                <span
                  style={{
                    fontSize: "var(--font-xs)",
                    color: tc.is_match === true ? "var(--color-success)" : tc.is_match === false ? "var(--color-error)" : "var(--text-muted)",
                  }}
                >
                  {tc.is_match === true
                    ? t("analysisRules.dateRule.testResultMatch")
                    : tc.is_match === false
                    ? t("analysisRules.dateRule.testResultMismatch")
                    : t("analysisRules.dateRule.testStatusNotRun")}
                </span>
              </div>
              <div style={{ fontSize: "var(--font-xs)", color: "var(--text-muted)", display: "flex", gap: "var(--space-4)" }}>
                <span>{t("analysisRules.dateRule.testResultExpected")}: {tc.expected_result}</span>
                {tc.actual_result && (
                  <span>{t("analysisRules.dateRule.testResultActual")}: {tc.actual_result}</span>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// サブコンポーネント: 変更履歴タブ
// ---------------------------------------------------------------------------

function HistoryTab() {
  const { t } = useTranslation();
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [histLoading, setHistLoading] = useState(false);
  const [histError, setHistError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  async function handleLoad() {
    setHistLoading(true);
    setHistError(null);
    try {
      const data = await fetchHistory();
      setHistory(data);
      setLoaded(true);
    } catch {
      setHistError(t("analysisRules.errors.unknown"));
    } finally {
      setHistLoading(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
      {!loaded && (
        <Button variant="secondary" onClick={handleLoad} loading={histLoading}>
          {t("analysisRules.dateRule.historyTitle")}
        </Button>
      )}

      {histError && (
        <p style={{ color: "var(--color-error)", fontSize: "var(--font-sm)" }}>{histError}</p>
      )}

      {history.length > 0 && (
        <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
          {history.map((h) => (
            <li
              key={h.id}
              style={{
                padding: "var(--space-3)",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border)",
                background: "var(--bg-card)",
                display: "grid",
                gridTemplateColumns: "1fr 1fr auto",
                gap: "var(--space-2)",
                fontSize: "var(--font-sm)",
              }}
            >
              <span style={{ color: "var(--text-primary)" }}>
                {t("analysisRules.dateRule.historyWho")}: {h.changed_by}
              </span>
              <span style={{ color: "var(--text-muted)" }}>
                {t("analysisRules.dateRule.historyAt")}: {h.changed_at}
              </span>
              <span style={{ color: "var(--text-muted)" }}>
                {t("analysisRules.dateRule.historyOp")}: {h.operation}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// サブコンポーネント: 有効化（C91: テスト未合格時非活性）
// ---------------------------------------------------------------------------

interface ActivateTabProps {
  current: PolicyCurrentResponse | null;
  loading: boolean;
  error: string | null;
  lastRunId: string | null;
  lastRunPassed: boolean;
  onActivated: () => void;
}

function ActivateSection({ current, loading, error, lastRunId, lastRunPassed, onActivated }: ActivateTabProps) {
  const { t } = useTranslation();
  const [activating, setActivating] = useState(false);
  const [activateError, setActivateError] = useState<string | null>(null);

  if (loading || error || !current) return null;

  const canActivate = lastRunId !== null && lastRunPassed;
  const revisionId = current.draft_revision_id ?? current.active_revision_id ?? "";

  async function handleActivate() {
    if (!current || !lastRunId) return;
    setActivating(true);
    setActivateError(null);
    try {
      await postActivate(revisionId, lastRunId, current);
      onActivated();
    } catch (e) {
      const msg = e instanceof ApiError && e.status === 409
        ? t("analysisRules.errors.conflict")
        : t("analysisRules.errors.unknown");
      setActivateError(msg);
    } finally {
      setActivating(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
      {!canActivate && (
        <p style={{ fontSize: "var(--font-sm)", color: "var(--text-muted)" }}>
          {t("analysisRules.dateRule.activateBtnDisabledHint")}
        </p>
      )}
      {activateError && (
        <p style={{ color: "var(--color-error)", fontSize: "var(--font-sm)" }}>{activateError}</p>
      )}
      <div>
        <Button
          variant="primary"
          onClick={handleActivate}
          loading={activating}
          disabled={!canActivate}
        >
          {t("analysisRules.dateRule.activateBtn")}
        </Button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// メインコンポーネント
// ---------------------------------------------------------------------------

export function DateRulesPanel() {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<DateRuleTab>("instruction");
  const [current, setCurrent] = useState<PolicyCurrentResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRunId, setLastRunId] = useState<string | null>(null);
  const [lastRunPassed, setLastRunPassed] = useState(false);

  async function loadCurrent() {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchCurrent();
      setCurrent(data);
    } catch (e) {
      const status = e instanceof ApiError ? e.status : 0;
      if (status === 401 || status === 403) {
        setError(t("analysisRules.errors.unauthorized"));
      } else if (status === 503) {
        setError(t("analysisRules.errors.serverUnavailable"));
      } else {
        setError(t("analysisRules.errors.unknown"));
      }
    } finally {
      setLoading(false);
    }
  }

  // 初回ロード
  useState(() => {
    void loadCurrent();
  });

  const tabItems: TabItem<DateRuleTab>[] = [
    { key: "instruction", label: t("analysisRules.tabs.instruction") },
    { key: "formats",     label: t("analysisRules.tabs.formats") },
    { key: "test",        label: t("analysisRules.tabs.test") },
    { key: "history",     label: t("analysisRules.tabs.history") },
  ];

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        padding: "var(--space-4)",
        gap: "var(--space-4)",
        overflowY: "auto",
      }}
    >
      <h3
        style={{
          margin: 0,
          fontSize: "var(--font-lg)",
          fontWeight: "var(--font-weight-bold)",
          color: "var(--text-primary)",
        }}
      >
        {t("analysisRules.dateRule.title")}
      </h3>

      <Tabs<DateRuleTab>
        items={tabItems}
        activeKey={activeTab}
        onChange={setActiveTab}
        variant="underline"
        size="sm"
      />

      <div style={{ flex: 1, minHeight: 0 }}>
        {activeTab === "instruction" && (
          <InstructionTab
            current={current}
            loading={loading}
            error={error}
            onReload={loadCurrent}
          />
        )}
        {activeTab === "formats" && (
          <FormatsTab
            current={current}
            loading={loading}
            error={error}
          />
        )}
        {activeTab === "test" && (
          <>
            <TestTab
              current={current}
              loading={loading}
              error={error}
              onTestRunComplete={(runId, allPassed) => {
                setLastRunId(runId);
                setLastRunPassed(allPassed);
              }}
            />
            {/* テストタブ下部: 有効化操作（C91: テスト未合格時非活性）*/}
            <div style={{ marginTop: "var(--space-6)", borderTop: "1px solid var(--border)", paddingTop: "var(--space-4)" }}>
              <ActivateSection
                current={current}
                loading={loading}
                error={error}
                lastRunId={lastRunId}
                lastRunPassed={lastRunPassed}
                onActivated={loadCurrent}
              />
            </div>
          </>
        )}
        {activeTab === "history" && <HistoryTab />}
      </div>
    </div>
  );
}
