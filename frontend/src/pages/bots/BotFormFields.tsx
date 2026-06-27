/**
 * BotFormFields — Bot 編集フォームフィールド（共通）
 *
 * BotsPage（Drawer内）と BotEditPage（フルページ）の両方で使用。
 * bot_code は作成時のみのため含まない。
 * staff 一覧は呼び出し元から渡す。
 */

import { useTranslation } from "react-i18next";
import { Select } from "../../components/Select";

export interface BotFormState {
  display_name: string;
  purpose: string;
  status: string;
  owner_staff_id: string;
  discord_user_id: string;
  sender_email: string;
}

export interface BotStaff {
  id: number;
  surname_jp: string;
  given_name_jp: string;
}

interface Props {
  form: BotFormState;
  onChange: (field: keyof BotFormState, value: string) => void;
  staff: BotStaff[];
}

export function BotFormFields({ form, onChange, staff }: Props) {
  const { t } = useTranslation();
  const purposeOptions = [
    { value: "invoice", label: t("bots.purposeInvoice") },
    { value: "shipment", label: t("bots.purposeShipment") },
    { value: "notification", label: t("bots.purposeNotification") },
    { value: "custom", label: t("bots.purposeCustom") },
  ];
  const statusOptions = [
    { value: "active", label: t("bots.statusActive") },
    { value: "inactive", label: t("bots.statusInactive") },
    { value: "maintenance", label: t("bots.statusMaintenance") },
  ];
  const staffOptions = staff.map((s) => ({
    value: String(s.id),
    label: `${s.surname_jp} ${s.given_name_jp}`,
  }));
  return (
    <>
      <div className="form-group">
        <label>{t("bots.displayName")} *</label>
        <input
          required
          value={form.display_name}
          onChange={(e) => onChange("display_name", e.target.value)}
        />
      </div>
      <Select
        label={t("bots.purposeLabel")}
        required
        value={form.purpose}
        onChange={(e) => onChange("purpose", e.target.value)}
        options={purposeOptions}
      />
      <Select
        label={t("common.status")}
        value={form.status}
        onChange={(e) => onChange("status", e.target.value)}
        options={statusOptions}
      />
      <Select
        label={t("bots.ownerStaff")}
        required
        value={form.owner_staff_id}
        onChange={(e) => onChange("owner_staff_id", e.target.value)}
        options={staffOptions}
        placeholder={t("common.pleaseSelect")}
      />
      <div className="form-group">
        <label>Discord Bot ID</label>
        <input
          value={form.discord_user_id}
          onChange={(e) => onChange("discord_user_id", e.target.value)}
        />
      </div>
      <div className="form-group">
        <label>{t("bots.senderEmail")}</label>
        <input
          type="email"
          value={form.sender_email}
          onChange={(e) => onChange("sender_email", e.target.value)}
        />
      </div>
    </>
  );
}
