// AY-5 試料の生成。前: origin/main(b6435490b) の JSX を写したマークアップ。後: 本物の Radio / RadioControl が描く DOM。
// 祖先の写し方は ay5-measure-ancestry.md に file:line で記録。
import { renderToStaticMarkup } from "react-dom/server";
import type { CSSProperties, ReactNode } from "react";
import { Radio } from "@src/components/Radio";
import { RadioControl } from "@src/components/RadioControl";

const noop = () => {};
type Side = "before" | "after";
type State = "u" | "c";

/* ---------- R1: RegisterPage.tsx（前 :456-475 / 後 :456-475 付近）---------- */
const fieldsetStyle: CSSProperties = { border: "1px solid var(--border-default)", borderRadius: "var(--radius-md)", padding: "var(--spacing-4)", marginBottom: "var(--spacing-4)" };
const requiredMark = <span style={{ color: "var(--color-red-500)", fontWeight: "var(--font-weight-bold)" }}>*</span>;
const T = { q: "配送先住所を登録しますか？", a: "配送先住所を登録する", b: "請求先と同じ住所に配送する", s1: "セクション1 - 請求先住所登録" };

const r1Choices = (side: Side, state: State): ReactNode =>
  side === "before" ? (
    <>
      <label style={{ display: "flex", alignItems: "center", gap: "var(--spacing-2)", cursor: "pointer" }}>
        <input type="radio" name="shipping_choice" value="proceed" checked={state === "c"} onChange={noop} />
        {T.a}
      </label>
      <label style={{ display: "flex", alignItems: "center", gap: "var(--spacing-2)", cursor: "pointer", marginTop: "var(--spacing-1)" }}>
        <input type="radio" name="shipping_choice" value="same" checked={false} onChange={noop} />
        {T.b}
      </label>
    </>
  ) : (
    <>
      <div>
        <Radio name="shipping_choice" value="proceed" checked={state === "c"} onChange={noop} label={T.a} />
      </div>
      <div>
        <Radio name="shipping_choice" value="same" checked={false} onChange={noop} label={T.b} />
      </div>
    </>
  );

const r1 = (side: Side, state: State) =>
  renderToStaticMarkup(
    <div data-sample className="page-container" style={{ maxWidth: "600px", margin: "0 auto", padding: "var(--spacing-6)" }}>
      <form>
        <fieldset style={fieldsetStyle}>
          <legend style={{ fontWeight: "var(--font-weight-bold)" }}>{T.s1}</legend>
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-3)" }}>
            <div style={{ marginTop: "var(--spacing-3)" }}>
              <p style={{ fontWeight: "var(--font-weight-bold)", marginBottom: "var(--spacing-2)" }}>
                {T.q} {requiredMark}
              </p>
              {r1Choices(side, state)}
            </div>
          </div>
        </fieldset>
      </form>
    </div>,
  );

/* ---------- R3/R4: RolesPage.tsx（前 :458-492）---------- */
const swatch = (side: Side, o: { c: string; checked: boolean; legacy?: boolean }) => {
  const cls = `color-swatch ${o.legacy ? "selected color-swatch-legacy" : o.checked ? "selected" : ""}`.trim();
  const props = o.legacy ? { checked: true, readOnly: true } : { checked: o.checked, onChange: noop };
  return (
    <label key={o.c} className={cls} style={{ background: o.c }} title={o.c} data-swatch>
      {side === "before" ? (
        <input type="radio" name="role-color" value={o.c} {...props} />
      ) : (
        <RadioControl name="role-color" value={o.c} {...props} />
      )}
    </label>
  );
};
const r34 = (side: Side, state: State) => {
  // u: 既存色がパレットに無い（legacy が選択・R3）＋パレット2つ。c: legacy 無し・パレット3つのうち1つ目が選択（R4）。
  const items =
    state === "u"
      ? [{ c: "#123456", checked: true, legacy: true }, { c: "#ef4444", checked: false }, { c: "#f97316", checked: false }]
      : [{ c: "#ef4444", checked: true }, { c: "#f97316", checked: false }, { c: "#eab308", checked: false }];
  return renderToStaticMarkup(
    <div data-sample className="comp-modal-dialog comp-modal-dialog--md" style={{ margin: 16 }}>
      <div className="comp-modal-header"><h2 className="comp-modal-title">ロール編集</h2></div>
      <div className="comp-modal-body">
        <form>
          <div className="form-group">
            <label>色</label>
            <div className="color-picker" role="radiogroup" aria-label="色">
              {items.map((o) => swatch(side, o))}
            </div>
          </div>
        </form>
      </div>
    </div>,
  );
};

/* ---------- R5: MergeCompanyModal.tsx（前 :146-147,:182-190,:200-231）---------- */
const r5 = (side: Side, state: State) => {
  const rows = [
    { id: 1, code: "C-0001", name: "株式会社サンプル", status: "active" },
    { id: 2, code: "C-0002", name: "テスト商事", status: "active" },
  ];
  const sel = state === "c" ? 1 : 0;
  return renderToStaticMarkup(
    <div data-sample className="comp-modal-dialog comp-modal-dialog--md" style={{ margin: 16 }}>
      <div className="comp-modal-header"><h2 className="comp-modal-title">会社を統合</h2></div>
      <div className="comp-modal-body">
        <div className="modal-content-wide">
          <div style={{ maxHeight: "var(--dropdown-list-h)", overflowY: "auto", border: "1px solid var(--border-light)", borderRadius: "var(--radius-sm)", marginTop: "var(--space-2)" }}>
            <table className="data-table" style={{ marginBottom: 0 }}>
              <thead>
                <tr>
                  <th style={{ width: "var(--col-width-checkbox)" }}></th>
                  <th>コード</th><th>名称</th><th>状態</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((c) => (
                  <tr key={c.id} data-row style={{ cursor: "pointer", background: c.id === sel ? "var(--warning-bg)" : undefined }}>
                    <td>
                      {side === "before" ? (
                        <input type="radio" name="master-candidate" checked={c.id === sel} onChange={noop} />
                      ) : (
                        <RadioControl name="master-candidate" checked={c.id === sel} onChange={noop} />
                      )}
                    </td>
                    <td>{c.code}</td>
                    <td>{c.name}</td>
                    <td><span className={`status-badge status-${c.status}`}>{c.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>,
  );
};

const build = (side: Side) => ({
  r1: { u: r1(side, "u"), c: r1(side, "c") },
  r34: { u: r34(side, "u"), c: r34(side, "c") },
  r5: { u: r5(side, "u"), c: r5(side, "c") },
});
console.log(JSON.stringify({ before: build("before"), after: build("after") }));
