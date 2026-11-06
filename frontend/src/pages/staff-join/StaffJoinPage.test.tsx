import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createInstance } from "i18next";
import { I18nextProvider } from "react-i18next";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import en from "../../locales/en.json";

import StaffJoinPage from "./StaffJoinPage";

let instance = createInstance();
const tr = (key: string) => String(instance.t(key));
let fetchMock: ReturnType<typeof vi.fn>;
let writeText: ReturnType<typeof vi.fn>;

const KEY = "1.abcDEF_-0123456789abcdefghijklmnopqrstuvwxyz";
const INFO = { tenant_name: "Fixture Co", role_name: "Fixture role", expires_at: "2030-01-01T00:00:00Z" };
const CODE = "ABCD-EFGH-JKLM-NPQR";

function renderAt(url: string) {
  render(
    <I18nextProvider i18n={instance}>
      <MemoryRouter initialEntries={[url]}>
        <Routes>
          <Route path="/staff-join" element={<StaffJoinPage />} />
        </Routes>
      </MemoryRouter>
    </I18nextProvider>,
  );
}

function json(body: unknown, status: number) {
  return Promise.resolve(new Response(JSON.stringify(body), { status }));
}

function fill(label: string, value: string) {
  const el = screen
    .getAllByText((text, node) => node?.tagName === "LABEL" && (text === label || text === label + " *"))[0]
    .parentElement?.querySelector("input");
  if (!el) throw new Error("Missing field " + label);
  fireEvent.change(el, { target: { value } });
}

function fillAll() {
  fill(tr("staff.surnameJp"), "Fixture");
  fill(tr("staff.givenNameJp"), "Staff");
  fill(tr("staff.surnameEn"), "EnFixture");
  fill(tr("staff.givenNameEn"), "EnStaff");
  fill(tr("staff.primaryEmail"), "fixture@example.test");
}

beforeEach(async () => {
  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
  writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
  instance = createInstance();
  await instance.init({ lng: "en", resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("StaffJoinPage", () => {
  it("shows the unusable-link notice and no form on 404", async () => {
    fetchMock.mockImplementation(() => json({ detail: "staff_join_invalid" }, 404));
    renderAt(`/staff-join#k=${KEY}`);

    expect(await screen.findByText(tr("staffJoin.invalidTitle"))).toBeTruthy();
    expect(screen.getByText(tr("staffJoin.invalidBody"))).toBeTruthy();
    expect(screen.queryByRole("button", { name: tr("staffJoin.submit") })).toBeNull();
    expect(fetchMock.mock.calls[0][0]).toBe(`/api/v1/public/staff-join/${encodeURIComponent(KEY)}`);
  });

  it("without a key in the hash it shows the notice and does not call the API", () => {
    renderAt("/staff-join");

    expect(screen.getByText(tr("staffJoin.invalidTitle"))).toBeTruthy();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("submits the form, then shows the registration number, copy button, discord link and steps", async () => {
    fetchMock.mockImplementation((_url: string, init?: RequestInit) =>
      init?.method === "POST"
        ? json({ registration_code: CODE, discord_invite_url: "https://discord.gg/fixture" }, 200)
        : json(INFO, 200),
    );
    renderAt(`/staff-join#k=${KEY}`);

    expect(await screen.findByText("Company: Fixture Co")).toBeTruthy();
    fillAll();
    fireEvent.click(screen.getByRole("button", { name: tr("staffJoin.submit") }));

    expect(await screen.findByText(tr("staffJoin.doneTitle"))).toBeTruthy();
    const post = fetchMock.mock.calls.find((c) => c[1]?.method === "POST");
    expect(post?.[0]).toBe(`/api/v1/public/staff-join/${encodeURIComponent(KEY)}`);
    expect(JSON.parse(post?.[1].body)).toEqual({
      surname_jp: "Fixture",
      given_name_jp: "Staff",
      surname_kana: null,
      given_name_kana: null,
      surname_en: "EnFixture",
      given_name_en: "EnStaff",
      primary_email: "fixture@example.test",
    });
    expect((screen.getByLabelText(tr("staffJoin.codeLabel")) as HTMLInputElement).value).toBe(CODE);
    const link = screen.getByRole("link", { name: tr("staffJoin.discordJoin") });
    expect(link.getAttribute("href")).toBe("https://discord.gg/fixture");
    expect(screen.getAllByRole("listitem").map((li) => li.textContent)).toEqual([
      tr("staffJoin.step1"),
      tr("staffJoin.step2"),
      tr("staffJoin.step3"),
    ]);
  });

  it("copies the registration number as-is and shows the copied label", async () => {
    fetchMock.mockImplementation((_url: string, init?: RequestInit) =>
      init?.method === "POST" ? json({ registration_code: CODE, discord_invite_url: null }, 200) : json(INFO, 200),
    );
    renderAt(`/staff-join#k=${KEY}`);
    await screen.findByText("Company: Fixture Co");
    fillAll();
    fireEvent.click(screen.getByRole("button", { name: tr("staffJoin.submit") }));
    await screen.findByText(tr("staffJoin.doneTitle"));

    expect(screen.getByText(tr("staffJoin.discordLater"))).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: tr("staffJoin.copy") }));

    expect(writeText).toHaveBeenCalledWith(CODE);
    expect(await screen.findByRole("button", { name: tr("staffJoin.copied") })).toBeTruthy();
  });

  it("409 shows the returned message and 403 asks to contact the administrator", async () => {
    let status = 409;
    fetchMock.mockImplementation((_url: string, init?: RequestInit) =>
      init?.method === "POST" ? json({ detail: "Email unavailable (fixture)" }, status) : json(INFO, 200),
    );
    renderAt(`/staff-join#k=${KEY}`);
    await screen.findByText("Company: Fixture Co");
    fillAll();
    fireEvent.click(screen.getByRole("button", { name: tr("staffJoin.submit") }));
    expect(await screen.findByText("Email unavailable (fixture)")).toBeTruthy();

    status = 403;
    fireEvent.click(screen.getByRole("button", { name: tr("staffJoin.submit") }));
    await waitFor(() => expect(screen.getByText(tr("staffJoin.contactAdmin"))).toBeTruthy());
  });
});
