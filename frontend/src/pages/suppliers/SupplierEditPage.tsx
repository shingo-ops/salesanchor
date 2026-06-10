/**
 * SupplierEditPage — 仕入先フルページ編集（/suppliers/:id/edit）
 *
 * Drawer 内「フルページで開く↗」から遷移するフルページ版。
 * SupplierFormFields を共有し、同一フォームで編集・保存できる。
 * 保存後は /suppliers 一覧へ戻る。
 */

import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { PageLayout } from "../../components/PageLayout";
import { api } from "../../lib/api";
import { SupplierFormFields, type SupplierFormState } from "./SupplierFormFields";

const emptyForm: SupplierFormState = {
  name: "", contact_name: "", email: "", phone: "", address: "", notes: "",
};

export default function SupplierEditPage() {
  const { t }        = useTranslation();
  const { id }       = useParams<{ id: string }>();
  const navigate     = useNavigate();
  const [form, setForm] = useState<SupplierFormState>(emptyForm);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  /* 既存データ取得 */
  useEffect(() => {
    if (!id) return;
    api.get<{ id: number; name: string; contact_name: string | null; email: string | null; phone: string | null; address: string | null; notes: string | null }>(`/suppliers/${id}`)
      .then(s => {
        setForm({
          name: s.name,
          contact_name: s.contact_name ?? "",
          email: s.email ?? "",
          phone: s.phone ?? "",
          address: s.address ?? "",
          notes: s.notes ?? "",
        });
      })
      .catch(e => setError(e instanceof Error ? e.message : t("common.fetchError")))
      .finally(() => setLoading(false));
  }, [id, t]);

  const handleChange = (field: keyof SupplierFormState, value: string) => {
    setForm(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    const toNull = (v: string) => v || null;
    const payload = {
      name: form.name,
      contact_name: toNull(form.contact_name),
      email: toNull(form.email),
      phone: toNull(form.phone),
      address: toNull(form.address),
      notes: toNull(form.notes),
    };
    try {
      await api.patch(`/suppliers/${id}`, payload);
      navigate("/suppliers");
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    }
  };

  return (
    <PageLayout navKey="nav.suppliers" subtitleKey="suppliers.subtitle">
      {error && <div className="error-message">{error}</div>}
      {loading ? (
        <div className="loading">{t("common.loading")}</div>
      ) : (
        <form onSubmit={handleSubmit} style={{ maxWidth: "var(--modal-max-w-md)" }}>
          <SupplierFormFields form={form} onChange={handleChange} />
          <div className="form-actions">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => navigate("/suppliers")}
            >
              {t("common.cancel")}
            </button>
            <button type="submit" className="btn-primary">
              {t("common.update")}
            </button>
          </div>
        </form>
      )}
    </PageLayout>
  );
}
