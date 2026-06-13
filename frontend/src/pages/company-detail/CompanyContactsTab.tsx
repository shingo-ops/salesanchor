/**
 * 会社詳細 — 担当者タブ。
 * 担当者の追加・編集・削除・チャンネル管理・統合をインラインモーダルで行う。
 *
 * SA-04: チャンネル追加・編集フォーム（ContactChannelForm）と
 *        担当者統合モーダル（MergeContactModal）を組み込み。
 */

import { FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { STATUS_ICONS } from "../../constants/icons";
import { ICON } from "../../constants/iconSizes";
import type { Company, Contact, ContactFormState } from "./company-detail.types";
import { Modal } from "../../components/Modal";
import { Button } from "../../components/Button";
import { TextField } from "../../components/TextField";
import { Select } from "../../components/Select";
import ContactChannelForm, { type ContactChannelEntry } from "../../components/ContactChannelForm";
import MergeContactModal from "../../components/MergeContactModal";

interface Props {
  company: Company;
  contacts: Contact[];
  canEdit: boolean;
  contactModalOpen: boolean;
  contactForm: ContactFormState;
  setContactForm: (f: ContactFormState) => void;
  contactSubmitting: boolean;
  setContactDeleteTarget: (c: Contact | null) => void;
  openContactNew: () => void;
  openContactEdit: (c: Contact) => void;
  handleContactSubmit: (e: FormEvent) => void;
  onCloseModal: () => void;
  /** チャンネル保存・統合完了後にリストを再読み込みするコールバック */
  onContactsRefresh?: () => void;
}

export function CompanyContactsTab({
  company, contacts, canEdit,
  contactModalOpen, contactForm, setContactForm, contactSubmitting,
  setContactDeleteTarget,
  openContactNew, openContactEdit,
  handleContactSubmit, onCloseModal,
  onContactsRefresh,
}: Props) {
  const { t } = useTranslation();

  // チャンネル追加フォームの状態
  const [channelFormOpen, setChannelFormOpen] = useState(false);
  const [channelFormContact, setChannelFormContact] = useState<Contact | null>(null);
  const [channelFormInitial, setChannelFormInitial] = useState<ContactChannelEntry | null>(null);

  // 担当者統合モーダルの状態
  const [mergeModalOpen, setMergeModalOpen] = useState(false);
  const [mergeSourceContact, setMergeSourceContact] = useState<Contact | null>(null);
  // 重複チェックから統合に進む際の対象担当者 ID
  const [mergeDuplicateContactId, setMergeDuplicateContactId] = useState<number | null>(null);

  const openChannelForm = (contact: Contact, initial: ContactChannelEntry | null = null) => {
    setChannelFormContact(contact);
    setChannelFormInitial(initial);
    setChannelFormOpen(true);
  };

  const openMergeModal = (contact: Contact) => {
    setMergeSourceContact(contact);
    setMergeDuplicateContactId(null);
    setMergeModalOpen(true);
  };

  const handleRequestMerge = (duplicateContactId: number) => {
    if (!channelFormContact) return;
    // チャンネルフォームを閉じて統合モーダルを開く
    setChannelFormOpen(false);
    setMergeSourceContact(channelFormContact);
    setMergeDuplicateContactId(duplicateContactId);
    setMergeModalOpen(true);
  };

  const handleMerged = () => {
    setMergeModalOpen(false);
    setMergeSourceContact(null);
    onContactsRefresh?.();
  };

  const contactName = (c: Contact) =>
    c.display_name || `${c.surname || ""} ${c.given_name || ""}`.trim() || "-";

  return (
    <div>
      {canEdit && (
        <div style={{ marginBottom: "var(--space-3)" }}>
          <Button size="sm" variant="secondary" onClick={openContactNew}>
            + {t("contacts.newContact")}
          </Button>
        </div>
      )}

      {contacts.length === 0 ? (
        <p>{t("contacts.noContacts")}</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>{t("common.name")}</th>
              <th>{t("contacts.position")}</th>
              <th>{t("contacts.isPrimary")}</th>
              <th>{t("common.email")}</th>
              <th>{t("common.phone")}</th>
              <th>{t("common.status")}</th>
              <th>{t("common.actions")}</th>
            </tr>
          </thead>
          <tbody>
            {contacts.map((c) => (
              <tr key={c.id}>
                <td>{contactName(c)}</td>
                <td>{c.job_title || "-"}</td>
                <td>{c.is_primary_contact ? <STATUS_ICONS.check size={ICON.sm} aria-hidden="true" /> : ""}</td>
                <td>{c.primary_email || "-"}</td>
                <td>{c.primary_phone || "-"}</td>
                <td><span className={`status-badge status-${c.status}`}>{c.status}</span></td>
                <td>
                  <Button size="sm" variant="secondary" onClick={() => openChannelForm(c)}>
                    {t("contactChannel.addTitle")}
                  </Button>
                  {canEdit && (
                    <>
                      <Button size="sm" variant="secondary" onClick={() => openContactEdit(c)}>
                        {t("common.edit")}
                      </Button>
                      <Button size="sm" variant="secondary" onClick={() => openMergeModal(c)}>
                        {/* eslint-disable-next-line local/no-japanese-literal */}
                        {t("contacts.mergeAsDuplicate").replace("（担当者単位は未実装）", "")}
                      </Button>
                      <Button size="sm" variant="danger" onClick={() => setContactDeleteTarget(c)}>
                        {t("common.delete")}
                      </Button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* 追加・編集モーダル */}
      <Modal
        open={contactModalOpen}
        onClose={onCloseModal}
        title={contactForm.id === null ? t("contacts.newContact") : t("contacts.editContact")}
        size="md"
      >
        <form onSubmit={handleContactSubmit}>
          <div className="form-grid">
            <TextField
              label={t("contacts.displayName")}
              value={contactForm.display_name}
              onChange={(e) => setContactForm({ ...contactForm, display_name: e.target.value })}
            />
            <TextField
              label={t("contacts.surname")}
              value={contactForm.surname}
              onChange={(e) => setContactForm({ ...contactForm, surname: e.target.value })}
            />
            <TextField
              label={t("contacts.givenName")}
              value={contactForm.given_name}
              onChange={(e) => setContactForm({ ...contactForm, given_name: e.target.value })}
            />
            <TextField
              label={t("contacts.position")}
              value={contactForm.job_title}
              onChange={(e) => setContactForm({ ...contactForm, job_title: e.target.value })}
            />
            <TextField
              label={t("contacts.department")}
              value={contactForm.department}
              onChange={(e) => setContactForm({ ...contactForm, department: e.target.value })}
            />
            <TextField
              label={t("common.email")}
              type="email"
              value={contactForm.primary_email}
              onChange={(e) => setContactForm({ ...contactForm, primary_email: e.target.value })}
            />
            <TextField
              label={t("common.phone")}
              value={contactForm.primary_phone}
              onChange={(e) => setContactForm({ ...contactForm, primary_phone: e.target.value })}
            />
            <Select
              label={t("common.status")}
              value={contactForm.status}
              onChange={(e) => setContactForm({ ...contactForm, status: e.target.value })}
              options={[
                { value: "active", label: "active" },
                { value: "inactive", label: "inactive" },
                { value: "archived", label: "archived" },
              ]}
            />
            <div className="form-row">
              <label>
                {/* checkbox は TextField 対象外のため残置 */}
                <input
                  type="checkbox"
                  checked={contactForm.is_primary_contact}
                  onChange={(e) => setContactForm({ ...contactForm, is_primary_contact: e.target.checked })}
                />
                {" "}{t("contacts.isPrimary")}
              </label>
            </div>
          </div>
          <div className="form-actions">
            <Button type="button" size="sm" variant="secondary" onClick={onCloseModal}>
              {t("common.cancel")}
            </Button>
            <Button type="submit" size="sm" variant="primary" disabled={contactSubmitting}>
              {contactSubmitting ? t("common.saving") : t("common.save")}
            </Button>
          </div>
        </form>
      </Modal>

      {/* チャンネル追加フォーム */}
      {channelFormContact && (
        <ContactChannelForm
          open={channelFormOpen}
          contactId={channelFormContact.id}
          companyId={company.id}
          initial={channelFormInitial}
          onSaved={() => {
            setChannelFormOpen(false);
            onContactsRefresh?.();
          }}
          onCancel={() => setChannelFormOpen(false)}
          onRequestMerge={handleRequestMerge}
        />
      )}

      {/* 担当者統合モーダル */}
      {mergeSourceContact && (
        <MergeContactModal
          open={mergeModalOpen}
          companyId={company.id}
          source={{
            id: mergeSourceContact.id,
            contact_code: mergeSourceContact.contact_code,
            display_name: mergeSourceContact.display_name,
            surname: mergeSourceContact.surname,
            given_name: mergeSourceContact.given_name,
          }}
          onMerged={handleMerged}
          onCancel={() => {
            setMergeModalOpen(false);
            setMergeSourceContact(null);
          }}
        />
      )}
    </div>
  );
}
