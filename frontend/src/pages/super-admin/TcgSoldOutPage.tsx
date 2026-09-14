import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { PageLayout } from "../../components/PageLayout";
import { Button } from "../../components/Button";
import { Select } from "../../components/Select";
import { ContentToolbar } from "../../components/ContentToolbar";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import { ApiError } from "../../lib/api";
import { fetchSoldOut, type SoldOutItem, type SoldOutResponse, type SourceScope } from "../../features/tcg-sold-out/soldOutApi";

function SourceDetail({ item }: { item: SoldOutItem }) {
  const { t } = useTranslation();
  const lines = item.raw_text.split("\n");
  const start = item.line_start;
  const end = item.line_end;
  const valid = start !== null && end !== null && Number.isInteger(start) && Number.isInteger(end)
    && start >= 1 && start <= end && end <= lines.length;
  return <details>
    <summary>{t("soldOut.source")}</summary>
    <dl>
      <dt>{t("soldOut.rawName")}</dt><dd>{item.raw_product_name}</dd>
      <dt>{t("soldOut.rawState")}</dt><dd>{item.raw_state}</dd>
      <dt>{t("soldOut.rawMemo")}</dt><dd>{item.raw_memo}</dd>
    </dl>
    {!valid && <p>{t("soldOut.invalidSpan")}</p>}
    <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
      {valid ? lines.map((line, index) => <span key={index}>
        {index + 1 >= start && index + 1 <= end ? <mark>{line}</mark> : line}
        {index < lines.length - 1 ? "\n" : ""}
      </span>) : item.raw_text}
    </pre>
  </details>;
}

export default function TcgSoldOutPage() {
  const { t, i18n } = useTranslation();
  const { isSuperAdmin, loading: authLoading } = useSuperAdmin();
  const [q, setQ] = useState("");
  const [draft, setDraft] = useState("");
  const [scope, setScope] = useState<SourceScope>("all");
  const [offset, setOffset] = useState(0);
  const [reload, setReload] = useState(0);
  const [data, setData] = useState<SoldOutResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorKey, setErrorKey] = useState("");
  useEffect(() => {
    if (authLoading || !isSuperAdmin) return;
    let cancelled = false;
    setLoading(true); setData(null); setErrorKey("");
    fetchSoldOut(q, scope, offset).then(result => {
      if (!cancelled) setData(result);
    }).catch((error: unknown) => {
      if (!cancelled) setErrorKey(error instanceof ApiError && (error.status === 401 || error.status === 403)
        ? "soldOut.denied" : "soldOut.unavailable");
    }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [authLoading, isSuperAdmin, q, scope, offset, reload]);
  const date = (value: string) => new Intl.DateTimeFormat(i18n.language.startsWith("ja") ? "ja-JP" : "en-GB", {
    timeZone: "Asia/Tokyo", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
  }).format(new Date(value));
  const columns: DataTableColumn<SoldOutItem>[] = [
    { key: "product_title", header: t("soldOut.product"), renderCell: item => item.product_title || <>
      {item.raw_product_name}<small> {t("soldOut.rawFallback")}</small>
    </> },
    { key: "provider", header: t("soldOut.provider") },
    { key: "status", header: t("soldOut.status"), renderCell: () => t("soldOut.soldOut") },
    { key: "raw_quantity", header: t("soldOut.quantity"), renderCell: item => `${item.raw_quantity} ${item.raw_unit}`.trim() },
    { key: "raw_price", header: t("soldOut.price") },
    { key: "line_posted_at", header: t("soldOut.posted"), renderCell: item => item.line_posted_at ? date(item.line_posted_at) : t("soldOut.noDate") },
    { key: "source_is_active", header: t("soldOut.sourceState"), renderCell: item => t(item.source_is_active === true
      ? "soldOut.active" : item.source_is_active === false ? "soldOut.history" : "soldOut.unknown") },
    { key: "source", header: t("soldOut.source"), renderCell: item => <SourceDetail key={item.analysis_result_id} item={item} /> },
  ];
  if (authLoading) return <PageLayout navKey="nav.superAdminTcgSoldOut">{t("common.loading")}</PageLayout>;
  if (!isSuperAdmin) return <PageLayout navKey="nav.superAdminTcgSoldOut"><p role="alert">{t("soldOut.denied")}</p></PageLayout>;
  return <PageLayout navKey="nav.superAdminTcgSoldOut" subtitleKey="soldOut.subtitle">
    <ContentToolbar left={<>
      <label className="comp-field">
        <span className="comp-field__label">{t("soldOut.search")}</span>
        <input className="comp-field__input" type="search" value={draft} maxLength={100}
          onChange={event => setDraft(event.target.value)}
          onKeyDown={event => { if (event.key === "Enter") { setQ(draft.trim()); setOffset(0); } }} />
      </label>
      <Select label={t("soldOut.scope")} value={scope} options={[
        { value: "all", label: t("soldOut.all") }, { value: "active", label: t("soldOut.active") }, { value: "history", label: t("soldOut.history") },
      ]} onChange={event => { setScope(event.target.value as SourceScope); setOffset(0); }} />
    </>} right={<><Button onClick={() => { setQ(draft.trim()); setOffset(0); }}>{t("soldOut.searchAction")}</Button><Button variant="secondary" disabled={loading} onClick={() => setReload(value => value + 1)}>{t("soldOut.reload")}</Button></>} />
    {loading && <p role="status">{t("common.loading")}</p>}
    {errorKey && <p role="alert">{t(errorKey)}</p>}
    {data && <>
      <p><span>{t("soldOut.total", { count: data.total })}</span> · <span>{t("soldOut.asOf", { date: date(data.as_of) })}</span></p>
      <DataTable columns={columns} data={data.items} rowKey={item => item.analysis_result_id}
        emptyState={t("soldOut.empty")} />
      <div>
        <Button variant="secondary" disabled={offset === 0} onClick={() => setOffset(value => Math.max(0, value - 50))}>{t("soldOut.previous")}</Button>
        <span> {t("soldOut.page", { page: Math.floor(offset / 50) + 1 })} </span>
        <Button variant="secondary" disabled={offset + data.items.length >= data.total} onClick={() => setOffset(value => value + 50)}>{t("soldOut.next")}</Button>
        {offset > 0 && <Button variant="secondary" onClick={() => setOffset(0)}>{t("soldOut.first")}</Button>}
      </div>
    </>}
  </PageLayout>;
}
