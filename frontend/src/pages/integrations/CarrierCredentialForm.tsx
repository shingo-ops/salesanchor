/**
 * CarrierCredentialForm — キャリア認証情報の入力・保存・接続テストフォーム
 *
 * CarrierIntegrationPage から切り出した独立コンポーネント。
 * 既存ページとガイド（FedexEtdSetupGuide 等）の両方から再利用可能。
 *
 * tenant_id はバックエンド（get_current_tenant）で自動セット。
 * このコンポーネントから tenant_id を送信しない（IDOR 対策）。
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import "./CarrierIntegrationPage.css";

export type Carrier = "fedex" | "dhl" | "ups";
export type Env = "production" | "sandbox";

/** フィールドラベルの i18n キー（キャリアごとの差異を吸収） */
export const CRED_LABEL: Record<Carrier, { id: string; secret: string }> = {
  fedex: { id: "carrierIntegration.labelFedExApiKey", secret: "carrierIntegration.labelFedExSecretKey" },
  ups: { id: "carrierIntegration.labelClientId", secret: "carrierIntegration.labelClientSecret" },
  dhl: { id: "carrierIntegration.labelApiKey", secret: "carrierIntegration.labelApiSecret" },
};

/** アカウント番号フィールドを表示するキャリア（ADR-125 D2） */
export const SHOWS_ACCOUNT_NUMBER: ReadonlySet<Carrier> = new Set(["fedex", "ups"]);

/** 本番/Sandbox 環境切り替えをサポートするキャリア（ADR-129） */
export const SUPPORTS_ENV_SELECT: ReadonlySet<Carrier> = new Set(["fedex"]);

interface CarrierCredentialFormProps {
  carrier: Carrier;
  env: Env;
  /** 翻訳済みの環境ラベル（例: "本番環境"）。親が t() して渡す */
  envLabel: string;
  /** 保存+接続テスト成功後に呼ぶ（親の loadStatus に相当）。完了後フォームを閉じる */
  onSaved: () => Promise<void>;
  onCancel: () => void;
}

export default function CarrierCredentialForm({
  carrier,
  env,
  envLabel,
  onSaved,
  onCancel,
}: CarrierCredentialFormProps) {
  const { t } = useTranslation();
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [accountNumber, setAccountNumber] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const labels = CRED_LABEL[carrier];

  const handleSaveAndTest = async () => {
    setBusy(true);
    setError("");
    try {
      await api.put(`/integrations/carriers/${carrier}/credentials`, {
        client_id: clientId,
        client_secret: clientSecret,
        environment: SUPPORTS_ENV_SELECT.has(carrier) ? env : "production",
        ...(SHOWS_ACCOUNT_NUMBER.has(carrier) && accountNumber
          ? { account_number: accountNumber }
          : {}),
      });
      // 保存成功: 接続テスト実行 → 親のステータス再取得（A4: 順次実行で結果をDBに保存）
      const query = SUPPORTS_ENV_SELECT.has(carrier) ? `?environment=${env}` : "";
      await api.post(`/integrations/carriers/${carrier}/test-connection${query}`, {}).catch(() => null);
      await onSaved();
      onCancel();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.operationError"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card carrier-env-card carrier-env-card--editing">
      <div className="carrier-env-card__header">
        <h3 className="carrier-env-card__title">
          {t("carrierIntegration.editFormTitle", { env: envLabel })}
        </h3>
      </div>
      <p className="carrier-env-card__hint">{t("carrierIntegration.editFormHint")}</p>
      <div className="update-form">
        <div className="form-group">
          <label htmlFor={`cred-id-${env}`}>{t(labels.id)}</label>
          {/* ui-allow: CarrierIntegrationPage から移動した既存 input のリファクタ（挙動不変） (#2601) */}
          <input
            id={`cred-id-${env}`}
            type="text"
            value={clientId}
            autoComplete="off"
            placeholder={t("carrierIntegration.apiKeyPlaceholder")}
            onChange={(e) => setClientId(e.target.value)}
          />
        </div>
        <div className="form-group">
          <label htmlFor={`cred-secret-${env}`}>{t(labels.secret)}</label>
          <input
            id={`cred-secret-${env}`}
            type="password"
            value={clientSecret}
            autoComplete="new-password"
            placeholder={t("carrierIntegration.secretPlaceholder")}
            onChange={(e) => setClientSecret(e.target.value)}
          />
        </div>
        {SHOWS_ACCOUNT_NUMBER.has(carrier) && (
          <div className="form-group">
            <label htmlFor={`cred-account-${env}`}>
              {t("carrierIntegration.labelAccountNumber")}
            </label>
            {/* ui-allow: CarrierIntegrationPage から移動した既存 input のリファクタ（挙動不変） (#2601) */}
            <input
              id={`cred-account-${env}`}
              type="text"
              value={accountNumber}
              autoComplete="off"
              placeholder={t("carrierIntegration.accountNumberEditPlaceholder")}
              onChange={(e) => setAccountNumber(e.target.value)}
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
          onClick={onCancel}
        >
          {t("common.cancel")}
        </button>
        <button
          className="btn-primary"
          disabled={busy || !clientId || !clientSecret}
          onClick={handleSaveAndTest}
        >
          {busy ? t("carrierIntegration.saving") : t("carrierIntegration.saveAndTest")}
        </button>
      </div>
    </section>
  );
}
