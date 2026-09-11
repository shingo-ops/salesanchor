import { api } from "../../lib/api";

export type Coverage =
  "complete" | "pending_review" | "discarded" | "legacy_unknown";
export interface MessagesStage {
  unit: "source_message";
  total: number | null;
  created?: number; reused?: number; inactive?: number; without_extraction_job?: number;
  reason?: string;
}
export interface ExtractionStage {
  unit: "extraction_job"; total: number | null; states?: Record<string, number>;
  completed?: number; pending?: number; running?: number; unknown?: number;
  succeeded?: number; empty?: number; failed?: number; residual_items_on_error?: number;
  residual_results_on_error?: number; reason?: string;
}
export interface AnalysisStage {
  unit: "extraction_item"; total: number | null; results_present?: number; results_missing?: number;
  needs_review?: number; review_reasons?: Record<string, number>; reasons_may_overlap?: boolean;
  execution_state?: "unrecorded"; execution_reason?: string; completed?: null; succeeded?: null;
  failed?: null; running?: null; pending?: null; reason?: string;
}
export interface ImportProgress {
  scope: { type: "import"; import_job_id: string };
  as_of: string;
  coverage: Coverage;
  review_status: string;
  reason: string | null;
  messages: MessagesStage;
  extraction: ExtractionStage;
  analysis: AnalysisStage;
}
export interface ImportItem {
  id: string;
  extraction_job_id: string;
  source_message_id: string;
  extraction_status: string;
  analysis_result_id: string | null;
  note_ja: string | null;
  needs_review: boolean | null;
  review_reasons: string | null;
  raw_product_name: string | null; raw_quantity: string | null; raw_price: string | null;
  raw_unit: string | null; raw_state: string | null; raw_memo: string | null;
  analysis_status: string | null; exclusion: string | null; quantity_normalized: number | string | null;
  price_normalized: number | string | null; analysis_execution_state: "unrecorded";
  created_at: string;
}
export interface ImportItems {
  scope: { type: "import"; import_job_id: string };
  as_of: string;
  coverage: Coverage;
  review_status: string;
  reason: string | null;
  total: number | null;
  items: ImportItem[] | null;
  limit: number;
  offset: number;
  filter: ImportItemFilter;
  unit: "extraction_item";
}
export type ImportItemFilter = "all" | "needs_review" | "extraction_error";
export const getImportProgress = (id: string) =>
  api.get<ImportProgress>(`/tcg/line-import/${id}/progress`);
export const getImportItems = (
  id: string,
  limit: number,
  offset: number,
  filter: ImportItemFilter,
) =>
  api.get<ImportItems>(
    `/tcg/line-import/${id}/items?limit=${limit}&offset=${offset}&filter=${filter}`,
  );
