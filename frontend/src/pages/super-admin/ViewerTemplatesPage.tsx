/**
 * /super-admin/viewer-templates — 閲覧者向け文面のテンプレート一覧（ADR-1019 段11 便1・読むだけ）。
 *
 * - 一覧は名前・送り方・いつ・最終更新の4列。台帳の9件が必ず出る（DB に行が無い鍵は「未登録」）
 * - 行を押すと右から詳細（名前・送り方・いつ・差し込み項目の説明・本文）が出る。「コピー」で copy_text を写す
 * - 編集は便2。is_super_admin=true のみアクセス可（Page 内で 403 ガード）
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { api } from "../../lib/api";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import { PageLayout } from "../../components/PageLayout";
import { Button } from "../../components/Button";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { EmptyState } from "../../components/EmptyState";
import { Drawer } from "../../components/Drawer";
import { Textarea } from "../../components/Textarea";

interface TemplateItem {
  key: string;
  body: string | null;
  copy_text: string | null;
  placeholders: string[];
  send_mode: "manual" | "auto";
  updated_at: string | null;
  updated_by_name: string | null;
}

function formatDate(value: string | null): string | null {
  if (!value) return null;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
}

export default function ViewerTemplatesPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { isSuperAdmin, loading: authLoading } = useSuperAdmin();
  const f = "superAdmin.viewerTemplates";
  const [items, setItems] = useState<TemplateItem[]>([]);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState("");
  const [detail, setDetail] = useState<TemplateItem | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (authLoading || !isSuperAdmin) return;
    let cancelled = false;
    setFetching(true);
    api
      .get<{ items: TemplateItem[] }>("/super-admin/viewer-templates")
      .then(res => {
        if (!cancelled) setItems(res.items);
      })
      .catch(() => {
        if (!cancelled) setError(t(`${f}.loadError`));
      })
      .finally(() => {
        if (!cancelled) setFetching(false);
      });
    return () => {
      cancelled = true;
    };
  }, [authLoading, isSuperAdmin, t]);

  if (authLoading) {
    return <div className="page">{t("common.loading")}</div>;
  }

  if (!isSuperAdmin) {
    return (
      <PageLayout navKey="nav.superAdminViewerTemplates">
        <div className="error-message" role="alert">
          {t("superAdmin.accessDenied")}
        </div>
      </PageLayout>
    );
  }

  const copyDetail = (text: string) => {
    navigator.clipboard.writeText(text).then(
      () => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      },
      () => setError(t(`${f}.copyError`)),
    );
  };

  const columns: DataTableColumn<TemplateItem>[] = [
    { key: "name", header: t(`${f}.colName`), renderCell: row => t(`${f}.names.${row.key}`) },
    { key: "send_mode", header: t(`${f}.colSendMode`), renderCell: row => t(`${f}.sendMode.${row.send_mode}`) },
    { key: "when", header: t(`${f}.colWhen`), renderCell: row => t(`${f}.when.${row.key}`) },
    {
      key: "updated_at",
      header: t(`${f}.colUpdated`),
      renderCell: row =>
        row.body === null ? t(`${f}.unregistered`) : formatDate(row.updated_at) ?? t(`${f}.empty`),
    },
  ];

  return (
    <PageLayout
      navKey="nav.superAdminViewerTemplates"
      subtitleKey="superAdmin.viewerTemplates.subtitle"
      headerAction={
        <Button variant="secondary" size="sm" onClick={() => navigate("/super-admin/viewers")}>
          {t(`${f}.backToViewers`)}
        </Button>
      }
    >
      {error && (
        <div className="error-message" role="alert" data-testid="viewer-templates-error">
          {error}
        </div>
      )}
      {fetching && items.length === 0 ? (
        <div>{t("common.loading")}</div>
      ) : (
        <DataTable
          columns={columns}
          data={items}
          rowKey={row => row.key}
          onRowClick={row => {
            setCopied(false);
            setDetail(row);
          }}
          emptyState={<EmptyState title={t("common.noData")} size="compact" />}
        />
      )}

      <Drawer
        open={detail !== null}
        onClose={() => setDetail(null)}
        title={t(`${f}.detailTitle`)}
        footer={
          detail && (
            <Button
              variant="primary"
              onClick={() => detail.copy_text !== null && copyDetail(detail.copy_text)}
              disabled={detail.copy_text === null}
              data-testid="viewer-templates-copy"
            >
              {copied ? t(`${f}.copied`) : t(`${f}.copy`)}
            </Button>
          )
        }
      >
        {detail && (
          <div className="form-grid" data-testid="viewer-templates-detail">
            <div className="form-row">
              <label>{t(`${f}.colName`)}</label>
              <div>{t(`${f}.names.${detail.key}`)}</div>
            </div>
            <div className="form-row">
              <label>{t(`${f}.colSendMode`)}</label>
              <div>{t(`${f}.sendMode.${detail.send_mode}`)}</div>
            </div>
            <div className="form-row">
              <label>{t(`${f}.colWhen`)}</label>
              <div>{t(`${f}.when.${detail.key}`)}</div>
            </div>
            <div className="form-row">
              <label>{t(`${f}.placeholdersLabel`)}</label>
              {detail.placeholders.length === 0 ? (
                <div>{t(`${f}.placeholdersNone`)}</div>
              ) : (
                <ul data-testid="viewer-templates-placeholders">
                  {detail.placeholders.map(p => (
                    <li key={p}>
                      {`{${p}}`} = {t(`${f}.placeholders.${p}`)}
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div className="form-row">
              {detail.body === null ? (
                <>
                  <label>{t(`${f}.bodyLabel`)}</label>
                  <div data-testid="viewer-templates-unregistered">{t(`${f}.unregistered`)}</div>
                </>
              ) : (
                <Textarea
                  label={t(`${f}.bodyLabel`)}
                  value={detail.body}
                  readOnly
                  rows={10}
                  fullWidth
                  data-testid="viewer-templates-body"
                />
              )}
            </div>
          </div>
        )}
      </Drawer>
    </PageLayout>
  );
}
