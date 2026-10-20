import "./ContentToolbar.css";
import { TextFieldControl } from "./TextField";

interface ContentToolbarProps {
  /** 左スロット: フィルタ・検索・タブ切替 */
  left?: React.ReactNode;
  /** 右スロット: 実行ボタン（Button金型 primary 1個＋secondary。ghost設定系はヘッダーへ） */
  right?: React.ReactNode;
  /** 2段目の左（並び替え・絞り込み）。bottomLeft/bottomRight のどちらかを渡したときだけ2段になる */
  bottomLeft?: React.ReactNode;
  /** 2段目の右（切替・リセット） */
  bottomRight?: React.ReactNode;
}

/**
 * 操作台（ContentToolbar・page-header-v2 改訂5・第3の金型）
 * design: docs/specs/design-system/component-ssot/page-header-v2/design.md §2.5
 * 1本の横棒で 左=フィルタ / 右=実行ボタン を同一X軸に揃える。
 * 親ページ: ヘッダー直下に置く / 子ページ: 子タイトル行と同一X軸に置く。
 * 高さ・余白は本部品が独占（ページ側の手書きmargin/paddingは禁止）。
 * 2段目の枠（bottomLeft/bottomRight）は任意。渡さないときは従来の1段 DOM のまま。
 */
export function ContentToolbar({ left, right, bottomLeft, bottomRight }: ContentToolbarProps) {
  if (bottomLeft === undefined && bottomRight === undefined) {
    return (
      <div className="content-toolbar">
        <div className="content-toolbar__left">{left}</div>
        <div className="content-toolbar__right">{right}</div>
      </div>
    );
  }
  return (
    <div className="content-toolbar content-toolbar--two-rows">
      <div className="content-toolbar__row">
        <div className="content-toolbar__left">{left}</div>
        <div className="content-toolbar__right">{right}</div>
      </div>
      <div className="content-toolbar__row">
        <div className="content-toolbar__left">{bottomLeft}</div>
        <div className="content-toolbar__right">{bottomRight}</div>
      </div>
    </div>
  );
}

export interface ContentToolbarRangeProps {
  minValue: string;
  maxValue: string;
  onMinChange: (v: string) => void;
  onMaxChange: (v: string) => void;
  /** 表示文字（t() で渡す） */
  minPlaceholder: string;
  maxPlaceholder: string;
  minAriaLabel: string;
  maxAriaLabel: string;
  /** `${prefix}-min` / `${prefix}-max` が data-testid になる */
  testIdPrefix: string;
}

/** 範囲入力（数字2つを「〜」でつなぐ）。幅は --input-width-price。 */
export function ContentToolbarRange({
  minValue,
  maxValue,
  onMinChange,
  onMaxChange,
  minPlaceholder,
  maxPlaceholder,
  minAriaLabel,
  maxAriaLabel,
  testIdPrefix,
}: ContentToolbarRangeProps) {
  return (
    <div className="content-toolbar__range">
      <TextFieldControl
        type="number"
        min="0"
        inputMode="numeric"
        className="field-h-md content-toolbar__range-input"
        data-testid={`${testIdPrefix}-min`}
        value={minValue}
        placeholder={minPlaceholder}
        aria-label={minAriaLabel}
        onChange={(e) => onMinChange(e.target.value)}
      />
      <span className="content-toolbar__range-sep" aria-hidden="true">〜</span>
      <TextFieldControl
        type="number"
        min="0"
        inputMode="numeric"
        className="field-h-md content-toolbar__range-input"
        data-testid={`${testIdPrefix}-max`}
        value={maxValue}
        placeholder={maxPlaceholder}
        aria-label={maxAriaLabel}
        onChange={(e) => onMaxChange(e.target.value)}
      />
    </div>
  );
}
