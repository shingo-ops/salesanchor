/**
 * 閲覧者の詳細（ViewerAccountsPage の Drawer）にある「請求先」の区切り。
 * ページの行数上限（check-page-size.js）を守るため、ページから切り出した部品。
 * お客さんが書いた請求先を読み、「請求先フォームを送る」操作を持つ。
 * 開く人が変わったときは、呼び出し側の key で作り直す（送った結果・エラーが消える）。
 */
import type React from "react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api, ApiError } from "../../../lib/api";
import { Button } from "../../../components/Button";
import { EmptyState } from "../../../components/EmptyState";
import { Stack } from "../../../components/Stack";
import { LoadingBlock } from "../../../components/loading";
import { useApiQuery } from "../../../lib/query/apiQuery";

/** お客さんが書いた請求先（GET /super-admin/viewers/{id}/billing-profile。無ければ null）。 */
interface BillingProfile {
  party_type: "company" | "individual";
  bill_to_name: string;
  contact_name: string | null;
  postal_code: string;
  address: string;
  phone: string;
  invoice_email: string | null;
  updated_at: string;
}

/** 「請求先フォームを送る」の結果（POST /super-admin/viewers/{id}/send-billing-form）。 */
interface BillingFormSendResult {
  room_notice: "sent" | "failed" | "no_room";
  room_notice_text: string;
  mail_queued: boolean;
  expires_at: string;
}

interface ViewerBillingSectionProps {
  viewerId: number;
  active: boolean;
  running: boolean;
  setRunning: (v: boolean) => void;
  renderCopyButton: (key: string, value: string) => React.ReactNode;
  formatDate: (value: string | null) => string | null;
}

export function ViewerBillingSection({
  viewerId,
  active,
  running,
  setRunning,
  renderCopyButton,
  formatDate,
}: ViewerBillingSectionProps) {
  const { t } = useTranslation();
  const f = "superAdmin.viewers";

  const [billingSendResult, setBillingSendResult] = useState<BillingFormSendResult | null>(null);
  const [billingSendError, setBillingSendError] = useState("");

  // 開いた人の請求先を読む（行が無ければ null。お客さんが送信したときに変わるので、管理者が送っても取り直さない）
  const billingQuery = useApiQuery<BillingProfile | null>(
    `/super-admin/viewers/${viewerId}/billing-profile`,
    { enabled: true },
  );
  // 行が無いときの null と、想定外の形の応答は「まだ無い」として扱う
  const billing = typeof billingQuery.data?.bill_to_name === "string" ? billingQuery.data : null;
  const billingLoading = billingQuery.isPending;
  const billingLoadError = billingQuery.isError;

  const sendBillingForm = async () => {
    if (!active) return;
    setRunning(true);
    setBillingSendResult(null);
    setBillingSendError("");
    try {
      const res = await api.post<BillingFormSendResult>(
        `/super-admin/viewers/${viewerId}/send-billing-form`,
        {},
      );
      setBillingSendResult(res);
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) setBillingSendError(t(`${f}.billingConflictError`));
      else if (e instanceof ApiError && e.status === 503) setBillingSendError(t(`${f}.templateNotFound`));
      else if (e instanceof ApiError && e.status === 404) setBillingSendError(t(`${f}.notFoundError`));
      else setBillingSendError(t(`${f}.genericError`));
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="form-row" data-testid="viewers-detail-billing">
      <label>{t(`${f}.billingTitle`)}</label>
      {billingLoading ? (
        <LoadingBlock />
      ) : billingLoadError ? (
        <div className="error-message" role="alert" data-testid="viewers-detail-billing-error">
          {t(`${f}.billingLoadError`)}
        </div>
      ) : billing ? (
        <Stack direction="column" gap="2">
          <div data-testid="viewers-detail-billing-party">
            {t(`${f}.billingPartyType`)}: {t(`${f}.${billing.party_type === "company" ? "billingCompany" : "billingIndividual"}`)}
          </div>
          <div data-testid="viewers-detail-billing-name">
            {t(`${f}.billingName`)}: {billing.bill_to_name}
          </div>
          {billing.contact_name && (
            <div data-testid="viewers-detail-billing-contact">
              {t(`${f}.billingContact`)}: {billing.contact_name}
            </div>
          )}
          <div data-testid="viewers-detail-billing-postal">
            {t(`${f}.billingPostal`)}: {billing.postal_code.slice(0, 3)}-{billing.postal_code.slice(3)}
          </div>
          <div data-testid="viewers-detail-billing-address">
            {t(`${f}.billingAddress`)}: {billing.address}
          </div>
          <div data-testid="viewers-detail-billing-phone">
            {t(`${f}.billingPhone`)}: {billing.phone}
          </div>
          <div data-testid="viewers-detail-billing-email">
            {t(`${f}.billingEmail`)}: {billing.invoice_email ?? t(`${f}.empty`)}
          </div>
        </Stack>
      ) : (
        <EmptyState title={t(`${f}.billingEmpty`)} size="compact" />
      )}
      {active && (
        <Stack direction="column" gap="2">
          <div>
            <Button
              variant="secondary"
              size="sm"
              disabled={running}
              onClick={() => { void sendBillingForm(); }}
              data-testid="viewers-detail-billing-send"
            >
              {t(`${f}.billingSend`)}
            </Button>
          </div>
          {billingSendError && (
            <div className="error-message" role="alert" data-testid="viewers-detail-billing-send-error">
              {billingSendError}
            </div>
          )}
          {billingSendResult && (
            <div data-testid="viewers-detail-billing-send-result">
              <p data-testid="viewers-detail-billing-room">
                {t(`${f}.billingRoom_${billingSendResult.room_notice}`)}
              </p>
              {billingSendResult.mail_queued && <p>{t(`${f}.billingMailQueued`)}</p>}
              <p>
                {t(`${f}.billingExpires`)}: {formatDate(billingSendResult.expires_at)}
              </p>
              {billingSendResult.room_notice !== "sent" && (
                <>
                  <p data-testid="viewers-detail-billing-text">{billingSendResult.room_notice_text}</p>
                  {renderCopyButton("billingForm", billingSendResult.room_notice_text)}
                </>
              )}
            </div>
          )}
        </Stack>
      )}
    </div>
  );
}
