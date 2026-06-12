/**
 * API連携 > 配送キャリア（FedEx / DHL / UPS）接続ページ（共通コンポーネント）
 *
 * PR-A: 設定UIを「見る（カード）」と「編集する（フォーム）」に分離
 *       - 状態カードがデフォルト表示。フォームは編集アクション時のみ展開
 *       - FedEx: 本番/Sandbox の2カードを並置（環境セレクタ廃止）
 *       - APIキーはマスク済みの hint をそのまま表示（フル値はフロントへ送らない）
 *       - 保存 → 自動接続テスト → バッジ更新
 *       - 削除は ConfirmModal 必須
 *       - タブ名: "Label Validation申請支援" → "連携ガイド"
 *
 * 変更履歴:
 *   2026-06-08: 初版（接続テストページ）
 *   2026-06-09: ADR-125 — FedEx/UPS に Account Number フィールド追加
 *   2026-06-10: ADR-125 UX — 登録済み可視化・environment 固定・ポカヨケ改善
 *   2026-06-12: ADR-129 — FedEx 環境セレクタ追加 + Label Validation タブ追加
 *   2026-06-12: PR-A  — view/edit 分離・タブ改名「連携ガイド」
 */

import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { PageLayout } from "../../components/PageLayout";
import { Tabs } from "../../components/Tabs";
import { Badge } from "../../components/Badge";
import ConfirmModal from "../../components/ConfirmModal";
import { FedexLabelValidationTab } from "./FedexLabelValidationTab";

type Carrier = "fedex" | "dhl" | "ups";
type PageTab = "credentials" | "integrationGuide";
type Env = "production" | "sandbox";

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

interface EnvData {
  status: CarrierStatus | null;
  testResult: TestResult | null;
  lastTested: Date | null;
}

// FedEx / UPS はアカウント番号が必要（ADR-125 D2）
const SHOWS_ACCOUNT_NUMBER: ReadonlySet<Carrier> = new Set(["fedex", "ups"]);

// ADR-129: FedEx のみ環境切り替えをサポート
const SUPPORTS_ENV_SELECT: ReadonlySet<Carrier> = new Set(["fedex"]);

const EMPTY_ENV_DATA: EnvData = { status: null, testResult: null, lastTested: null };

export default function CarrierIntegrationPage({ carrier }: { carrier: Carrier }) {
  const { t } = useTranslation();

  const [pageTab, setPageTab] = useState<PageTab>("credentials");
  const [prodData, setProdData] = useState<EnvData>(EMPTY_ENV_DATA);
  const [sandboxData, setSandboxData] = useState<EnvData>(EMPTY_ENV_DATA);
  // editingEnv: 編集フォームを展開中の環境（null = ビューモード）
  const [editingEnv, setEditingEnv] = useState<Env | null>(null);
  const [formClientId, setFormClientId] = useState("");
  const [formClientSecret, setFormClientSecret] = useState("");
  const [formAccountNumber, setFormAccountNumber] = useState("");
  const [deleteConfirmEnv, setDeleteConfirmEnv] = useState<Env | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const loadStatus = useCallback(async () => {
    if (SUPPORTS_ENV_SELECT.has(carrier)) {
      // FedEx: 本番/Sandbox を並行ロード
      const [prod, sandbox] = await Promise.allSettled([
        api.get<CarrierStatus>(`/integrations/carriers/${carrier}/status?environment=production`),
        api.get<CarrierStatus>(`/integrations/carriers/${carrier}/status?environment=sandbox`),
      ]);
      setProdData((d) => ({ ...d, status: prod.status === "fulfilled" ? prod.value : null }));
      setSandboxData((d) => ({ ...d, status: sandbox.status === "fulfilled" ? sandbox.value : null }));
    } else {
      // 他キャリア: production のみ（environment クエリなし）
      const s = await api.get<CarrierStatus>(`/integrations/carriers/${carrier}/status`).catch(() => null);
      setProdData((d) => ({ ...d, status: s }));
    }
  }, [carrier]);

  useEffect(() => {
    setProdData(EMPTY_ENV_DATA);
    setSandboxData(EMPTY_ENV_DATA);
    setEditingEnv(null);
    loadStatus();
  }, [loadStatus]);

  const openEdit = (env: Env) => {
    setFormClientId("");
    setFormClientSecret("");
    setFormAccountNumber("");
    setError("");
    setEditingEnv(env);
  };

  const handleSaveAndTest = async () => {
    if (!editingEnv) return;
    setBusy(true);
    setError("");
    try {
      await api.put(`/integrations/carriers/${carrier}/credentials`, {
        client_id: formClientId,
        client_secret: formClientSecret,
        environment: SUPPORTS_ENV_SELECT.has(carrier) ? editingEnv : "production",
        ...(SHOWS_ACCOUNT_NUMBER.has(carrier) && formAccountNumber
          ? { account_number: formAccountNumber }
          : {}),
      });
      // 保存成功: ステータス取得 + 接続テストを並行実行
      const query = SUPPORTS_ENV_SELECT.has(carrier) ? `?environment=${editingEnv}` : "";
      const [statusResult, testResult] = await Promise.allSettled([
        api.get<CarrierStatus>(`/integrations/carriers/${carrier}/status${query}`),
        api.post<TestResult>(`/integrations/carriers/${carrier}/test-connection${query}`, {}),
      ]);
      const newStatus = statusResult.status === "fulfilled" ? statusResult.value : null;
      const testRes: TestResult =
        testResult.status === "fulfilled"
          ? testResult.value
          : {
              ok: false,
              status_code: null,
              message:
                testResult.reason instanceof Error
                  ? testResult.reason.message
                  : t("common.operationError"),
            };
      const setEnvData = editingEnv === "production" ? setProdData : setSandboxData;
      setEnvData({ status: newStatus, testResult: testRes, lastTested: new Date() });
      setEditingEnv(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.operationError"));
    } finally {
      setBusy(false);
    }
  };

  const handleTest = async (env: Env) => {
    setBusy(true);
    setError("");
    try {
      const query = SUPPORTS_ENV_SELECT.has(carrier) ? `?environment=${env}` : "";
      const res = await api.post<TestResult>(
        `/integrations/carriers/${carrier}/test-connection${query}`,
        {},
      );
      const setEnvData = env === "production" ? setProdData : setSandboxData;
      setEnvData((d) => ({ ...d, testResult: res, lastTested: new Date() }));
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.operationError"));
    } finally {
      setBusy(false);
    }
  };

  const handleDeleteConfirmed = async () => {
    if (!deleteConfirmEnv) return;
    setBusy(true);
    setError("");
    try {
      const query = SUPPORTS_ENV_SELECT.has(carrier) ? `?environment=${deleteConfirmEnv}` : "";
      await api.delete(`/integrations/carriers/${carrier}/credentials${query}`);
      const setEnvData = deleteConfirmEnv === "production" ? setProdData : setSandboxData;
      setEnvData(EMPTY_ENV_DATA);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.operationError"));
    } finally {
      setBusy(false);
      setDeleteConfirmEnv(null);
    }
  };

  const labels = CRED_LABEL[carrier];
  const isFedex = SUPPORTS_ENV_SELECT.has(carrier);

  const pageTabs = isFedex
    ? [
        { key: "credentials" as PageTab, label: t("carrierIntegration.tabCredentials") },
        { key: "integrationGuide" as PageTab, label: t("carrierIntegration.tabIntegrationGuide") },
      ]
    : null;

  const renderStatusBadge = (data: EnvData) => {
    if (!data.status?.configured) return null;
    if (!data.testResult) {
      return (
        <Badge variant="neutral" size="sm" dot>
          {t("carrierIntegration.statusUnverified")}
        </Badge>
      );
    }
    return data.testResult.ok ? (
      <Badge variant="success" size="sm" dot>
        {t("carrierIntegration.statusOk")}
      </Badge>
    ) : (
      <Badge variant="danger" size="sm" dot>
        {t("carrierIntegration.statusError")}
      </Badge>
    );
  };

  const renderCard = (env: Env, data: EnvData) => {
    const configured = data.status?.configured ?? false;
    const isEditing = editingEnv === env;
    const cardTitle =
      env === "production"
        ? t("carrierIntegration.envCardTitleProd")
        : t("carrierIntegration.envCardTitleSandbox");

    // ── 編集フォーム ──
    if (isEditing) {
      return (
        <section key={`${env}-edit`} className="card carrier-env-card carrier-env-card--editing">
          <div className="carrier-env-card__header">
            <h3 className="carrier-env-card__title">
              {t("carrierIntegration.editFormTitle", { env: cardTitle })}
            </h3>
          </div>
          <p className="carrier-env-card__hint">{t("carrierIntegration.editFormHint")}</p>
          <div className="update-form">
            <div className="form-group">
              <label htmlFor={`cred-id-${env}`}>{t(labels.id)}</label>
              <input
                id={`cred-id-${env}`}
                type="text"
                value={formClientId}
                autoComplete="off"
                placeholder={t("carrierIntegration.apiKeyPlaceholder")}
                onChange={(e) => setFormClientId(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label htmlFor={`cred-secret-${env}`}>{t(labels.secret)}</label>
              <input
                id={`cred-secret-${env}`}
                type="password"
                value={formClientSecret}
                autoComplete="new-password"
                placeholder={t("carrierIntegration.secretPlaceholder")}
                onChange={(e) => setFormClientSecret(e.target.value)}
              />
            </div>
            {SHOWS_ACCOUNT_NUMBER.has(carrier) && (
              <div className="form-group">
                <label htmlFor={`cred-account-${env}`}>
                  {t("carrierIntegration.labelAccountNumber")}
                </label>
                <input
                  id={`cred-account-${env}`}
                  type="text"
                  value={formAccountNumber}
                  autoComplete="off"
                  placeholder={t("carrierIntegration.accountNumberEditPlaceholder")}
                  onChange={(e) => setFormAccountNumber(e.target.value)}
                />
                <p className="carrier-env-card__hint">
                  {t("carrierIntegration.accountNumberHint")}
                </p>
              </div>
            )}
          </div>
          {error && <p className="error-message">{error}</p>}
          <div className="form-actions">
            <button
              className="btn-secondary"
              disabled={busy}
              onClick={() => {
                setEditingEnv(null);
                setError("");
              }}
            >
              {t("common.cancel")}
            </button>
            <button
              className="btn-primary"
              disabled={busy || !formClientId || !formClientSecret}
              onClick={handleSaveAndTest}
            >
              {busy ? t("carrierIntegration.saving") : t("carrierIntegration.saveAndTest")}
            </button>
          </div>
        </section>
      );
    }

    // ── 未登録カード ──
    if (!configured) {
      return (
        <section key={`${env}-empty`} className="card carrier-env-card carrier-env-card--empty">
          <div className="carrier-env-card__header">
            <h3 className="carrier-env-card__title">{cardTitle}</h3>
          </div>
          {env === "sandbox" && (
            <p className="carrier-env-card__hint">
              {t("carrierIntegration.sandboxEmptyHint")}
            </p>
          )}
          <div className="form-actions">
            <button className="btn-secondary" disabled={busy} onClick={() => openEdit(env)}>
              {env === "sandbox"
                ? t("carrierIntegration.registerSandboxKey")
                : t("carrierIntegration.registerProdKey")}
            </button>
          </div>
        </section>
      );
    }

    // ── 登録済みビューカード ──
    return (
      <section key={`${env}-view`} className="card carrier-env-card">
        <div className="carrier-env-card__header">
          <h3 className="carrier-env-card__title">{cardTitle}</h3>
          {renderStatusBadge(data)}
          {data.lastTested && (
            <span className="carrier-env-card__last-tested">
              {t("carrierIntegration.lastTested", {
                time: data.lastTested.toLocaleTimeString(),
              })}
            </span>
          )}
        </div>
        {data.testResult && !data.testResult.ok && (
          <p className="error-message carrier-env-card__test-error">
            {data.testResult.message}
            {data.testResult.status_code ? ` (HTTP ${data.testResult.status_code})` : ""}
          </p>
        )}
        <div className="carrier-env-card__body">
          <div className="carrier-env-info-row">
            <span className="carrier-env-info-label">{t(labels.id)}</span>
            <span className="carrier-env-info-value carrier-env-info-value--masked">
              {data.status?.client_id_hint ?? "—"}
            </span>
          </div>
          {SHOWS_ACCOUNT_NUMBER.has(carrier) && (
            <div className="carrier-env-info-row">
              <span className="carrier-env-info-label">
                {t("carrierIntegration.labelAccountNumber")}
              </span>
              <span
                className={`carrier-env-info-value ${!data.status?.account_number_hint ? "carrier-env-info-value--warn" : ""}`}
              >
                {data.status?.account_number_hint ??
                  t("carrierIntegration.accountNumberNotSet")}
              </span>
            </div>
          )}
          <div className="carrier-env-info-row">
            <span className="carrier-env-info-label">{t(labels.secret)}</span>
            <span className="carrier-env-info-value carrier-env-info-value--muted">
              {t("carrierIntegration.secretRegistered")}
            </span>
          </div>
        </div>
        <div className="form-actions">
          <button
            className="btn-secondary"
            disabled={busy}
            onClick={() => handleTest(env)}
          >
            {busy ? t("carrierIntegration.testing") : t("carrierIntegration.testButton")}
          </button>
          <button className="btn-secondary" disabled={busy} onClick={() => openEdit(env)}>
            {t("common.edit")}
          </button>
          <button
            className="btn-ghost carrier-env-card__delete-btn"
            disabled={busy}
            onClick={() => setDeleteConfirmEnv(env)}
          >
            {t("carrierIntegration.disconnect")}
          </button>
        </div>
      </section>
    );
  };

  return (
    <PageLayout navKey={NAV_KEY[carrier]} subtitleKey="carrierIntegration.subtitle">
      {/* FedEx: ページタブ（API連携設定 / 連携ガイド） */}
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

      {/* 連携ガイドタブ（FedEx のみ・中身は Part B で作り替え） */}
      {pageTab === "integrationGuide" && isFedex && <FedexLabelValidationTab />}

      {/* API連携設定タブ（全キャリア共通） */}
      {pageTab === "credentials" && (
        <>
          {renderCard("production", prodData)}
          {isFedex && renderCard("sandbox", sandboxData)}
        </>
      )}

      {/* 削除確認モーダル */}
      <ConfirmModal
        open={deleteConfirmEnv !== null}
        title={t("carrierIntegration.deleteConfirmTitle")}
        message={
          deleteConfirmEnv === "production"
            ? t("carrierIntegration.deleteConfirmMessageProd")
            : t("carrierIntegration.deleteConfirmMessageSandbox")
        }
        confirmLabel={t("carrierIntegration.deleteConfirmButton")}
        danger
        onConfirm={handleDeleteConfirmed}
        onCancel={() => setDeleteConfirmEnv(null)}
      />

      {/* フォーム外グローバルエラー（接続テスト失敗等） */}
      {error && !editingEnv && <p className="error-message">{error}</p>}
    </PageLayout>
  );
}
