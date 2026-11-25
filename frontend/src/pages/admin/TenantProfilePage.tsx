/**
 * TenantProfilePage（会社情報。Sprint 8 / F8 → ADR-1061 便2-2c2b）
 *
 * 上から: 印鑑画像 URL・既定の言語（この画面のフォーム）、書類に載せる会社情報（国内用・海外用。IssuerProfileSection）。
 * 会社名・住所・電話・メール・サイトの欄は IssuerProfileSection へ移した（design.md §3-4）。
 *
 * 権限:
 *   tenant.profile.view → 閲覧
 *   tenant.profile.edit → 保存
 *
 * 関連:
 *   backend/app/routers/tenant_profile.py
 *   backend/app/routers/issuer_profiles.py
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { useApiCache, useApiQuery } from "../../lib/query/apiQuery";
import { useSeededForm } from "../../lib/query/useSeededForm";
import { usePermissions } from "../../hooks/usePermissions";
import { PageLayout } from "../../components/PageLayout";
import { Button } from "../../components/Button";
import { SelectControl } from "../../components/Select";
import { Stack } from "../../components/Stack";
import { TextFieldControl } from "../../components/TextField";
import { LoadingBlock } from "../../components/loading";
import { IssuerProfileSection } from "./IssuerProfileSection";

interface TenantProfile {
  id: number;
  seal_image_url: string | null;
  default_language: string;
  created_at: string;
  updated_at: string;
}

interface FormState {
  seal_image_url: string;
  default_language: string;
}

const emptyForm: FormState = {
  seal_image_url: "",
  default_language: "ja",
};

const PROFILE_PATH = "/admin/tenant-profile";
const toForm = (data: TenantProfile): FormState => ({
  seal_image_url: data.seal_image_url ?? "",
  default_language: data.default_language ?? "ja",
});

export default function TenantProfilePage() {
  const { t } = useTranslation();
  const { hasPermission } = usePermissions();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  const canView = hasPermission("tenant.profile.view");
  const canEdit = hasPermission("tenant.profile.edit");
  const profileQ = useApiQuery<TenantProfile>(PROFILE_PATH, { enabled: canView });
  const { form, setForm, ready } = useSeededForm(PROFILE_PATH, profileQ.data, toForm, emptyForm);
  const cache = useApiCache();
  const readError = profileQ.error ? (profileQ.error instanceof Error ? profileQ.error.message : t("common.fetchError")) : "";
  const shownError = error || readError;

  const handleChange = (key: keyof FormState) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>,
  ) => {
    setForm((prev) => ({ ...prev, [key]: e.target.value }));
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setInfo("");
    setSaving(true);
    try {
      // 空文字は null に変換 (バックエンド側で null と空文字を等価扱い)
      const payload: Record<string, string | null> = {};
      (Object.keys(form) as Array<keyof FormState>).forEach((k) => {
        const v = form[k];
        payload[k] = v === "" ? null : v;
      });
      const saved = await api.put<TenantProfile>("/admin/tenant-profile", payload);
      cache.write(PROFILE_PATH, saved);
      setInfo(t("tenantProfile.saved"));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.operationError"));
    } finally {
      setSaving(false);
    }
  };

  if (!canView) {
    return (
      <PageLayout navKey="nav.tenantProfile">
        <div className="error-message">{t("tenantProfile.permissionRequired")}</div>
      </PageLayout>
    );
  }

  return (
    <PageLayout navKey="nav.tenantProfile" subtitleKey="tenantProfile.subtitle">
      {profileQ.isPending ? (
        <LoadingBlock />
      ) : !ready ? (
        <div className="error-message">{shownError}</div>
      ) : (
        <Stack gap="6">
          <form className="form" onSubmit={handleSave} data-testid="tenant-profile-form">
            {shownError && <div className="error-message">{shownError}</div>}
            {info && <div className="info-message" data-testid="tenant-profile-info">{info}</div>}

            <div className="form-group">
              <label htmlFor="tp-seal-url">{t("tenantProfile.sealImageUrl")}</label>
              <TextFieldControl
                id="tp-seal-url"
                data-testid="tp-seal-image-url"
                type="text"
                value={form.seal_image_url}
                onChange={handleChange("seal_image_url")}
                disabled={!canEdit}
                placeholder="https://..."
              />
              <small className="form-hint">{t("tenantProfile.sealHint")}</small>
            </div>

            <div className="form-group">
              <label htmlFor="tp-default-language">{t("tenantProfile.defaultLanguage")}</label>
              <SelectControl
                fullWidth
                id="tp-default-language"
                data-testid="tp-default-language"
                value={form.default_language}
                onChange={handleChange("default_language")}
                disabled={!canEdit}
              >
                <option value="ja">{t("language.ja")} (ja)</option>
                <option value="en">English (en)</option>
                <option value="ko">한국어 (ko)</option>
                <option value="zh">{t("language.zh")} (zh)</option>
              </SelectControl>
            </div>

            {canEdit && (
              <div className="form-actions">
                <Button loading={saving} variant="primary" size="md"
                  type="submit"

                  disabled={saving}
                  data-testid="tenant-profile-save"
                >
                  {t("common.save")}
                </Button>
              </div>
            )}
          </form>
          <IssuerProfileSection canEdit={canEdit} />
        </Stack>
      )}
    </PageLayout>
  );
}
