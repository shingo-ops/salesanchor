import { createRef } from "react";
import { createInstance } from "i18next";
import { I18nextProvider } from "react-i18next";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { PasswordFieldControl } from "./PasswordField";
import en from "../locales/en.json";

let instance = createInstance();

beforeEach(async () => {
  instance = createInstance();
  await instance.init({ lng: "en", resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
});

afterEach(cleanup);

function renderField(node: React.ReactNode) {
  return render(<I18nextProvider i18n={instance}>{node}</I18nextProvider>);
}

describe("PasswordFieldControl", () => {
  it("starts as type=password and toggles to text and back with the aria-label", () => {
    renderField(<PasswordFieldControl id="pw" aria-label="field" defaultValue="abc" />);
    const input = screen.getByLabelText("field", { exact: true }) as HTMLInputElement;
    expect(input.type).toBe("password");
    const toggle = screen.getByRole("button", { name: "Show password" });
    expect(toggle.hasAttribute("aria-pressed")).toBe(false);
    fireEvent.click(toggle);
    expect(input.type).toBe("text");
    expect(input.value).toBe("abc");
    fireEvent.click(screen.getByRole("button", { name: "Hide password" }));
    expect(input.type).toBe("password");
  });

  it("toggle is type=button and does not submit the form", () => {
    const submit = vi.fn((e: React.FormEvent) => e.preventDefault());
    renderField(<form onSubmit={submit}><PasswordFieldControl aria-label="field" /></form>);
    const toggle = screen.getByRole("button", { name: "Show password" });
    expect(toggle.getAttribute("type")).toBe("button");
    fireEvent.click(toggle);
    expect(submit).not.toHaveBeenCalled();
  });

  it("forwards ref to the input and passes className and variant through", () => {
    const ref = createRef<HTMLInputElement>();
    renderField(<PasswordFieldControl ref={ref} variant="login" className="extra" aria-label="field" />);
    const input = screen.getByLabelText("field", { exact: true });
    expect(ref.current).toBe(input);
    expect(input.classList.contains("comp-password-field__input")).toBe(true);
    expect(input.classList.contains("comp-input--login")).toBe(true);
    expect(input.classList.contains("extra")).toBe(true);
  });
});
