// AY-3b 実測用: Toggle を renderToStaticMarkup した HTML を JSON で出す（手書きしない。設計 §5）。
// 実行: node ay3b-measure.cjs が esbuild でこのファイルを束ねて呼ぶ。
import { renderToStaticMarkup } from "react-dom/server";
import { Toggle } from "../../../../frontend/src/components/Toggle";

const noop = () => {};
const specs: Record<string, { id?: string; label?: string }> = {
  "inbox-1": { label: "Show right panel" },
  "inbox-2": { label: "Default unread only" },
  "inbox-3": { label: "Browser notifications" },
  "inbox-4": { label: "Sound" },
  pref: { id: "dark-mode-toggle" },
  allday: { label: "All day" },
  "sched-self": { label: "Visible" },
  "sched-other": { label: "Visible" },
};
const out: Record<string, { off: string; on: string }> = {};
for (const [k, s] of Object.entries(specs)) {
  const p = { id: s.id, "aria-label": s.label, onCheckedChange: noop };
  out[k] = {
    off: renderToStaticMarkup(<Toggle checked={false} {...p} />),
    on: renderToStaticMarkup(<Toggle checked={true} {...p} />),
  };
}
process.stdout.write(JSON.stringify(out));
