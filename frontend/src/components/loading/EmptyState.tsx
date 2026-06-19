import type { ReactNode } from 'react';

export interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  /** CTA, e.g. <Button>新規登録</Button> */
  action?: ReactNode;
}

/**
 * Centered no-data placeholder with a soft fade-in. Use when a list returns 0 rows.
 */
export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="sa-empty">
      {icon && <div className="sa-empty__icon">{icon}</div>}
      <div className="sa-empty__body">
        <span className="sa-empty__title">{title}</span>
        {description && <span className="sa-empty__desc">{description}</span>}
      </div>
      {action}
    </div>
  );
}
