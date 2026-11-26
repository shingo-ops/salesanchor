import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CountryCombobox } from "./CountryCombobox";

const apiMock = vi.hoisted(() => ({
  get: vi.fn(),
}));
vi.mock("../lib/api", () => ({ api: apiMock }));

apiMock.get.mockResolvedValue([
  { code: "JP", name: "Japan", dial_code: "+81", is_active: true },
  { code: "US", name: "United States", dial_code: "+1", is_active: true },
]);

afterEach(() => cleanup());

const noop = () => {};

describe("CountryCombobox label / error", () => {
  it("T1: label with required shows one required mark and labels the input", async () => {
    const { container } = render(<CountryCombobox id="c" label="Country" required value="" onChange={noop} />);
    await waitFor(() => expect(apiMock.get).toHaveBeenCalled());
    expect(container.querySelectorAll(".comp-field__label").length).toBe(1);
    expect(container.querySelectorAll(".comp-field__required").length).toBe(1);
    expect(screen.getByLabelText(/^Country\*?$/)).toBeTruthy();
  });

  it("T2: label without required shows no required mark", async () => {
    const { container } = render(<CountryCombobox id="c" label="Country" value="" onChange={noop} />);
    await waitFor(() => expect(apiMock.get).toHaveBeenCalled());
    expect(container.querySelectorAll(".comp-field__label").length).toBe(1);
    expect(container.querySelectorAll(".comp-field__required").length).toBe(0);
  });

  it("T3: without label and error the original markup is kept", async () => {
    const { container } = render(<CountryCombobox id="c" value="" onChange={noop} />);
    await waitFor(() => expect(apiMock.get).toHaveBeenCalled());
    expect(container.querySelector(".comp-field")).toBeNull();
    expect(container.querySelectorAll("label").length).toBe(0);
  });

  it("T4: error is shown in a role=alert line", async () => {
    render(<CountryCombobox id="c" label="Country" error="Required" value="" onChange={noop} />);
    await waitFor(() => expect(apiMock.get).toHaveBeenCalled());
    const alerts = screen.getAllByRole("alert");
    expect(alerts.length).toBe(1);
    expect(alerts[0].textContent).toBe("Required");
  });
});
