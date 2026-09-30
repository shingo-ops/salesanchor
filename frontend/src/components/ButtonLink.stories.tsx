import type { Meta, StoryObj } from "@storybook/react-vite";
import { MemoryRouter } from "react-router-dom";
import { ButtonLink } from "./ButtonLink";

const meta: Meta<typeof ButtonLink> = {
  title: "Components/ButtonLink",
  component: ButtonLink,
  parameters: { layout: "padded" },
  tags: ["autodocs"],
  decorators: [(Story) => <MemoryRouter><Story /></MemoryRouter>],
};
export default meta;

type Story = StoryObj<typeof ButtonLink>;

export const RouterNavigation: Story = {
  args: { to: "/invoices", variant: "primary", children: "Invoices" },
};

export const ExternalAnchor: Story = {
  args: {
    href: "https://example.com/invoice",
    target: "_blank",
    rel: "noopener noreferrer",
    variant: "secondary",
    children: "Open invoice",
  },
};

export const Sizes: Story = {
  render: () => <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
    <ButtonLink to="/small" variant="ghost" size="sm">Small</ButtonLink>
    <ButtonLink to="/medium" variant="ghost" size="md">Medium</ButtonLink>
    <ButtonLink to="/large" variant="ghost" size="lg">Large</ButtonLink>
  </div>,
};
