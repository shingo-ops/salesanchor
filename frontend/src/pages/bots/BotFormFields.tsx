/**
 * BotFormFields — Bot 編集フォームフィールド（共通）
 *
 * BotsPage（Drawer内）と BotEditPage（フルページ）の両方で使用。
 * bot_code は作成時のみのため含まない。
 * staff 一覧は呼び出し元から渡す。
 */

import { useTranslation } from "react-i18next";

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
      <div className="form-group">
        <label>{t("bots.purposeLabel")} *</label>
        <select
          required
          value={form.purpose}
          onChange={(e) => onChange("purpose", e.target.value)}
        >
          <option value="invoice">{t("bots.purposeInvoice")}</option>
          <option value="shipment">{t("bots.purposeShipment")}</option>
          <option value="notification">{t("bots.purposeNotification")}</option>
          <option value="custom">{t("bots.purposeCustom")}</option>
        </select>
      </div>
      <div className="form-group">
        <label>{t("common.status")}</label>
        <select
          value={form.status}
          onChange={(e) => onChange("status", e.target.value)}
        >
          <option value="active">{t("bots.statusActive")}</option>
          <option value="inactive">{t("bots.statusInactive")}</option>
          <option value="maintenance">{t("bots.statusMaintenance")}</option>
        </select>
      </div>
      <div className="form-group">
        <label>{t("bots.ownerStaff")} *</label>
        <select
          required
          value={form.owner_staff_id}
          onChange={(e) => onChange("owner_staff_id", e.target.value)}
        >
          <option value="">{t("common.pleaseSelect")}</option>
          {staff.map((s) => (
            <option key={s.id} value={s.id}>
              {s.surname_jp} {s.given_name_jp}
            </option>
          ))}
        </select>
      </div>
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
