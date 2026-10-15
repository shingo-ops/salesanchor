/**
 * MultiSelect — ストーリーカタログ
 */
import { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { MultiSelect } from "./MultiSelect";

const OPTIONS = [
  { value: "a", label: "仕入元A" },
  { value: "b", label: "仕入元B" },
  { value: "c", label: "仕入元C" },
];

const meta: Meta<typeof MultiSelect> = {
  title: "Components/MultiSelect",
  component: MultiSelect,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
};
export default meta;

type Story = StoryObj<typeof MultiSelect>;

function Demo({ initial }: { initial: string[] }) {
  const [selected, setSelected] = useState<string[]>(initial);
  return (
    <MultiSelect
      label="仕入元"
      options={OPTIONS}
      selected={selected}
      onChange={setSelected}
      clearLabel="選択をクリア"
      allLabel="すべて"
      countLabel={(n) => `${n}件選択中`}
      testId="story-multiselect"
    />
  );
}

export const Empty: Story = { render: () => <Demo initial={[]} /> };
export const One: Story = { render: () => <Demo initial={["b"]} /> };
export const Many: Story = { render: () => <Demo initial={["a", "c"]} /> };
