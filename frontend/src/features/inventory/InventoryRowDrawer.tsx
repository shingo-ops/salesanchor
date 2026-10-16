/**
 * 在庫表の行から開く解析パネル（見るだけ）。super admin 専用。
 * 行の元になった extraction_items.id（まとめた行は組の全件）を /tcg/analysis-results へ ID 指定で渡し、
 * 要確認パネルと同じ ReviewItemDrawer（viewOnly）で 原文・Gemini 抽出・システム解析 を表示する。
 */
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Callout } from "../../components/Callout";
import { Drawer } from "../../components/Drawer";
import { Tabs } from "../../components/Tabs";
import { api, ApiError } from "../../lib/api";
import { ReviewItemDrawer, type ReviewDrawerItem } from "../tcg-analysis-review/ReviewItemDrawer";
import type { InventoryRow } from "./inventoryColumns";

interface Props {
  row: InventoryRow;
  onClose: () => void;
}

interface AnalysisResultsResponse {
  items: ReviewDrawerItem[];
}

type LoadState = "loading" | "ready" | "forbidden" | "error";

export function InventoryRowDrawer({ row, onClose }: Props) {
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

  if (state === "ready" && items.length > 0) {
    const current = items.find((it) => it.extraction_item_id === activeKey) ?? items[0];
    const tabs =
      items.length >= 2 ? (
        <Tabs
          items={items.map((it, i) => ({ key: it.extraction_item_id, label: t("inventory.rowDrawer.itemTab", { n: i + 1 }) }))}
          activeKey={current.extraction_item_id}
          onChange={setActiveKey}
          variant="pill"
        />
      ) : undefined;
    return <ReviewItemDrawer item={current} viewOnly onClose={onClose} onRefresh={load} headerSlot={tabs} />;
  }

  return (
    <Drawer open size="wide" title={t("inventory.rowDrawer.title")} onClose={onClose}>
      {state === "loading" && <p role="status">{t("common.loading")}</p>}
      {state === "forbidden" && <Callout variant="warning" title={t("superAdmin.supplierQuality.superAdminOnly")} />}
      {state === "error" && <Callout variant="warning" title={t("inventory.rowDrawer.loadError")} />}
      {state === "ready" && <Callout variant="info" title={t("inventory.rowDrawer.notFound")} />}
    </Drawer>
  );
}
