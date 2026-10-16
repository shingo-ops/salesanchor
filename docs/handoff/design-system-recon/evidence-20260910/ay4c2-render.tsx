// AY-4c-2a 実測用: 型ごとの「実物の親」の HTML 断片を前後で作り JSON に出す（金型の DOM は本物を renderToStaticMarkup。手書きしない）。
// 変更前のマークアップは origin/main 52b8a4003 の実ファイルのチェック欄部分をそのまま写している（ref に file:line）。
// 後のマークアップは作業ツリーの実ファイル（設計 §3）どおり。"@src" は esbuild の alias で frontend/src（作業ツリー）。
import { renderToStaticMarkup } from "react-dom/server";
import type { ReactNode } from "react";
import { Checkbox } from "@src/components/Checkbox";
import { CheckboxControl } from "@src/components/CheckboxControl";
import { TextField } from "@src/components/TextField";

type V = "before" | "after";
const noop = () => {};
const pane = (w: number, children: ReactNode) => (
  <div data-sample style={{ width: `min(${w}px, 100vw)`, boxSizing: "border-box", padding: "var(--space-5) var(--space-6)", background: "var(--bg-surface)" }}>{children}</div>
);
// 次の兄弟（TextFieldControl の .form-group。ContactEditPage.tsx:175-176 と同じ形）
const NEXT = <div className="form-group"><label>メール</label><TextField value="sample@example.com" onChange={noop} /></div>;

// ---- H1-1: MultiSelect.tsx:76-87（Popover の中。Popover の枠は .comp-popover の padding space-2 + 枠を再現）----
const h11 = (v: V, c: boolean) => {
  const opts: Array<[string, boolean]> = [["仕入先A", c], ["仕入先B", true], ["仕入先C", false]];
  return (
    <div data-sample style={{ width: "min(420px, 100vw)", boxSizing: "border-box", padding: "var(--space-2)", border: "1px solid var(--border)", background: "var(--bg-surface)" }}>
      <div className="comp-multiselect__menu"><div className="comp-multiselect__list">
        {opts.map(([name, ch]) => (
          <label key={name} className="comp-multiselect__option">
            {v === "before"
              ? <input type="checkbox" className="comp-multiselect__check" checked={ch} onChange={noop} data-testid={"opt-" + name} />
              : <CheckboxControl checked={ch} onChange={noop} data-testid={"opt-" + name} />}
            {name}
          </label>
        ))}
      </div></div>
    </div>
  );
};
// ---- H1-6: SalesFormMultiSelect.tsx:118-141（div.sales-form-dropdown の中に label.sales-form-option）----
const h16 = (v: V, c: boolean) => {
  const opts: Array<[string, boolean]> = [["卸売", c], ["小売", true], ["ネット販売", false]];
  return (
    <div data-sample style={{ width: "min(320px, 100vw)", height: 170, boxSizing: "border-box", padding: "var(--space-1)", background: "var(--bg-surface)" }}>
      <div style={{ position: "relative", height: 36, border: "1px solid var(--border)", borderRadius: "var(--radius-sm)" }}>
        <div className="sales-form-dropdown" role="listbox">
          {opts.map(([name, ch]) => (
            <label key={name} className={`sales-form-option${ch ? " sales-form-option--checked" : ""}`}>
              {v === "before"
                ? <input type="checkbox" checked={ch} onChange={noop} aria-label={name} />
                : <CheckboxControl checked={ch} onChange={noop} aria-label={name} />}
              <span className="sales-form-option-label">{name}</span>
            </label>
          ))}
        </div>
      </div>
    </div>
  );
};
// ---- H1-7: RolesPage.tsx:419-429（div.permission-group-body > label.permission-item）----
const h17 = (v: V, c: boolean) => {
  const items: Array<[string, boolean, boolean]> = [["顧客の一覧を見る", c, false], ["顧客を編集する（権限がないため変更できない行）", true, true], ["この権限があると、担当者は自分のチームに属する全ての顧客・商談・見積・請求の情報を一覧で見て、条件で絞り込んで確認できる（長い説明文で2行以上に折れる行）", false, false]];
  return (
    <div data-sample style={{ width: "min(720px, 100vw)", boxSizing: "border-box", background: "var(--bg-surface)" }}>
      <div className="permission-group-body">
        {items.map(([d, ch, dis], i) => (
          <label key={i} className="permission-item">
            {v === "before"
              ? <input type="checkbox" checked={ch} disabled={dis} onChange={noop} />
              : <CheckboxControl checked={ch} disabled={dis} onChange={noop} />}
            <div className="permission-item-text"><div className="permission-item-desc">{d}</div></div>
          </label>
        ))}
      </div>
    </div>
  );
};
// ---- H2: ContactEditPage.tsx:169-174（div.form-group > label > input + 文字）。次の兄弟は TextFieldControl の form-group ----
const L2 = "主担当者として登録する";
const h2 = (v: V, c: boolean) =>
  pane(560, <form>
    <div className="form-group">
      {v === "before"
        ? <label><input type="checkbox" checked={c} onChange={noop} />{" "}{L2}</label>
        : <Checkbox label={L2} checked={c} onChange={noop} />}
    </div>
    {NEXT}
  </form>);
// ---- H2-3/H2-4: StaffEditPage.tsx:209-218・StaffPage.tsx:286-291（Object.entries(labels).map の div.form-group を縦に並べる。中身は H2 と同形）----
const LABELS = ["受信箱を表示する", "営業メモを表示する", "通知を受け取る"];
const h2list = (v: V, c: boolean) =>
  pane(560, <form>
    {LABELS.map((label, i) => {
      const ch = i === 0 ? c : i === 1;
      return (
        <div className="form-group" key={i}>
          {v === "before"
            ? <label><input type="checkbox" checked={ch} onChange={noop} />{" "}{label}</label>
            : <Checkbox label={label} checked={ch} onChange={noop} />}
        </div>
      );
    })}
    {NEXT}
  </form>);
// ---- H2N: NotificationsPage.tsx:128-138（見出し label ＋ eventTypes.map の Checkbox 3 つ。前は直下、後は div で1つずつ包む）----
const EV = ["商談の更新", "見積の送付", "請求の入金"];
const h2n = (v: V, c: boolean) =>
  pane(560, <form>
    <div className="form-group">
      <label data-heading>通知するイベント</label>
      {EV.map((name, i) => {
        const ch = i === 0 ? c : i === 1;
        return v === "before"
          ? <Checkbox key={i} label={name} checked={ch} onChange={noop} />
          : <div key={i}><Checkbox label={name} checked={ch} onChange={noop} /></div>;
      })}
    </div>
    {NEXT}
  </form>);
// ---- H3: InboxProfileModal.tsx:252-264（div.right-panel-row（縦 flex）> span.right-panel-label + 欄）----
const h3 = (v: V, c: boolean) => {
  const text = c ? "確認済み" : "未確認";
  return (
    <div data-sample style={{ width: "min(320px, 100vw)", boxSizing: "border-box", padding: "var(--space-4) var(--space-3)", background: "var(--bg-surface)" }}>
      <div className="right-panel-row">
        <span className="right-panel-label">競合チェック</span>
        {v === "before"
          ? <label style={{ display: "flex", alignItems: "center", gap: "var(--space-1)" }}>
              <input type="checkbox" checked={c} onChange={noop} />
              <span className="right-panel-value">{text}</span>
            </label>
          : <Checkbox label={text} checked={c} onChange={noop} />}
      </div>
    </div>
  );
};

type Sample = { id: string; type: string; ref: string; build: (v: V, c: boolean) => ReactNode };
const S: Sample[] = [
  { id: "MultiSelect(項目1)", type: "H1-1", ref: "frontend/src/components/MultiSelect.tsx:76-87（Popover 内 .comp-multiselect__menu > __list > label.comp-multiselect__option。Popover 枠は .comp-popover の padding space-2 と枠を再現）", build: h11 },
  { id: "SalesFormMultiSelect(項目6)", type: "H1-6", ref: "frontend/src/pages/inbox/SalesFormMultiSelect.tsx:118-141（div.sales-form-dropdown > label.sales-form-option、うち1つは --checked。ドロップダウンは位置指定で下に出るため、トリガー枠の高さ 36px の外側の余白に描く）", build: h16 },
  { id: "RolesPage(項目7)", type: "H1-7", ref: "frontend/src/pages/roles/RolesPage.tsx:419-429（div.permission-group-body の grid に label.permission-item を3つ。2つ目は disabled、3つ目は2行以上に折れる長い文字）", build: h17 },
  { id: "ContactEditPage(項目2)", type: "H2", ref: "frontend/src/pages/contacts/ContactEditPage.tsx:169-176（div.form-group の次の兄弟が TextFieldControl の div.form-group）", build: h2 },
  { id: "StaffEditPage(項目3)", type: "H2-3", ref: "frontend/src/pages/staff/StaffEditPage.tsx:209-218（Object.entries(labels).map の div.form-group key={k}。中身は項目2と同形＝ div.form-group の唯一の子）", build: h2list },
  { id: "StaffPage(項目4)", type: "H2-4", ref: "frontend/src/pages/staff/StaffPage.tsx:286-291（同上。項目3と同形の div.form-group を縦に並べる）", build: h2list },
  { id: "NotificationsPage(副作用)", type: "H2N", ref: "frontend/src/pages/notifications/NotificationsPage.tsx:128-138・:155-165（div.form-group > 見出し label ＋ eventTypes.map。前は Checkbox 直下、後は div で包む）", build: h2n },
  { id: "InboxProfileModal(項目5)", type: "H3", ref: "frontend/src/pages/inbox/InboxProfileModal.tsx:252-264（div.right-panel-row（縦 flex）> span.right-panel-label + 欄）", build: h3 },
];

(globalThis as any).window = { matchMedia: () => ({ matches: false, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {} }) };
const h = (n: ReactNode) => renderToStaticMarkup(n as any);
process.stdout.write(
  JSON.stringify(
    S.map((s) => ({ id: s.id, type: s.type, ref: s.ref, html: { before: { u: h(s.build("before", false)), c: h(s.build("before", true)) }, after: { u: h(s.build("after", false)), c: h(s.build("after", true)) } } })),
  ),
);
