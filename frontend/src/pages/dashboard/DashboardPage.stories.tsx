/**
 * Dashboard — デザイントークンカタログ (ADR-067)
 *
 * 新規追加トークン（rgba 直書き禁止対応）の視覚確認:
 * - --danger-bg-subtle  期限超過アイテム背景
 * - --accent-bg-subtle  当日期限アイテム背景
 * - --warning-bg-subtle 停滞アイテム背景
 * ライト / ダークモード両対応
 */
import type { Meta, StoryObj } from '@storybook/react-vite'
import { DashboardIcons } from '../../constants/icons'
import './DashboardPage.css'
import './WeeklyAdvisorSection.css'
import './PriorityProspectsSection.css'

const meta: Meta = {
  title: 'Pages/Dashboard',
  parameters: { layout: 'padded' },
  tags: ['autodocs'],
}
export default meta

type Story = StoryObj

// ─────────────────────────────────────────────
// フォローアップアイテムの状態色（rgba→トークン化）
// ─────────────────────────────────────────────
export const FollowupStatusColors: Story = {
  name: 'フォローアップ状態色（ADR-067 rgba トークン）',
  render: () => (
    <div style={{ width: 'var(--ds-preview-width)' }}>
      <div className="db-followup-item db-overdue" style={{ padding: 'var(--space-3)', marginBottom: 'var(--space-2)', borderRadius: 'var(--radius-md)' }}>
        <span style={{ fontSize: 'var(--font-sm)' }}>期限超過（--danger-bg-subtle）</span>
      </div>
      <div className="db-followup-item db-due-today" style={{ padding: 'var(--space-3)', marginBottom: 'var(--space-2)', borderRadius: 'var(--radius-md)' }}>
        <span style={{ fontSize: 'var(--font-sm)' }}>当日期限（--accent-bg-subtle）</span>
      </div>
      <div className="db-followup-item db-stalled" style={{ padding: 'var(--space-3)', borderRadius: 'var(--radius-md)' }}>
        <span style={{ fontSize: 'var(--font-sm)' }}>停滞中（--warning-bg-subtle）</span>
      </div>
    </div>
  ),
}

// ─────────────────────────────────────────────
// タブナビゲーション
// ─────────────────────────────────────────────
export const Tabs: Story = {
  name: 'タブナビゲーション',
  render: () => (
    <div className="db-controls">
      <div className="db-tabs">
        <button className="db-tab active">月次</button>
        <button className="db-tab">週次</button>
        <button className="db-tab">日次</button>
      </div>
    </div>
  ),
}

export const TodayActionsSplit: Story = {
  name: 'Today actions split',
  render: () => (
    <div style={{ width: 'var(--ds-preview-width)' }} className="db-content-stack">
      <div className="db-section-card db-priority-card">
        <div className="db-section-header">
          <DashboardIcons.goalFlag aria-hidden="true" className="db-section-icon" />
          <h3>
            Priority prospects
            <span className="db-priority-ai-pill">Opportunity</span>
          </h3>
        </div>
        <p className="db-priority-subtitle">Sort offensive targets by ease and expected value.</p>
        <div className="db-priority-item">
          <div className="db-priority-item-head">
            <span className="db-priority-badge">Opportunity</span>
            <span className="db-priority-type">Priority prospect</span>
            <span className="db-priority-score-label">Rank score: <strong>25,088,000</strong></span>
          </div>
          <div className="db-priority-company">Blue Ocean Co.</div>
          <div className="db-priority-meta">
            <span>Ease: 78.4%</span>
            <span>Monthly forecast: ¥320,000</span>
          </div>
          <div className="db-priority-flag-row">
            <span className="db-priority-flag">Small sample</span>
          </div>
          <div className="db-priority-axis">
            <span className="db-priority-axis-chip"><span className="db-priority-axis-label">channel_type:</span><span className="db-priority-axis-value">web</span></span>
            <span className="db-priority-axis-chip"><span className="db-priority-axis-label">country:</span><span className="db-priority-axis-value">JP</span></span>
          </div>
        </div>
      </div>

      <div className="db-section-card db-weekly-card">
        <div className="db-section-header">
          <DashboardIcons.goalDone aria-hidden="true" className="db-section-icon" />
          <h3>
            Today's Actions
            <span className="db-weekly-ai-pill">AI Suggested</span>
          </h3>
        </div>
        <p className="db-weekly-subtitle">Defensive priorities stay intact below.</p>
        <div className="db-weekly-item db-weekly-item--reorder">
          <div className="db-weekly-item-head">
            <span className="db-weekly-rank">#1</span>
            <span className="db-weekly-type">Reorder Soon</span>
            <span className="db-weekly-score-label">Score: <strong>12,800</strong></span>
          </div>
          <div className="db-weekly-company">Blue Ocean Co.</div>
          <div className="db-weekly-meta">
            <span>Expected value: ¥320,000</span>
            <span>Reconnect soon</span>
          </div>
        </div>
      </div>
    </div>
  ),
}
