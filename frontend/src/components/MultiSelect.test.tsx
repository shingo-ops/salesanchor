import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MultiSelect } from "./MultiSelect";

afterEach(cleanup);

const OPTIONS = [
  { value: "a", label: "Alpha" },
  { value: "b", label: "Beta" },
  { value: "c", label: "Gamma" },
];

function setup(selected: string[], onChange = vi.fn()) {
  render(
    <MultiSelect
      label="Supplier"
      options={OPTIONS}
      selected={selected}
      onChange={onChange}
      clearLabel="Clear"
      allLabel="All"
      countLabel={(n) => `${n} selected`}
      testId="ms"
    />,
  );
  return onChange;
}

describe("MultiSelect", () => {
  it("shows 'label: all' for 0 selected", () => {
    setup([]);
    expect(screen.getByTestId("ms-button").textContent).toBe("Supplier: All");
  });

  it("shows the option label for 1 selected", () => {
    setup(["b"]);
    expect(screen.getByTestId("ms-button").textContent).toBe("Beta");
  });

  it("shows the count for 2 or more selected", () => {
    setup(["a", "c"]);
    expect(screen.getByTestId("ms-button").textContent).toBe("2 selected");
  });

  it("clear calls onChange with []", () => {
    const onChange = setup(["a", "b"]);
    fireEvent.click(screen.getByTestId("ms-button"));
    fireEvent.click(screen.getByTestId("ms-clear"));
    expect(onChange).toHaveBeenCalledWith([]);
  });

  it("checking adds and unchecking removes a value", () => {
    const onChange = vi.fn();
    function Wrapper() {
      const [sel, setSel] = useState<string[]>([]);
      return (
        <MultiSelect
          label="Supplier"
          options={OPTIONS}
          selected={sel}
          onChange={(n) => { onChange(n); setSel(n); }}
          clearLabel="Clear"
          allLabel="All"
          countLabel={(n) => `${n} selected`}
          testId="ms"
        />
      );
    }
    render(<Wrapper />);
    fireEvent.click(screen.getByTestId("ms-button"));
    fireEvent.click(screen.getByTestId("ms-option-a"));
    expect(onChange).toHaveBeenLastCalledWith(["a"]);
    fireEvent.click(screen.getByTestId("ms-option-c"));
    expect(onChange).toHaveBeenLastCalledWith(["a", "c"]);
    fireEvent.click(screen.getByTestId("ms-option-a"));
    expect(onChange).toHaveBeenLastCalledWith(["c"]);
  });

  it("layout omitted (default) stays popover: button renders and the --popover modifier classes are used once opened", () => {
    // layout 省略時が今までどおり popover であることの固定（design.md 4-1）
    setup([]);
    expect(screen.getByTestId("ms-button")).toBeTruthy();
    fireEvent.click(screen.getByTestId("ms-button"));
    expect(document.querySelector(".comp-multiselect__menu--popover")).toBeTruthy();
    expect(document.querySelector(".comp-multiselect__list--popover")).toBeTruthy();
  });

  describe("layout=\"inline\"", () => {
    function setupInline(selected: string[], onChange = vi.fn()) {
      render(
        <MultiSelect
          layout="inline"
          label="Supplier"
          options={OPTIONS}
          selected={selected}
          onChange={onChange}
          clearLabel="Clear"
          allLabel="All"
          countLabel={(n) => `${n} selected`}
          testId="ms"
        />,
      );
      return onChange;
    }

    it("renders no popover button, and one checkbox row per option", () => {
      setupInline([]);
      expect(screen.queryByTestId("ms-button")).toBeNull();
      for (const o of OPTIONS) {
        expect(screen.getByTestId(`ms-option-${o.value}`)).toBeTruthy();
      }
      expect(document.querySelectorAll(".comp-multiselect__option--inline")).toHaveLength(OPTIONS.length);
    });

    it("hides 'clear' when nothing is selected, shows it once something is", () => {
      setupInline([]);
      expect(screen.queryByTestId("ms-clear")).toBeNull();
      setupInline(["a"]);
      expect(screen.getByTestId("ms-clear")).toBeTruthy();
    });

    it("shows allLabel for 0 selected, and a comma-joined list of labels for 1+", () => {
      const { unmount } = render(
        <MultiSelect
          layout="inline"
          label="Supplier"
          options={OPTIONS}
          selected={[]}
          onChange={vi.fn()}
          clearLabel="Clear"
          allLabel="All"
          countLabel={(n) => `${n} selected`}
          testId="ms"
        />,
      );
      expect(screen.getByText("All")).toBeTruthy();
      unmount();

      setupInline(["b", "a"]);
      expect(screen.getByText("Beta, Alpha")).toBeTruthy();
    });

    it("checking an option calls onChange, clear calls onChange with []", () => {
      const onChange = setupInline(["a"]);
      fireEvent.click(screen.getByTestId("ms-option-c"));
      expect(onChange).toHaveBeenCalledWith(["a", "c"]);
      fireEvent.click(screen.getByTestId("ms-clear"));
      expect(onChange).toHaveBeenCalledWith([]);
    });
  });
});
