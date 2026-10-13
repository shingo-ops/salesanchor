import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { DataTable, type DataTableColumn } from "./DataTable";

afterEach(cleanup);

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
