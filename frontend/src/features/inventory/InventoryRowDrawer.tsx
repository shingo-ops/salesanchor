/**
 * 在庫表の行から開くスライド。
 * super admin: 「解析｜原文」の2タブ（既定は解析）。非 super admin（products.view）: 原文だけ。
 * 解析タブ: 行の元になった extraction_items.id（まとめた行は組の全件）を /tcg/analysis-results へ ID 指定で渡し、
 * 要確認パネルと同じ ReviewItemDrawerで 原文・Gemini 抽出・システム解析 を表示する。
 */
import { useCallback, useEffect, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Callout } from "../../components/Callout";
import { Drawer } from "../../components/Drawer";
import { Stack } from "../../components/Stack";
import { Tabs } from "../../components/Tabs";
import { useRealtimeRefresh } from "../../hooks/useRealtimeRefresh";
import { api, ApiError } from "../../lib/api";
import { TOPICS } from "../../lib/realtime/topics";
import { ReviewItemDrawer, type ReviewDrawerItem } from "../tcg-analysis-review/ReviewItemDrawer";
import { ShadowSourcePane } from "../tcg-analysis-review/ShadowSourcePane";
import type { InventoryRow } from "./inventoryColumns";
import { fmtOfferedAt, supplierLabel } from "./inventoryFormat";
import "./inventory-row-drawer.css";
import { LoadingBlock } from "../../components/loading";

interface Props {
  row: InventoryRow;
  onClose: () => void;
  onChanged: () => void;
  isSuperAdmin: boolean;
}

interface AnalysisResultsResponse {
  items: ReviewDrawerItem[];
}

interface RawTextItem {
  extraction_item_id: string;
  raw_text: string;
  line_start: number | null;
  line_end: number | null;
}

interface RawTextsResponse {
  items: RawTextItem[];
}

type LoadState = "loading" | "ready" | "forbidden" | "notFound" | "error";
type DrawerTab = "analysis" | "rawText";

interface PaneProps {
  row: InventoryRow;
  onClose: () => void;
  onChanged: () => void;
  /** super admin のときだけ渡す「解析｜原文」タブ */
  modeTabs?: ReactNode;
}

const REVIEW_TOPICS = [TOPICS.tcgReview] as const;

function AnalysisPane({ row, onClose, onChanged, modeTabs }: PaneProps) {
  const { t } = useTranslation();
  const [items, setItems] = useState<ReviewDrawerItem[]>([]);
  const [state, setState] = useState<LoadState>("loading");
  const [activeKey, setActiveKey] = useState<string | null>(null);

  const load = useCallback(async (): Promise<void> => {
    const params = new URLSearchParams();
    for (const id of row.extraction_item_ids) params.append("extraction_item_ids", id);
    try {
      const result = await api.get<AnalysisResultsResponse>(`/tcg/analysis-results?${params.toString()}`);
      setItems(result.items);
      setState("ready");
    } catch (error: unknown) {
      setState(error instanceof ApiError && (error.status === 401 || error.status === 403) ? "forbidden" : "error");
    }
  }, [row.extraction_item_ids]);

  useEffect(() => {
    setState("loading");
    void load();
  }, [load]);

  const refresh = useCallback(async (): Promise<void> => {
    await load();
    onChanged();
  }, [load, onChanged]);

  useRealtimeRefresh(REVIEW_TOPICS, () => {
    void refresh();
  });

  if (state === "ready" && items.length > 0) {
    const current = items.find((it) => it.extraction_item_id === activeKey) ?? items[0];
    const itemTabs =
      items.length >= 2 ? (
        <Tabs
          items={items.map((it, i) => ({ key: it.extraction_item_id, label: t("inventory.rowDrawer.itemTab", { n: i + 1 }) }))}
          activeKey={current.extraction_item_id}
          onChange={setActiveKey}
          variant="pill"
        />
      ) : undefined;
    const tabs =
      modeTabs && itemTabs ? (
        <Stack gap="2">
          {modeTabs}
          {itemTabs}
        </Stack>
      ) : (
        (modeTabs ?? itemTabs)
      );
    return (
      <ReviewItemDrawer
        key={current.extraction_item_id}
        item={current}
        onClose={onClose}
        onRefresh={refresh}
        headerSlot={tabs}
      />
    );
  }

  return (
    <Drawer open size="wide" title={t("inventory.rowDrawer.title")} onClose={onClose}>
      {modeTabs}
      {state === "loading" && <LoadingBlock />}
      {state === "forbidden" && <Callout variant="warning" title={t("superAdmin.supplierQuality.superAdminOnly")} />}
      {state === "error" && <Callout variant="warning" title={t("inventory.rowDrawer.loadError")} />}
      {state === "ready" && <Callout variant="info" title={t("inventory.rowDrawer.notFound")} />}
    </Drawer>
  );
}

function RawTextPane({ row, onClose, modeTabs }: PaneProps) {
  const { t } = useTranslation();
  const [items, setItems] = useState<RawTextItem[]>([]);
  const [state, setState] = useState<LoadState>("loading");
  const [activeKey, setActiveKey] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setState("loading");
    const params = new URLSearchParams();
    for (const id of row.extraction_item_ids) params.append("extraction_item_ids", id);
    api
      .get<RawTextsResponse>(`/inventory/raw-texts?${params.toString()}`)
      .then((result) => {
        if (cancelled) return;
        const order = row.extraction_item_ids;
        setItems([...result.items].sort((a, b) => order.indexOf(a.extraction_item_id) - order.indexOf(b.extraction_item_id)));
        setState("ready");
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        if (error instanceof ApiError && error.status === 404) setState("notFound");
        else setState("error");
      });
    return () => {
      cancelled = true;
    };
  }, [row.extraction_item_ids]);

  const current = items.find((it) => it.extraction_item_id === activeKey) ?? items[0];
  const itemTabs =
    items.length >= 2 ? (
      <Tabs
        items={items.map((it, i) => ({ key: it.extraction_item_id, label: t("inventory.rowDrawer.itemTab", { n: i + 1 }) }))}
        activeKey={current.extraction_item_id}
        onChange={setActiveKey}
        variant="pill"
      />
    ) : undefined;

  return (
    <Drawer
      open
      size="wide"
      title={t("inventory.rowDrawer.rawTextTitle", { supplier: supplierLabel(row), postedAt: fmtOfferedAt(row.offered_at) })}
      onClose={onClose}
    >
      <Stack gap="4" className="inventory-rawtext-pane">
        {modeTabs}
        {itemTabs}
        {state === "loading" && <LoadingBlock />}
        {state === "notFound" && <Callout variant="info" title={t("inventory.rowDrawer.notFound")} />}
        {state === "error" && <Callout variant="warning" title={t("inventory.rowDrawer.loadError")} />}
        {state === "ready" && current && (
          <ShadowSourcePane
            key={current.extraction_item_id}
            rawText={current.raw_text}
            showLegend={false}
            blockRange={
              current.line_start != null && current.line_end != null
                ? { start: current.line_start, end: current.line_end }
                : undefined
            }
          />
        )}
      </Stack>
    </Drawer>
  );
}

export function InventoryRowDrawer({ row, onClose, onChanged, isSuperAdmin }: Props) {
  const { t } = useTranslation();
  const [tab, setTab] = useState<DrawerTab>("analysis");

  if (!isSuperAdmin) return <RawTextPane row={row} onClose={onClose} onChanged={onChanged} />;

  const modeTabs = (
    <Tabs
      items={[
        { key: "analysis", label: t("inventory.rowDrawer.tabAnalysis") },
        { key: "rawText", label: t("inventory.rowDrawer.tabRawText") },
      ]}
      activeKey={tab}
      onChange={setTab}
      variant="underline"
    />
  );
  return tab === "analysis" ? (
    <AnalysisPane row={row} onClose={onClose} onChanged={onChanged} modeTabs={modeTabs} />
  ) : (
    <RawTextPane row={row} onClose={onClose} onChanged={onChanged} modeTabs={modeTabs} />
  );
}
