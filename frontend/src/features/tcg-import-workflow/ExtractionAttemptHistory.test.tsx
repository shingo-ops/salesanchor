import { act, fireEvent, render, screen, waitFor, cleanup } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import { ExtractionAttemptHistory } from "./ExtractionAttemptHistory";
import { getExtractionAttempts, type ExtractionAttempt } from "./extractionAttemptsApi";
vi.mock("./extractionAttemptsApi", async importOriginal => ({ ...await importOriginal<typeof import("./extractionAttemptsApi")>(), getExtractionAttempts: vi.fn() }));
const job = "00000000-0000-0000-0000-000000000001";
const record: ExtractionAttempt = { id: "00000000-0000-0000-0000-000000000002", jobId: job, phase: "failed", completion: "failed", code: "SOFT_TIME_LIMIT", startedAt: null, receivedAt: null, finishedAt: null };
const open = () => fireEvent.click(screen.getByRole("button", { name: i18n.t("pmgAttempt.open") }));
beforeEach(async () => { vi.clearAllMocks(); await i18n.changeLanguage("en"); vi.mocked(getExtractionAttempts).mockResolvedValue([record]); Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: vi.fn().mockResolvedValue(undefined) } }); });
afterEach(cleanup);
describe("attempt history", () => {
 it("loads only after explicit action and copies safe facts", async () => {
  render(<ExtractionAttemptHistory jobId={job}/>); expect(getExtractionAttempts).not.toHaveBeenCalled(); open();
  await screen.findByText("Attempt failed"); fireEvent.click(screen.getByRole("button", {name: "Copy diagnostic information"})); await screen.findByText("Diagnostic information copied");
  expect(navigator.clipboard.writeText).toHaveBeenCalledWith(expect.stringContaining("SOFT_TIME_LIMIT"));
 });
 it.each([403,404,503])("shows %s as unavailable, not empty", async status => {
  vi.mocked(getExtractionAttempts).mockRejectedValue(new Error(String(status))); render(<ExtractionAttemptHistory jobId={job}/>); open(); await screen.findByRole("alert"); expect(screen.queryByText("There are no attempt records on this page.")).toBeNull();
 });
 it("removes old copy actions while refreshing and after failure", async () => {
  render(<ExtractionAttemptHistory jobId={job}/>); open(); await screen.findByText("Attempt failed"); vi.mocked(getExtractionAttempts).mockRejectedValue(new Error()); fireEvent.click(screen.getByRole("button", {name:"Refresh history"})); expect(screen.queryByRole("button", {name:"Copy diagnostic information"})).toBeNull(); await screen.findByRole("alert");
 });
 it("does not report clipboard failure as success", async () => {
  vi.mocked(navigator.clipboard.writeText).mockRejectedValue(new Error()); render(<ExtractionAttemptHistory jobId={job}/>); open(); await screen.findByText("Attempt failed"); fireEvent.click(screen.getByRole("button", {name:"Copy diagnostic information"})); await screen.findByRole("alert"); expect(screen.queryByText("Diagnostic information copied")).toBeNull();
 });
 it("ignores delayed results after job change", async () => {
  let resolve!: (r: ExtractionAttempt[]) => void; vi.mocked(getExtractionAttempts).mockImplementationOnce(() => new Promise(r => { resolve = r; })).mockResolvedValue([]);
  const {rerender} = render(<ExtractionAttemptHistory jobId={job}/>); open(); rerender(<ExtractionAttemptHistory jobId="00000000-0000-0000-0000-000000000003"/>); await screen.findByText("There are no attempt records on this page."); await act(async () => resolve([record])); expect(screen.queryByText("Attempt failed")).toBeNull();
 });
 it("allows returning from an empty next page", async () => {
  vi.mocked(getExtractionAttempts).mockResolvedValueOnce(Array.from({length:25}, (_, i) => ({...record,id:String(i)}))).mockResolvedValueOnce([]);
  render(<ExtractionAttemptHistory jobId={job}/>); open(); await screen.findAllByText("Attempt failed"); fireEvent.click(screen.getByRole("button",{name:"Next"})); await screen.findByText("There are no attempt records on this page."); expect((screen.getByRole("button",{name:"Previous"}) as HTMLButtonElement).disabled).toBe(false); expect(getExtractionAttempts).toHaveBeenLastCalledWith(job,25);
 });
 it("keeps feedback from the latest copy operation", async () => {
  let success!: () => void;
  vi.mocked(navigator.clipboard.writeText).mockImplementationOnce(() => new Promise<void>(resolve => { success = resolve; })).mockRejectedValueOnce(new Error());
  render(<ExtractionAttemptHistory jobId={job}/>); open(); await screen.findByText("Attempt failed");
  const button = screen.getByRole("button", {name:"Copy diagnostic information"});
  fireEvent.click(button); fireEvent.click(button); await screen.findByRole("alert");
  await act(async () => success()); expect(screen.queryByText("Diagnostic information copied")).toBeNull(); expect(screen.getByRole("alert")).toBeTruthy();
 });
 it("renders Japanese cause and action", async () => {
  await i18n.changeLanguage("ja"); render(<ExtractionAttemptHistory jobId={job}/>); open(); await waitFor(() => expect(screen.getByText(i18n.t("pmgAttempt.reason.SOFT_TIME_LIMIT"))).toBeTruthy());
 });
});
