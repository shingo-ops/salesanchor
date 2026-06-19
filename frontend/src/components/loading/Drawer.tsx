import { useEffect, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { CloseIcon } from './icons';

export interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title?: ReactNode;
  children?: ReactNode;
}

/**
 * Right-side detail panel that slides in over an overlay.
 * Closes on overlay click and Escape.
 */
export function Drawer({ open, onClose, title, children }: DrawerProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (typeof document === 'undefined') return null;

  return createPortal(
    <>
      <div className={`sa-overlay${open ? ' sa-overlay--open' : ''}`} onClick={onClose} />
      <aside className={`sa-drawer${open ? ' sa-drawer--open' : ''}`} role="dialog" aria-modal="true" aria-hidden={!open}>
        <header className="sa-drawer__header">
          <span className="sa-drawer__title">{title}</span>
          <button onClick={onClose} aria-label="Close" className="sa-drawer__close">
            <CloseIcon className="sa-drawer__close-icon" />
          </button>
        </header>
        <div className="sa-drawer__content">{children}</div>
      </aside>
    </>,
    document.body,
  );
}
