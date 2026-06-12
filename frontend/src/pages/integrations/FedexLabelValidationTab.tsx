/**
 * FedEx Label Validation 申請支援タブ（ADR-129）
 *
 * FedEx 国際配送（IP / IE / IPE / FICP）の Label Validation 申請を
 * 9ステップでガイドする。
 *
 * - Step 1: Sandbox 認証情報の確認
 * - Step 2: テストラベル発行（4サービス、Sandbox）
 * - Step 3: 印刷（手動）
 * - Step 4: テスト情報手書き記入（手動）
 * - Step 5: スキャン（手動）
 * - Step 6: カバーシートダウンロード
 * - Step 7: メール文面コピー
 * - Step 8: メール送信
 * - Step 9: 申請完了
 *
 * 変更履歴:
 *   2026-06-12: 初版（ADR-129）
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";

interface LVSampleLabel {
  service_abbr: string;
  service_name: string;
  service_type: string;
  tracking_number: string;
  pdf_base64: string;
}

interface EmailTemplate {
  subject: string;
  body: string;
}

function StepHeader({ num, title, done }: { num: number; title: string; done?: boolean }) {
  return (
    <div className="lv-step-header">
      <span className={`lv-step-num ${done ? "lv-step-num--done" : ""}`}>{num}</span>
      <strong>{title}</strong>
      {/* done indicator is CSS-only (::after pseudo-element) to avoid hardcoded non-i18n characters */}
      {done && <span className="lv-step-badge-done" aria-label="done" />}
    </div>
  );
}

export function FedexLabelValidationTab() {
  const { t } = useTranslation();

  // Step 2: labels
  const [labelBusy, setLabelBusy] = useState(false);
  const [labels, setLabels] = useState<LVSampleLabel[] | null>(null);
  const [labelError, setLabelError] = useState("");

  // Step 3-5: manual checklist
  const [step3Done, setStep3Done] = useState(false);
  const [step4Done, setStep4Done] = useState(false);
  const [step5Done, setStep5Done] = useState(false);

  // Step 6: cover sheet
  const [coverBusy, setCoverBusy] = useState(false);
  const [coverError, setCoverError] = useState("");

  // Step 7: email template
  const [emailBusy, setEmailBusy] = useState(false);
  const [emailTemplate, setEmailTemplate] = useState<EmailTemplate | null>(null);
  const [emailError, setEmailError] = useState("");
  const [emailCopied, setEmailCopied] = useState(false);

  const handleIssueLabels = async () => {
    setLabelBusy(true);
    setLabelError("");
    setLabels(null);
    try {
      const res = await api.post<{ labels: LVSampleLabel[] }>(
        "/shipping/label-validation/samples",
        {},
      );
      setLabels(res.labels);
    } catch (e) {
      setLabelError(e instanceof Error ? e.message : t("common.operationError"));
    } finally {
      setLabelBusy(false);
    }
  };

  const handleDownloadLabel = (label: LVSampleLabel) => {
    const bytes = Uint8Array.from(atob(label.pdf_base64), (c) => c.charCodeAt(0));
    const blob = new Blob([bytes], { type: "application/pdf" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `fedex_lv_${label.service_abbr}_${label.tracking_number}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadCoverSheet = async () => {
    setCoverBusy(true);
    setCoverError("");
    try {
      const blob = await api.getBlob("/shipping/label-validation/cover-sheet");
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "fedex_label_validation_cover.pdf";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setCoverError(e instanceof Error ? e.message : t("common.operationError"));
    } finally {
      setCoverBusy(false);
    }
  };

  const handleGetEmailTemplate = async () => {
    setEmailBusy(true);
    setEmailError("");
    setEmailTemplate(null);
    try {
      const res = await api.get<EmailTemplate>("/shipping/label-validation/email-template");
      setEmailTemplate(res);
    } catch (e) {
      setEmailError(e instanceof Error ? e.message : t("common.operationError"));
    } finally {
      setEmailBusy(false);
    }
  };

  const handleCopyEmailBody = async () => {
    if (!emailTemplate) return;
    await navigator.clipboard.writeText(emailTemplate.body);
    setEmailCopied(true);
    setTimeout(() => setEmailCopied(false), 2000);
  };

  const mailtoHref = emailTemplate
    ? `mailto:?subject=${encodeURIComponent(emailTemplate.subject)}&body=${encodeURIComponent(emailTemplate.body)}`
    : "mailto:";

  return (
    <div className="lv-wizard">
      <h3>{t("carrierIntegration.lvTitle")}</h3>
      <p className="form-hint">{t("carrierIntegration.lvDescription")}</p>

      {/* ── Step 1: Sandbox 認証情報確認 ── */}
      <section className="lv-step card">
        <StepHeader num={1} title={t("carrierIntegration.lvStep1Title")} />
        <p className="form-hint">{t("carrierIntegration.lvStep1Desc")}</p>
      </section>

      {/* ── Step 2: テストラベル発行 ── */}
      <section className="lv-step card">
        <StepHeader num={2} title={t("carrierIntegration.lvStep2Title")} done={!!labels} />
        <p className="form-hint">{t("carrierIntegration.lvStep2Desc")}</p>
        <div className="form-actions">
          <button
            className="btn-primary"
            disabled={labelBusy}
            onClick={handleIssueLabels}
          >
            {labelBusy ? t("carrierIntegration.lvStep2Issuing") : t("carrierIntegration.lvStep2Button")}
          </button>
        </div>
        {labelError && <p className="error-message">{labelError}</p>}
        {labels && (
          <div className="lv-label-list">
            <p className="success-message">{t("carrierIntegration.lvStep2Success")}</p>
            {labels.map((label) => (
              <div key={label.service_abbr} className="lv-label-item">
                <span className="lv-service-badge">{label.service_abbr}</span>
                <span className="lv-service-name">{label.service_name}</span>
                <span className="lv-tracking-number">{label.tracking_number}</span>
                <button
                  className="btn-secondary btn-sm"
                  onClick={() => handleDownloadLabel(label)}
                >
                  {t("carrierIntegration.lvStep2Download")}
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ── Step 3: 印刷（手動） ── */}
      <section className={`lv-step card ${step3Done ? "lv-step--done" : ""}`}>
        <StepHeader num={3} title={t("carrierIntegration.lvStep3Title")} done={step3Done} />
        <p className="form-hint">{t("carrierIntegration.lvStep3Desc")}</p>
        <label className="lv-check-label">
          <input
            type="checkbox"
            checked={step3Done}
            onChange={(e) => setStep3Done(e.target.checked)}
          />
          {t("carrierIntegration.lvCheckDone")}
        </label>
      </section>

      {/* ── Step 4: 手書き記入（手動） ── */}
      <section className={`lv-step card ${step4Done ? "lv-step--done" : ""}`}>
        <StepHeader num={4} title={t("carrierIntegration.lvStep4Title")} done={step4Done} />
        <p className="form-hint">{t("carrierIntegration.lvStep4Desc")}</p>
        <label className="lv-check-label">
          <input
            type="checkbox"
            checked={step4Done}
            onChange={(e) => setStep4Done(e.target.checked)}
          />
          {t("carrierIntegration.lvCheckDone")}
        </label>
      </section>

      {/* ── Step 5: スキャン（手動） ── */}
      <section className={`lv-step card ${step5Done ? "lv-step--done" : ""}`}>
        <StepHeader num={5} title={t("carrierIntegration.lvStep5Title")} done={step5Done} />
        <p className="form-hint">{t("carrierIntegration.lvStep5Desc")}</p>
        <label className="lv-check-label">
          <input
            type="checkbox"
            checked={step5Done}
            onChange={(e) => setStep5Done(e.target.checked)}
          />
          {t("carrierIntegration.lvCheckDone")}
        </label>
      </section>

      {/* ── Step 6: カバーシートダウンロード ── */}
      <section className="lv-step card">
        <StepHeader num={6} title={t("carrierIntegration.lvStep6Title")} />
        <p className="form-hint">{t("carrierIntegration.lvStep6Desc")}</p>
        <div className="form-actions">
          <button
            className="btn-secondary"
            disabled={coverBusy}
            onClick={handleDownloadCoverSheet}
          >
            {coverBusy ? t("carrierIntegration.lvStep6Downloading") : t("carrierIntegration.lvStep6Button")}
          </button>
        </div>
        {coverError && <p className="error-message">{coverError}</p>}
      </section>

      {/* ── Step 7: メール文面 ── */}
      <section className="lv-step card">
        <StepHeader num={7} title={t("carrierIntegration.lvStep7Title")} done={!!emailTemplate} />
        <p className="form-hint">{t("carrierIntegration.lvStep7Desc")}</p>
        <div className="form-actions">
          <button
            className="btn-secondary"
            disabled={emailBusy}
            onClick={handleGetEmailTemplate}
          >
            {emailBusy ? t("carrierIntegration.lvStep7Loading") : t("carrierIntegration.lvStep7Button")}
          </button>
        </div>
        {emailError && <p className="error-message">{emailError}</p>}
        {emailTemplate && (
          <div className="lv-email-template">
            <div className="lv-email-field">
              <span className="lv-email-label">{t("carrierIntegration.lvStep7Subject")}:</span>
              <span className="lv-email-value">{emailTemplate.subject}</span>
            </div>
            <div className="lv-email-field lv-email-body-field">
              <span className="lv-email-label">{t("carrierIntegration.lvStep7Body")}:</span>
              <pre className="lv-email-body">{emailTemplate.body}</pre>
            </div>
            <div className="form-actions">
              <button className="btn-secondary" onClick={handleCopyEmailBody}>
                {emailCopied
                  ? t("carrierIntegration.lvStep7Copied")
                  : t("carrierIntegration.lvStep7CopyButton")}
              </button>
            </div>
          </div>
        )}
      </section>

      {/* ── Step 8: メール送信 ── */}
      <section className="lv-step card">
        <StepHeader num={8} title={t("carrierIntegration.lvStep8Title")} />
        <p className="form-hint">{t("carrierIntegration.lvStep8Desc")}</p>
        <div className="form-actions">
          <a
            href={mailtoHref}
            className="btn-primary"
          >
            {t("carrierIntegration.lvStep8MailtoButton")}
          </a>
        </div>
      </section>

      {/* ── Step 9: 完了 ── */}
      <section className="lv-step card lv-step--complete">
        <StepHeader num={9} title={t("carrierIntegration.lvStep9Title")} />
        <p className="form-hint">{t("carrierIntegration.lvStep9Desc")}</p>
      </section>
    </div>
  );
}
