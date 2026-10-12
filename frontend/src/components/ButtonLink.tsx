import { forwardRef } from "react";
import type { AnchorHTMLAttributes, ReactNode } from "react";
import { Link } from "react-router-dom";
import type { LinkProps } from "react-router-dom";
import { buttonAppearance } from "./buttonAppearance";
import type { ButtonSize, ButtonVariant } from "./buttonAppearance";
import "./Button.css";

type ButtonLinkVariant = Exclude<ButtonVariant, "tab">;

interface ButtonLinkOwnProps {
  variant?: ButtonLinkVariant;
  size?: ButtonSize;
  fullWidth?: boolean;
  children?: ReactNode;
  /** 同じリンク要素への外側配置専用クラス */
  layoutClassName?: string;
}

type AppearanceKeys = keyof ButtonLinkOwnProps | "className" | "style";

type RouterButtonLinkProps = ButtonLinkOwnProps
  & Omit<LinkProps, AppearanceKeys | "to" | "href">
  & { to: LinkProps["to"]; href?: never };

type AnchorButtonLinkProps = ButtonLinkOwnProps
  & Omit<AnchorHTMLAttributes<HTMLAnchorElement>, AppearanceKeys | "href">
  & { href: string; to?: never };

export type ButtonLinkProps = RouterButtonLinkProps | AnchorButtonLinkProps;

function isRouterButtonLink(props: ButtonLinkProps): props is RouterButtonLinkProps {
  return "to" in props && props.to !== undefined;
}

export const ButtonLink = forwardRef<HTMLAnchorElement, ButtonLinkProps>(function ButtonLink(props, ref) {
  const className = buttonAppearance({
    variant: props.variant ?? "primary",
    size: props.size ?? "md",
    fullWidth: props.fullWidth,
    layoutClassName: props.layoutClassName,
  });

  if (isRouterButtonLink(props)) {
    const { variant, size, fullWidth, layoutClassName, children, to, ...rest } = props;
    void [variant, size, fullWidth, layoutClassName];
    return <Link ref={ref} className={className} to={to} {...rest}>{children}</Link>;
  }

  const { variant, size, fullWidth, layoutClassName, children, href, ...rest } = props;
  void [variant, size, fullWidth, layoutClassName];
  return <a ref={ref} className={className} href={href} {...rest}>{children}</a>;
});
