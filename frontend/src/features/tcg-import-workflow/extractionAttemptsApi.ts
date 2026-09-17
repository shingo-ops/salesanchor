import { api } from "../../lib/api";

export const attemptCodes = ["SOFT_TIME_LIMIT", "API_ERROR", "INVALID_RESPONSE", "REFERENCE_CHANGED", "WORK_ID_CONFLICT", "RECORD_WRITE_FAILED", "RESPONSE_NOT_RECORDED", "INPUT_TOO_LARGE", "RESPONSE_TOO_LARGE", "PARSED_TOO_LARGE", "CLAIM_CONFLICT", "ATTEMPT_CONFLICT"] as const;
export type AttemptCode = typeof attemptCodes[number] | "unknown";
export type AttemptPhase = "started" | "received" | "completed" | "failed" | "unknown";
export interface ExtractionAttempt {
  id: string; jobId: string; phase: AttemptPhase; code: AttemptCode;
  completion: "unconfirmed" | "completed" | "failed" | "unknown";
  startedAt: string | null; receivedAt: string | null; finishedAt: string | null;
}
const uuid = (value: unknown): value is string => typeof value === "string" && /^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/i.test(value);
const object = (value: unknown): value is Record<string, unknown> => typeof value === "object" && value !== null && !Array.isArray(value);
const date = (value: unknown) => typeof value === "string" && /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/.test(value) && Number.isFinite(Date.parse(value)) ? new Date(value).toISOString() : null;
export function parseAttempts(value: unknown, jobId: string): ExtractionAttempt[] {
  if (!uuid(jobId) || !object(value) || value.extraction_job_id !== jobId || !Array.isArray(value.attempts) || value.attempts.length > 25) throw new Error("Invalid attempt response");
  const ids = new Set<string>();
  return value.attempts.map((row: unknown) => {
    if (!object(row) || !uuid(row.id) || row.extraction_job_id !== jobId || ids.has(row.id)) throw new Error("Invalid attempt identity");
    ids.add(row.id);
    const phase = ["started", "received", "completed", "failed"].includes(String(row.phase)) && typeof row.phase === "string" ? row.phase as AttemptPhase : "unknown";
    const completion = phase === "started" || phase === "received" || row.completion === "unconfirmed" ? "unconfirmed" : (phase === "completed" || phase === "failed") && row.completion === phase ? phase : "unknown";
    return { id: row.id, jobId, phase, completion, code: attemptCodes.includes(row.error_code as typeof attemptCodes[number]) ? row.error_code as AttemptCode : "unknown", startedAt: date(row.started_at), receivedAt: date(row.response_received_at), finishedAt: date(row.finished_at) };
  });
}
export async function getExtractionAttempts(jobId: string, offset: number) {
  if (!uuid(jobId) || !Number.isSafeInteger(offset) || offset < 0) throw new Error("Invalid attempt request");
  return parseAttempts(await api.get<unknown>(`/tcg/diagnostics/extraction-jobs/${jobId}/attempts?limit=25&offset=${offset}`), jobId);
}
export const attemptCopy = (row: ExtractionAttempt) => JSON.stringify({ extraction_job_id: row.jobId, attempt_id: row.id, phase: row.phase, error_code: row.code, started_at: row.startedAt, response_received_at: row.receivedAt, finished_at: row.finishedAt }, null, 2);
