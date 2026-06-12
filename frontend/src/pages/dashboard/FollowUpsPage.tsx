/**
 * FollowUpsPage — 要フォロー顧客 下層ページ（PR5）
 * /dashboard/follow-ups
 * モックデータ駆動。区分チップ3つ + DataTable + useRecordDrawer
 */

import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { PageLayout } from "../../components/PageLayout";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { Drawer } from "../../components/Drawer";
import { useRecordDrawer } from "../../hooks/useRecordDrawer";
import { getFollowUps, type FollowUpItem } from "../../api/funnel";
import "./FollowUpsPage.css";

type SegmentFilter = "all" | "order_stopped" | "no_repeat_after_first" | "won_no_order";

// フォーム状態（ドロワー表示用）
interface FollowUpViewForm {
  customer_id: number;
  name: string;
  segment: string;
  days: number;
  last_order_at: string | null;
  last_contact_at: string | null;
  assignee: string;
}

const emptyForm: FollowUpViewForm = {
  customer_id: 0,
  name: "",
  segment: "",
  days: 0,
  last_order_at: null,
  last_contact_at: null,
  assignee: "",
};

function toForm(r: FollowUpItem): FollowUpViewForm {
  return {
    customer_id: r.customer_id,
    name: r.name,
    segment: r.segment,
    days: r.days,
    last_order_at: r.last_order_at,
    last_contact_at: r.last_contact_at,
    assignee: r.assignee,
  };
}

// FollowUpItem は customer_id をキーとして持つが DataTable は id を期待するため型アダプター
interface FollowUpRow extends FollowUpItem {
  id: number;
}

export default function FollowUpsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [items, setItems] = useState<FollowUpRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<SegmentFilter>("all");
  const [page, setPage] = useState(1);

  const PAGE_SIZE = 20;

  const { drawerOpen, editForm, handleRowClick, closeDrawer } =
    useRecordDrawer<FollowUpRow, FollowUpViewForm>({ toForm, emptyForm });

  useEffect(() => {
    setLoading(true);
    getFollowUps()
      .then((res) => {
        setItems(res.items.map((i) => ({ ...i, id: i.customer_id })));
      })
      .finally(() => setLoading(false));
  }, []);

  const filtered = items.filter(
    (i) => filter === "all" || i.segment === filter,
  );
  const pageItems = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const hasNextPage = filtered.length > page * PAGE_SIZE;

  const counts = {
    all: items.length,
    order_stopped: items.filter((i) => i.segment === "order_stopped").length,
    no_repeat_after_first: items.filter((i) => i.segment === "no_repeat_after_first").length,
    won_no_order: items.filter((i) => i.segment === "won_no_order").length,
  };

  const columns: DataTableColumn<FollowUpRow>[] = [
    {
      key: "name",
      header: t("funnel.colCustomer"),
      renderCell: (row) => <span className="fu-customer-name">{row.name}</span>,
    },
    {
      key: "segment",
      header: t("funnel.colSegment"),
      renderCell: (row) => (
        <span className={`fu-segment-chip fu-segment--${row.segment}`}>
          {t(`funnel.seg_${row.segment}`)}
        </span>
      ),
    },
    {
      key: "days",
      header: t("funnel.colDays"),
      renderCell: (row) => `${row.days}${t("common.unitDay", { defaultValue: "日" })}`,
    },
    {
      key: "last_order_at",
      header: t("funnel.colLastOrder"),
      renderCell: (row) => row.last_order_at ?? "-",
    },
    {
      key: "last_contact_at",
      header: t("funnel.colLastContact"),
      renderCell: (row) => row.last_contact_at ?? "-",
    },
    {
      key: "assignee",
      header: t("funnel.colAssignee"),
      renderCell: (row) => row.assignee,
    },
  ];

  const segmentFilters: { key: SegmentFilter; label: string }[] = [
    { key: "all", label: t("common.all") },
    { key: "order_stopped", label: t("funnel.segOrderStopped") },
    { key: "no_repeat_after_first", label: t("funnel.segNoRepeat") },
    { key: "won_no_order", label: t("funnel.segWonNoOrder") },
  ];

  return (
    <PageLayout
      navKey="nav.dashboard"
      subtitleKey="funnel.followUpTitle"
      headerAction={
        <button
          type="button"
          className="fu-back-btn"
          onClick={() => navigate("/")}
        >
          ← {t("nav.dashboard")}
        </button>
      }
    >
      {/* セグメントフィルタチップ */}
      <div className="fu-filter-row">
        {segmentFilters.map((f) => (
          <button
            key={f.key}
            type="button"
            className={`fu-filter-chip${filter === f.key ? " active" : ""} fu-chip--${f.key}`}
            onClick={() => { setFilter(f.key); setPage(1); }}
          >
            {f.label}
            <span className="fu-chip-count">{counts[f.key]}</span>
          </button>
        ))}
      </div>

      {/* DataTable */}
      {loading ? (
        <div className="fu-loading">{t("common.loading")}</div>
      ) : (
        <DataTable<FollowUpRow>
          columns={columns}
          data={pageItems}
          rowKey={(row) => String(row.id)}
          onRowClick={handleRowClick}
          page={page}
          hasNextPage={hasNextPage}
          onPageChange={setPage}
          prevPageLabel={t("common.prevPage")}
          nextPageLabel={t("common.nextPage")}
          emptyState={<p className="fu-empty">{t("funnel.noFollowUps")}</p>}
        />
      )}

      {/* 詳細ドロワー */}
      <Drawer
        open={drawerOpen}
        onClose={closeDrawer}
        title={editForm.name || t("funnel.followUpTitle")}
        onOpenFullPage={
          editForm.customer_id
            ? () => { navigate(`/crm/companies/${editForm.customer_id}`); closeDrawer(); }
            : undefined
        }
      >
        {drawerOpen && (
          <div className="fu-drawer-body">
            <div className="fu-drawer-row">
              <span className="fu-drawer-label">{t("funnel.colSegment")}</span>
              <span className={`fu-segment-chip fu-segment--${editForm.segment}`}>
                {t(`funnel.seg_${editForm.segment}`)}
              </span>
            </div>
            <div className="fu-drawer-row">
              <span className="fu-drawer-label">{t("funnel.colDays")}</span>
              <span>{editForm.days}{t("common.unitDay", { defaultValue: "日" })}</span>
            </div>
            <div className="fu-drawer-row">
              <span className="fu-drawer-label">{t("funnel.colLastOrder")}</span>
              <span>{editForm.last_order_at ?? "-"}</span>
            </div>
            <div className="fu-drawer-row">
              <span className="fu-drawer-label">{t("funnel.colLastContact")}</span>
              <span>{editForm.last_contact_at ?? "-"}</span>
            </div>
            <div className="fu-drawer-row">
              <span className="fu-drawer-label">{t("funnel.colAssignee")}</span>
              <span>{editForm.assignee}</span>
            </div>
          </div>
        )}
      </Drawer>
    </PageLayout>
  );
}
