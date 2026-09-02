import React from 'react';
import type { ReviewTab, ReviewTabId } from '../reviewTabs';
import './status-tab-bar.css';

export function StatusTabBar({ tabs, activeTab, counts, onChange }: { tabs: ReviewTab[]; activeTab: ReviewTabId; counts: Partial<Record<ReviewTabId, number>>; onChange: (id: ReviewTabId) => void }) {
  return <nav className="status-tabs" aria-label="確認状況"><div role="tablist">{tabs.map((tab) => <button key={tab.id} role="tab" type="button" aria-selected={activeTab === tab.id} disabled={!tab.enabled} title={!tab.enabled ? '出力完了との正式な1:1対応確認後に有効化します' : undefined} className={`status-tab status-tab-${tab.tone}`} onClick={() => onChange(tab.id)}>{tab.label}{tab.enabled && <span>{counts[tab.id] ?? 0}</span>}{!tab.enabled && <small>準備中</small>}</button>)}</div></nav>;
}
