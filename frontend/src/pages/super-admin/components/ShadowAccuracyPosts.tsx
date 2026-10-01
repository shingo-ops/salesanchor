/**
 * 解析精度管理（新方式）: 投稿照合タブ。
 * 左に投稿一覧（run 単位・ページング）、右に詳細（原文と、ブロックごとの書き写し・判定・理由）。
 */
import { useEffect, useState } from "react";
import type { TFunction } from "i18next";
import { useTranslation } from "react-i18next";
import { Badge } from "../../../components/Badge";
import { Button } from "../../../components/Button";
import { Card } from "../../../components/Card";
import { DataTable, type DataTableColumn } from "../../../components/DataTable";
import { Select } from "../../../components/Select";
import { ShadowSourcePane } from "../../../features/tcg-analysis-review/ShadowSourcePane";
import { api } from "../../../lib/api";
import { errorKeyOf } from "./shadowAccuracyErrors";
import {
  SIGNAL_CODES,
  type AccuracyBlock,
  type AccuracyPostDetail,
  type AccuracyPostRow,
  type AccuracyPostsResponse,
  type PeriodDays,
  type PostFilters,
  type ReviewItemEntry,
  type SignalCode,
} from "./shadowAccuracyTypes";

const PAGE_SIZE = 20;

interface Props {
  days: PeriodDays;
  supplierId: string;
  filters: PostFilters;
  onFiltersChange: (filters: PostFilters) => void;
}

function formatDate(isoString: string | null, locale: string): string {
  if (!isoString) return "—";
  return new Intl.DateTimeFormat(locale.startsWith("ja") ? "ja-JP" : "en-GB", {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).format(new Date(isoString));
}

function hitSignals(signals: Record<SignalCode, boolean | number>): SignalCode[] {
  return SIGNAL_CODES.filter((code) => Boolean(signals[code]));
}

function cell(value: string | number | null | undefined): string {
  return value == null || value === "" ? "—" : String(value);
}

interface StageRow {
  stage: "copy" | "judgement" | "reason";
  product: string;
  price: string;
  unit: string;
  quantity: string;
  state: string;
  ship: string;
}

function reasonsOf(items: ReviewItemEntry[], names: string[]): string {
  const hits = items.filter((r) => r.item != null && names.includes(r.item) && r.reason);
  return hits.map((r) => r.reason).join(" / ") || "—";
}

const MATCH_STATUS_KEY = {
  matched: "shadowReview.matchStatusMatched",
  ambiguous: "shadowReview.matchStatusAmbiguous",
  unmatched: "shadowReview.matchStatusUnmatched",
} as const;

function stageRows(block: AccuracyBlock, t: TFunction): StageRow[] {
  const judgedName = block.product_name ?? (block.product_id != null ? String(block.product_id) : null);
  const productReason = reasonsOf(block.review_items, ["product"]);
  const basis = block.evidence?.basis ? `(${block.evidence.basis})` : "";
  return [
    {
      stage: "copy",
      product: cell(block.raw_product_name),
      price: cell(block.raw_price),
      unit: cell(block.raw_unit),
      quantity: cell(block.raw_quantity),
      state: cell(block.raw_state),
      ship: cell(block.raw_ship),
    },
    {
      stage: "judgement",
      product: `${cell(judgedName)} [${t(MATCH_STATUS_KEY[block.match_status])}]`,
      price: cell(block.price_normalized),
      unit: "—",
      quantity: cell(block.quantity_normalized),
      state: [block.condition_canonical, block.status].filter(Boolean).join(" / ") || "—",
      ship: [block.ship_offer_type, block.ship_timing].filter(Boolean).join(" / ") || "—",
    },
    {
      stage: "reason",
      product: [productReason === "—" ? "" : productReason, basis].filter(Boolean).join(" ") || "—",
      price: reasonsOf(block.review_items, ["price_qty"]),
      unit: "—",
      quantity: "—",
      state: "—",
      ship: reasonsOf(block.review_items, ["verify_copied"]),
    },
  ];
}

export function ShadowAccuracyPosts({ days, supplierId, filters, onFiltersChange }: Props) {
  const { t, i18n } = useTranslation();
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<AccuracyPostsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorKey, setErrorKey] = useState("");

  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [detail, setDetail] = useState<AccuracyPostDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailErrorKey, setDetailErrorKey] = useState("");
  const [selectedBlock, setSelectedBlock] = useState<AccuracyBlock | null>(null);

  // 絞り込みが変わったら 1 ページ目に戻す
  useEffect(() => {
    setOffset(0);
  }, [days, supplierId, filters.needsReview, filters.signal]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setErrorKey("");
    const params = new URLSearchParams({
      days: String(days),
      offset: String(offset),
      limit: String(PAGE_SIZE),
    });
    if (supplierId) params.set("supplier_id", supplierId);
    if (filters.needsReview) params.set("needs_review", filters.needsReview);
    if (filters.signal) params.set("signal", filters.signal);
    api
      .get<AccuracyPostsResponse>(`/tcg/shadow-accuracy/posts?${params.toString()}`)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((error: unknown) => {
        if (!cancelled) setErrorKey(errorKeyOf(error));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [days, supplierId, filters.needsReview, filters.signal, offset]);

  useEffect(() => {
    if (!selectedJobId) return;
    let cancelled = false;
    setDetailLoading(true);
    setDetailErrorKey("");
    setSelectedBlock(null);
    api
      .get<AccuracyPostDetail>(`/tcg/shadow-accuracy/posts/${selectedJobId}`)
      .then((result) => {
        if (!cancelled) setDetail(result);
      })
      .catch((error: unknown) => {
        if (!cancelled) setDetailErrorKey(errorKeyOf(error));
      })
      .finally(() => {
        if (!cancelled) setDetailLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedJobId]);

  const postColumns: DataTableColumn<AccuracyPostRow>[] = [
    { key: "supplier_name", header: t("shadowAccuracy.supplier"), renderCell: (r) => r.supplier_name || "—" },
    {
      key: "posted_at",
      header: t("shadowAccuracy.posts.postedAt"),
      renderCell: (r) => formatDate(r.posted_at, i18n.language),
    },
    { key: "blocks", header: t("shadowAccuracy.metric.blocks"), renderCell: (r) => String(r.blocks) },
    {
      key: "needs_review_count",
      header: t("shadowAccuracy.posts.pending"),
      renderCell: (r) => String(r.needs_review_count),
    },
    {
      key: "signals",
      header: t("shadowAccuracy.signal.title"),
      renderCell: (r) => hitSignals(r.signals).map((code) => `${code}×${r.signals[code]}`).join(" ") || "—",
    },
  ];

  const stageColumns: DataTableColumn<StageRow>[] = [
    { key: "stage", header: t("shadowAccuracy.stage.title"), renderCell: (r) => t(`shadowAccuracy.stage.${r.stage}`) },
    { key: "product", header: t("shadowAccuracy.stage.product"), renderCell: (r) => r.product },
    { key: "price", header: t("shadowAccuracy.stage.price"), renderCell: (r) => r.price },
    { key: "unit", header: t("shadowAccuracy.stage.unit"), renderCell: (r) => r.unit },
    { key: "quantity", header: t("shadowAccuracy.stage.quantity"), renderCell: (r) => r.quantity },
    { key: "state", header: t("shadowAccuracy.stage.state"), renderCell: (r) => r.state },
    { key: "ship", header: t("shadowAccuracy.stage.ship"), renderCell: (r) => r.ship },
  ];

  return (
    <div className="shadow-accuracy-posts">
      <div className="shadow-accuracy-filters">
        <Select
          label={t("shadowAccuracy.posts.filterReview")}
          value={filters.needsReview}
          onChange={(e) =>
            onFiltersChange({ ...filters, needsReview: e.target.value as PostFilters["needsReview"] })
          }
          options={[
            { value: "", label: t("shadowAccuracy.posts.reviewAll") },
            { value: "true", label: t("shadowAccuracy.posts.reviewPending") },
            { value: "false", label: t("shadowAccuracy.posts.reviewConfirmed") },
          ]}
        />
        <Select
          label={t("shadowAccuracy.posts.filterSignal")}
          value={filters.signal}
          onChange={(e) => onFiltersChange({ ...filters, signal: e.target.value as PostFilters["signal"] })}
          options={[
            { value: "", label: t("shadowAccuracy.posts.signalAll") },
            ...SIGNAL_CODES.map((code) => ({
              value: code,
              label: `${code} ${t(`shadowAccuracy.signal.label.${code}`)}`,
            })),
          ]}
        />
      </div>

      <div className="shadow-accuracy-split">
        <div className="shadow-accuracy-list">
          {loading && <p role="status">{t("common.loading")}</p>}
          {errorKey && <p role="alert" className="shadow-accuracy-error">{t(errorKey)}</p>}
          {data && (
            <DataTable
              columns={postColumns}
              data={data.items}
              rowKey={(r) => r.job_id}
              density="compact"
              emptyState={t("shadowAccuracy.posts.noItems")}
              onRowClick={(row) => setSelectedJobId(row.job_id)}
              rowClassName={(row) => (row.job_id === selectedJobId ? "shadow-accuracy-row--selected" : "")}
              page={Math.floor(offset / PAGE_SIZE) + 1}
              hasNextPage={offset + data.items.length < data.total}
              onPageChange={(page) => setOffset((page - 1) * PAGE_SIZE)}
              pageInfo={t("shadowAccuracy.posts.total", { count: data.total })}
            />
          )}
        </div>

        <div className="shadow-accuracy-detail" aria-live="polite">
          {!selectedJobId && <p className="shadow-accuracy-note">{t("shadowAccuracy.posts.selectHint")}</p>}
          {detailLoading && <p role="status">{t("common.loading")}</p>}
          {detailErrorKey && <p role="alert" className="shadow-accuracy-error">{t(detailErrorKey)}</p>}
          {detail && selectedJobId && !detailLoading && (
            <>
              <h3>
                {detail.supplier_name || "—"} / {formatDate(detail.posted_at, i18n.language)}
              </h3>
              <p className="shadow-accuracy-note">
                {t("shadowAccuracy.detail.run", {
                  engine: detail.run.engine_version,
                  model: detail.run.requested_model,
                })}
              </p>
              <ShadowSourcePane
                rawText={detail.raw_text}
                blockRange={
                  selectedBlock ? { start: selectedBlock.line_start, end: selectedBlock.line_end } : null
                }
                headingRange={
                  selectedBlock
                    ? { start: selectedBlock.heading_line_start, end: selectedBlock.heading_line_end }
                    : null
                }
              />
              <div className="shadow-accuracy-blocks">
                {detail.blocks.map((block) => (
                  <Card
                    key={block.id}
                    density="compact"
                    className={selectedBlock?.id === block.id ? "shadow-accuracy-block--selected" : ""}
                  >
                    <div className="shadow-accuracy-block-head">
                      <strong>
                        {t("shadowAccuracy.detail.block", { index: block.block_index + 1 })}
                        {block.line_start != null && ` (L${block.line_start}-L${block.line_end})`}
                      </strong>
                      {block.needs_review && (
                        <Badge variant="warning">{t("shadowAccuracy.detail.needsReview")}</Badge>
                      )}
                      {hitSignals(block.signals).map((code) => (
                        <Badge key={code} variant="danger">
                          {code} {t(`shadowAccuracy.signal.short.${code}`)}
                        </Badge>
                      ))}
                      <Button variant="ghost" size="sm" onClick={() => setSelectedBlock(block)}>
                        {t("shadowAccuracy.detail.showInSource")}
                      </Button>
                    </div>
                    <DataTable
                      columns={stageColumns}
                      data={stageRows(block, t)}
                      rowKey={(r) => r.stage}
                      density="compact"
                    />
                  </Card>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
