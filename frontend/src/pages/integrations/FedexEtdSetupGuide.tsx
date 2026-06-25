import { useEffect, useRef, useState, type ReactNode } from "react";
import { Trans, useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { Badge } from "../../components/Badge";
import { Check } from "../../constants/icons";
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
  heading: string;
}

const ETD_ENABLED = import.meta.env.VITE_FEDEX_ETD_ENABLED === "true";

const PORTAL_URL = "https://developer.fedex.com/api/ja-jp/home.html";

function StepIndicator({
  steps,
  activeIndex,
  ariaLabel,
}: {
  steps: StepDefinition[];
  activeIndex: number;
  ariaLabel: string;
}) {
  return (
    <nav className="etd-stepper" aria-label={ariaLabel}>
      <ol className="etd-stepper__list">
        {steps.map((step, index) => {
          const isDone = index < activeIndex;
          const isCurrent = index === activeIndex;
          const stateClass = isDone
            ? " etd-stepper__item--done"
            : isCurrent
              ? " etd-stepper__item--current"
              : "";
          return (
            <li
              key={step.key}
              className={`etd-stepper__item${stateClass}`}
              aria-current={isCurrent ? "step" : undefined}
            >
              <div className="etd-stepper__dot" aria-hidden="true">
                {isDone ? <Check size={14} /> : index + 1}
              </div>
              <span className="etd-stepper__label">{step.heading}</span>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

interface SubstepItem {
  label: string;
  descriptions: string[];
  screenshots: Array<{ src: string }>;
}

function SubstepPane({
  substeps,
  screenshotAlt,
  onLastReached,
  onAdvance,
  advanceLabel,
}: {
  substeps: SubstepItem[];
  screenshotAlt: string;
  onLastReached?: (isLast: boolean) => void;
  onAdvance?: () => void;
  advanceLabel?: string;
}) {
  const [activeIndex, setActiveIndex] = useState(0);
  const active = substeps[activeIndex] ?? substeps[0];
  const isLast = activeIndex === substeps.length - 1;

  return (
    <div className="etd-guide__substep-pane">
      <ol className="etd-guide__substep-nav" role="tablist">
        {substeps.map((sub, i) => (
          <li key={sub.label}>
            <button
              type="button"
              role="tab"
              aria-selected={i === activeIndex}
              className={`etd-guide__substep-nav-item${i === activeIndex ? " etd-guide__substep-nav-item--active" : ""}`}
              onClick={(e) => {
                const pane = (e.currentTarget as HTMLElement).closest(
                  ".page-layout-content",
                ) as HTMLElement | null;
                const scrollTop = pane?.scrollTop ?? 0;
                setActiveIndex(i);
                onLastReached?.(i === substeps.length - 1);
                requestAnimationFrame(() => {
                  if (pane) pane.scrollTop = scrollTop;
                });
              }}
            >
              {sub.label}
            </button>
          </li>
        ))}
      </ol>
      <div className="etd-guide__substep-detail" role="tabpanel">
        {active.descriptions.map((desc, i) => (
          <p key={i} className="form-hint">{desc}</p>
        ))}
        {active.screenshots.map((shot) => (
          <a
            key={shot.src}
            href={shot.src}
            target="_blank"
            rel="noopener noreferrer"
            className="etd-guide__screenshot-link"
          >
            <img
              src={shot.src}
              alt={screenshotAlt}
              className="etd-guide__screenshot"
            />
          </a>
        ))}
        {isLast && onAdvance && (
          <div className="form-actions etd-guide__substep-advance">
            <button type="button" className="btn-primary" onClick={onAdvance}>
              {advanceLabel}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function StepCard({
  stepNumber,
  heading,
  intro,
  children,
  isActive,
}: {
  stepNumber: number;
  heading: string;
  intro?: ReactNode;
  children: ReactNode;
  isActive: boolean;
}) {
  return (
    <section className="etd-guide__step">
      <div className="etd-guide__step-header">
        <div className="etd-guide__step-title-row">
          <span className="etd-guide__step-number">{stepNumber}</span>
          <strong>{heading}</strong>
        </div>
        {intro && <p className="etd-guide__step-intro">{intro}</p>}
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
  const [portalAtEnd, setPortalAtEnd] = useState(false);
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

  useEffect(() => {
    setPortalAtEnd(false);
  }, [activeStepIndex]);

  const isConnected = Boolean(
    (productionStatus?.configured && productionStatus.last_test_ok === true)
      || (sandboxStatus?.configured && sandboxStatus.last_test_ok === true),
  );

  const stepDefinitions: StepDefinition[] = [
    { key: "portal", title: t("carrierIntegration.fedexEtdGuideStep1Title"), heading: t("carrierIntegration.fedexEtdGuideStep1Heading") },
    { key: "apis", title: t("carrierIntegration.fedexEtdGuideStep2Title"), heading: t("carrierIntegration.fedexEtdGuideStep2Heading") },
    { key: "credentials", title: t("carrierIntegration.fedexEtdGuideStep3Title"), heading: t("carrierIntegration.fedexEtdGuideStep3Heading") },
    ...(ETD_ENABLED
      ? [{ key: "etd" as const, title: t("carrierIntegration.fedexEtdGuideStep4Title"), heading: t("carrierIntegration.fedexEtdGuideStep4Heading") }]
      : []),
    { key: "done", title: t("carrierIntegration.fedexEtdGuideStep5Title"), heading: t("carrierIntegration.fedexEtdGuideStep5Heading") },
  ];

  const currentStep = stepDefinitions[activeStepIndex] ?? stepDefinitions[0];
  const currentIndex = activeStepIndex + 1;

  const currentImages = registeredImages[etdEnvironment];
  const etdComplete = Boolean(!ETD_ENABLED || (currentImages.LETTERHEAD && currentImages.SIGNATURE));
  const guideComplete = Boolean(isConnected && etdComplete);

  const advance = () => {
    setActiveStepIndex((index) => Math.min(index + 1, stepDefinitions.length - 1));
  };

  const canAdvance = currentStep.key !== "portal" || portalAtEnd;

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
    <section className="etd-guide">
      <StepIndicator
        steps={stepDefinitions}
        activeIndex={activeStepIndex}
        ariaLabel={t("carrierIntegration.fedexEtdGuideProgressLabel")}
      />

      {statusLoading && <p className="form-hint">{t("common.loading")}</p>}
      {statusError && <p className="error-message">{statusError}</p>}

      <StepCard
        stepNumber={currentIndex}
        heading={currentStep.heading}
        intro={
          currentStep.key === "portal" ? (
            <Trans
              i18nKey="carrierIntegration.fedexEtdGuideStep1Desc"
              components={{
                portalLink: (
                  <a
                    href={PORTAL_URL}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="etd-guide__inline-link"
                  />
                ),
              }}
            />
          ) : currentStep.key === "apis" ? (
            t("carrierIntegration.fedexEtdGuideStep2Desc")
          ) : currentStep.key === "credentials" ? (
            t("carrierIntegration.fedexEtdGuideStep3Desc")
          ) : currentStep.key === "etd" && ETD_ENABLED ? (
            t("carrierIntegration.fedexEtdGuideStep4Desc")
          ) : undefined
        }
        isActive
      >
        {currentStep.key === "portal" && (
          <SubstepPane
            screenshotAlt={t("carrierIntegration.fedexEtdGuideScreenshotAlt")}
            onLastReached={setPortalAtEnd}
            onAdvance={advance}
            advanceLabel={t("carrierIntegration.fedexEtdGuideStep1AdvanceButton")}
            substeps={[
              {
                label: "1-1",
                descriptions: [t("carrierIntegration.fedexEtdGuideStep1_1")],
                screenshots: [{ src: "/images/fedex-setup/step1-01-my-projects.png" }],
              },
              {
                label: "1-2",
                descriptions: [t("carrierIntegration.fedexEtdGuideStep1_2")],
                screenshots: [{ src: "/images/fedex-setup/step1-02-purpose.png" }],
              },
              {
                label: "1-3",
                descriptions: [t("carrierIntegration.fedexEtdGuideStep1_3")],
                screenshots: [
                  { src: "/images/fedex-setup/step1-03-api-cards.png" },
                  { src: "/images/fedex-setup/step1-04-api-checklist.png" },
                ],
              },
              {
                label: "1-4",
                descriptions: [t("carrierIntegration.fedexEtdGuideStep1_4")],
                screenshots: [{ src: "/images/fedex-setup/step1-05-config.png" }],
              },
              {
                label: "1-5",
                descriptions: [t("carrierIntegration.fedexEtdGuideStep1_5")],
                screenshots: [{ src: "/images/fedex-setup/step1-06-confirm.png" }],
              },
              {
                label: "1-6",
                descriptions: [
                  t("carrierIntegration.fedexEtdGuideStep1_6"),
                  t("carrierIntegration.fedexEtdGuideStep1_6b"),
                ],
                screenshots: [{ src: "/images/fedex-setup/step1-07-overview.png" }],
              },
            ]}
          />
        )}

        {currentStep.key === "apis" && (
          <div className="etd-guide__note">
            {t("carrierIntegration.fedexEtdGuideStep2TradeDocumentsNote")}
          </div>
        )}

        {currentStep.key === "credentials" && (
          <>
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

        {currentStep.key !== "portal" && (
          <div className="form-actions etd-guide__nav">
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
        )}
      </StepCard>
    </section>
  );
}
