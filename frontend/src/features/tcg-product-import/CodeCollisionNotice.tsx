import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { TFunction } from "i18next";
import { Callout } from "../../components/Callout";
import { Button } from "../../components/Button";
import ConfirmModal from "../../components/ConfirmModal";
import { ApiError } from "../../lib/api";
import type { AddWordResult } from "./productDetailModel";

export interface CodeCollision {
  product_id: string; name: string; work_name: string;
  matched_value: string; matched_field: string;
  suggest_add_to_this: string[]; suggest_add_to_other: string[];
  already_excluded_by_this: string[]; already_excluded_by_other: string[];
}

interface Props {
  collisions: CodeCollision[];
  /** 相手の商品の除外ワードに足す。渡さなければボタンを出さない */
  onAddToOther?: (productId: number, word: string) => Promise<AddWordResult>;
  /** この商品の除外ワードに足す。渡さなければボタンを出さない */
  onAddToThis?: (word: string) => Promise<AddWordResult>;
  /** この商品に足すとき確認を挟むか（保存済みの商品へ API で足す場合） */
  confirmAddToThis?: boolean;
  thisName?: string;
}
interface Pending { side: "this" | "other"; collision: CodeCollision; word: string }

const fieldKey = (field: string) => (field === "product_code" ? "product_code" : "mark");
const itemName = (c: CodeCollision, t: TFunction) =>
  c.work_name ? t("codeCollision.itemWithWork", { name: c.name, work: c.work_name }) : c.name;

/** 型番の重なりを案内する枠。語の追加は呼び出し側から渡された動きで行う（ここでは API を呼ばない）。 */
export function CodeCollisionNotice({ collisions, onAddToOther, onAddToThis, confirmAddToThis = false, thisName = "" }: Props) {
  const { t } = useTranslation();
  const [done, setDone] = useState<Record<string, AddWordResult>>({});
  const [failed, setFailed] = useState<Record<string, string>>({});
  const [pending, setPending] = useState<Pending | null>(null);
  if (collisions.length === 0) return null;
  const keyOf = (side: string, c: CodeCollision, word: string) => `${side}:${c.product_id}:${word}`;
  async function run({ side, collision, word }: Pending) {
    const key = keyOf(side, collision, word);
    setFailed(previous => ({ ...previous, [key]: "" }));
    try {
      const result = side === "other" ? await onAddToOther!(Number(collision.product_id), word) : await onAddToThis!(word);
      setDone(previous => ({ ...previous, [key]: result }));
    } catch (err) {
      const message = err instanceof ApiError && err.status === 409 ? "productDetail.conflict" : "codeCollision.addError";
      setFailed(previous => ({ ...previous, [key]: message }));
    }
  }
  function request(next: Pending) {
    if (next.side === "this" && !confirmAddToThis) void run(next);
    else setPending(next);
  }
  const wordRow = (side: "this" | "other", c: CodeCollision, word: string, enabled: boolean) => {
    const key = keyOf(side, c, word);
    const result = done[key];
    return <span key={key} className="code-collision__word">
      <strong>{word}</strong>{" "}
      {result ? <span role="status">{t(`codeCollision.result.${result}`)}</span>
        : enabled && <Button type="button" size="sm" variant="secondary" onClick={() => request({ side, collision: c, word })}>
          {t(side === "other" ? "codeCollision.addToOtherButton" : "codeCollision.addToThisButton")}</Button>}
      {failed[key] && <span role="status"> {t(failed[key])}</span>}{" "}
    </span>;
  };
  return <><Callout variant="warning" title={t("codeCollision.title")}>
    <p>{t("codeCollision.hint")}</p>
    <ul>
      {collisions.map(item => <li key={`${item.product_id}-${item.matched_field}`}>
        <strong>{itemName(item, t)}</strong>
        <div>{t("codeCollision.matched", { field: t(`codeCollision.fields.${fieldKey(item.matched_field)}`), value: item.matched_value })}</div>
        {item.suggest_add_to_this.length > 0 && <div>{t("codeCollision.addToThis", { words: "" })}
          {item.suggest_add_to_this.map(word => wordRow("this", item, word, onAddToThis !== undefined))}</div>}
        {item.suggest_add_to_other.length > 0 && <div>{t("codeCollision.addToOther", { words: "" })}
          {item.suggest_add_to_other.map(word => wordRow("other", item, word, onAddToOther !== undefined))}</div>}
        {item.suggest_add_to_this.length === 0 && item.suggest_add_to_other.length === 0 &&
          <div>{t("codeCollision.registered")}</div>}
      </li>)}
    </ul>
  </Callout>
  <ConfirmModal open={pending !== null} title={t("codeCollision.confirmTitle")}
    message={pending ? t("codeCollision.confirmMessage", {
      product: pending.side === "other" ? itemName(pending.collision, t) : thisName, word: pending.word }) : ""}
    confirmLabel={t("codeCollision.confirmAction")}
    onConfirm={() => { const next = pending; setPending(null); if (next) void run(next); }}
    onCancel={() => setPending(null)} /></>;
}
