import { Spinner } from './Spinner';
import { CheckIcon } from './icons';

export type SaveStatus = 'idle' | 'saving' | 'saved';

/**
 * Inline autosave feedback for a cell/field: editing → saving (spinner) → saved (✓).
 * Drive `status` from your debounced autosave mutation.
 */
export function SaveIndicator({ status }: { status: SaveStatus }) {
  if (status === 'idle') return null;
  if (status === 'saving') {
    return (
      <span className="sa-save">
        <Spinner size="sm" label="Saving" /> Saving
      </span>
    );
  }
  return (
    <span className="sa-save sa-save--saved">
      <CheckIcon className="sa-save__icon" /> Saved
    </span>
  );
}
