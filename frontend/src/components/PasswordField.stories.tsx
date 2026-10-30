/**
 * PasswordFieldControl — 目のマーク付きのパスワード欄（login-round-inputs/design.md §6.2）
 */
import type { Meta, StoryObj } from '@storybook/react-vite'
import { PasswordFieldControl } from './PasswordField'

const meta: Meta<typeof PasswordFieldControl> = {
  title: 'Components/PasswordField',
  component: PasswordFieldControl,
  parameters: { layout: 'padded' },
  tags: ['autodocs'],
}
export default meta

type Story = StoryObj<typeof PasswordFieldControl>

export const Standard: Story = {
  name: 'standard',
  args: { defaultValue: 'secret-password', 'aria-label': 'password' },
}

export const Login: Story = {
  name: 'login variant',
  args: { variant: 'login', defaultValue: 'secret-password', 'aria-label': 'password' },
}
