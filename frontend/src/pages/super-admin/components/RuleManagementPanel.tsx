/**
 * RuleManagementPanel — ルール管理パネル
 *
 * tcg_status_master のルール運用ビュー。
 * StatusMasterPanel（マスタ管理）とは別で、ルールのメンテナンスに特化。
 *
 * ADR-027: 全UI文字列は t("key") 経由。
 * ADR-144: 金型クラスのみ使用。
 */
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../../lib/api";
import { ContentToolbar } from "../../../components/ContentToolbar";
import { HeaderButton } from "../../../components/HeaderButton";
import { DataTable, type DataTableColumn } from "../../../components/DataTable";
import { Badge } from "../../../components/Badge";
import { TextField } from "../../../components/TextField";
import { EmptyState } from "../../../components/EmptyState";
import { Tabs, type TabItem } from "../../../components/Tabs";
import { RuleTestPanel } from "./RuleTestPanel";
import { RuleCreateDrawer } from "./RuleCreateDrawer";
import ConfirmModal from "../../../components/ConfirmModal";

interface RuleEntry {
  id: number;
  status_id: string;
  canonical: string;
  search_pattern: string;
  exclude_pattern: string;
  priority: number;
  enabled: boolean;
  note: string;
  match_type: string;
  effect: string;
  created_at: string;
  updated_at: string;
}

const PER_PAGE = 50;

type RuleTab = "sold-out" | "date" | "default" | "test";

export function RuleManagementPanel() {
  const { t } = useTranslation();
  const f = "ruleManagement";

  const [items, setItems] = useState<RuleEntry[]>([]);
  const [error, setError] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [toggling, setToggling] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<RuleTab>("sold-out");
  const [toggleTarget, setToggleTarget] = useState<RuleEntry | null>(null);
  const [createDrawerOpen, setCreateDrawerOpen] = useState(false);

  const load = useCallback(async () => {
    try {
      const params = new URLSearchParams({ page: String(page), per_page: String(PER_PAGE) });
      if (search.trim()) params.set("q", search.trim());
      const data = await api.get<RuleEntry[]>(`/super-admin/status-master?${params.toString()}`);
      setItems(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    }
  }, [page, search, t]);

  useEffect(() => { void load(); }, [load]);

  const runSearch = () => { setSearch(searchInput); setPage(1); };

  const filteredItems = items.filter((item) => {
    switch (activeTab) {
      case "sold-out": return item.effect === "EXCLUDE";
      case "date": return item.effect === "OUTPUT" && item.match_type !== "DEFAULT";
      case "default": return item.match_type === "DEFAULT";
      case "test": return false;
    }
  });

  const tabItems: TabItem<RuleTab>[] = [
    { key: "sold-out", label: t(`${f}.tabs.soldOut`), count: items.filter((i) => i.effect === "EXCLUDE").length },
    { key: "date", label: t(`${f}.tabs.date`), count: items.filter((i) => i.effect === "OUTPUT" && i.match_type !== "DEFAULT").length },
    { key: "default", label: t(`${f}.tabs.default`), count: items.filter((i) => i.match_type === "DEFAULT").length },
    { key: "test", label: t(`${f}.tabs.test`) },
  ];

  const handleRowClick = (row: RuleEntry) => {
    setToggleTarget(row);
  };

  const handleToggleConfirm = async () => {
    if (!toggleTarget) return;
    setToggling(toggleTarget.id);
    setError("");
    try {
      await api.patch(`/super-admin/status-master/${toggleTarget.id}`, { enabled: !toggleTarget.enabled });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t(`${f}.toggleFail`));
    } finally {
      setToggling(null);
      setToggleTarget(null);
    }
  };

  const columns: DataTableColumn<RuleEntry>[] = [
    { key: "canonical", header: t(`${f}.columns.canonical`) },
    { key: "search_pattern", header: t(`${f}.columns.searchPattern`) },
    { key: "exclude_pattern", header: t(`${f}.columns.excludePattern`) },
    {
      key: "match_type",
      header: t(`${f}.columns.matchType`),
      renderCell: (row) => {
        const variantMap: Record<string, "info" | "neutral"> = {
          REGEX: "info",
          LITERAL: "neutral",
          DEFAULT: "neutral",
        };
        const variant = variantMap[row.match_type] ?? "neutral";
        const label = t(`${f}.matchType.${row.match_type}`, { defaultValue: row.match_type });
        return <Badge variant={variant}>{label}</Badge>;
      },
    },
    {
      key: "effect",
      header: t(`${f}.columns.effect`),
      renderCell: (row) => {
        const variant = row.effect === "EXCLUDE" ? "danger" : "success";
        const label = t(`${f}.effect.${row.effect}`, { defaultValue: row.effect });
        return <Badge variant={variant}>{label}</Badge>;
      },
    },
    { key: "priority", header: t(`${f}.columns.priority`) },
    {
      key: "enabled",
      header: t(`${f}.columns.enabled`),
      renderCell: (row) => {
        const variant = row.enabled ? "success" : "neutral";
        const label = t(`${f}.enabled.${String(row.enabled)}`);
        return <Badge variant={variant}>{label}</Badge>;
      },
    },
  ];

  return (
    <>
      <Tabs
        items={tabItems}
        activeKey={activeTab}
        onChange={(key) => { setActiveTab(key); setPage(1); }}
        variant="underline"
      />
      {activeTab === "test" ? (
        <RuleTestPanel />
      ) : (
        <>
          <ContentToolbar
            left={
              <TextField
                type="search"
                label={t(`${f}.search`)}
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") runSearch(); }}
                data-testid="rule-management-search"
              />
            }
            right={
              <>
                <HeaderButton
                  variant="primary"
                  data-testid="rule-management-search-btn"
                  onClick={runSearch}
                >
                  {t("common.search")}
                </HeaderButton>
                <HeaderButton
                  data-testid="rule-management-create-btn"
                  onClick={() => setCreateDrawerOpen(true)}
                >
                  {t(`${f}.createRule`)}
                </HeaderButton>
              </>
            }
          />
          {error && <p role="alert" style={{ color: "var(--color-error)", padding: "var(--space-2) 0" }}>{error}</p>}
          {filteredItems.length > 0 && (
            <p style={{ fontSize: "var(--font-sm)", color: "var(--text-muted)", marginBottom: "var(--space-2)" }}>
              {t(`${f}.total`, { count: filteredItems.length })}
            </p>
          )}
          <DataTable
            columns={columns}
            data={filteredItems}
            rowKey={(row) => String(row.id)}
            onRowClick={(row) => { if (toggling === null) handleRowClick(row); }}
            emptyState={<EmptyState title={t(`${f}.noData`)} size="compact" />}
            page={page}
            hasNextPage={filteredItems.length >= PER_PAGE}
            onPageChange={setPage}
            prevPageLabel={t("common.prevPage")}
            nextPageLabel={t("common.nextPage")}
          />
        </>
      )}
      <ConfirmModal
        open={toggleTarget !== null}
        title={toggleTarget?.enabled ? t(`${f}.toggleDisable`) : t(`${f}.toggleEnable`)}
        message={toggleTarget ? t(`${f}.toggleConfirm`, { name: toggleTarget.canonical, action: toggleTarget.enabled ? t(`${f}.toggleDisable`) : t(`${f}.toggleEnable`) }) : ""}
        danger={toggleTarget?.enabled === true}
        onConfirm={() => { void handleToggleConfirm(); }}
        onCancel={() => setToggleTarget(null)}
      />
      <RuleCreateDrawer
        open={createDrawerOpen}
        onClose={() => setCreateDrawerOpen(false)}
        onCreated={() => { setCreateDrawerOpen(false); void load(); }}
      />
    </>
  );
}
