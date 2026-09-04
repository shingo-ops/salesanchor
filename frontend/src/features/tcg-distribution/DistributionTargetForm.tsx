/**
 * DistributionTargetForm — 配信先の登録/編集ドロワー
 *
 * 機能:
 *   - スプレッドシートID 形式バリデーション（フロントエンド）
 *   - 保存時に GET /tcg/distribution/verify-access でアクセス確認
 *   - アクセス失敗時は保存せず共有手順を表示
 *   - 成功時は POST/PUT して onSaved() コールバックを呼ぶ
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { NAV_ICONS } from "../../constants/icons";
import type { DistributionTarget, DistributionTargetCreate, DistributionTargetUpdate } from "./distributionApi";
import { createTarget, updateTarget, verifySpreadsheetAccess } from "./distributionApi";

const SA_EMAIL = "salesanchor-drive@sales-ops-with-claude.iam.gserviceaccount.com";

/** スプレッドシートID の形式を検証（20文字以上の英数字・ハイフン・アンダースコア） */
function isValidSpreadsheetId(id: string): boolean {
  return /^[a-zA-Z0-9_-]{20,}$/.test(id.trim());
}

interface FormValues {
  name: string;
  spreadsheet_id: string;
  sheet_name: string;
  is_active: boolean;
  sa_key_secret_name: string;
}

interface Props {
  /** 編集対象。null なら新規登録 */
  target: DistributionTarget | null;
  onClose: () => void;
  onSaved: () => void;
}

export function DistributionTargetForm({ target, onClose, onSaved }: Props) {
  const { t } = useTranslation();
  const isEdit = target !== null;

  const [values, setValues] = useState<FormValues>({
    name: target?.name ?? "",
    spreadsheet_id: target?.spreadsheet_id ?? "",
    sheet_name: target?.sheet_name ?? "",
    is_active: target?.is_active ?? true,
    sa_key_secret_name: target?.sa_key_secret_name ?? "TCG_SHEETS_SA_KEY_FILE",
  });

  const [errors, setErrors] = useState<Partial<Record<keyof FormValues, string>>>({});
  const [accessError, setAccessError] = useState("");
  const [saving, setSaving] = useState(false);
  const [copied, setCopied] = useState(false);

  const set = (key: keyof FormValues, value: string | boolean) => {
    setValues((v) => ({ ...v, [key]: value }));
    setErrors((e) => ({ ...e, [key]: undefined }));
    if (key === "spreadsheet_id") setAccessError("");
  };

  const validate = (): boolean => {
    const e: Partial<Record<keyof FormValues, string>> = {};
    if (!values.name.trim()) e.name = t("distributionTarget.form.errorRequired");
    if (!values.spreadsheet_id.trim()) {
      e.spreadsheet_id = t("distributionTarget.form.errorRequired");
    } else if (!isValidSpreadsheetId(values.spreadsheet_id)) {
      e.spreadsheet_id = t("distributionTarget.form.errorSpreadsheetIdFormat");
    }
    if (!values.sheet_name.trim()) e.sheet_name = t("distributionTarget.form.errorRequired");
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSave = async () => {
    if (!validate()) return;
    setSaving(true);
    setAccessError("");

    // 保存前にシートアクセスを確認
    try {
      const verify = await verifySpreadsheetAccess(values.spreadsheet_id.trim());
      if (!verify.accessible) {
        setAccessError(verify.error ?? t("distributionTarget.form.accessErrorGeneric"));
        setSaving(false);
        return;
      }
    } catch (e: unknown) {
      setAccessError(e instanceof Error ? e.message : String(e));
      setSaving(false);
      return;
    }

    // アクセス確認OK → 登録/更新
    try {
      if (isEdit) {
        const data: DistributionTargetUpdate = {
          name: values.name.trim(),
          spreadsheet_id: values.spreadsheet_id.trim(),
          sheet_name: values.sheet_name.trim(),
          is_active: values.is_active,
          sa_key_secret_name: values.sa_key_secret_name.trim() || "TCG_SHEETS_SA_KEY_FILE",
        };
        await updateTarget(target.id, data);
      } else {
        const data: DistributionTargetCreate = {
          name: values.name.trim(),
          spreadsheet_id: values.spreadsheet_id.trim(),
          sheet_name: values.sheet_name.trim(),
          is_active: values.is_active,
          sa_key_secret_name: values.sa_key_secret_name.trim() || "TCG_SHEETS_SA_KEY_FILE",
        };
        await createTarget(data);
      }
      onSaved();
    } catch (e: unknown) {
      setAccessError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(SA_EMAIL).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <>
      <div className="dist-drawer-backdrop" onClick={onClose} />
      <aside className="dist-drawer" aria-label={isEdit ? t("distributionTarget.form.titleEdit") : t("distributionTarget.form.titleNew")}>
        <div className="dist-drawer-header">
          <h3>{isEdit ? t("distributionTarget.form.titleEdit") : t("distributionTarget.form.titleNew")}</h3>
          <button
            type="button"
            className="dist-drawer-close"
            onClick={onClose}
            aria-label={t("common.close")}
          >
            <NAV_ICONS.close size={20} aria-hidden="true" />
          </button>
        </div>

        <div className="dist-drawer-body">
          {/* サービスアカウント共有案内 */}
          <div className="dist-sa-notice">
            <div className="dist-sa-notice-label">
              {t("distributionTarget.form.saNoticeLabel")}
            </div>
            <div className="dist-sa-notice-body">
              {t("distributionTarget.form.saNoticeBody")}
            </div>
            <div className="dist-sa-email-row">
              <span className="dist-sa-email">{SA_EMAIL}</span>
              <button
                type="button"
                className="dist-btn dist-btn--ghost"
                style={{ fontSize: "var(--font-xs)", padding: "2px var(--space-2)" }}
                onClick={handleCopy}
              >
                {copied ? t("distributionTarget.form.copied") : t("distributionTarget.form.copy")}
              </button>
            </div>
          </div>

          {/* アクセスエラー表示 */}
          {accessError && (
            <div className="dist-access-error">
              <div>{t("distributionTarget.form.accessErrorTitle")}</div>
              <div className="dist-access-error-detail">{accessError}</div>
              <div>{t("distributionTarget.form.saNoticeBody")}</div>
            </div>
          )}

          {/* クライアント名 */}
          <div className="dist-field">
            <label htmlFor="dist-name">
              {t("distributionTarget.form.name")}
              <span style={{ color: "var(--color-error)", marginLeft: "2px" }}>*</span>
            </label>
            <input
              id="dist-name"
              className={`dist-input${errors.name ? " dist-input--error" : ""}`}
              type="text"
              value={values.name}
              onChange={(e) => set("name", e.target.value)}
              placeholder={t("distributionTarget.form.namePlaceholder")}
            />
            {errors.name && <span className="dist-field-error">{errors.name}</span>}
          </div>

          {/* スプレッドシートID */}
          <div className="dist-field">
            <label htmlFor="dist-spreadsheet-id">
              {t("distributionTarget.form.spreadsheetId")}
              <span style={{ color: "var(--color-error)", marginLeft: "2px" }}>*</span>
            </label>
            <input
              id="dist-spreadsheet-id"
              className={`dist-input${errors.spreadsheet_id ? " dist-input--error" : ""}`}
              type="text"
              value={values.spreadsheet_id}
              onChange={(e) => set("spreadsheet_id", e.target.value)}
              placeholder={t("distributionTarget.form.spreadsheetIdPlaceholder")}
              autoComplete="off"
              spellCheck={false}
            />
            <span className="dist-field-hint">
              {t("distributionTarget.form.spreadsheetIdHint")}
            </span>
            {errors.spreadsheet_id && (
              <span className="dist-field-error">{errors.spreadsheet_id}</span>
            )}
          </div>

          {/* タブ名 */}
          <div className="dist-field">
            <label htmlFor="dist-sheet-name">
              {t("distributionTarget.form.sheetName")}
              <span style={{ color: "var(--color-error)", marginLeft: "2px" }}>*</span>
            </label>
            <input
              id="dist-sheet-name"
              className={`dist-input${errors.sheet_name ? " dist-input--error" : ""}`}
              type="text"
              value={values.sheet_name}
              onChange={(e) => set("sheet_name", e.target.value)}
              placeholder={t("distributionTarget.form.sheetNamePlaceholder")}
            />
            {errors.sheet_name && (
              <span className="dist-field-error">{errors.sheet_name}</span>
            )}
          </div>

          {/* 有効フラグ */}
          <label className="dist-checkbox-row">
            <input
              type="checkbox"
              checked={values.is_active}
              onChange={(e) => set("is_active", e.target.checked)}
            />
            {t("distributionTarget.form.isActive")}
          </label>
        </div>

        <div className="dist-drawer-footer">
          <button type="button" className="dist-btn dist-btn--ghost" onClick={onClose}>
            {t("common.cancel")}
          </button>
          <button
            type="button"
            className="dist-btn dist-btn--primary"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? t("common.saving") : t("common.save")}
          </button>
        </div>
      </aside>
    </>
  );
}
