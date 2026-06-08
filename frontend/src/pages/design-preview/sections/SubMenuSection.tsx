/**
 * §11 サブメニュー (SubMenu)
 * grouped / flat・件数バッジ・disabled の目視確認。
 */
import { useState } from "react";
import { SubMenu } from "../../../components/SubMenu";
import type { SubMenuGroup } from "../../../components/SubMenu";
import { SectionHeader } from "./_shared";

const CRM_GROUPS: SubMenuGroup<string>[] = [
  {
    title: "顧客管理",
    items: [
      { key: "leads",     label: "リード",     badge: 42 },
      { key: "companies", label: "会社",       badge: 15 },
      { key: "contacts",  label: "担当者",     badge: 8  },
    ],
  },
  {
    title: "分析",
    items: [
      { key: "analytics", label: "アナリティクス" },
      { key: "reports",   label: "レポート", disabled: true },
    ],
  },
];

const FLAT_ITEMS: SubMenuGroup<string>[] = [
  {
    items: [
      { key: "dashboard", label: "ダッシュボード", badge: 3  },
      { key: "inbox",     label: "受信箱",         badge: 12 },
      { key: "orders",    label: "受注管理"        },
      { key: "schedule",  label: "スケジュール"    },
      { key: "settings",  label: "設定", disabled: true },
    ],
  },
];

export function SubMenuSection() {
  const [groupedActive, setGroupedActive] = useState("leads");
  const [flatActive,    setFlatActive]    = useState("dashboard");

  return (
    <section className="dp-section">
      <SectionHeader
        title="11. サブメニュー (SubMenu)"
        desc="grouped（グループ見出し付き縦型）/ flat（フラット縦型）・件数バッジ・disabled の目視確認。"
      />

      {/* grouped: グループ見出し + 件数バッジ + disabled */}
      <div className="dp-row dp-row--top">
        <span className="dp-row-label">grouped</span>
        <div className="dp-subnav-demo">
          <SubMenu
            variant="grouped"
            groups={CRM_GROUPS}
            activeKey={groupedActive}
            onChange={setGroupedActive}
          />
        </div>
      </div>

      {/* flat: グループ見出しなし + 件数バッジ + disabled */}
      <div className="dp-row dp-row--top">
        <span className="dp-row-label">flat</span>
        <div className="dp-subnav-demo">
          <SubMenu
            variant="flat"
            groups={FLAT_ITEMS}
            activeKey={flatActive}
            onChange={setFlatActive}
          />
        </div>
      </div>
    </section>
  );
}
