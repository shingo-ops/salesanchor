/**
 * 書類に載せる会社情報（国内用・海外用のタブ）（ADR-1061 便2-2c2b。design.md §3-4・§3-4a・§3-4b）。
 *
 * 正本は会社ごとの tenant_issuer_profiles（国内用・海外用の2行まで）。
 * 行が無いタブは、前の会社情報（古い6欄）を読むだけの欄で見せ、入れ直しを案内する。
 * 都道府県と国の一覧は API から読む（画面のコードに名前を書かない）。
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { ApiError, api } from "../../lib/api";
import { useApiCache, useApiQuery } from "../../lib/query/apiQuery";
import { useSeededForm } from "../../lib/query/useSeededForm";
import { Button } from "../../components/Button";
import { Callout } from "../../components/Callout";
import { CountryCombobox } from "../../components/CountryCombobox";
import { SectionCard } from "../../components/SectionCard";
import { Select } from "../../components/Select";
import { Stack } from "../../components/Stack";
import { Tabs } from "../../components/Tabs";
import { TextField } from "../../components/TextField";
import { Textarea } from "../../components/Textarea";
import { LoadingBlock } from "../../components/loading";
import { InvoiceRegistrationField } from "./InvoiceRegistrationField";
import {
  ISSUER_PROFILES_PATH,
  PREFECTURES_PATH,
  emptyIssuerForm,
  fieldErrorKeys,
  isJapan,
  legacyText,
  prefectureOptions,
  toIssuerForm,
  toIssuerPayload,
  toRegionForm,
  type FieldErrors,
  type IssuerProfile,
  type IssuerProfiles,
  type IssuerRegion,
  type Prefecture,
  type RegionForm,
} from "./issuerProfileForm";

interface IssuerProfileSectionProps {
  canEdit: boolean;
}

export function IssuerProfileSection({ canEdit }: IssuerProfileSectionProps) {
  const { t, i18n } = useTranslation();
  const [region, setRegion] = useState<IssuerRegion>("domestic");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});

  const profilesQ = useApiQuery<IssuerProfiles>(ISSUER_PROFILES_PATH);
  const prefecturesQ = useApiQuery<Prefecture[]>(PREFECTURES_PATH);
  const { form, setForm, ready } = useSeededForm(ISSUER_PROFILES_PATH, profilesQ.data, toIssuerForm, emptyIssuerForm);
  const cache = useApiCache();
  const readError = profilesQ.error ? (profilesQ.error instanceof Error ? profilesQ.error.message : t("common.fetchError")) : "";

  const current = form[region];
  const row = profilesQ.data?.[region] ?? null;
  const legacy = profilesQ.data?.legacy ?? null;
  const jp = isJapan(current);
  const locked = !canEdit;
  const idp = `issuer-${region}`;
  const fieldError = (key: keyof RegionForm): string | undefined => {
    const messageKey = fieldErrors[key];
    return messageKey ? t(messageKey) : undefined;
  };

  const update = <K extends keyof RegionForm>(key: K, value: RegionForm[K]) => {
    setForm((prev) => ({ ...prev, [region]: { ...prev[region], [key]: value } }));
  };

  const changeRegion = (next: IssuerRegion) => {
    setRegion(next);
    setFieldErrors({});
    setError("");
    setInfo("");
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setInfo("");
    setFieldErrors({});
    setSaving(true);
    try {
      const saved = await api.put<IssuerProfile>(`${ISSUER_PROFILES_PATH}/${region}`, toIssuerPayload(current));
      const base: IssuerProfiles = profilesQ.data ?? { domestic: null, overseas: null, legacy: null };
      cache.write(ISSUER_PROFILES_PATH, { ...base, [region]: saved });
      setForm((prev) => ({ ...prev, [region]: toRegionForm(saved) }));
      setInfo(region === "domestic" ? t("issuerProfile.savedDomestic") : t("issuerProfile.savedOverseas"));
    } catch (err) {
      const keys = err instanceof ApiError && err.status === 422 ? fieldErrorKeys(err.responseDetail) : null;
      if (keys) {
        setFieldErrors(keys);
        setError(t("issuerProfile.fixFields"));
      } else {
        setError(err instanceof Error ? err.message : t("common.operationError"));
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <SectionCard title={t("issuerProfile.sectionTitle")}>
      {profilesQ.isPending ? (
        <LoadingBlock />
      ) : !ready ? (
        <div className="error-message">{readError}</div>
      ) : (
        <form className="form" onSubmit={handleSave} data-testid="issuer-profile-form">
          <Stack gap="4">
            <Tabs<IssuerRegion>
              items={[
                { key: "domestic", label: t("issuerProfile.tabDomestic") },
                { key: "overseas", label: t("issuerProfile.tabOverseas") },
              ]}
              activeKey={region}
              onChange={changeRegion}
              variant="underline"
            />
            {error && <div className="error-message">{error}</div>}
            {info && <div className="info-message" data-testid="issuer-profile-info">{info}</div>}
            {row === null && (
              <Callout variant="info" title={t("issuerProfile.legacyTitle")}>
                <Stack gap="2">
                  <p>{t("issuerProfile.legacyBody")}</p>
                  {legacy && legacyText(legacy) !== "" && (
                    <Textarea
                      id={`${idp}-legacy`}
                      label={t("issuerProfile.legacyValues")}
                      value={legacyText(legacy)}
                      readOnly
                      rows={6}
                    />
                  )}
                </Stack>
              </Callout>
            )}
            <TextField
              id={`${idp}-company-name`}
              data-testid={`${idp}-company-name`}
              label={t("issuerProfile.companyName")}
              value={current.company_name}
              onChange={(e) => update("company_name", e.target.value)}
              error={fieldError("company_name")}
              disabled={locked}
              maxLength={255}
              required
              fullWidth
            />
            <TextField
              id={`${idp}-email`}
              label={t("issuerProfile.email")}
              type="email"
              value={current.email}
              onChange={(e) => update("email", e.target.value)}
              error={fieldError("email")}
              disabled={locked}
              maxLength={255}
              fullWidth
            />
            <TextField
              id={`${idp}-website`}
              label={t("issuerProfile.website")}
              value={current.website}
              onChange={(e) => update("website", e.target.value)}
              error={fieldError("website")}
              disabled={locked}
              maxLength={255}
              fullWidth
            />
            <div className="form-group">
              <label htmlFor={`${idp}-country`}>{t("issuerProfile.country")}</label>
              <CountryCombobox
                id={`${idp}-country`}
                value={current.country_code}
                onChange={(value) => update("country_code", value)}
                disabled={locked}
                required
              />
              {fieldError("country_code") && <div className="error-message">{fieldError("country_code")}</div>}
            </div>
            <TextField
              id={`${idp}-postal-code`}
              label={t("issuerProfile.postalCode")}
              helperText={jp ? t("issuerProfile.postalHintJp") : t("issuerProfile.postalHintForeign")}
              value={current.postal_code}
              onChange={(e) => update("postal_code", e.target.value)}
              error={fieldError("postal_code")}
              disabled={locked}
              maxLength={10}
              required={jp}
              fullWidth
            />
            {jp ? (
              <Select
                id={`${idp}-prefecture`}
                label={t("issuerProfile.prefecture")}
                placeholder={t("issuerProfile.prefecturePlaceholder")}
                options={prefectureOptions(prefecturesQ.data ?? [], i18n.language)}
                value={current.prefecture_code}
                onChange={(e) => update("prefecture_code", e.target.value)}
                error={fieldError("prefecture_code")}
                disabled={locked}
                required
                fullWidth
              />
            ) : (
              <TextField
                id={`${idp}-state-region`}
                label={t("issuerProfile.stateRegion")}
                value={current.state_region}
                onChange={(e) => update("state_region", e.target.value)}
                error={fieldError("state_region")}
                disabled={locked}
                maxLength={100}
                fullWidth
              />
            )}
            <TextField
              id={`${idp}-city`}
              label={t("issuerProfile.city")}
              value={current.city}
              onChange={(e) => update("city", e.target.value)}
              error={fieldError("city")}
              disabled={locked}
              maxLength={100}
              required
              fullWidth
            />
            <TextField
              id={`${idp}-address1`}
              label={t("issuerProfile.address1")}
              value={current.address1}
              onChange={(e) => update("address1", e.target.value)}
              error={fieldError("address1")}
              disabled={locked}
              maxLength={255}
              required
              fullWidth
            />
            <TextField
              id={`${idp}-address2`}
              label={t("issuerProfile.address2")}
              value={current.address2}
              onChange={(e) => update("address2", e.target.value)}
              error={fieldError("address2")}
              disabled={locked}
              fullWidth
            />
            <TextField
              id={`${idp}-phone`}
              label={t("issuerProfile.phone")}
              helperText={jp ? t("issuerProfile.phoneHintJp") : t("issuerProfile.phoneHintForeign")}
              value={current.phone}
              onChange={(e) => update("phone", e.target.value)}
              error={fieldError("phone")}
              disabled={locked}
              maxLength={16}
              fullWidth
            />
            <InvoiceRegistrationField
              idPrefix={idp}
              registered={current.is_invoice_registered}
              number={current.registration_number}
              disabled={locked}
              error={fieldError("registration_number")}
              onRegisteredChange={(next) => update("is_invoice_registered", next)}
              onNumberChange={(next) => update("registration_number", next)}
            />
            {canEdit && (
              <div className="form-actions">
                <Button loading={saving} variant="primary" size="md"
                  type="submit"
                  disabled={saving}
                  data-testid="issuer-profile-save"
                >
                  {t("common.save")}
                </Button>
              </div>
            )}
          </Stack>
        </form>
      )}
    </SectionCard>
  );
}
