import type { AnalysisReviewItem } from './ItemComparison';
import { reviewIssueBadges, type ReviewIssuePresentation } from './reviewIssues';
import type { ReviewListColumnId } from './reviewListColumns';

export type ReviewListRow = {
  extraction_item_id: string;
  source_message_id: string;
  issueBadges: ReviewIssuePresentation[];
  values: Record<Exclude<ReviewListColumnId, 'REVIEW_STATUS'>, string>;
};

const displayRaw = (value: string | undefined) => value || '未記載';
const displayResolved = (value: string | undefined) => value || '未解決';
const memoPreview = (memo: string) => memo.length > 120 ? `${memo.slice(0, 120)}…` : memo || '—';

export function buildReviewListRow(item: AnalysisReviewItem, memo: string): ReviewListRow {
  return {
    extraction_item_id: item.extraction_item_id,
    source_message_id: item.source_message_id,
    issueBadges: reviewIssueBadges(item.review_issues || []),
    values: {
      PROVIDER: item.provider || '未記載',
      PRODUCT_NAME: displayRaw(item.gemini.name),
      PRODUCT_ID: displayResolved(item.system.product_id),
      QUANTITY: displayRaw(item.gemini.quantity),
      PRICE: displayRaw(item.gemini.price),
      UNIT: displayResolved(item.system.unit),
      CONDITION: displayResolved(item.system.condition),
      MEMO: memoPreview(memo)
    }
  };
}
