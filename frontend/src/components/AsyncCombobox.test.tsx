import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AsyncCombobox, type AsyncComboboxOption } from "./AsyncCombobox";

const OPTIONS: AsyncComboboxOption[] = [
  { value: "u-1", label: "Alpha Box" },
  { value: "u-2", label: "Beta Box" },
];

function setup(overrides: Partial<React.ComponentProps<typeof AsyncCombobox>> = {}) {
  const loadOptions = vi.fn(async () => OPTIONS);
  const onSelect = vi.fn();
  render(
    <AsyncCombobox
      id="cb"
      ariaLabel="Product"
      value="Current"
      placeholder="Type"
      loadOptions={loadOptions}
      onSelect={onSelect}
      debounceMs={1}
      noResultsText="NO-RESULTS-TEXT"
      loadingText="LOADING-TEXT"
      {...overrides}
    />,
  );
  return { loadOptions, onSelect, input: screen.getByRole("combobox", { name: "Product" }) as HTMLInputElement };
}

afterEach(() => cleanup());

describe("AsyncCombobox", () => {
  it("shows the current value when closed and loads options with the trimmed text when typing", async () => {
    const { input, loadOptions } = setup();
    expect(input.value).toBe("Current");
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: " box " } });
    await screen.findByRole("option", { name: "Alpha Box" });
    expect(loadOptions).toHaveBeenCalledWith("box");
    expect(screen.getAllByRole("option")).toHaveLength(2);
  });

  it("does not call onSelect while typing, only when an option is chosen, then closes", async () => {
    const { input, onSelect } = setup();
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "box" } });
    fireEvent.click(await screen.findByRole("option", { name: "Beta Box" }));
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith({ value: "u-2", label: "Beta Box" });
    expect(screen.queryByRole("listbox")).toBeNull();
  });

  it("does not select anything for typed text alone", async () => {
    const { input, onSelect } = setup();
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "box" } });
    await screen.findByRole("option", { name: "Alpha Box" });
    expect(onSelect).not.toHaveBeenCalled();
  });

  it("moves with the arrow keys and selects with Enter", async () => {
    const { input, onSelect } = setup();
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "box" } });
    await screen.findByRole("option", { name: "Alpha Box" });
    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "ArrowDown" });
    expect(screen.getByRole("option", { name: "Beta Box" }).getAttribute("aria-selected")).toBe("true");
    fireEvent.keyDown(input, { key: "ArrowUp" });
    fireEvent.keyDown(input, { key: "ArrowUp" });
    expect(screen.getByRole("option", { name: "Beta Box" }).getAttribute("aria-selected")).toBe("true");
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onSelect).toHaveBeenCalledWith({ value: "u-2", label: "Beta Box" });
  });

  it("does not select when Enter confirms Japanese composition (isComposing)", async () => {
    const { input, onSelect } = setup();
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "box" } });
    await screen.findByRole("option", { name: "Alpha Box" });
    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "Enter", isComposing: true });
    fireEvent.keyDown(input, { key: "Enter", keyCode: 229 });
    expect(onSelect).not.toHaveBeenCalled();
    expect(screen.getByRole("listbox")).toBeTruthy();
  });

  it("does not select the first option on Enter when options only appeared", async () => {
    const { input, onSelect } = setup();
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "box" } });
    await screen.findByRole("option", { name: "Alpha Box" });
    expect(screen.getAllByRole("option").every((o) => o.getAttribute("aria-selected") === "false")).toBe(true);
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onSelect).not.toHaveBeenCalled();
  });

  it("selects with Enter after choosing an option by arrow key, and by click", async () => {
    const { input, onSelect } = setup();
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "box" } });
    await screen.findByRole("option", { name: "Alpha Box" });
    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onSelect).toHaveBeenCalledWith({ value: "u-1", label: "Alpha Box" });
  });

  it("does not point aria-controls at a missing list while closed", () => {
    const { input } = setup();
    expect(input.getAttribute("aria-controls")).toBeNull();
  });

  it("closes with Escape without selecting", async () => {
    const { input, onSelect } = setup();
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "box" } });
    await screen.findByRole("listbox");
    fireEvent.keyDown(input, { key: "Escape" });
    expect(screen.queryByRole("listbox")).toBeNull();
    expect(onSelect).not.toHaveBeenCalled();
  });

  it("shows the loading text while waiting and the no-results text for zero options, both from props", async () => {
    let resolve: (rows: AsyncComboboxOption[]) => void = () => undefined;
    const pending = new Promise<AsyncComboboxOption[]>((r) => { resolve = r; });
    const { input } = setup({ loadOptions: () => pending });
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "x" } });
    expect((await screen.findByRole("listbox")).textContent).toBe("LOADING-TEXT");
    resolve([]);
    await waitFor(() => expect(screen.getByRole("listbox").textContent).toBe("NO-RESULTS-TEXT"));
  });

  it("shows errorText when loading fails, falling back to the no-results text", async () => {
    const failing = vi.fn(async () => { throw new Error("boom"); });
    const { input } = setup({ loadOptions: failing, errorText: "ERROR-TEXT" });
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "x" } });
    await waitFor(() => expect(screen.getByRole("listbox").textContent).toBe("ERROR-TEXT"));
  });

  it("does not search below minChars", async () => {
    const { input, loadOptions } = setup({ minChars: 3 });
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "ab" } });
    await new Promise((r) => setTimeout(r, 20));
    expect(loadOptions).not.toHaveBeenCalled();
    expect(screen.queryByRole("listbox")).toBeNull();
  });

  it("ignores a stale response that arrives after a newer search", async () => {
    const resolvers: Array<(rows: AsyncComboboxOption[]) => void> = [];
    const load = vi.fn(() => new Promise<AsyncComboboxOption[]>((r) => { resolvers.push(r); }));
    const { input } = setup({ loadOptions: load });
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "a" } });
    await waitFor(() => expect(load).toHaveBeenCalledTimes(1));
    fireEvent.change(input, { target: { value: "ab" } });
    await waitFor(() => expect(load).toHaveBeenCalledTimes(2));
    resolvers[1]([{ value: "new", label: "New result" }]);
    await screen.findByRole("option", { name: "New result" });
    resolvers[0]([{ value: "old", label: "Old result" }]);
    await new Promise((r) => setTimeout(r, 10));
    expect(screen.queryByRole("option", { name: "Old result" })).toBeNull();
  });

  it("renders the list outside the input's container so a table cell cannot clip it", async () => {
    const { input } = setup();
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "box" } });
    const list = await screen.findByRole("listbox");
    expect(list.parentElement).toBe(document.body);
    expect(list.className).toContain("comp-async-combobox__list");
  });

  it("does not open when disabled", () => {
    const { input } = setup({ disabled: true });
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "box" } });
    expect(screen.queryByRole("listbox")).toBeNull();
  });
});
