import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";

const mock = vi.hoisted(() => ({
  allowed: false,
  getVoice: vi.fn(),
  saveVoice: vi.fn(),
}));

vi.mock("../../contexts/ThemeContext", () => ({
  useTheme: () => ({ theme: "light", changeTheme: vi.fn() }),
}));
vi.mock("../../contexts/LocaleContext", () => ({
  useLocale: () => ({ locale: "en", changeLanguage: vi.fn() }),
}));
vi.mock("../../features/secretary/useSecretaryAccess", () => ({
  useSecretaryAccess: () => ({ ready: true, allowed: mock.allowed }),
}));
vi.mock("../../features/secretary/secretaryApi", () => ({
  getSecretaryVoice: mock.getVoice,
  saveSecretaryVoice: mock.saveVoice,
}));

import PreferencesSection from "./PreferencesSection";

const VOICES = {
  voices: ["Aoede", "Charon", "Erinome", "Zubenelgenubi"],
  default: "Charon",
  selected: "Charon",
};

beforeEach(async () => {
  mock.allowed = false;
  mock.getVoice.mockReset().mockResolvedValue(VOICES);
  mock.saveVoice.mockReset().mockResolvedValue({ ...VOICES, selected: "Aoede" });
  await i18n.changeLanguage("en");
});
afterEach(() => cleanup());

describe("PreferencesSection secretary voice", () => {
  it("has no voice row for someone who cannot see the secretary", () => {
    render(<PreferencesSection />);
    expect(screen.queryByLabelText(i18n.t("accountSettings.secretaryVoiceLabel"))).toBeNull();
    expect(mock.getVoice).not.toHaveBeenCalled();
  });

  it("shows 4 options with the saved voice selected", async () => {
    mock.allowed = true;
    render(<PreferencesSection />);
    const select = (await screen.findByLabelText(i18n.t("accountSettings.secretaryVoiceLabel"))) as HTMLSelectElement;
    expect(Array.from(select.options).map((o) => o.value)).toEqual(VOICES.voices);
    expect(select.value).toBe("Charon");
  });

  it("saves the new voice once when changed", async () => {
    mock.allowed = true;
    render(<PreferencesSection />);
    const select = (await screen.findByLabelText(i18n.t("accountSettings.secretaryVoiceLabel"))) as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "Aoede" } });
    await waitFor(() => expect(mock.saveVoice).toHaveBeenCalledTimes(1));
    expect(mock.saveVoice).toHaveBeenCalledWith("Aoede");
    await waitFor(() => expect(select.value).toBe("Aoede"));
  });
});
