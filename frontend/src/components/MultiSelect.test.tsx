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
});
