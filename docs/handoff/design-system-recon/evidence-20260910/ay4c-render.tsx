// AY-4c-1 実測用: 型ごとの「実物の親」の HTML 断片を前後で作り JSON に出す（金型の DOM は本物を renderToStaticMarkup。手書きしない）。
// 変更前のマークアップは origin/main の実ファイルのチェック欄部分をそのまま写している（ref に file:line）。
// "@src" は esbuild の alias で frontend/src（作業ツリー）を指す。TextField など変更していない部品は前後で同じもの。
import { renderToStaticMarkup } from "react-dom/server";
import { Fragment, type ReactNode } from "react";
import { Checkbox } from "@src/components/Checkbox";
import { CheckboxControl } from "@src/components/CheckboxControl";
import { TextField } from "@src/components/TextField";

type V = "before" | "after";
const noop = () => {};
const L = "有効にする";
const TF = (label: string) => <TextField label={label} value="サンプル" onChange={noop} />;
const G = (label: string, full = false) => (
  <div className="form-group" style={full ? { gridColumn: "1 / -1" } : undefined}>{TF(label)}</div>
);
const pane = (w: number, children: ReactNode) => (
  <div data-sample style={{ width: `min(${w}px, 100vw)`, boxSizing: "border-box", padding: "var(--space-5) var(--space-6)", background: "var(--bg-surface)" }}>{children}</div>
);
const GRID2 = { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-3) var(--space-4)" } as const;
const grid2 = (kids: string, slot: ReactNode) =>
  pane(560, <form><div style={GRID2}>{kids.split("").map((k, i) => <Fragment key={i}>{G("項目" + (i + 1), k === "F")}</Fragment>)}{slot}</div></form>);

// ---- G1: div.form-row > label。例 CompanyAddressModal.tsx:147-153 ----
const g1 = (v: V, c: boolean) =>
  v === "before" ? (
    <div className="form-row"><label><input type="checkbox" checked={c} onChange={noop} />{" "}{L}</label></div>
  ) : (
    <div className="form-row"><Checkbox label={L} checked={c} onChange={noop} /></div>
  );
// ---- G2: label のインライン style ----
const g2a = (v: V, c: boolean) => // #15 InventoryFilterPanel.tsx:132-141
  v === "before" ? (
    <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", fontWeight: "var(--font-weight-semi)" }}>
      <input type="checkbox" data-testid="inventory-filter-enabled" checked={c} onChange={noop} />{L}
    </label>
  ) : (
    <Checkbox label={L} data-testid="inventory-filter-enabled" checked={c} onChange={noop} />
  );
const g2b = (v: V, c: boolean, name: string, key: string) => // #16 InventoryFilterPanel.tsx:152-160
  v === "before" ? (
    <label key={key} style={{ display: "flex", alignItems: "center", gap: "var(--space-1)" }}>
      <input type="checkbox" checked={c} onChange={noop} />{name}
    </label>
  ) : (
    <Checkbox key={key} label={name} checked={c} onChange={noop} />
  );
const g2same = (v: V, c: boolean) => // #21 NoteMasterPage.tsx:315 ほか
  v === "before" ? (
    <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
      <input type="checkbox" checked={c} onChange={noop} />{L}
    </label>
  ) : (
    <Checkbox label={L} checked={c} onChange={noop} />
  );
// ---- G3: gridColumn 1 / -1。#8 ConditionsPage.tsx:352-359 ----
const g3 = (v: V, c: boolean) =>
  v === "before" ? (
    <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", gridColumn: "1 / -1" }}>
      <input type="checkbox" checked={c} onChange={noop} />{L}
    </label>
  ) : (
    <div style={{ gridColumn: "1 / -1" }}><Checkbox label={L} checked={c} onChange={noop} /></div>
  );
// ---- G4: RolesPage.tsx:396-415 ----
const g4 = (v: V, c: boolean) =>
  v === "before" ? (
    <div className="permission-group-toggles">
      <label className="chk-label" title="全て選択"><input type="checkbox" checked={c} onChange={noop} />すべて選択</label>
      <label className="chk-label" title="メニュー表示"><input type="checkbox" checked={c} onChange={noop} />メニューに表示</label>
    </div>
  ) : (
    <div className="permission-group-toggles">
      <span title="全て選択"><Checkbox label="すべて選択" checked={c} onChange={noop} /></span>
      <span title="メニュー表示"><Checkbox label="メニューに表示" checked={c} onChange={noop} /></span>
    </div>
  );
// ---- G5: 表のセル ----
const g5 = (v: V, c: boolean, extra: Record<string, string>) =>
  v === "before" ? <input type="checkbox" checked={c} onChange={noop} aria-label="x" {...extra} /> : <CheckboxControl checked={c} onChange={noop} aria-label="x" {...extra} />;
// ---- G6: InboxConversationList.tsx:117-135 ----
const ICONBOX = <span style={{ display: "inline-block", width: "var(--icon-sm, 16px)", height: "var(--icon-sm, 16px)", background: "currentColor" }} aria-hidden="true" />;
const g6 = (count: string) => (v: V, c: boolean) => (
  <div data-sample style={{ width: "min(360px, 100vw)", boxSizing: "border-box" }}>
    <div className="inbox-bulk-bar">
      {v === "before" ? (
        <input type="checkbox" className="inbox-bulk-check-all" checked={c} onChange={noop} aria-label="全選択" />
      ) : (
        <CheckboxControl size="sm" checked={c} onChange={noop} aria-label="全選択" />
      )}
      <span className="inbox-bulk-count">{count}</span>
      {["a", "b", "c", "d"].map((k) => <button key={k} type="button" className="inbox-bulk-action">{ICONBOX}</button>)}
    </div>
  </div>
);
// 実際の文言（locales/ja.json:1286 "{{count}}件選択中"）と、縮みの検証用に折り返せない長い文字（数字 30 桁）で行全体を幅 360 より広くした場合
const G6_REAL = g6("12件選択中");
const G6_STRESS = g6("選択中 123456789012345678901234567890 件");

type Sample = { id: string; type: string; ref: string; build: (v: V, c: boolean) => ReactNode };
const S: Sample[] = [
  { id: "CompanyAddressModal(#4)", type: "G1", ref: "frontend/src/pages/company-detail/CompanyAddressModal.tsx:78-81,147-153（.modal-content-wide > form.form-grid > div.form-row、#10 ContactsPage.tsx:303-304,333 も同じ親）", build: (v, c) => pane(560, <div className="modal-content-wide"><form className="form-grid"><div className="form-row"><label>国コード</label><TextField value="JP" onChange={noop} /></div>{g1(v, c)}</form></div>) },
  { id: "CompanyDiscordTab(#6)", type: "G1", ref: "frontend/src/pages/company-detail/CompanyDiscordTab.tsx:38-48（div > form > div.form-grid > div.form-row、.modal-content-wide なし。#1 ContactChannelForm.tsx:192,225、#5 CompanyContactsTab.tsx:156,206 も .form-grid 直下）", build: (v, c) => pane(560, <div><form><div className="form-grid"><div className="form-row"><label>名前</label><TextField value="サンプル" onChange={noop} /></div>{g1(v, c)}</div></form></div>) },
  { id: "InventoryFilterPanel(#15)", type: "G2", ref: "frontend/src/pages/inventory/InventoryFilterPanel.tsx:101-115,132-141（section.inventory-filter-panel: flex column gap space-3 padding space-3、label が直下）", build: (v, c) => (
    <section data-sample style={{ width: "min(900px, 100vw)", boxSizing: "border-box", display: "flex", flexDirection: "column", gap: "var(--space-3)", padding: "var(--space-3)", background: "var(--bg-surface)", border: "1px solid var(--border)" }}>
      {g2a(v, c)}<div style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>カテゴリー</div>
    </section>) },
  { id: "InventoryFilterPanel(#16)", type: "G2", ref: "frontend/src/pages/inventory/InventoryFilterPanel.tsx:146-160（div flex wrap gap space-2 の中に3つ並ぶ。#17-#20 も同じ形）", build: (v, c) => (
    <section data-sample style={{ width: "min(900px, 100vw)", boxSizing: "border-box", display: "flex", flexDirection: "column", gap: "var(--space-3)", padding: "var(--space-3)", background: "var(--bg-surface)", border: "1px solid var(--border)" }}>
      <div><div style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}>カテゴリー</div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)" }}>{[["ポケモン", c], ["遊戯王", true], ["ワンピース", false]].map(([n, ch], i) => g2b(v, ch as boolean, n as string, String(i)))}</div></div>
    </section>) },
  { id: "NoteMasterPage(#21)", type: "G2-same-row", ref: "frontend/src/pages/note-master/NoteMasterPage.tsx:271-315（grid 1fr 1fr、form-group 5 件の後＝右列で priority の TextField と同じ行）", build: (v, c) => grid2("ggggg", g2same(v, c)) },
  { id: "ProductCategoriesPage(#22)", type: "G2-same-row", ref: "frontend/src/pages/product-categories/ProductCategoriesPage.tsx:199-225（grid 1fr 1fr、form-group 3 件の後＝右列で同じ行）", build: (v, c) => grid2("ggg", g2same(v, c)) },
  { id: "UnitsPage(#32)", type: "G2-same-row", ref: "frontend/src/pages/units/UnitsPage.tsx:275-301（grid 1fr 1fr、form-group 3 件の後＝右列で同じ行）", build: (v, c) => grid2("ggg", g2same(v, c)) },
  { id: "UnitsPage(#33)", type: "G2-same-row", ref: "frontend/src/pages/units/UnitsPage.tsx:326-353（grid 1fr 1fr、form-group 3 件の後＝右列で同じ行）", build: (v, c) => grid2("ggg", g2same(v, c)) },
  { id: "ConditionsPage(#8)", type: "G3", ref: "frontend/src/pages/conditions/ConditionsPage.tsx:302-359（grid 1fr 1fr、form-group 数件＋全幅 form-group の後に全幅のチェック欄。#31 StatusMasterPage.tsx:300-307 も同じ）", build: (v, c) => grid2("ggggFF", g3(v, c)) },
  { id: "RolesPage(#24,#25)", type: "G4", ref: "frontend/src/pages/roles/RolesPage.tsx:396-415（div.permission-group-toggles の中に2つ）", build: (v, c) => pane(560, g4(v, c)) },
  { id: "InventoryVisibilityPage(#3)", type: "G5", ref: "frontend/src/pages/admin/InventoryVisibilityPage.tsx:133,153-159（table.data-table の td）", build: (v, c) => pane(720, <table className="data-table"><thead><tr><th>ロール</th><th>表示</th></tr></thead><tbody><tr><td>管理者</td><td>{g5(v, c, { "data-testid": "vis-1-x" })}</td></tr></tbody></table>) },
  { id: "ConditionsPage(#7)", type: "G5", ref: "frontend/src/pages/conditions/ConditionsPage.tsx:249-258（DataTable の renderCell。td.comp-table__td）", build: (v, c) => pane(720, <table className="comp-table__table"><thead><tr><th className="comp-table__th"></th><th className="comp-table__th">コード</th></tr></thead><tbody><tr><td className="comp-table__td">{g5(v, c, {})}</td><td className="comp-table__td">A</td></tr></tbody></table>) },
  { id: "ProductsPage(#23)", type: "G5", ref: "frontend/src/pages/products/ProductsPage.tsx:289,355-362（table.data-table width 100%、td rowSpan=2 text-align center vertical-align middle）", build: (v, c) => pane(720, <table className="data-table" style={{ width: "100%" }}><thead><tr><th>選択</th><th>名前</th></tr></thead><tbody><tr><td rowSpan={2} style={{ textAlign: "center", verticalAlign: "middle" }}>{g5(v, c, { "data-testid": "product-select-1" })}</td><td>商品</td></tr><tr><td>詳細</td></tr></tbody></table>) },
  { id: "InboxConversationList(#11)", type: "G6", ref: "frontend/src/pages/inbox/InboxConversationList.tsx:117-148（.inbox-bulk-bar: flex、右に .inbox-bulk-count flex:1 と操作ボタン4つ。文言は locales/ja.json:1286。#12 Mobile.tsx:141-171 も同じ）", build: G6_REAL },
  { id: "InboxConversationList(#11)-stress", type: "G6-stress", ref: "同上。行全体が幅 360 を超える長い文字（数字 30 桁）での縮み検証（実際の文言ではない）", build: G6_STRESS },
];

(globalThis as any).window = { matchMedia: () => ({ matches: false, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {} }) };
const h = (n: ReactNode) => renderToStaticMarkup(n as any);
process.stdout.write(
  JSON.stringify(
    S.map((s) => ({ id: s.id, type: s.type, ref: s.ref, html: { before: { u: h(s.build("before", false)), c: h(s.build("before", true)) }, after: { u: h(s.build("after", false)), c: h(s.build("after", true)) } } })),
  ),
);
