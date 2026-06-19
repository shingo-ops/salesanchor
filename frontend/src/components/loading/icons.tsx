// Minimal inline icons (Heroicons-style stroke). Use currentColor so the
// caller controls color via a token-bound CSS color.
export function CheckIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="1em" height="1em" viewBox="0 0 24 24" fill="none" aria-hidden="true" focusable="false">
      <path d="M5 13 L10 18 L19 7" stroke="currentColor" strokeWidth={3} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function CloseIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="1em" height="1em" viewBox="0 0 24 24" fill="none" aria-hidden="true" focusable="false">
      <path d="M6 6 L18 18 M18 6 L6 18" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
    </svg>
  );
}
