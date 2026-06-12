/**
 * 会社詳細ページ（Phase 1-B-2 Step 5c-2）。
 *
 * URL: /companies/:id
 * 5 タブ: 基本情報 / 住所（multi_branch）/ 担当者 / 販売チャネル / Discord
 *
 * このファイルはオーケストレーターのみ。ロジックは useCompanyDetail、
 * UI は各タブコンポーネントに分割済み。
 */

import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { usePermissions } from "../../hooks/usePermissions";
import { api } from "../../lib/api";
import ConfirmModal from "../../components/ConfirmModal";
import MergeCompanyModal from "../../components/MergeCompanyModal";
import { useCompanyDetail } from "./useCompanyDetail";
import { CompanyBasicTab } from "./CompanyBasicTab";
import { CompanyAddressesTab } from "./CompanyAddressesTab";
import { CompanyContactsTab } from "./CompanyContactsTab";
import { CompanyChannelsTab } from "./CompanyChannelsTab";
import { CompanyDiscordTab } from "./CompanyDiscordTab";
import { CompanyConvLogsTab } from "./CompanyConvLogsTab";
import { CompanyAddressModal } from "./CompanyAddressModal";
import { typeLabel } from "./company-detail.types";

export default function CompanyDetailPage() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { hasPermission } = usePermissions();
  const canEdit = hasPermission("customers.update");
  // A-4: 会社マージは customers.delete 権限相当
  const canMerge = hasPermission("customers.delete");
  // ADR-SA-03 + ADR-127: 登録リンク発行（register / add_address / change_billing）
  const [regLinkUrl, setRegLinkUrl] = useState<string | null>(null);
  const [regLinkLoading, setRegLinkLoading] = useState(false);
  const [addrLinkUrl, setAddrLinkUrl] = useState<string | null>(null);
  const [addrLinkLoading, setAddrLinkLoading] = useState(false);
  const [changeBillingLinkUrl, setChangeBillingLinkUrl] = useState<string | null>(null);
  const [changeBillingLinkLoading, setChangeBillingLinkLoading] = useState(false);

  const state = useCompanyDetail(id);
  const {
    company, contacts, loading, error,
    activeTab, setActiveTab,
    basicForm, setBasicForm, basicDirty, setBasicDirty, basicSubmitting,
    channelsText, setChannelsText, channelsDirty, setChannelsDirty, channelsSubmitting,
    addrModalOpen, setAddrModalOpen,
    addrForm, setAddrForm,
    addrDeleteTarget, setAddrDeleteTarget,
    contactModalOpen, setContactModalOpen,
    contactForm, setContactForm, contactSubmitting,
    contactDeleteTarget, setContactDeleteTarget,
    discordForm, setDiscordForm, discordDirty, setDiscordDirty, discordSubmitting,
    dedupConfirmOpen, setDedupConfirmOpen, dedupSubmitting,
    mergeModalOpen, setMergeModalOpen,
    handleBasicSubmit, handleChannelsSubmit,
    submitAddresses,
    openAddressNew, openAddressEdit,
    handleAddressTypeChange,
    openContactNew, openContactEdit,
    handleContactSubmit, handleContactDelete,
    handleDiscordSubmit, handleDiscordDelete,
    handleResolveAsDistinct, handleAddressDelete,
    load,
  } = state;

  if (loading) return <div className="page-container"><p>{t("common.loading")}</p></div>;
  if (!company) {
    return (
      <div className="page-container">
        <p>{t("common.noData")}</p>
        <button onClick={() => navigate("/companies")}>{t("common.back")}</button>
      </div>
    );
  }

  const handleGenerateRegLink = async () => {
    if (!company.lead_id) return;
    setRegLinkLoading(true);
    try {
      const res = await api.post("/registration-tokens", {
        lead_id: company.lead_id,
        type: "register",
      }) as { registration_url: string };
      setRegLinkUrl(res.registration_url);
    } catch {
      // noop
    } finally {
      setRegLinkLoading(false);
    }
  };

  const handleGenerateAddrLink = async () => {
    if (!company.lead_id) return;
    setAddrLinkLoading(true);
    try {
      const res = await api.post("/registration-tokens", {
        lead_id: company.lead_id,
        type: "add_address",
      }) as { registration_url: string };
      setAddrLinkUrl(res.registration_url);
    } catch {
      // noop
    } finally {
      setAddrLinkLoading(false);
    }
  };

  const handleGenerateChangeBillingLink = async () => {
    if (!company.lead_id) return;
    setChangeBillingLinkLoading(true);
    try {
      const res = await api.post("/registration-tokens", {
        lead_id: company.lead_id,
        type: "change_billing",
      }) as { registration_url: string };
      setChangeBillingLinkUrl(res.registration_url);
    } catch {
      // noop
    } finally {
      setChangeBillingLinkLoading(false);
    }
  };

  const billingAddresses = company.addresses.filter((a) => a.address_type === "billing");
  const deliveryAddresses = company.addresses.filter((a) => a.address_type === "delivery");
  // ADR-127 §4: 第1層ゲート — 登録済み（billing is_default=true が存在）なら register 発行を無効化
  const isAlreadyRegistered = billingAddresses.some((a) => a.is_default);

  const switchTab = (tab: typeof activeTab) => {
    if ((basicDirty || channelsDirty) && tab !== activeTab) {
      if (!window.confirm(t("companies.unsavedChangesConfirm"))) return;
      setBasicForm(state.basicForm ? { ...state.basicForm } : null);
      setChannelsText(company.sales_channels.join(", "));
      setBasicDirty(false);
      setChannelsDirty(false);
    }
    setActiveTab(tab);
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <button className="btn-sm" onClick={() => navigate("/companies")}>&larr; {t("common.back")}</button>
          <h1>{company.name}</h1>
        </div>
        <div className="page-header-actions">
          {canEdit && company.lead_id && (
            <>
              <button
                className="btn-sm btn-primary"
                onClick={handleGenerateRegLink}
                disabled={regLinkLoading || isAlreadyRegistered}
                title={isAlreadyRegistered ? t("registration.alreadyRegisteredGate") : undefined}
              >
                {regLinkLoading ? t("common.loading") : isAlreadyRegistered ? t("registration.registeredLabel") : t("registration.generateLink")}
              </button>
              {isAlreadyRegistered && (
                <>
                  <button
                    className="btn-sm"
                    onClick={handleGenerateAddrLink}
                    disabled={addrLinkLoading}
                  >
                    {addrLinkLoading ? t("common.loading") : t("registration.generateAddressLink")}
                  </button>
                  <button
                    className="btn-sm"
                    onClick={handleGenerateChangeBillingLink}
                    disabled={changeBillingLinkLoading}
                  >
                    {changeBillingLinkLoading ? t("common.loading") : t("registration.generateChangeBillingLink")}
                  </button>
                </>
              )}
            </>
          )}
          <span className={`status-badge status-${company.status}`}>{company.status}</span>
        </div>
      </div>

      {regLinkUrl && (
        <div className="info-banner" style={{ marginBottom: "var(--spacing-4)", wordBreak: "break-all" }}>
          {t("registration.linkGenerated")}: <a href={regLinkUrl} target="_blank" rel="noopener noreferrer">{regLinkUrl}</a>
          <button className="btn-sm" style={{ marginLeft: "var(--spacing-2)" }}
            onClick={() => { navigator.clipboard.writeText(regLinkUrl); }}>
            {t("registration.copyLink")}
          </button>
        </div>
      )}
      {addrLinkUrl && (
        <div className="info-banner" style={{ marginBottom: "var(--spacing-4)", wordBreak: "break-all" }}>
          {t("registration.addressLinkGenerated")}: <a href={addrLinkUrl} target="_blank" rel="noopener noreferrer">{addrLinkUrl}</a>
          <button className="btn-sm" style={{ marginLeft: "var(--spacing-2)" }}
            onClick={() => { navigator.clipboard.writeText(addrLinkUrl); }}>
            {t("registration.copyLink")}
          </button>
        </div>
      )}
      {changeBillingLinkUrl && (
        <div className="info-banner" style={{ marginBottom: "var(--spacing-4)", wordBreak: "break-all" }}>
          {t("registration.changeBillingLinkGenerated")}: <a href={changeBillingLinkUrl} target="_blank" rel="noopener noreferrer">{changeBillingLinkUrl}</a>
          <button className="btn-sm" style={{ marginLeft: "var(--spacing-2)" }}
            onClick={() => { navigator.clipboard.writeText(changeBillingLinkUrl); }}>
            {t("registration.copyLink")}
          </button>
        </div>
      )}

      {error && <div className="error-banner">{error}</div>}

      <div className="tabs">
        <button className={`tab ${activeTab === "basic" ? "active" : ""}`} onClick={() => switchTab("basic")}>
          {t("companies.basicInfo")}
        </button>
        <button className={`tab ${activeTab === "addresses" ? "active" : ""}`} onClick={() => switchTab("addresses")}>
          {t("companies.address")} ({company.addresses.length})
        </button>
        <button className={`tab ${activeTab === "contacts" ? "active" : ""}`} onClick={() => switchTab("contacts")}>
          {t("contacts.title")} ({contacts.length})
        </button>
        <button className={`tab ${activeTab === "channels" ? "active" : ""}`} onClick={() => switchTab("channels")}>
          {t("nav.channels")} ({company.sales_channels.length})
        </button>
        <button className={`tab ${activeTab === "discord" ? "active" : ""}`} onClick={() => switchTab("discord")}>
          {t("discord.title")}
        </button>
        <button className={`tab ${activeTab === "convHistory" ? "active" : ""}`} onClick={() => switchTab("convHistory")}>
          {t("companies.convHistory.tabLabel")}
        </button>
      </div>

      {activeTab === "basic" && basicForm && (
        <CompanyBasicTab
          basicForm={basicForm}
          setBasicForm={setBasicForm}
          basicDirty={basicDirty}
          setBasicDirty={setBasicDirty}
          basicSubmitting={basicSubmitting}
          handleBasicSubmit={handleBasicSubmit}
          canEdit={canEdit}
          canMerge={canMerge}
          company={company}
          dedupSubmitting={dedupSubmitting}
          setDedupConfirmOpen={setDedupConfirmOpen}
          setMergeModalOpen={setMergeModalOpen}
        />
      )}

      {activeTab === "addresses" && (
        <CompanyAddressesTab
          billingAddresses={billingAddresses}
          deliveryAddresses={deliveryAddresses}
          canEdit={canEdit}
          openAddressNew={openAddressNew}
          openAddressEdit={openAddressEdit}
          setAddrDeleteTarget={setAddrDeleteTarget}
        />
      )}

      {activeTab === "contacts" && (
        <CompanyContactsTab
          company={company}
          contacts={contacts}
          canEdit={canEdit}
          contactModalOpen={contactModalOpen}
          contactForm={contactForm}
          setContactForm={setContactForm}
          contactSubmitting={contactSubmitting}
          setContactDeleteTarget={setContactDeleteTarget}
          openContactNew={openContactNew}
          openContactEdit={openContactEdit}
          handleContactSubmit={handleContactSubmit}
          onCloseModal={() => setContactModalOpen(false)}
          onContactsRefresh={load}
        />
      )}

      {activeTab === "channels" && (
        <CompanyChannelsTab
          company={company}
          channelsText={channelsText}
          setChannelsText={setChannelsText}
          channelsDirty={channelsDirty}
          setChannelsDirty={setChannelsDirty}
          channelsSubmitting={channelsSubmitting}
          handleChannelsSubmit={handleChannelsSubmit}
          canEdit={canEdit}
        />
      )}

      {activeTab === "discord" && (
        <CompanyDiscordTab
          discordForm={discordForm}
          setDiscordForm={setDiscordForm}
          discordDirty={discordDirty}
          setDiscordDirty={setDiscordDirty}
          discordSubmitting={discordSubmitting}
          handleDiscordSubmit={handleDiscordSubmit}
          handleDiscordDelete={handleDiscordDelete}
          canEdit={canEdit}
        />
      )}

      {activeTab === "convHistory" && (
        <CompanyConvLogsTab
          companyId={company.id}
          contacts={contacts}
        />
      )}

      <CompanyAddressModal
        isOpen={addrModalOpen}
        onClose={() => setAddrModalOpen(false)}
        addrForm={addrForm}
        setAddrForm={setAddrForm}
        submitAddresses={submitAddresses}
        company={company}
        canEdit={canEdit}
        handleAddressTypeChange={handleAddressTypeChange}
      />

      <ConfirmModal
        open={addrDeleteTarget !== null}
        title={t("companies.deleteAddressTitle")}
        message={
          addrDeleteTarget
            // eslint-disable-next-line local/no-japanese-literal -- TODO: 文章全体を1翻訳キーに統合（ADR-027 既知負債）
            ? `${typeLabel(t, addrDeleteTarget.address_type)}${t("companies.address")}「${addrDeleteTarget.branch_name || addrDeleteTarget.name || "(無名)"}」を${t("common.delete")}しますか？`
            : ""
        }
        confirmLabel={t("common.delete")}
        onConfirm={handleAddressDelete}
        onCancel={() => setAddrDeleteTarget(null)}
      />

      <ConfirmModal
        open={contactDeleteTarget !== null}
        title={t("contacts.deleteContact")}
        message={
          contactDeleteTarget
            ? t("contacts.deleteConfirmMessage", {
                name: contactDeleteTarget.display_name || `${contactDeleteTarget.surname || ""} ${contactDeleteTarget.given_name || ""}`.trim() || "-",
                code: contactDeleteTarget.contact_code,
              })
            : ""
        }
        confirmLabel={t("common.delete")}
        onConfirm={handleContactDelete}
        onCancel={() => setContactDeleteTarget(null)}
      />

      {/* PR #145 Q2: 別会社として確定の確認 */}
      <ConfirmModal
        open={dedupConfirmOpen}
        title={t("companies.dedupResolveTitle")}
        message={t("companies.dedupResolveConfirmMessage", { name: company.name })}
        confirmLabel={t("companies.dedupResolveConfirmLabel")}
        onConfirm={handleResolveAsDistinct}
        onCancel={() => setDedupConfirmOpen(false)}
      />

      {/* A-4: 重複マージモーダル */}
      <MergeCompanyModal
        open={mergeModalOpen}
        source={{ id: company.id, name: company.name, company_code: company.company_code }}
        onMerged={(masterId) => {
          setMergeModalOpen(false);
          navigate(`/companies/${masterId}`);
        }}
        onCancel={() => setMergeModalOpen(false)}
      />
    </div>
  );
}
