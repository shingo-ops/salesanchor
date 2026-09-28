import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Badge, type BadgeVariant } from "../../../components/Badge";
import { Button } from "../../../components/Button";
import { Card } from "../../../components/Card";
import type { AnalysisRulesSidebarKey } from "./AnalysisRulesSidebar";
import "./LineWorkflowGuidePanel.css";

const STEP_NUMBERS = [1, 2, 3, 4, 5, 6, 7] as const;
type StepNumber = (typeof STEP_NUMBERS)[number];

type GuideAction =
  | { label: string; section: AnalysisRulesSidebarKey }
  | { label: string; pathname: "/super-admin/tcg-distribution" };

const OWNER_VARIANTS: Record<StepNumber, BadgeVariant> = {
  1: "info",
  2: "warning",
  3: "info",
  4: "warning",
  5: "info",
  6: "warning",
  7: "info",
};

const STEP_ACTIONS: Record<StepNumber, readonly GuideAction[]> = {
  1: [{ label: "openImport", section: "import" }],
  2: [{ label: "openSupplierMaster", section: "supplier-master" }],
  3: [{ label: "openImport", section: "import" }],
  4: [
    { label: "openExtractionRules", section: "extraction-rules" },
    { label: "openKnowledgeAliases", section: "knowledge-aliases" },
    { label: "openPromptConfig", section: "prompt-config" },
    { label: "openErrorLog", section: "error-log" },
  ],
  5: [
    { label: "openProductMaster", section: "product-master" },
    { label: "openUnitMaster", section: "unit-master" },
    { label: "openConditionsMaster", section: "conditions-master" },
  ],
  6: [
    { label: "openImport", section: "import" },
    { label: "openProductMaster", section: "product-master" },
    { label: "openSupplierMaster", section: "supplier-master" },
    { label: "openErrorLog", section: "error-log" },
  ],
  7: [{ label: "openDistribution", pathname: "/super-admin/tcg-distribution" }],
};

const DETAIL_KEYS = ["purpose", "reference", "input", "result", "next", "trouble"] as const;

interface LineWorkflowGuidePanelProps {
  onNavigate: (key: AnalysisRulesSidebarKey) => void;
}

export function LineWorkflowGuidePanel({ onNavigate }: LineWorkflowGuidePanelProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const prefix = "analysisRules.lineWorkflowGuide";

  const runAction = (action: GuideAction) => {
    if ("section" in action) {
      onNavigate(action.section);
      return;
    }
    navigate(action.pathname);
  };

  return (
    <article className="line-workflow-guide" aria-labelledby="line-workflow-guide-title">
      <section className="line-workflow-guide__section">
        <h3 id="line-workflow-guide-title" className="line-workflow-guide__section-title">
          {t(`${prefix}.title`)}
        </h3>
        <p className="line-workflow-guide__body">{t(`${prefix}.intro`)}</p>
        <p className="line-workflow-guide__caption">{t(`${prefix}.readOnlyNotice`)}</p>
      </section>

      <section className="line-workflow-guide__section" aria-labelledby="line-workflow-prerequisites-title">
        <h3 id="line-workflow-prerequisites-title" className="line-workflow-guide__section-title">
          {t(`${prefix}.prerequisites.title`)}
        </h3>
        <ul className="line-workflow-guide__list">
          {[1, 2, 3].map((item) => (
            <li key={item}>{t(`${prefix}.prerequisites.item${item}`)}</li>
          ))}
        </ul>
      </section>

      <nav className="line-workflow-guide__section" aria-label={t(`${prefix}.toc.ariaLabel`)}>
        <h3 className="line-workflow-guide__section-title">{t(`${prefix}.toc.title`)}</h3>
        <ol className="line-workflow-guide__toc-list">
          {STEP_NUMBERS.map((step) => (
            <li key={step}>
              <a href={`#line-workflow-step-${step}`}>{t(`${prefix}.steps.step${step}.title`)}</a>
            </li>
          ))}
        </ol>
      </nav>

      <section className="line-workflow-guide__section" aria-labelledby="line-workflow-steps-title">
        <h3 id="line-workflow-steps-title" className="line-workflow-guide__section-title">
          {t(`${prefix}.stepsTitle`)}
        </h3>
        <ol className="line-workflow-guide__steps">
          {STEP_NUMBERS.map((step) => {
            const stepPrefix = `${prefix}.steps.step${step}`;
            return (
              <li key={step}>
                <Card
                  variant="container"
                  density="compact"
                  className="line-workflow-guide__card"
                  data-testid="line-workflow-step"
                >
                  <div className="line-workflow-guide__step-heading">
                    <h3
                      id={`line-workflow-step-${step}`}
                      className="line-workflow-guide__card-title"
                      tabIndex={-1}
                    >
                      {t(`${prefix}.stepLabel`, { step })}: {t(`${stepPrefix}.title`)}
                    </h3>
                    <Badge variant={OWNER_VARIANTS[step]} size="sm">
                      {t(`${stepPrefix}.owner`)}
                    </Badge>
                  </div>

                  <dl className="line-workflow-guide__details">
                    {DETAIL_KEYS.map((detailKey) => (
                      <div key={detailKey} className="line-workflow-guide__detail">
                        <dt>{t(`${prefix}.fields.${detailKey}`)}</dt>
                        <dd>{t(`${stepPrefix}.${detailKey}`)}</dd>
                      </div>
                    ))}
                  </dl>

                  <div
                    className="line-workflow-guide__actions"
                    aria-label={t(`${prefix}.actions.ariaLabel`, { step })}
                  >
                    {STEP_ACTIONS[step].map((action) => (
                      <Button
                        key={action.label}
                        type="button"
                        variant="secondary"
                        size="sm"
                        onClick={() => runAction(action)}
                      >
                        {t(`${prefix}.actions.${action.label}`)}
                      </Button>
                    ))}
                  </div>
                </Card>
              </li>
            );
          })}
        </ol>
      </section>

      <section className="line-workflow-guide__section" aria-labelledby="line-workflow-exceptions-title">
        <h3 id="line-workflow-exceptions-title" className="line-workflow-guide__section-title">
          {t(`${prefix}.exceptions.title`)}
        </h3>
        <ul className="line-workflow-guide__list">
          {[1, 2, 3, 4].map((item) => (
            <li key={item}>{t(`${prefix}.exceptions.item${item}`)}</li>
          ))}
        </ul>
      </section>
    </article>
  );
}
