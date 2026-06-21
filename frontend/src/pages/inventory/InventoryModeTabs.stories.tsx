import type { Meta, StoryObj } from "@storybook/react-vite";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import InventoryModeTabs from "./InventoryModeTabs";

const meta = {
  title: "Pages/Inventory/InventoryModeTabs",
  component: InventoryModeTabs,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
} satisfies Meta<typeof InventoryModeTabs>;

export default meta;
type Story = StoryObj<typeof meta>;

function withRouter(initialPath: string) {
  return (
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/inventory" element={<InventoryModeTabs />} />
        <Route path="/own-inventory" element={<InventoryModeTabs />} />
      </Routes>
    </MemoryRouter>
  );
}

export const WegoActive: Story = {
  name: "WEGO active",
  render: () => withRouter("/inventory"),
};

export const OwnActive: Story = {
  name: "自社 active",
  render: () => withRouter("/own-inventory"),
};
