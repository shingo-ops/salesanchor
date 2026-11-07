/**
 * スタッフ自己登録の招待リンク（ADR-1068・設計 §3-5）。
 * 「招待リンクを作る」Modal と「招待リンクの一覧」Modal。メールは送らない（管理者が URL を手で送る）。
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Modal } from "../../components/Modal";
import { Select } from "../../components/Select";
import { Button } from "../../components/Button";
import { DataTable } from "../../components/DataTable";
import type { DataTableColumn } from "../../components/DataTable";
import ConfirmModal from "../../components/ConfirmModal";
import { TextFieldControl } from "../../components/TextField";
import { LoadingBlock } from "../../components/loading";
import { api } from "../../lib/api";
import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";
import type { StaffRole } from "./StaffFormFields";

interface InviteCreated {
  id: number;
  url: string;
  expires_at: string;
}

interface InviteItem {
  id: number;
  status: string;
  role_id: number;
  role_name: string | null;
  expires_at: string;
  created_at: string | null;
  created_by: number;
  created_by_name: string | null;
}

/** URL の読み取り専用の欄・コピーのボタン・期限。作成と作り直しで共用する。 */
function InviteLinkResult({ result }: { result: InviteCreated }) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);
  const [copyFailed, setCopyFailed] = useState(false);

  const copy = () => {
    setCopyFailed(false);
    navigator.clipboard.writeText(result.url).then(
      () => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      },
      () => setCopyFailed(true),
    );
  };

  return (
    <div>
      <div className="form-group">
        <label htmlFor="staff_join_invite_url">{t("staff.join.inviteUrl")}</label>
        <div className="actions">
          <TextFieldControl id="staff_join_invite_url" readOnly value={result.url} onFocus={(e) => e.currentTarget.select()} />
          <Button type="button" variant="secondary" size="sm" onClick={copy}>
            {copied ? t("staff.join.copied") : t("staff.join.copy")}
          </Button>
        </div>
      </div>
      <p>{t("staff.join.inviteExpires", { date: new Date(result.expires_at).toLocaleString() })}</p>
      <p>{t("staff.join.inviteNoMail")}</p>
      {copyFailed && <div className="error-message">{t("staff.join.copyFailed")}</div>}
    </div>
  );
}

interface CreateProps {
  open: boolean;
  onClose: () => void;
  roles: StaffRole[];
}

/** 「招待リンクを作る」Modal。役割を選んで作成すると URL とコピーが出る。 */
export function StaffJoinInviteCreateModal({ open, onClose, roles }: CreateProps) {
  const { t } = useTranslation();
  const invalidate = useInvalidateApi();
  const [roleId, setRoleId] = useState("");
  const [result, setResult] = useState<InviteCreated | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const close = () => {
    setRoleId("");
    setResult(null);
    setError("");
    onClose();
  };

  const create = async () => {
    if (busy || !roleId) return;
    setError("");
    setBusy(true);
    try {
      const created = await api.post<InviteCreated>("/staff/join-invites", { role_id: parseInt(roleId, 10) });
      setResult(created);
      void invalidate(["staff", "join-invites"]);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.saveError"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal open={open} onClose={close} title={t("staff.join.createTitle")} size="md">
      {error && <div className="error-message">{error}</div>}
      {result ? (
        <>
          <InviteLinkResult result={result} />
          <div className="form-actions">
            <Button type="button" variant="secondary" size="md" onClick={close}>{t("common.close")}</Button>
          </div>
        </>
      ) : (
        <>
          <Select
            label={t("staff.role")}
            required
            value={roleId}
            onChange={(e) => setRoleId(e.target.value)}
            placeholder={t("common.pleaseSelect")}
            options={roles.map((r) => ({ value: String(r.id), label: r.name }))}
          />
          <div className="form-actions">
            <Button type="button" variant="secondary" size="md" onClick={close} disabled={busy}>{t("common.cancel")}</Button>
            <Button type="button" variant="primary" size="md" loading={busy} disabled={busy || !roleId} onClick={create}>
              {t("staff.join.create")}
            </Button>
          </div>
        </>
      )}
    </Modal>
  );
}

interface ListProps {
  open: boolean;
  onClose: () => void;
}

/** 「招待リンクの一覧」Modal。open の行だけ「作り直す」「取り消す」。 */
export function StaffJoinInviteListModal({ open, onClose }: ListProps) {
  const { t } = useTranslation();
  const invitesQ = useApiQuery<InviteItem[]>("/staff/join-invites", { enabled: open });
  const invalidate = useInvalidateApi();
  const [reissued, setReissued] = useState<InviteCreated | null>(null);
  const [revokeTarget, setRevokeTarget] = useState<InviteItem | null>(null);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);

  const close = () => {
    setReissued(null);
    setRevokeTarget(null);
    setError("");
    onClose();
  };

  const reload = () => void invalidate(["staff", "join-invites"]);

  const reissue = async (item: InviteItem) => {
    if (busyId !== null) return;
    setError("");
    setBusyId(item.id);
    try {
      setReissued(await api.post<InviteCreated>(`/staff/join-invites/${item.id}/reissue`, {}));
      reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.saveError"));
    } finally {
      setBusyId(null);
    }
  };

  const revoke = async () => {
    if (!revokeTarget) return;
    const id = revokeTarget.id;
    setRevokeTarget(null);
    setError("");
    try {
      await api.post(`/staff/join-invites/${id}/revoke`, {});
      if (reissued?.id === id) setReissued(null);
      reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.saveError"));
    }
  };

  const statusLabel = (status: string) =>
    status === "open" || status === "submitted" ? t(`staff.join.status_${status}`) : status;

  const columns: DataTableColumn<InviteItem>[] = [
    { key: "status", header: t("staff.join.colStatus"), renderCell: (i) => statusLabel(i.status) },
    { key: "role", header: t("staff.join.colRole"), renderCell: (i) => i.role_name || "-" },
    { key: "expires", header: t("staff.join.colExpires"), renderCell: (i) => new Date(i.expires_at).toLocaleString() },
    { key: "creator", header: t("staff.join.colCreatedBy"), renderCell: (i) => i.created_by_name || "-" },
    {
      key: "actions",
      header: t("common.actions"),
      renderCell: (i) =>
        i.status === "open" ? (
          <span className="actions">
            <Button variant="secondary" size="sm" disabled={busyId !== null} onClick={() => void reissue(i)}>
              {t("staff.join.reissue")}
            </Button>
            <Button variant="danger" size="sm" disabled={busyId !== null} onClick={() => setRevokeTarget(i)}>
              {t("staff.join.revoke")}
            </Button>
          </span>
        ) : null,
    },
  ];

  const loadError = invitesQ.error
    ? (invitesQ.error instanceof Error ? invitesQ.error.message : t("common.fetchError"))
    : "";
  const shownError = error || loadError;

  return (
    <>
      <Modal open={open} onClose={close} title={t("staff.join.listTitle")} size="lg">
        {shownError && <div className="error-message">{shownError}</div>}
        {reissued && <InviteLinkResult result={reissued} />}
        {invitesQ.isPending ? (
          <LoadingBlock />
        ) : (
          <DataTable
            columns={columns}
            data={invitesQ.data ?? []}
            rowKey={(i) => String(i.id)}
            emptyState={<span>{t("staff.join.empty")}</span>}
          />
        )}
        <div className="form-actions">
          <Button type="button" variant="secondary" size="md" onClick={close}>{t("common.close")}</Button>
        </div>
      </Modal>
      <ConfirmModal
        open={!!revokeTarget}
        title={t("staff.join.revokeTitle")}
        message={t("staff.join.revokeMessage")}
        confirmLabel={t("staff.join.revoke")}
        danger
        onConfirm={() => void revoke()}
        onCancel={() => setRevokeTarget(null)}
      />
    </>
  );
}
