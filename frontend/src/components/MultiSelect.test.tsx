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

  it("A20: layout omitted (default) stays popover: button renders and the --popover modifier classes are used once opened", () => {
    // layout 省略時が今までどおり popover であることの固定（docs/handoff/viewer-filter-subscreen/design.md §4-1）
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

    it("resolves selected names from allOptions even when options is narrowed by search (design.md 4-2, review item 6)", () => {
      // options は検索で絞られた1件だけ。allOptions には全件を渡す。
      render(
        <MultiSelect
          layout="inline"
          label="Supplier"
          options={[OPTIONS[1]]}
          allOptions={OPTIONS}
          selected={["a", "b"]}
          onChange={vi.fn()}
          clearLabel="Clear"
          allLabel="All"
          countLabel={(n) => `${n} selected`}
          testId="ms"
        />,
      );
      // "a" (Alpha) は絞り込まれた options には無いが、allOptions から正しく解決される
      expect(screen.getByText("Alpha, Beta")).toBeTruthy();
    });

    it("falls back to options when allOptions is omitted, and to the raw value when the name cannot be resolved at all", () => {
      render(
        <MultiSelect
          layout="inline"
          label="Supplier"
          options={[OPTIONS[1]]}
          selected={["a", "zzz"]}
          onChange={vi.fn()}
          clearLabel="Clear"
          allLabel="All"
          countLabel={(n) => `${n} selected`}
          testId="ms"
        />,
      );
      // allOptions 省略時は options のみから解決するため、絞られて消えた "a" は生の値のまま
      expect(screen.getByText("a, zzz")).toBeTruthy();
    });

    it("shows emptyLabel instead of the list when options is empty (design.md 4-2, review item 7)", () => {
      render(
        <MultiSelect
          layout="inline"
          label="Supplier"
          options={[]}
          selected={[]}
          onChange={vi.fn()}
          clearLabel="Clear"
          allLabel="All"
          countLabel={(n) => `${n} selected`}
          emptyLabel="No matches"
          testId="ms"
        />,
      );
      expect(screen.getByText("No matches")).toBeTruthy();
      expect(document.querySelectorAll(".comp-multiselect__option--inline")).toHaveLength(0);
    });
  });

  describe("layout=\"row\"", () => {
    function setupRow(selected: string[], onOpen = vi.fn()) {
      render(
        <MultiSelect
          layout="row"
          label="Supplier"
          options={OPTIONS}
          selected={selected}
          onChange={vi.fn()}
          clearLabel="Clear"
          allLabel="All"
          countLabel={(n) => `${n} selected`}
          testId="ms"
          onOpen={onOpen}
        />,
      );
      return onOpen;
    }

    it("renders a single button row with testid `${testId}-row`, no popover button and no checkboxes", () => {
      setupRow([]);
      expect(screen.getByTestId("ms-row")).toBeTruthy();
      expect(screen.queryByTestId("ms-button")).toBeNull();
      expect(screen.queryByTestId("ms-option-a")).toBeNull();
    });

    it("shows allLabel as the current value for 0 selected, and the comma-joined names for 1+", () => {
      setupRow([]);
      expect(screen.getByTestId("ms-row").textContent).toContain("All");
      cleanup();
      setupRow(["b", "a"]);
      expect(screen.getByTestId("ms-row").textContent).toContain("Beta, Alpha");
    });

    it("calls onOpen when clicked, and never calls onChange", () => {
      const onChange = vi.fn();
      const onOpen = vi.fn();
      render(
        <MultiSelect
          layout="row"
          label="Supplier"
          options={OPTIONS}
          selected={[]}
          onChange={onChange}
          clearLabel="Clear"
          allLabel="All"
          countLabel={(n) => `${n} selected`}
          testId="ms"
          onOpen={onOpen}
        />,
      );
      fireEvent.click(screen.getByTestId("ms-row"));
      expect(onOpen).toHaveBeenCalledTimes(1);
      expect(onChange).not.toHaveBeenCalled();
    });

    it("resolves the current value from allOptions, not the narrowed options", () => {
      render(
        <MultiSelect
          layout="row"
          label="Supplier"
          options={[OPTIONS[1]]}
          allOptions={OPTIONS}
          selected={["a", "b"]}
          onChange={vi.fn()}
          clearLabel="Clear"
          allLabel="All"
          countLabel={(n) => `${n} selected`}
          testId="ms"
          onOpen={() => undefined}
        />,
      );
      expect(screen.getByTestId("ms-row").textContent).toContain("Alpha, Beta");
    });
  });
});
