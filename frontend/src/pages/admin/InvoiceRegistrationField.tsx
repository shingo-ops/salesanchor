/**
 * インボイス登録の有無と番号の欄（ADR-1061 便2-2c2b。design.md §3-4a。Toggle と TextField の金型）。
 * 番号の決まり（T と13桁）の正本は backend の issuer_rules.py と表の CHECK。
 */
import { useTranslation } from "react-i18next";
import { Stack } from "../../components/Stack";
import { TextField } from "../../components/TextField";
import { Toggle } from "../../components/Toggle";

interface InvoiceRegistrationFieldProps {
  idPrefix: string;
  registered: boolean;
  number: string;
  disabled: boolean;
  error?: string;
  onRegisteredChange: (next: boolean) => void;
  onNumberChange: (next: string) => void;
}

export function InvoiceRegistrationField({
  idPrefix,
  registered,
  number,
  disabled,
  error,
  onRegisteredChange,
  onNumberChange,
}: InvoiceRegistrationFieldProps) {
  const { t } = useTranslation();
  const toggleId = `${idPrefix}-invoice-registered`;
  return (
    <Stack gap="2">
      <div className="form-group">
        <label htmlFor={toggleId}>{t("issuerProfile.invoiceRegistered")}</label>
        <Toggle
          id={toggleId}
          checked={registered}
          onCheckedChange={onRegisteredChange}
          disabled={disabled}
        />
      </div>
      {registered && (
        <TextField
          id={`${idPrefix}-registration-number`}
          data-testid={`${idPrefix}-registration-number`}
          label={t("issuerProfile.registrationNumber")}
          helperText={t("issuerProfile.registrationHint")}
          error={error}
          value={number}
          onChange={(e) => onNumberChange(e.target.value)}
          disabled={disabled}
          maxLength={14}
          required
          fullWidth
        />
      )}
    </Stack>
  );
}
