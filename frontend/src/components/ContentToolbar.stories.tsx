import type { Meta, StoryObj } from "@storybook/react-vite";
import { Button } from "./Button";
import { ContentToolbar } from "./ContentToolbar";

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
