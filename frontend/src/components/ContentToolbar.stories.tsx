import type { Meta, StoryObj } from "@storybook/react-vite";
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
      right={<button className="btn-primary">新規登録</button>}
    />
  ),
};

export const ActionOnlyNoFilter: Story = {
  name: "実行ボタンのみ_フィルタ無し",
  render: () => (
    <ContentToolbar right={<button className="btn-primary">新規発注</button>} />
  ),
};
