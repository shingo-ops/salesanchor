/**
 * DistributionSettingsDrawer — 配信設定ドロワー
 *
 * 配信除外時間（max_age_hours）等の設定値を表示・更新する。
 * API: GET /tcg/distribution/settings
 *      PUT /tcg/distribution/settings/max_age_hours
 *
 * ADR-027: 全UI文字列は t("key") 経由。
 * ADR-144: 金型コンポーネント（Drawer, TextField, Button）のみ使用。
 */
import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Drawer } from "../../../components/Drawer";
import { TextField } from "../../../components/TextField";
import { Button } from "../../../components/Button";
import { api } from "../../../lib/api";

interface DistributionSetting {
  key: string;
  value: string;
  note: string | null;
}

interface DistributionSettingsDrawerProps {
  open: boolean;
  onClose: () => void;
}

export function DistributionSettingsDrawer({
  open,
  onClose,
}: DistributionSettingsDrawerProps) {
  const { t } = useTranslation();
  const [maxAgeHours, setMaxAgeHours] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // open 時にAPIから設定を取得
  useEffect(() => {
    if (!open) return;
    setSaved(false);
    setError(null);
    api
      .get<DistributionSetting[]>("/tcg/distribution/settings")
      .then((settings) => {
        const found = settings.find((s) => s.key === "max_age_hours");
        if (found) setMaxAgeHours(found.value);
      })
      .catch(() => {
        // 取得失敗時は空のまま編集可能にする
      });
  }, [open]);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      await api.put("/tcg/distribution/settings/max_age_hours", {
        value: maxAgeHours,
      });
      setSaved(true);
    } catch {
      setError(t("analysisRules.errors.unknown"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title={t("distributionSettings.drawerTitle")}
    >
      <div>
        <TextField
          type="number"
          label={t("distributionSettings.maxAgeHours.label")}
          value={maxAgeHours}
          onChange={(e) => {
            setMaxAgeHours(e.target.value);
            setSaved(false);
          }}
          min={0}
          fullWidth
        />
        <p
          style={{
            color: "var(--color-text-secondary)",
            fontSize: "var(--font-size-sm)",
            marginTop: "var(--space-xs)",
          }}
        >
          {t("distributionSettings.maxAgeHours.description")}
        </p>
      </div>
      {error != null && (
        <p
          style={{
            color: "var(--color-error)",
            fontSize: "var(--font-size-sm)",
            marginTop: "var(--space-sm)",
          }}
        >
          {error}
        </p>
      )}
      <div style={{ marginTop: "var(--space-lg)" }}>
        <Button variant="primary" onClick={handleSave} disabled={saving}>
          {saved
            ? t("distributionSettings.saved")
            : t("distributionSettings.save")}
        </Button>
      </div>
    </Drawer>
  );
}
