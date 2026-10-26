import { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Modal } from "./Modal";
import { Button } from "./Button";

interface Props {
  open: boolean;
  title: string;
  message: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  /** 第9便: 入力未完了（例: プルダウン未選択）のときに確定を押せなくする。既定 false（後方互換） */
  confirmDisabled?: boolean;
  /** 便8a: 押した処理が終わるまで確定ボタンに丸を出し押せなくする。既定 false（後方互換） */
  confirmLoading?: boolean;
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
  confirmDisabled = false,
  confirmLoading = false,
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
        <Button type="button" variant="secondary" onClick={onCancel}>{resolvedCancelLabel}</Button>
        <Button
          type="button"
          variant={danger ? "danger" : "primary"}
          onClick={onConfirm}
          disabled={confirmDisabled}
          loading={confirmLoading}
          autoFocus
        >
          {resolvedConfirmLabel}
        </Button>
      </div>
    </Modal>
  );
}
