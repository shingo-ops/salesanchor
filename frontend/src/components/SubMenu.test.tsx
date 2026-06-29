import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { SubMenu } from "./SubMenu";
import type { SubMenuGroup } from "./SubMenu";

describe("SubMenu", () => {
  it("door item navigates", () => {
    const groups: SubMenuGroup[] = [
      { items: [{ key: "staff", label: "Staff", to: "/mc/staff" }] },
    ];
    render(
      <MemoryRouter initialEntries={["/mc"]}>
        <Routes>
          <Route
            path="/mc"
            element={
              <SubMenu groups={groups} activeKey="staff" onChange={() => {}} />
            }
          />
          <Route path="/mc/staff" element={<div>STAFF_PAGE</div>} />
        </Routes>
      </MemoryRouter>,
    );
    const link = screen.getByRole("link", { name: "Staff" });
    expect(link.getAttribute("href")).toBe("/mc/staff");
    fireEvent.click(link);
    expect(screen.getByText("STAFF_PAGE")).toBeTruthy();
  });

  it("remote item calls onChange", () => {
    const onChange = vi.fn();
    const groups: SubMenuGroup[] = [
      { items: [{ key: "leads", label: "Leads" }] },
    ];
    render(
      <MemoryRouter>
        <SubMenu groups={groups} activeKey="leads" onChange={onChange} />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Leads" }));
    expect(onChange).toHaveBeenCalledWith("leads");
  });
});
