import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { createInstance } from "i18next";
import { I18nextProvider } from "react-i18next";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import StaffPage from "./StaffPage";
import { UiPrefsProvider } from "../../contexts/UiPrefsContext";
import en from "../../locales/en.json";
import { queryClient } from "../../lib/query/apiQuery";

const mock = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
  user: { uid: "fixture-user" },
}));
vi.mock("../../lib/api", () => ({ api: mock }));
vi.mock("../../contexts/AuthContext", () => ({ useAuth: () => ({ user: mock.user, loading: false }) }));

let instance = createInstance();
const tr = (key: string) => String(instance.t(key));
let writeText: ReturnType<typeof vi.fn>;
let permissions: string[];

const URL_1 = "https://app.example.test/staff-join#k=1.fixturekey";
const URL_2 = "https://app.example.test/staff-join#k=1.reissuedkey";
const roles = [{ id: 2, name: "Fixture role" }];
const invites = [
  { id: 11, status: "open", role_id: 2, role_name: "Fixture role", expires_at: "2030-01-01T00:00:00Z", created_at: null, created_by: 1, created_by_name: "Fixture admin" },
  { id: 12, status: "submitted", role_id: 2, role_name: "Fixture role", expires_at: "2030-01-02T00:00:00Z", created_at: null, created_by: 1, created_by_name: "Fixture admin" },
];

function mount() {
  render(
    <I18nextProvider i18n={instance}>
      <MemoryRouter initialEntries={["/staff"]}>
        <UiPrefsProvider>
          <StaffPage />
        </UiPrefsProvider>
      </MemoryRouter>
    </I18nextProvider>,
  );
}

beforeEach(async () => {
  vi.resetAllMocks();
  permissions = ["staff.create", "staff.update", "staff.delete"];
  writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
  instance = createInstance();
  await instance.init({ lng: "en", resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  mock.get.mockImplementation(async (url: string) => {
    if (url === "/staff/me") throw new Error("Fixture staff unlinked");
    if (url === "/staff") return [];
    if (url === "/roles") return roles;
    if (url === "/me/permissions") return { permissions };
    if (url === "/staff/join-invites") return invites;
    throw new Error("Unexpected GET " + url);
  });
  mock.post.mockImplementation(async (url: string) => {
    if (url === "/staff/join-invites") return { id: 11, url: URL_1, expires_at: "2030-01-01T00:00:00Z" };
    if (url === "/staff/join-invites/11/reissue") return { id: 11, url: URL_2, expires_at: "2030-01-04T00:00:00Z" };
    if (url === "/staff/join-invites/11/revoke") return { id: 11, status: "revoked" };
    throw new Error("Unexpected POST " + url);
  });
});
afterEach(() => {
  cleanup();
  queryClient.clear();
  vi.restoreAllMocks();
});

describe("StaffPage invite link modals (ADR-1068)", () => {
  it("creating an invite shows a read-only url and a copy button that copies it", async () => {
    mount();
    fireEvent.click(await screen.findByRole("button", { name: tr("staff.join.createButton") }));
    const dialog = screen.getByRole("dialog", { name: tr("staff.join.createTitle") });

    fireEvent.change(within(dialog).getByLabelText(new RegExp(tr("staff.role"))), { target: { value: "2" } });
    fireEvent.click(within(dialog).getByRole("button", { name: tr("staff.join.create") }));

    const field = (await within(dialog).findByLabelText(tr("staff.join.inviteUrl"))) as HTMLInputElement;
    expect(mock.post).toHaveBeenCalledWith("/staff/join-invites", { role_id: 2 });
    expect(field.value).toBe(URL_1);
    expect(field.readOnly).toBe(true);
    fireEvent.click(within(dialog).getByRole("button", { name: tr("staff.join.copy") }));
    expect(writeText).toHaveBeenCalledWith(URL_1);
    expect(await within(dialog).findByRole("button", { name: tr("staff.join.copied") })).toBeTruthy();
  });

  it("the list shows reissue and revoke only on open rows; reissue shows the new url", async () => {
    mount();
    fireEvent.click(await screen.findByRole("button", { name: tr("staff.join.listButton") }));
    const dialog = await screen.findByRole("dialog", { name: tr("staff.join.listTitle") });
    await within(dialog).findByText(tr("staff.join.status_open"));

    expect(within(dialog).getAllByRole("button", { name: tr("staff.join.reissue") })).toHaveLength(1);
    expect(within(dialog).getAllByRole("button", { name: tr("staff.join.revoke") })).toHaveLength(1);
    expect(within(dialog).getByText(tr("staff.join.status_submitted"))).toBeTruthy();

    fireEvent.click(within(dialog).getByRole("button", { name: tr("staff.join.reissue") }));
    const field = (await within(dialog).findByLabelText(tr("staff.join.inviteUrl"))) as HTMLInputElement;
    expect(field.value).toBe(URL_2);
  });

  it("revoke asks for confirmation, then posts revoke", async () => {
    mount();
    fireEvent.click(await screen.findByRole("button", { name: tr("staff.join.listButton") }));
    const dialog = await screen.findByRole("dialog", { name: tr("staff.join.listTitle") });
    await within(dialog).findByText(tr("staff.join.status_open"));

    fireEvent.click(within(dialog).getByRole("button", { name: tr("staff.join.revoke") }));
    expect(mock.post).not.toHaveBeenCalledWith("/staff/join-invites/11/revoke", expect.anything());
    const confirm = await screen.findByRole("dialog", { name: tr("staff.join.revokeTitle") });
    fireEvent.click(within(confirm).getByRole("button", { name: tr("staff.join.revoke") }));

    await waitFor(() => expect(mock.post).toHaveBeenCalledWith("/staff/join-invites/11/revoke", {}));
  });

  it("people without staff.create do not see the invite buttons", async () => {
    permissions = ["staff.view"];
    mount();
    await waitFor(() => expect(mock.get).toHaveBeenCalledWith("/me/permissions"));
    await screen.findByText(tr("staff.noStaff"));

    expect(screen.queryByRole("button", { name: tr("staff.join.createButton") })).toBeNull();
    expect(screen.queryByRole("button", { name: tr("staff.join.listButton") })).toBeNull();
  });
});
