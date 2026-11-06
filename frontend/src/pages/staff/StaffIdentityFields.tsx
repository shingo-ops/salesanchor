/**
 * スタッフの本人情報の入力欄（姓名・かな・英語名・主メールの7欄）。
 *
 * 新規作成 Modal（StaffPage）と、スタッフ自己登録の申込ページ（StaffJoinPage）で共用する（ADR-1068）。
 * 見た目と動きは、StaffPage の新規作成 Modal にあった7欄と同じ。
 */

import { useTranslation } from "react-i18next";
import { TextFieldControl } from "../../components/TextField";

export type StaffIdentityState = {
  surname_jp: string;
  given_name_jp: string;
  surname_kana: string;
  given_name_kana: string;
  surname_en: string;
  given_name_en: string;
  primary_email: string;
};

export const emptyStaffIdentity: StaffIdentityState = {
  surname_jp: "",
  given_name_jp: "",
  surname_kana: "",
  given_name_kana: "",
  surname_en: "",
  given_name_en: "",
  primary_email: "",
};

interface Props {
  form: StaffIdentityState;
  onChange: (field: keyof StaffIdentityState, value: string) => void;
}

export function StaffIdentityFields({ form, onChange }: Props) {
  const { t } = useTranslation();
  return (
    <>
      <div className="form-group"><label>{t("staff.surnameJp")} *</label>
        <TextFieldControl required value={form.surname_jp} onChange={(e) => onChange("surname_jp", e.target.value)} />
      </div>
      <div className="form-group"><label>{t("staff.givenNameJp")} *</label>
        <TextFieldControl required value={form.given_name_jp} onChange={(e) => onChange("given_name_jp", e.target.value)} />
      </div>
      <div className="form-group"><label>{t("staff.surnameKana")}</label>
        <TextFieldControl value={form.surname_kana} onChange={(e) => onChange("surname_kana", e.target.value)} />
      </div>
      <div className="form-group"><label>{t("staff.givenNameKana")}</label>
        <TextFieldControl value={form.given_name_kana} onChange={(e) => onChange("given_name_kana", e.target.value)} />
      </div>
      <div className="form-group"><label>{t("staff.surnameEn")} *</label>
        <TextFieldControl required aria-required="true" value={form.surname_en} onChange={(e) => onChange("surname_en", e.target.value)} />
      </div>
      <div className="form-group"><label>{t("staff.givenNameEn")} *</label>
        <TextFieldControl required aria-required="true" value={form.given_name_en} onChange={(e) => onChange("given_name_en", e.target.value)} />
      </div>
      <div className="form-group"><label>{t("staff.primaryEmail")} *</label>
        <TextFieldControl required type="email" value={form.primary_email} onChange={(e) => onChange("primary_email", e.target.value)} />
      </div>
    </>
  );
}
