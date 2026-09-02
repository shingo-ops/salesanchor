import React from 'react';

export function StatusBadge({ label, tone }: { label: string; tone: 'warning' | 'danger' | 'success' }) {
  return <span className={`badge badge-${tone}`}>{label}</span>;
}
