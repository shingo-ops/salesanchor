/**
 * 住所追加・編集モーダル。
 * addrPhoneError / addrModalError / addrSubmitting はモーダル内ローカル状態で管理。
 */

import { useState, FormEvent } from "react";
import { useTranslation } from "react-i18next";
import type { AddressFormState, Company } from "./company-detail.types";
import { addressFromApi, typeLabel, PHONE_RE } from "./company-detail.types";
import { Modal } from "../../components/Modal";
import { Button } from "../../components/Button";
import { TextField } from "../../components/TextField";
import { Select } from "../../components/Select";
import { Checkbox } from "../../components/Checkbox";
import { DELIVERY_ADDRESS_LINE_MAX, deliveryAddressLineError } from "../../utils/addressRules";

type LineKey = "address_line_1" | "address_line_2" | "address_line_3";
const LINE_KEYS: readonly LineKey[] = ["address_line_1", "address_line_2", "address_line_3"];

interface Props {
  isOpen: boolean;
  onClose: () => void;
  addrForm: AddressFormState;
  setAddrForm: (form: AddressFormState) => void;
  submitAddresses: (next: AddressFormState[]) => Promise<void>;
  company: Company;
  canEdit: boolean;
  handleAddressTypeChange: (newType: "billing" | "delivery") => void;
}

export function CompanyAddressModal({
  isOpen, onClose, addrForm, setAddrForm,
  submitAddresses, company, canEdit, handleAddressTypeChange,
}: Props) {
  const { t } = useTranslation();
  const [addrSubmitting, setAddrSubmitting] = useState(false);
  const [addrPhoneError, setAddrPhoneError] = useState<string | null>(null);
  const [addrModalError, setAddrModalError] = useState<string | null>(null);
  const [lineErrors, setLineErrors] = useState<Partial<Record<LineKey, string>>>({});

  /** 住所1〜3を打ち直したら、その欄の赤を消す。 */
  const setLine = (key: LineKey, value: string) => {
    setAddrForm({ ...addrForm, [key]: value });
    setLineErrors((prev) => ({ ...prev, [key]: undefined }));
  };

  const handleSave = async (e: FormEvent) => {
    e.preventDefault();
    setAddrModalError(null);
    // クライアント電話番号バリデーション
    if (addrForm.telephone) {
      const cleaned = addrForm.telephone.replace(/[\s\-()]/g, "");
      if (!PHONE_RE.test(cleaned)) {
        setAddrPhoneError(t("companies.phoneError"));
        return;
      }
    }
    setAddrPhoneError(null);
    // 送り先だけ住所1〜3に決まりを当てる（保存を押した時だけ赤くする・請求先は確かめない）
    if (addrForm.address_type === "delivery") {
      const found: Partial<Record<LineKey, string>> = {};
      for (const key of LINE_KEYS) {
        const ruleKey = deliveryAddressLineError(addrForm[key]);
        if (ruleKey) found[key] = t(ruleKey, { max: DELIVERY_ADDRESS_LINE_MAX });
      }
      if (Object.keys(found).length > 0) {
        setLineErrors(found);
        return;
      }
    }
    setLineErrors({});
    // F5: country_code は空 or 2 文字のみ許容
    if (addrForm.country_code && addrForm.country_code.length !== 2) {
      setAddrModalError(t("companies.countryCodeError"));
      return;
    }
    setAddrSubmitting(true);
    try {
      const currentForms = (company.addresses || []).map(addressFromApi);
      let next: AddressFormState[];
      if (addrForm.id === null) {
        next = [...currentForms, addrForm];
      } else {
        next = currentForms.map((a) => (a.id === addrForm.id ? addrForm : a));
      }
      await submitAddresses(next);
      onClose();
    } catch (err) {
      setAddrModalError(err instanceof Error ? err.message : t("common.saveError"));
    } finally {
      setAddrSubmitting(false);
    }
  };

  /* eslint-disable local/no-japanese-literal -- TODO: 文章全体を1翻訳キーに統合（ADR-027 既知負債） */
  const addrTitle = addrForm.id === null
    ? `${typeLabel(t, addrForm.address_type)}${t("companies.address")}を${t("common.add")}`
    : `${typeLabel(t, addrForm.address_type)}${t("companies.address")}を${t("common.edit")}`;
  /* eslint-enable local/no-japanese-literal */

  return (
    <Modal open={isOpen} onClose={onClose} title={addrTitle} size="lg">
      <div className="modal-content-wide">
        {/* F6: モーダル内エラー（page top の error-banner は overlay で隠れる） */}
        {addrModalError && <div className="error-banner">{addrModalError}</div>}
        <form onSubmit={handleSave} className="form-grid">
          <div className="form-row">
            <label>{t("common.type")}</label>
            <Select
              options={[
                { value: "billing", label: t("companies.billing") },
                { value: "delivery", label: t("companies.delivery") },
              ]}
              disabled={!canEdit || addrSubmitting}
              value={addrForm.address_type}
              onChange={(e) => { setLineErrors({}); handleAddressTypeChange(e.target.value as "billing" | "delivery"); }}
            />
          </div>
          <div className="form-row">
            <label>{t("companies.branchNameHint")}</label>
            <TextField disabled={!canEdit || addrSubmitting} value={addrForm.branch_name}
              onChange={(e) => setAddrForm({ ...addrForm, branch_name: e.target.value })} />
          </div>
          <div className="form-row"><label>{t("companies.contactName")}</label>
            <TextField disabled={!canEdit || addrSubmitting} value={addrForm.name}
              onChange={(e) => setAddrForm({ ...addrForm, name: e.target.value })} />
          </div>
          <div className="form-row"><label>{t("common.email")}</label>
            <TextField type="email" disabled={!canEdit || addrSubmitting} value={addrForm.email}
              onChange={(e) => setAddrForm({ ...addrForm, email: e.target.value })} />
          </div>
          <div className="form-row"><label>{t("common.phone")}</label>
            <TextField disabled={!canEdit || addrSubmitting} value={addrForm.telephone}
              onChange={(e) => setAddrForm({ ...addrForm, telephone: e.target.value })}
              error={addrPhoneError ?? undefined} />
          </div>
          <div className="form-row"><label>{t("companies.taxId")}</label>
            <TextField disabled={!canEdit || addrSubmitting} value={addrForm.tax_id}
              onChange={(e) => setAddrForm({ ...addrForm, tax_id: e.target.value })} />
          </div>
          <div className="form-row"><label>{t("shipping.address1")}</label>
            <TextField disabled={!canEdit || addrSubmitting} value={addrForm.address_line_1}
              onChange={(e) => setLine("address_line_1", e.target.value)}
              error={lineErrors.address_line_1} />
          </div>
          <div className="form-row"><label>{t("shipping.address2")}</label>
            <TextField disabled={!canEdit || addrSubmitting} value={addrForm.address_line_2}
              onChange={(e) => setLine("address_line_2", e.target.value)}
              error={lineErrors.address_line_2} />
          </div>
          <div className="form-row"><label>{t("shipping.address3")}</label>
            <TextField disabled={!canEdit || addrSubmitting} value={addrForm.address_line_3}
              onChange={(e) => setLine("address_line_3", e.target.value)}
              error={lineErrors.address_line_3} />
          </div>
          <div className="form-row"><label>{t("shipping.city")}</label>
            <TextField disabled={!canEdit || addrSubmitting} value={addrForm.city}
              onChange={(e) => setAddrForm({ ...addrForm, city: e.target.value })} />
          </div>
          <div className="form-row"><label>{t("shipping.stateCode")}</label>
            <TextField disabled={!canEdit || addrSubmitting} value={addrForm.state}
              onChange={(e) => setAddrForm({ ...addrForm, state: e.target.value })} />
          </div>
          <div className="form-row"><label>{t("shipping.zipCode")}</label>
            <TextField disabled={!canEdit || addrSubmitting} value={addrForm.zip}
              onChange={(e) => setAddrForm({ ...addrForm, zip: e.target.value })} />
          </div>
          <div className="form-row">
            <label>{t("shipping.countryCode")}{t("companies.countryCodeHint")}</label>
            <TextField maxLength={2} disabled={!canEdit || addrSubmitting} value={addrForm.country_code}
              onChange={(e) => setAddrForm({ ...addrForm, country_code: e.target.value.toUpperCase() })} />
          </div>
          <div className="form-row">
            <Checkbox
              label={t("companies.setAsDefault")}
              disabled={!canEdit || addrSubmitting}
              checked={addrForm.is_default}
              onChange={(e) => setAddrForm({ ...addrForm, is_default: e.target.checked })}
            />
          </div>
          <div className="form-actions">
            <Button type="button" variant="secondary" onClick={onClose} disabled={addrSubmitting}>{t("common.cancel")}</Button>
            <Button loading={addrSubmitting} type="submit" disabled={!canEdit || addrSubmitting}>
              {t("common.save")}
            </Button>
          </div>
        </form>
      </div>
    </Modal>
  );
}
