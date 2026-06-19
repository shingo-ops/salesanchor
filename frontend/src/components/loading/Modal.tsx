import { useEffect, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

export interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: ReactNode;
  children?: ReactNode;
  /** Footer actions (buttons). */
  footer?: ReactNode;
}

/**
 * Centered confirmation dialog. Overlay fades, dialog scales in.
 * Closes on overlay click and Escape.
 */
export function Modal({ open, onClose, title, children, footer }: ModalProps) {
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
      <div className="sa-modal-wrap" aria-hidden={!open}>
        <div className={`sa-modal${open ? ' sa-modal--open' : ''}`} role="dialog" aria-modal="true">
          {title && <h2 className="sa-modal__title">{title}</h2>}
          <div className="sa-modal__body">{children}</div>
          {footer && <div className="sa-modal__footer">{footer}</div>}
        </div>
      </div>
    </>,
    document.body,
  );
}
