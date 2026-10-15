import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { DataTable, type DataTableColumn } from "./DataTable";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

interface Row {
  id: string;
  name: string;
  qty: number;
}
const DATA: Row[] = [
  { id: "1", name: "Alpha", qty: 3 },
  { id: "2", name: "Beta", qty: 5 },
];
const COLS: DataTableColumn<Row>[] = [
  { key: "name", header: "Name" },
  { key: "qty", header: "Qty" },
];

function mockMatchMedia(mobile: boolean) {
  vi.stubGlobal(
    "matchMedia",
    vi.fn((q: string) => ({
      matches: q.includes("max-width") ? mobile : !mobile,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })),
  );
}

describe("DataTable defaults (no new props)", () => {
  it("keeps the original DOM: region wrapper holds table and pagination", () => {
    const { container } = render(
      <DataTable<Row> columns={COLS} data={DATA} rowKey={(r) => r.id} onPageChange={() => {}} />,
    );
    const root = container.firstElementChild as HTMLElement;
    expect(root.className).toBe("comp-table comp-table--default");
    expect(root.getAttribute("role")).toBe("region");
    expect(root.querySelector(":scope > table.comp-table__table")).not.toBeNull();
    expect(root.querySelector(":scope > .comp-table__pagination")).not.toBeNull();
    expect(container.querySelector(".comp-table-frame, .comp-table-fit__card, .comp-table--sticky")).toBeNull();
    expect(container.querySelector("th")!.className).toBe("comp-table__th");
    expect(container.querySelector("td")!.className).toBe("comp-table__td");
  });
});

describe("DataTable testid / pagination", () => {
  it("puts rowTestId on each tr", () => {
    render(<DataTable<Row> columns={COLS} data={DATA} rowKey={(r) => r.id} rowTestId={(r) => `row-${r.id}`} />);
    expect(screen.getByTestId("row-1").tagName).toBe("TR");
    expect(screen.getByTestId("row-2").tagName).toBe("TR");
  });

  it("puts paginationTestIds on prev, next and label", () => {
    render(
      <DataTable<Row>
        columns={COLS}
        data={DATA}
        rowKey={(r) => r.id}
        page={2}
        hasNextPage
        onPageChange={() => {}}
        paginationTestIds={{ prev: "p-prev", next: "p-next", label: "p-label" }}
      />,
    );
    expect((screen.getByTestId("p-prev") as HTMLButtonElement).disabled).toBe(false);
    expect((screen.getByTestId("p-next") as HTMLButtonElement).disabled).toBe(false);
    expect(screen.getByTestId("p-label").textContent).toBe("2");
  });

  it("paginationDisabled disables both buttons", () => {
    render(
      <DataTable<Row>
        columns={COLS}
        data={DATA}
        rowKey={(r) => r.id}
        page={2}
        hasNextPage
        onPageChange={() => {}}
        paginationDisabled
        paginationTestIds={{ prev: "p-prev", next: "p-next", label: "p-label" }}
      />,
    );
    expect((screen.getByTestId("p-prev") as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByTestId("p-next") as HTMLButtonElement).disabled).toBe(true);
  });

  it("prev stays disabled on page 1 and next on no next page", () => {
    render(
      <DataTable<Row>
        columns={COLS}
        data={DATA}
        rowKey={(r) => r.id}
        onPageChange={() => {}}
        paginationTestIds={{ prev: "p-prev", next: "p-next", label: "p-label" }}
      />,
    );
    expect((screen.getByTestId("p-prev") as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByTestId("p-next") as HTMLButtonElement).disabled).toBe(true);
  });
});

describe("DataTable align", () => {
  it("adds align classes to th and td", () => {
    const { container } = render(
      <DataTable<Row>
        columns={[{ key: "name", header: "Name", align: "right" }, { key: "qty", header: "Qty", align: "center" }]}
        data={DATA}
        rowKey={(r) => r.id}
      />,
    );
    const ths = container.querySelectorAll("th");
    expect(ths[0].classList.contains("comp-table__cell--align-right")).toBe(true);
    expect(ths[1].classList.contains("comp-table__cell--align-center")).toBe(true);
    expect(container.querySelector("td")!.classList.contains("comp-table__cell--align-right")).toBe(true);
  });
});

describe("DataTable stickyHeader / stickyLeft", () => {
  it("renders frame > scroll box(--sticky) > table, with pagination outside the scroll box", () => {
    const { container } = render(
      <DataTable<Row>
        columns={[{ key: "name", header: "Name", stickyLeft: true }, { key: "qty", header: "Qty" }]}
        data={DATA}
        rowKey={(r) => r.id}
        stickyHeader
        onPageChange={() => {}}
      />,
    );
    const frame = container.firstElementChild as HTMLElement;
    expect(frame.className).toBe("comp-table-frame");
    expect(frame.getAttribute("role")).toBe("region");
    const scroll = frame.querySelector(":scope > .comp-table.comp-table--sticky") as HTMLElement;
    expect(scroll).not.toBeNull();
    expect(scroll.querySelector("table")).not.toBeNull();
    expect(scroll.querySelector(".comp-table__pagination")).toBeNull();
    expect(frame.querySelector(":scope > .comp-table__pagination")).not.toBeNull();
    expect(container.querySelector("th")!.classList.contains("comp-table__cell--sticky-left")).toBe(true);
    expect(container.querySelector("td")!.classList.contains("comp-table__cell--sticky-left")).toBe(true);
  });

  it("uses sticky-check and sticky-left-after-check when selectable", () => {
    const { container } = render(
      <DataTable<Row>
        columns={[{ key: "name", header: "Name", stickyLeft: true }, { key: "qty", header: "Qty" }]}
        data={DATA}
        rowKey={(r) => r.id}
        stickyHeader
        selectable
      />,
    );
    const ths = container.querySelectorAll("th");
    expect(ths[0].classList.contains("comp-table__cell--sticky-check")).toBe(true);
    expect(ths[1].classList.contains("comp-table__cell--sticky-left-after-check")).toBe(true);
    expect(ths[2].className).toBe("comp-table__th");
  });

  it("fitToWidth adds the fit card between frame and scroll box (no --sticky)", () => {
    const { container } = render(
      <DataTable<Row> columns={COLS} data={DATA} rowKey={(r) => r.id} fitToWidth />,
    );
    const frame = container.firstElementChild as HTMLElement;
    expect(frame.className).toBe("comp-table-frame");
    const card = frame.querySelector(":scope > .comp-table-fit__card") as HTMLElement;
    expect(card).not.toBeNull();
    expect(card.querySelector(":scope > .comp-table")).not.toBeNull();
    expect(container.querySelector(".comp-table--sticky")).toBeNull();
  });
});

describe("DataTable mobileCards", () => {
  const CARD_COLS: DataTableColumn<Row>[] = [
    { key: "name", header: "Name", mobileOrder: 2 },
    { key: "qty", header: "Qty", mobileOrder: 1, mobileLabel: "Quantity" },
    { key: "hid", header: "Hidden", mobileHidden: true, renderCell: () => "secret" },
    { key: "tail", header: "Tail", renderCell: () => "t" },
  ];

  it("renders cards in mobileOrder, hides mobileHidden, shows labels and rowTestId", () => {
    mockMatchMedia(true);
    const { container } = render(
      <DataTable<Row>
        columns={CARD_COLS}
        data={DATA}
        rowKey={(r) => r.id}
        mobileCards
        stickyHeader
        rowTestId={(r) => `card-${r.id}`}
      />,
    );
    expect(container.querySelector("table")).toBeNull();
    const list = container.querySelector(".comp-table-cards") as HTMLElement;
    expect(list.getAttribute("role")).toBe("list");
    const card = screen.getByTestId("card-1");
    expect(card.getAttribute("role")).toBe("listitem");
    const labels = [...card.querySelectorAll(".comp-table__card-label")].map((e) => e.textContent);
    expect(labels).toEqual(["Quantity", "Name", "Tail"]);
    const values = [...card.querySelectorAll(".comp-table__card-value")].map((e) => e.textContent);
    expect(values).toEqual(["3", "Alpha", "t"]);
    expect(card.textContent).not.toContain("secret");
  });

  it("keeps the table when not mobile", () => {
    mockMatchMedia(false);
    const { container } = render(
      <DataTable<Row> columns={CARD_COLS} data={DATA} rowKey={(r) => r.id} mobileCards />,
    );
    expect(container.querySelector("table")).not.toBeNull();
    expect(container.querySelector(".comp-table-cards")).toBeNull();
  });
});
