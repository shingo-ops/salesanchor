/**
 * §10 タブ (Tabs)
 * underline / pill・件数バッジ・6タブ・3タブ・disabled の目視確認。
 */
import { useState } from "react";
import { Tabs } from "../../../components/Tabs";
import type { TabItem } from "../../../components/Tabs";
import { SectionHeader } from "./_shared";

const THREE_TABS: TabItem<string>[] = [
  { key: "deal",    label: "商談"   },
  { key: "company", label: "会社"   },
  { key: "contact", label: "担当者" },
];

const SIX_TABS: TabItem<string>[] = [
  { key: "all",      label: "すべて",     count: 128 },
  { key: "lead",     label: "リード",     count: 42  },
  { key: "deal",     label: "商談",       count: 21  },
  { key: "existing", label: "既存顧客",   count: 35  },
  { key: "followup", label: "フォロー",   count: 18  },
  { key: "archive",  label: "アーカイブ", count: 12  },
];

const DISABLED_TABS: TabItem<string>[] = [
  { key: "deal",    label: "商談"             },
  { key: "company", label: "会社"             },
  { key: "contact", label: "担当者（未対応）", disabled: true },
];

export function TabsSection() {
  const [underlineMd3,  setUnderlineMd3]  = useState("deal");
  const [underlineSm3,  setUnderlineSm3]  = useState("deal");
  const [pillMd6,       setPillMd6]       = useState("all");
  const [underlineMd6,  setUnderlineMd6]  = useState("all");
  const [disabledTab,   setDisabledTab]   = useState("deal");

  return (
    <section className="dp-section">
      <SectionHeader
        title="10. タブ (Tabs)"
        desc="underline / pill・件数バッジ・6タブ・3タブ・disabled・横スクロールの目視確認。"
      />

      {/* underline md — 3タブ（KartePanel / right-panel-tab 系） */}
      <div className="dp-row">
        <span className="dp-row-label">underline / md / 3タブ</span>
        <div className="dp-row-items">
          <Tabs
            items={THREE_TABS}
            activeKey={underlineMd3}
            onChange={setUnderlineMd3}
            variant="underline"
            size="md"
          />
        </div>
      </div>

      {/* underline sm — 3タブ */}
      <div className="dp-row">
        <span className="dp-row-label">underline / sm / 3タブ</span>
        <div className="dp-row-items">
          <Tabs
            items={THREE_TABS}
            activeKey={underlineSm3}
            onChange={setUnderlineSm3}
            variant="underline"
            size="sm"
          />
        </div>
      </div>

      {/* pill md — 6タブ + 件数バッジ（inbox-full-tab-bar 系） */}
      <div className="dp-row">
        <span className="dp-row-label">pill / md / 6タブ + count</span>
        <div className="dp-row-items">
          <Tabs
            items={SIX_TABS}
            activeKey={pillMd6}
            onChange={setPillMd6}
            variant="pill"
            size="md"
          />
        </div>
      </div>

      {/* underline md — 6タブ + 件数バッジ */}
      <div className="dp-row">
        <span className="dp-row-label">underline / md / 6タブ + count</span>
        <div className="dp-row-items">
          <Tabs
            items={SIX_TABS}
            activeKey={underlineMd6}
            onChange={setUnderlineMd6}
            variant="underline"
            size="md"
          />
        </div>
      </div>

      {/* disabled */}
      <div className="dp-row">
        <span className="dp-row-label">disabled タブ</span>
        <div className="dp-row-items">
          <Tabs
            items={DISABLED_TABS}
            activeKey={disabledTab}
            onChange={setDisabledTab}
            variant="underline"
            size="md"
          />
        </div>
      </div>

      {/* 横スクロール（375px幅） */}
      <div className="dp-row">
        <span className="dp-row-label">横スクロール (375px)</span>
        <div className="dp-row-items">
          <div style={{ maxWidth: 375, overflow: "hidden", width: "100%" }}>
            <Tabs
              items={SIX_TABS}
              activeKey={pillMd6}
              onChange={setPillMd6}
              variant="pill"
              size="md"
            />
          </div>
        </div>
      </div>
    </section>
  );
}
