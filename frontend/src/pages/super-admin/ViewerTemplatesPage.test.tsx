import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api } from "../../lib/api";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import i18n from "../../i18n";
import ViewerTemplatesPage from "./ViewerTemplatesPage";

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../../lib/api")>("../../lib/api");
  return { ...actual, api: { get: vi.fn() } };
});
vi.mock("../../hooks/useSuperAdmin", () => ({ useSuperAdmin: vi.fn() }));

const KEYS = [
  "signup_request", "reissue_notice", "reissue_notice_no_invite", "room_welcome", "room_recreated",
  "notice_extended", "notice_activated", "notice_suspended", "interview_request",
];
const PLACEHOLDERS: Record<string, string[]> = {
  signup_request: ["signup_url"],
  reissue_notice: ["line_name", "code", "expires", "invite_url"],
  reissue_notice_no_invite: ["line_name", "code", "expires"],
  room_welcome: ["email", "password"],
  room_recreated: ["email"],
  notice_extended: ["until_date"],
  notice_activated: [],
  notice_suspended: [],
  interview_request: ["expires_date"],
};
const MANUAL = ["signup_request", "reissue_notice", "reissue_notice_no_invite"];

const ITEMS = KEYS.map(key => ({
  key,
  body: key === "notice_suspended" ? null : `body-${key}\nline2`,
  copy_text: key === "notice_suspended" ? null : `copy-${key}`,
  placeholders: PLACEHOLDERS[key],
  send_mode: MANUAL.includes(key) ? "manual" : "auto",
  updated_at: key === "notice_suspended" ? null : "2026-10-20T00:00:00Z",
  updated_by_name: null,
}));

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/super-admin/viewer-templates"]}>
      <Routes>
        <Route path="/super-admin/viewer-templates" element={<ViewerTemplatesPage />} />
        <Route path="/super-admin/viewers" element={<div data-testid="viewers-page" />} />
      </Routes>
    </MemoryRouter>,
  );
}

const writeText = vi.fn();

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage("en");
  vi.mocked(useSuperAdmin).mockReturnValue({ loading: false, isSuperAdmin: true });
  vi.mocked(api.get).mockResolvedValue({ items: ITEMS });
  writeText.mockResolvedValue(undefined);
  Object.assign(navigator, { clipboard: { writeText } });
});
afterEach(() => cleanup());

it("shows only the access denied message for a non super admin and loads nothing", () => {
  vi.mocked(useSuperAdmin).mockReturnValue({ loading: false, isSuperAdmin: false });
  renderPage();
  expect(screen.getByText(i18n.t("superAdmin.accessDenied"))).toBeTruthy();
  expect(api.get).not.toHaveBeenCalled();
});

it("lists the nine templates in 4 columns", async () => {
  renderPage();
  await screen.findByText(i18n.t("superAdmin.viewerTemplates.names.signup_request"));
  expect(screen.getAllByRole("columnheader").map(h => h.textContent)).toEqual([
    "Name", "How it is sent", "When", "Last updated",
  ]);
  for (const key of KEYS) {
    expect(screen.getByText(i18n.t(`superAdmin.viewerTemplates.names.${key}`))).toBeTruthy();
  }
  expect(screen.getAllByRole("row").length).toBe(1 + KEYS.length);
  expect(api.get).toHaveBeenCalledWith("/super-admin/viewer-templates");
});

it("opens a drawer on row click with name, send mode, when, placeholders and body, and copies copy_text", async () => {
  renderPage();
  const name = await screen.findByText(i18n.t("superAdmin.viewerTemplates.names.reissue_notice"));
  fireEvent.click(name.closest("tr") as HTMLElement);
  const detail = await screen.findByTestId("viewer-templates-detail");
  expect(within(detail).getByText(i18n.t("superAdmin.viewerTemplates.names.reissue_notice"))).toBeTruthy();
  expect(within(detail).getByText(i18n.t("superAdmin.viewerTemplates.sendMode.manual"))).toBeTruthy();
  expect(within(detail).getByText(i18n.t("superAdmin.viewerTemplates.when.reissue_notice"))).toBeTruthy();
  const phs = within(screen.getByTestId("viewer-templates-placeholders")).getAllByRole("listitem");
  expect(phs.map(li => li.textContent)).toEqual([
    "{line_name} = LINE name",
    "{code} = Sign-up code",
    "{expires} = Sign-up code expiry (date and time)",
    "{invite_url} = Discord invite URL",
  ]);
  const body = screen.getByTestId("viewer-templates-body") as HTMLTextAreaElement;
  expect(body.value).toBe("body-reissue_notice\nline2");
  expect(body.readOnly).toBe(true);

  fireEvent.click(screen.getByTestId("viewer-templates-copy"));
  await waitFor(() => expect(writeText).toHaveBeenCalledWith("copy-reissue_notice"));
});

it("shows the unregistered label and disables copy when the body is null", async () => {
  renderPage();
  const name = await screen.findByText(i18n.t("superAdmin.viewerTemplates.names.notice_suspended"));
  fireEvent.click(name.closest("tr") as HTMLElement);
  await screen.findByTestId("viewer-templates-detail");
  expect(screen.getByTestId("viewer-templates-unregistered").textContent).toBe("Not registered");
  expect(screen.queryByTestId("viewer-templates-body")).toBeNull();
  expect((screen.getByTestId("viewer-templates-copy") as HTMLButtonElement).disabled).toBe(true);
  expect(screen.getByText("None")).toBeTruthy();
  fireEvent.click(screen.getByTestId("viewer-templates-copy"));
  expect(writeText).not.toHaveBeenCalled();
});

it("goes back to the viewer management page with the back button", async () => {
  renderPage();
  await screen.findByText(i18n.t("superAdmin.viewerTemplates.names.signup_request"));
  fireEvent.click(screen.getByText("Back to Viewer Management"));
  expect(await screen.findByTestId("viewers-page")).toBeTruthy();
});

it("shows an error message when loading fails", async () => {
  vi.mocked(api.get).mockRejectedValue(new Error("x"));
  renderPage();
  expect((await screen.findByTestId("viewer-templates-error")).textContent).toBe("Could not load the templates");
});
