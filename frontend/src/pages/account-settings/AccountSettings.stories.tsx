/**
 * AccountSettings — デザイントークンカタログ (ADR-067)
 *
 * アカウント設定ページのフォームスタイル確認
 */
import type { Meta, StoryObj } from '@storybook/react-vite'
import { Button } from '../../components/Button'
import './account-settings.css'

const meta: Meta = {
  title: 'Pages/AccountSettings',
  parameters: { layout: 'padded' },
  tags: ['autodocs'],
}
export default meta

type Story = StoryObj

export const ProfileSection: Story = {
  name: 'プロフィールセクション',
  render: () => (
    <div className="account-settings-layout" style={{ maxWidth: 600 }}>
      <div className="account-settings-section">
        <div className="account-settings-section-title">プロフィール</div>
        <div className="account-settings-field">
          <div className="account-settings-label">氏名</div>
          <div className="account-settings-readonly">山田 太郎</div>
        </div>
        <div className="account-settings-field">
          <div className="account-settings-label">メールアドレス</div>
          <div className="account-settings-readonly">taro@example.com</div>
        </div>
        <div className="account-settings-note">
          プロフィール情報は管理者が変更できます。
        </div>
      </div>
    </div>
  ),
}

export const SuccessMessage: Story = {
  name: '保存成功メッセージ',
  render: () => (
    <div className="account-settings-layout" style={{ maxWidth: 600 }}>
      <div className="account-settings-section">
        <div className="account-settings-success">
          設定が保存されました。
        </div>
        <div className="account-settings-actions">
          <Button variant="primary" size="md">保存</Button>
          <Button variant="secondary" size="md">キャンセル</Button>
        </div>
      </div>
    </div>
  ),
}
