import React from 'react';
import './status-badge.css';

export function StatusBadge({ label, tone }: { label: string; tone: 'warning' | 'danger' | 'success' }) {
  // status-ssot-exempt: review issue tone (warning/danger/success) — not a business status domain
  return <span className={`tcg-status-badge tcg-status-badge--${tone}`}>{label}</span>;
}
