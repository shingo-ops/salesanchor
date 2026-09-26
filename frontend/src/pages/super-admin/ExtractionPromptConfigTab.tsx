/**
 * ExtractionPromptConfigTab — 抽出プロンプト設定パネル
 *
 * Gemini 抽出プロンプト（base_extraction / work_id_extraction）を
 * DB 管理化して管理画面から編集可能にする。
 *
 * ADR-027: 全UI文字列は t("key") 経由。
 * ADR-144: デザインシステムコンポーネント使用、CSS変数のみ。
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";

const PROMPT_KEYS = ["base_extraction", "work_id_extraction"] as const;
type PromptKey = (typeof PROMPT_KEYS)[number];

interface PromptConfig {
  prompt_key: string;
  prompt_text: string;
  is_active: boolean;
  version: number;
}

const emptyConfig = (key: PromptKey): PromptConfig => ({
  prompt_key: key,
  prompt_text: "",
  is_active: true,
  version: 0,
});

export default function ExtractionPromptConfigTab() {
  const { t } = useTranslation();
  const p = "analysisRules.extractionPromptConfig";

  const [configs, setConfigs] = useState<Record<PromptKey, PromptConfig>>({
    base_extraction: emptyConfig("base_extraction"),
    work_id_extraction: emptyConfig("work_id_extraction"),
  });
  const [saving, setSaving] = useState<Record<PromptKey, boolean>>({
    base_extraction: false,
    work_id_extraction: false,
  });
  const [messages, setMessages] = useState<Record<PromptKey, string>>({
    base_extraction: "",
    work_id_extraction: "",
  });
  const [errors, setErrors] = useState<Record<PromptKey, string>>({
    base_extraction: "",
    work_id_extraction: "",
  });
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState("");

  const loadAll = async () => {
    setFetchError("");
    setLoading(true);
    try {
      const data = await api.get<PromptConfig[]>("/super-admin/extraction-prompts");
      const next = {
        base_extraction: emptyConfig("base_extraction"),
        work_id_extraction: emptyConfig("work_id_extraction"),
      };
      for (const item of data) {
        if (item.prompt_key === "base_extraction" || item.prompt_key === "work_id_extraction") {
          next[item.prompt_key] = item;
        }
      }
      setConfigs(next);
    } catch (e) {
      setFetchError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSave = async (key: PromptKey) => {
    setSaving((prev) => ({ ...prev, [key]: true }));
    setMessages((prev) => ({ ...prev, [key]: "" }));
    setErrors((prev) => ({ ...prev, [key]: "" }));
    try {
      const updated = await api.put<PromptConfig>(
        `/super-admin/extraction-prompts/${encodeURIComponent(key)}`,
        {
          prompt_text: configs[key].prompt_text,
          is_active: configs[key].is_active,
        },
      );
      setConfigs((prev) => ({ ...prev, [key]: updated }));
      setMessages((prev) => ({ ...prev, [key]: t(`${p}.saved`) }));
    } catch (e) {
      setErrors((prev) => ({
        ...prev,
        [key]: e instanceof Error ? e.message : t(`${p}.error`),
      }));
    } finally {
      setSaving((prev) => ({ ...prev, [key]: false }));
    }
  };

  const labelFor = (key: PromptKey) =>
    key === "base_extraction" ? t(`${p}.baseExtraction`) : t(`${p}.workIdExtraction`);

  if (loading) {
    return (
      <div style={{ padding: "var(--space-6)", color: "var(--text-muted)" }}>
        {t("common.loading")}
      </div>
    );
  }

  return (
    <div style={{ padding: "var(--space-6)" }}>
      <h3
        style={{
          margin: "0 0 var(--space-2)",
          fontSize: "var(--font-xl)",
          fontWeight: "var(--font-weight-bold)",
          color: "var(--text-primary)",
        }}
      >
        {t(`${p}.title`)}
      </h3>

      {fetchError && (
        <div className="error-message" style={{ marginBottom: "var(--space-4)" }}>
          {fetchError}
        </div>
      )}

      {PROMPT_KEYS.map((key) => (
        <section
          key={key}
          style={{
            marginBottom: "var(--space-8)",
            padding: "var(--space-5)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-md)",
            background: "var(--surface)",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "var(--space-3)",
              marginBottom: "var(--space-3)",
              flexWrap: "wrap",
            }}
          >
            <strong
              style={{
                margin: 0,
                fontSize: "var(--font-lg)",
                fontWeight: "var(--font-weight-semibold)",
                color: "var(--text-primary)",
              }}
            >
              {labelFor(key)}
            </strong>
            {configs[key].version > 0 && (
              <span
                style={{
                  fontSize: "var(--font-xs)",
                  color: "var(--text-muted)",
                  background: "var(--surface-alt)",
                  padding: "2px var(--space-2)",
                  borderRadius: "var(--radius-sm)",
                }}
              >
                {t(`${p}.version`)} {configs[key].version}
              </span>
            )}
          </div>

          {errors[key] && (
            <div className="error-message" style={{ marginBottom: "var(--space-3)" }}>
              {errors[key]}
            </div>
          )}
          {messages[key] && (
            <div
              style={{
                marginBottom: "var(--space-3)",
                color: "var(--text-success, var(--text-secondary))",
                fontSize: "var(--font-sm)",
              }}
            >
              {messages[key]}
            </div>
          )}

          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: "var(--space-2)",
              marginBottom: "var(--space-3)",
              fontSize: "var(--font-sm)",
              color: "var(--text-secondary)",
            }}
          >
            <input
              type="checkbox"
              checked={configs[key].is_active}
              data-testid={`prompt-active-${key}`}
              onChange={(e) =>
                setConfigs((prev) => ({
                  ...prev,
                  [key]: { ...prev[key], is_active: e.target.checked },
                }))
              }
            />
            {configs[key].is_active ? t(`${p}.active`) : t(`${p}.inactive`)}
          </label>

          <textarea
            value={configs[key].prompt_text}
            data-testid={`prompt-textarea-${key}`}
            onChange={(e) =>
              setConfigs((prev) => ({
                ...prev,
                [key]: { ...prev[key], prompt_text: e.target.value },
              }))
            }
            placeholder={t(`${p}.placeholder`)}
            rows={16}
            style={{
              width: "100%",
              fontFamily: "var(--font-mono, monospace)",
              fontSize: "var(--font-sm)",
              boxSizing: "border-box",
            }}
          />

          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "var(--space-3)" }}>
            <button
              type="button"
              className="btn-primary"
              disabled={saving[key]}
              data-testid={`prompt-save-${key}`}
              onClick={() => void handleSave(key)}
            >
              {saving[key] ? t("common.saving") : t(`${p}.save`)}
            </button>
          </div>
        </section>
      ))}
    </div>
  );
}
