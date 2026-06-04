/**
 * ContactChannelLinks — デザイントークンカタログ (ADR-067)
 *
 * 担当者チャンネルリンク一覧コンポーネント
 * ※ APIコールを行うため Storybook 上では空表示となる（スタイル確認が目的）
 */
import type { Meta, StoryObj } from '@storybook/react-vite'
import { MemoryRouter } from 'react-router-dom'
import ContactChannelLinks from './ContactChannelLinks'

const meta: Meta<typeof ContactChannelLinks> = {
  title: 'Components/ContactChannelLinks',
  component: ContactChannelLinks,
  decorators: [(Story) => <MemoryRouter><Story /></MemoryRouter>],
  parameters: { layout: 'padded' },
  tags: ['autodocs'],
}
export default meta

type Story = StoryObj<typeof ContactChannelLinks>

export const Default: Story = {
  name: '担当者チャンネルリンク',
  args: {
    contactId: 1,
  },
}
