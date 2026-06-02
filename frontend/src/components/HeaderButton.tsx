/**
 * HeaderButton — ページヘッダーアクション用ボタン SSoT (ADR-069)
 *
 * CSSクラスへのマッピングのみを担う薄いラッパー。スタイル定義は components.css に集約済み。
 * variant="icon" の場合は aria-label が必須（TypeScript で強制）。
 *
 * 使用例:
 *   <HeaderButton variant="ghost" onClick={...}>{t("nav.templates")}</HeaderButton>
 *   <HeaderButton variant="icon" aria-label={t("inbox.settings.title")} data-tooltip={t("inbox.settings.tooltip")}>
 *     <PAGE_ICONS.settingsSolid size={ICON.md} aria-hidden="true" />
 *   </HeaderButton>
 */
import type { ReactNode } from "react";

// variant → CSSクラス の1対1マッピング（components.css に定義済み）
const VARIANT_CLASS = {
  primary: "btn-primary",
  secondary: "btn-secondary",
  ghost: "btn-ghost",
  icon: "icon-btn",
} as const;

type BaseProps = {
  onClick?: () => void;
  disabled?: boolean;
  children: ReactNode;
  "data-tooltip"?: string;
  "data-testid"?: string;
};

// テキストボタン: aria-label は任意
type TextButtonProps = BaseProps & {
  variant: "ghost" | "primary" | "secondary";
  "aria-label"?: string;
};

// アイコンボタン: aria-label 必須（アクセシビリティ要件）
type IconButtonProps = BaseProps & {
  variant: "icon";
  "aria-label": string;
};

export type HeaderButtonProps = TextButtonProps | IconButtonProps;

export function HeaderButton(props: HeaderButtonProps) {
  const { variant, onClick, disabled, children } = props;
  return (
    <button
      type="button"
      className={VARIANT_CLASS[variant]}
      onClick={onClick}
      disabled={disabled}
      aria-label={"aria-label" in props ? props["aria-label"] : undefined}
      data-tooltip={"data-tooltip" in props ? props["data-tooltip"] : undefined}
      data-testid={"data-testid" in props ? props["data-testid"] : undefined}
    >
      {children}
    </button>
  );
}
