/**
 * 利用者管理の小さなメニュー。閲覧者の画面とログインの許可待ちの画面が共有する。
 * 1つ目の組: 閲覧者（すべて＋状態ごと）。2つ目の組（題なし）: ログインの許可待ち。
 */
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { SubMenu, type SubMenuGroup } from "../../../components/SubMenu";

export const USER_MENU_STATUSES = ["pending", "trial", "active"] as const;
export type UserMenuStatus = "all" | (typeof USER_MENU_STATUSES)[number];

interface Props {
  /** 閲覧者の画面で今選んでいる状態。ログインの画面では未指定。 */
  activeKey?: UserMenuStatus;
  /** 状態ごとの数。未指定なら数を出さない。 */
  counts?: Partial<Record<UserMenuStatus, number>>;
  /** 閲覧者の画面での切り替え。未指定（ログインの画面）なら /super-admin/users/viewers へ移る。 */
  onChange?: (key: UserMenuStatus) => void;
  /** 状態ごとの文字（閲覧者の画面と同じ言葉を渡す）。 */
  statusLabel: (key: UserMenuStatus) => string;
}

export function UserManagementSubMenu({ activeKey, counts, onChange, statusLabel }: Props) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const keys: UserMenuStatus[] = ["all", ...USER_MENU_STATUSES];

  const groups: SubMenuGroup[] = [
    {
      title: t("superAdmin.users.groupViewers"),
      items: keys.map((key) => ({
        key,
        label: statusLabel(key),
        badge: counts?.[key],
      })),
    },
    {
      items: [
        {
          key: "login-requests",
          label: t("nav.superAdminLoginRequests"),
          to: "/super-admin/users/login-requests",
        },
      ],
    },
  ];

  const handleChange = (key: string) => {
    if (key === "login-requests") return;
    const status = key as UserMenuStatus;
    if (onChange) {
      onChange(status);
      return;
    }
    navigate(status === "all" ? "/super-admin/users/viewers" : `/super-admin/users/viewers?status=${status}`);
  };

  return (
    <SubMenu
      variant="grouped"
      className="hub-subnav"
      groups={groups}
      activeKey={activeKey ?? "login-requests"}
      onChange={handleChange}
    />
  );
}
