/**
 * TextLink — 枠のない文字リンク（login-round-inputs/design.md §6.1）
 */
import type { Meta, StoryObj } from '@storybook/react-vite'
import { MemoryRouter } from 'react-router-dom'
import { TextLink } from './TextLink'

const meta: Meta<typeof TextLink> = {
  title: 'Components/TextLink',
  component: TextLink,
  parameters: { layout: 'padded' },
  tags: ['autodocs'],
}
export default meta

type Story = StoryObj<typeof TextLink>

export const AsButton: Story = {
  name: 'onClick — button（画面の切り替え）',
  args: { onClick: () => {}, children: 'パスワードをお忘れですか？' },
}

export const AsLink: Story = {
  name: 'to — Link（移動）',
  render: () => (
    <MemoryRouter>
      <TextLink to="/login">ログイン画面に戻る</TextLink>
    </MemoryRouter>
  ),
}
