/**
 * ログインの許可待ちの一覧と許可の小窓（ADR-1055 K7・ADR-1063）。
 * 運営の画面（/super-admin/login-requests）と会社のオーナーの画面（/management-center/login-requests）で共有する。
 * - 許可には本人確認の方法（note）が必須
 * - 読む先・許可する先だけを props で受ける（見た目と動きは1か所）
 */
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { Button } from "../../components/Button";
import ConfirmModal from "../../components/ConfirmModal";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { Stack } from "../../components/Stack";
import { TextFieldControl } from "../../components/TextField";
import { LoadingBlock } from "../../components/loading";

export interface AdminLoginRequestRow {
  id: string;
  user_id: number;
  email: string | null;
  full_name: string | null;
  status: string;
  label: string | null;
  location: string | null;
  created_at: string | null;
  expires_at: string | null;
}

export interface AdminLoginRequestListProps {
  /** 一覧を読む先（api の相対パス） */
  listPath: string;
  /** 許可する先（api の相対パス） */
  approvePath: (id: string) => string;
}

const NOTE_MAX_LENGTH = 200;

export default function AdminLoginRequestList({ listPath, approvePath }: AdminLoginRequestListProps) {
  const { t, i18n } = useTranslation();
  const [rows, setRows] = useState<AdminLoginRequestRow[]>([]);
  const [fetching, setFetching] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [target, setTarget] = useState<AdminLoginRequestRow | null>(null);
  const [note, setNote] = useState("");
  const [approving, setApproving] = useState(false);

  const load = useCallback(async () => {
    setFetching(true);
    setError("");
    try {
      const res = await api.get<{ items: AdminLoginRequestRow[] }>(listPath);
      setRows(res.items);
    } catch {
      setError(t("superAdmin.loginRequests.loadError"));
    } finally {
      setFetching(false);
    }
  }, [listPath, t]);

  useEffect(() => {
    void load();
  }, [load]);

  const closeConfirm = () => {
    setTarget(null);
    setNote("");
  };

  const handleApprove = async () => {
    if (!target || note.trim() === "") return;
    setError("");
    setSuccess("");
    setApproving(true);
    try {
      await api.post(approvePath(target.id), { note: note.trim() });
      setSuccess(t("superAdmin.loginRequests.approved"));
      closeConfirm();
      await load();
    } catch {
      closeConfirm();
      setError(t("superAdmin.loginRequests.approveError"));
    } finally {
      setApproving(false);
    }
  };

  const formatDate = (value: string | null) => (value ? new Date(value).toLocaleString(i18n.language) : "");

  const columns: DataTableColumn<AdminLoginRequestRow>[] = [
    {
      key: "user",
      header: t("superAdmin.loginRequests.colUser"),
      renderCell: (row) => row.full_name || row.email || String(row.user_id),
    },
    { key: "email", header: t("superAdmin.loginRequests.colEmail"), renderCell: (row) => row.email ?? "" },
    {
      key: "label",
      header: t("superAdmin.loginRequests.colDevice"),
      renderCell: (row) => row.label ?? t("superAdmin.loginRequests.unknown"),
    },
    {
      key: "location",
      header: t("superAdmin.loginRequests.colLocation"),
      renderCell: (row) => row.location ?? t("superAdmin.loginRequests.unknown"),
    },
    {
      key: "created_at",
      header: t("superAdmin.loginRequests.colRequested"),
      renderCell: (row) => formatDate(row.created_at),
    },
    {
      key: "expires_at",
      header: t("superAdmin.loginRequests.colExpires"),
      renderCell: (row) => formatDate(row.expires_at),
    },
    {
      key: "actions",
      header: "",
      renderCell: (row) => (
        <Button type="button" variant="primary" size="sm" onClick={() => setTarget(row)}>
          {t("superAdmin.loginRequests.approve")}
        </Button>
      ),
    },
  ];

  return (
    <>
      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}
      {success && (
        <div className="success-message" role="status">
          {success}
        </div>
      )}
      {fetching ? (
        <LoadingBlock />
      ) : (
        <DataTable<AdminLoginRequestRow>
          columns={columns}
          data={rows}
          rowKey={(row) => row.id}
          emptyState={t("superAdmin.loginRequests.empty")}
          mobileCards
        />
      )}
      <ConfirmModal
        open={target !== null}
        title={t("superAdmin.loginRequests.approveTitle")}
        message={
          <Stack gap="3">
            <p>{t("superAdmin.loginRequests.approveMessage")}</p>
            <label htmlFor="login-request-note">{t("superAdmin.loginRequests.noteLabel")}</label>
            <TextFieldControl
              id="login-request-note"
              type="text"
              maxLength={NOTE_MAX_LENGTH}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              required
            />
            <p>{t("superAdmin.loginRequests.noteHelp")}</p>
          </Stack>
        }
        confirmLabel={t("superAdmin.loginRequests.approve")}
        confirmDisabled={note.trim() === ""}
        confirmLoading={approving}
        onConfirm={() => void handleApprove()}
        onCancel={closeConfirm}
      />
    </>
  );
}
