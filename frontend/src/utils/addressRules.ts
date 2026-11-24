/** 送り先の住所1行の決まり（customer-address-form design §2）。受け口の validate_delivery_address_line（backend/app/schemas/base.py）と同じ。 */
export const DELIVERY_ADDRESS_LINE_MAX = 35;
const PRINTABLE_ASCII = /^[\x20-\x7E]*$/;

export type AddressRuleError = "addressRule.ascii" | "addressRule.maxLength";

/** 決まりに合わなければ翻訳キーを返す。合えば null。空欄は null。 */
export function deliveryAddressLineError(value: string | null | undefined): AddressRuleError | null {
  if (!value) return null;
  if (!PRINTABLE_ASCII.test(value)) return "addressRule.ascii";
  if (value.length > DELIVERY_ADDRESS_LINE_MAX) return "addressRule.maxLength";
  return null;
}
