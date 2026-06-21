import { useEffect } from "react";
import type { ComponentProps } from "react";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { ChannelTypeCombobox } from "./ChannelTypeCombobox";
import { api } from "../lib/api";

const MOCK_CHANNELS = [
  { id: 1, platform: "messenger", display_name: "Messenger", connection_type: "auto", is_active: true },
  { id: 2, platform: "instagram", display_name: "Instagram", connection_type: "auto", is_active: true },
  { id: 3, platform: "discord", display_name: "Discord", connection_type: "auto", is_active: true },
  { id: 4, platform: "phone", display_name: "電話", connection_type: "manual", is_active: true },
  { id: 5, platform: "in_person", display_name: "対面", connection_type: "manual", is_active: true },
  { id: 6, platform: "whatsapp", display_name: "WhatsApp", connection_type: "manual", is_active: true },
];

type ChannelTypeComboboxStoryProps = ComponentProps<typeof ChannelTypeCombobox>;

function ChannelTypeComboboxStory(props: ChannelTypeComboboxStoryProps) {
  const originalGet = api.get;
  api.get = async () => MOCK_CHANNELS as any;

  useEffect(
    () => () => {
      api.get = originalGet;
    },
    [originalGet],
  );

  return <ChannelTypeCombobox {...props} />;
}

const meta: Meta<typeof ChannelTypeCombobox> = {
  title: "Components/ChannelTypeCombobox",
  component: ChannelTypeCombobox,
  parameters: { layout: "padded" },
  tags: ["autodocs"],
};

export default meta;

type Story = StoryObj<typeof ChannelTypeCombobox>;

export const Default: Story = {
  name: "初期表示",
  args: {
    id: "channel-type-combobox-story",
    value: "whatsapp",
    placeholder: "チャネルを選択",
    onChange: () => {},
    onCommit: () => {},
  },
  render: (args) => <ChannelTypeComboboxStory {...args} />,
};
