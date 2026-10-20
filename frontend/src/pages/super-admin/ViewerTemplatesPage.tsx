/**
 * /super-admin/viewer-templates — 閲覧者向け文面のテンプレート一覧と編集（ADR-1019 段11 便1・便2）。
 *
 * - 一覧は名前・送り方・いつ・最終更新の4列。台帳の9件が必ず出る（DB に行が無い鍵は「未登録」）
 * - 行を押すと右から詳細（名前・送り方・いつ・差し込み項目の説明・本文）が出る。「コピー」で copy_text を写す
 * - 本文は Drawer 内で編集して保存できる（PUT。開いた時の updated_at を expected_updated_at に送り、食い違えば 409）
 * - is_super_admin=true のみアクセス可（Page 内で 403 ガード）
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../../lib/api";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import { PageLayout } from "../../components/PageLayout";
import { Button } from "../../components/Button";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { EmptyState } from "../../components/EmptyState";
import { Drawer } from "../../components/Drawer";
import { Textarea } from "../../components/Textarea";
import { Stack } from "../../components/Stack";

interface TemplateItem {
  key: string;
  body: string | null;
  copy_text: string | null;
  placeholders: string[];
  send_mode: "manual" | "auto";
  updated_at: string | null;
  updated_by_name: string | null;
}

// PUT が返す 422 の detail コード → i18n キー（superAdmin.viewerTemplates.*）
const ERROR_KEYS: Record<string, string> = {
  template_placeholders: "errorPlaceholders",
  template_bad_syntax: "errorBadSyntax",
  template_format_spec: "errorFormatSpec",
  template_empty: "errorEmpty",
  template_too_long: "errorTooLong",
  template_line_name_prefix: "errorLineNamePrefix",
};

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
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState("");

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

  const reloadItems = async (): Promise<TemplateItem[] | null> => {
    try {
      const list = await api.get<{ items: TemplateItem[] }>("/super-admin/viewer-templates");
      setItems(list.items);
      return list.items;
    } catch {
      return null;
    }
  };

  // 行を開くたびに一覧を取り直し、最新の行（updated_at）で開く。取れなければ手元の行で開く
  const openDetail = async (row: TemplateItem) => {
    setCopied(false);
    setSaved(false);
    setSaveError("");
    setDraft(row.body ?? "");
    setDetail(row);
    const latest = await reloadItems();
    const fresh = latest?.find(i => i.key === row.key);
    if (fresh) {
      setDetail(fresh);
      setDraft(fresh.body ?? "");
    }
  };

  const save = async () => {
    if (!detail || saving) return;
    setSaving(true);
    setSaved(false);
    setSaveError("");
    try {
      // 開いた時の updated_at（未登録は null）を送る。食い違えば 409
      const res = await api.put<TemplateItem>(`/super-admin/viewer-templates/${detail.key}`, {
        body: draft,
        expected_updated_at: detail.updated_at,
      });
      setDetail(res);
      setDraft(res.body ?? "");
      setSaved(true);
      if ((await reloadItems()) === null) setError(t(`${f}.loadError`));
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setSaveError(t(`${f}.conflict`));
        // 開き直したとき最新の updated_at になるよう一覧だけ取り直す（入力中の文と開いているスライドは変えない）
        await reloadItems();
      }
      else if (e instanceof ApiError && e.status === 404) setSaveError(t(`${f}.errorNotFound`));
      else if (e instanceof ApiError && e.status === 422 && ERROR_KEYS[e.message]) {
        setSaveError(t(`${f}.${ERROR_KEYS[e.message]}`));
      } else setSaveError(t(`${f}.saveError`));
    } finally {
      setSaving(false);
    }
  };

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
          onRowClick={row => { void openDetail(row); }}
          emptyState={<EmptyState title={t("common.noData")} size="compact" />}
        />
      )}

      <Drawer
        open={detail !== null}
        onClose={() => setDetail(null)}
        title={t(`${f}.detailTitle`)}
        footer={
          detail && (
            <Stack direction="row" gap="2">
              <Button
                variant="primary"
                onClick={() => { void save(); }}
                disabled={saving || draft === (detail.body ?? "")}
                data-testid="viewer-templates-save"
              >
                {saving ? t(`${f}.saving`) : t(`${f}.save`)}
              </Button>
              <Button
                variant="secondary"
                onClick={() => detail.copy_text !== null && copyDetail(detail.copy_text)}
                disabled={detail.copy_text === null}
                data-testid="viewer-templates-copy"
              >
                {copied ? t(`${f}.copied`) : t(`${f}.copy`)}
              </Button>
            </Stack>
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
              <Textarea
                label={t(`${f}.bodyLabel`)}
                value={draft}
                onChange={e => {
                  setDraft(e.target.value);
                  setSaved(false);
                }}
                rows={10}
                fullWidth
                helperText={t(`${f}.charCount`, { count: Array.from(draft).length })}
                data-testid="viewer-templates-body"
              />
              {detail.body === null && (
                <div data-testid="viewer-templates-unregistered">{t(`${f}.unregistered`)}</div>
              )}
              {saved && (
                <div role="status" data-testid="viewer-templates-saved">
                  {t(`${f}.saved`)}
                </div>
              )}
              {saveError && (
                <div className="error-message" role="alert" data-testid="viewer-templates-save-error">
                  {saveError}
                </div>
              )}
            </div>
          </div>
        )}
      </Drawer>
    </PageLayout>
  );
}
