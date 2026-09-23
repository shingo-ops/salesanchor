import i18n from "../../i18n";
export type AtomicReviewIssueId = 'PRODUCT_ID_UNRESOLVED' | 'UNIT_UNRESOLVED' | 'EXCLUDED' | 'PRODUCT_MASTER_UNREGISTERED' | 'SUPPLIER_UNREGISTERED' | 'PRODUCT_CONFIRMED' | 'CONDITION_REVIEW_REQUIRED';
export type ReviewIssuePresentation = { id: AtomicReviewIssueId | 'NEEDS_REVIEW'; label: string; tone: 'warning' | 'danger' | 'success'; visible: boolean };

export const REVIEW_ISSUES: Record<AtomicReviewIssueId, ReviewIssuePresentation> = {
  CONDITION_REVIEW_REQUIRED: { id: 'CONDITION_REVIEW_REQUIRED', get label() { return i18n.t("conditionReview.needsReview"); }, tone: 'warning', visible: true },
  PRODUCT_ID_UNRESOLVED: { id: 'PRODUCT_ID_UNRESOLVED', get label() { return i18n.t("reviewIssues.productIdUnresolved"); }, tone: 'danger', visible: false },
  UNIT_UNRESOLVED: { id: 'UNIT_UNRESOLVED', get label() { return i18n.t("reviewIssues.unitUnresolved"); }, tone: 'warning', visible: true },
  EXCLUDED: { id: 'EXCLUDED', get label() { return i18n.t("reviewIssues.excluded"); }, tone: 'danger', visible: true },
  PRODUCT_MASTER_UNREGISTERED: { id: 'PRODUCT_MASTER_UNREGISTERED', get label() { return i18n.t("reviewIssues.productMasterUnregistered"); }, tone: 'danger', visible: true },
  SUPPLIER_UNREGISTERED: { id: 'SUPPLIER_UNREGISTERED', get label() { return i18n.t("reviewIssues.supplierUnregistered"); }, tone: 'warning', visible: true },
  PRODUCT_CONFIRMED: { id: 'PRODUCT_CONFIRMED', get label() { return i18n.t("reviewIssues.confirmed"); }, tone: 'success', visible: true },
};

const needsReviewIssueIds: AtomicReviewIssueId[] = ['PRODUCT_ID_UNRESOLVED', 'UNIT_UNRESOLVED', 'EXCLUDED', 'CONDITION_REVIEW_REQUIRED'];
const needsReviewBadge: ReviewIssuePresentation = { id: 'NEEDS_REVIEW', get label() { return i18n.t("conditionReview.needsReview"); }, tone: 'warning', visible: true };

export const hasNeedsReview = (issues: string[]) => needsReviewIssueIds.some((issue) => issues.includes(issue));

export const reviewIssueBadges = (issues: string[]) => {
  const atomicBadges = issues
    .filter((id): id is AtomicReviewIssueId => id in REVIEW_ISSUES)
    .map((id) => REVIEW_ISSUES[id])
    .filter((issue) => issue.visible);
  const hasOnlyPidDerivedReview = issues.includes('PRODUCT_MASTER_UNREGISTERED') && !issues.includes('UNIT_UNRESOLVED') && !issues.includes('EXCLUDED') && !issues.includes('CONDITION_REVIEW_REQUIRED');
  return [...atomicBadges, ...(hasNeedsReview(issues) && !hasOnlyPidDerivedReview ? [needsReviewBadge] : [])];
};

// The backend currently emits both IDs for the same unresolved-PID predicate.
// Item presentation uses the master-specific label (without a duplicate summary badge)
// while status tabs retain both IDs.
export const productMetadataIssueBadges = (issues: string[]) => reviewIssueBadges(issues).filter((issue) => issue.id === 'PRODUCT_MASTER_UNREGISTERED');
