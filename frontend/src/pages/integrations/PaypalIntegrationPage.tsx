/**
 * API連携 > PayPal 決済連携 接続テストページ（Model A：テナント別認証情報）
 *
 * 各テナントが自社の PayPal アプリの認証情報（Client ID / Secret）を入力・保存し、
 * 接続(認証)テストを行う。決済作成(Orders API)等の実機能は別途(Phase B)。
 * 認証情報はテナント別に暗号化保存（シークレットは画面に表示しない）。
 * 将来 Model B（Connect with PayPal）へ拡張可能な構造。
 *
 * 変更履歴:
 *   2026-06-10: 初版（接続テストページ・Model A）
 */

import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { PageLayout } from "../../components/PageLayout";

interface PaypalStatus {
  configured: boolean;
  environment: string;
}

interface TestResult {
  ok: boolean;
  status_code: number | null;
  message: string;
}

interface PaymentTestResult {
  invoice_id: number;
  invoice_number: string;
  amount: number;
  currency: string;
  approval_url: string;
}

export default function PaypalIntegrationPage() {
  const { t } = useTranslation();
  const [status, setStatus] = useState<PaypalStatus | null>(null);
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [environment, setEnvironment] = useState("sandbox");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [result, setResult] = useState<TestResult | null>(null);
  const [payTest, setPayTest] = useState<PaymentTestResult | null>(null);
  const [error, setError] = useState("");

  const loadStatus = useCallback(() => {
    api
      .get<PaypalStatus>("/integrations/paypal/status")
      .then((s) => {
        setStatus(s);
        setEnvironment(s.environment || "sandbox");
      })
      .catch(() => setStatus(null));
  }, []);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  const handleSave = async () => {
    setBusy(true);
    setError("");
    setSaved(false);
    setResult(null);
    try {
      await api.put("/integrations/paypal/credentials", {
        client_id: clientId,
        client_secret: clientSecret,
        environment,
      });
      setSaved(true);
      setClientId("");
      setClientSecret("");
      loadStatus();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.operationError"));
    } finally {
      setBusy(false);
    }
  };

  const handleTest = async () => {
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const res = await api.post<TestResult>("/integrations/paypal/test-connection", {});
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.operationError"));
    } finally {
      setBusy(false);
    }
  };

  const handlePaymentTest = async () => {
    setBusy(true);
    setError("");
    setPayTest(null);
    try {
      const res = await api.post<PaymentTestResult>("/integrations/paypal/test-invoice", {});
      setPayTest(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.operationError"));
    } finally {
      setBusy(false);
    }
  };

  const handleDisconnect = async () => {
    setBusy(true);
    setError("");
    try {
      await api.delete("/integrations/paypal/credentials");
      setResult(null);
      setSaved(false);
      loadStatus();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.operationError"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <PageLayout navKey="nav.integrationPaypal" subtitleKey="paypalIntegration.subtitle">
      {/* 認証情報の登録 */}
      <section className="card">
        <h3>{t("paypalIntegration.credTitle")}</h3>
        <p className="form-hint">{t("paypalIntegration.hint")}</p>
        <p>
          {status?.configured
            ? t("paypalIntegration.configured")
            : t("paypalIntegration.notConfigured")}
        </p>
        <div className="form-group">
          <label htmlFor="paypal-id">{t("paypalIntegration.labelClientId")}</label>
          <input
            id="paypal-id"
            type="text"
            value={clientId}
            autoComplete="off"
            onChange={(e) => setClientId(e.target.value)}
          />
        </div>
        <div className="form-group">
          <label htmlFor="paypal-secret">{t("paypalIntegration.labelClientSecret")}</label>
          <input
            id="paypal-secret"
            type="password"
            value={clientSecret}
            autoComplete="new-password"
            placeholder={t("paypalIntegration.secretPlaceholder")}
            onChange={(e) => setClientSecret(e.target.value)}
          />
        </div>
        <div className="form-group">
          <label htmlFor="paypal-env">{t("paypalIntegration.envLabel")}</label>
          <select
            id="paypal-env"
            value={environment}
            onChange={(e) => setEnvironment(e.target.value)}
          >
            <option value="sandbox">{t("paypalIntegration.envSandbox")}</option>
            <option value="live">{t("paypalIntegration.envLive")}</option>
          </select>
        </div>
        <div className="form-actions">
          {status?.configured && (
            <button className="btn-secondary" disabled={busy} onClick={handleDisconnect}>
              {t("paypalIntegration.disconnect")}
            </button>
          )}
          <button
            className="btn-primary"
            disabled={busy || !clientId || !clientSecret}
            onClick={handleSave}
          >
            {busy ? t("paypalIntegration.saving") : t("paypalIntegration.save")}
          </button>
        </div>
        {saved && <p className="success-message">{t("paypalIntegration.saved")}</p>}
      </section>

      {/* 接続テスト */}
      <section className="card">
        <h3>{t("paypalIntegration.testTitle")}</h3>
        <div className="form-actions">
          <button
            className="btn-primary"
            disabled={busy || !status?.configured}
            onClick={handleTest}
          >
            {busy ? t("paypalIntegration.testing") : t("paypalIntegration.testButton")}
          </button>
        </div>
        {!status?.configured && (
          <p className="form-hint">{t("paypalIntegration.testNeedsSave")}</p>
        )}
        {result && (
          <p className={result.ok ? "success-message" : "error-message"}>
            {result.ok
              ? t("paypalIntegration.successMsg")
              : t("paypalIntegration.failMsg")}
            ：{result.message}
            {result.status_code ? `（HTTP ${result.status_code}）` : ""}
          </p>
        )}
      </section>

      {/* 決済テスト（sandbox 限定） */}
      {status?.configured && status?.environment === "sandbox" && (
        <section className="card">
          <h3>{t("paypalIntegration.payTestTitle")}</h3>
          <p className="form-hint">{t("paypalIntegration.payTestHint")}</p>
          <div className="form-actions">
            <button className="btn-primary" disabled={busy} onClick={handlePaymentTest}>
              {busy ? t("paypalIntegration.payTestRunning") : t("paypalIntegration.payTestButton")}
            </button>
          </div>
          {payTest && (
            <div style={{ marginTop: "var(--space-3)", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)", padding: "var(--space-3)" }}>
              <p style={{ fontWeight: "var(--font-weight-semi)", marginBottom: "var(--space-1)" }}>
                {t("paypalIntegration.payTestCreated")}（{payTest.invoice_number} / {payTest.amount} {payTest.currency}）
              </p>
              <p className="form-hint">{t("paypalIntegration.payTestSteps")}</p>
              <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap", marginTop: "var(--space-2)" }}>
                <a className="btn-primary" href={payTest.approval_url} target="_blank" rel="noopener noreferrer">
                  {t("paypalIntegration.payTestPay")}
                </a>
                <a className="btn-secondary" href={`/invoices/${payTest.invoice_id}`} target="_blank" rel="noopener noreferrer">
                  {t("paypalIntegration.payTestOpenInvoice")}
                </a>
              </div>
            </div>
          )}
        </section>
      )}

      {error && <p className="error-message">{error}</p>}
    </PageLayout>
  );
}
