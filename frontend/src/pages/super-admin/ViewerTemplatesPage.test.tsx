import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api, ApiError } from "../../lib/api";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import i18n from "../../i18n";
import ViewerTemplatesPage from "./ViewerTemplatesPage";

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../../lib/api")>("../../lib/api");
  return { ...actual, api: { get: vi.fn(), put: vi.fn() } };
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
  expect(body.readOnly).toBe(false);

  fireEvent.click(screen.getByTestId("viewer-templates-copy"));
  await waitFor(() => expect(writeText).toHaveBeenCalledWith("copy-reissue_notice"));
});

it("shows the unregistered label and disables copy when the body is null", async () => {
  renderPage();
  const name = await screen.findByText(i18n.t("superAdmin.viewerTemplates.names.notice_suspended"));
  fireEvent.click(name.closest("tr") as HTMLElement);
  await screen.findByTestId("viewer-templates-detail");
  expect(screen.getByTestId("viewer-templates-unregistered").textContent).toBe("Not registered");
  expect((screen.getByTestId("viewer-templates-body") as HTMLTextAreaElement).value).toBe("");
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

async function openRow(key: string) {
  const name = await screen.findByText(i18n.t(`superAdmin.viewerTemplates.names.${key}`));
  fireEvent.click(name.closest("tr") as HTMLElement);
  await screen.findByTestId("viewer-templates-detail");
}

function edit(value: string) {
  fireEvent.change(screen.getByTestId("viewer-templates-body"), { target: { value } });
}

it("saves an edit with the opened updated_at, shows saved, and refreshes the list", async () => {
  const saved = { ...ITEMS[4], body: "new body", copy_text: "new copy", updated_at: "2026-10-21T00:00:00Z" };
  vi.mocked(api.put).mockResolvedValue(saved);
  vi.mocked(api.get)
    .mockResolvedValueOnce({ items: ITEMS })
    .mockResolvedValueOnce({ items: ITEMS })
    .mockResolvedValueOnce({ items: ITEMS.map(i => (i.key === "room_recreated" ? saved : i)) });
  renderPage();
  await openRow("room_recreated");
  edit("new body");
  fireEvent.click(screen.getByTestId("viewer-templates-save"));
  expect((await screen.findByTestId("viewer-templates-saved")).textContent).toBe("Saved");
  expect(api.put).toHaveBeenCalledWith("/super-admin/viewer-templates/room_recreated", {
    body: "new body",
    expected_updated_at: "2026-10-20T00:00:00Z",
  });
  await waitFor(() => expect(api.get).toHaveBeenCalledTimes(3));
  expect((screen.getByTestId("viewer-templates-body") as HTMLTextAreaElement).value).toBe("new body");
  fireEvent.click(screen.getByTestId("viewer-templates-copy"));
  await waitFor(() => expect(writeText).toHaveBeenCalledWith("new copy"));
});

it("saves an unregistered row with expected_updated_at null", async () => {
  vi.mocked(api.put).mockResolvedValue({ ...ITEMS[7], body: "hello", copy_text: null, updated_at: "2026-10-21T00:00:00Z" });
  renderPage();
  await openRow("notice_suspended");
  edit("hello");
  fireEvent.click(screen.getByTestId("viewer-templates-save"));
  await screen.findByTestId("viewer-templates-saved");
  expect(api.put).toHaveBeenCalledWith("/super-admin/viewer-templates/notice_suspended", {
    body: "hello",
    expected_updated_at: null,
  });
});

it("shows the conflict message on 409", async () => {
  vi.mocked(api.put).mockRejectedValue(new ApiError("template_conflict", 409, "template_conflict"));
  renderPage();
  await openRow("room_recreated");
  edit("x");
  fireEvent.click(screen.getByTestId("viewer-templates-save"));
  expect((await screen.findByTestId("viewer-templates-save-error")).textContent).toBe(
    i18n.t("superAdmin.viewerTemplates.conflict"),
  );
  expect(screen.queryByTestId("viewer-templates-saved")).toBeNull();
});

it.each([
  ["template_placeholders", "errorPlaceholders"],
  ["template_bad_syntax", "errorBadSyntax"],
  ["template_format_spec", "errorFormatSpec"],
  ["template_empty", "errorEmpty"],
  ["template_too_long", "errorTooLong"],
  ["template_line_name_prefix", "errorLineNamePrefix"],
])("shows the reason for the 422 code %s", async (code, key) => {
  vi.mocked(api.put).mockRejectedValue(new ApiError(code, 422, code));
  renderPage();
  await openRow("room_recreated");
  edit("x");
  fireEvent.click(screen.getByTestId("viewer-templates-save"));
  expect((await screen.findByTestId("viewer-templates-save-error")).textContent).toBe(
    i18n.t(`superAdmin.viewerTemplates.${key}`),
  );
});

it("shows the generic save error for other failures", async () => {
  vi.mocked(api.put).mockRejectedValue(new ApiError("boom", 500, "boom"));
  renderPage();
  await openRow("room_recreated");
  edit("x");
  fireEvent.click(screen.getByTestId("viewer-templates-save"));
  expect((await screen.findByTestId("viewer-templates-save-error")).textContent).toBe("Could not save");
});

it("shows the character count by code points and keeps save disabled until edited", async () => {
  renderPage();
  await openRow("room_recreated");
  expect((screen.getByTestId("viewer-templates-save") as HTMLButtonElement).disabled).toBe(true);
  edit("a\u{1F600}b");
  expect(screen.getByText("3 / 1800")).toBeTruthy();
  expect((screen.getByTestId("viewer-templates-save") as HTMLButtonElement).disabled).toBe(false);
});

it("after a 409, closing and reopening the row sends the newest updated_at", async () => {
  const newer = { ...ITEMS[4], body: "someone else", copy_text: "c", updated_at: "2026-10-21T01:00:00Z" };
  vi.mocked(api.get)
    .mockResolvedValueOnce({ items: ITEMS }) // initial
    .mockResolvedValueOnce({ items: ITEMS }) // first open
    .mockResolvedValueOnce({ items: ITEMS.map(i => (i.key === "room_recreated" ? newer : i)) }) // after 409
    .mockResolvedValueOnce({ items: ITEMS.map(i => (i.key === "room_recreated" ? newer : i)) }); // second open
  vi.mocked(api.put)
    .mockRejectedValueOnce(new ApiError("template_conflict", 409, "template_conflict"))
    .mockResolvedValueOnce({ ...newer, body: "mine" });
  renderPage();
  await openRow("room_recreated");
  edit("mine");
  fireEvent.click(screen.getByTestId("viewer-templates-save"));
  await screen.findByTestId("viewer-templates-save-error");
  // typed text is kept after the 409
  expect((screen.getByTestId("viewer-templates-body") as HTMLTextAreaElement).value).toBe("mine");
  await waitFor(() => expect(api.get).toHaveBeenCalledTimes(3));
  // close and reopen
  const name = screen.getAllByText(i18n.t("superAdmin.viewerTemplates.names.room_recreated"))[0];
  fireEvent.click(name.closest("tr") as HTMLElement);
  await waitFor(() => expect(api.get).toHaveBeenCalledTimes(4));
  await waitFor(() =>
    expect((screen.getByTestId("viewer-templates-body") as HTMLTextAreaElement).value).toBe("someone else"),
  );
  edit("mine");
  fireEvent.click(screen.getByTestId("viewer-templates-save"));
  await screen.findByTestId("viewer-templates-saved");
  expect(vi.mocked(api.put).mock.calls[1][1]).toEqual({ body: "mine", expected_updated_at: "2026-10-21T01:00:00Z" });
});
