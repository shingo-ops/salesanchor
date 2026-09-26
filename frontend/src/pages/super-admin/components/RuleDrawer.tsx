/**
 * RuleDrawer — ルール新規作成 / 編集ドロワー
 *
 * editRule=null/undefined → 新規作成モード (POST)
 * editRule=object         → 編集モード (PATCH)
 *
 * 機能:
 *  - status_id は backend で自動採番（フォームから除去）
 *  - match_type は LITERAL に固定（フォームから除去）
 *  - exclude_pattern は空文字に固定（フォームから除去）
 *  - canonical はDBから取得した Select に変更（effect を自動セット）
 *  - テストゲート: 判定合格後のみ作成 / 更新ボタンが有効になる
 *  - 無効化ボタン: 編集モードかつ enabled=true のときのみ表示
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

export interface RuleEntry {
  id: number;
  status_id: string;
  canonical: string;
  search_pattern: string;
  exclude_pattern: string;
  priority: number;
  enabled: boolean;
  note: string;
  match_type: string;
  effect: string;
  created_at: string;
  updated_at: string;
}

interface RuleDrawerProps {
  open: boolean;
  onClose: () => void;
  /** コールバック: 作成 / 更新 / 無効化 後に呼ばれる */
  onSaved: () => void;
  /** null/undefined = 新規作成モード、object = 編集モード */
  editRule?: RuleEntry | null;
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

const ruleToFormDraft = (rule: RuleEntry): FormDraft => ({
  canonical: rule.canonical,
  effect: rule.effect,
  searchPattern: rule.search_pattern,
  priority: String(rule.priority),
  note: rule.note ?? "",
});

export function RuleDrawer({ open, onClose, onSaved, editRule }: RuleDrawerProps) {
  const { t } = useTranslation();
  const f = "ruleManagement";
  const fc = `${f}.create`;
  const fe = `${f}.edit`;

  const isEditMode = editRule != null;

  const [draft, setDraft] = useState<FormDraft>(emptyDraft);
  const [submitting, setSubmitting] = useState(false);
  const [disabling, setDisabling] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [testInput, setTestInput] = useState("");
  const [testResult, setTestResult] = useState<PreviewResponse | null>(null);
  const [testing, setTesting] = useState(false);
  const [testPassed, setTestPassed] = useState(false);
  const [canonicals, setCanonicals] = useState<CanonicalOption[]>([]);

  // ドロワーが開くたびにフォームを初期化
  useEffect(() => {
    if (!open) return;
    if (isEditMode) {
      setDraft(ruleToFormDraft(editRule));
    } else {
      setDraft(emptyDraft);
    }
    setTestInput("");
    setTestResult(null);
    setTestPassed(false);
    setSubmitError("");
  }, [open, editRule, isEditMode]);

  // canonical オプションをバックエンドから取得
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

  const handleSubmit = async () => {
    setSubmitting(true);
    setSubmitError("");
    try {
      if (isEditMode) {
        // 編集モード: PATCH
        await api.patch(`/super-admin/status-master/${editRule.id}`, {
          canonical: draft.canonical,
          search_pattern: draft.searchPattern,
          match_type: "LITERAL",
          effect: draft.effect,
          priority: Number(draft.priority) || 0,
          note: draft.note,
        });
      } else {
        // 新規作成モード: POST
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
      }
      onSaved();
    } catch (e) {
      setSubmitError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDisable = async () => {
    if (!isEditMode) return;
    setDisabling(true);
    setSubmitError("");
    try {
      await api.patch(`/super-admin/status-master/${editRule.id}`, { enabled: false });
      onSaved();
    } catch (e) {
      setSubmitError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      setDisabling(false);
    }
  };

  const handleClose = () => {
    setDraft(emptyDraft);
    setTestInput("");
    setTestResult(null);
    setTestPassed(false);
    setSubmitError("");
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

  const isSubmitBusy = submitting || disabling;

  const footer = (
    <>
      {/* 無効化ボタン: 編集モードかつ enabled=true のときのみ */}
      {isEditMode && editRule.enabled && (
        <div style={{ borderBottom: "1px solid var(--border-subtle)", paddingBottom: "var(--space-3)", marginBottom: "var(--space-3)", width: "100%" }}>
          <Button
            variant="danger"
            onClick={() => { void handleDisable(); }}
            disabled={isSubmitBusy}
            loading={disabling}
            loadingText={t(`${fe}.disabling`)}
            fullWidth
            data-testid="rule-drawer-disable-btn"
          >
            {t(`${fe}.disable`)}
          </Button>
        </div>
      )}
      <Button variant="secondary" onClick={handleClose} disabled={isSubmitBusy}>
        {t("common.cancel")}
      </Button>
      <Button
        variant="primary"
        onClick={() => { void handleSubmit(); }}
        disabled={!testPassed || isSubmitBusy}
        loading={submitting}
        loadingText={isEditMode ? t(`${fe}.updating`) : t(`${fc}.creating`)}
        data-testid="rule-drawer-submit-btn"
      >
        {isEditMode ? t(`${fe}.update`) : t(`${f}.createRule`)}
      </Button>
    </>
  );

  return (
    <Drawer
      open={open}
      onClose={handleClose}
      title={isEditMode ? t(`${fe}.title`) : t(`${fc}.title`)}
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
          data-testid="rule-drawer-canonical"
        />

        {/* 2. 除外 / 検索 (effect) */}
        <Select
          label={t(`${fc}.effect`)}
          options={effectOptions}
          value={draft.effect}
          onChange={(e) => set("effect", e.target.value)}
          fullWidth
          data-testid="rule-drawer-effect"
        />

        {/* 3. ワード (search_pattern) */}
        <TextField
          label={t(`${fc}.searchPattern`)}
          value={draft.searchPattern}
          onChange={(e) => set("searchPattern", e.target.value)}
          fullWidth
          data-testid="rule-drawer-search-pattern"
        />

        {/* 4. 優先度 (priority) */}
        <TextField
          label={t(`${fc}.priority`)}
          type="number"
          value={draft.priority}
          onChange={(e) => set("priority", e.target.value)}
          fullWidth
          data-testid="rule-drawer-priority"
        />

        {/* 5. メモ (note) */}
        <TextField
          label={t(`${fc}.note`)}
          value={draft.note}
          onChange={(e) => set("note", e.target.value)}
          fullWidth
          data-testid="rule-drawer-note"
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
              data-testid="rule-drawer-test-input"
            />
            <Button
              variant="secondary"
              onClick={() => { void handleTest(); }}
              loading={testing}
              disabled={!testInput.trim() || testing}
              data-testid="rule-drawer-test-button"
            >
              {t(`${fc}.testButton`)}
            </Button>
            {testResult !== null && (
              <div style={{ display: "flex", alignItems: "flex-start", gap: "var(--space-2)", flexWrap: "wrap" }}>
                <Badge variant={testResult.matched ? "success" : "danger"} data-testid="rule-drawer-test-result">
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

        {submitError && (
          <p role="alert" style={{ color: "var(--color-error)", fontSize: "var(--font-sm)", margin: 0 }}>
            {submitError}
          </p>
        )}
      </div>
    </Drawer>
  );
}
