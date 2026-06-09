import { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Modal } from "./Modal";

interface Props {
  open: boolean;
  title: string;
  message: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmModal({
  open,
  title,
  message,
  confirmLabel,
  cancelLabel,
  danger = false,
  onConfirm,
  onCancel,
}: Props) {
  const { t } = useTranslation();
  const resolvedConfirmLabel = confirmLabel ?? t("confirmModal.defaultConfirm");
  const resolvedCancelLabel = cancelLabel ?? t("confirmModal.defaultCancel");
  return (
    <Modal open={open} onClose={onCancel} title={title} size="sm">
      <div style={{ marginBottom: "var(--space-4)", lineHeight: 1.6 }}>{message}</div>
      <div className="form-actions">
        <button type="button" className="btn-secondary" onClick={onCancel}>{resolvedCancelLabel}</button>
        <button
          type="button"
          className={danger ? "btn-danger" : "btn-primary"}
          onClick={onConfirm}
          autoFocus
        >
          {resolvedConfirmLabel}
        </button>
      </div>
    </Modal>
  );
}
