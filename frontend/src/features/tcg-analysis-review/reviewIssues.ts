export type AtomicReviewIssueId = 'PRODUCT_ID_UNRESOLVED' | 'UNIT_UNRESOLVED' | 'EXCLUDED' | 'PRODUCT_MASTER_UNREGISTERED' | 'SUPPLIER_UNREGISTERED';
export type ReviewIssuePresentation = { id: AtomicReviewIssueId | 'NEEDS_REVIEW'; label: string; tone: 'warning' | 'danger'; visible: boolean };

export const REVIEW_ISSUES: Record<AtomicReviewIssueId, ReviewIssuePresentation> = {
  PRODUCT_ID_UNRESOLVED: { id: 'PRODUCT_ID_UNRESOLVED', label: '商品ID未解決', tone: 'danger', visible: false },
  UNIT_UNRESOLVED: { id: 'UNIT_UNRESOLVED', label: '単位未解決', tone: 'warning', visible: true },
  EXCLUDED: { id: 'EXCLUDED', label: '除外対象', tone: 'danger', visible: true },
  PRODUCT_MASTER_UNREGISTERED: { id: 'PRODUCT_MASTER_UNREGISTERED', label: '商品マスタ未登録', tone: 'danger', visible: true },
  SUPPLIER_UNREGISTERED: { id: 'SUPPLIER_UNREGISTERED', label: '仕入元未登録', tone: 'warning', visible: true }
};

const needsReviewIssueIds: AtomicReviewIssueId[] = ['PRODUCT_ID_UNRESOLVED', 'UNIT_UNRESOLVED', 'EXCLUDED'];
const needsReviewBadge: ReviewIssuePresentation = { id: 'NEEDS_REVIEW', label: '要確認', tone: 'warning', visible: true };

export const hasNeedsReview = (issues: string[]) => needsReviewIssueIds.some((issue) => issues.includes(issue));

export const reviewIssueBadges = (issues: string[]) => {
  const atomicBadges = issues
    .filter((id): id is AtomicReviewIssueId => id in REVIEW_ISSUES)
    .map((id) => REVIEW_ISSUES[id])
    .filter((issue) => issue.visible);
  const hasOnlyPidDerivedReview = issues.includes('PRODUCT_MASTER_UNREGISTERED') && !issues.includes('UNIT_UNRESOLVED') && !issues.includes('EXCLUDED');
  return [...atomicBadges, ...(hasNeedsReview(issues) && !hasOnlyPidDerivedReview ? [needsReviewBadge] : [])];
};

// The backend currently emits both IDs for the same unresolved-PID predicate.
// Item presentation uses the master-specific label (without a duplicate summary badge)
// while status tabs retain both IDs.
export const productMetadataIssueBadges = (issues: string[]) => reviewIssueBadges(issues).filter((issue) => issue.id === 'PRODUCT_MASTER_UNREGISTERED');
