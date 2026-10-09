import type { ReviewReasonDetail } from "./reviewReasonLabel";

/** GET /api/v1/tcg/v102/posts の1行（backend: tcg_v102_posts.PostSummary） */
export interface V102PostSummary {
  job_id: string;
  source_message_id: string;
  provider: string;
  line_posted_at: string | null;
  job_review_reason_details: ReviewReasonDetail[];
  item_count: number;
  extraction_item_count: number;
}

export interface V102PostListResponse {
  items: V102PostSummary[];
  total: number;
  limit: number;
  offset: number;
}

/** GET /api/v1/tcg/v102/posts/{job_id} の件（backend: PostItem） */
export interface V102PostItem {
  id: string;
  gemini_index: number | null;
  source_lines: number[];
  raw_price: string | null;
  raw_quantity: string | null;
  review_reason_details: ReviewReasonDetail[];
}

export interface V102PostDetail {
  job_id: string;
  source_message_id: string;
  provider: string;
  line_posted_at: string | null;
  lines: { number: number; text: string }[];
  job_review_reason_details: ReviewReasonDetail[];
  items: V102PostItem[];
}

/** PUT /api/v1/tcg/v102/posts/{job_id}/items の応答（backend: SaveItemsResponse） */
export interface V102SaveResponse {
  changed: boolean;
  item_ids: string[];
  enqueued: boolean;
}
