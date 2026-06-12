/**
 * API連携 > 配送キャリア（FedEx / DHL / UPS）接続テストページ（共通コンポーネント）
 *
 * 各テナントが自社の配送キャリア API 認証情報を入力・保存し、接続(認証)テストを行う。
 * - FedEx: APIキー / シークレットキー（FedEx 公式名称）+ Account Number
 * - UPS:   Client ID / Client Secret + Account Number
 * - DHL:   API Key / API Secret（MyDHL API Basic 認証）
 * 認証情報はテナント別に暗号化保存（シークレットは画面に表示しない）。
 * Account Number は FedEx Rates / Ship API に必須（ADR-125）。
 * ADR-129: FedEx のみ 本番/Sandbox を切り替えて個別に認証情報を登録可能。
 *          Label Validation 申請支援タブを追加（FedEx のみ）。
 *
 * 変更履歴:
 *   2026-06-08: 初版（接続テストページ）
 *   2026-06-09: ADR-125 — FedEx/UPS に Account Number フィールド追加
 *   2026-06-10: ADR-125 UX — 登録済み可視化・environment 固定・ポカヨケ改善
 *   2026-06-12: ADR-129 — FedEx 環境セレクタ追加 + Label Validation タブ追加
 */

import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { PageLayout } from "../../components/PageLayout";
import { Tabs } from "../../components/Tabs";
import { FedexLabelValidationTab } from "./FedexLabelValidationTab";

type Carrier = "fedex" | "dhl" | "ups";
type PageTab = "credentials" | "labelValidation";

const NAV_KEY: Record<Carrier, `nav.${string}`> = {
  fedex: "nav.integrationFedex",
  dhl: "nav.integrationDhl",
  ups: "nav.integrationUps",
};

// 認証情報の表示ラベル（FedEx=APIキー/シークレットキー、UPS=Client ID/Secret、DHL=API Key/Secret）
const CRED_LABEL: Record<Carrier, { id: string; secret: string }> = {
  fedex: { id: "carrierIntegration.labelFedExApiKey", secret: "carrierIntegration.labelFedExSecretKey" },
  ups: { id: "carrierIntegration.labelClientId", secret: "carrierIntegration.labelClientSecret" },
  dhl: { id: "carrierIntegration.labelApiKey", secret: "carrierIntegration.labelApiSecret" },
};

interface CarrierStatus {
  carrier: string;
  configured: boolean;
  environment: string;
  client_id_hint: string | null;
  secret_configured: boolean;
  account_number_hint: string | null;
}

interface TestResult {
  ok: boolean;
  status_code: number | null;
  message: string;
}

// FedEx / UPS はアカウント番号が必要（ADR-125 D2）
const SHOWS_ACCOUNT_NUMBER: ReadonlySet<Carrier> = new Set(["fedex", "ups"]);

// ADR-129: FedEx のみ環境切り替えをサポート
const SUPPORTS_ENV_SELECT: ReadonlySet<Carrier> = new Set(["fedex"]);

export default function CarrierIntegrationPage({ carrier }: { carrier: Carrier }) {
  const { t } = useTranslation();

  // ADR-129: FedEx は credential ページタブ + Label Validation タブ
  const [pageTab, setPageTab] = useState<PageTab>("credentials");
  // ADR-129: FedEx のみ本番/Sandbox 切り替え
  const [env, setEnv] = useState<"production" | "sandbox">("production");

  const [status, setStatus] = useState<CarrierStatus | null>(null);
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [accountNumber, setAccountNumber] = useState("");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [result, setResult] = useState<TestResult | null>(null);
  const [error, setError] = useState("");

  const loadStatus = useCallback(() => {
    const query = SUPPORTS_ENV_SELECT.has(carrier) ? `?environment=${env}` : "";
    api
      .get<CarrierStatus>(`/integrations/carriers/${carrier}/status${query}`)
      .then((s) => setStatus(s))
      .catch(() => setStatus(null));
  }, [carrier, env]);

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
        // ADR-129: FedEx は選択中の environment を送る。他キャリアは production 固定。
        environment: SUPPORTS_ENV_SELECT.has(carrier) ? env : "production",
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
      const query = SUPPORTS_ENV_SELECT.has(carrier) ? `?environment=${env}` : "";
      const res = await api.post<TestResult>(
        `/integrations/carriers/${carrier}/test-connection${query}`,
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
      const query = SUPPORTS_ENV_SELECT.has(carrier) ? `?environment=${env}` : "";
      await api.delete(`/integrations/carriers/${carrier}/credentials${query}`);
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

  const pageTabs = carrier === "fedex" ? [
    { key: "credentials" as PageTab, label: t("carrierIntegration.tabCredentials") },
    { key: "labelValidation" as PageTab, label: t("carrierIntegration.tabLabelValidation") },
  ] : null;

  const envTabs = SUPPORTS_ENV_SELECT.has(carrier) ? [
    { key: "production" as const, label: t("carrierIntegration.tabProduction") },
    { key: "sandbox" as const, label: t("carrierIntegration.tabSandbox") },
  ] : null;

  return (
    <PageLayout navKey={NAV_KEY[carrier]} subtitleKey="carrierIntegration.subtitle">
      {/* FedEx: ページタブ（API連携設定 / Label Validation） */}
      {pageTabs && (
        <Tabs
          items={pageTabs}
          activeKey={pageTab}
          onChange={setPageTab}
          variant="pill"
          size="md"
          className="carrier-page-tabs"
        />
      )}

      {/* Label Validation タブ（FedEx のみ） */}
      {pageTab === "labelValidation" && carrier === "fedex" && (
        <FedexLabelValidationTab />
      )}

      {/* 認証情報タブ（全キャリア共通） */}
      {pageTab === "credentials" && (
        <>
          {/* ADR-129: FedEx のみ環境セレクタ */}
          {envTabs && (
            <Tabs
              items={envTabs}
              activeKey={env}
              onChange={(k) => { setEnv(k); setResult(null); setSaved(false); }}
              variant="underline"
              size="sm"
              className="carrier-env-tabs"
            />
          )}

          {/* 認証情報の登録 */}
          <section className="card">
            <h3>{t("carrierIntegration.credTitle")}</h3>
            <p className="form-hint">{t("carrierIntegration.hint")}</p>

            {/* 登録済み情報の表示（ADR-125 UX） */}
            {status?.configured && (
              <div className="registered-info">
                <h4>{t("carrierIntegration.registeredInfoTitle")}</h4>
                <div className="form-group">
                  <label>{t(labels.id)}</label>
                  <p className="registered-value">{status.client_id_hint}</p>
                </div>
                <div className="form-group">
                  <label>{t(labels.secret)}</label>
                  <p className="registered-value muted">{t("carrierIntegration.secretRegistered")}</p>
                </div>
                {SHOWS_ACCOUNT_NUMBER.has(carrier) && (
                  <div className="form-group">
                    <label>{t("carrierIntegration.labelAccountNumber")}</label>
                    {status.account_number_hint ? (
                      <p className="registered-value">{status.account_number_hint}</p>
                    ) : (
                      <p className="registered-value warning">{t("carrierIntegration.accountNumberNotSet")}</p>
                    )}
                  </div>
                )}
                <div className="form-group">
                  <label>{t("carrierIntegration.envLabel")}</label>
                  <p className="registered-value muted">
                    {SUPPORTS_ENV_SELECT.has(carrier)
                      ? t(env === "production" ? "carrierIntegration.envProduction" : "carrierIntegration.envSandbox")
                      : t("carrierIntegration.productionFixed")}
                  </p>
                </div>
              </div>
            )}

            {/* 未登録時のメッセージ */}
            {!status?.configured && (
              <p>{t("carrierIntegration.notConfigured")}</p>
            )}

            {/* 更新フォーム */}
            <div className="update-form">
              {status?.configured && (
                <p className="form-hint">{t("carrierIntegration.updateSectionTitle")}</p>
              )}
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
              {/* environment 表示（FedEx=選択中の環境、それ以外=本番固定） */}
              <div className="form-group">
                <label>{t("carrierIntegration.envLabel")}</label>
                <p className="form-value-fixed">
                  {SUPPORTS_ENV_SELECT.has(carrier)
                    ? t(env === "production" ? "carrierIntegration.envProduction" : "carrierIntegration.envSandbox")
                    : t("carrierIntegration.productionFixed")}
                </p>
              </div>
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
                {t("common.colon")}{result.message}
                {result.status_code ? ` (HTTP ${result.status_code})` : ""}
              </p>
            )}
          </section>
        </>
      )}

      {error && <p className="error-message">{error}</p>}
    </PageLayout>
  );
}
