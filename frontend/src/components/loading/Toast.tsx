import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { CheckIcon } from './icons';

export type ToastVariant = 'success' | 'warning' | 'error' | 'info';
export interface ToastOptions { description?: string; duration?: number }
interface ToastItem { id: number; variant: ToastVariant; title: string; description?: string; duration: number }

// --- tiny store (no Context needed; call toast.* from anywhere) ---
let items: ToastItem[] = [];
let listeners: Array<(items: ToastItem[]) => void> = [];
let seq = 0;
const emit = () => listeners.forEach((l) => l(items));

function dismiss(id: number) {
  items = items.filter((i) => i.id !== id);
  emit();
}
function push(variant: ToastVariant, title: string, opts?: ToastOptions) {
  const id = ++seq;
  const duration = opts?.duration ?? 4000;
  items = [...items, { id, variant, title, description: opts?.description, duration }];
  emit();
  window.setTimeout(() => dismiss(id), duration);
  return id;
}

/** Fire from anywhere: toast.success('Completed'). Requires <Toaster /> mounted once. */
export const toast = {
  success: (title: string, o?: ToastOptions) => push('success', title, o),
  warning: (title: string, o?: ToastOptions) => push('warning', title, o),
  error: (title: string, o?: ToastOptions) => push('error', title, o),
  info: (title: string, o?: ToastOptions) => push('info', title, o),
  dismiss,
};

function ToastView({ item }: { item: ToastItem }) {
  return (
    <div className={`sa-toast sa-toast--${item.variant}`} role="status" aria-live="polite">
      <span className="sa-toast__dot">{item.variant === 'success' ? <CheckIcon /> : <Dot />}</span>
      <div className="sa-toast__body">
        <span className="sa-toast__title">{item.title}</span>
        {item.description && <span className="sa-toast__desc">{item.description}</span>}
      </div>
    </div>
  );
}
const Dot = () => <span className="sa-toast__fallback-dot" aria-hidden="true" />;

/** Mount once near the app root (e.g. inside the top-level layout). */
export function Toaster() {
  const [list, setList] = useState<ToastItem[]>(items);
  useEffect(() => {
    listeners.push(setList);
    return () => {
      listeners = listeners.filter((l) => l !== setList);
    };
  }, []);
  if (typeof document === 'undefined') return null;
  return createPortal(
    <div className="sa-toast-region">
      {list.map((t) => (
        <ToastView key={t.id} item={t} />
      ))}
    </div>,
    document.body,
  );
}
