import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../../i18n";
import { api } from "../../../lib/api";
import { AiJobsSection } from "./AiJobsSection";

vi.mock("../../../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn() },
  ApiError: class extends Error {},
}));

const JOB_KEYS = [
  "line_extraction",
  "secretary_intent",
  "translation_inbound",
  "translation_inbound_escalation",
  "translation_outbound",
];
const ERROR_CODES = ["auth_failed", "timeout", "rate_limited", "http_error", "unreadable", "tool_used", "not_ready", "busy", "other"];
const PROVIDERS = ["gemini", "codex", "claude"];
const LOGIN_REASONS = ["auth_failed", "key_missing", "not_ready"];

function job(jobKey: string, over: Record<string, unknown> = {}) {
  const secretary = jobKey === "secretary_intent";
  return {
    job_key: jobKey,
    provider: secretary ? "claude" : "gemini",
    model: secretary ? "sonnet" : "gemini-3.1-flash-lite",
    choice_id: secretary ? 17 : 1,
    choices: secretary
      ? [
          { choice_id: 17, provider: "claude", model: "sonnet" },
          { choice_id: 18, provider: "claude", model: "test-model" },
        ]
      : [{ choice_id: 1, provider: "gemini", model: "gemini-3.1-flash-lite" }],
    login_ok: true,
    login_reason: null,
    last_ok_at: null,
    count_24h: 0,
    failed_24h: 0,
    last_error_code: null,
    last_error_at: null,
    login_refreshed_at: null,
    switchable: secretary,
    ...over,
  };
}

const HISTORY = {
  items: [
    { job_key: "secretary_intent", old: { provider: "claude", model: "sonnet" }, new: { provider: "claude", model: "test-model" }, changed_by_name: "Tanaka", changed_by_id: 7, changed_at: "2026-11-03T03:00:00Z" },
    { job_key: "secretary_intent", old: { provider: "claude", model: "test-model" }, new: { provider: "claude", model: "sonnet" }, changed_by_name: null, changed_by_id: 8, changed_at: "2026-11-03T02:00:00Z" },
    { job_key: "secretary_intent", old: { provider: "claude", model: "sonnet" }, new: { provider: "claude", model: "test-model" }, changed_by_name: null, changed_by_id: null, changed_at: "2026-11-03T01:00:00Z" },
  ],
};

function mockGets(jobs = JOB_KEYS.map((k) => job(k))) {
  vi.mocked(api.get).mockImplementation((path: string) => {
    if (path.startsWith("/super-admin/ai-jobs/history")) return Promise.resolve(HISTORY as never);
    return Promise.resolve({ jobs } as never);
  });
}

const view = () => render(<AiJobsSection t={i18n.t.bind(i18n)} />);

describe("AiJobsSection", () => {
  beforeEach(async () => {
    vi.resetAllMocks();
    await i18n.changeLanguage("en");
  });

  it("shows 5 rows and the change button only on switchable rows (K3・K11)", async () => {
    mockGets();
    view();
    // 秘書の名前は履歴の表にも出るので、1つ以上あることを待つ（findByText だと複数で止まる）
    await screen.findAllByText(i18n.t("analysisRules.dashboard.aiJobs.job.secretary_intent"));
    for (const key of JOB_KEYS) {
      expect(screen.getAllByText(i18n.t(`analysisRules.dashboard.aiJobs.job.${key}`)).length).toBeGreaterThan(0);
    }
    expect(screen.getAllByRole("button", { name: i18n.t("analysisRules.dashboard.aiJobs.change") })).toHaveLength(1);
    expect(screen.getAllByText(i18n.t("analysisRules.dashboard.aiJobs.notSwitchable"))).toHaveLength(4);
  });

  it("shows the login reason when login is not ok", async () => {
    mockGets(JOB_KEYS.map((k) => (k === "line_extraction" ? job(k, { login_ok: false, login_reason: "key_missing" }) : job(k))));
    view();
    expect(await screen.findByText(i18n.t("analysisRules.dashboard.aiJobs.loginReason.key_missing"))).toBeTruthy();
  });

  it("changes the secretary in two steps and sends a numeric choice_id", async () => {
    mockGets();
    vi.mocked(api.put).mockResolvedValue(job("secretary_intent", { choice_id: 18, model: "test-model" }) as never);
    view();
    fireEvent.click(await screen.findByRole("button", { name: i18n.t("analysisRules.dashboard.aiJobs.change") }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText(i18n.t("analysisRules.dashboard.aiJobs.selectLabel")), { target: { value: "18" } });
    fireEvent.click(within(dialog).getByRole("button", { name: i18n.t("analysisRules.dashboard.aiJobs.next") }));
    expect(api.put).not.toHaveBeenCalled();
    fireEvent.click(within(dialog).getByRole("button", { name: i18n.t("analysisRules.dashboard.aiJobs.change") }));
    await waitFor(() => expect(api.put).toHaveBeenCalledWith("/super-admin/ai-jobs/secretary_intent", { choice_id: 18 }));
  });

  it("shows name, ID or unknown for who changed", async () => {
    mockGets();
    view();
    expect(await screen.findByText("Tanaka")).toBeTruthy();
    expect(screen.getByText(i18n.t("analysisRules.dashboard.aiJobs.userId", { id: 8 }))).toBeTruthy();
    expect(screen.getByText(i18n.t("analysisRules.dashboard.aiJobs.unknownUser"))).toBeTruthy();
  });

  it("has ja and en keys for every job, provider, login reason and error code (K7)", () => {
    const keys = [
      ...JOB_KEYS.map((k) => `analysisRules.dashboard.aiJobs.job.${k}`),
      ...PROVIDERS.map((k) => `analysisRules.dashboard.aiJobs.provider.${k}`),
      ...LOGIN_REASONS.map((k) => `analysisRules.dashboard.aiJobs.loginReason.${k}`),
      ...ERROR_CODES.map((k) => `analysisRules.dashboard.aiJobs.errorCode.${k}`),
    ];
    for (const lng of ["ja", "en"]) {
      const missing = keys.filter((k) => !i18n.exists(k, { lng }));
      expect(missing).toEqual([]);
    }
  });

  it("uses 8 columns with role wording and puts the change button in the 4th cell (ja)", async () => {
    await i18n.changeLanguage("ja");
    mockGets(JOB_KEYS.map((k) => (k === "secretary_intent" ? job(k, { count_24h: 70, failed_24h: 0 }) : job(k))));
    view();
    await screen.findAllByText(i18n.t("analysisRules.dashboard.aiJobs.job.secretary_intent"));
    const table = screen.getAllByRole("table")[0];
    const headers = within(table).getAllByRole("columnheader");
    expect(headers).toHaveLength(8);
    const headerTexts = headers.map((h) => h.textContent);
    expect(headerTexts[0]).toBe(i18n.t("analysisRules.dashboard.aiJobs.colJob"));
    expect(headerTexts).toContain(i18n.t("analysisRules.dashboard.aiJobs.colAiModel"));
    expect(headerTexts).toContain(i18n.t("analysisRules.dashboard.aiJobs.col24h"));
    expect(table.textContent).not.toContain(String.fromCharCode(0x4ed5, 0x4e8b));
    const row = within(table).getAllByRole("row").find((r) => within(r).queryByRole("button", { name: i18n.t("analysisRules.dashboard.aiJobs.change") }));
    expect(row).toBeTruthy();
    const cells = within(row as HTMLElement).getAllByRole("cell");
    expect(within(cells[3]).getByRole("button", { name: i18n.t("analysisRules.dashboard.aiJobs.change") })).toBeTruthy();
    expect(cells[5].textContent).toBe(i18n.t("analysisRules.dashboard.aiJobs.count24h", { count: 70, failed: 0 }))
    expect(cells[5].textContent).toMatch(/^70 .+0.$/);
    expect(cells[1].textContent).toBe(i18n.t("analysisRules.dashboard.aiJobs.choiceLabel", { provider: "Claude", model: "sonnet" }));
  });

  it("shows calls in en as '70 calls (0 failed)'", async () => {
    mockGets(JOB_KEYS.map((k) => (k === "secretary_intent" ? job(k, { count_24h: 70, failed_24h: 0 }) : job(k))));
    view();
    expect(await screen.findByText("70 calls (0 failed)")).toBeTruthy();
  });

  it("has ja and en keys for the merged column labels", () => {
    const keys = ["colAiModel", "col24h", "count24h"].map((k) => `analysisRules.dashboard.aiJobs.${k}`);
    for (const lng of ["ja", "en"]) {
      expect(keys.filter((k) => !i18n.exists(k, { lng }))).toEqual([]);
    }
  });
});
