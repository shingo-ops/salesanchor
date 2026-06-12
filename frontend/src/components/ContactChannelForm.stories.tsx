/**
 * ContactChannelForm — デザイントークンカタログ (ADR-067)
 *
 * 担当者チャンネル追加・編集フォーム（ADR-098 SA-04）
 * ※ API 通信を含むため Storybook 上では実際のデータ保存は行われない
 *   フォームレイアウト・バリデーション表示のスタイル確認が目的
 */
import type { Meta, StoryObj } from '@storybook/react-vite'
import ContactChannelForm from './ContactChannelForm'

const meta: Meta<typeof ContactChannelForm> = {
  title: 'Components/ContactChannelForm',
  component: ContactChannelForm,
  parameters: { layout: 'centered' },
  tags: ['autodocs'],
}
export default meta

type Story = StoryObj<typeof ContactChannelForm>

export const AddNew: Story = {
  name: '新規追加モード',
  args: {
    open: true,
    contactId: 1,
    companyId: 1,
    initial: null,
    onSaved: () => {},
    onCancel: () => {},
  },
}

export const EditExisting: Story = {
  name: '編集モード',
  args: {
    open: true,
    contactId: 1,
    companyId: 1,
    initial: {
      id: 42,
      channel: 'whatsapp',
      purpose: '+819012345678',
      guild_id: null,
      is_primary: true,
    },
    onSaved: () => {},
    onCancel: () => {},
  },
}

export const DiscordChannel: Story = {
  name: 'Discord チャンネル（guild_id 入力欄表示）',
  args: {
    open: true,
    contactId: 1,
    companyId: 1,
    initial: {
      id: 43,
      channel: 'discord',
      purpose: 'user#1234',
      guild_id: '123456789012345678',
      is_primary: false,
    },
    onSaved: () => {},
    onCancel: () => {},
  },
}
