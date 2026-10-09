import { useTranslation } from "react-i18next";
import { Callout } from "../../components/Callout";

export interface CodeCollision {
  product_id: string; name: string; work_name: string;
  matched_value: string; matched_field: string;
  suggest_add_to_this: string[]; suggest_add_to_other: string[];
  already_excluded_by_this: string[]; already_excluded_by_other: string[];
}

const fieldKey = (field: string) => (field === "product_code" ? "product_code" : "mark");

/** 型番の重なりを案内する枠。語の自動登録はしない（案内だけ）。 */
export function CodeCollisionNotice({ collisions }: { collisions: CodeCollision[] }) {
  const { t } = useTranslation();
  if (collisions.length === 0) return null;
  return <Callout variant="warning" title={t("codeCollision.title")}>
    <p>{t("codeCollision.hint")}</p>
    <ul>
      {collisions.map(item => <li key={`${item.product_id}-${item.matched_field}`}>
        <strong>{item.work_name
          ? t("codeCollision.itemWithWork", { name: item.name, work: item.work_name })
          : item.name}</strong>
        <div>{t("codeCollision.matched", { field: t(`codeCollision.fields.${fieldKey(item.matched_field)}`), value: item.matched_value })}</div>
        {item.suggest_add_to_this.length > 0 &&
          <div>{t("codeCollision.addToThis", { words: item.suggest_add_to_this.join(", ") })}</div>}
        {item.suggest_add_to_other.length > 0 &&
          <div>{t("codeCollision.addToOther", { words: item.suggest_add_to_other.join(", ") })}</div>}
        {item.suggest_add_to_this.length === 0 && item.suggest_add_to_other.length === 0 &&
          <div>{t("codeCollision.registered")}</div>}
      </li>)}
    </ul>
  </Callout>;
}
