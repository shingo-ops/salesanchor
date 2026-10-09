/**
 * TeamFormFields — チームフォームフィールド（共通）
 *
 * TeamsPage（Drawer内）と TeamEditPage（フルページ）の両方で使用。
 * フォーム状態・onChange のみを受け取り、submit / cancel は呼び出し元が担う。
 */

import { useTranslation } from "react-i18next";
import { TextareaControl } from "../../components/Textarea";
import { TextFieldControl } from "../../components/TextField";

export interface TeamFormState {
  name: string;
  leader_id: string;
  description: string;
}

interface Props {
  form: TeamFormState;
  onChange: (field: keyof TeamFormState, value: string) => void;
}

export function TeamFormFields({ form, onChange }: Props) {
  const { t } = useTranslation();
  return (
    <>
      <div className="form-group">
        <label>{t("teams.teamName")} *</label>
        <TextFieldControl
          required
          value={form.name}
          onChange={(e) => onChange("name", e.target.value)}
        />
      </div>
      <div className="form-group">
        <label>{t("teams.leaderUserIdLabel")}</label>
        <TextFieldControl
          type="number"
          min="1"
          value={form.leader_id}
          onChange={(e) => onChange("leader_id", e.target.value)}
        />
      </div>
      <div className="form-group">
        <label>{t("common.description")}</label>
        <TextareaControl
          value={form.description}
          onChange={(e) => onChange("description", e.target.value)}
        />
      </div>
    </>
  );
}
