/**
 * 予備の合言葉を作る案内（ADR-1055 段A・A-3・design.md D8・D16）。
 * ログイン後に GET /auth/recovery-codes/status の残りが0のとき、Modal を1回出す。
 * 出したことは localStorage に「recoveryPrompt:{人の id}:{sid}」の鍵で覚え、同じログインの間は別のタブでも出し直さない。
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { Modal } from "../../components/Modal";
import { Stack } from "../../components/Stack";
import { api } from "../../lib/api";
import { isSelfAuth } from "../../lib/auth/provider";
import { currentAccessToken, readClaims } from "../../lib/auth/selfAuth";

const KEY_PREFIX = "recoveryPrompt:";

/** 鍵は「recoveryPrompt:{userId}:{sid}」。sid の無い古いトークンのときは sid の所を空にする（鍵は人の id だけ）。 */
export function recoveryPromptKey(userId: string, sid: string | null): string {
  return `${KEY_PREFIX}${userId}:${sid ?? ""}`;
}

/** signIn の成功時とログアウト時に呼ぶ。「recoveryPrompt:{userId}:」で始まる鍵を全部消す。 */
export function clearRecoveryPromptMarks(userId?: string): void {
  try {
    const prefix = userId ? `${KEY_PREFIX}${userId}:` : KEY_PREFIX;
    const targets: string[] = [];
    for (let i = 0; i < localStorage.length; i += 1) {
      const key = localStorage.key(i);
      if (key && key.startsWith(prefix)) targets.push(key);
    }
    for (const key of targets) localStorage.removeItem(key);
  } catch {
    // 保存領域が使えないときは何もしない
  }
}

/** 今のトークンの人の鍵を消す。signIn の成功時・許可で入ったとき・ログアウトの直前に呼ぶ。 */
export function clearRecoveryPromptMarksForCurrentUser(): void {
  const token = currentAccessToken();
  const claims = token ? readClaims(token) : null;
  if (claims) clearRecoveryPromptMarks(claims.sub);
}

function alreadyShown(key: string): boolean {
  try {
    return localStorage.getItem(key) !== null;
  } catch {
    return false; // 読めなければ出す側に倒す
  }
}

function markShown(key: string): void {
  try {
    localStorage.setItem(key, "1");
  } catch {
    // 覚えられなくても案内は出せている
  }
}

export default function RecoveryCodePrompt() {
  const selfMode = isSelfAuth();
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [codes, setCodes] = useState<string[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!selfMode) return;
    const token = currentAccessToken();
    const claims = token ? readClaims(token) : null;
    if (!claims) return;
    const key = recoveryPromptKey(claims.sub, claims.sid);
    if (alreadyShown(key)) return;
    let cancelled = false;
    void (async () => {
      try {
        const res = await api.get<{ remaining: number }>("/auth/recovery-codes/status");
        if (cancelled || res.remaining > 0) return;
        markShown(key);
        setOpen(true);
      } catch {
        // 案内は補助。取れなければ出さない
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selfMode]);

  if (!selfMode) return null;

  const create = async () => {
    if (busy) return;
    setBusy(true);
    try {
      const res = await api.post<{ codes: string[] }>("/auth/recovery-codes", {});
      setCodes(res.codes);
    } catch {
      // 作れなかったときは閉じずに、もう一度押せるようにする
    } finally {
      setBusy(false);
    }
  };

  const copy = async () => {
    if (!codes) return;
    try {
      await navigator.clipboard.writeText(codes.join("\n"));
      setCopied(true);
    } catch {
      // コピーできなくても、画面の10個を書き留められる
    }
  };

  const close = () => {
    setOpen(false);
    setCodes(null);
    setCopied(false);
  };

  return (
    <Modal
      open={open}
      size="sm"
      title={t(codes ? "accountSettings.recoveryCodes.shownTitle" : "accountSettings.recoveryCodes.promptTitle")}
      onClose={close}
      footer={
        codes ? (
          <>
            <Button variant="secondary" onClick={() => void copy()}>
              {t(copied ? "accountSettings.recoveryCodes.copied" : "accountSettings.recoveryCodes.copy")}
            </Button>
            <Button variant="primary" onClick={close}>
              {t("common.close")}
            </Button>
          </>
        ) : (
          <>
            <Button variant="secondary" disabled={busy} onClick={close}>
              {t("accountSettings.recoveryCodes.promptLater")}
            </Button>
            <Button variant="primary" loading={busy} disabled={busy} onClick={() => void create()}>
              {t("accountSettings.recoveryCodes.promptCreate")}
            </Button>
          </>
        )
      }
    >
      {codes ? (
        <Stack gap="3">
          <p>{t("accountSettings.recoveryCodes.shownBody")}</p>
          <ul>
            {codes.map((code) => (
              <li key={code}>{code}</li>
            ))}
          </ul>
        </Stack>
      ) : (
        <p>{t("accountSettings.recoveryCodes.promptBody")}</p>
      )}
    </Modal>
  );
}
