/**
 * TextLink — 枠のない文字リンク金型（design.md login-round-inputs §6.1）
 *
 * - onClick を渡すと <button type="button">（画面の切り替えだけで移動しない操作）
 * - to を渡すと react-router の <Link>（移動する操作）
 * どちらか片方だけ（型で強制）。色・下線・focus は TextLink.css が持つ。
 * ページ側から className / style は渡せない。
 */
import { forwardRef } from "react";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Link } from "react-router-dom";
import type { LinkProps } from "react-router-dom";
import "./TextLink.css";

const ROOT_CLASS = "comp-text-link";

type AppearanceKeys = "className" | "style";

interface TextLinkOwnProps {
  children?: ReactNode;
}

type ButtonTextLinkProps = TextLinkOwnProps
  & Omit<ButtonHTMLAttributes<HTMLButtonElement>, AppearanceKeys | "type" | "children">
  & { onClick: NonNullable<ButtonHTMLAttributes<HTMLButtonElement>["onClick"]>; to?: never };

type RouterTextLinkProps = TextLinkOwnProps
  & Omit<LinkProps, AppearanceKeys | "to" | "onClick" | "children">
  & { to: LinkProps["to"]; onClick?: never };

export type TextLinkProps = ButtonTextLinkProps | RouterTextLinkProps;

function isRouterTextLink(props: TextLinkProps): props is RouterTextLinkProps {
  return "to" in props && props.to !== undefined;
}

export const TextLink = forwardRef<HTMLButtonElement | HTMLAnchorElement, TextLinkProps>(function TextLink(props, ref) {
  if (isRouterTextLink(props)) {
    const { children, to, ...rest } = props;
    return <Link ref={ref as React.Ref<HTMLAnchorElement>} className={ROOT_CLASS} to={to} {...rest}>{children}</Link>;
  }
  const { children, to, ...rest } = props;
  void to;
  return <button ref={ref as React.Ref<HTMLButtonElement>} type="button" className={ROOT_CLASS} {...rest}>{children}</button>;
});
