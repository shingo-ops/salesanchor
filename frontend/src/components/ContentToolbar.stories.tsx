import type { Meta, StoryObj } from "@storybook/react-vite";
import { Button } from "./Button";
import { ContentToolbar, ContentToolbarRange } from "./ContentToolbar";

const meta: Meta<typeof ContentToolbar> = {
  title: "Components/ContentToolbar",
  component: ContentToolbar,
};
export default meta;
type Story = StoryObj<typeof ContentToolbar>;

export const FilterAndAction: Story = {
  name: "フィルタと実行ボタン",
  render: () => (
    <ContentToolbar
      left={<select><option>全ステータス</option></select>}
      right={<Button variant="primary" size="md">新規登録</Button>}
    />
  ),
};

export const ActionOnlyNoFilter: Story = {
  name: "実行ボタンのみ_フィルタ無し",
  render: () => (
    <ContentToolbar right={<Button variant="primary" size="md">新規発注</Button>} />
  ),
};

export const TwoRows: Story = {
  name: "2段_検索と範囲の下に並び替え",
  render: () => (
    <ContentToolbar
      left={<input aria-label="検索" placeholder="検索" />}
      right={null}
      bottomLeft={<select><option>並び替え</option></select>}
      bottomRight={<Button variant="secondary" size="md">リセット</Button>}
    />
  ),
};

export const RangeInput: Story = {
  name: "範囲入力",
  render: () => (
    <ContentToolbar
      left={
        <ContentToolbarRange
          minValue=""
          maxValue=""
          onMinChange={() => {}}
          onMaxChange={() => {}}
          minPlaceholder="最低"
          maxPlaceholder="最高"
          minAriaLabel="最低"
          maxAriaLabel="最高"
          testIdPrefix="story-range"
        />
      }
    />
  ),
};
