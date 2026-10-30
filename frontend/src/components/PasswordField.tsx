/**
 * PasswordFieldControl — 目のマーク付きのパスワード欄（login-round-inputs/design.md §6.2）
 *
 * TextFieldControl を包み、右端の目のマークで type を password と text で切り替える。
 * 状態は aria-label の切り替えだけで伝える（aria-pressed は付けない）。
 * type は部品が持つので受け取らない。丸いボタン（shape）はログイン画面だけなので付けない。
 */
import { forwardRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "./Button";
import { TextFieldControl } from "./TextField";
import type { TextFieldControlProps } from "./TextField";
import { PASSWORD_FIELD_ICONS } from "../constants/icons";
import { ICON } from "../constants/iconSizes";
import "./PasswordField.css";

type DistributiveOmit<T, K extends PropertyKey> = T extends unknown ? Omit<T, K> : never;

export type PasswordFieldControlProps = DistributiveOmit<TextFieldControlProps, "type">;

export const PasswordFieldControl = forwardRef<HTMLInputElement, PasswordFieldControlProps>(
  function PasswordFieldControl({ className, ...rest }, ref) {
    const { t } = useTranslation();
    const [visible, setVisible] = useState(false);
    const ToggleIcon = visible ? PASSWORD_FIELD_ICONS.hide : PASSWORD_FIELD_ICONS.show;
    const inputClass = ["comp-password-field__input", className ?? ""].filter(Boolean).join(" ");

    return (
      <div className="comp-password-field">
        <TextFieldControl
          {...(rest as TextFieldControlProps)}
          ref={ref}
          type={visible ? "text" : "password"}
          className={inputClass}
        />
        <Button
          variant="ghost"
          size="sm"
          iconOnly
          type="button"
          layoutClassName="comp-password-field__toggle"
          aria-label={visible ? t("common.hidePassword") : t("common.showPassword")}
          onClick={() => setVisible((v) => !v)}
        >
          <ToggleIcon size={ICON.base} aria-hidden="true" />
        </Button>
      </div>
    );
  },
);
PasswordFieldControl.displayName = "PasswordFieldControl";
