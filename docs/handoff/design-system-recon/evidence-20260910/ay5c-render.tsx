// AY-5c 試料の生成。RolesPage.tsx の色見本（パレット外の現在色）を写す。前は属性なし、後は data-current-label 付き。
import { renderToStaticMarkup } from "react-dom/server";
import { RadioControl } from "@src/components/RadioControl";

const sample = (label: string | null) => {
  const extra = label === null ? {} : { "data-current-label": label };
  return renderToStaticMarkup(
    <div data-sample className="comp-modal-dialog comp-modal-dialog--md" style={{ margin: 16, paddingBottom: 24 }}>
      <div className="comp-modal-body">
        <form>
          <div className="form-group">
            <div className="color-picker" role="radiogroup" aria-label="color">
              <label className="color-swatch selected color-swatch-legacy" style={{ background: "rgb(18, 52, 86)" }} title="x" {...extra}>
                <RadioControl name="role-color" value="x" checked readOnly />
              </label>
            </div>
          </div>
        </form>
      </div>
    </div>,
  );
};
console.log(JSON.stringify({ before: { ja: sample(null) }, after: { ja: sample("現在"), en: sample("Current") } }));
