import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { DataTable, type DataTableColumn } from "./DataTable";
import { useIsMobile } from "../hooks/useIsMobile";

vi.mock("../hooks/useIsMobile", () => ({ useIsMobile: vi.fn(() => false) }));

afterEach(() => {
  cleanup();
  vi.mocked(useIsMobile).mockReturnValue(false);
});

interface Row {
  id: string;
  name: string;
}
const DATA: Row[] = [{ id: "1", name: "very long product name" }];

const renderTable = (columns: DataTableColumn<Row>[]) =>
  render(<DataTable<Row> columns={columns} data={DATA} rowKey={(row) => row.id} />);

describe("DataTable ellipsis", () => {
  it("leaves the cell markup unchanged when ellipsis is not set", () => {
    renderTable([{ key: "name", header: "Name", width: "120px" }]);
    const td = document.querySelector("tbody td") as HTMLElement;
    expect(td.className).toBe("comp-table__td");
    expect(td.innerHTML).toBe("very long product name");
  });

  it("wraps the content in an ellipsis box with a title for string content", () => {
    renderTable([{ key: "name", header: "Name", ellipsis: true }]);
    const td = document.querySelector("tbody td") as HTMLElement;
    expect(td.className).toBe("comp-table__td comp-table__td--ellipsis");
    const box = td.querySelector(".comp-table__cell-ellipsis") as HTMLElement;
    expect(box.textContent).toBe("very long product name");
    expect(box.getAttribute("title")).toBe("very long product name");
  });

  it("keeps a var() width as max-width on the ellipsis box", () => {
    renderTable([{ key: "name", header: "Name", ellipsis: true, width: "var(--col-width-wide)" }]);
    const box = document.querySelector(".comp-table__cell-ellipsis") as HTMLElement;
    expect(box.style.maxWidth).toBe("var(--col-width-wide)");
  });

  it("sets no max-width inline when width is missing", () => {
    renderTable([{ key: "name", header: "Name", ellipsis: true }]);
    const box = document.querySelector(".comp-table__cell-ellipsis") as HTMLElement;
    expect(box.style.maxWidth).toBe("");
  });

  it("does not set a title when the content is not a string", () => {
    renderTable([{ key: "name", header: "Name", ellipsis: true, renderCell: (row) => <b>{row.name}</b> }]);
    const box = document.querySelector(".comp-table__cell-ellipsis") as HTMLElement;
    expect(box.hasAttribute("title")).toBe(false);
  });
});

describe("DataTable selection", () => {
  const TWO: Row[] = [
    { id: "1", name: "a" },
    { id: "2", name: "b" },
  ];
  const renderSelectable = (
    selected: Set<string>,
    onSelectChange: (keys: Set<string>) => void,
    mobileCards = false,
  ) =>
    render(
      <DataTable<Row>
        mobileCards={mobileCards}
        columns={[{ key: "name", header: "Name" }]}
        data={TWO}
        rowKey={(row) => row.id}
        selectable
        selectedKeys={selected}
        onSelectChange={onSelectChange}
      />,
    );

  it("selects all keys when the header checkbox is clicked with nothing selected", () => {
    const fn = vi.fn();
    renderSelectable(new Set(), fn);
    fireEvent.click(screen.getByLabelText("select all rows"));
    expect(fn).toHaveBeenCalledWith(new Set(["1", "2"]));
  });

  it("shows the header checkbox as indeterminate when only some rows are selected", () => {
    renderSelectable(new Set(["1"]), () => {});
    const head = screen.getByLabelText("select all rows") as HTMLInputElement;
    expect(head.checked).toBe(false);
    expect(head.indeterminate).toBe(true);
  });

  it("calls onSelectChange with a Set containing the row key when a row checkbox is clicked", () => {
    const fn = vi.fn();
    renderSelectable(new Set(), fn);
    fireEvent.click(screen.getByLabelText("select row 2"));
    expect(fn).toHaveBeenCalledWith(new Set(["2"]));
  });

  it("clears the selection when the header checkbox is clicked with everything selected", () => {
    const fn = vi.fn();
    renderSelectable(new Set(["1", "2"]), fn);
    fireEvent.click(screen.getByLabelText("select all rows"));
    expect(fn).toHaveBeenCalledWith(new Set());
  });

  it("uses the shared CheckboxControl for the row checkbox in card mode", () => {
    vi.mocked(useIsMobile).mockReturnValue(true);
    const fn = vi.fn();
    renderSelectable(new Set(), fn, true);
    expect(document.querySelector(".comp-table__card")).not.toBeNull();
    const box = screen.getByLabelText("select row 2") as HTMLInputElement;
    expect(box.classList.contains("comp-checkbox")).toBe(true);
    fireEvent.click(box);
    expect(fn).toHaveBeenCalledWith(new Set(["2"]));
  });
});
