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

function RowDemo({ initial }: { initial: string[] }) {
  const [selected, setSelected] = useState<string[]>(initial);
  const [open, setOpen] = useState(false);
  return (
    <div style={{ width: "320px" }}>
      <MultiSelect
        layout="row"
        label="仕入元"
        options={OPTIONS}
        selected={selected}
        onChange={setSelected}
        clearLabel="選択をクリア"
        allLabel="すべて"
        countLabel={(n) => `${n}件選択中`}
        testId="story-multiselect-row"
        onOpen={() => setOpen((v) => !v)}
      />
      {open && (
        <MultiSelect
          layout="inline"
          label="仕入元"
          options={OPTIONS}
          selected={selected}
          onChange={setSelected}
          clearLabel="選択をクリア"
          allLabel="すべて"
          countLabel={(n) => `${n}件選択中`}
          emptyLabel="見つかりません"
          testId="story-multiselect-row-options"
        />
      )}
    </div>
  );
}

export const Row: Story = { render: () => <RowDemo initial={[]} /> };
export const RowWithSelection: Story = { render: () => <RowDemo initial={["a", "c"]} /> };
