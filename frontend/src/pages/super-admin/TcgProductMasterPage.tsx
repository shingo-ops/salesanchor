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

import "../../features/tcg-product-import/product-csv.css";

interface ProductRow {
  code: string; japanese_title: string; mark: string;
  release_date: string; keyword_count: number;
}
interface ProductList { total: number; items: ProductRow[] }
const PAGE_SIZE = 50;

export default function TcgProductMasterPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { isSuperAdmin, loading: authLoading } = useSuperAdmin();
  const [filter, setFilter] = useState({ query: "", page: 1 });
  const [data, setData] = useState<ProductList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    if (authLoading || !isSuperAdmin) return;
    let cancelled = false;
    setLoading(true); setError(false); setData(null);
    const params = new URLSearchParams({ query: filter.query, limit: String(PAGE_SIZE), offset: String((filter.page - 1) * PAGE_SIZE) });
    void api.get<ProductList>(`/tcg/products/list?${params}`).then(result => {
      if (!cancelled) setData(result);
    }).catch(() => { if (!cancelled) setError(true); }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [authLoading, isSuperAdmin, filter, retry]);
  const columns: DataTableColumn<ProductRow>[] = [
    { key: "code", header: t("productCsv.code") },
    { key: "japanese_title", header: t("productCsv.title") },
    { key: "mark", header: t("productCsv.mark") },
    { key: "release_date", header: t("productCsv.releaseDate") },
    { key: "keyword_count", header: t("productCsv.keywords"), renderCell: row => row.keyword_count === 0 ? <span className="product-csv__warning">{t("productCsv.noKeywords")}</span> : row.keyword_count },
  ];
  return <PageLayout navKey="nav.superAdminTcgProductMaster" headerAction={isSuperAdmin ? <HeaderButton variant="primary" onClick={() => navigate("/super-admin/tcg-product-master/import")}>{t("productCsv.openImport")}</HeaderButton> : undefined}>
    {authLoading ? <p>{t("common.loading")}</p> : !isSuperAdmin ? <p role="alert">{t("productCsv.denied")}</p> : <>
      <ContentToolbar left={<TextField type="search" label={t("productCsv.search")} value={filter.query} onChange={e => setFilter({ query: e.target.value, page: 1 })} />} />
      {loading ? <p>{t("common.loading")}</p> : error ? <div role="alert"><p>{t("productCsv.loadError")}</p><HeaderButton variant="secondary" onClick={() => setRetry(value => value + 1)}>{t("productCsv.retry")}</HeaderButton></div> : data && <>
        <p role="status">{t("productCsv.total", { count: data.total })}</p>
        <DataTable columns={columns} data={data.items} rowKey={row => row.code} emptyState={<EmptyState title={t("productCsv.empty")} size="compact" />} page={filter.page} hasNextPage={filter.page * PAGE_SIZE < data.total} onPageChange={page => setFilter(value => ({ ...value, page }))} prevPageLabel={t("productCsv.previous")} nextPageLabel={t("productCsv.next")} />
      </>}
    </>}
  </PageLayout>;
}
