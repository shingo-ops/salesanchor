/**
 * HeaderButton — ページヘッダーアクション用ボタン SSoT (ADR-069)
 *
 * テキスト操作は標準 Button、アイコン操作は既存 icon-btn を使用する薄いラッパー。
 * variant="icon" の場合は aria-label が必須（TypeScript で強制）。
 *
 * 使用例:
 *   <HeaderButton variant="ghost" onClick={...}>{t("nav.templates")}</HeaderButton>
 *   <HeaderButton variant="icon" aria-label={t("inbox.settings.title")} data-tooltip={t("inbox.settings.tooltip")}>
 *     <PAGE_ICONS.settingsSolid size={ICON.md} aria-hidden="true" />
 *   </HeaderButton>
 */
import type { ReactNode } from "react";
import { Button } from "./Button";

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
  const ariaLabel = "aria-label" in props ? props["aria-label"] : undefined;
  const tooltip = "data-tooltip" in props ? props["data-tooltip"] : undefined;
  const testId = "data-testid" in props ? props["data-testid"] : undefined;

  if (variant !== "icon") {
    return (
      <Button
        type="button"
        variant={variant}
        size="md"
        onClick={onClick}
        disabled={disabled}
        aria-label={ariaLabel}
        data-tooltip={tooltip}
        data-testid={testId}
      >
        {children}
      </Button>
    );
  }

  return (
    <button
      type="button"
      className="icon-btn"
      onClick={onClick}
      disabled={disabled}
      aria-label={ariaLabel}
      data-tooltip={tooltip}
      data-testid={testId}
    >
      {children}
    </button>
  );
}
