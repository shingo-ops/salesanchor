import { useEffect, useState } from "react";
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

import "../../features/tcg-product-import/product-csv.css";

interface ProductRow {
  code: string; japanese_title: string; mark: string;
  release_date: string; keyword_count: number;
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
    { key: "code", header: t("productCsv.code") },
    { key: "japanese_title", header: t("productCsv.title") },
    { key: "mark", header: t("productCsv.mark") },
    { key: "release_date", header: t("productCsv.releaseDate") },
    { key: "keyword_count", header: t("productCsv.keywords"), renderCell: row => row.keyword_count === 0 ? <span className="product-csv__warning">{t("productCsv.noKeywords")}</span> : row.keyword_count },
  ];
  return <PageLayout navKey="nav.superAdminTcgProductMaster" headerAction={isSuperAdmin ? <HeaderButton variant="primary" onClick={() => navigate("/super-admin/tcg-product-master/import")}>{t("productCsv.openImport")}</HeaderButton> : undefined}>
    {authLoading ? <p>{t("common.loading")}</p> : !isSuperAdmin ? <p role="alert">{t("productCsv.denied")}</p> : <>
      <Tabs items={[{ key: "", label: t("productCsv.allWorks") }, ...visibleWorks.map(work => ({ key: work.id, label: workLabel(work) }))]} activeKey={filter.workId} onChange={workId => { setSelectedWork(visibleWorks.find(work => work.id === workId) ?? null); setFilter(value => ({ ...value, workId, page: 1 })); }} variant="underline" size="md" />
      <ContentToolbar left={<TextField type="search" label={t("productCsv.search")} value={filter.query} onChange={e => setFilter(value => ({ ...value, query: e.target.value, page: 1 }))} />} />
      {loading ? <p>{t("common.loading")}</p> : error ? <div role="alert"><p>{t("productCsv.loadError")}</p><HeaderButton variant="secondary" onClick={() => setRetry(value => value + 1)}>{t("productCsv.retry")}</HeaderButton></div> : data && <>
        <p role="status">{t("productCsv.total", { count: data.total })}</p>
        <DataTable columns={columns} data={data.items} rowKey={row => row.code} emptyState={<EmptyState title={t("productCsv.empty")} size="compact" />} page={filter.page} hasNextPage={filter.page * PAGE_SIZE < data.total} onPageChange={page => setFilter(value => ({ ...value, page }))} prevPageLabel={t("productCsv.previous")} nextPageLabel={t("productCsv.next")} />
      </>}
    </>}
  </PageLayout>;
}
