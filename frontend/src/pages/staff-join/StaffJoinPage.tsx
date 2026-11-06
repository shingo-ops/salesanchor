import { useEffect, useState, FormEvent } from "react";
import { useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { PageLayout } from "../../components/PageLayout";
import { Button } from "../../components/Button";
import { ButtonLink } from "../../components/ButtonLink";
import { Callout } from "../../components/Callout";
import { LoadingBlock } from "../../components/loading";
import { TextFieldControl } from "../../components/TextField";
import {
  StaffIdentityFields,
  emptyStaffIdentity,
  type StaffIdentityState,
} from "../staff/StaffIdentityFields";

/**
 * スタッフ自己登録の申込ページ（ADR-1068・設計 §3-5）。管理者が手で送った
 * `/staff-join#k=<鍵>` から来る。ログイン不要。鍵は # の後ろにあるので、サーバーのログや Referer に残らない。
 * 送ると「登録待ち」で作られ、登録番号（この1回だけ）と Discord の参加リンクを出す。
 */

interface JoinInfo {
  tenant_name: string;
  role_name: string | null;
  expires_at: string;
}

interface Submitted {
  registration_code: string;
  discord_invite_url: string | null;
}

type Phase = "loading" | "invalid" | "ready" | "done";

const API = "/api/v1/public/staff-join";

export default function StaffJoinPage() {
  const { t } = useTranslation();
  const { hash } = useLocation();
  const key = new URLSearchParams(hash.replace(/^#/, "")).get("k") ?? "";

  const [phase, setPhase] = useState<Phase>(key ? "loading" : "invalid");
  const [info, setInfo] = useState<JoinInfo | null>(null);
  const [form, setForm] = useState<StaffIdentityState>(emptyStaffIdentity);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState<Submitted | null>(null);
  const [copied, setCopied] = useState(false);
  const [copyFailed, setCopyFailed] = useState(false);

  useEffect(() => {
    if (!key) {
      setPhase("invalid");
      return;
    }
    let cancelled = false;
    setPhase("loading");
    fetch(`${API}/${encodeURIComponent(key)}`)
      .then(async (res) => {
        if (!res.ok) throw new Error(String(res.status));
        return (await res.json()) as JoinInfo;
      })
      .then((data) => {
        if (cancelled) return;
        setInfo(data);
        setPhase("ready");
      })
      .catch(() => {
        if (!cancelled) setPhase("invalid");
      });
    return () => {
      cancelled = true;
    };
  }, [key]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (saving) return;
    setError("");
    setSaving(true);
    try {
      const res = await fetch(`${API}/${encodeURIComponent(key)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          surname_jp: form.surname_jp,
          given_name_jp: form.given_name_jp,
          surname_kana: form.surname_kana || null,
          given_name_kana: form.given_name_kana || null,
          surname_en: form.surname_en,
          given_name_en: form.given_name_en,
          primary_email: form.primary_email,
        }),
      });
      if (res.ok) {
        setResult((await res.json()) as Submitted);
        setPhase("done");
        return;
      }
      if (res.status === 404) {
        setPhase("invalid");
        return;
      }
      if (res.status === 409) {
        const body = (await res.json().catch(() => null)) as { detail?: unknown } | null;
        setError(typeof body?.detail === "string" ? body.detail : t("staffJoin.submitError"));
      } else if (res.status === 403) {
        setError(t("staffJoin.contactAdmin"));
      } else if (res.status === 429) {
        setError(t("staffJoin.tooMany"));
      } else {
        setError(t("staffJoin.submitError"));
      }
    } catch {
      setError(t("staffJoin.submitError"));
    } finally {
      setSaving(false);
    }
  };

  const copyCode = () => {
    if (!result) return;
    setCopyFailed(false);
    navigator.clipboard.writeText(result.registration_code).then(
      () => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      },
      () => setCopyFailed(true),
    );
  };

  return (
    <PageLayout titleText={t("staffJoin.title")} subtitleKey="staffJoin.subtitle">
      {phase === "loading" && <LoadingBlock />}

      {phase === "invalid" && (
        <Callout variant="warning" title={t("staffJoin.invalidTitle")}>
          {t("staffJoin.invalidBody")}
        </Callout>
      )}

      {phase === "ready" && info && (
        <form onSubmit={handleSubmit}>
          <p>{t("staffJoin.company", { name: info.tenant_name })}</p>
          <p>{t("staffJoin.role", { name: info.role_name ?? "-" })}</p>
          <p>{t("staffJoin.expires", { date: new Date(info.expires_at).toLocaleString() })}</p>
          <StaffIdentityFields
            form={form}
            onChange={(field, value) => setForm((prev) => ({ ...prev, [field]: value }))}
          />
          {error && (
            <Callout variant="warning" title={t("staffJoin.errorTitle")}>
              {error}
            </Callout>
          )}
          <Button loading={saving} variant="primary" size="md" type="submit" disabled={saving}>
            {t("staffJoin.submit")}
          </Button>
        </form>
      )}

      {phase === "done" && result && (
        <>
          <Callout variant="info" title={t("staffJoin.doneTitle")}>
            {t("staffJoin.doneBody")}
          </Callout>
          <div className="form-group">
            <label htmlFor="staff_join_reg_code">{t("staffJoin.codeLabel")}</label>
            <div className="actions">
              <TextFieldControl id="staff_join_reg_code" readOnly value={result.registration_code} />
              <Button type="button" variant="secondary" size="sm" onClick={copyCode}>
                {copied ? t("staffJoin.copied") : t("staffJoin.copy")}
              </Button>
            </div>
            {copyFailed && <div className="error-message">{t("staffJoin.copyFailed")}</div>}
            <p>{t("staffJoin.codeOnce")}</p>
          </div>
          {result.discord_invite_url ? (
            <ButtonLink href={result.discord_invite_url} variant="primary" target="_blank" rel="noopener noreferrer">
              {t("staffJoin.discordJoin")}
            </ButtonLink>
          ) : (
            <Callout variant="info" title={t("staffJoin.discordLater")}>
              {t("staffJoin.discordLaterBody")}
            </Callout>
          )}
          <ol>
            <li>{t("staffJoin.step1")}</li>
            <li>{t("staffJoin.step2")}</li>
            <li>{t("staffJoin.step3")}</li>
          </ol>
        </>
      )}
    </PageLayout>
  );
}
