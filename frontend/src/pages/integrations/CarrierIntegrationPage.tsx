/**
 * API連携 > 配送キャリア（FedEx / DHL / UPS）接続テストページ（共通コンポーネント）
 *
 * 各テナントが自社の配送キャリア API 認証情報を入力・保存し、接続(認証)テストを行う。
 * - FedEx/UPS: Client ID / Client Secret（OAuth2）+ Account Number（ADR-125 D2 追加）
 * - DHL: API Key / API Secret（MyDHL API Basic 認証）
 * 認証情報はテナント別に暗号化保存（シークレットは画面に表示しない）。
 * Account Number は FedEx Rates / Ship API に必須（ADR-125）。
 *
 * 変更履歴:
 *   2026-06-08: 初版（接続テストページ）
 *   2026-06-09: ADR-125 — FedEx/UPS に Account Number フィールド追加
 */

import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { PageLayout } from "../../components/PageLayout";

type Carrier = "fedex" | "dhl" | "ups";

const NAV_KEY: Record<Carrier, `nav.${string}`> = {
  fedex: "nav.integrationFedex",
  dhl: "nav.integrationDhl",
  ups: "nav.integrationUps",
};

// 認証情報の表示ラベル（FedEx/UPS=Client ID/Secret、DHL=API Key/Secret）
const CRED_LABEL: Record<Carrier, { id: string; secret: string }> = {
  fedex: { id: "carrierIntegration.labelClientId", secret: "carrierIntegration.labelClientSecret" },
  ups: { id: "carrierIntegration.labelClientId", secret: "carrierIntegration.labelClientSecret" },
  dhl: { id: "carrierIntegration.labelApiKey", secret: "carrierIntegration.labelApiSecret" },
};

interface CarrierStatus {
  carrier: string;
  configured: boolean;
  environment: string;
}

interface TestResult {
  ok: boolean;
  status_code: number | null;
  message: string;
}

// FedEx / UPS はアカウント番号が必要（ADR-125 D2）
const SHOWS_ACCOUNT_NUMBER: ReadonlySet<Carrier> = new Set(["fedex", "ups"]);

export default function CarrierIntegrationPage({ carrier }: { carrier: Carrier }) {
  const { t } = useTranslation();
  const [status, setStatus] = useState<CarrierStatus | null>(null);
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [accountNumber, setAccountNumber] = useState("");
  const [environment, setEnvironment] = useState("sandbox");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [result, setResult] = useState<TestResult | null>(null);
  const [error, setError] = useState("");

  const loadStatus = useCallback(() => {
    api
      .get<CarrierStatus>(`/integrations/carriers/${carrier}/status`)
      .then((s) => {
        setStatus(s);
        setEnvironment(s.environment || "sandbox");
      })
      .catch(() => setStatus(null));
  }, [carrier]);

  useEffect(() => {
    setResult(null);
    setSaved(false);
    setClientId("");
    setClientSecret("");
    setAccountNumber("");
    loadStatus();
  }, [loadStatus]);

  const handleSave = async () => {
    setBusy(true);
    setError("");
    setSaved(false);
    setResult(null);
    try {
      await api.put(`/integrations/carriers/${carrier}/credentials`, {
        client_id: clientId,
        client_secret: clientSecret,
        environment,
        ...(SHOWS_ACCOUNT_NUMBER.has(carrier) && accountNumber
          ? { account_number: accountNumber }
          : {}),
      });
      setSaved(true);
      setClientId("");
      setClientSecret("");
      setAccountNumber("");
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
      const res = await api.post<TestResult>(
        `/integrations/carriers/${carrier}/test-connection`,
        {},
      );
      setResult(res);
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
      await api.delete(`/integrations/carriers/${carrier}/credentials`);
      setResult(null);
      setSaved(false);
      loadStatus();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.operationError"));
    } finally {
      setBusy(false);
    }
  };

  const labels = CRED_LABEL[carrier];

  return (
    <PageLayout navKey={NAV_KEY[carrier]} subtitleKey="carrierIntegration.subtitle">
      {/* 認証情報の登録 */}
      <section className="card">
        <h3>{t("carrierIntegration.credTitle")}</h3>
        <p className="form-hint">{t("carrierIntegration.hint")}</p>
        <p>
          {status?.configured
            ? t("carrierIntegration.configured")
            : t("carrierIntegration.notConfigured")}
        </p>
        <div className="form-group">
          <label htmlFor="cred-id">{t(labels.id)}</label>
          <input
            id="cred-id"
            type="text"
            value={clientId}
            autoComplete="off"
            onChange={(e) => setClientId(e.target.value)}
          />
        </div>
        <div className="form-group">
          <label htmlFor="cred-secret">{t(labels.secret)}</label>
          <input
            id="cred-secret"
            type="password"
            value={clientSecret}
            autoComplete="new-password"
            placeholder={t("carrierIntegration.secretPlaceholder")}
            onChange={(e) => setClientSecret(e.target.value)}
          />
        </div>
        {/* ADR-125 D2: FedEx / UPS のみアカウント番号フィールドを表示 */}
        {SHOWS_ACCOUNT_NUMBER.has(carrier) && (
          <div className="form-group">
            <label htmlFor="cred-account">{t("carrierIntegration.labelAccountNumber")}</label>
            <input
              id="cred-account"
              type="text"
              value={accountNumber}
              autoComplete="off"
              placeholder={t("carrierIntegration.accountNumberPlaceholder")}
              onChange={(e) => setAccountNumber(e.target.value)}
            />
            <p className="form-hint">{t("carrierIntegration.accountNumberHint")}</p>
          </div>
        )}
        <div className="form-group">
          <label htmlFor="cred-env">{t("carrierIntegration.envLabel")}</label>
          <select
            id="cred-env"
            value={environment}
            onChange={(e) => setEnvironment(e.target.value)}
          >
            <option value="sandbox">{t("carrierIntegration.envSandbox")}</option>
            <option value="production">{t("carrierIntegration.envProduction")}</option>
          </select>
        </div>
        <div className="form-actions">
          {status?.configured && (
            <button className="btn-secondary" disabled={busy} onClick={handleDisconnect}>
              {t("carrierIntegration.disconnect")}
            </button>
          )}
          <button
            className="btn-primary"
            disabled={busy || !clientId || !clientSecret}
            onClick={handleSave}
          >
            {busy ? t("carrierIntegration.saving") : t("carrierIntegration.save")}
          </button>
        </div>
        {saved && <p className="success-message">{t("carrierIntegration.saved")}</p>}
      </section>

      {/* 接続テスト */}
      <section className="card">
        <h3>{t("carrierIntegration.testTitle")}</h3>
        <div className="form-actions">
          <button
            className="btn-primary"
            disabled={busy || !status?.configured}
            onClick={handleTest}
          >
            {busy ? t("carrierIntegration.testing") : t("carrierIntegration.testButton")}
          </button>
        </div>
        {!status?.configured && (
          <p className="form-hint">{t("carrierIntegration.testNeedsSave")}</p>
        )}
        {result && (
          <p className={result.ok ? "success-message" : "error-message"}>
            {result.ok
              ? t("carrierIntegration.successMsg")
              : t("carrierIntegration.failMsg")}
            ：{result.message}
            {result.status_code ? `（HTTP ${result.status_code}）` : ""}
          </p>
        )}
      </section>

      {error && <p className="error-message">{error}</p>}
    </PageLayout>
  );
}
