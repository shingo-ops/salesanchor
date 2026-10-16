// AY-4b 実測用: 型ごとの「実物の親」の HTML 断片を前後で作り JSON に出す（金型の DOM は本物を renderToStaticMarkup。手書きしない）。
// 変更前のマークアップは origin/main の実ファイルのチェック欄部分をそのまま写している（ref に file:line）。
// "@src" は esbuild の alias で frontend/src（作業ツリー）を指す。TextField など変更していない部品は前後で同じもの。
import { renderToStaticMarkup } from "react-dom/server";
import { Fragment, type ReactNode } from "react";
import { Checkbox } from "@src/components/Checkbox";
import { CheckboxControl } from "@src/components/CheckboxControl";
import { TextField, TextFieldControl } from "@src/components/TextField";
import { TextareaControl } from "@src/components/Textarea";

type V = "before" | "after";
const noop = () => {};
const L = "有効にする";
const TF = (label: string) => <TextField label={label} value="サンプル" onChange={noop} />;
const G = (label: string, full = false) => (
  <div className="form-group" style={full ? { gridColumn: "1 / -1" } : undefined}>{TF(label)}</div>
);

// ---- チェック欄そのもの（前=実ファイルのマークアップ、後=金型）----
// A: label のインライン style（flex, gap）。例 ProductCategoriesMasterPanel.tsx:280-287
const boxA = (v: V, c: boolean) =>
  v === "before" ? (
    <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
      <input type="checkbox" checked={c} onChange={noop} />
      {L}
    </label>
  ) : (
    <Checkbox label={L} checked={c} onChange={noop} />
  );
// A': RuleTestPanel.tsx:483-490
const boxA2 = (v: V, c: boolean) =>
  v === "before" ? (
    <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", cursor: "pointer" }}>
      <input type="checkbox" checked={c} onChange={noop} />
      <span style={{ fontSize: "var(--font-sm)" }}>{L}</span>
    </label>
  ) : (
    <Checkbox label={L} checked={c} onChange={noop} />
  );
// B: DistributionTargetForm.tsx:238-245
const boxB = (v: V, c: boolean) =>
  v === "before" ? (
    <label className="dist-checkbox-row">
      <input type="checkbox" checked={c} onChange={noop} />
      {L}
    </label>
  ) : (
    <Checkbox label={L} checked={c} onChange={noop} />
  );
// C: FedexLabelValidationTab.tsx:288-295
const boxC = (v: V, c: boolean) =>
  v === "before" ? (
    <label className="lv-check-label">
      <input type="checkbox" checked={c} onChange={noop} />
      {L}
    </label>
  ) : (
    <Checkbox label={L} checked={c} onChange={noop} />
  );
// D: ProductMasterDrawer.tsx:233-240
const boxD = (v: V, c: boolean) =>
  v === "before" ? (
    <label className="pmd-confirm-check">
      <input type="checkbox" checked={c} onChange={noop} />
      {L}
    </label>
  ) : (
    <Checkbox label={L} checked={c} onChange={noop} />
  );
// E: ExtractionPromptConfigTab.tsx:199-221
const boxE = (v: V, c: boolean) =>
  v === "before" ? (
    <label
      style={{
        display: "flex",
        alignItems: "center",
        gap: "var(--space-2)",
        marginBottom: "var(--space-3)",
        fontSize: "var(--font-sm)",
        color: "var(--text-secondary)",
      }}
    >
      <input type="checkbox" checked={c} onChange={noop} />
      {L}
    </label>
  ) : (
    <div style={{ marginBottom: "var(--space-3)" }}>
      <Checkbox label={L} checked={c} onChange={noop} />
    </div>
  );
// F: KnowledgeAliasesTab.tsx:339-347 / :415-423
const boxF = (v: V, c: boolean) =>
  v === "before" ? (
    <input type="checkbox" checked={c} onChange={noop} aria-label="pattern" data-testid="rule-select-1" />
  ) : (
    <CheckboxControl checked={c} onChange={noop} aria-label="pattern" data-testid="rule-select-1" />
  );

// ---- 親 ----
const drawer = (children: ReactNode) => (
  <div data-sample style={{ width: "min(var(--drawer-panel-w-default), 100vw)", boxSizing: "border-box", padding: "var(--space-5) var(--space-6)", background: "var(--bg-surface)" }}>{children}</div>
);
const GRID2 = { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-3) var(--space-4)" } as const;
// kids: "g"=form-group, "F"=全幅 form-group
const grid2 = (kids: string, slot: ReactNode) =>
  drawer(
    <form>
      <div style={GRID2}>
        {kids.split("").map((k, i) => <Fragment key={i}>{G("項目" + (i + 1), k === "F")}</Fragment>)}
        {slot}
      </div>
    </form>,
  );

type Sample = { id: string; type: string; ref: string; build: (v: V, c: boolean) => ReactNode };
const S: Sample[] = [
  // A-同じ行（チェック欄が左の TextField と同じ行の右列）
  { id: "ProductCategoriesMasterPanel", type: "A-same-row", ref: "frontend/src/pages/super-admin/components/ProductCategoriesMasterPanel.tsx:256-287（form-group 3 件の後）", build: (v, c) => grid2("ggg", boxA(v, c)) },
  { id: "UnitMasterPanel", type: "A-same-row", ref: "frontend/src/pages/super-admin/components/UnitMasterPanel.tsx:307-338（form-group 3 件の後）", build: (v, c) => grid2("ggg", boxA(v, c)) },
  { id: "NoteMasterPanel", type: "A-same-row", ref: "frontend/src/pages/super-admin/components/NoteMasterPanel.tsx:258-307（form-group 5 件の後）", build: (v, c) => grid2("ggggg", boxA(v, c)) },
  { id: "QuantityUnitsMasterPanel", type: "A-same-row", ref: "frontend/src/pages/super-admin/components/QuantityUnitsMasterPanel.tsx:201-248（form-group 5 件の後）", build: (v, c) => grid2("ggggg", boxA(v, c)) },
  { id: "TypeMasterPanel", type: "A-same-row", ref: "frontend/src/pages/super-admin/components/TypeMasterPanel.tsx:225-275（form-group 5 件の後）", build: (v, c) => grid2("ggggg", boxA(v, c)) },
  // KnowledgeAliasesTab.tsx:481 は form-group 5 件の後＝同じ行（6 番目）。左はラベル＋入力欄の form-group
  { id: "KnowledgeAliasesTab(#10)", type: "A-same-row", ref: "frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:436-483（grid 1fr 1fr、form-group 5 件の後）", build: (v, c) => grid2("gggg", <><div className="form-group"><label>言語</label><TextFieldControl value="ja" onChange={noop} /></div>{boxA(v, c)}</>) },
  // A-単独行（grid でチェック欄だけの行）
  { id: "ConditionDefsMasterPanel", type: "A-alone-row", ref: "frontend/src/pages/super-admin/components/ConditionDefsMasterPanel.tsx:194-233（form-group 4 件の後）", build: (v, c) => grid2("gggg", boxA(v, c)) },
  { id: "ConditionsMasterPanel", type: "A-alone-row", ref: "frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:318-449（g,g,F,F,F,g,g,g,g,F の後）", build: (v, c) => grid2("ggFFFggggF", boxA(v, c)) },
  { id: "ProductFormatsMasterPanel", type: "A-alone-row", ref: "frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx:251-318（form-group 6 件の後）", build: (v, c) => grid2("gggggg", boxA(v, c)) },
  { id: "ProductKindsMasterPanel", type: "A-alone-row", ref: "frontend/src/pages/super-admin/components/ProductKindsMasterPanel.tsx:191-230（form-group 4 件の後）", build: (v, c) => grid2("gggg", boxA(v, c)) },
  { id: "ProductLinesMasterPanel", type: "A-alone-row", ref: "frontend/src/pages/super-admin/components/ProductLinesMasterPanel.tsx:250-317（form-group 6 件の後）", build: (v, c) => grid2("gggggg", boxA(v, c)) },
  { id: "SupplierMasterPanel", type: "A-alone-row", ref: "frontend/src/pages/super-admin/components/SupplierMasterPanel.tsx:311-380（F,g,g,F,g,g,g,g,F の後）", build: (v, c) => grid2("FggFggggF", boxA(v, c)) },
  { id: "UnitIgnorePhrasesPanel", type: "A-alone-row", ref: "frontend/src/pages/super-admin/components/UnitIgnorePhrasesPanel.tsx:155-175（grid 1fr、TextField 2 件の後）", build: (v, c) => drawer(<form><div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "var(--space-3)" }}>{TF("項目1")}{TF("項目2")}{boxA(v, c)}</div></form>) },
  { id: "WeightClassesMasterPanel", type: "A-alone-row", ref: "frontend/src/pages/super-admin/components/WeightClassesMasterPanel.tsx:205-260（form-group 6 件の後）", build: (v, c) => grid2("gggggg", boxA(v, c)) },
  // #1 SupplierDetailDrawer.tsx:341-420: form.product-detail__form（flex column, gap space-4）。未到達
  { id: "SupplierDetailDrawer(#1)", type: "A-alone-row", ref: "frontend/src/features/supplier-master/SupplierDetailDrawer.tsx:341-420（form.product-detail__form: flex column gap space-4、未到達）", build: (v, c) => drawer(<form className="product-detail__form"><TextField label="名前" value="サンプル" onChange={noop} fullWidth />{boxA(v, c)}<div style={{ marginTop: "var(--space-4)" }}>{TF("項目")}</div></form>) },
  // A'
  { id: "RuleTestPanel", type: "A2-span", ref: "frontend/src/pages/super-admin/components/RuleTestPanel.tsx:463-490（flex column gap space-4）", build: (v, c) => drawer(<div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>{TF("項目1")}{boxA2(v, c)}{TF("メモ")}</div>) },
  // B
  { id: "DistributionTargetForm", type: "B-dist", ref: "frontend/src/features/tcg-distribution/DistributionTargetForm.tsx:200-245（.dist-drawer-body: flex column gap space-4、.dist-field の後）", build: (v, c) => (
    <div data-sample style={{ width: "min(var(--drawer-panel-w-default), 100vw)", boxSizing: "border-box", background: "var(--bg-surface)" }}>
      <div className="dist-drawer-body"><div className="dist-field"><label htmlFor="sn">シート名</label><TextFieldControl id="sn" value="Sheet1" onChange={noop} /></div>{boxB(v, c)}</div>
    </div>) },
  // C
  { id: "FedexLabelValidationTab", type: "C-lv", ref: "frontend/src/pages/integrations/FedexLabelValidationTab.tsx:285-295（section.lv-step.card、p.form-hint の下、未到達）", build: (v, c) => (
    <div data-sample style={{ width: "min(560px, 100vw)", boxSizing: "border-box" }}>
      <section className="lv-step card"><div className="lv-step-header"><span className="lv-step-num">3</span><strong>ステップ</strong></div><p className="form-hint">説明文のサンプルです。</p>{boxC(v, c)}</section>
    </div>) },
  // D
  { id: "ProductMasterDrawer", type: "D-pmd", ref: "frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:228-241（section.pmd-warning）", build: (v, c) => drawer(<section className="pmd-warning"><strong>重複の警告</strong><p>PM-00001: タイトル</p>{boxD(v, c)}</section>) },
  // E
  { id: "ExtractionPromptConfigTab", type: "E-prompt", ref: "frontend/src/pages/super-admin/ExtractionPromptConfigTab.tsx:150-232（カード内、見出しの下・TextareaControl の上）", build: (v, c) => (
    <div data-sample style={{ width: "min(720px, 100vw)", boxSizing: "border-box" }}>
      <div className="card"><div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "var(--space-3)" }}><strong>プロンプト</strong></div>{boxE(v, c)}<TextareaControl value="プロンプト本文" onChange={noop} rows={6} textStyle="code" /></div>
    </div>) },
  // F
  { id: "KnowledgeAliasesTab(#8)", type: "F-td", ref: "frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:339-347（table.data-table の td、text-align center）", build: (v, c) => (
    <div data-sample style={{ width: "min(720px, 100vw)", boxSizing: "border-box", background: "var(--bg-surface)" }}>
      <table className="data-table"><thead><tr><th></th><th>カテゴリ</th><th>パターン</th></tr></thead><tbody><tr><td style={{ textAlign: "center" }}>{boxF(v, c)}</td><td>カテゴリ</td><td><code>pattern</code></td></tr></tbody></table>
    </div>) },
  { id: "KnowledgeAliasesTab(#9)", type: "F-td", ref: "frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:415-423（table.data-table の td、text-align center）", build: (v, c) => (
    <div data-sample style={{ width: "min(720px, 100vw)", boxSizing: "border-box", background: "var(--bg-surface)" }}>
      <table className="data-table"><thead><tr><th></th><th>仕入元</th><th>別名</th></tr></thead><tbody><tr><td style={{ textAlign: "center" }}>{boxF(v, c)}</td><td>仕入元</td><td><code>alias</code></td></tr></tbody></table>
    </div>) },
];

(globalThis as any).window = { matchMedia: () => ({ matches: false, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {} }) };
const h = (n: ReactNode) => renderToStaticMarkup(n as any);
process.stdout.write(
  JSON.stringify(
    S.map((s) => ({ id: s.id, type: s.type, ref: s.ref, html: { before: { u: h(s.build("before", false)), c: h(s.build("before", true)) }, after: { u: h(s.build("after", false)), c: h(s.build("after", true)) } } })),
  ),
);
