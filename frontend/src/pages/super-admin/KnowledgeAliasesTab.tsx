/**
 * /super-admin/masters — 仕入先別プロンプト + 正規化ルール + 仕入元個別ルール タブ。
 *
 * ADR-093 UX 改修 (2026-06-03):
 *   - 正規化ルール: 一致方法(pattern_type)を日本語ラベル化、パターン→変換前ワード /
 *     正規化先→変換後ワードへリネーム、ID列・CSV入出力を撤去。
 *   - 仕入元別名 → 「仕入元個別ルール」へ改名。ID/仕入元ID/言語列を撤去し、
 *     「受信通知のワード → 解析する仕入元(名)」の形で表示。仕入元は名前で選択。
 *   - 両セクションとも編集・削除を商品マスタと同じ方式に統一:
 *     最左チェックボックス + 一括削除 + 編集/新規はポップアップ。検索窓は広め。
 */
import { useEffect, useMemo, useState, FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import ConfirmModal from "../../components/ConfirmModal";

interface KnowledgeRule {
  id: number;
  category: string;
  pattern_type: string;
  pattern: string;
  normalized_to: string;
  priority: number;
  language: string;
  is_active: boolean;
  created_at: string;
}

interface SupplierAlias {
  id: number;
  supplier_id: number;
  alias_text: string;
  language: string;
  product_id: number | null;
  source: string | null;
}

const PATTERN_TYPES = ["regex", "exact", "prefix", "suffix", "contains"];

const emptyRule = {
  category: "",
  pattern_type: "contains",
  pattern: "",
  normalized_to: "",
  priority: 100,
  language: "ja",
  is_active: true,
};

const emptyAlias = {
  supplier_id: 0,
  alias_text: "",
  language: "ja",
  product_id: null as number | null,
  source: "manual",
};

// 検索窓は従来の約 2 倍幅（ユーザー要望）。
const SEARCH_WIDTH = "30rem";

export default function KnowledgeAliasesTab() {
  const { t } = useTranslation();

  // ---- 仕入先別 Gemini プロンプト (ADR-085) ----
  const [suppliers, setSuppliers] = useState<{ id: number; name: string }[]>([]);
  const [promptSupplierId, setPromptSupplierId] = useState<number | null>(null);
  const [promptText, setPromptText] = useState("");
  const [promptActive, setPromptActive] = useState(true);
  const [promptMsg, setPromptMsg] = useState("");
  const [promptError, setPromptError] = useState("");
  const [promptSaving, setPromptSaving] = useState(false);

  // ---- 正規化ルール ----
  const [rules, setRules] = useState<KnowledgeRule[]>([]);
  const [ruleSearch, setRuleSearch] = useState("");
  const [ruleError, setRuleError] = useState("");
  const [ruleSelected, setRuleSelected] = useState<Set<number>>(new Set());
  const [ruleConfirmDelete, setRuleConfirmDelete] = useState(false);
  const [showRuleForm, setShowRuleForm] = useState(false);
  const [ruleForm, setRuleForm] = useState(emptyRule);
  const [ruleEditId, setRuleEditId] = useState<number | null>(null);

  // ---- 仕入元個別ルール（旧 仕入元別名） ----
  const [aliases, setAliases] = useState<SupplierAlias[]>([]);
  const [aliasSearch, setAliasSearch] = useState("");
  const [aliasError, setAliasError] = useState("");
  const [aliasSelected, setAliasSelected] = useState<Set<number>>(new Set());
  const [aliasConfirmDelete, setAliasConfirmDelete] = useState(false);
  const [showAliasForm, setShowAliasForm] = useState(false);
  const [aliasForm, setAliasForm] = useState(emptyAlias);
  const [aliasEditId, setAliasEditId] = useState<number | null>(null);

  // supplier_id → 名前（個別ルール一覧を名前で表示するため）
  const supplierName = useMemo(
    () => new Map(suppliers.map((s) => [s.id, s.name])),
    [suppliers],
  );

  const loadSuppliers = async () => {
    try {
      const data = await api.get<{ id: number; name: string }[]>(
        "/super-admin/suppliers?per_page=500",
      );
      setSuppliers(data);
    } catch (e) {
      setPromptError(e instanceof Error ? e.message : t("common.fetchError"));
    }
  };

  const loadPrompt = async (supplierId: number) => {
    setPromptError("");
    setPromptMsg("");
    try {
      const data = await api.get<{ prompt: string; is_active: boolean }>(
        `/super-admin/suppliers/${supplierId}/prompt`,
      );
      setPromptText(data.prompt);
      setPromptActive(data.is_active);
    } catch (e) {
      setPromptError(e instanceof Error ? e.message : t("common.fetchError"));
    }
  };

  const savePrompt = async () => {
    if (promptSupplierId === null) return;
    setPromptError("");
    setPromptMsg("");
    setPromptSaving(true);
    try {
      await api.put(`/super-admin/suppliers/${promptSupplierId}/prompt`, {
        prompt: promptText,
        is_active: promptActive,
      });
      setPromptMsg(t("common.saved"));
    } catch (e) {
      setPromptError(e instanceof Error ? e.message : t("common.saveError"));
    } finally {
      setPromptSaving(false);
    }
  };

  const loadRules = async (q?: string) => {
    try {
      const data = await api.get<KnowledgeRule[]>(
        `/super-admin/knowledge${q ? `?q=${encodeURIComponent(q)}` : ""}`,
      );
      setRules(data);
    } catch (e) {
      setRuleError(e instanceof Error ? e.message : t("common.fetchError"));
    }
  };

  const loadAliases = async (q?: string) => {
    try {
      const data = await api.get<SupplierAlias[]>(
        `/super-admin/aliases${q ? `?q=${encodeURIComponent(q)}` : ""}`,
      );
      setAliases(data);
    } catch (e) {
      setAliasError(e instanceof Error ? e.message : t("common.fetchError"));
    }
  };

  useEffect(() => {
    loadRules();
    loadAliases();
    loadSuppliers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---- 正規化ルール: 作成/編集（ポップアップ） ----
  const openCreateRule = () => {
    setRuleEditId(null);
    setRuleForm(emptyRule);
    setRuleError("");
    setShowRuleForm(true);
  };
  const openEditRule = (r: KnowledgeRule) => {
    setRuleEditId(r.id);
    setRuleForm({
      category: r.category,
      pattern_type: r.pattern_type,
      pattern: r.pattern,
      normalized_to: r.normalized_to,
      priority: r.priority,
      language: r.language,
      is_active: r.is_active,
    });
    setRuleError("");
    setShowRuleForm(true);
  };
  const submitRule = async (e: FormEvent) => {
    e.preventDefault();
    setRuleError("");
    try {
      if (ruleEditId !== null) {
        await api.patch(`/super-admin/knowledge/${ruleEditId}`, ruleForm);
      } else {
        await api.post("/super-admin/knowledge", ruleForm);
      }
      setShowRuleForm(false);
      setRuleForm(emptyRule);
      setRuleEditId(null);
      await loadRules(ruleSearch);
    } catch (err) {
      setRuleError(err instanceof Error ? err.message : t("common.saveError"));
    }
  };
  const toggleRule = (id: number) => {
    setRuleSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };
  const bulkDeleteRules = async () => {
    setRuleConfirmDelete(false);
    const results = await Promise.allSettled(
      Array.from(ruleSelected).map((id) => api.delete(`/super-admin/knowledge/${id}`)),
    );
    if (results.some((r) => r.status === "rejected")) {
      setRuleError(t("common.deleteError"));
    }
    setRuleSelected(new Set());
    await loadRules(ruleSearch);
  };

  // ---- 仕入元個別ルール: 作成/編集（ポップアップ） ----
  const openCreateAlias = () => {
    setAliasEditId(null);
    setAliasForm(emptyAlias);
    setAliasError("");
    setShowAliasForm(true);
  };
  const openEditAlias = (a: SupplierAlias) => {
    setAliasEditId(a.id);
    setAliasForm({
      supplier_id: a.supplier_id,
      alias_text: a.alias_text,
      language: a.language,
      product_id: a.product_id,
      source: a.source ?? "manual",
    });
    setAliasError("");
    setShowAliasForm(true);
  };
  const submitAlias = async (e: FormEvent) => {
    e.preventDefault();
    setAliasError("");
    if (!aliasForm.supplier_id) {
      setAliasError(t("superAdmin.knowledge.selectSupplier"));
      return;
    }
    try {
      if (aliasEditId !== null) {
        await api.patch(`/super-admin/aliases/${aliasEditId}`, aliasForm);
      } else {
        await api.post("/super-admin/aliases", aliasForm);
      }
      setShowAliasForm(false);
      setAliasForm(emptyAlias);
      setAliasEditId(null);
      await loadAliases(aliasSearch);
    } catch (err) {
      setAliasError(err instanceof Error ? err.message : t("common.saveError"));
    }
  };
  const toggleAlias = (id: number) => {
    setAliasSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };
  const bulkDeleteAliases = async () => {
    setAliasConfirmDelete(false);
    const results = await Promise.allSettled(
      Array.from(aliasSelected).map((id) => api.delete(`/super-admin/aliases/${id}`)),
    );
    if (results.some((r) => r.status === "rejected")) {
      setAliasError(t("common.deleteError"));
    }
    setAliasSelected(new Set());
    await loadAliases(aliasSearch);
  };

  const f = "superAdmin.knowledge.fields";

  return (
    <div className="super-admin-knowledge-tab">
      {/* ============ 仕入先別 Gemini プロンプト (ADR-085) ============ */}
      <section style={{ marginBottom: "var(--space-8)" }}>
        <h3>{t("superAdmin.knowledge.promptSection")}</h3>
        <p style={{ color: "var(--text-secondary)", fontSize: "var(--font-sm)" }}>
          {t("superAdmin.knowledge.promptHelp")}
        </p>
        {promptError && <div className="error-message">{promptError}</div>}
        <div style={{ margin: "0.5rem 0" }}>
          <div style={{ display: "flex", gap: "var(--space-2)", alignItems: "center", marginBottom: "var(--space-2)", flexWrap: "wrap" }}>
            <label>
              {t("superAdmin.suppliersAdmin.fields.name")}:{" "}
              <select
                value={promptSupplierId ?? ""}
                data-testid="supplier-prompt-select"
                onChange={(e) => {
                  const id = e.target.value ? Number(e.target.value) : null;
                  setPromptSupplierId(id);
                  setPromptText("");
                  setPromptMsg("");
                  if (id !== null) loadPrompt(id);
                }}
              >
                <option value="">—</option>
                {suppliers.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <input
                type="checkbox"
                checked={promptActive}
                onChange={(e) => setPromptActive(e.target.checked)}
              />{" "}
              {t("superAdmin.suppliersAdmin.fields.isActive")}
            </label>
            <button
              type="button"
              className="btn-primary"
              disabled={promptSupplierId === null || promptSaving}
              onClick={savePrompt}
              data-testid="supplier-prompt-save"
            >
              {promptSaving ? t("common.saving") : t("common.save")}
            </button>
            {promptMsg && <span style={{ color: "var(--text-secondary)" }}>{promptMsg}</span>}
          </div>
          <textarea
            value={promptText}
            data-testid="supplier-prompt-textarea"
            disabled={promptSupplierId === null}
            onChange={(e) => setPromptText(e.target.value)}
            placeholder={t("superAdmin.knowledge.promptPlaceholder")}
            rows={16}
            style={{ width: "100%", fontFamily: "var(--font-mono, monospace)", fontSize: "var(--font-sm)" }}
          />
        </div>
      </section>

      {/* ============ 正規化ルール ============ */}
      <section style={{ marginBottom: "var(--space-8)" }}>
        <h3>{t("superAdmin.knowledge.rulesSection")}</h3>
        <p style={{ color: "var(--text-secondary)", fontSize: "var(--font-sm)" }}>
          {t("superAdmin.knowledge.rulesHelp")}
        </p>
        {ruleError && <div className="error-message">{ruleError}</div>}
        <div style={{ display: "flex", gap: "var(--space-2)", margin: "0.5rem 0", alignItems: "center", flexWrap: "wrap" }}>
          <input
            placeholder={t("common.search")}
            value={ruleSearch}
            data-testid="rules-search"
            onChange={(e) => setRuleSearch(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") loadRules(ruleSearch); }}
            style={{ width: SEARCH_WIDTH, maxWidth: "100%" }}
          />
          <button onClick={() => loadRules(ruleSearch)} className="btn-secondary btn-sm" data-testid="rules-search-btn">
            {t("common.search")}
          </button>
          <button onClick={openCreateRule} className="btn-primary btn-sm" data-testid="rules-new" style={{ marginLeft: "auto" }}>
            {t("superAdmin.knowledge.newRule")}
          </button>
          <button
            onClick={() => setRuleConfirmDelete(true)}
            className="btn-danger btn-sm"
            disabled={ruleSelected.size === 0}
            data-testid="rules-bulk-delete"
          >
            {t("common.delete")}
          </button>
        </div>

        <table className="data-table">
          <thead>
            <tr>
              <th style={{ width: "var(--col-width-checkbox)", textAlign: "center" }} aria-label={t("common.select")}></th>
              <th>{t(`${f}.category`)}</th>
              <th>{t(`${f}.patternType`)}</th>
              <th>{t(`${f}.pattern`)}</th>
              <th>{t(`${f}.normalizedTo`)}</th>
              <th>{t(`${f}.priority`)}</th>
              <th>{t(`${f}.language`)}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rules.length === 0 ? (
              <tr><td colSpan={8} className="empty">{t("common.noData")}</td></tr>
            ) : (
              rules.map((r) => (
                <tr key={r.id} data-testid={`rule-row-${r.id}`}>
                  <td style={{ textAlign: "center" }}>
                    <input
                      type="checkbox"
                      checked={ruleSelected.has(r.id)}
                      onChange={() => toggleRule(r.id)}
                      aria-label={r.pattern}
                      data-testid={`rule-select-${r.id}`}
                    />
                  </td>
                  <td>{r.category}</td>
                  <td>{t(`superAdmin.knowledge.patternTypes.${r.pattern_type}`, { defaultValue: r.pattern_type })}</td>
                  <td><code>{r.pattern}</code></td>
                  <td><code>{r.normalized_to}</code></td>
                  <td>{r.priority}</td>
                  <td>{r.language}</td>
                  <td style={{ textAlign: "right" }}>
                    <button className="btn-sm" onClick={() => openEditRule(r)} data-testid={`rule-edit-${r.id}`}>
                      {t("common.edit")}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </section>

      {/* ============ 仕入元個別ルール（旧 仕入元別名） ============ */}
      <section>
        <h3>{t("superAdmin.knowledge.aliasesSection")}</h3>
        <p style={{ color: "var(--text-secondary)", fontSize: "var(--font-sm)" }}>
          {t("superAdmin.knowledge.aliasesHelp")}
        </p>
        {aliasError && <div className="error-message">{aliasError}</div>}
        <div style={{ display: "flex", gap: "var(--space-2)", margin: "0.5rem 0", alignItems: "center", flexWrap: "wrap" }}>
          <input
            placeholder={t("common.search")}
            value={aliasSearch}
            data-testid="aliases-search"
            onChange={(e) => setAliasSearch(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") loadAliases(aliasSearch); }}
            style={{ width: SEARCH_WIDTH, maxWidth: "100%" }}
          />
          <button onClick={() => loadAliases(aliasSearch)} className="btn-secondary btn-sm" data-testid="aliases-search-btn">
            {t("common.search")}
          </button>
          <button onClick={openCreateAlias} className="btn-primary btn-sm" data-testid="aliases-new" style={{ marginLeft: "auto" }}>
            {t("superAdmin.knowledge.newAlias")}
          </button>
          <button
            onClick={() => setAliasConfirmDelete(true)}
            className="btn-danger btn-sm"
            disabled={aliasSelected.size === 0}
            data-testid="aliases-bulk-delete"
          >
            {t("common.delete")}
          </button>
        </div>

        <table className="data-table">
          <thead>
            <tr>
              <th style={{ width: "var(--col-width-checkbox)", textAlign: "center" }} aria-label={t("common.select")}></th>
              <th>{t(`${f}.aliasText`)}</th>
              <th>{t(`${f}.supplierName`)}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {aliases.length === 0 ? (
              <tr><td colSpan={4} className="empty">{t("common.noData")}</td></tr>
            ) : (
              aliases.map((a) => (
                <tr key={a.id} data-testid={`alias-row-${a.id}`}>
                  <td style={{ textAlign: "center" }}>
                    <input
                      type="checkbox"
                      checked={aliasSelected.has(a.id)}
                      onChange={() => toggleAlias(a.id)}
                      aria-label={a.alias_text}
                      data-testid={`alias-select-${a.id}`}
                    />
                  </td>
                  <td><code>{a.alias_text}</code></td>
                  <td>{supplierName.get(a.supplier_id) ?? `#${a.supplier_id}`}</td>
                  <td style={{ textAlign: "right" }}>
                    <button className="btn-sm" onClick={() => openEditAlias(a)} data-testid={`alias-edit-${a.id}`}>
                      {t("common.edit")}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </section>

      {/* ============ 正規化ルール 編集/新規 ポップアップ ============ */}
      {showRuleForm && (
        <div className="modal-overlay" onClick={() => setShowRuleForm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "min(96vw, 640px)" }}>
            <h3>{ruleEditId !== null ? t("common.edit") : t("superAdmin.knowledge.newRule")}</h3>
            <form onSubmit={submitRule}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-3) var(--space-4)" }}>
                <div className="form-group"><label>{t(`${f}.category`)} *</label>
                  <input required value={ruleForm.category} onChange={(e) => setRuleForm({ ...ruleForm, category: e.target.value })} />
                </div>
                <div className="form-group"><label>{t(`${f}.patternType`)}</label>
                  <select value={ruleForm.pattern_type} onChange={(e) => setRuleForm({ ...ruleForm, pattern_type: e.target.value })}>
                    {PATTERN_TYPES.map((pt) => (
                      <option key={pt} value={pt}>{t(`superAdmin.knowledge.patternTypes.${pt}`)}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group"><label>{t(`${f}.pattern`)} *</label>
                  <input required value={ruleForm.pattern} onChange={(e) => setRuleForm({ ...ruleForm, pattern: e.target.value })} />
                </div>
                <div className="form-group"><label>{t(`${f}.normalizedTo`)} *</label>
                  <input required value={ruleForm.normalized_to} onChange={(e) => setRuleForm({ ...ruleForm, normalized_to: e.target.value })} />
                </div>
                <div className="form-group"><label>{t(`${f}.priority`)}</label>
                  <input type="number" min="0" value={ruleForm.priority} onChange={(e) => setRuleForm({ ...ruleForm, priority: Number(e.target.value) || 0 })} />
                </div>
                <div className="form-group"><label>{t(`${f}.language`)}</label>
                  <select value={ruleForm.language} onChange={(e) => setRuleForm({ ...ruleForm, language: e.target.value })}>
                    <option value="ja">ja</option>
                    <option value="en">en</option>
                    <option value="ko">ko</option>
                    <option value="zh">zh</option>
                  </select>
                </div>
                <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                  <input type="checkbox" checked={ruleForm.is_active} onChange={(e) => setRuleForm({ ...ruleForm, is_active: e.target.checked })} />
                  {t(`${f}.isActive`)}
                </label>
              </div>
              <div className="form-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowRuleForm(false)}>{t("common.cancel")}</button>
                <button type="submit" className="btn-primary" data-testid="rule-save">{ruleEditId !== null ? t("common.update") : t("common.create")}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ============ 仕入元個別ルール 編集/新規 ポップアップ ============ */}
      {showAliasForm && (
        <div className="modal-overlay" onClick={() => setShowAliasForm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "min(96vw, 560px)" }}>
            <h3>{aliasEditId !== null ? t("common.edit") : t("superAdmin.knowledge.newAlias")}</h3>
            <form onSubmit={submitAlias}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "var(--space-3)" }}>
                <div className="form-group"><label>{t(`${f}.aliasText`)} *</label>
                  <input
                    required
                    value={aliasForm.alias_text}
                    data-testid="alias-text-input"
                    onChange={(e) => setAliasForm({ ...aliasForm, alias_text: e.target.value })}
                  />
                </div>
                <div className="form-group"><label>{t(`${f}.supplierName`)} *</label>
                  <select
                    required
                    value={aliasForm.supplier_id || ""}
                    data-testid="alias-supplier-select"
                    onChange={(e) => setAliasForm({ ...aliasForm, supplier_id: Number(e.target.value) })}
                  >
                    <option value="">—</option>
                    {suppliers.map((s) => (
                      <option key={s.id} value={s.id}>{s.name}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="form-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowAliasForm(false)}>{t("common.cancel")}</button>
                <button type="submit" className="btn-primary" data-testid="alias-save">{aliasEditId !== null ? t("common.update") : t("common.create")}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      <ConfirmModal
        open={ruleConfirmDelete}
        title={t("common.delete")}
        message={t("superAdmin.knowledge.bulkDeleteConfirm", { count: ruleSelected.size })}
        confirmLabel={t("common.delete")}
        danger
        onConfirm={() => void bulkDeleteRules()}
        onCancel={() => setRuleConfirmDelete(false)}
      />
      <ConfirmModal
        open={aliasConfirmDelete}
        title={t("common.delete")}
        message={t("superAdmin.knowledge.bulkDeleteConfirm", { count: aliasSelected.size })}
        confirmLabel={t("common.delete")}
        danger
        onConfirm={() => void bulkDeleteAliases()}
        onCancel={() => setAliasConfirmDelete(false)}
      />
    </div>
  );
}
