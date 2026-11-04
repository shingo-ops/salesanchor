/** ⑦ 請求先フォーム（本契約のお客さんが、メール・部屋のリンクから請求先を書いて送る。ログイン不要） */
import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { EmptyState } from "../../components/EmptyState";
import { LoadingBlock } from "../../components/loading";
import { Radio } from "../../components/Radio";
import { TextField } from "../../components/TextField";
import { ViewerApiError, openBillingForm, submitBillingForm } from "./api";
import type { ViewerBillingFormValues } from "./types";

interface BillingFormViewProps {
  /** リンクの #billing= に入っていた鍵 */
  token: string;
}

type Step = "opening" | "form" | "done" | "invalid";

const EMPTY: ViewerBillingFormValues = {
  party_type: null,
  bill_to_name: "",
  contact_name: "",
  postal_code: "",
  address: "",
  phone: "",
  invoice_email: "",
};

export function BillingFormView({ token }: BillingFormViewProps) {
  const { t } = useTranslation();
  const [step, setStep] = useState<Step>("opening");
  const [values, setValues] = useState<ViewerBillingFormValues>(EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 開いたら今の値を入れる。無効の鍵（期限切れ・使用済み・本契約でない）はどれも同じ案内
  useEffect(() => {
    let alive = true;
    openBillingForm(token).then(
      (res) => {
        if (!alive) return;
        setValues(res);
        setStep("form");
      },
      (err: unknown) => {
        if (!alive) return;
        if (err instanceof ViewerApiError && err.status === 429) {
          setError(t("viewer.error.viewer_too_many_attempts"));
          setStep("form");
          return;
        }
        setStep("invalid");
      },
    );
    return () => {
      alive = false;
    };
  }, [token, t]);

  const set = (key: keyof ViewerBillingFormValues, value: string) =>
    setValues((prev) => ({ ...prev, [key]: value }));

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (values.party_type === null) {
      setError(t("viewer.billing.partyRequired"));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await submitBillingForm(token, { ...values, party_type: values.party_type });
      setStep("done");
    } catch (err) {
      if (err instanceof ViewerApiError && err.status === 400) {
        setStep("invalid");
      } else if (err instanceof ViewerApiError && err.status === 422) {
        setError(t("viewer.billing.invalidInput"));
      } else if (err instanceof ViewerApiError && err.status === 429) {
        setError(t("viewer.error.viewer_too_many_attempts"));
      } else {
        setError(t("viewer.error.generic"));
      }
    } finally {
      setBusy(false);
    }
  };

  if (step === "opening") {
    return (
      <div className="viewer-center" aria-live="polite" data-testid="viewer-billing-opening">
        <LoadingBlock />
      </div>
    );
  }

  if (step === "invalid") {
    return (
      <div className="viewer-center" data-testid="viewer-billing-invalid">
        <EmptyState title={t("viewer.billing.invalidTitle")} description={t("viewer.billing.invalidDescription")} />
      </div>
    );
  }

  if (step === "done") {
    return (
      <div className="viewer-center" data-testid="viewer-billing-done">
        <EmptyState title={t("viewer.billing.doneTitle")} description={t("viewer.billing.doneDescription")} />
      </div>
    );
  }

  return (
    <form className="viewer-login" onSubmit={submit} data-testid="viewer-billing-form">
      <h1 className="viewer-login__title">{t("viewer.billing.title")}</h1>
      <Radio
        name="billing-party-type"
        label={t("viewer.billing.company")}
        checked={values.party_type === "company"}
        onChange={() => setValues((prev) => ({ ...prev, party_type: "company" }))}
        data-testid="viewer-billing-company"
      />
      <Radio
        name="billing-party-type"
        label={t("viewer.billing.individual")}
        checked={values.party_type === "individual"}
        onChange={() => setValues((prev) => ({ ...prev, party_type: "individual" }))}
        data-testid="viewer-billing-individual"
      />
      <TextField
        label={t("viewer.billing.billToName")}
        value={values.bill_to_name}
        onChange={(e) => set("bill_to_name", e.target.value)}
        maxLength={100}
        required
        fullWidth
      />
      {values.party_type === "company" && (
        <TextField
          label={t("viewer.billing.contactName")}
          value={values.contact_name}
          onChange={(e) => set("contact_name", e.target.value)}
          maxLength={50}
          required
          fullWidth
          data-testid="viewer-billing-contact"
        />
      )}
      <TextField
        label={t("viewer.billing.postalCode")}
        helperText={t("viewer.billing.postalCodeHelp")}
        inputMode="numeric"
        autoComplete="postal-code"
        value={values.postal_code}
        onChange={(e) => set("postal_code", e.target.value)}
        required
        fullWidth
      />
      <TextField
        label={t("viewer.billing.address")}
        autoComplete="street-address"
        value={values.address}
        onChange={(e) => set("address", e.target.value)}
        maxLength={200}
        required
        fullWidth
      />
      <TextField
        label={t("viewer.billing.phone")}
        helperText={t("viewer.billing.phoneHelp")}
        type="tel"
        autoComplete="tel"
        value={values.phone}
        onChange={(e) => set("phone", e.target.value)}
        required
        fullWidth
      />
      <TextField
        label={t("viewer.billing.invoiceEmail")}
        helperText={t("viewer.billing.invoiceEmailHelp")}
        type="email"
        value={values.invoice_email}
        onChange={(e) => set("invoice_email", e.target.value)}
        maxLength={254}
        fullWidth
      />
      {error && (
        <p className="viewer-login__error" role="alert" data-testid="viewer-billing-error">
          {error}
        </p>
      )}
      <Button type="submit" fullWidth loading={busy} disabled={busy}>
        {t("viewer.billing.submit")}
      </Button>
    </form>
  );
}
