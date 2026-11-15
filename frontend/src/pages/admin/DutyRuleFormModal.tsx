/**
 * 関税の額の決まりを足す・直す窓（invoice-create-portfolio 便B・design.md §3-6）。
 * - 根拠の URL は必須。中身の行は 1〜20 行。
 * - 送料の会社は空なら「どの送料の会社でも」。保存の形（小文字・空白なし）はサーバーが決める。
 * - 重なり（409）・入力の誤り（422）はそれぞれの文で知らせ、窓は閉じない。
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api, ApiError } from "../../lib/api";
import { Modal } from "../../components/Modal";
import { Button } from "../../components/Button";
import { Stack } from "../../components/Stack";
import { TextField } from "../../components/TextField";
import { Textarea } from "../../components/Textarea";
import { Select } from "../../components/Select";
import { Toggle } from "../../components/Toggle";
import { CountryCombobox } from "../../components/CountryCombobox";
import type { DutyRule, DutyRuleOptions } from "./dutyRuleTypes";

interface ComponentDraft {
  label: string;
  base: string;
  rate_pct: string;
  min_amount: string;
  max_amount: string;
  amount_currency: string;
}

interface RuleDraft {
  destination_country_code: string;
  carrier: string;
  label: string;
  effective_from: string;
  effective_to: string;
  source_url: string;
  note: string;
  is_active: boolean;
  components: ComponentDraft[];
}

/** 基準の名前（値の正本はサーバーの選択肢。ここは見せる文の対応だけ） */
export const BASE_LABEL_KEYS: Record<string, string> = {
  subtotal: "dutyRules.baseSubtotal",
  subtotal_shipping: "dutyRules.baseSubtotalShipping",
  subtotal_shipping_prior: "dutyRules.baseSubtotalShippingPrior",
};

const MAX_COMPONENTS = 20;

function emptyComponent(options: DutyRuleOptions): ComponentDraft {
  return { label: "", base: options.bases[0] ?? "", rate_pct: "", min_amount: "", max_amount: "", amount_currency: "" };
}

function toDraft(rule: DutyRule | null, options: DutyRuleOptions): RuleDraft {
  if (rule === null) {
    return {
      destination_country_code: "", carrier: "", label: "", effective_from: "", effective_to: "",
      source_url: "", note: "", is_active: true, components: [emptyComponent(options)],
    };
  }
  return {
    destination_country_code: rule.destination_country_code,
    carrier: rule.carrier ?? "",
    label: rule.label,
    effective_from: rule.effective_from,
    effective_to: rule.effective_to ?? "",
    source_url: rule.source_url,
    note: rule.note ?? "",
    is_active: rule.is_active,
    components: rule.components.map((c) => ({
      label: c.label,
      base: c.base,
      rate_pct: c.rate_pct,
      min_amount: c.min_amount ?? "",
      max_amount: c.max_amount ?? "",
      amount_currency: c.amount_currency ?? "",
    })),
  };
}

/** 空の欄は null で送る（サーバーも空を null にするが、送る形をはっきりさせる） */
function toBody(draft: RuleDraft) {
  const blank = (v: string) => (v.trim() === "" ? null : v.trim());
  return {
    destination_country_code: draft.destination_country_code,
    carrier: blank(draft.carrier),
    label: draft.label.trim(),
    effective_from: draft.effective_from,
    effective_to: blank(draft.effective_to),
    source_url: draft.source_url.trim(),
    note: blank(draft.note),
    is_active: draft.is_active,
    components: draft.components.map((c) => ({
      label: c.label.trim(),
      base: c.base,
      rate_pct: c.rate_pct.trim(),
      min_amount: blank(c.min_amount),
      max_amount: blank(c.max_amount),
      amount_currency: blank(c.amount_currency),
    })),
  };
}

interface Props {
  open: boolean;
  rule: DutyRule | null;
  options: DutyRuleOptions;
  onClose: () => void;
  onSaved: () => void;
}

export function DutyRuleFormModal({ open, rule, options, onClose, onSaved }: Props) {
  const { t } = useTranslation();
  const [draft, setDraft] = useState<RuleDraft>(() => toDraft(rule, options));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set = <K extends keyof RuleDraft>(key: K, value: RuleDraft[K]) =>
    setDraft((d) => ({ ...d, [key]: value }));
  const setComponent = (index: number, key: keyof ComponentDraft, value: string) =>
    setDraft((d) => ({
      ...d,
      components: d.components.map((c, i) => (i === index ? { ...c, [key]: value } : c)),
    }));

  const canSave =
    draft.destination_country_code !== "" &&
    draft.label.trim() !== "" &&
    draft.effective_from !== "" &&
    draft.source_url.trim() !== "" &&
    draft.components.length > 0 &&
    draft.components.every((c) => c.label.trim() !== "" && c.base !== "" && c.rate_pct.trim() !== "");

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      if (rule === null) {
        await api.post("/admin/duty-rules", toBody(draft));
      } else {
        await api.put(`/admin/duty-rules/${rule.id}`, toBody(draft));
      }
      onSaved();
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) setError(t("dutyRules.overlapError"));
      else if (e instanceof ApiError && e.status === 422) setError(t("dutyRules.inputError"));
      else setError(t("dutyRules.saveError"));
    } finally {
      setSaving(false);
    }
  };

  const baseOptions = options.bases.map((b) => ({ value: b, label: BASE_LABEL_KEYS[b] ? t(BASE_LABEL_KEYS[b]) : b }));
  const currencyOptions = [
    { value: "", label: t("dutyRules.currencyNone") },
    ...options.currencies.map((c) => ({ value: c, label: c })),
  ];

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={rule === null ? t("dutyRules.addTitle") : t("dutyRules.editTitle")}
      size="lg"
      dismissOnOverlay={false}
      footer={
        <>
          <Button type="button" variant="secondary" size="md" onClick={onClose} disabled={saving}>
            {t("common.cancel")}
          </Button>
          <Button
            type="button"
            variant="primary"
            size="md"
            loading={saving}
            disabled={saving || !canSave}
            onClick={() => void handleSave()}
          >
            {t("dutyRules.save")}
          </Button>
        </>
      }
    >
      <Stack gap="4">
        <div className="comp-field">
          <label htmlFor="duty-rule-country" className="comp-field__label">{t("dutyRules.country")}</label>
          <CountryCombobox
            id="duty-rule-country"
            value={draft.destination_country_code}
            onChange={(v) => set("destination_country_code", v)}
            placeholder={t("common.search")}
            required
          />
        </div>
        <TextField
          label={t("dutyRules.carrier")}
          helperText={t("dutyRules.carrierHelp")}
          value={draft.carrier}
          onChange={(e) => set("carrier", e.target.value)}
          fullWidth
        />
        <TextField
          label={t("dutyRules.label")}
          helperText={t("dutyRules.labelHelp")}
          value={draft.label}
          onChange={(e) => set("label", e.target.value)}
          required
          fullWidth
        />
        <Stack direction="row" gap="3">
          <TextField
            type="date"
            label={t("dutyRules.effectiveFrom")}
            value={draft.effective_from}
            onChange={(e) => set("effective_from", e.target.value)}
            required
          />
          <TextField
            type="date"
            label={t("dutyRules.effectiveTo")}
            helperText={t("dutyRules.effectiveToHelp")}
            value={draft.effective_to}
            onChange={(e) => set("effective_to", e.target.value)}
          />
        </Stack>
        <TextField
          type="url"
          label={t("dutyRules.sourceUrl")}
          helperText={t("dutyRules.sourceUrlHelp")}
          value={draft.source_url}
          onChange={(e) => set("source_url", e.target.value)}
          required
          fullWidth
        />
        <Textarea
          label={t("dutyRules.note")}
          value={draft.note}
          onChange={(e) => set("note", e.target.value)}
          fullWidth
        />
        <Stack direction="row" gap="2">
          <Toggle
            id="duty-rule-active"
            checked={draft.is_active}
            onCheckedChange={(v) => set("is_active", v)}
            aria-label={t("dutyRules.active")}
          />
          <label htmlFor="duty-rule-active" className="comp-field__label">{t("dutyRules.active")}</label>
        </Stack>

        <h3>{t("dutyRules.componentsTitle")}</h3>
        {draft.components.map((c, i) => (
          <Stack key={i} gap="2">
            <Stack direction="row" gap="3">
              <TextField
                label={t("dutyRules.componentLabel", { n: i + 1 })}
                value={c.label}
                onChange={(e) => setComponent(i, "label", e.target.value)}
                required
              />
              <Select
                label={t("dutyRules.base")}
                options={baseOptions}
                value={c.base}
                onChange={(e) => setComponent(i, "base", e.target.value)}
              />
              <TextField
                type="number"
                inputMode="decimal"
                min="0"
                step="0.0001"
                label={t("dutyRules.ratePct")}
                value={c.rate_pct}
                onChange={(e) => setComponent(i, "rate_pct", e.target.value)}
                required
              />
            </Stack>
            <Stack direction="row" gap="3">
              <TextField
                type="number"
                inputMode="decimal"
                min="0"
                step="0.01"
                label={t("dutyRules.minAmount")}
                value={c.min_amount}
                onChange={(e) => setComponent(i, "min_amount", e.target.value)}
              />
              <TextField
                type="number"
                inputMode="decimal"
                min="0"
                step="0.01"
                label={t("dutyRules.maxAmount")}
                value={c.max_amount}
                onChange={(e) => setComponent(i, "max_amount", e.target.value)}
              />
              <Select
                label={t("dutyRules.amountCurrency")}
                helperText={t("dutyRules.amountCurrencyHelp")}
                options={currencyOptions}
                value={c.amount_currency}
                onChange={(e) => setComponent(i, "amount_currency", e.target.value)}
              />
            </Stack>
            {draft.components.length > 1 && (
              <Stack direction="row" gap="2">
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => set("components", draft.components.filter((_, j) => j !== i))}
                >
                  {t("dutyRules.removeComponent", { n: i + 1 })}
                </Button>
              </Stack>
            )}
          </Stack>
        ))}
        {draft.components.length < MAX_COMPONENTS && (
          <Stack direction="row" gap="2">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => set("components", [...draft.components, emptyComponent(options)])}
            >
              {t("dutyRules.addComponent")}
            </Button>
          </Stack>
        )}
        {error && <p role="alert">{error}</p>}
      </Stack>
    </Modal>
  );
}
