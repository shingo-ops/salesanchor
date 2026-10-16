// AY-4c-2b 試料の生成。前: 変更前の SchedulePageImpl.tsx:522-529・:553-560 から写したマークアップ。後: 本物の CheckboxControl が描く DOM。
// 親の構造は SchedulePageImpl.tsx の サイドバー > section > .schedule-calendar-list > label.schedule-calendar-item を写す。
import { renderToStaticMarkup } from "react-dom/server";
import { CheckboxControl } from "@src/components/CheckboxControl";

type Owner = { name: string; color: string; self?: boolean };
const OWNERS: Owner[] = [
  { name: "Self", color: "#1a73e8", self: true },
  { name: "Other A", color: "#e8710a" },
  { name: "Other B", color: "#0b8043" },
];
const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/"/g, "&quot;");

const meta = (o: Owner) =>
  `<div class="schedule-calendar-item__meta"><span class="schedule-calendar-item__swatch" style="background:${o.color}" aria-hidden="true"></span><span class="schedule-calendar-item__label">${o.name}</span></div>`;

const beforeInput = (o: Owner, checked: boolean) =>
  `<input type="checkbox" class="schedule-calendar-checkbox" style="accent-color:${o.color}"${checked ? " checked" : ""}${o.self ? " disabled" : ""} aria-label="${esc(o.name)}"/>`;
const afterInput = (o: Owner, checked: boolean) =>
  o.self
    ? renderToStaticMarkup(<CheckboxControl dataColor={o.color} checked={checked} disabled aria-label={o.name} readOnly />)
    : renderToStaticMarkup(<CheckboxControl dataColor={o.color} checked={checked} onChange={() => {}} aria-label={o.name} />);

const build = (side: "before" | "after", state: "u" | "c") => {
  const rows = OWNERS.map((o) => {
    const checked = o.self ? true : state === "c";
    const cls = o.self || checked ? "schedule-calendar-item" : "schedule-calendar-item schedule-calendar-item--hidden";
    const inp = side === "before" ? beforeInput(o, checked) : afterInput(o, checked);
    return `<label class="${cls}" data-row${o.self ? " data-self" : ""}>${meta(o)}${inp}</label>`;
  }).join("");
  return `<div data-sample style="padding:16px"><aside class="schedule-sidebar"><section class="schedule-sidebar__section"><div class="schedule-calendar-list">${rows}</div></section></aside></div>`;
};

const out = { before: { u: build("before", "u"), c: build("before", "c") }, after: { u: build("after", "u"), c: build("after", "c") } };
console.log(JSON.stringify(out));
