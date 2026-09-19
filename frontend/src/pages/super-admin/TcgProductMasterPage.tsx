import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import { PageLayout } from "../../components/PageLayout";
import { ContentToolbar } from "../../components/ContentToolbar";
import { HeaderButton } from "../../components/HeaderButton";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { EmptyState } from "../../components/EmptyState";
import { TextField } from "../../components/TextField";
import { Tabs } from "../../components/Tabs";

import { TcgProductDetailDrawer } from "../../features/tcg-product-import/TcgProductDetailDrawer";
import "../../features/tcg-product-import/product-csv.css";

interface ProductRow {
  code: string; japanese_title: string; english_title: string; mark: string;
  release_date: string; keyword_count: number; exclude_keyword_count: number;
}
interface ProductWork { id: string; code: string; display_name: string; alt_name: string }
interface ProductList { total: number; items: ProductRow[]; works: ProductWork[] }
const PAGE_SIZE = 50;

export default function TcgProductMasterPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { isSuperAdmin, loading: authLoading } = useSuperAdmin();
  const [filter, setFilter] = useState({ query: "", page: 1, workId: "" });
  const [works, setWorks] = useState<ProductWork[]>([]);
  const [selectedWork, setSelectedWork] = useState<ProductWork | null>(null);
  const [data, setData] = useState<ProductList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);
  const [selectedProduct, setSelectedProduct] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState(false);
  const exportLock = useRef(false);
  async function downloadExport() {
    if (authLoading || !isSuperAdmin || exportLock.current) return;
    exportLock.current = true; setExporting(true); setExportError(false);
    let url: string | undefined;
    const anchor = document.createElement("a");
    try {
      const blob = await api.getBlob("/tcg/products/export");
      url = URL.createObjectURL(blob); anchor.href = url;
      anchor.download = "tcg-products-update.csv";
      document.body.appendChild(anchor); anchor.click();
    } catch { setExportError(true); }
    finally { anchor.remove(); if (url) URL.revokeObjectURL(url); exportLock.current = false; setExporting(false); }
  }
  useEffect(() => {
    if (authLoading || !isSuperAdmin) return;
    let cancelled = false;
    setLoading(true); setError(false); setData(null);
    const params = new URLSearchParams({ query: filter.query, limit: String(PAGE_SIZE), offset: String((filter.page - 1) * PAGE_SIZE) });
    if (filter.workId) params.set("work_id", filter.workId);
    void api.get<ProductList>(`/tcg/products/list?${params}`).then(result => {
      if (cancelled) return;
      if (!Array.isArray(result.works) || !result.works.every(work => work && typeof work.id === "string" && typeof work.code === "string" && typeof work.display_name === "string" && typeof work.alt_name === "string")) throw new Error("Invalid product works");
      setWorks(result.works);
      setSelectedWork(value => result.works.find(work => work.id === filter.workId) ?? value);
      setData(result);
    }).catch(() => { if (!cancelled) setError(true); }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [authLoading, isSuperAdmin, filter, retry]);
  const visibleWorks = selectedWork && selectedWork.id === filter.workId && !works.some(work => work.id === filter.workId) ? [...works, selectedWork] : works;
  const workLabel = (work: ProductWork) => i18n.language.startsWith("ja") ? work.alt_name.trim() || work.display_name : work.display_name;
  const columns: DataTableColumn<ProductRow>[] = [
    { key: "mark", header: t("productCsv.mark") },
    { key: "japanese_title", header: t("productCsv.title"), renderCell: row => <div className="product-detail__name">
      <span>{row.japanese_title}</span>
      {row.english_title && <span className="product-detail__english">{row.english_title}</span>}
    </div> },
    { key: "release_date", header: t("productCsv.releaseDate") },
    { key: "keyword_count", header: t("productDetail.searchCount") },
    { key: "exclude_keyword_count", header: t("productDetail.excludeCount") },
  ];
  return <PageLayout navKey="nav.superAdminTcgProductMaster" headerAction={isSuperAdmin ? <><HeaderButton variant="secondary" disabled={exporting} onClick={() => void downloadExport()}>{t(exporting ? "common.loading" : "productCsv.export")}</HeaderButton><HeaderButton variant="primary" onClick={() => setCreating(true)}>{t("productCsv.addProduct")}</HeaderButton><HeaderButton variant="primary" onClick={() => navigate("/super-admin/tcg-product-master/import")}>{t("productCsv.openImport")}</HeaderButton></> : undefined}>
    {authLoading ? <p>{t("common.loading")}</p> : !isSuperAdmin ? <p role="alert">{t("productCsv.denied")}</p> : <>
      <p>{t("productCsv.exportHint")}</p>
      {exportError && <p role="alert">{t("productCsv.exportError")}</p>}
      <Tabs items={[{ key: "", label: t("productCsv.allWorks") }, ...visibleWorks.map(work => ({ key: work.id, label: workLabel(work) }))]} activeKey={filter.workId} onChange={workId => { setSelectedWork(visibleWorks.find(work => work.id === workId) ?? null); setFilter(value => ({ ...value, workId, page: 1 })); }} variant="underline" size="md" />
      <ContentToolbar left={<TextField type="search" label={t("productCsv.search")} value={filter.query} onChange={e => setFilter(value => ({ ...value, query: e.target.value, page: 1 }))} />} />
      {loading ? <p>{t("common.loading")}</p> : error ? <div role="alert"><p>{t("productCsv.loadError")}</p><HeaderButton variant="secondary" onClick={() => setRetry(value => value + 1)}>{t("productCsv.retry")}</HeaderButton></div> : data && <>
        <p role="status">{t("productCsv.total", { count: data.total })}</p>
        <DataTable columns={columns} data={data.items} rowKey={row => row.code} onRowClick={row => setSelectedProduct(row.code)} emptyState={<EmptyState title={t("productCsv.empty")} size="compact" />} page={filter.page} hasNextPage={filter.page * PAGE_SIZE < data.total} onPageChange={page => setFilter(value => ({ ...value, page }))} prevPageLabel={t("productCsv.previous")} nextPageLabel={t("productCsv.next")} />
      </>}
      <TcgProductDetailDrawer productCode={selectedProduct} onClose={() => setSelectedProduct(null)} onSaved={() => setRetry(value => value + 1)} />
      <TcgProductDetailDrawer productCode={null} open={creating} mode="create" onClose={() => setCreating(false)} onSaved={() => { setCreating(false); setRetry(v => v + 1); }} />
    </>}
  </PageLayout>;
}
