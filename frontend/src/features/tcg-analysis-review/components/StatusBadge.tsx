import React from 'react';

export function StatusBadge({ label, tone }: { label: string; tone: 'warning' | 'danger' | 'success' }) {
  // status-ssot-exempt: review issue tone (warning/danger/success) — not a business status domain
  return <span className={`badge badge-${tone}`}>{label}</span>;
}
