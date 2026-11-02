/**
 * SupplierEditPage — 仕入先フルページ編集（/suppliers/:id/edit）
 *
 * Drawer 内「フルページで開く↗」から遷移するフルページ版。
 * SupplierFormFields を共有し、同一フォームで編集・保存できる。
 * 保存後は /suppliers 一覧へ戻る。
 */

import { LoadingBlock } from "../../components/loading";
import { useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { PageLayout } from "../../components/PageLayout";
import { Button } from "../../components/Button";
import { api } from "../../lib/api";
import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";
import { useSeededForm } from "../../lib/query/useSeededForm";
import { SupplierFormFields, type SupplierFormState } from "./SupplierFormFields";

const emptyForm: SupplierFormState = {
  name: "", contact_name: "", email: "", phone: "", address: "", notes: "",
};

type SupplierDetail = {
  id: number; name: string; contact_name: string | null; email: string | null;
  phone: string | null; address: string | null; notes: string | null;
};

const formFromSupplier = (s: SupplierDetail): SupplierFormState => ({
  name: s.name,
  contact_name: s.contact_name ?? "",
  email: s.email ?? "",
  phone: s.phone ?? "",
  address: s.address ?? "",
  notes: s.notes ?? "",
});

export default function SupplierEditPage() {
  const { t }        = useTranslation();
  const { id }       = useParams<{ id: string }>();
  const navigate     = useNavigate();
  const supplierQ = useApiQuery<SupplierDetail>(`/suppliers/${id}`, { enabled: id !== undefined });
  const { form, setForm, ready } = useSeededForm(`supplier/${id}`, supplierQ.data, formFromSupplier, emptyForm);
  const [error, setError] = useState("");
  const loading = supplierQ.error === null && !ready;
  const shownError = error || (supplierQ.error ? (supplierQ.error instanceof Error ? supplierQ.error.message : t("common.fetchError")) : "");
  const invalidate = useInvalidateApi();

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
      void invalidate(["suppliers", id ?? ""]);
      navigate("/suppliers");
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    }
  };

  return (
    <PageLayout navKey="nav.suppliers" subtitleKey="suppliers.subtitle">
      {shownError && <div className="error-message">{shownError}</div>}
      {loading ? (
        <LoadingBlock />
      ) : (
        <form onSubmit={handleSubmit} style={{ maxWidth: "var(--modal-max-w-md)" }}>
          <SupplierFormFields form={form} onChange={handleChange} />
          <div className="form-actions">
            <Button
              type="button"
              variant="secondary" size="md"
              onClick={() => navigate("/suppliers")}
            >
              {t("common.cancel")}
            </Button>
            <Button type="submit" variant="primary" size="md">
              {t("common.update")}
            </Button>
          </div>
        </form>
      )}
    </PageLayout>
  );
}
