// STEP-C test: raw <select> in pages/ — should be blocked by UI governance gate
import { t } from '../../i18n';

export function UIGateBlockTest() {
  return (
    <div>
      <select value="" onChange={() => {}}>
        <option value="">{t("test.placeholder")}</option>
      </select>
    </div>
  );
}
