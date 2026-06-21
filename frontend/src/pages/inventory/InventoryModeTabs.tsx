import { useTranslation } from "react-i18next";
import { useLocation, useNavigate } from "react-router-dom";
import { Tabs } from "../../components/Tabs";

type InventoryMode = "wego" | "own";

const MODE_TO_PATH: Record<InventoryMode, string> = {
  wego: "/inventory",
  own: "/own-inventory",
};

export default function InventoryModeTabs() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { pathname } = useLocation();

  const activeKey: InventoryMode = pathname === MODE_TO_PATH.own ? "own" : "wego";
  const items: { key: InventoryMode; label: string }[] = [
    { key: "wego", label: t("nav.wegoInventory") },
    { key: "own", label: t("nav.ownInventory") },
  ];

  return (
    <Tabs
      items={items}
      activeKey={activeKey}
      onChange={(key) => navigate(MODE_TO_PATH[key])}
      variant="pill"
      size="md"
      className="inventory-mode-tabs"
    />
  );
}
