import React, { createRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Button, type ButtonVariant } from '/Users/tanizawashingo/worktrees/salesanchor/release-frontend-calendar-source/frontend/src/components/Button';
import { Spinner } from '/Users/tanizawashingo/worktrees/salesanchor/release-frontend-calendar-source/frontend/src/components/loading/Spinner';
import '/Users/tanizawashingo/worktrees/salesanchor/release-frontend-calendar-source/frontend/src/tokens.css';
import '/Users/tanizawashingo/worktrees/salesanchor/release-frontend-calendar-source/frontend/src/index.css';
import '/Users/tanizawashingo/worktrees/salesanchor/release-frontend-calendar-source/frontend/src/components.css';

const variants: ButtonVariant[] = ['primary', 'secondary', 'ghost', 'danger', 'outline', 'tab'];
const refs = Object.fromEntries(variants.map((v) => [v, createRef<HTMLButtonElement>()]));
const probe = { counts: Object.fromEntries(variants.map((v) => [v, 0])), refs, original: {}, setMode: (_mode: string) => {} };
(window as any).buttonProbe = probe;
function App() {
  const [mode, setMode] = useState('normal');
  probe.setMode = setMode;
  return <main>
    <div>{variants.map((variant) => <Button key={variant} ref={refs[variant]} id={variant} type="button"
      variant={variant} disabled={mode === 'disabled'} loading={mode === 'loading'}
      onClick={() => { probe.counts[variant] += 1; }}>{variant}</Button>)}</div>
    <div id="inherited" style={{ color: 'var(--text-primary)' }}><Spinner tone="inherit" onAccent color="var(--danger)" decorative /></div>
    <div id="normal"><Spinner /></div>
    <div id="on-accent"><Spinner onAccent /></div>
  </main>;
}
createRoot(document.getElementById('root')!).render(<App />);
