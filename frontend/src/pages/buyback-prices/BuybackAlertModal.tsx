/**
 * BuybackAlertModal — 買取価格アラートルール設定 Modal（スーパー管理者専用）
 */
import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { Modal } from "../../components/Modal";
import { Card } from "../../components/Card";
import { Badge } from "../../components/Badge";
import { Button } from "../../components/Button";
import { TextField } from "../../components/TextField";
import { SelectControl } from "../../components/Select";
import {
  type AlertRule,
  type AlertFormState,
  INITIAL_ALERT_FORM,
} from "./buybackTypes";

/* ─── AlertRuleForm サブコンポーネント ─────────────────────────────────── */

interface AlertRuleFormProps {
  onSave: (form: AlertFormState) => Promise<void>;
  onCancel: () => void;
}

function AlertRuleForm({ onSave, onCancel }: AlertRuleFormProps) {
  const { t } = useTranslation();
  const [form, setForm] = useState<AlertFormState>(INITIAL_ALERT_FORM);
  const [saving, setSaving] = useState(false);

  const set = (field: keyof AlertFormState, value: string | boolean) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await onSave(form);
    } finally {
      setSaving(false);
    }
  };

  const directionOptions = [
    { value: "down", label: t("buybackPrices.alertDirectionDown") },
    { value: "up", label: t("buybackPrices.alertDirectionUp") },
    { value: "both", label: t("buybackPrices.alertDirectionBoth") },
  ];

  const gradeOptions = [
    { value: "price_s", label: "S" },
    { value: "price_a", label: "A" },
    { value: "price_am", label: "A-" },
    { value: "price_b", label: "B" },
    { value: "price_c", label: "C" },
  ];

  const gameOptions = [
    { value: "", label: t("buybackPrices.allGames") },
    { value: "pokemon", label: t("buybackPrices.pokemon") },
    { value: "onepiece", label: t("buybackPrices.onepiece") },
    { value: "yugioh", label: t("buybackPrices.yugioh") },
    { value: "dragonball", label: t("buybackPrices.dragonball") },
    { value: "weiss", label: t("buybackPrices.weiss") },
    { value: "lorcana", label: t("buybackPrices.lorcana") },
  ];

  const shopOptions = [
    { value: "", label: t("buybackPrices.allShops") },
    { value: "shinsoku", label: t("buybackPrices.shinsoku") },
    { value: "homura", label: t("buybackPrices.homura") },
  ];

  return (
    <Card variant="container">
      <form onSubmit={handleSubmit}>
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
          <TextField
            label={t("buybackPrices.alertName")}
            value={form.name}
            onChange={(e) => set("name", e.target.value)}
            required
            size="sm"
            fullWidth
          />

          <div style={{ display: "flex", gap: "var(--space-3)", flexWrap: "wrap" }}>
            <div style={{ flex: "1 1 160px" }}>
              <label style={{ display: "block", fontSize: "var(--font-size-sm)", color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}>
                {t("buybackPrices.alertDirection")}
              </label>
              <SelectControl
                options={directionOptions}
                value={form.direction}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => set("direction", e.target.value)}
                size="sm"
              />
            </div>

            <div style={{ flex: "1 1 120px" }}>
              <TextField
                label={t("buybackPrices.alertThreshold")}
                type="number"
                value={form.threshold_pct}
                onChange={(e) => set("threshold_pct", e.target.value)}
                min="0"
                max="100"
                step="0.1"
                required
                size="sm"
                fullWidth
              />
            </div>

            <div style={{ flex: "1 1 120px" }}>
              <label style={{ display: "block", fontSize: "var(--font-size-sm)", color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}>
                {t("buybackPrices.alertGrade")}
              </label>
              <SelectControl
                options={gradeOptions}
                value={form.price_grade}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => set("price_grade", e.target.value)}
                size="sm"
              />
            </div>
          </div>

          <div style={{ display: "flex", gap: "var(--space-3)", flexWrap: "wrap" }}>
            <div style={{ flex: "1 1 160px" }}>
              <label style={{ display: "block", fontSize: "var(--font-size-sm)", color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}>
                {t("buybackPrices.alertCardGame")}
              </label>
              <SelectControl
                options={gameOptions}
                value={form.card_game}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => set("card_game", e.target.value)}
                size="sm"
              />
            </div>

            <div style={{ flex: "1 1 160px" }}>
              <label style={{ display: "block", fontSize: "var(--font-size-sm)", color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}>
                {t("buybackPrices.alertShop")}
              </label>
              <SelectControl
                options={shopOptions}
                value={form.shop_code}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => set("shop_code", e.target.value)}
                size="sm"
              />
            </div>

            <div style={{ flex: "1 1 120px" }}>
              <TextField
                label={t("buybackPrices.alertCooldown")}
                type="number"
                value={form.cooldown_minutes}
                onChange={(e) => set("cooldown_minutes", e.target.value)}
                min="1"
                required
                size="sm"
                fullWidth
              />
            </div>
          </div>

          <div style={{ display: "flex", gap: "var(--space-2)", justifyContent: "flex-end" }}>
            <Button type="button" variant="ghost" size="sm" onClick={onCancel}>
              {t("buybackPrices.alertCancel")}
            </Button>
            <Button type="submit" variant="primary" size="sm" disabled={saving}>
              {t("buybackPrices.alertSave")}
            </Button>
          </div>
        </div>
      </form>
    </Card>
  );
}

interface AlertRulesResponse {
  items: AlertRule[];
}

/* ─── BuybackAlertModal ─────────────────────────────────────────────────── */

interface BuybackAlertModalProps {
  open: boolean;
  onClose: () => void;
}

export function BuybackAlertModal({ open, onClose }: BuybackAlertModalProps) {
  const { t } = useTranslation();
  const [alertRules, setAlertRules] = useState<AlertRule[]>([]);
  const [alertLoading, setAlertLoading] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);

  React.useEffect(() => {
    if (!open) return;
    setAlertLoading(true);
    api
      .get<AlertRulesResponse>("/buyback-alerts")
      .then((res) => setAlertRules(res.items))
      .catch(() => { /* ignore */ })
      .finally(() => setAlertLoading(false));
  }, [open]);

  const fetchAlertRules = async () => {
    setAlertLoading(true);
    try {
      const res = await api.get<AlertRulesResponse>("/buyback-alerts");
      setAlertRules(res.items);
    } catch { /* ignore */ }
    setAlertLoading(false);
  };

  const createAlertRule = async (form: AlertFormState) => {
    await api.post("/buyback-alerts", {
      name: form.name,
      card_game: form.card_game || null,
      shop_code: form.shop_code || null,
      product_type: form.product_type || null,
      direction: form.direction,
      threshold_pct: parseFloat(form.threshold_pct),
      price_grade: form.price_grade,
      is_active: form.is_active,
      cooldown_minutes: parseInt(form.cooldown_minutes, 10),
    });
    await fetchAlertRules();
    setShowCreateForm(false);
  };

  const toggleAlertRule = async (rule: AlertRule) => {
    await api.put(`/buyback-alerts/${rule.id}`, {
      ...rule,
      is_active: !rule.is_active,
    });
    await fetchAlertRules();
  };

  const deleteAlertRule = async (id: string) => {
    await api.delete(`/buyback-alerts/${id}`);
    await fetchAlertRules();
  };

  const handleClose = () => {
    setShowCreateForm(false);
    onClose();
  };

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title={t("buybackPrices.alertSettings")}
      size="lg"
    >
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
        {!showCreateForm && (
          <Button variant="secondary" size="sm" onClick={() => setShowCreateForm(true)}>
            {t("buybackPrices.alertCreate")}
          </Button>
        )}

        {showCreateForm && (
          <AlertRuleForm
            onSave={createAlertRule}
            onCancel={() => setShowCreateForm(false)}
          />
        )}

        {alertLoading ? (
          <p style={{ color: "var(--text-secondary)" }}>{t("buybackPrices.loading")}</p>
        ) : alertRules.length === 0 ? (
          <p style={{ color: "var(--text-muted)" }}>{t("buybackPrices.alertNoRules")}</p>
        ) : (
          alertRules.map((rule) => (
            <Card key={rule.id} variant="container">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "var(--space-2)" }}>
                <div>
                  <strong>{rule.name}</strong>
                  <p style={{ color: "var(--text-secondary)", fontSize: "var(--font-size-sm)", margin: 0 }}>
                    {rule.direction === "down"
                      ? t("buybackPrices.alertDirectionDown")
                      : rule.direction === "up"
                        ? t("buybackPrices.alertDirectionUp")
                        : t("buybackPrices.alertDirectionBoth")}
                    {" "}{rule.threshold_pct}% | {rule.price_grade}
                    {rule.card_game && ` | ${rule.card_game}`}
                    {rule.shop_code && ` | ${rule.shop_code}`}
                  </p>
                </div>
                <div style={{ display: "flex", gap: "var(--space-2)", alignItems: "center", flexShrink: 0 }}>
                  <Badge variant={rule.is_active ? "success" : "neutral"} size="sm">
                    {rule.is_active ? t("buybackPrices.alertActive") : t("buybackPrices.alertInactive")}
                  </Badge>
                  <Button variant="ghost" size="sm" onClick={() => toggleAlertRule(rule)}>
                    {rule.is_active ? t("buybackPrices.alertDisable") : t("buybackPrices.alertEnable")}
                  </Button>
                  <Button variant="danger" size="sm" onClick={() => deleteAlertRule(rule.id)}>
                    {t("buybackPrices.alertDelete")}
                  </Button>
                </div>
              </div>
            </Card>
          ))
        )}
      </div>
    </Modal>
  );
}
