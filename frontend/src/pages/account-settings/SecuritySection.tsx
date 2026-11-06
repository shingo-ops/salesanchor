import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { authErrorMessage } from "../../lib/auth/authErrorMessage";
import { isDevSession } from "../../lib/auth/devSessionSlot";
import { api } from "../../lib/api";
import PasswordChangeForm from "../../features/auth/PasswordChangeForm";
import { ACCOUNT_ICONS } from "../../constants/icons";
import { ICON } from "../../constants/iconSizes";
import { Badge } from "../../components/Badge";
import { Button } from "../../components/Button";
import ConfirmModal from "../../components/ConfirmModal";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { Modal } from "../../components/Modal";
import { Stack } from "../../components/Stack";
import PasskeySection from "./PasskeySection";
import PushNotifySection from "./PushNotifySection";

interface DeviceItem {
  id: number;
  label: string;
  location: string | null;
  created_via: string;
  created_at: string | null;
  last_used_at: string | null;
  is_current: boolean;
}

/** ログインしている機械の一覧と、その機械のログアウト（ADR-1055・K8） */
function DevicesSection() {
  const { t, i18n } = useTranslation();
  const [items, setItems] = useState<DeviceItem[]>([]);
  const [pendingRemove, setPendingRemove] = useState<DeviceItem | null>(null);
  const [removing, setRemoving] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const res = await api.get<{ items: DeviceItem[] }>("/auth/devices");
      setItems(res.items);
    } catch (err) {
      setError(authErrorMessage(err, t, "login"));
    }
  }, [t]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleRemove = async () => {
    if (!pendingRemove) return;
    setError("");
    setRemoving(true);
    try {
      await api.delete("/auth/devices/" + pendingRemove.id);
      setPendingRemove(null);
      await load();
    } catch (err) {
      setPendingRemove(null);
      setError(authErrorMessage(err, t, "login"));
    } finally {
      setRemoving(false);
    }
  };

  const formatDate = (value: string) => new Date(value).toLocaleString(i18n.language);

  const columns: DataTableColumn<DeviceItem>[] = [
    {
      key: "label",
      header: t("accountSettings.devices.colLabel"),
      renderCell: (row) => (
        <>
          {row.label}
          {row.is_current && (
            <Badge variant="info" size="sm">
              {t("accountSettings.devices.current")}
            </Badge>
          )}
        </>
      ),
    },
    {
      key: "location",
      header: t("accountSettings.devices.colLocation"),
      renderCell: (row) => row.location ?? t("accountSettings.devices.unknown"),
    },
    {
      key: "last_used_at",
      header: t("accountSettings.devices.colLastUsed"),
      renderCell: (row) => (row.last_used_at ? formatDate(row.last_used_at) : ""),
    },
    {
      key: "actions",
      header: "",
      renderCell: (row) => (
        <Button type="button" variant="danger" size="sm" onClick={() => setPendingRemove(row)}>
          {t("accountSettings.devices.remove")}
        </Button>
      ),
    },
  ];

  return (
    <section className="account-settings-section">
      <div className="account-settings-section-title">
        <ACCOUNT_ICONS.security size={ICON.md} aria-hidden="true" />
        {t("accountSettings.devices.title")}
      </div>
      <p>{t("accountSettings.devices.description")}</p>
      <Stack gap="4">
        <DataTable<DeviceItem>
          columns={columns}
          data={items}
          rowKey={(row) => String(row.id)}
          emptyState={t("accountSettings.devices.empty")}
          mobileCards
        />
        <p>{t("accountSettings.devices.geoipCredit")}</p>
        {error && <div className="error-message">{error}</div>}
      </Stack>
      <ConfirmModal
        open={pendingRemove !== null}
        danger
        title={t("accountSettings.devices.removeTitle")}
        message={t("accountSettings.devices.removeMessage")}
        confirmLabel={t("accountSettings.devices.remove")}
        confirmLoading={removing}
        onConfirm={() => void handleRemove()}
        onCancel={() => setPendingRemove(null)}
      />
    </section>
  );
}

/** 予備の合言葉の残り数と作り直し。10個は作ったときに1回だけ見せる（ADR-1055・D14） */
function RecoveryCodesSection() {
  const { t } = useTranslation();
  const [remaining, setRemaining] = useState<number | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [codes, setCodes] = useState<string[] | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const res = await api.get<{ remaining: number }>("/auth/recovery-codes/status");
      setRemaining(res.remaining);
    } catch (err) {
      setError(authErrorMessage(err, t, "login"));
    }
  }, [t]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleCreate = async () => {
    setError("");
    setBusy(true);
    try {
      const res = await api.post<{ codes: string[] }>("/auth/recovery-codes", {});
      setConfirmOpen(false);
      setCodes(res.codes);
      await load();
    } catch (err) {
      setConfirmOpen(false);
      setError(authErrorMessage(err, t, "login"));
    } finally {
      setBusy(false);
    }
  };

  const handleCopy = async () => {
    if (!codes) return;
    try {
      await navigator.clipboard.writeText(codes.join("\n"));
      setCopied(true);
    } catch {
      // コピーできなくても、画面の10個を書き留められる
    }
  };

  const closeShown = () => {
    setCodes(null);
    setCopied(false);
  };

  return (
    <section className="account-settings-section">
      <div className="account-settings-section-title">
        <ACCOUNT_ICONS.security size={ICON.md} aria-hidden="true" />
        {t("accountSettings.recoveryCodes.title")}
      </div>
      <p>{t("accountSettings.recoveryCodes.description")}</p>
      <Stack gap="3">
        {remaining !== null && <p>{t("accountSettings.recoveryCodes.remaining", { count: remaining })}</p>}
        {error && <div className="error-message">{error}</div>}
        <Button type="button" variant="secondary" disabled={busy} onClick={() => setConfirmOpen(true)}>
          {t("accountSettings.recoveryCodes.regenerate")}
        </Button>
      </Stack>
      <ConfirmModal
        open={confirmOpen}
        title={t("accountSettings.recoveryCodes.regenerateTitle")}
        message={t("accountSettings.recoveryCodes.regenerateMessage")}
        confirmLabel={t("accountSettings.recoveryCodes.regenerate")}
        confirmLoading={busy}
        onConfirm={() => void handleCreate()}
        onCancel={() => setConfirmOpen(false)}
      />
      <Modal
        open={codes !== null}
        size="sm"
        title={t("accountSettings.recoveryCodes.shownTitle")}
        onClose={closeShown}
        footer={
          <>
            <Button variant="secondary" onClick={() => void handleCopy()}>
              {t(copied ? "accountSettings.recoveryCodes.copied" : "accountSettings.recoveryCodes.copy")}
            </Button>
            <Button variant="primary" onClick={closeShown}>
              {t("common.close")}
            </Button>
          </>
        }
      >
        <p>{t("accountSettings.recoveryCodes.shownBody")}</p>
        <ul>
          {(codes ?? []).map((code) => (
            <li key={code}>{code}</li>
          ))}
        </ul>
      </Modal>
    </section>
  );
}

export default function SecuritySection() {
  const { t } = useTranslation();

  return (
    <>
    <section className="account-settings-section">
      <div className="account-settings-section-title">
        <ACCOUNT_ICONS.security size={ICON.md} aria-hidden="true" />
        {t("accountSettings.sectionSecurity")}
      </div>

      <PasswordChangeForm />
    </section>
    {!isDevSession() && <PushNotifySection />}
    {!isDevSession() && <DevicesSection />}
    {!isDevSession() && <RecoveryCodesSection />}
    {!isDevSession() && <PasskeySection />}
    </>
  );
}
