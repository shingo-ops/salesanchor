import { describe, expect, it, vi } from "vitest";
import { api } from "../../lib/api";
import { attemptCopy, getExtractionAttempts, parseAttempts } from "./extractionAttemptsApi";
vi.mock("../../lib/api", () => ({ api: { get: vi.fn() } }));
const job = "00000000-0000-0000-0000-000000000001";
const id = "00000000-0000-0000-0000-000000000002";
const row = { id, extraction_job_id: job, phase: "failed", completion: "failed", error_code: "API_ERROR", started_at: "2026-09-14T00:00:00Z", finished_at: "invalid" };
const response = (r: unknown = row) => ({ extraction_job_id: job, attempts: [r] });
describe("attempt summary boundary", () => {
 it("projects only allowed facts, never private payloads", () => {
  const [safe] = parseAttempts(response({ ...row, input_payload: "SECRET", response_text: "SECRET", supplier_name: "SECRET" }), job);
  expect(JSON.stringify(safe)).not.toContain("SECRET"); expect(attemptCopy(safe)).not.toContain("SECRET"); expect(safe.finishedAt).toBeNull();
 });
 it("maps unknown values to fixed labels and copy codes", () => {
  const [safe] = parseAttempts(response({ ...row, phase: "SECRET", error_code: "SECRET", completion: "SECRET" }), job);
  expect(safe.phase).toBe("unknown"); expect(safe.completion).toBe("unknown"); expect(attemptCopy(safe)).not.toContain("SECRET");
 });
 it.each([null, {}, { extraction_job_id: id, attempts: [] }, response({ ...row, extraction_job_id: id }), response({ ...row, id: "SECRET" }), { extraction_job_id: job, attempts: [row, row] }])("rejects malformed/foreign records", value => expect(() => parseAttempts(value, job)).toThrow());
 it.each(["started", "received"])("does not claim %s is finished", phase => expect(parseAttempts(response({ ...row, phase, completion: "completed" }), job)[0].completion).toBe("unconfirmed"));
 it("uses only paginated list GET", async () => {
  vi.mocked(api.get).mockResolvedValue(response()); await getExtractionAttempts(job, 25);
  expect(api.get).toHaveBeenCalledWith(`/tcg/diagnostics/extraction-jobs/${job}/attempts?limit=25&offset=25`);
 });
});
