export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "outline" | "tab";
export type ButtonSize = "sm" | "md" | "lg";

const VARIANT_CLASS: Record<ButtonVariant, string> = {
  primary:   "comp-btn--primary",
  secondary: "comp-btn--secondary",
  ghost:     "comp-btn--ghost",
  danger:    "comp-btn--danger",
  outline:   "comp-btn--outline",
  tab:       "comp-btn--tab",
};

interface ButtonAppearanceOptions {
  variant: ButtonVariant;
  size: ButtonSize;
  fullWidth?: boolean;
  loading?: boolean;
  active?: boolean;
  iconOnly?: boolean;
  layoutClassName?: string;
}

export function buttonAppearance({
  variant,
  size,
  fullWidth = false,
  loading = false,
  active = false,
  iconOnly = false,
  layoutClassName,
}: ButtonAppearanceOptions): string {
  const isTab = variant === "tab";
  return [
    "comp-btn",
    VARIANT_CLASS[variant],
    isTab ? "" : (size === "sm" ? "comp-btn--sm" : size === "lg" ? "comp-btn--lg" : ""),
    isTab && active ? "comp-btn--active" : "",
    fullWidth  ? "comp-btn--full"      : "",
    loading    ? "comp-btn--loading"   : "",
    iconOnly   ? "comp-btn--icon-only" : "",
    layoutClassName ?? "",
  ].filter(Boolean).join(" ");
}
