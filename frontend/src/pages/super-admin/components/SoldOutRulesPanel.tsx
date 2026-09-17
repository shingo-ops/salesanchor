/**
 * SoldOutRulesPanel — 完売ルール 4サブタブパネル
 *
 * サブタブ: 指示文 / 検索・除外ワード / テスト / 変更履歴
 * API: /api/v1/super-admin/analysis-policies/sold-out
 *
 * ADR-027: 全UI文字列は t("key") 経由。
 * ADR-144: 金型コンポーネント（Tabs / Button / TextField / Textarea）のみ使用。
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Tabs } from "../../../components/Tabs";
import type { TabItem } from "../../../components/Tabs";
import { Button } from "../../../components/Button";
import { TextField } from "../../../components/TextField";
import { Textarea } from "../../../components/Textarea";
import { Select } from "../../../components/Select";

// ---------------------------------------------------------------------------
// 型定義
// ---------------------------------------------------------------------------

type SoldOutTab = "instruction" | "words" | "test" | "history";

interface PolicyCurrentResponse {
  active_revision_id: string | null;
  draft_revision_id: string | null;
  current_suite_revision_id: string | null;
  lock_version: number;
  instruction?: string;
  draft_instruction?: string;
}

interface RuleWord {
  id: string;
  search_word: string;
  exclude_word?: string;
  invalidated_at: string | null;
}

interface TestCase {
  id: string;
  source_text: string;
  post_date?: string;
  expected_result: string;
  actual_result?: string;
  is_match?: boolean | null;
  evidence?: string;
  status: "not_run" | "running" | "done" | "error";
}

interface HistoryEntry {
  id: string;
  changed_by: string;
  changed_at: string;
  operation: string;
  diff_before?: string;
  diff_after?: string;
}

interface TestRunResult {
  run_id: string;
  all_passed: boolean;
  cases: TestCase[];
}

// ---------------------------------------------------------------------------
// API フェッチヘルパー
// ---------------------------------------------------------------------------

const BASE = "/api/v1/super-admin/analysis-policies/sold-out";

async function fetchCurrent(): Promise<PolicyCurrentResponse> {
  const res = await fetch(`${BASE}/current`, { credentials: "include" });
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

async function fetchWords(revisionId: string, q: string, wordKind: string): Promise<RuleWord[]> {
  const params = new URLSearchParams({ q, word_kind: wordKind });
  const res = await fetch(`${BASE}/revisions/${revisionId}/rules?${params.toString()}`, { credentials: "include" });
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

async function fetchHistory(): Promise<HistoryEntry[]> {
  const res = await fetch(`${BASE}/history`, { credentials: "include" });
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

async function postTestRun(revisionId: string, suiteRevisionId: string): Promise<{ run_id: string }> {
  const body = {
    revision_id: revisionId,
    suite_revision_id: suiteRevisionId,
    request_key: crypto.randomUUID(),
  };
  const res = await fetch(`${BASE}/test-runs`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

async function fetchTestRun(runId: string): Promise<TestRunResult> {
  const res = await fetch(`${BASE}/test-runs/${runId}`, { credentials: "include" });
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

async function postActivate(revisionId: string, runId: string, current: PolicyCurrentResponse): Promise<void> {
  const body = {
    revision_id: revisionId,
    run_id: runId,
    expected_active_id: current.active_revision_id,
    lock_version: current.lock_version,
    request_key: crypto.randomUUID(),
  };
  const res = await fetch(`${BASE}/activate`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (res.status === 409) throw new Error("conflict");
  if (!res.ok) throw new Error(`${res.status}`);
}

async function postDraftRevision(current: PolicyCurrentResponse, instruction: string): Promise<void> {
  const body = {
    expected_draft_id: current.draft_revision_id,
    expected_active_id: current.active_revision_id,
    lock_version: current.lock_version,
    changes: [{ type: "instruction", value: instruction }],
    request_key: crypto.randomUUID(),
  };
  const res = await fetch(`${BASE}/draft-revisions`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (res.status === 409) throw new Error("conflict");
  if (!res.ok) throw new Error(`${res.status}`);
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
      const msg = e instanceof Error && e.message === "conflict"
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
            {t("analysisRules.soldOut.activeBadge")}
          </span>
        )}
        {current.draft_revision_id && (
          <span style={{ fontSize: "var(--font-xs)", color: "var(--accent)", background: "var(--sidebar-item-active-bg)", padding: "2px var(--space-2)", borderRadius: "var(--radius-sm)" }}>
            {t("analysisRules.soldOut.draftBadge")}
          </span>
        )}
      </div>

      <Textarea
        label={t("analysisRules.soldOut.instructionLabel")}
        value={draft || current.draft_instruction || current.instruction || ""}
        onChange={(e) => setDraft(e.target.value)}
        rows={8}
      />

      {saveError && (
        <p style={{ color: "var(--color-error)", fontSize: "var(--font-sm)" }}>{saveError}</p>
      )}

      <div style={{ display: "flex", gap: "var(--space-2)" }}>
        <Button variant="secondary" onClick={handleSaveDraft} loading={saving}>
          {t("analysisRules.soldOut.saveDraft")}
        </Button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// サブコンポーネント: 検索・除外ワードタブ
// ---------------------------------------------------------------------------

interface WordsTabProps {
  current: PolicyCurrentResponse | null;
  loading: boolean;
  error: string | null;
}

function WordsTab({ current, loading, error }: WordsTabProps) {
  const { t } = useTranslation();
  const [words, setWords] = useState<RuleWord[]>([]);
  const [wordsLoading, setWordsLoading] = useState(false);
  const [wordsError, setWordsError] = useState<string | null>(null);
  const [searchQ, setSearchQ] = useState("");
  const [wordKind, setWordKind] = useState("both");

  async function loadWords() {
    if (!current?.draft_revision_id && !current?.active_revision_id) return;
    const revId = current.draft_revision_id ?? current.active_revision_id ?? "";
    setWordsLoading(true);
    setWordsError(null);
    try {
      const data = await fetchWords(revId, searchQ, wordKind);
      setWords(data);
    } catch {
      setWordsError(t("analysisRules.errors.unknown"));
    } finally {
      setWordsLoading(false);
    }
  }

  if (loading) return <p>{t("common.loading")}</p>;
  if (error) return <p style={{ color: "var(--color-error)" }}>{error}</p>;

  const wordKindOptions = [
    { value: "both", label: t("analysisRules.soldOut.wordKindAll") },
    { value: "search", label: t("analysisRules.soldOut.wordKindSearch") },
    { value: "exclude", label: t("analysisRules.soldOut.wordKindExclude") },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
      <div style={{ display: "flex", gap: "var(--space-2)", alignItems: "flex-end" }}>
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
      </div>

      {wordsError && (
        <p style={{ color: "var(--color-error)", fontSize: "var(--font-sm)" }}>{wordsError}</p>
      )}

      {words.length === 0 && !wordsLoading && (
        <p style={{ color: "var(--text-muted)", fontSize: "var(--font-sm)" }}>
          {t("common.noResults") ?? "No results"}
        </p>
      )}

      <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
        {words.map((w) => (
          <li
            key={w.id}
            style={{
              display: "flex",
              gap: "var(--space-4)",
              padding: "var(--space-2) var(--space-3)",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border)",
              opacity: w.invalidated_at ? 0.5 : 1,
              background: "var(--bg-card)",
            }}
          >
            <span style={{ flex: 1, fontSize: "var(--font-sm)", color: "var(--text-primary)" }}>
              {w.search_word}
            </span>
            <span style={{ flex: 1, fontSize: "var(--font-sm)", color: "var(--text-muted)" }}>
              {w.exclude_word ?? "—"}
            </span>
            {w.invalidated_at && (
              <span style={{ fontSize: "var(--font-xs)", color: "var(--text-muted)" }}>
                {t("analysisRules.soldOut.invalidatedLabel")}
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

// ---------------------------------------------------------------------------
// サブコンポーネント: テストタブ
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
      // ポーリング: 結果を取得
      const result = await fetchTestRun(run_id);
      setTestCases(result.cases);
      onTestRunComplete(run_id, result.all_passed);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "unknown";
      setRunError(msg === "conflict"
        ? t("analysisRules.errors.testExpired")
        : t("analysisRules.errors.unknown"));
    } finally {
      setRunning(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
      <div style={{ display: "flex", gap: "var(--space-2)" }}>
        <Button variant="primary" onClick={handleRunAll} loading={running}>
          {t("analysisRules.soldOut.testRunAll")}
        </Button>
      </div>

      {runError && (
        <p style={{ color: "var(--color-error)", fontSize: "var(--font-sm)" }}>{runError}</p>
      )}

      {running && (
        <p style={{ color: "var(--text-muted)", fontSize: "var(--font-sm)" }}>
          {t("analysisRules.soldOut.testStatusRunning")}
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
                    ? t("analysisRules.soldOut.testResultMatch")
                    : tc.is_match === false
                    ? t("analysisRules.soldOut.testResultMismatch")
                    : t("analysisRules.soldOut.testStatusNotRun")}
                </span>
              </div>
              <div style={{ fontSize: "var(--font-xs)", color: "var(--text-muted)", display: "flex", gap: "var(--space-4)" }}>
                <span>{t("analysisRules.soldOut.testResultExpected")}: {tc.expected_result}</span>
                {tc.actual_result && (
                  <span>{t("analysisRules.soldOut.testResultActual")}: {tc.actual_result}</span>
                )}
              </div>
              {tc.evidence && (
                <p style={{ fontSize: "var(--font-xs)", color: "var(--text-muted)", marginTop: "var(--space-1)" }}>
                  {t("analysisRules.soldOut.testResultEvidence")}: {tc.evidence}
                </p>
              )}
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
          {t("analysisRules.soldOut.historyTitle")}
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
                {t("analysisRules.soldOut.historyWho")}: {h.changed_by}
              </span>
              <span style={{ color: "var(--text-muted)" }}>
                {t("analysisRules.soldOut.historyAt")}: {h.changed_at}
              </span>
              <span style={{ color: "var(--text-muted)" }}>
                {t("analysisRules.soldOut.historyOp")}: {h.operation}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// サブコンポーネント: 有効化タブ（C91: テスト未合格時非活性）
// ---------------------------------------------------------------------------

interface ActivateTabProps {
  current: PolicyCurrentResponse | null;
  loading: boolean;
  error: string | null;
  lastRunId: string | null;
  lastRunPassed: boolean;
  onActivated: () => void;
}

function ActivateTab({ current, loading, error, lastRunId, lastRunPassed, onActivated }: ActivateTabProps) {
  const { t } = useTranslation();
  const [activating, setActivating] = useState(false);
  const [activateError, setActivateError] = useState<string | null>(null);

  if (loading) return <p>{t("common.loading")}</p>;
  if (error) return <p style={{ color: "var(--color-error)" }}>{error}</p>;

  const canActivate = current !== null && lastRunId !== null && lastRunPassed;
  const revisionId = current?.draft_revision_id ?? current?.active_revision_id ?? "";

  async function handleActivate() {
    if (!current || !lastRunId) return;
    setActivating(true);
    setActivateError(null);
    try {
      await postActivate(revisionId, lastRunId, current);
      onActivated();
    } catch (e) {
      const msg = e instanceof Error && e.message === "conflict"
        ? t("analysisRules.errors.conflict")
        : t("analysisRules.errors.unknown");
      setActivateError(msg);
    } finally {
      setActivating(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
      <div>
        <p style={{ fontSize: "var(--font-sm)", color: "var(--text-muted)", marginBottom: "var(--space-2)" }}>
          {t("analysisRules.soldOut.activateRevisionLabel")}: {revisionId || "—"}
        </p>
        {lastRunId && (
          <p style={{ fontSize: "var(--font-sm)", color: "var(--text-muted)", marginBottom: "var(--space-2)" }}>
            {t("analysisRules.soldOut.activateRunLabel")}: {lastRunId}
          </p>
        )}
      </div>

      {!canActivate && (
        <p style={{ fontSize: "var(--font-sm)", color: "var(--text-muted)" }}>
          {t("analysisRules.soldOut.activateBtnDisabledHint")}
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
          {t("analysisRules.soldOut.activateBtn")}
        </Button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// メインコンポーネント
// ---------------------------------------------------------------------------

export function SoldOutRulesPanel() {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<SoldOutTab>("instruction");
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
      const status = e instanceof Error ? e.message : "";
      if (status === "401" || status === "403") {
        setError(t("analysisRules.errors.unauthorized"));
      } else if (status === "503") {
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

  const tabItems: TabItem<SoldOutTab>[] = [
    { key: "instruction", label: t("analysisRules.tabs.instruction") },
    { key: "words",       label: t("analysisRules.tabs.words") },
    { key: "test",        label: t("analysisRules.tabs.test") },
    { key: "history",     label: t("analysisRules.tabs.history") },
  ];

  // 有効化パネルは「テスト」タブの下部に統合して表示する（設計§5に準拠）

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
        {t("analysisRules.soldOut.title")}
      </h3>

      <Tabs<SoldOutTab>
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
        {activeTab === "words" && (
          <WordsTab
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
              <ActivateTab
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
