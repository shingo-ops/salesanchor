/**
 * RuleTestPanel — ルールテスト実行パネル
 *
 * テストケース管理 + テスト実行 + 結果表示。
 * tcg_status_master のルールが正しく動作するか検証する。
 *
 * ADR-027: 全UI文字列は t("key") 経由。
 * ADR-144: 金型クラスのみ使用。
 */
import { useCallback, useEffect, useRef, useState } from "react";
import type { MouseEvent } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../../lib/api";
import { DataTable, type DataTableColumn } from "../../../components/DataTable";
import { Badge } from "../../../components/Badge";
import { Button } from "../../../components/Button";
import { TextField } from "../../../components/TextField";
import { EmptyState } from "../../../components/EmptyState";
import { Modal } from "../../../components/Modal";
import ConfirmModal from "../../../components/ConfirmModal";

/* ── 型定義 ──────────────────────────────────────────────────────────────── */

interface TestCase {
  id: number;
  input_text: string;
  expected_canonical: string;
  expected_effect: string | null;
  note: string;
  created_at: string;
}

interface TestRunResult {
  case_id: number;
  input_text: string;
  expected_canonical: string;
  expected_effect: string | null;
  actual_canonical: string | null;
  actual_effect: string | null;
  is_match: boolean;
}

interface TestRun {
  id: string;
  state: string; // pending, running, passed, failed, error
  started_at: string;
  completed_at: string | null;
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  results: TestRunResult[];
}

interface GateStatus {
  gate_open: boolean;
  latest_state: string | null;
}

/* ── ゲートステータスバッジ ─────────────────────────────────────────────── */

function GateBadge({ state }: { state: string | null }) {
  const { t } = useTranslation();
  const f = "ruleManagement.test";

  if (state === "passed") {
    return <Badge variant="success">{t(`${f}.gateOpen`)}</Badge>;
  }
  if (state === "failed") {
    return <Badge variant="danger">{t(`${f}.gateFailed`)}</Badge>;
  }
  if (state === "error") {
    return <Badge variant="danger">{t(`${f}.gateError`)}</Badge>;
  }
  if (state === "pending" || state === "running") {
    return <Badge variant="warning">{t(`${f}.gateRunning`)}</Badge>;
  }
  return <Badge variant="neutral">{t(`${f}.gateNever`)}</Badge>;
}

/* ── メインコンポーネント ────────────────────────────────────────────────── */

export function RuleTestPanel() {
  const { t } = useTranslation();
  const f = "ruleManagement.test";

  const [cases, setCases] = useState<TestCase[]>([]);
  const [latestRun, setLatestRun] = useState<TestRun | null>(null);
  const [gate, setGate] = useState<GateStatus>({ gate_open: false, latest_state: null });
  const [error, setError] = useState("");

  // 追加モーダル
  const [addOpen, setAddOpen] = useState(false);
  const [addInputText, setAddInputText] = useState("");
  const [addExpectedCanonical, setAddExpectedCanonical] = useState("");
  const [addEffectExcluded, setAddEffectExcluded] = useState(false);
  const [addNote, setAddNote] = useState("");
  const [addSaving, setAddSaving] = useState(false);
  const [addError, setAddError] = useState("");

  // 削除確認
  const [deleteTargetId, setDeleteTargetId] = useState<number | null>(null);

  // テスト実行中
  const [running, setRunning] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  /* ── データ取得 ── */

  const loadCases = useCallback(async () => {
    try {
      const data = await api.get<TestCase[]>("/super-admin/rule-tests/cases");
      setCases(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    }
  }, [t]);

  const loadLatestRun = useCallback(async () => {
    try {
      const data = await api.get<TestRun | null>("/super-admin/rule-tests/runs/latest");
      setLatestRun(data);
    } catch {
      // latest run が存在しない場合は null のまま
    }
  }, []);

  const loadGate = useCallback(async () => {
    try {
      const data = await api.get<GateStatus>("/super-admin/rule-tests/gate");
      setGate(data);
    } catch {
      // gate 取得失敗は無視
    }
  }, []);

  useEffect(() => {
    void loadCases();
    void loadLatestRun();
    void loadGate();
  }, [loadCases, loadLatestRun, loadGate]);

  /* ── ポーリング ── */

  const stopPolling = useCallback(() => {
    if (pollRef.current !== null) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const startPolling = useCallback(() => {
    stopPolling();
    pollRef.current = setInterval(() => {
      void loadLatestRun().then(() => {
        setLatestRun((prev: TestRun | null) => {
          if (prev && prev.state !== "pending" && prev.state !== "running") {
            stopPolling();
            setRunning(false);
            void loadGate();
          }
          return prev;
        });
      });
    }, 2000);
  }, [stopPolling, loadLatestRun, loadGate]);

  useEffect(() => () => stopPolling(), [stopPolling]);

  /* ── テスト実行 ── */

  const handleRunTests = async () => {
    setRunning(true);
    setError("");
    try {
      await api.post("/super-admin/rule-tests/run", {});
      await loadLatestRun();
      startPolling();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
      setRunning(false);
    }
  };

  /* ── テストケース追加 ── */

  const resetAddForm = () => {
    setAddInputText("");
    setAddExpectedCanonical("");
    setAddEffectExcluded(false);
    setAddNote("");
    setAddError("");
  };

  const handleAddCase = async () => {
    if (!addInputText.trim() || !addExpectedCanonical.trim()) {
      setAddError(t("common.required"));
      return;
    }
    setAddSaving(true);
    setAddError("");
    try {
      await api.post("/super-admin/rule-tests/cases", {
        input_text: addInputText.trim(),
        expected_canonical: addExpectedCanonical.trim(),
        expected_effect: addEffectExcluded ? "excluded" : null,
        note: addNote.trim(),
      });
      resetAddForm();
      setAddOpen(false);
      await loadCases();
    } catch (e) {
      setAddError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      setAddSaving(false);
    }
  };

  /* ── テストケース削除 ── */

  const handleDeleteConfirm = async () => {
    if (deleteTargetId === null) return;
    try {
      await api.delete(`/super-admin/rule-tests/cases/${deleteTargetId}`);
      await loadCases();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      setDeleteTargetId(null);
    }
  };

  /* ── テーブル列定義（テストケース） ── */

  const caseColumns: DataTableColumn<TestCase>[] = [
    { key: "input_text", header: t(`${f}.inputText`) },
    { key: "expected_canonical", header: t(`${f}.expectedCanonical`) },
    {
      key: "expected_effect",
      header: t(`${f}.expectedEffect`),
      renderCell: (row) =>
        row.expected_effect === "excluded" ? (
          <Badge variant="danger">{t(`${f}.expectedEffectExcluded`)}</Badge>
        ) : (
          <Badge variant="neutral">{t(`${f}.expectedEffectNone`)}</Badge>
        ),
    },
    { key: "note", header: t(`${f}.note`) },
    {
      key: "id",
      header: "",
      width: "60px",
      renderCell: (row) => (
        <Button
          variant="danger"
          size="sm"
          onClick={(e: MouseEvent<HTMLButtonElement>) => {
            e.stopPropagation();
            setDeleteTargetId(row.id);
          }}
        >
          {t("common.delete")}
        </Button>
      ),
    },
  ];

  /* ── テーブル列定義（テスト結果） ── */

  const resultColumns: DataTableColumn<TestRunResult>[] = [
    { key: "input_text", header: t(`${f}.inputText`) },
    { key: "expected_canonical", header: t(`${f}.expectedCanonical`) },
    { key: "actual_canonical", header: t(`${f}.actualCanonical`) },
    {
      key: "actual_effect",
      header: t(`${f}.actualEffect`),
      renderCell: (row) =>
        row.actual_effect ? (
          <Badge variant="danger">{row.actual_effect}</Badge>
        ) : (
          <Badge variant="neutral">—</Badge>
        ),
    },
    {
      key: "is_match",
      header: "",
      width: "80px",
      renderCell: (row) =>
        row.is_match ? (
          <Badge variant="success">{t(`${f}.match`)}</Badge>
        ) : (
          <Badge variant="danger">{t(`${f}.mismatch`)}</Badge>
        ),
    },
  ];

  const isRunningState =
    running ||
    latestRun?.state === "pending" ||
    latestRun?.state === "running";

  /* ── レンダー ── */

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
      {/* ゲートステータス */}
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
        <GateBadge state={gate.latest_state} />
      </div>

      {error && (
        <p role="alert" style={{ color: "var(--color-error)", fontSize: "var(--font-sm)" }}>
          {error}
        </p>
      )}

      {/* テストケースセクション */}
      <section>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: "var(--space-3)",
          }}
        >
          <h3 style={{ fontSize: "var(--font-md)", fontWeight: "var(--font-semibold)", margin: 0 }}>
            {t(`${f}.casesTitle`)}
          </h3>
          <Button variant="secondary" size="sm" onClick={() => setAddOpen(true)}>
            {t(`${f}.addCase`)}
          </Button>
        </div>
        <DataTable
          columns={caseColumns}
          data={cases}
          rowKey={(row) => String(row.id)}
          emptyState={<EmptyState title={t(`${f}.noCases`)} size="compact" />}
          density="compact"
        />
      </section>

      {/* テスト実行ボタン */}
      <div>
        <Button
          variant="primary"
          onClick={() => { void handleRunTests(); }}
          disabled={cases.length === 0 || isRunningState}
          loading={isRunningState}
          loadingText={t(`${f}.running`)}
        >
          {t(`${f}.runAll`)}
        </Button>
      </div>

      {/* テスト結果セクション */}
      {latestRun !== null && (
        <section>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "var(--space-3)",
              marginBottom: "var(--space-3)",
            }}
          >
            <h3 style={{ fontSize: "var(--font-md)", fontWeight: "var(--font-semibold)", margin: 0 }}>
              {t(`${f}.resultsTitle`)}
            </h3>
            <GateBadge state={latestRun.state} />
            <span style={{ fontSize: "var(--font-sm)", color: "var(--text-muted)" }}>
              {t(`${f}.resultsPassed`, {
                passed: latestRun.passed_cases,
                total: latestRun.total_cases,
              })}
            </span>
          </div>
          <DataTable
            columns={resultColumns}
            data={latestRun.results}
            rowKey={(row) => String(row.case_id)}
            emptyState={<EmptyState title={t(`${f}.noResults`)} size="compact" />}
            density="compact"
          />
        </section>
      )}

      {/* テストケース追加モーダル */}
      <Modal
        open={addOpen}
        onClose={() => { resetAddForm(); setAddOpen(false); }}
        title={t(`${f}.addCase`)}
        size="sm"
        footer={
          <div style={{ display: "flex", gap: "var(--space-2)", justifyContent: "flex-end" }}>
            <Button variant="secondary" onClick={() => { resetAddForm(); setAddOpen(false); }}>
              {t("common.cancel")}
            </Button>
            <Button variant="primary" onClick={() => { void handleAddCase(); }} loading={addSaving}>
              {t("common.save")}
            </Button>
          </div>
        }
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
          {addError && (
            <p role="alert" style={{ color: "var(--color-error)", fontSize: "var(--font-sm)", margin: 0 }}>
              {addError}
            </p>
          )}
          <TextField
            label={t(`${f}.inputText`)}
            value={addInputText}
            onChange={(e) => setAddInputText(e.target.value)}
            required
            fullWidth
          />
          <TextField
            label={t(`${f}.expectedCanonical`)}
            value={addExpectedCanonical}
            onChange={(e) => setAddExpectedCanonical(e.target.value)}
            required
            fullWidth
          />
          <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={addEffectExcluded}
              onChange={(e) => setAddEffectExcluded(e.target.checked)}
            />
            <span style={{ fontSize: "var(--font-sm)" }}>{t(`${f}.expectedEffectExcluded`)}</span>
          </label>
          <TextField
            label={t(`${f}.note`)}
            value={addNote}
            onChange={(e) => setAddNote(e.target.value)}
            fullWidth
          />
        </div>
      </Modal>

      {/* 削除確認モーダル */}
      <ConfirmModal
        open={deleteTargetId !== null}
        title={t("common.delete")}
        message={t(`${f}.deleteConfirm`)}
        danger
        onConfirm={() => { void handleDeleteConfirm(); }}
        onCancel={() => setDeleteTargetId(null)}
      />
    </div>
  );
}
