import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import {
  currentSubscription,
  pushSupport,
  subscribeThisDevice,
  unsubscribeThisDevice,
  type PushSupport,
} from "../../lib/webPush";
import { ACCOUNT_ICONS } from "../../constants/icons";
import { ICON } from "../../constants/iconSizes";
import { Stack } from "../../components/Stack";
import { Toggle } from "../../components/Toggle";

interface DeviceItem {
  id: number;
  is_current?: boolean;
}

interface SubscriptionJson {
  endpoint?: string;
  keys?: { p256dh?: string; auth?: string };
}

const TITLE_ID = "account-settings-push-title";

function notificationPermission(): NotificationPermission | null {
  return typeof Notification === "undefined" ? null : Notification.permission;
}

/** 通知の購読の送信（同じ endpoint は upsert） */
async function postSubscription(sub: PushSubscription): Promise<number> {
  const json = sub.toJSON() as SubscriptionJson;
  const res = await api.post<{ id: number }>("/auth/push-subscriptions", {
    endpoint: json.endpoint,
    keys: { p256dh: json.keys?.p256dh, auth: json.keys?.auth },
  });
  return res.id;
}

/** この機械に許可依頼の通知を出す切り替え（ADR-1055 段W） */
export default function PushNotifySection() {
  const { t } = useTranslation();
  const [publicKey, setPublicKey] = useState<string | null>(null);
  const [isTrusted, setIsTrusted] = useState(false);
  const [subId, setSubId] = useState<number | null>(null);
  const [on, setOn] = useState(false);
  const [busy, setBusy] = useState(false);
  const [denied, setDenied] = useState(false);
  const [error, setError] = useState(false);
  const support: PushSupport = pushSupport();

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const [keyRes, devRes] = await Promise.all([
          api.get<{ public_key?: string | null }>("/auth/push-public-key"),
          api.get<{ items?: DeviceItem[] }>("/auth/devices"),
        ]);
        if (cancelled) return;
        if (typeof keyRes?.public_key !== "string") return;
        const trusted = (devRes?.items ?? []).some((d) => d.is_current);
        setPublicKey(keyRes.public_key);
        setIsTrusted(trusted);
        if (notificationPermission() === "denied") setDenied(true);
        if (support === "supported" && trusted && notificationPermission() === "granted") {
          const sub = await currentSubscription();
          if (cancelled || !sub) return;
          const id = await postSubscription(sub);
          if (cancelled) return;
          setSubId(id);
          setOn(true);
        }
      } catch {
        // 読み込み失敗: 何も描かない
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [support]);

  if (typeof publicKey !== "string") return null;

  const handleChange = async (next: boolean) => {
    if (busy) return;
    setError(false);
    setBusy(true);
    try {
      if (next) {
        // 最初の await は許可の確認（iPhone は本人の操作の直後でないと出さない）
        const permission = await Notification.requestPermission();
        if (permission !== "granted") {
          setDenied(permission === "denied");
          if (permission !== "denied") setError(true);
          return;
        }
        const sub = await subscribeThisDevice(publicKey);
        const id = await postSubscription(sub);
        setSubId(id);
        setOn(true);
      } else {
        if (subId !== null) {
          try {
            await api.delete("/auth/push-subscriptions/" + subId);
          } catch {
            // 404 などでも、この機械の購読は外す
          }
        }
        await unsubscribeThisDevice();
        setSubId(null);
        setOn(false);
      }
    } catch {
      setError(true);
      setOn(!next);
    } finally {
      setBusy(false);
    }
  };

  const canToggle = support === "supported";
  const toggleDisabled = busy || !isTrusted || denied;

  return (
    <section className="account-settings-section">
      <div className="account-settings-section-title">
        <ACCOUNT_ICONS.security size={ICON.md} aria-hidden="true" />
        <span id={TITLE_ID}>{t("accountSettings.push.title")}</span>
      </div>
      <p>{t("accountSettings.push.description")}</p>
      <Stack gap="4">
        {support === "ios_needs_home_screen" && <p>{t("accountSettings.push.iosHint")}</p>}
        {support === "unsupported" && <p>{t("accountSettings.push.unsupported")}</p>}
        {canToggle && !isTrusted && <p>{t("accountSettings.push.notTrusted")}</p>}
        {canToggle && denied && <p>{t("accountSettings.push.denied")}</p>}
        {canToggle && (
          <Toggle
            checked={on}
            disabled={toggleDisabled}
            aria-labelledby={TITLE_ID}
            onCheckedChange={(next) => void handleChange(next)}
          />
        )}
        {error && <div className="error-message">{t("accountSettings.push.error")}</div>}
      </Stack>
    </section>
  );
}
