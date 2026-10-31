import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { browserSupportsWebAuthn } from "@simplewebauthn/browser";
import { api } from "../../lib/api";
import { authErrorMessage } from "../../lib/auth/authErrorMessage";
import { passkeyBrowserError, registerPasskey } from "../../lib/auth/passkey";
import { ACCOUNT_ICONS } from "../../constants/icons";
import { ICON } from "../../constants/iconSizes";
import { Button } from "../../components/Button";
import ConfirmModal from "../../components/ConfirmModal";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { Stack } from "../../components/Stack";
import { TextFieldControl } from "../../components/TextField";

interface PasskeyItem {
  id: number;
  label: string | null;
  created_at: string | null;
  last_used_at: string | null;
}

export default function PasskeySection() {
  const { t, i18n } = useTranslation();
  const [items, setItems] = useState<PasskeyItem[]>([]);
  const [label, setLabel] = useState("");
  const [adding, setAdding] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<PasskeyItem | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const supported = browserSupportsWebAuthn();

  const load = useCallback(async () => {
    try {
      const res = await api.get<{ items: PasskeyItem[] }>("/auth/passkeys");
      setItems(res.items);
    } catch (err) {
      setError(authErrorMessage(err, t, "passkey"));
    }
  }, [t]);

  useEffect(() => {
    void load();
  }, [load]);

  const errorText = (err: unknown): string => {
    const kind = passkeyBrowserError(err);
    if (kind === "cancelled") return t("authError.passkeyCancelled");
    if (kind === "exists") return t("authError.passkeyExists");
    return authErrorMessage(err, t, "passkey");
  };

  const handleAdd = async () => {
    setError("");
    setSuccess(false);
    setAdding(true);
    try {
      await registerPasskey(label);
      setLabel("");
      setSuccess(true);
      await load();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setAdding(false);
    }
  };

  const handleDelete = async () => {
    if (!pendingDelete) return;
    setError("");
    setSuccess(false);
    setDeleting(true);
    try {
      await api.delete("/auth/passkeys/" + pendingDelete.id);
      setPendingDelete(null);
      await load();
    } catch (err) {
      setPendingDelete(null);
      setError(errorText(err));
    } finally {
      setDeleting(false);
    }
  };

  const formatDate = (value: string) => new Date(value).toLocaleDateString(i18n.language);

  const columns: DataTableColumn<PasskeyItem>[] = [
    {
      key: "label",
      header: t("accountSettings.passkeyColName"),
      renderCell: (row) => row.label || t("accountSettings.passkeyUnnamed"),
    },
    {
      key: "created_at",
      header: t("accountSettings.passkeyColCreated"),
      renderCell: (row) => (row.created_at ? formatDate(row.created_at) : ""),
    },
    {
      key: "last_used_at",
      header: t("accountSettings.passkeyColLastUsed"),
      renderCell: (row) =>
        row.last_used_at ? formatDate(row.last_used_at) : t("accountSettings.passkeyNeverUsed"),
    },
    {
      key: "actions",
      header: "",
      renderCell: (row) => (
        <Button type="button" variant="danger" size="sm" onClick={() => setPendingDelete(row)}>
          {t("accountSettings.passkeyDelete")}
        </Button>
      ),
    },
  ];

  return (
    <section className="account-settings-section">
      <div className="account-settings-section-title">
        <ACCOUNT_ICONS.security size={ICON.md} aria-hidden="true" />
        {t("accountSettings.passkeyTitle")}
      </div>
      <p>{t("accountSettings.passkeyDescription")}</p>

      <Stack gap="4">
        <DataTable<PasskeyItem>
          columns={columns}
          data={items}
          rowKey={(row) => String(row.id)}
          emptyState={t("accountSettings.passkeyEmpty")}
          mobileCards
        />

        {error && <div className="error-message">{error}</div>}
        {success && <div className="account-settings-success">{t("accountSettings.passkeyAdded")}</div>}

        {supported ? (
          <Stack gap="3">
            <div className="form-group">
              <label htmlFor="passkey_label">{t("accountSettings.passkeyLabel")}</label>
              <TextFieldControl
                id="passkey_label"
                type="text"
                maxLength={64}
                value={label}
                onChange={(e) => setLabel(e.target.value)}
              />
            </div>
            <Button
              type="button"
              variant="secondary"
              loading={adding}
              disabled={adding}
              onClick={() => void handleAdd()}
            >
              {t("accountSettings.passkeyAdd")}
            </Button>
          </Stack>
        ) : (
          <p>{t("accountSettings.passkeyUnsupported")}</p>
        )}
      </Stack>

      <ConfirmModal
        open={pendingDelete !== null}
        danger
        title={t("accountSettings.passkeyDeleteTitle")}
        message={t("accountSettings.passkeyDeleteMessage")}
        confirmLabel={t("accountSettings.passkeyDelete")}
        confirmLoading={deleting}
        onConfirm={() => void handleDelete()}
        onCancel={() => setPendingDelete(null)}
      />
    </section>
  );
}
