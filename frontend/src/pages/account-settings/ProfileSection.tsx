import { useState, FormEvent, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { AvatarUpload } from "../../components/AvatarUpload";
import { api } from "../../lib/api";
import {
  avatarErrorKind,
  deleteMyAvatar,
  hasEnglishNames,
  patchMyProfile,
  toSameOriginAvatarUrl,
  uploadMyAvatar,
} from "../../lib/staffProfile";
import type { AvatarErrorKind } from "../../lib/staffProfile";
import { useUiPrefs } from "../../contexts/UiPrefsContext";
import { ACCOUNT_ICONS } from "../../constants/icons";
import { ICON } from "../../constants/iconSizes";
import { TextFieldControl } from "../../components/TextField";

interface StaffMe {
  surname_jp: string;
  given_name_jp: string;
  surname_kana: string | null;
  given_name_kana: string | null;
  surname_en: string | null;
  given_name_en: string | null;
  primary_email: string;
  phone: string | null;
  avatar_url: string | null;
}

interface AvatarFailure {
  kind: AvatarErrorKind;
  /** 保存失敗時の「もう一度試す」の動作（同じ操作をやり直す） */
  retry: () => void;
}

export default function ProfileSection() {
  const { t } = useTranslation();
  const { refresh } = useUiPrefs();
  const [form, setForm] = useState({
    surname_jp: "", given_name_jp: "",
    surname_kana: "", given_name_kana: "",
    surname_en: "", given_name_en: "",
    phone: "",
  });
  const [email, setEmail] = useState("");
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const [avatarUploading, setAvatarUploading] = useState(false);
  const [avatarFailure, setAvatarFailure] = useState<AvatarFailure | null>(null);

  useEffect(() => {
    api.get<StaffMe>("/staff/me").then((me) => {
      setEmail(me.primary_email);
      setAvatarUrl(me.avatar_url ?? null);
      setForm({
        surname_jp: me.surname_jp ?? "",
        given_name_jp: me.given_name_jp ?? "",
        surname_kana: me.surname_kana ?? "",
        given_name_kana: me.given_name_kana ?? "",
        surname_en: me.surname_en ?? "",
        given_name_en: me.given_name_en ?? "",
        phone: me.phone ?? "",
      });
    }).catch(() => {
      setError(t("common.fetchError"));
    });
  }, [t]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSuccess(false); setError("");
    if (!hasEnglishNames(form)) {
      setError(t("accountSettings.englishNameRequired"));
      return;
    }
    setSaving(true);
    try {
      await patchMyProfile({ ...form, phone: form.phone === "" ? null : form.phone });
      await refresh();
      setSuccess(true);
    } catch {
      setError(t("common.saveError"));
    } finally {
      setSaving(false);
    }
  };

  const uploadAvatar = async (file: File) => {
    setAvatarUploading(true); setAvatarFailure(null);
    try {
      const res = await uploadMyAvatar(file);
      setAvatarUrl(res.avatar_url);
    } catch (err) {
      setAvatarFailure({ kind: avatarErrorKind(err), retry: () => { void uploadAvatar(file); } });
    } finally {
      setAvatarUploading(false);
    }
  };

  const removeAvatar = async () => {
    setAvatarUploading(true); setAvatarFailure(null);
    try {
      await deleteMyAvatar();
      setAvatarUrl(null);
    } catch {
      setAvatarFailure({ kind: "saveFailed", retry: () => { void removeAvatar(); } });
    } finally {
      setAvatarUploading(false);
    }
  };

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((prev) => ({ ...prev, [k]: e.target.value }));

  return (
    <section className="account-settings-section">
      <div className="account-settings-section-title">
        <ACCOUNT_ICONS.profile size={ICON.md} aria-hidden="true" />
        {t("accountSettings.sectionProfile")}
      </div>

      <div className="account-settings-field">
        <span className="account-settings-label">{t("accountSettings.emailLabel")}</span>
        <span className="account-settings-readonly">{email}</span>
        <span className="account-settings-note">{t("accountSettings.emailReadOnlyNote")}</span>
      </div>

      <div className="account-settings-field">
        <span className="account-settings-label">{t("accountSettings.avatarLabel")}</span>
        <AvatarUpload
          imageUrl={toSameOriginAvatarUrl(avatarUrl)}
          uploading={avatarUploading}
          onSelect={uploadAvatar}
          onDelete={removeAvatar}
          errorMessage={
            avatarFailure
              ? t(avatarFailure.kind === "invalidImage" ? "accountSettings.avatarErrorInvalid" : "accountSettings.avatarErrorSave")
              : undefined
          }
          onErrorAction={avatarFailure?.kind === "saveFailed" ? avatarFailure.retry : undefined}
          labels={{
            choose: t("accountSettings.avatarChoose"),
            change: t("accountSettings.avatarChange"),
            remove: t("accountSettings.avatarRemove"),
            uploading: t("accountSettings.avatarUploading"),
            hint: t("accountSettings.avatarHint"),
            imageAlt: t("accountSettings.avatarAlt"),
            errorAction: t(
              avatarFailure?.kind === "saveFailed"
                ? "accountSettings.avatarErrorSaveAction"
                : "accountSettings.avatarErrorInvalidAction",
            ),
          }}
        />
      </div>

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="phone">{t("accountSettings.phoneLabel")}</label>
          <TextFieldControl id="phone" type="tel" value={form.phone} onChange={set("phone")} />
        </div>

        <div className="account-settings-row">
          <div className="form-group">
            <label htmlFor="surname_jp">{t("accountSettings.surnameJp")}</label>
            <TextFieldControl id="surname_jp" value={form.surname_jp} onChange={set("surname_jp")} />
          </div>
          <div className="form-group">
            <label htmlFor="given_name_jp">{t("accountSettings.givenNameJp")}</label>
            <TextFieldControl id="given_name_jp" value={form.given_name_jp} onChange={set("given_name_jp")} />
          </div>
        </div>

        <div className="account-settings-row">
          <div className="form-group">
            <label htmlFor="surname_kana">{t("staff.surnameKana")}</label>
            <TextFieldControl id="surname_kana" value={form.surname_kana} onChange={set("surname_kana")} />
          </div>
          <div className="form-group">
            <label htmlFor="given_name_kana">{t("staff.givenNameKana")}</label>
            <TextFieldControl id="given_name_kana" value={form.given_name_kana} onChange={set("given_name_kana")} />
          </div>
        </div>

        <div className="account-settings-row">
          <div className="form-group">
            <label htmlFor="surname_en">{t("accountSettings.surnameEn")} *</label>
            <TextFieldControl id="surname_en" aria-required="true" value={form.surname_en ?? ""} onChange={set("surname_en")} />
          </div>
          <div className="form-group">
            <label htmlFor="given_name_en">{t("accountSettings.givenNameEn")} *</label>
            <TextFieldControl id="given_name_en" aria-required="true" value={form.given_name_en ?? ""} onChange={set("given_name_en")} />
          </div>
        </div>

        <div className="account-settings-note">{t("accountSettings.englishNameHelp")}</div>

        {error && <div className="error-message">{error}</div>}
        {success && <div className="account-settings-success">{t("accountSettings.profileSaved")}</div>}

        <div className="account-settings-actions">
          <Button type="submit" variant="primary" size="md" disabled={saving}>
            {saving ? t("accountSettings.saving") : t("common.save")}
          </Button>
        </div>
      </form>
    </section>
  );
}
