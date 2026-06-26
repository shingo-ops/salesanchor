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
 *   2026-06-26: 鍵入力フォームを CarrierCredentialForm として切り出し（挙動不変）
 */

import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { PageLayout } from "../../components/PageLayout";
import { Badge } from "../../components/Badge";
import ConfirmModal from "../../components/ConfirmModal";
import CarrierCredentialForm, {
  type Carrier,
  type Env,
  CRED_LABEL,
  SHOWS_ACCOUNT_NUMBER,
  SUPPORTS_ENV_SELECT,
} from "./CarrierCredentialForm";
import "./CarrierIntegrationPage.css";

const NAV_KEY: Record<Carrier, `nav.${string}`> = {
  fedex: "nav.integrationFedex",
  dhl: "nav.integrationDhl",
  ups: "nav.integrationUps",
};

interface CarrierStatus {
  carrier: string;
  configured: boolean;
  environment: string;
  client_id_hint: string | null;
  secret_configured: boolean;
  account_number_hint: string | null;
  // A4: 接続テスト結果（永続化）
  last_tested_at: string | null;
  last_test_ok: boolean | null;
  last_test_message: string | null;
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

const EMPTY_ENV_DATA: EnvData = { status: null, testResult: null, lastTested: null };

export default function CarrierIntegrationPage({ carrier }: { carrier: Carrier }) {
  const { t } = useTranslation();

  const [prodData, setProdData] = useState<EnvData>(EMPTY_ENV_DATA);
  const [sandboxData, setSandboxData] = useState<EnvData>(EMPTY_ENV_DATA);
  // editingEnv: 編集フォームを展開中の環境（null = ビューモード）
  const [editingEnv, setEditingEnv] = useState<Env | null>(null);
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
    setError("");
    setEditingEnv(env);
  };

  const handleTest = async (env: Env) => {
    setBusy(true);
    setError("");
    try {
      const query = SUPPORTS_ENV_SELECT.has(carrier) ? `?environment=${env}` : "";
      await api.post<TestResult>(
        `/integrations/carriers/${carrier}/test-connection${query}`,
        {},
      );
      // A4: テスト結果はDBに保存済み → ステータス再取得で永続化された結果を表示
      await loadStatus();
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

  const renderStatusBadge = (data: EnvData) => {
    if (!data.status?.configured) return null;
    // A4: バッジはDBに永続化されたテスト結果を参照
    if (data.status.last_test_ok === null) {
      return (
        <Badge variant="neutral" size="sm" dot>
          {t("carrierIntegration.statusUnverified")}
        </Badge>
      );
    }
    return data.status.last_test_ok ? (
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
        <CarrierCredentialForm
          key={env}
          carrier={carrier}
          env={env}
          envLabel={cardTitle}
          onSaved={loadStatus}
          onCancel={() => {
            setEditingEnv(null);
            setError("");
          }}
        />
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
          {data.status?.last_tested_at && (
            <span className="carrier-env-card__last-tested">
              {t("carrierIntegration.lastTested", {
                time: new Intl.DateTimeFormat("ja-JP", {
                  year: "numeric",
                  month: "numeric",
                  day: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                  hour12: false,
                }).format(new Date(data.status.last_tested_at)),
              })}
            </span>
          )}
        </div>
        {data.status?.last_test_ok === false && data.status.last_test_message && (
          <p className="error-message carrier-env-card__test-error">
            {data.status.last_test_message}
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
    <PageLayout
      navKey={NAV_KEY[carrier]}
      subtitleKey="carrierIntegration.subtitle"
      headerAction={
        isFedex ? (
          <a
            href={`/management-center/integrations/${carrier}/setup-guide`}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-secondary"
          >
            {t("carrierIntegration.openSetupGuide")}
          </a>
        ) : undefined
      }
    >
      {/* API連携設定（全キャリア共通） */}
      {renderCard("production", prodData)}
      {isFedex && renderCard("sandbox", sandboxData)}

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
