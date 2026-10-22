import { useTranslation } from 'react-i18next';
import { Spinner } from './Spinner';
import type { SpinnerSize } from './Spinner';
import './LoadingBlock.css';

export interface LoadingBlockProps {
  /** Accessible label. Default: t("common.loading"). */
  label?: string;
  size?: SpinnerSize;
  /** Inline (no padding) for use inside a row or form. */
  inline?: boolean;
  className?: string;
}

/** The single loading indicator for areas that are fetching data. */
export function LoadingBlock({ label, size = 'md', inline = false, className }: LoadingBlockProps) {
  const { t } = useTranslation();
  const cls = ['sa-loading-block', inline ? 'sa-loading-block--inline' : '', className].filter(Boolean).join(' ');
  return (
    <div className={cls}>
      <Spinner size={size} label={label ?? t('common.loading')} />
    </div>
  );
}
