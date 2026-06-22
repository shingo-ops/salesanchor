import { useEffect, useRef, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { Badge } from "../../components/Badge";
import "./FedexLabelValidationTab.css";

type Env = "sandbox" | "production";
type StepKey = "portal" | "apis" | "credentials" | "etd" | "done";

interface CarrierStatus {
  configured: boolean;
  last_test_ok: boolean | null;
  last_test_message: string | null;
  last_tested_at: string | null;
  client_id_hint: string | null;
  account_number_hint: string | null;
}

interface StepDefinition {
  key: StepKey;
  title: string;
}

const ETD_ENABLED = import.meta.env.VITE_FEDEX_ETD_ENABLED === "true";

const PORTAL_URL = "https://developer.fedex.com/api/ja-jp/home.html";

function StepCard({
  stepNumber,
  title,
  children,
  isActive,
}: {
  stepNumber: number;
  title: string;
  children: ReactNode;
  isActive: boolean;
}) {
  return (
    <section className={`etd-guide__step card ${isActive ? "etd-guide__step--active" : ""}`}>
      <div className="etd-guide__step-header">
        <span className="etd-guide__step-number">{stepNumber}</span>
        <strong>{title}</strong>
      </div>
      {children}
    </section>
  );
}

export function FedexEtdSetupGuide({
  onOpenCredentialsTab,
}: {
  onOpenCredentialsTab: () => void;
}) {
  const { t } = useTranslation();
  const [activeStepIndex, setActiveStepIndex] = useState(0);
  const [productionStatus, setProductionStatus] = useState<CarrierStatus | null>(null);
  const [sandboxStatus, setSandboxStatus] = useState<CarrierStatus | null>(null);
  const [statusError, setStatusError] = useState("");
  const [statusLoading, setStatusLoading] = useState(true);
  const [etdEnvironment, setEtdEnvironment] = useState<Env>("sandbox");
  const [registeredImages, setRegisteredImages] = useState<Record<Env, Record<string, boolean>>>({
    sandbox: {},
    production: {},
  });
  const [uploadBusy, setUploadBusy] = useState({ letterhead: false, signature: false });
  const [uploadSuccess, setUploadSuccess] = useState({ letterhead: false, signature: false });
  const [uploadError, setUploadError] = useState({ letterhead: "", signature: "" });
  const letterheadInputRef = useRef<HTMLInputElement>(null);
  const signatureInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let cancelled = false;

    const loadStatuses = async () => {
      setStatusLoading(true);
      setStatusError("");
      try {
        const [prod, sandbox] = await Promise.allSettled([
          api.get<CarrierStatus>("/integrations/carriers/fedex/status?environment=production"),
          api.get<CarrierStatus>("/integrations/carriers/fedex/status?environment=sandbox"),
        ]);
        if (cancelled) return;
        setProductionStatus(prod.status === "fulfilled" ? prod.value : null);
        setSandboxStatus(sandbox.status === "fulfilled" ? sandbox.value : null);
        if (prod.status === "rejected" || sandbox.status === "rejected") {
          setStatusError(t("common.fetchError"));
        }
      } catch (e) {
        if (!cancelled) setStatusError(e instanceof Error ? e.message : t("common.operationError"));
      } finally {
        if (!cancelled) setStatusLoading(false);
      }
    };

    void loadStatuses();

    return () => {
      cancelled = true;
    };
  }, [t]);

  useEffect(() => {
    let cancelled = false;

    const loadRegisteredImages = async () => {
      try {
        const res = await api.get<{ images: Array<{ image_type: string; fedex_image_index: string }> }>(
          `/shipping/etd/images?environment=${etdEnvironment}`,
        );
        if (cancelled) return;
        const next: Record<string, boolean> = {};
        for (const image of res.images) {
          next[image.image_type] = true;
        }
        setRegisteredImages((prev) => ({
          ...prev,
          [etdEnvironment]: next,
        }));
        setUploadSuccess({
          letterhead: !!next.LETTERHEAD,
          signature: !!next.SIGNATURE,
        });
      } catch {
        if (!cancelled) {
          setRegisteredImages((prev) => ({
            ...prev,
            [etdEnvironment]: {},
          }));
          setUploadSuccess({ letterhead: false, signature: false });
        }
      }
    };

    void loadRegisteredImages();

    return () => {
      cancelled = true;
    };
  }, [etdEnvironment]);

  const isConnected = Boolean(
    (productionStatus?.configured && productionStatus.last_test_ok === true)
      || (sandboxStatus?.configured && sandboxStatus.last_test_ok === true),
  );

  const stepDefinitions: StepDefinition[] = [
    { key: "portal", title: t("carrierIntegration.fedexEtdGuideStep1Title") },
    { key: "apis", title: t("carrierIntegration.fedexEtdGuideStep2Title") },
    { key: "credentials", title: t("carrierIntegration.fedexEtdGuideStep3Title") },
    ...(ETD_ENABLED
      ? [{ key: "etd" as const, title: t("carrierIntegration.fedexEtdGuideStep4Title") }]
      : []),
    { key: "done", title: t("carrierIntegration.fedexEtdGuideStep5Title") },
  ];

  const currentStep = stepDefinitions[activeStepIndex] ?? stepDefinitions[0];
  const currentIndex = activeStepIndex + 1;
  const totalSteps = stepDefinitions.length;

  const currentImages = registeredImages[etdEnvironment];
  const etdComplete = Boolean(!ETD_ENABLED || (currentImages.LETTERHEAD && currentImages.SIGNATURE));
  const guideComplete = Boolean(isConnected && etdComplete);

  const advance = () => {
    setActiveStepIndex((index) => Math.min(index + 1, stepDefinitions.length - 1));
  };

  const retreat = () => {
    setActiveStepIndex((index) => Math.max(index - 1, 0));
  };

  const handleUpload = async (imageType: "LETTERHEAD" | "SIGNATURE") => {
    const inputRef = imageType === "LETTERHEAD" ? letterheadInputRef : signatureInputRef;
    const file = inputRef.current?.files?.[0];
    if (!file) return;

    setUploadBusy((prev) => ({ ...prev, [imageType === "LETTERHEAD" ? "letterhead" : "signature"]: true }));
    setUploadError((prev) => ({ ...prev, [imageType === "LETTERHEAD" ? "letterhead" : "signature"]: "" }));
    setUploadSuccess((prev) => ({ ...prev, [imageType === "LETTERHEAD" ? "letterhead" : "signature"]: false }));

    try {
      const form = new FormData();
      form.append("image_type", imageType);
      form.append("environment", etdEnvironment);
      form.append("file", file);
      await api.postForm("/shipping/etd/images", form);

      setRegisteredImages((prev) => ({
        ...prev,
        [etdEnvironment]: {
          ...prev[etdEnvironment],
          [imageType]: true,
        },
      }));
      setUploadSuccess((prev) => ({
        ...prev,
        [imageType === "LETTERHEAD" ? "letterhead" : "signature"]: true,
      }));
    } catch (e) {
      setUploadError((prev) => ({
        ...prev,
        [imageType === "LETTERHEAD" ? "letterhead" : "signature"]: e instanceof Error ? e.message : t("common.operationError"),
      }));
    } finally {
      setUploadBusy((prev) => ({ ...prev, [imageType === "LETTERHEAD" ? "letterhead" : "signature"]: false }));
    }
  };

  return (
    <section className="etd-guide card">
      <div className="etd-guide__header">
        <p className="etd-guide__eyebrow">{t("carrierIntegration.fedexEtdGuideEyebrow")}</p>
        <h3 className="etd-guide__title">{t("carrierIntegration.fedexEtdGuideTitle")}</h3>
        <p className="form-hint">{t("carrierIntegration.fedexEtdGuideIntro")}</p>
      </div>

      <div className="etd-guide__progress" aria-label={t("carrierIntegration.fedexEtdGuideProgressLabel")}>
        <div className="etd-guide__progress-track">
          <div
            className="etd-guide__progress-fill"
            style={{ width: `${(currentIndex / totalSteps) * 100}%` }}
          />
        </div>
        <div className="etd-guide__progress-meta">
          <span>{t("carrierIntegration.fedexEtdGuideProgress", { current: currentIndex, total: totalSteps })}</span>
          <span>{currentStep?.title}</span>
        </div>
      </div>

      {statusLoading && <p className="form-hint">{t("common.loading")}</p>}
      {statusError && <p className="error-message">{statusError}</p>}

      <StepCard stepNumber={currentIndex} title={currentStep.title} isActive>
        {currentStep.key === "portal" && (
          <>
            <p className="form-hint">{t("carrierIntegration.fedexEtdGuideStep1Desc")}</p>
            <div className="form-actions">
              <a href={PORTAL_URL} target="_blank" rel="noopener noreferrer" className="btn-primary">
                {t("carrierIntegration.fedexEtdGuideOpenPortal")}
              </a>
            </div>

            <ol className="etd-guide__substeps">
              <li className="etd-guide__substep">
                <p className="etd-guide__substep-label">1-1</p>
                <p className="form-hint">{t("carrierIntegration.fedexEtdGuideStep1_1")}</p>
                <img
                  src="/images/fedex-setup/step1-01-my-projects.png"
                  alt={t("carrierIntegration.fedexEtdGuideScreenshotAlt")}
                  className="etd-guide__screenshot"
                />
              </li>
              <li className="etd-guide__substep">
                <p className="etd-guide__substep-label">1-2</p>
                <p className="form-hint">{t("carrierIntegration.fedexEtdGuideStep1_2")}</p>
                <img
                  src="/images/fedex-setup/step1-02-purpose.png"
                  alt={t("carrierIntegration.fedexEtdGuideScreenshotAlt")}
                  className="etd-guide__screenshot"
                />
              </li>
              <li className="etd-guide__substep">
                <p className="etd-guide__substep-label">1-3</p>
                <p className="form-hint">{t("carrierIntegration.fedexEtdGuideStep1_3")}</p>
                <img
                  src="/images/fedex-setup/step1-03-api-cards.png"
                  alt={t("carrierIntegration.fedexEtdGuideScreenshotAlt")}
                  className="etd-guide__screenshot"
                />
                <img
                  src="/images/fedex-setup/step1-04-api-checklist.png"
                  alt={t("carrierIntegration.fedexEtdGuideScreenshotAlt")}
                  className="etd-guide__screenshot"
                />
              </li>
              <li className="etd-guide__substep">
                <p className="etd-guide__substep-label">1-4</p>
                <p className="form-hint">{t("carrierIntegration.fedexEtdGuideStep1_4")}</p>
                <img
                  src="/images/fedex-setup/step1-05-config.png"
                  alt={t("carrierIntegration.fedexEtdGuideScreenshotAlt")}
                  className="etd-guide__screenshot"
                />
              </li>
              <li className="etd-guide__substep">
                <p className="etd-guide__substep-label">1-5</p>
                <p className="form-hint">{t("carrierIntegration.fedexEtdGuideStep1_5")}</p>
                <img
                  src="/images/fedex-setup/step1-06-confirm.png"
                  alt={t("carrierIntegration.fedexEtdGuideScreenshotAlt")}
                  className="etd-guide__screenshot"
                />
              </li>
              <li className="etd-guide__substep">
                <p className="etd-guide__substep-label">1-6</p>
                <p className="form-hint">{t("carrierIntegration.fedexEtdGuideStep1_6")}</p>
                <img
                  src="/images/fedex-setup/step1-07-overview.png"
                  alt={t("carrierIntegration.fedexEtdGuideScreenshotAlt")}
                  className="etd-guide__screenshot"
                />
              </li>
            </ol>

            <div className="etd-guide__note etd-guide__note--info">
              {t("carrierIntegration.fedexEtdGuideStep1SandboxNote")}
            </div>
          </>
        )}

        {currentStep.key === "apis" && (
          <>
            <p className="form-hint">{t("carrierIntegration.fedexEtdGuideStep2Desc")}</p>
            <div className="etd-guide__note">
              {t("carrierIntegration.fedexEtdGuideStep2TradeDocumentsNote")}
            </div>
          </>
        )}

        {currentStep.key === "credentials" && (
          <>
            <p className="form-hint">{t("carrierIntegration.fedexEtdGuideStep3Desc")}</p>
            <div className="form-actions">
              <button className="btn-primary" type="button" onClick={onOpenCredentialsTab}>
                {t("carrierIntegration.fedexEtdGuideOpenCredentials")}
              </button>
            </div>
            {isConnected ? (
              <Badge variant="success" size="sm" dot>
                {t("carrierIntegration.fedexEtdGuideConnected")}
              </Badge>
            ) : (
              <p className="form-hint">{t("carrierIntegration.fedexEtdGuideConnectionHint")}</p>
            )}
          </>
        )}

        {currentStep.key === "etd" && ETD_ENABLED && (
          <div className="etd-upload">
            <p className="form-hint">{t("carrierIntegration.fedexEtdGuideStep4Desc")}</p>

            <div className="form-group">
              <label htmlFor="etd-environment">{t("carrierIntegration.fedexEtdGuideEnvironmentLabel")}</label>
              <select
                id="etd-environment"
                value={etdEnvironment}
                onChange={(e) => setEtdEnvironment(e.target.value as Env)}
              >
                <option value="sandbox">{t("carrierIntegration.fedexEtdGuideEnvironmentSandbox")}</option>
                <option value="production">{t("carrierIntegration.fedexEtdGuideEnvironmentProduction")}</option>
              </select>
            </div>

            <div className="etd-upload__grid">
              <div className="form-group">
                <label htmlFor="etd-letterhead">{t("carrierIntegration.fedexEtdGuideLetterheadLabel")}</label>
                <p className="form-hint">{t("carrierIntegration.fedexEtdGuideLetterheadHint")}</p>
                <input
                  id="etd-letterhead"
                  type="file"
                  accept="image/gif,image/png"
                  ref={letterheadInputRef}
                />
                <div className="form-actions">
                  <button
                    type="button"
                    className="btn-secondary"
                    disabled={uploadBusy.letterhead}
                    onClick={() => void handleUpload("LETTERHEAD")}
                  >
                    {uploadBusy.letterhead
                      ? t("carrierIntegration.fedexEtdGuideUploading")
                      : t("carrierIntegration.fedexEtdGuideUploadButton")}
                  </button>
                </div>
                {uploadError.letterhead && <p className="error-message">{uploadError.letterhead}</p>}
                {uploadSuccess.letterhead && (
                  <Badge variant="success" size="sm" dot>
                    {t("carrierIntegration.fedexEtdGuideRegistered")}
                  </Badge>
                )}
              </div>

              <div className="form-group">
                <label htmlFor="etd-signature">{t("carrierIntegration.fedexEtdGuideSignatureLabel")}</label>
                <p className="form-hint">{t("carrierIntegration.fedexEtdGuideSignatureHint")}</p>
                <input
                  id="etd-signature"
                  type="file"
                  accept="image/gif,image/png"
                  ref={signatureInputRef}
                />
                <div className="form-actions">
                  <button
                    type="button"
                    className="btn-secondary"
                    disabled={uploadBusy.signature}
                    onClick={() => void handleUpload("SIGNATURE")}
                  >
                    {uploadBusy.signature
                      ? t("carrierIntegration.fedexEtdGuideUploading")
                      : t("carrierIntegration.fedexEtdGuideUploadButton")}
                  </button>
                </div>
                {uploadError.signature && <p className="error-message">{uploadError.signature}</p>}
                {uploadSuccess.signature && (
                  <Badge variant="success" size="sm" dot>
                    {t("carrierIntegration.fedexEtdGuideRegistered")}
                  </Badge>
                )}
              </div>
            </div>

            <p className="form-hint">
              {t("carrierIntegration.fedexEtdGuideConstraints")}
            </p>
          </div>
        )}

        {currentStep.key === "done" && (
          <div className="etd-guide__complete">
            {guideComplete ? (
              <>
                <Badge variant="success" size="sm" dot>
                  {t("carrierIntegration.fedexEtdGuideComplete")}
                </Badge>
                <p className="form-hint">{t("carrierIntegration.fedexEtdGuideCompleteDesc")}</p>
              </>
            ) : (
              <>
                <Badge variant="neutral" size="sm" dot>
                  {t("carrierIntegration.fedexEtdGuideIncomplete")}
                </Badge>
                <p className="form-hint">{t("carrierIntegration.fedexEtdGuideIncompleteDesc")}</p>
              </>
            )}
          </div>
        )}

        <div className="form-actions etd-guide__nav">
          <button type="button" className="btn-secondary" onClick={retreat} disabled={activeStepIndex === 0}>
            {t("common.back")}
          </button>
          <button
            type="button"
            className="btn-primary"
            onClick={advance}
          >
            {activeStepIndex === stepDefinitions.length - 1
              ? t("carrierIntegration.fedexEtdGuideFinishedButton")
              : t("common.next")}
          </button>
        </div>
      </StepCard>
    </section>
  );
}
