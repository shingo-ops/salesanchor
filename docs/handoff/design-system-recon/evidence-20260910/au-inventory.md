# Legacy button inventory

- Baseline: `303c3cfe756b1d82c042cba342c3a3150fc5ab8c`
- Legacy nodes: **221** across **71** files
- Native `button` outside `btn`/`btn-*`: **180** (separate; excluded from migration scope count)
- Classifications: statically_mapped=156, custom_styles=51, links=8, dynamic=6
- Tags: button=213, Link=1, a=7
- Parse errors: 0

## Live open-PR overlaps

- PR #2685: frontend/src/pages/quote-detail/QuoteDetailPage.tsx, frontend/src/pages/super-admin/FxRatePage.tsx
- PR #2668: frontend/src/pages/invoices/InvoicesPage.tsx
- PR #2667: frontend/src/pages/inbox/InboxPage.tsx
- PR #2656: frontend/src/pages/admin/DiscordConfigPage.tsx
- PR #2401: frontend/src/pages/inventory/InventoryPage.tsx, frontend/src/pages/inventory/OwnInventoryPage.tsx
- PR #2362: frontend/src/pages/inventory/InventoryPage.tsx, frontend/src/pages/inventory/OwnInventoryPage.tsx

## frontend/src/components/CommissionPanel.tsx (2)

- L228 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => handleUnassign(key)}","inline":true,"name":null}}; form=null; type="button"; disabled={savingRole === key}; style=null

```tsx
<button
                            className="btn-sm"
                            type="button"
                            data-testid={`commission-unassign-${key}`}
                            disabled={savingRole === key}
                            onClick={() => handleUnassign(key)}
                          >
                            {t("commission.unassignBtn")}
                          </button>
```

- L255 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{handleRecalc}","inline":false,"name":"handleRecalc"}}; form=null; type="button"; disabled={recalcing}; style=null

```tsx
<button
                type="button"
                className="btn-primary"
                onClick={handleRecalc}
                disabled={recalcing}
                data-testid="commission-recalc"
              >
                {recalcing ? t("commission.recalculating") : t("commission.recalc")}
              </button>
```

## frontend/src/components/DataTable.tsx (2)

- L286 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => onPageChange(Math.max(1, page - 1))}","inline":true,"name":null}}; form=null; type="button"; disabled={page <= 1}; style=null

```tsx
<button
            type="button"
            className="btn-sm"
            onClick={() => onPageChange(Math.max(1, page - 1))}
            disabled={page <= 1}
            aria-label="previous page"
          >
            {prevPageLabel}
          </button>
```

- L298 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => onPageChange(page + 1)}","inline":true,"name":null}}; form=null; type="button"; disabled={!hasNextPage}; style=null

```tsx
<button
            type="button"
            className="btn-sm"
            onClick={() => onPageChange(page + 1)}
            disabled={!hasNextPage}
            aria-label="next page"
          >
            {nextPageLabel}
          </button>
```

## frontend/src/components/MergeLeadModal.tsx (2)

- L246 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => setStage(\"confirm\")}","inline":true,"name":null}}; form=null; type="button"; disabled={!selected}; style=null

```tsx
<button
                type="button"
                className="btn-primary"
                disabled={!selected}
                onClick={() => setStage("confirm")}
              >
                {t("mergeLead.nextStep")}
              </button>
```

- L309 `button` — statically_mapped; class=static; handlers={}; form=null; type="submit"; disabled={submitting}; style=null

```tsx
<button
                type="submit"
                className="btn-danger"
                disabled={submitting}
              >
                {submitting
                  ? t("mergeLead.merging")
                  : t("mergeLead.executeLabel", { masterName: selected.customer_name })}
              </button>
```

## frontend/src/components/master-list-editor/MasterListEditor.tsx (2)

- L144 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => { setSearch(\"\"); setSearchInput(\"\"); }}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button type="button" className="btn-sm" onClick={() => { setSearch(""); setSearchInput(""); }}>
                {t("common.clear")}
              </button>
```

- L212 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => remove(r.id)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-danger btn-sm" onClick={() => remove(r.id)}>{t("common.delete")}</button>
```

## frontend/src/pages/account-settings/SecuritySection.tsx (1)

- L104 `button` — statically_mapped; class=static; handlers={}; form=null; type="submit"; disabled={changing}; style=null

```tsx
<button type="submit" className="btn-primary" disabled={changing}>
            {changing ? t("accountSettings.changing") : t("accountSettings.changePassword")}
          </button>
```

## frontend/src/pages/admin/DiscordAnnouncePage.tsx (1)

- L115 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{handleSend}","inline":false,"name":"handleSend"}}; form=null; type=null; disabled={sending || !channelId.trim() || !message.trim()}; style=null

```tsx
<button
            onClick={handleSend}
            disabled={sending || !channelId.trim() || !message.trim()}
            className="btn btn-primary"
          >
            {sending ? t("discordAnnounce.sending") : t("discordAnnounce.send")}
          </button>
```

## frontend/src/pages/admin/DiscordConfigPage.tsx (4)

- L278 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{handleSave}","inline":false,"name":"handleSave"}}; form=null; type=null; disabled={saving}; style=null

```tsx
<button onClick={handleSave} disabled={saving} className="btn btn-primary">
              {saving ? t("common.saving") : t("common.save")}
            </button>
```

- L300 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{handleAutoSetup}","inline":false,"name":"handleAutoSetup"}}; form=null; type=null; disabled={!guildId || autoSetupRunning}; style=null

```tsx
<button
              onClick={handleAutoSetup}
              disabled={!guildId || autoSetupRunning}
              className="btn btn-secondary"
            >
              {autoSetupRunning ? t("discordAutoSetup.running") : t("discordAutoSetup.runButton")}
            </button>
```

- L541 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{handleTicketSave}","inline":false,"name":"handleTicketSave"}}; form=null; type=null; disabled={ticketSaving}; style=null

```tsx
<button onClick={handleTicketSave} disabled={ticketSaving} className="btn btn-primary">
              {ticketSaving ? t("common.saving") : t("common.save")}
            </button>
```

- L557 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{handleDeployButton}","inline":false,"name":"handleDeployButton"}}; form=null; type=null; disabled={deploying}; style=null

```tsx
<button
                onClick={handleDeployButton}
                disabled={deploying}
                className="btn btn-secondary"
              >
                {deploying ? t("discordTicketConfig.deploying") : t("discordTicketConfig.deployButton")}
              </button>
```

## frontend/src/pages/admin/InventoryVisibilityPage.tsx (1)

- L161 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => saveRole(row)}","inline":true,"name":null}}; form=null; type=null; disabled={savingFor === row.role_id}; style=null

```tsx
<button
                    onClick={() => saveRole(row)}
                    className="btn-primary"
                    disabled={savingFor === row.role_id}
                  >
                    {savingFor === row.role_id
                      ? t("common.saving")
                      : t("inventoryVisibility.save")}
                  </button>
```

## frontend/src/pages/admin/TenantPolicyPage.tsx (1)

- L304 `button` — statically_mapped; class=static; handlers={}; form=null; type="submit"; disabled={saving}; style=null

```tsx
<button
                type="submit"
                className="btn-primary"
                disabled={saving}
                data-testid="tenant-policy-save"
              >
                {saving ? t("common.saving") : t("common.save")}
              </button>
```

## frontend/src/pages/admin/TenantProfilePage.tsx (1)

- L249 `button` — statically_mapped; class=static; handlers={}; form=null; type="submit"; disabled={saving}; style=null

```tsx
<button
                type="submit"
                className="btn-primary"
                disabled={saving}
                data-testid="tenant-profile-save"
              >
                {saving ? t("common.saving") : t("common.save")}
              </button>
```

## frontend/src/pages/archives/ArchivesPage.tsx (1)

- L60 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => restore(a.id)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm btn-primary" onClick={() => restore(a.id)}>{t("archives.restore")}</button>
```

## frontend/src/pages/bots/BotsPage.tsx (5)

- L203 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{() => { setShowCreate(true); setCreateForm(emptyCreateForm); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-primary field-h-md" onClick={() => { setShowCreate(true); setCreateForm(emptyCreateForm); }}>
            {t("bots.newBot")}
          </button>
```

- L213 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{() => setNewApiKey(null)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style={{ marginTop: "var(--space-2)" }}

```tsx
<button className="btn-sm" onClick={() => setNewApiKey(null)} style={{ marginTop: "var(--space-2)" }}>{t("bots.apiKeyConfirm")}</button>
```

- L311 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{(e) => { e.stopPropagation(); handleRowClick(b); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm" onClick={(e) => { e.stopPropagation(); handleRowClick(b); }}>{t("common.edit")}</button>
```

- L312 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{(e) => { e.stopPropagation(); setRotateTarget(b); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm" onClick={(e) => { e.stopPropagation(); setRotateTarget(b); }}>{t("bots.rotateKey")}</button>
```

- L313 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{(e) => { e.stopPropagation(); setDeleteTarget(b); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); setDeleteTarget(b); }}>{t("common.delete")}</button>
```

## frontend/src/pages/buddy/BuddyPage.tsx (1)

- L85 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => endPair(p.id)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm btn-danger" onClick={() => endPair(p.id)}>{t("buddy.end")}</button>
```

## frontend/src/pages/channels/ChannelsPage.tsx (7)

- L386 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{handleConnect}","inline":false,"name":"handleConnect"}}; form=null; type=null; disabled={connecting}; style=null

```tsx
<button
              className="btn-sm"
              onClick={handleConnect}
              disabled={connecting}
            >
              {connecting ? t("channels.connecting") : t("channels.reauthAction")}
            </button>
```

- L404 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{loadChannels}","inline":false,"name":"loadChannels"}}; form=null; type="button"; disabled=null; style={{ marginLeft: "var(--space-2)" }}

```tsx
<button
            type="button"
            className="btn-sm"
            style={{ marginLeft: "var(--space-2)" }}
            onClick={loadChannels}
          >
            {t("channels.reload")}
          </button>
```

- L435 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{handleConnect}","inline":false,"name":"handleConnect"}}; form=null; type=null; disabled={connecting}; style={{ fontSize: "var(--font-md)", padding: "var(--space-3) var(--space-6)" }}

```tsx
<button
              className="btn-primary"
              onClick={handleConnect}
              disabled={connecting}
              style={{ fontSize: "var(--font-md)", padding: "var(--space-3) var(--space-6)" }}
            >
              {connecting ? t("channels.connecting") : t("channels.connect")}
            </button>
```

- L521 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => setDisconnectTarget(ch)}","inline":true,"name":null}}; form=null; type=null; disabled={disconnecting}; style=null

```tsx
<button
                      className="btn-sm btn-danger"
                      onClick={() => setDisconnectTarget(ch)}
                      disabled={disconnecting}
                    >
                      {t("channels.disconnect")}
                    </button>
```

- L557 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{handleDiscordConnect}","inline":false,"name":"handleDiscordConnect"}}; form=null; type=null; disabled={discordConnecting}; style={{ fontSize: "var(--font-md)", padding: "var(--space-3) var(--space-6)" }}

```tsx
<button
                  className="btn-primary"
                  onClick={handleDiscordConnect}
                  disabled={discordConnecting}
                  style={{ fontSize: "var(--font-md)", padding: "var(--space-3) var(--space-6)" }}
                >
                  {discordConnecting ? t("channels.discordConnecting") : t("channels.discordAddBot")}
                </button>
```

- L600 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => navigate(\"/admin/discord-config\")}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button
                  className="btn-sm btn-ghost"
                  onClick={() => navigate("/admin/discord-config")}
                >
                  {t("channels.discordOpenSettings")}
                </button>
```

- L607 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => setDiscordDisconnectOpen(true)}","inline":true,"name":null}}; form=null; type=null; disabled={discordDisconnecting}; style=null

```tsx
<button
                    className="btn-sm btn-danger"
                    onClick={() => setDiscordDisconnectOpen(true)}
                    disabled={discordDisconnecting}
                  >
                    {t("channels.discordDisconnect")}
                  </button>
```

## frontend/src/pages/commission-settings/CommissionSettingsPage.tsx (1)

- L251 `button` — statically_mapped; class=static; handlers={}; form=null; type="submit"; disabled={saving}; style=null

```tsx
<button
                type="submit"
                className="btn-primary"
                disabled={saving}
                data-testid="settings-save"
              >
                {saving ? t("common.saving") : t("common.save")}
              </button>
```

## frontend/src/pages/commissions/CommissionsPage.tsx (1)

- L226 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => setAssigning(o)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                  type="button"
                  className="btn-sm"
                  data-testid={`commissions-assign-${o.order_id}`}
                  onClick={() => setAssigning(o)}
                >
                  {t("commissions.assignStaff")}
                </button>
```

## frontend/src/pages/companies/CompaniesPage.tsx (4)

- L359 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{() => {\n        setCreateForm(emptyForm);\n        setActiveTab(\"basic\");\n        setPhoneError(null);\n        setAddressesDirty(false);\n        setShowCreate(true);\n      }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button
      className="btn-primary field-h-md"
      onClick={() => {
        setCreateForm(emptyForm);
        setActiveTab("basic");
        setPhoneError(null);
        setAddressesDirty(false);
        setShowCreate(true);
      }}
    >
      + {t("companies.newCompany")}
    </button>
```

- L408 `Link` — links; class=static; handlers={"onClick":{"raw":"{(e) => e.stopPropagation()}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<Link to={`/companies/${c.id}`} className="btn-sm" onClick={(e) => e.stopPropagation()}>{t("companies.viewDetail")}</Link>
```

- L410 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{(e) => { e.stopPropagation(); handleRowClick(c); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm" onClick={(e) => { e.stopPropagation(); handleRowClick(c); }}>{t("common.edit")}</button>
```

- L413 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{(e) => { e.stopPropagation(); setDeleteTarget(c); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); setDeleteTarget(c); }}>{t("common.delete")}</button>
```

## frontend/src/pages/company-detail/CompanyAddressesTab.tsx (4)

- L52 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => openAddressEdit(a)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm" onClick={() => openAddressEdit(a)}>{t("common.edit")}</button>
```

- L53 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => setAddrDeleteTarget(a)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm btn-danger" onClick={() => setAddrDeleteTarget(a)}>{t("common.delete")}</button>
```

- L73 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{() => openAddressNew(\"billing\")}","inline":true,"name":null}}; form=null; type=null; disabled=null; style={{ marginLeft: "var(--space-3)" }}

```tsx
<button className="btn-sm" style={{ marginLeft: "var(--space-3)" }} onClick={() => openAddressNew("billing")}>
            + {t("common.add")}
          </button>
```

- L87 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{() => openAddressNew(\"delivery\")}","inline":true,"name":null}}; form=null; type=null; disabled=null; style={{ marginLeft: "var(--space-3)" }}

```tsx
<button className="btn-sm" style={{ marginLeft: "var(--space-3)" }} onClick={() => openAddressNew("delivery")}>
            + {t("common.add")}
          </button>
```

## frontend/src/pages/company-detail/CompanyBasicTab.tsx (2)

- L127 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => setDedupConfirmOpen(true)}","inline":true,"name":null}}; form=null; type="button"; disabled={dedupSubmitting || basicDirty}; style=null

```tsx
<button
              type="button"
              className="btn-primary"
              onClick={() => setDedupConfirmOpen(true)}
              disabled={dedupSubmitting || basicDirty}
              title={basicDirty ? t("companies.dedupUnsavedHint") : ""}
            >
              {t("companies.dedupConfirmAsDistinct")}
            </button>
```

- L136 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => setMergeModalOpen(true)}","inline":true,"name":null}}; form=null; type="button"; disabled={!canMerge || dedupSubmitting || basicDirty}; style=null

```tsx
<button
              type="button"
              className="btn-danger"
              onClick={() => setMergeModalOpen(true)}
              disabled={!canMerge || dedupSubmitting || basicDirty}
              title={
                !canMerge
                  ? t("companies.dedupMergeNoPermission")
                  : basicDirty
                    ? t("companies.dedupUnsavedHint")
                    : t("companies.dedupMergeHint")
              }
            >
              {t("companies.dedupMergeLabel")}
            </button>
```

## frontend/src/pages/company-detail/CompanyDiscordTab.tsx (2)

- L90 `button` — statically_mapped; class=static; handlers={}; form=null; type="submit"; disabled={!discordDirty || discordSubmitting}; style=null

```tsx
<button
              type="submit"
              className="btn-sm btn-primary"
              disabled={!discordDirty || discordSubmitting}
            >
              {discordSubmitting ? t("common.saving") : t("common.save")}
            </button>
```

- L97 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{handleDiscordDelete}","inline":false,"name":"handleDiscordDelete"}}; form=null; type="button"; disabled=null; style={{ marginLeft: "var(--space-2)" }}

```tsx
<button
              type="button"
              className="btn-sm btn-danger"
              onClick={handleDiscordDelete}
              style={{ marginLeft: "var(--space-2)" }}
            >
              {t("discord.deleteSettings")}
            </button>
```

## frontend/src/pages/conditions/ConditionsPage.tsx (4)

- L279 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{(e) => { e.stopPropagation(); openEdit(c); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm" onClick={(e) => { e.stopPropagation(); openEdit(c); }}>
              {t("common.edit")}
            </button>
```

- L420 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => { setSearch(\"\"); setSearchInput(\"\"); setPage(1); }}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                type="button"
                className="btn-sm"
                onClick={() => { setSearch(""); setSearchInput(""); setPage(1); }}
              >
                {t("common.clear")}
              </button>
```

- L595 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => setPage(p => Math.max(1, p - 1))}","inline":true,"name":null}}; form=null; type=null; disabled={page <= 1}; style=null

```tsx
<button
              className="btn-sm"
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page <= 1}
              data-testid="conditions-page-prev"
            >
              {t("common.prevPage")}
            </button>
```

- L608 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => setPage(p => p + 1)}","inline":true,"name":null}}; form=null; type=null; disabled={!hasNext}; style=null

```tsx
<button
              className="btn-sm"
              onClick={() => setPage(p => p + 1)}
              disabled={!hasNext}
              data-testid="conditions-page-next"
            >
              {t("common.nextPage")}
            </button>
```

## frontend/src/pages/contacts/ContactEditPage.tsx (1)

- L199 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{handleResolveAsDistinct}","inline":false,"name":"handleResolveAsDistinct"}}; form=null; type="button"; disabled={dedupSubmitting}; style=null

```tsx
<button type="button" className="btn-primary" onClick={handleResolveAsDistinct} disabled={dedupSubmitting}>
                  {t("contacts.confirmAsDistinctFull")}
                </button>
```

## frontend/src/pages/contacts/ContactsPage.tsx (4)

- L253 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{() => {\n        setCreateForm({ ...emptyCreateForm, company_id: companyFilter });\n        setShowCreate(true);\n      }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button
      className="btn-primary field-h-md"
      onClick={() => {
        setCreateForm({ ...emptyCreateForm, company_id: companyFilter });
        setShowCreate(true);
      }}
    >
      + {t("contacts.newContact")}
    </button>
```

- L397 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{(e) => { e.stopPropagation(); handleRowClick(c); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm" onClick={(e) => { e.stopPropagation(); handleRowClick(c); }}>{t("common.edit")}</button>
```

- L400 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{(e) => { e.stopPropagation(); setDedupConfirmTarget(c); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm" onClick={(e) => { e.stopPropagation(); setDedupConfirmTarget(c); }}>
                  {t("contacts.confirmAsDistinct")}
                </button>
```

- L405 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{(e) => { e.stopPropagation(); setDeleteTarget(c); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); setDeleteTarget(c); }}>{t("common.delete")}</button>
```

## frontend/src/pages/design-system/DesignSystemPage.tsx (6)

- L166 `button` — statically_mapped; class=static; handlers={}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-primary">btn-primary</button>
```

- L167 `button` — statically_mapped; class=static; handlers={}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-secondary">btn-secondary</button>
```

- L168 `button` — statically_mapped; class=static; handlers={}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm">btn-sm</button>
```

- L169 `button` — statically_mapped; class=static; handlers={}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm btn-danger">btn-sm danger</button>
```

- L412 `button` — statically_mapped; class=static; handlers={}; form=null; type="button"; disabled=null; style=null

```tsx
<button type="button" className="btn-ghost">FAQ</button>
```

- L429 `button` — statically_mapped; class=static; handlers={}; form=null; type="button"; disabled=null; style=null

```tsx
<button type="button" className="btn-ghost">FAQ</button>
```

## frontend/src/pages/erp/ERPPage.tsx (1)

- L58 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{exportInvoices}","inline":false,"name":"exportInvoices"}}; form=null; type=null; disabled={exporting}; style=null

```tsx
<button className="btn-primary field-h-md" onClick={exportInvoices} disabled={exporting}>
              {exporting ? t("erp.exporting") : t("erp.exportInvoices")}
            </button>
```

## frontend/src/pages/goal-setting/GoalSettingPage.tsx (2)

- L201 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{onSave}","inline":false,"name":"onSave"}}; form=null; type=null; disabled={saving}; style=null

```tsx
<button className="btn-primary gs-save-btn" onClick={onSave} disabled={saving}>
        {saving ? t("common.saving") : t("goals.save")}
      </button>
```

- L360 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{fetchAdvice}","inline":false,"name":"fetchAdvice"}}; form=null; type="button"; disabled={loadingAdvice}; style=null

```tsx
<button
                type="button"
                className="btn-primary gs-advisor__run-btn"
                data-testid="goal-advisor-generate"
                onClick={fetchAdvice}
                disabled={loadingAdvice}
              >
                {loadingAdvice ? t("common.loading") : t("goals.advisorGenerate")}
              </button>
```

## frontend/src/pages/inbox/InboxKartePanel.tsx (6)

- L318 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{() => { navigator.clipboard.writeText(regLink); }}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style={{ marginLeft: "var(--spacing-1)" }}

```tsx
<button
                type="button"
                className="btn-sm"
                style={{ marginLeft: "var(--spacing-1)" }}
                onClick={() => { navigator.clipboard.writeText(regLink); }}
              >
                {t("registration.copyLink")}
              </button>
```

- L733 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{handleSend}","inline":false,"name":"handleSend"}}; form=null; type=null; disabled={sending}; style=null

```tsx
<button
          onClick={handleSend}
          disabled={sending}
          className="btn btn-secondary text-xs"
        >
          {sending ? t("leads.channelInviteSending") : t("leads.channelInviteSend")}
        </button>
```

- L791 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{handleResync}","inline":false,"name":"handleResync"}}; form=null; type=null; disabled={syncing}; style=null

```tsx
<button
          onClick={handleResync}
          disabled={syncing}
          className="btn btn-secondary text-xs"
        >
          {syncing ? t("leads.discordRoleSyncing") : t("leads.discordRoleResync")}
        </button>
```

- L834 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{() => handleAction(\"remove-from-channel\")}","inline":true,"name":null}}; form=null; type=null; disabled={loading !== null}; style=null

```tsx
<button
              onClick={() => handleAction("remove-from-channel")}
              disabled={loading !== null}
              className="btn btn-secondary text-xs"
            >
              {loading === "remove-from-channel" ? t("common.processing") : t("leads.discordRemoveFromChannel")}
            </button>
```

- L842 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{() => handleAction(\"kick\")}","inline":true,"name":null}}; form=null; type=null; disabled={loading !== null}; style=null

```tsx
<button
            onClick={() => handleAction("kick")}
            disabled={loading !== null}
            className="btn btn-secondary text-xs"
          >
            {loading === "kick" ? t("common.processing") : t("leads.discordKick")}
          </button>
```

- L849 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{() => handleAction(\"ban\")}","inline":true,"name":null}}; form=null; type=null; disabled={loading !== null}; style=null

```tsx
<button
            onClick={() => handleAction("ban")}
            disabled={loading !== null}
            className="btn btn-danger text-xs"
          >
            {loading === "ban" ? t("common.processing") : t("leads.discordBan")}
          </button>
```

## frontend/src/pages/inbox/InboxPage.tsx (2)

- L46 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => navigate(\"/templates\")}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
        type="button"
        className="btn-ghost"
        onClick={() => navigate("/templates")}
        aria-label={t("nav.templates")}
        data-tooltip={t("nav.templates")}
      >
        {t("nav.templates")}
      </button>
```

- L55 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => navigate(\"/faq\")}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
        type="button"
        className="btn-ghost"
        onClick={() => navigate("/faq")}
        aria-label={t("faq.title")}
        data-tooltip={t("faq.title")}
      >
        FAQ
      </button>
```

## frontend/src/pages/integrations/CarrierCredentialForm.tsx (1)

- L144 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{handleSaveAndTest}","inline":false,"name":"handleSaveAndTest"}}; form=null; type=null; disabled={busy || !clientId || !clientSecret}; style=null

```tsx
<button
          className="btn-primary"
          disabled={busy || !clientId || !clientSecret}
          onClick={handleSaveAndTest}
        >
          {busy ? t("carrierIntegration.saving") : t("carrierIntegration.saveAndTest")}
        </button>
```

## frontend/src/pages/integrations/CarrierIntegrationPage.tsx (3)

- L270 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => handleTest(env)}","inline":true,"name":null}}; form=null; type=null; disabled={busy}; style=null

```tsx
<button
            className="btn-secondary"
            disabled={busy}
            onClick={() => handleTest(env)}
          >
            {busy ? t("carrierIntegration.testing") : t("carrierIntegration.testButton")}
          </button>
```

- L280 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{() => setDeleteConfirmEnv(env)}","inline":true,"name":null}}; form=null; type=null; disabled={busy}; style=null

```tsx
<button
            className="btn-ghost carrier-env-card__delete-btn"
            disabled={busy}
            onClick={() => setDeleteConfirmEnv(env)}
          >
            {t("carrierIntegration.disconnect")}
          </button>
```

- L298 `a` — links; class=static; handlers={}; form=null; type=null; disabled=null; style=null

```tsx
<a
            href={`/management-center/integrations/${carrier}/setup-guide`}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-secondary"
          >
            {t("carrierIntegration.openSetupGuide")}
          </a>
```

## frontend/src/pages/integrations/FedexEtdSetupGuide.tsx (4)

- L147 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{onAdvance}","inline":false,"name":"onAdvance"}}; form=null; type="button"; disabled=null; style=null

```tsx
<button type="button" className="btn-primary" onClick={onAdvance}>
              {advanceLabel}
            </button>
```

- L514 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => void handleUpload(\"LETTERHEAD\")}","inline":true,"name":null}}; form=null; type="button"; disabled={uploadBusy.letterhead}; style=null

```tsx
<button
                    type="button"
                    className="btn-secondary"
                    disabled={uploadBusy.letterhead}
                    onClick={() => void handleUpload("LETTERHEAD")}
                  >
                    {uploadBusy.letterhead
                      ? t("carrierIntegration.fedexEtdGuideUploading")
                      : t("carrierIntegration.fedexEtdGuideUploadButton")}
                  </button>
```

- L543 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => void handleUpload(\"SIGNATURE\")}","inline":true,"name":null}}; form=null; type="button"; disabled={uploadBusy.signature}; style=null

```tsx
<button
                    type="button"
                    className="btn-secondary"
                    disabled={uploadBusy.signature}
                    onClick={() => void handleUpload("SIGNATURE")}
                  >
                    {uploadBusy.signature
                      ? t("carrierIntegration.fedexEtdGuideUploading")
                      : t("carrierIntegration.fedexEtdGuideUploadButton")}
                  </button>
```

- L591 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{advance}","inline":false,"name":"advance"}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
              type="button"
              className="btn-primary"
              onClick={advance}
            >
              {activeStepIndex === stepDefinitions.length - 1
                ? t("carrierIntegration.fedexEtdGuideFinishedButton")
                : t("common.next")}
            </button>
```

## frontend/src/pages/integrations/FedexLabelValidationTab.tsx (7)

- L184 `a` — links; class=static; handlers={}; form=null; type=null; disabled=null; style=null

```tsx
<a
              href="https://developer.fedex.com/api/ja-jp/home.html"
              target="_blank"
              rel="noopener noreferrer"
              className="btn-primary"
            >
              {t("carrierIntegration.fedexGuideDeveloperPortalButton")}
            </a>
```

- L252 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{handleIssueLabels}","inline":false,"name":"handleIssueLabels"}}; form=null; type=null; disabled={labelBusy}; style=null

```tsx
<button
            className="btn-primary"
            disabled={labelBusy}
            onClick={handleIssueLabels}
          >
            {labelBusy ? t("carrierIntegration.lvStep2Issuing") : t("carrierIntegration.lvStep2Button")}
          </button>
```

- L269 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => handleDownloadPdf(label)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button
                  className="btn-secondary btn-sm"
                  onClick={() => handleDownloadPdf(label)}
                >
                  {t("carrierIntegration.lvStep2DownloadPdf")}
                </button>
```

- L366 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{handleDownloadCoverSheet}","inline":false,"name":"handleDownloadCoverSheet"}}; form=null; type=null; disabled={coverBusy || !contactName || !printerModel || !printerCount}; style=null

```tsx
<button
            className="btn-secondary"
            disabled={coverBusy || !contactName || !printerModel || !printerCount}
            onClick={handleDownloadCoverSheet}
          >
            {coverBusy ? t("carrierIntegration.lvStep6Downloading") : t("carrierIntegration.lvStep6Button")}
          </button>
```

- L382 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{handleGetEmailTemplate}","inline":false,"name":"handleGetEmailTemplate"}}; form=null; type=null; disabled={emailBusy}; style=null

```tsx
<button
            className="btn-secondary"
            disabled={emailBusy}
            onClick={handleGetEmailTemplate}
          >
            {emailBusy ? t("carrierIntegration.lvStep7Loading") : t("carrierIntegration.lvStep7Button")}
          </button>
```

- L402 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{handleCopyEmailBody}","inline":false,"name":"handleCopyEmailBody"}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-secondary" onClick={handleCopyEmailBody}>
                {emailCopied
                  ? t("carrierIntegration.lvStep7Copied")
                  : t("carrierIntegration.lvStep7CopyButton")}
              </button>
```

- L417 `a` — links; class=static; handlers={}; form=null; type=null; disabled=null; style=null

```tsx
<a
            href={mailtoHref}
            className="btn-primary"
          >
            {t("carrierIntegration.lvStep8MailtoButton")}
          </a>
```

## frontend/src/pages/integrations/GoogleDriveIntegrationPage.tsx (3)

- L130 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{handleConnect}","inline":false,"name":"handleConnect"}}; form=null; type=null; disabled={busy}; style=null

```tsx
<button className="btn-primary" disabled={busy} onClick={handleConnect}>
              {busy
                ? t("googleDriveIntegration.connecting")
                : t("googleDriveIntegration.connectButton")}
            </button>
```

- L149 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{handleDisconnect}","inline":false,"name":"handleDisconnect"}}; form=null; type=null; disabled={busy}; style=null

```tsx
<button className="btn-secondary" disabled={busy} onClick={handleDisconnect}>
                {t("googleDriveIntegration.disconnect")}
              </button>
```

- L173 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{handleTest}","inline":false,"name":"handleTest"}}; form=null; type=null; disabled={busy}; style=null

```tsx
<button className="btn-primary" disabled={busy} onClick={handleTest}>
                {busy
                  ? t("googleDriveIntegration.testing")
                  : t("googleDriveIntegration.testButton")}
              </button>
```

## frontend/src/pages/integrations/PaypalIntegrationPage.tsx (6)

- L173 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{handleDisconnect}","inline":false,"name":"handleDisconnect"}}; form=null; type=null; disabled={busy}; style=null

```tsx
<button className="btn-secondary" disabled={busy} onClick={handleDisconnect}>
              {t("paypalIntegration.disconnect")}
            </button>
```

- L177 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{handleSave}","inline":false,"name":"handleSave"}}; form=null; type=null; disabled={busy || !clientId || !clientSecret}; style=null

```tsx
<button
            className="btn-primary"
            disabled={busy || !clientId || !clientSecret}
            onClick={handleSave}
          >
            {busy ? t("paypalIntegration.saving") : t("paypalIntegration.save")}
          </button>
```

- L192 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{handleTest}","inline":false,"name":"handleTest"}}; form=null; type=null; disabled={busy || !status?.configured}; style=null

```tsx
<button
            className="btn-primary"
            disabled={busy || !status?.configured}
            onClick={handleTest}
          >
            {busy ? t("paypalIntegration.testing") : t("paypalIntegration.testButton")}
          </button>
```

- L220 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{handlePaymentTest}","inline":false,"name":"handlePaymentTest"}}; form=null; type=null; disabled={busy}; style=null

```tsx
<button className="btn-primary" disabled={busy} onClick={handlePaymentTest}>
              {busy ? t("paypalIntegration.payTestRunning") : t("paypalIntegration.payTestButton")}
            </button>
```

- L231 `a` — links; class=static; handlers={}; form=null; type=null; disabled=null; style=null

```tsx
<a className="btn-primary" href={payTest.approval_url} target="_blank" rel="noopener noreferrer">
                  {t("paypalIntegration.payTestPay")}
                </a>
```

- L234 `a` — links; class=static; handlers={}; form=null; type=null; disabled=null; style=null

```tsx
<a className="btn-secondary" href={`/invoices/${payTest.invoice_id}`} target="_blank" rel="noopener noreferrer">
                  {t("paypalIntegration.payTestOpenInvoice")}
                </a>
```

## frontend/src/pages/inventory/InventoryFilterPanel.tsx (1)

- L304 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{onClose}","inline":false,"name":"onClose"}}; form=null; type="button"; disabled=null; style=null

```tsx
<button type="button" className="btn-sm" onClick={onClose}>
          {t("common.close")}
        </button>
```

## frontend/src/pages/inventory/InventoryPage.tsx (3)

- L395 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{runSearch}","inline":false,"name":"runSearch"}}; form=null; type="button"; disabled=null; style=null

```tsx
<button type="button" className="btn-primary btn-sm field-h-md" data-testid="inventory-search-btn" onClick={runSearch}>
                {t("common.search")}
              </button>
```

- L398 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{resetAll}","inline":false,"name":"resetAll"}}; form=null; type="button"; disabled=null; style=null

```tsx
<button type="button" className="btn-secondary btn-sm field-h-md" data-testid="inventory-reset-sort" onClick={resetAll}>
                {t("inventory.resetSort")}
              </button>
```

- L401 `button` — dynamic; class=dynamic; handlers={"onClick":{"raw":"{() => setShowFilterPanel((v) => !v)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                type="button"
                className={filterEnabled ? "btn-primary btn-sm field-h-md" : "btn-secondary btn-sm field-h-md"}
                data-testid="inventory-filter-toggle"
                aria-expanded={showFilterPanel}
                aria-pressed={filterEnabled}
                onClick={() => setShowFilterPanel((v) => !v)}
              >
                {t("inventory.filterPanel.button")}
              </button>
```

## frontend/src/pages/inventory/OwnInventoryPage.tsx (3)

- L168 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => openAction(row, \"reserve\")}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                        type="button"
                        className="btn btn-sm btn-primary"
                        onClick={() => openAction(row, "reserve")}
                        aria-label={t("ownInventory.reserve")}
                      >
                        {t("ownInventory.reserve")}
                      </button>
```

- L176 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => openAction(row, \"release\")}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                        type="button"
                        className="btn btn-sm btn-secondary"
                        onClick={() => openAction(row, "release")}
                        aria-label={t("ownInventory.release")}
                      >
                        {t("ownInventory.release")}
                      </button>
```

- L184 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => openAction(row, \"ship\")}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                        type="button"
                        className="btn btn-sm btn-danger"
                        onClick={() => openAction(row, "ship")}
                        aria-label={t("ownInventory.ship")}
                      >
                        {t("ownInventory.ship")}
                      </button>
```

## frontend/src/pages/invoice-create/InvoiceCreatePage.tsx (4)

- L234 `button` — dynamic; class=dynamic; handlers={"onClick":{"raw":"{() => setMode(\"inventory\")}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button
          className={mode === "inventory" ? "btn-primary" : "btn-secondary"}
          onClick={() => setMode("inventory")}
          data-testid="invoice-mode-inventory"
        >
          {t("invoices.fromInventory")}
        </button>
```

- L241 `button` — dynamic; class=dynamic; handlers={"onClick":{"raw":"{() => { setSourceQuoteCode(null); setMode(\"quote\"); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button
          className={mode === "quote" ? "btn-primary" : "btn-secondary"}
          onClick={() => { setSourceQuoteCode(null); setMode("quote"); }}
          data-testid="invoice-mode-quote"
        >
          {t("invoices.fromQuote")}
        </button>
```

- L394 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => removeItem(i)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button type="button" className="btn-sm btn-danger" onClick={() => removeItem(i)}>{t("quotes.removeItem")}</button>
```

- L436 `button` — statically_mapped; class=static; handlers={}; form=null; type="submit"; disabled={saving}; style=null

```tsx
<button type="submit" className="btn-primary" disabled={saving}>{saving ? t("common.saving") : t("invoices.createBtn")}</button>
```

## frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx (10)

- L195 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{() => doAction(\"issue\")}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-primary field-h-md" onClick={() => doAction("issue")}>{t("invoices.issueAction")}</button>
```

- L198 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{() => doAction(\"pay\")}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-primary field-h-md" onClick={() => doAction("pay")}>{t("invoices.payAction")}</button>
```

- L201 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{() => doAction(\"paypal-link\")}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-secondary field-h-md" onClick={() => doAction("paypal-link")}>{t("invoices.paypal.issueLink")}</button>
```

- L204 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{() => doAction(\"paypal-confirm\")}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-primary field-h-md" onClick={() => doAction("paypal-confirm")}>{t("invoices.paypal.confirm")}</button>
```

- L207 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{() => setShowVoidForm(true)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-danger field-h-md" onClick={() => setShowVoidForm(true)}>{t("invoices.voidAction")}</button>
```

- L209 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{handleDownloadPdf}","inline":false,"name":"handleDownloadPdf"}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-secondary field-h-md" onClick={handleDownloadPdf}>{t("invoices.snapshot.downloadPdf")}</button>
```

- L222 `a` — links; class=static; handlers={}; form=null; type=null; disabled=null; style=null

```tsx
<a className="btn-secondary" href={invoice.paypal_approval_url} target="_blank" rel="noopener noreferrer">{t("invoices.paypal.openLink")}</a>
```

- L232 `a` — links; class=static; handlers={}; form=null; type=null; disabled=null; style=null

```tsx
<a className="btn-secondary" href={invoice.paypal_invoicer_view_url} target="_blank" rel="noopener noreferrer">{t("invoices.paypal.openOriginal")}</a>
```

- L235 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{handleDownloadCopyPdf}","inline":false,"name":"handleDownloadCopyPdf"}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-secondary" onClick={handleDownloadCopyPdf}>{t("invoices.paypal.downloadCopyPdf")}</button>
```

- L274 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{handleVoid}","inline":false,"name":"handleVoid"}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-danger" onClick={handleVoid}>{t("invoices.voidExecute")}</button>
```

## frontend/src/pages/invoices/InvoicesPage.tsx (2)

- L113 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => navigate(`/invoices/${inv.id}`)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm" onClick={() => navigate(`/invoices/${inv.id}`)}>
          {t("common.detail")}
        </button>
```

- L140 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{() => navigate(\"/invoices/new\")}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-primary field-h-md" onClick={() => navigate("/invoices/new")}>
            {t("invoices.createTitle")}
          </button>
```

## frontend/src/pages/leads/LeadsPage.tsx (4)

- L314 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{() => { setShowCreate(true); setCreateForm(emptyCreateForm); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-primary field-h-md" onClick={() => { setShowCreate(true); setCreateForm(emptyCreateForm); }}>{t("leads.newLead")}</button>
```

- L501 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{(e) => { e.stopPropagation(); setConvertTarget(l); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm btn-primary" onClick={(e) => { e.stopPropagation(); setConvertTarget(l); }}>{t("leads.convert")}</button>
```

- L504 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{(e) => { e.stopPropagation(); setMergeSource(l); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm" onClick={(e) => { e.stopPropagation(); setMergeSource(l); }}>{t("leads.merge")}</button>
```

- L506 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{(e) => { e.stopPropagation(); setDeleteTarget(l); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); setDeleteTarget(l); }}>{t("common.delete")}</button>
```

## frontend/src/pages/login/LoginPage.tsx (2)

- L119 `button` — statically_mapped; class=static; handlers={}; form=null; type="submit"; disabled={loading}; style=null

```tsx
<button type="submit" className="btn-primary" disabled={loading}>
                {loading ? t("login.signingIn") : t("login.signIn")}
              </button>
```

- L144 `button` — statically_mapped; class=static; handlers={}; form=null; type="submit"; disabled={loading}; style=null

```tsx
<button type="submit" className="btn-primary" disabled={loading}>
                  {loading ? t("login.sendingEmail") : t("login.sendResetEmail")}
                </button>
```

## frontend/src/pages/note-master/NoteMasterPage.tsx (2)

- L236 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{(e) => { e.stopPropagation(); openEdit(n); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button
              className="btn-sm"
              onClick={(e) => { e.stopPropagation(); openEdit(n); }}
            >
              {t("common.edit")}
            </button>
```

- L244 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{(e) => { e.stopPropagation(); setDeleteTarget(n); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button
              className="btn-sm btn-danger"
              onClick={(e) => { e.stopPropagation(); setDeleteTarget(n); }}
            >
              {t("common.delete")}
            </button>
```

## frontend/src/pages/notifications/NotificationsPage.tsx (1)

- L99 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => handleDelete(ch.id)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm btn-danger" onClick={() => handleDelete(ch.id)}>{t("common.delete")}</button>
```

## frontend/src/pages/orders/OrdersTable.tsx (8)

- L139 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => handleEdit(o)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm" onClick={() => handleEdit(o)}>{t("common.edit")}</button>
```

- L143 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => setPaidOrder(o, true)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button
                className="btn-sm"
                onClick={() => setPaidOrder(o, true)}
                data-testid={`mark-paid-${o.id}`}
              >
                {t("orders.markPaid")}
              </button>
```

- L152 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => setPurchaseTarget(o)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button
                className="btn-sm"
                onClick={() => setPurchaseTarget(o)}
                data-testid={`mark-purchased-${o.id}`}
              >
                {t("orders.markPurchased")}
              </button>
```

- L161 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => setShippingTarget(o)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button
                className="btn-sm"
                onClick={() => setShippingTarget(o)}
                data-testid={`issue-label-${o.id}`}
              >
                {t("orders.issueLabel")}
              </button>
```

- L171 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => setPaidOrder(o, false)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button
                className="btn-sm"
                onClick={() => setPaidOrder(o, false)}
                data-testid={`mark-unpaid-${o.id}`}
              >
                {t("orders.markUnpaid")}
              </button>
```

- L181 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => setShippingTarget(o)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm" onClick={() => setShippingTarget(o)} data-testid={`open-shipping-${o.id}`}>
              {t("orders.shipping")}
            </button>
```

- L184 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => setPurchaseTarget(o)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm" onClick={() => setPurchaseTarget(o)} data-testid={`open-purchase-${o.id}`}>
              {t("orders.purchase")}
            </button>
```

- L187 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => setDeleteTarget(o)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm btn-danger" onClick={() => setDeleteTarget(o)}>
              {t("common.delete")}
            </button>
```

## frontend/src/pages/product-categories/ProductCategoriesPage.tsx (5)

- L181 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{(e) => { e.stopPropagation(); openEdit(c); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm" onClick={(e) => { e.stopPropagation(); openEdit(c); }}>
              {t("common.edit")}
            </button>
```

- L186 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{(e) => { e.stopPropagation(); setDeleteTarget(c); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); setDeleteTarget(c); }}>
              {t("common.delete")}
            </button>
```

- L294 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => { setSearch(\"\"); setSearchInput(\"\"); setPage(1); }}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                type="button"
                className="btn-sm"
                onClick={() => { setSearch(""); setSearchInput(""); setPage(1); }}
              >
                {t("common.clear")}
              </button>
```

- L377 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => setPage(p => Math.max(1, p - 1))}","inline":true,"name":null}}; form=null; type=null; disabled={page <= 1}; style=null

```tsx
<button
              className="btn-sm"
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page <= 1}
              data-testid="product-categories-page-prev"
            >
              {t("common.prevPage")}
            </button>
```

- L390 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => setPage(p => p + 1)}","inline":true,"name":null}}; form=null; type=null; disabled={!hasNext}; style=null

```tsx
<button
              className="btn-sm"
              onClick={() => setPage(p => p + 1)}
              disabled={!hasNext}
              data-testid="product-categories-page-next"
            >
              {t("common.nextPage")}
            </button>
```

## frontend/src/pages/products/ProductsPage.tsx (7)

- L200 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => setConfirmBulkDelete(true)}","inline":true,"name":null}}; form=null; type="button"; disabled={selectedIds.size === 0}; style=null

```tsx
<button
          type="button"
          className="btn-danger"
          disabled={selectedIds.size === 0}
          onClick={() => setConfirmBulkDelete(true)}
          data-testid="products-bulk-delete"
        >
          {t("common.delete")}
        </button>
```

- L235 `button` — dynamic; class=dynamic; handlers={"onClick":{"raw":"{toggleReorderMode}","inline":false,"name":"toggleReorderMode"}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                type="button"
                className={reorderMode ? "btn-primary btn-sm" : "btn-sm"}
                onClick={toggleReorderMode}
                aria-pressed={reorderMode}
                data-testid="products-reorder-toggle"
                title={t("products.reorderHint")}
              >
                {reorderMode ? t("products.reorderModeOn") : t("products.reorderMode")}
              </button>
```

- L269 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => goCreate(\"/quotes/new\")}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-primary btn-sm" onClick={() => goCreate("/quotes/new")} data-testid="create-quote-from-products">
            {t("products.createQuote")}
          </button>
```

- L272 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => goCreate(\"/invoices/new\")}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-primary btn-sm" onClick={() => goCreate("/invoices/new")} data-testid="create-invoice-from-products">
            {t("products.createInvoice")}
          </button>
```

- L275 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => setSelectedIds(new Set())}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm" onClick={() => setSelectedIds(new Set())}>
            {t("common.clear")}
          </button>
```

- L423 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => setPage((p) => Math.max(1, p - 1))}","inline":true,"name":null}}; form=null; type=null; disabled={page <= 1}; style=null

```tsx
<button
              className="btn-sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              data-testid="products-page-prev"
            >
              {t("common.prevPage")}
            </button>
```

- L436 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => setPage((p) => p + 1)}","inline":true,"name":null}}; form=null; type=null; disabled={!hasNext}; style=null

```tsx
<button
              className="btn-sm"
              onClick={() => setPage((p) => p + 1)}
              disabled={!hasNext}
              data-testid="products-page-next"
            >
              {t("common.nextPage")}
            </button>
```

## frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx (2)

- L202 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => removeItem(i)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button type="button" className="btn-sm btn-danger" onClick={() => removeItem(i)}>{t("quotes.removeItem")}</button>
```

- L210 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{addItem}","inline":false,"name":"addItem"}}; form=null; type="button"; disabled=null; style={{ marginTop: "var(--space-2)" }}

```tsx
<button type="button" className="btn-secondary" onClick={addItem} style={{ marginTop: "var(--space-2)" }}>{t("quotes.addItem")}</button>
```

## frontend/src/pages/purchase-orders/PurchaseOrdersPage.tsx (6)

- L243 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => doAction(p.id, \"receive\")}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm btn-primary" onClick={() => doAction(p.id, "receive")}>{t("purchaseOrders.actionReceive")}</button>
```

- L247 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => doAction(p.id, \"unreceive\")}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button
                    className="btn-sm btn-secondary"
                    data-testid={`po-unreceive-${p.id}`}
                    onClick={() => doAction(p.id, "unreceive")}
                  >
                    {t("purchaseOrders.actionUnreceive")}
                  </button>
```

- L256 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => doAction(p.id, \"cancel\")}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm btn-danger" onClick={() => doAction(p.id, "cancel")}>{t("purchaseOrders.actionCancel")}</button>
```

- L260 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => downloadPdf(p.id, p.po_number, p.status)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button
                    className="btn-sm btn-secondary"
                    data-testid={`po-pdf-${p.id}`}
                    onClick={() => downloadPdf(p.id, p.po_number, p.status)}
                  >
                    {t("purchaseOrders.actionDownloadPdf")}
                  </button>
```

- L269 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => sendEmail(p.id)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button
                    className="btn-sm btn-secondary"
                    data-testid={`po-send-email-${p.id}`}
                    onClick={() => sendEmail(p.id)}
                  >
                    {t("purchaseOrders.actionSendEmail")}
                  </button>
```

- L278 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => resendEmail(p.id)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button
                    className="btn-sm btn-primary"
                    data-testid={`po-resend-email-${p.id}`}
                    onClick={() => resendEmail(p.id)}
                  >
                    {t("purchaseOrders.actionResendEmail")}
                  </button>
```

## frontend/src/pages/quote-create/QuoteCreatePage.tsx (1)

- L243 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => removeItem(i)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button type="button" className="btn-sm btn-danger" onClick={() => removeItem(i)}>{t("quotes.removeItem")}</button>
```

## frontend/src/pages/quote-detail/QuoteDetailPage.tsx (6)

- L133 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{() => doAction(\"send\")}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-primary field-h-md" onClick={() => doAction("send")}>{t("quotes.send")}</button>
```

- L137 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{() => doAction(\"approve\")}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-primary field-h-md" onClick={() => doAction("approve")}>{t("quotes.approve")}</button>
```

- L138 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{() => doAction(\"reject\")}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-danger field-h-md" onClick={() => doAction("reject")}>{t("quotes.reject")}</button>
```

- L142 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{convertToInvoice}","inline":false,"name":"convertToInvoice"}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-primary field-h-md" onClick={convertToInvoice}>{t("quotes.convertToInvoice")}</button>
```

- L145 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{handleFetchFxRate}","inline":false,"name":"handleFetchFxRate"}}; form=null; type=null; disabled={fxLoading}; style=null

```tsx
<button className="btn-secondary field-h-md" onClick={handleFetchFxRate} disabled={fxLoading}>
                {fxLoading ? t("common.loading") : t("quotes.fx.fetchRate")}
              </button>
```

- L149 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{handleDownloadPdf}","inline":false,"name":"handleDownloadPdf"}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-secondary field-h-md" onClick={handleDownloadPdf}>{t("invoices.snapshot.downloadPdf")}</button>
```

## frontend/src/pages/quotes/QuotesPage.tsx (2)

- L101 `button` — dynamic; class=dynamic; handlers={"onClick":{"raw":"{() => setStatusFilter(\"\")}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
              type="button"
              className={statusFilter === "" ? "btn-primary btn-sm" : "btn-secondary btn-sm"}
              data-testid="quotes-filter-all"
              aria-pressed={statusFilter === ""}
              onClick={() => setStatusFilter("")}
            >
              {t("quotes.allStatuses")}
            </button>
```

- L168 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => navigate(`/quotes/${q.id}`)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm" onClick={() => navigate(`/quotes/${q.id}`)}>{t("common.detail")}</button>
```

## frontend/src/pages/register/RegisterAddressPage.tsx (2)

- L294 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{toggleLang}","inline":false,"name":"toggleLang"}}; form=null; type="button"; disabled=null; style={{ fontSize: "var(--font-size-sm)" }}

```tsx
<button type="button" className="btn btn-ghost" onClick={toggleLang} style={{ fontSize: "var(--font-size-sm)" }}>
          {currentLang === "en" ? t("registration.switchToJapanese") : t("registration.switchToEnglish")}
        </button>
```

- L461 `button` — custom_styles; class=static; handlers={}; form=null; type="submit"; disabled={submitting}; style={{ width: "100%" }}

```tsx
<button
          type="submit"
          className="btn btn-primary"
          disabled={submitting}
          style={{ width: "100%" }}
        >
          {submitting ? t("common.saving") : t("registration.addAddress")}
        </button>
```

## frontend/src/pages/register/RegisterChangeBillingPage.tsx (2)

- L227 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{toggleLang}","inline":false,"name":"toggleLang"}}; form=null; type="button"; disabled=null; style={{ fontSize: "var(--font-size-sm)" }}

```tsx
<button type="button" className="btn btn-ghost" onClick={toggleLang} style={{ fontSize: "var(--font-size-sm)" }}>
          {currentLang === "en" ? t("registration.switchToJapanese") : t("registration.switchToEnglish")}
        </button>
```

- L407 `button` — custom_styles; class=static; handlers={}; form=null; type="submit"; disabled={submitting}; style={{ width: "100%" }}

```tsx
<button
          type="submit"
          className="btn btn-primary"
          disabled={submitting}
          style={{ width: "100%" }}
        >
          {submitting ? t("common.saving") : t("registration.changeBillingSubmit")}
        </button>
```

## frontend/src/pages/register/RegisterPage.tsx (2)

- L279 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{toggleLang}","inline":false,"name":"toggleLang"}}; form=null; type="button"; disabled=null; style={{ fontSize: "var(--font-size-sm)" }}

```tsx
<button type="button" className="btn btn-ghost" onClick={toggleLang} style={{ fontSize: "var(--font-size-sm)" }}>
          {currentLang === "en" ? t("registration.switchToJapanese") : t("registration.switchToEnglish")}
        </button>
```

- L538 `button` — custom_styles; class=static; handlers={}; form=null; type="submit"; disabled={submitting}; style={{ width: "100%" }}

```tsx
<button
          type="submit"
          className="btn btn-primary"
          disabled={submitting}
          style={{ width: "100%" }}
        >
          {submitting ? t("common.saving") : t("registration.submit")}
        </button>
```

## frontend/src/pages/roles/RolesPage.tsx (5)

- L340 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{openCreateRole}","inline":false,"name":"openCreateRole"}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-primary btn-sm" onClick={openCreateRole}>+ {t("common.new")}</button>
```

- L366 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => setUserAssignOpen(true)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-secondary btn-block" onClick={() => setUserAssignOpen(true)}>
              {t("roles.assignUsers")}
            </button>
```

- L398 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => openEditRole(selectedRole)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm" onClick={() => openEditRole(selectedRole)}>{t("common.edit")}</button>
```

- L400 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => setDeleteTarget(selectedRole)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm btn-danger" onClick={() => setDeleteTarget(selectedRole)}>{t("common.delete")}</button>
```

- L407 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{savePermissions}","inline":false,"name":"savePermissions"}}; form=null; type=null; disabled={!dirty || savingPerms || !canEditPerms}; style=null

```tsx
<button className="btn-primary" disabled={!dirty || savingPerms || !canEditPerms} onClick={savePermissions}>
                    {savingPerms ? t("common.saving") : t("roles.saveChanges")}
                  </button>
```

## frontend/src/pages/sales/SalesPage.tsx (1)

- L167 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => setEditing(o)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                  type="button"
                  className="btn-sm"
                  data-testid={`sales-edit-${o.order_id}`}
                  onClick={() => setEditing(o)}
                >
                  {t("sales.editFinancial")}
                </button>
```

## frontend/src/pages/shifts/ShiftsPage.tsx (1)

- L114 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => handleDelete(s.id)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm btn-danger" onClick={() => handleDelete(s.id)}>{t("common.delete")}</button>
```

## frontend/src/pages/staff/StaffPage.tsx (3)

- L220 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{() => { setShowCreate(true); setCreateForm(emptyCreateForm); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-primary field-h-md" onClick={() => { setShowCreate(true); setCreateForm(emptyCreateForm); }}>
            {t("staff.newStaff")}
          </button>
```

- L366 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{(e) => { e.stopPropagation(); handleRowClick(s); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm" onClick={(e) => { e.stopPropagation(); handleRowClick(s); }}>{t("common.edit")}</button>
```

- L367 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{(e) => { e.stopPropagation(); setDeleteTarget(s); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); setDeleteTarget(s); }}>{t("common.delete")}</button>
```

## frontend/src/pages/status-master/StatusMasterPage.tsx (5)

- L208 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{(e) => { e.stopPropagation(); openEdit(s); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm" onClick={(e) => { e.stopPropagation(); openEdit(s); }}>
              {t("common.edit")}
            </button>
```

- L213 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{(e) => { e.stopPropagation(); setDeleteTarget(s); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); setDeleteTarget(s); }}>
              {t("common.delete")}
            </button>
```

- L362 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => { setSearch(\"\"); setSearchInput(\"\"); setPage(1); }}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                type="button"
                className="btn-sm"
                onClick={() => { setSearch(""); setSearchInput(""); setPage(1); }}
              >
                {t("common.clear")}
              </button>
```

- L445 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => setPage(p => Math.max(1, p - 1))}","inline":true,"name":null}}; form=null; type=null; disabled={page <= 1}; style=null

```tsx
<button
              className="btn-sm"
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page <= 1}
              data-testid="status-master-page-prev"
            >
              {t("common.prevPage")}
            </button>
```

- L458 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => setPage(p => p + 1)}","inline":true,"name":null}}; form=null; type=null; disabled={!hasNext}; style=null

```tsx
<button
              className="btn-sm"
              onClick={() => setPage(p => p + 1)}
              disabled={!hasNext}
              data-testid="status-master-page-next"
            >
              {t("common.nextPage")}
            </button>
```

## frontend/src/pages/super-admin/DexTab.tsx (2)

- L223 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{runImportPreview}","inline":false,"name":"runImportPreview"}}; form=null; type="button"; disabled={importing}; style=null

```tsx
<button
            type="button"
            className="btn-secondary"
            disabled={importing}
            onClick={runImportPreview}
            data-testid="dex-import-preview-btn"
          >
            {t("superAdmin.dex.import.previewBtn")}
          </button>
```

- L277 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{runImportApply}","inline":false,"name":"runImportApply"}}; form=null; type="button"; disabled={importing}; style=null

```tsx
<button
            type="button"
            className="btn-primary"
            disabled={importing}
            onClick={runImportApply}
            data-testid="dex-import-apply-btn"
          >
            {t("superAdmin.dex.import.applyBtn", {
              count: importPreview.added_count,
            })}
          </button>
```

## frontend/src/pages/super-admin/ExtractionPromptConfigTab.tsx (1)

- L241 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => void handleSave(key)}","inline":true,"name":null}}; form=null; type="button"; disabled={saving[key]}; style=null

```tsx
<button
              type="button"
              className="btn-primary"
              disabled={saving[key]}
              data-testid={`prompt-save-${key}`}
              onClick={() => void handleSave(key)}
            >
              {saving[key] ? t("common.saving") : t(`${p}.save`)}
            </button>
```

## frontend/src/pages/super-admin/FxRatePage.tsx (1)

- L93 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{handleRefresh}","inline":false,"name":"handleRefresh"}}; form=null; type="button"; disabled={refreshing}; style=null

```tsx
<button
            type="button"
            className="btn-primary field-h-md"
            onClick={handleRefresh}
            disabled={refreshing}
            data-testid="fx-rate-refresh-btn"
          >
            <RefreshIcon size={16} aria-hidden="true" />
            {refreshing ? t("common.loading") : t("superAdmin.fxRate.refreshBtn")}
          </button>
```

## frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx (7)

- L342 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{openCreateRule}","inline":false,"name":"openCreateRule"}}; form=null; type=null; disabled=null; style={{ marginLeft: "auto" }}

```tsx
<button onClick={openCreateRule} className="btn-primary btn-sm" data-testid="rules-new" style={{ marginLeft: "auto" }}>
            {t("superAdmin.knowledge.newRule")}
          </button>
```

- L345 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => setRuleConfirmDelete(true)}","inline":true,"name":null}}; form=null; type=null; disabled={ruleSelected.size === 0}; style=null

```tsx
<button
            onClick={() => setRuleConfirmDelete(true)}
            className="btn-danger btn-sm"
            disabled={ruleSelected.size === 0}
            data-testid="rules-bulk-delete"
          >
            {t("common.delete")}
          </button>
```

- L390 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => openEditRule(r)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm" onClick={() => openEditRule(r)} data-testid={`rule-edit-${r.id}`}>
                      {t("common.edit")}
                    </button>
```

- L420 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{openCreateAlias}","inline":false,"name":"openCreateAlias"}}; form=null; type=null; disabled=null; style={{ marginLeft: "auto" }}

```tsx
<button onClick={openCreateAlias} className="btn-primary btn-sm" data-testid="aliases-new" style={{ marginLeft: "auto" }}>
            {t("superAdmin.knowledge.newAlias")}
          </button>
```

- L423 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => setAliasConfirmDelete(true)}","inline":true,"name":null}}; form=null; type=null; disabled={aliasSelected.size === 0}; style=null

```tsx
<button
            onClick={() => setAliasConfirmDelete(true)}
            className="btn-danger btn-sm"
            disabled={aliasSelected.size === 0}
            data-testid="aliases-bulk-delete"
          >
            {t("common.delete")}
          </button>
```

- L462 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => openEditAlias(a)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm" onClick={() => openEditAlias(a)} data-testid={`alias-edit-${a.id}`}>
                      {t("common.edit")}
                    </button>
```

- L511 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{savePrompt}","inline":false,"name":"savePrompt"}}; form=null; type="button"; disabled={promptSupplierId === null || promptSaving}; style=null

```tsx
<button
              type="button"
              className="btn-primary"
              disabled={promptSupplierId === null || promptSaving}
              onClick={savePrompt}
              data-testid="supplier-prompt-save"
            >
              {promptSaving ? t("common.saving") : t("common.save")}
            </button>
```

## frontend/src/pages/super-admin/LLMBudgetTab.tsx (2)

- L227 `button` — statically_mapped; class=static; handlers={}; form=null; type="submit"; disabled=null; style=null

```tsx
<button
              type="submit"
              className="btn-primary"
              data-testid="llm-budget-save"
            >
              {t("common.save")}
            </button>
```

- L234 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{cancelEdit}","inline":false,"name":"cancelEdit"}}; form=null; type="button"; disabled=null; style={{ marginLeft: "var(--space-2)" }}

```tsx
<button
              type="button"
              className="btn-secondary"
              onClick={cancelEdit}
              style={{ marginLeft: "var(--space-2)" }}
              data-testid="llm-budget-cancel"
            >
              {t("common.cancel")}
            </button>
```

## frontend/src/pages/super-admin/ParseReviewPage.tsx (4)

- L844 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => void handleApprove()}","inline":true,"name":null}}; form=null; type=null; disabled={isFinal || submitting}; style=null

```tsx
<button
                  onClick={() => void handleApprove()}
                  disabled={isFinal || submitting}
                  data-testid="review-approve-btn"
                  className="btn-primary"
                >
                  {t("superAdmin.inbound.review.approveBtn")}
                </button>
```

- L852 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{() => setShowRejectDialog(true)}","inline":true,"name":null}}; form=null; type=null; disabled={isFinal || submitting}; style={{ marginLeft: "var(--space-2)" }}

```tsx
<button
                  onClick={() => setShowRejectDialog(true)}
                  disabled={isFinal || submitting}
                  data-testid="review-reject-btn"
                  className="btn-danger"
                  style={{ marginLeft: "var(--space-2)" }}
                >
                  {t("superAdmin.inbound.review.rejectBtn")}
                </button>
```

- L890 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => void handleReject()}","inline":true,"name":null}}; form=null; type=null; disabled={submitting}; style=null

```tsx
<button
                  onClick={() => void handleReject()}
                  disabled={submitting}
                  data-testid="review-reject-confirm-btn"
                  className="btn-danger"
                >
                  {t("superAdmin.inbound.review.rejectConfirmBtn")}
                </button>
```

- L898 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{() => {\n                    setShowRejectDialog(false);\n                    setRejectReason(\"\");\n                  }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style={{ marginLeft: "var(--space-2)" }}

```tsx
<button
                  onClick={() => {
                    setShowRejectDialog(false);
                    setRejectReason("");
                  }}
                  className="btn-secondary"
                  style={{ marginLeft: "var(--space-2)" }}
                >
                  {t("common.cancel")}
                </button>
```

## frontend/src/pages/super-admin/ProductMastersTab.tsx (1)

- L116 `button` — dynamic; class=dynamic; handlers={"onClick":{"raw":"{() => setAttr(a.key)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style={{ padding: "var(--space-1) var(--space-3)" }}

```tsx
<button
            key={a.key}
            role="tab"
            aria-selected={attr === a.key}
            className={attr === a.key ? "btn-primary" : "btn-secondary"}
            onClick={() => setAttr(a.key)}
            style={{ padding: "var(--space-1) var(--space-3)" }}
            data-testid={`attr-master-tab-${a.key}`}
          >
            {t(a.labelKey)}
          </button>
```

## frontend/src/pages/super-admin/TcgSeriesTab.tsx (2)

- L277 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => removeType(tp.id)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                  type="button"
                  className="btn-danger-link"
                  aria-label={`${t("common.delete")} ${tp.name_ja}`}
                  onClick={() => removeType(tp.id)}
                >
                  {t("common.delete")}
                </button>
```

- L365 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => remove(it.id)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button onClick={() => remove(it.id)} className="btn-danger-link">
                  {t("common.delete")}
                </button>
```

## frontend/src/pages/suppliers/SuppliersPage.tsx (5)

- L179 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => { setSearch(\"\"); setSearchInput(\"\"); setPage(1); }}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                type="button"
                className="btn-sm"
                onClick={() => { setSearch(""); setSearchInput(""); setPage(1); }}
              >
                {t("common.clear")}
              </button>
```

- L239 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{(e) => { e.stopPropagation(); handleRowClick(s); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm" onClick={(e) => { e.stopPropagation(); handleRowClick(s); }}>{t("common.edit")}</button>
```

- L240 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{(e) => { e.stopPropagation(); setDeleteTarget(s); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); setDeleteTarget(s); }}>{t("suppliers.deleteSupplier")}</button>
```

- L275 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => setPage((p) => Math.max(1, p - 1))}","inline":true,"name":null}}; form=null; type=null; disabled={page <= 1}; style=null

```tsx
<button
              className="btn-sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              data-testid="suppliers-page-prev"
            >
              {t("common.prevPage")}
            </button>
```

- L288 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => setPage((p) => p + 1)}","inline":true,"name":null}}; form=null; type=null; disabled={!hasNext}; style=null

```tsx
<button
              className="btn-sm"
              onClick={() => setPage((p) => p + 1)}
              disabled={!hasNext}
              data-testid="suppliers-page-next"
            >
              {t("common.nextPage")}
            </button>
```

## frontend/src/pages/teams/TeamsPage.tsx (6)

- L181 `button` — custom_styles; class=static; handlers={"onClick":{"raw":"{() => { setShowCreate(true); setCreateForm(emptyForm); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-primary field-h-md" onClick={() => { setShowCreate(true); setCreateForm(emptyForm); }}>
              {t("teams.newTeam")}
            </button>
```

- L244 `button` — statically_mapped; class=static; handlers={}; form=null; type="submit"; disabled=null; style=null

```tsx
<button type="submit" className="btn-primary">{t("common.add")}</button>
```

- L254 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => removeMember(m.user_id)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm btn-danger" onClick={() => removeMember(m.user_id)}>{t("common.remove")}</button>
```

- L281 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{(e) => { e.stopPropagation(); openMembers(team); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm" onClick={(e) => { e.stopPropagation(); openMembers(team); }}>{t("teams.membersBtn")}</button>
```

- L283 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{(e) => { e.stopPropagation(); handleRowClick(team); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm" onClick={(e) => { e.stopPropagation(); handleRowClick(team); }}>{t("common.edit")}</button>
```

- L286 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{(e) => { e.stopPropagation(); setDeleteTarget(team); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); setDeleteTarget(team); }}>{t("common.delete")}</button>
```

## frontend/src/pages/units/UnitsPage.tsx (5)

- L189 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{(e) => { e.stopPropagation(); openEdit(u); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm" onClick={(e) => { e.stopPropagation(); openEdit(u); }}>
              {t("common.edit")}
            </button>
```

- L194 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{(e) => { e.stopPropagation(); setDeleteTarget(u); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); setDeleteTarget(u); }}>
              {t("common.delete")}
            </button>
```

- L253 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => { setSearch(\"\"); setSearchInput(\"\"); setPage(1); }}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                type="button"
                className="btn-sm"
                onClick={() => { setSearch(""); setSearchInput(""); setPage(1); }}
              >
                {t("common.clear")}
              </button>
```

- L400 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => setPage(p => Math.max(1, p - 1))}","inline":true,"name":null}}; form=null; type=null; disabled={page <= 1}; style=null

```tsx
<button
              className="btn-sm"
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page <= 1}
              data-testid="units-page-prev"
            >
              {t("common.prevPage")}
            </button>
```

- L413 `button` — statically_mapped; class=static; handlers={"onClick":{"raw":"{() => setPage(p => p + 1)}","inline":true,"name":null}}; form=null; type=null; disabled={!hasNext}; style=null

```tsx
<button
              className="btn-sm"
              onClick={() => setPage(p => p + 1)}
              disabled={!hasNext}
              data-testid="units-page-next"
            >
              {t("common.nextPage")}
            </button>
```

# Native buttons outside btn-prefix (180)

- frontend/src/components/Button.tsx:L76; class=dynamic; handlers={}; form=null; type=null; disabled={disabled || loading}; style=null

```tsx
<button
      ref={ref}
      className={classes}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      aria-pressed={isTab ? active : undefined}
      aria-label={ariaLabel}
      {...rest}
    >
      {loading && <Spinner size="sm" tone="inherit" decorative />}
      {loading ? (loadingText ?? children) : children}
    </button>
```

- frontend/src/components/ChannelTypeCombobox.tsx:L120; class=absent; handlers={"onClick":{"raw":"{() => {\n              onChange(\"\");\n              onCommit?.();\n              setQuery(\"\");\n              setOpen(false);\n            }}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style={{
              position: "absolute",
              right: "var(--space-2)",
              top: "50%",
              transform: "translateY(-50%)",
              border: 0,
              background: "transparent",
              color: "var(--text-secondary)",
              cursor: "pointer",
              padding: 0,
            }}

```tsx
<button
            type="button"
            aria-label={t("common.clear", { defaultValue: "Clear" })}
            onClick={() => {
              onChange("");
              onCommit?.();
              setQuery("");
              setOpen(false);
            }}
            style={{
              position: "absolute",
              right: "var(--space-2)",
              top: "50%",
              transform: "translateY(-50%)",
              border: 0,
              background: "transparent",
              color: "var(--text-secondary)",
              cursor: "pointer",
              padding: 0,
            }}
          >
            ×
          </button>
```

- frontend/src/components/ChannelTypeCombobox.tsx:L173; class=absent; handlers={"onMouseDown":{"raw":"{(e) => e.preventDefault()}","inline":true,"name":null},"onClick":{"raw":"{() => {\n                  onChange(channel.platform);\n                  onCommit?.();\n                  setOpen(false);\n                  setQuery(\"\");\n                }}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style={{
                  display: "block",
                  width: "100%",
                  textAlign: "left",
                  padding: "var(--space-2) var(--space-3)",
                  border: 0,
                  background: channel.platform === value ? "var(--bg-muted)" : "transparent",
                  color: "var(--text-primary)",
                  cursor: "pointer",
                }}

```tsx
<button
                key={channel.platform}
                type="button"
                role="option"
                aria-selected={channel.platform === value}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => {
                  onChange(channel.platform);
                  onCommit?.();
                  setOpen(false);
                  setQuery("");
                }}
                style={{
                  display: "block",
                  width: "100%",
                  textAlign: "left",
                  padding: "var(--space-2) var(--space-3)",
                  border: 0,
                  background: channel.platform === value ? "var(--bg-muted)" : "transparent",
                  color: "var(--text-primary)",
                  cursor: "pointer",
                }}
              >
                <strong>{channel.display_name}</strong>
                <span style={{ marginLeft: "var(--space-2)", color: "var(--text-secondary)" }}>
                  {channel.platform} · {channel.connection_type}
                </span>
              </button>
```

- frontend/src/components/CountryCombobox.tsx:L119; class=absent; handlers={"onClick":{"raw":"{() => {\n              onChange(\"\");\n              onCommit?.();\n              setQuery(\"\");\n              setOpen(false);\n            }}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style={{
              position: "absolute",
              right: "var(--space-2)",
              top: "50%",
              transform: "translateY(-50%)",
              border: 0,
              background: "transparent",
              color: "var(--text-secondary)",
              cursor: "pointer",
              padding: 0,
            }}

```tsx
<button
            type="button"
            aria-label={t("common.clear", { defaultValue: "Clear" })}
            onClick={() => {
              onChange("");
              onCommit?.();
              setQuery("");
              setOpen(false);
            }}
            style={{
              position: "absolute",
              right: "var(--space-2)",
              top: "50%",
              transform: "translateY(-50%)",
              border: 0,
              background: "transparent",
              color: "var(--text-secondary)",
              cursor: "pointer",
              padding: 0,
            }}
          >
            ×
          </button>
```

- frontend/src/components/CountryCombobox.tsx:L172; class=absent; handlers={"onMouseDown":{"raw":"{(e) => e.preventDefault()}","inline":true,"name":null},"onClick":{"raw":"{() => {\n                  onChange(country.code);\n                  onCommit?.();\n                  setOpen(false);\n                  setQuery(\"\");\n                }}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style={{
                  display: "block",
                  width: "100%",
                  textAlign: "left",
                  padding: "var(--space-2) var(--space-3)",
                  border: 0,
                  background: country.code === value ? "var(--bg-muted)" : "transparent",
                  color: "var(--text-primary)",
                  cursor: "pointer",
                }}

```tsx
<button
                key={country.code}
                type="button"
                role="option"
                aria-selected={country.code === value}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => {
                  onChange(country.code);
                  onCommit?.();
                  setOpen(false);
                  setQuery("");
                }}
                style={{
                  display: "block",
                  width: "100%",
                  textAlign: "left",
                  padding: "var(--space-2) var(--space-3)",
                  border: 0,
                  background: country.code === value ? "var(--bg-muted)" : "transparent",
                  color: "var(--text-primary)",
                  cursor: "pointer",
                }}
              >
                <strong>{country.name}</strong>
                <span style={{ marginLeft: "var(--space-2)", color: "var(--text-secondary)" }}>
                  {country.code} · {country.dial_code}
                </span>
              </button>
```

- frontend/src/components/DataTable.tsx:L197; class=dynamic; handlers={"onClick":{"raw":"{() => handleSort(col.key)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                    type="button"
                    className={[
                      'comp-table__sort-btn',
                      sortKey === col.key ? 'comp-table__sort-btn--active' : '',
                    ].filter(Boolean).join(' ')}
                    onClick={() => handleSort(col.key)}
                  >
                    {col.header}
                    <span className="comp-table__sort-icon" aria-hidden="true">
                      {sortKey === col.key ? (
                        sortDir === 'asc'
                          ? <TABLE_ICONS.sortAsc size={12} />
                          : <TABLE_ICONS.sortDesc size={12} />
                      ) : (
                        <TABLE_ICONS.sortAsc size={12} />
                      )}
                    </span>
                  </button>
```

- frontend/src/components/DesktopShell.tsx:L68; class=dynamic; handlers={"onClick":{"raw":"{onToggle}","inline":false,"name":"onToggle"}}; form=null; type=null; disabled=null; style=null

```tsx
<button
        className={`sidebar-item sidebar-accordion-btn${isActive ? " active" : ""}`}
        onClick={onToggle}
        aria-expanded={isOpen}
      >
        <span className="sidebar-icon">{icon}</span>
        <span className="sidebar-label">{label}</span>
        {isExpanded && (
          <span className={`sidebar-caret${isOpen ? " open" : ""}`}>
            <NAV_ICONS.chevronDown size={ICON.sm} />
          </span>
        )}
      </button>
```

- frontend/src/components/DesktopShell.tsx:L415; class=static; handlers={"onClick":{"raw":"{() => setDrawerOpen(true)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button
        className="avatar-btn"
        onClick={() => setDrawerOpen(true)}
        aria-label={t("nav.openUserMenu")}
        data-tooltip={t("nav.openUserMenu")}
      >
        {user?.email ? user.email[0].toUpperCase() : <NAV_ICONS.logout size={18} />}
      </button>
```

- frontend/src/components/DesktopShell.tsx:L442; class=static; handlers={"onClick":{"raw":"{() => setDrawerOpen(false)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button
            className="user-drawer-close"
            onClick={() => setDrawerOpen(false)}
            aria-label={t("common.close")}
            data-tooltip={t("common.close")}
          >
            <NAV_ICONS.close size={ICON.md} aria-hidden="true" />
          </button>
```

- frontend/src/components/DesktopShell.tsx:L455; class=static; handlers={"onClick":{"raw":"{() => { setDrawerOpen(false); navigate(\"/account/settings\"); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button
            className="user-drawer-action"
            onClick={() => { setDrawerOpen(false); navigate("/account/settings"); }}
          >
            <ACCOUNT_ICONS.profile size={ICON.md} aria-hidden="true" />
            <span>{t("nav.accountSettings")}</span>
          </button>
```

- frontend/src/components/DesktopShell.tsx:L465; class=static; handlers={"onClick":{"raw":"{() => changeTheme(theme === \"light\" ? \"dark\" : \"light\")}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button
            className="user-drawer-action"
            onClick={() => changeTheme(theme === "light" ? "dark" : "light")}
          >
            {theme === "light"
              ? <THEME_ICONS.light size={ICON.md} aria-hidden="true" />
              : <THEME_ICONS.dark size={ICON.md} aria-hidden="true" />}
            <span>{theme === "light" ? t("nav.switchToDark") : t("nav.switchToLight")}</span>
          </button>
```

- frontend/src/components/DesktopShell.tsx:L475; class=static; handlers={"onClick":{"raw":"{() => changeLanguage(locale === \"ja\" ? \"en\" : \"ja\")}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button
            className="user-drawer-action"
            onClick={() => changeLanguage(locale === "ja" ? "en" : "ja")}
          >
            <GlobeIcon size={ICON.md} aria-hidden="true" />
            <span>{locale === "ja" ? t("language.en") : t("language.ja")}</span>
          </button>
```

- frontend/src/components/DesktopShell.tsx:L483; class=static; handlers={"onClick":{"raw":"{() => { setDrawerOpen(false); setShowLogoutConfirm(true); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button
            className="user-drawer-action user-drawer-action--danger"
            onClick={() => { setDrawerOpen(false); setShowLogoutConfirm(true); }}
          >
            <NAV_ICONS.logout size={ICON.md} aria-hidden="true" />
            <span>{t("nav.signOut")}</span>
          </button>
```

- frontend/src/components/GoogleCalendarStatusBar.tsx:L129; class=absent; handlers={"onClick":{"raw":"{handleReconnect}","inline":false,"name":"handleReconnect"}}; form=null; type=null; disabled={reconnecting}; style={{
            marginLeft: "var(--space-3)",
            padding: "var(--space-1) var(--space-3)",
            background: "var(--calendar-status-error-text)",
            color: "var(--on-accent)",
            border: "none",
            borderRadius: "var(--radius-sm)",
            cursor: "pointer",
            fontSize: "var(--font-sm)",
            fontWeight: "var(--font-weight-medium)",
          }}

```tsx
<button
          onClick={handleReconnect}
          disabled={reconnecting}
          style={{
            marginLeft: "var(--space-3)",
            padding: "var(--space-1) var(--space-3)",
            background: "var(--calendar-status-error-text)",
            color: "var(--on-accent)",
            border: "none",
            borderRadius: "var(--radius-sm)",
            cursor: "pointer",
            fontSize: "var(--font-sm)",
            fontWeight: "var(--font-weight-medium)",
          }}
        >
          {reconnecting ? t("common.saving") : t("schedule.statusReconnect")}
        </button>
```

- frontend/src/components/HeaderButton.tsx:L48; class=dynamic; handlers={"onClick":{"raw":"{onClick}","inline":false,"name":"onClick"}}; form=null; type="button"; disabled={disabled}; style=null

```tsx
<button
      type="button"
      className={VARIANT_CLASS[variant]}
      onClick={onClick}
      disabled={disabled}
      aria-label={"aria-label" in props ? props["aria-label"] : undefined}
      data-tooltip={"data-tooltip" in props ? props["data-tooltip"] : undefined}
      data-testid={"data-testid" in props ? props["data-testid"] : undefined}
    >
      {children}
    </button>
```

- frontend/src/components/InventorySearchBar.tsx:L301; class=absent; handlers={"onClick":{"raw":"{() => setOp(\"and\")}","inline":true,"name":null}}; form=null; type="button"; disabled={opToggleDisabled}; style={{
              padding: "var(--space-1) var(--space-10px)",
              border: "none",
              background: op === "and" ? "var(--accent-bg)" : "transparent",
              color: op === "and" ? "var(--on-accent)" : "inherit",
              cursor: opToggleDisabled ? "not-allowed" : "pointer",
            }}

```tsx
<button
            type="button"
            onClick={() => setOp("and")}
            disabled={opToggleDisabled}
            aria-pressed={op === "and"}
            data-testid={`${testIdPrefix}-op-and`}
            style={{
              padding: "var(--space-1) var(--space-10px)",
              border: "none",
              background: op === "and" ? "var(--accent-bg)" : "transparent",
              color: op === "and" ? "var(--on-accent)" : "inherit",
              cursor: opToggleDisabled ? "not-allowed" : "pointer",
            }}
          >
            {t("inventory.search.opAnd")}
          </button>
```

- frontend/src/components/InventorySearchBar.tsx:L317; class=absent; handlers={"onClick":{"raw":"{() => setOp(\"or\")}","inline":true,"name":null}}; form=null; type="button"; disabled={opToggleDisabled}; style={{
              padding: "var(--space-1) var(--space-10px)",
              border: "none",
              background: op === "or" ? "var(--accent-bg)" : "transparent",
              color: op === "or" ? "var(--on-accent)" : "inherit",
              cursor: opToggleDisabled ? "not-allowed" : "pointer",
            }}

```tsx
<button
            type="button"
            onClick={() => setOp("or")}
            disabled={opToggleDisabled}
            aria-pressed={op === "or"}
            data-testid={`${testIdPrefix}-op-or`}
            style={{
              padding: "var(--space-1) var(--space-10px)",
              border: "none",
              background: op === "or" ? "var(--accent-bg)" : "transparent",
              color: op === "or" ? "var(--on-accent)" : "inherit",
              cursor: opToggleDisabled ? "not-allowed" : "pointer",
            }}
          >
            {t("inventory.search.opOr")}
          </button>
```

- frontend/src/components/MergeLeadModal.tsx:L243; class=absent; handlers={"onClick":{"raw":"{onCancel}","inline":false,"name":"onCancel"}}; form=null; type="button"; disabled=null; style=null

```tsx
<button type="button" onClick={onCancel}>
                {t("common.cancel")}
              </button>
```

- frontend/src/components/MergeLeadModal.tsx:L302; class=absent; handlers={"onClick":{"raw":"{() => setStage(\"select\")}","inline":true,"name":null}}; form=null; type="button"; disabled={submitting}; style=null

```tsx
<button
                type="button"
                onClick={() => setStage("select")}
                disabled={submitting}
              >
                {t("common.back")}
              </button>
```

- frontend/src/components/MobileShell.tsx:L230; class=static; handlers={"onClick":{"raw":"{() => changeTheme(theme === \"light\" ? \"dark\" : \"light\")}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button
            className="mobile-menu-action"
            onClick={() => changeTheme(theme === "light" ? "dark" : "light")}
          >
            {theme === "light" ? (
              <THEME_ICONS.light size={ICON.md} aria-hidden="true" />
            ) : (
              <THEME_ICONS.dark size={ICON.md} aria-hidden="true" />
            )}
            <span>
              {theme === "light"
                ? t("nav.switchToDark")
                : t("nav.switchToLight")}
            </span>
          </button>
```

- frontend/src/components/MobileShell.tsx:L246; class=static; handlers={"onClick":{"raw":"{() => changeLanguage(locale === \"ja\" ? \"en\" : \"ja\")}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button
            className="mobile-menu-action"
            onClick={() => changeLanguage(locale === "ja" ? "en" : "ja")}
          >
            <GlobeIcon size={ICON.md} aria-hidden="true" />
            <span>{locale === "ja" ? t("language.en") : t("language.ja")}</span>
          </button>
```

- frontend/src/components/MobileShell.tsx:L254; class=static; handlers={"onClick":{"raw":"{() => {\n              setMoreSheetOpen(false);\n              setShowLogoutConfirm(true);\n            }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button
            className="mobile-menu-action mobile-menu-action--danger"
            onClick={() => {
              setMoreSheetOpen(false);
              setShowLogoutConfirm(true);
            }}
          >
            <NAV_ICONS.logout size={ICON.md} aria-hidden="true" />
            <span>{t("nav.signOut")}</span>
          </button>
```

- frontend/src/components/MobileShell.tsx:L317; class=static; handlers={"onClick":{"raw":"{() => setMoreSheetOpen(true)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button
          className="mobile-tab"
          onClick={() => setMoreSheetOpen(true)}
          aria-label={t("nav.menu")}
          aria-expanded={moreSheetOpen}
        >
          <NAV_ICONS.more size={ICON.base} aria-hidden="true" />
        </button>
```

- frontend/src/components/NavDropdown.tsx:L47; class=dynamic; handlers={"onClick":{"raw":"{() => setOpen((v) => !v)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button
        className={`nav-dropdown-toggle ${isActive ? "active" : ""}`}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        {label}
        <NAV_ICONS.chevronDown size={12} aria-hidden="true" />
      </button>
```

- frontend/src/components/SubMenu.tsx:L96; class=dynamic; handlers={"onClick":{"raw":"{() => !item.disabled && onChange?.(item.key)}","inline":true,"name":null}}; form=null; type="button"; disabled={item.disabled}; style=null

```tsx
<button
                key={item.key}
                type="button"
                className={[
                  "comp-subnav__item",
                  isActive      && "comp-subnav__item--active",
                  item.disabled && "comp-subnav__item--disabled",
                ]
                  .filter(Boolean)
                  .join(" ")}
                onClick={() => !item.disabled && onChange?.(item.key)}
                disabled={item.disabled}
                aria-current={isActive ? "page" : undefined}
              >
                {item.icon && (
                  <span className="comp-subnav__icon">{item.icon}</span>
                )}
                <span className="comp-subnav__label">{item.label}</span>
                {item.badge !== undefined && (
                  <span className="comp-subnav__badge">{item.badge}</span>
                )}
              </button>
```

- frontend/src/components/Tabs.tsx:L74; class=dynamic; handlers={"onClick":{"raw":"{() => {\n              if (!item.disabled) onChange(item.key);\n            }}","inline":true,"name":null}}; form=null; type="button"; disabled={item.disabled}; style=null

```tsx
<button
            key={item.key}
            role="tab"
            type="button"
            aria-selected={isActive}
            disabled={item.disabled}
            className={[
              "comp-tabs__tab",
              isActive ? "comp-tabs__tab--active" : "",
              item.disabled ? "comp-tabs__tab--disabled" : "",
            ]
              .filter(Boolean)
              .join(" ")}
            onClick={() => {
              if (!item.disabled) onChange(item.key);
            }}
          >
            {item.icon != null && (
              <span className="comp-tabs__icon" aria-hidden="true">
                {item.icon}
              </span>
            )}
            <span className="comp-tabs__label">{item.label}</span>
            {item.count !== undefined && (
              <Badge variant="neutral" appearance="soft" size="sm">
                {String(item.count)}
              </Badge>
            )}
          </button>
```

- frontend/src/components/loading/Drawer.tsx:L32; class=static; handlers={"onClick":{"raw":"{onClose}","inline":false,"name":"onClose"}}; form=null; type=null; disabled=null; style=null

```tsx
<button onClick={onClose} aria-label="Close" className="sa-drawer__close">
            <CloseIcon className="sa-drawer__close-icon" />
          </button>
```

- frontend/src/features/tcg-analysis-review/ItemComparison.tsx:L33; class=static; handlers={"onClick":{"raw":"{() => onJumpToSourceLine(line)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button className="line-jump" type="button" onClick={() => onJumpToSourceLine(line)}>{lineSpan}</button>
```

- frontend/src/features/tcg-analysis-review/ItemComparison.tsx:L33; class=absent; handlers={"onClick":{"raw":"{onCorrectionSave}","inline":false,"name":"onCorrectionSave"}}; form=null; type="button"; disabled={true}; style=null

```tsx
<button type="button" disabled={true} onClick={onCorrectionSave}>{correctionState === 'saving' ? t('tcgAnalysisReview.saving') : t('tcgAnalysisReview.saveCorrected')}</button>
```

- frontend/src/features/tcg-analysis-review/ItemComparison.tsx:L33; class=absent; handlers={"onClick":{"raw":"{onNoteSave}","inline":false,"name":"onNoteSave"}}; form=null; type="button"; disabled={true}; style=null

```tsx
<button type="button" disabled={true} onClick={onNoteSave}>{noteState === 'saving' ? t('tcgAnalysisReview.saving') : t('tcgAnalysisReview.saveMemo')}</button>
```

- frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:L254; class=absent; handlers={"onClick":{"raw":"{checkDuplicates}","inline":false,"name":"checkDuplicates"}}; form=null; type="button"; disabled={!required || status === 'checking' || status === 'saving'}; style=null

```tsx
<button
              type="button"
              disabled={!required || status === 'checking' || status === 'saving'}
              onClick={checkDuplicates}
            >
              {status === 'checking' ? '確認中…' : '重複候補を確認'}
            </button>
```

- frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:L261; class=absent; handlers={"onClick":{"raw":"{save}","inline":false,"name":"save"}}; form=null; type="button"; disabled={!required || (candidates.length > 0 && !confirmed) || status === 'saving'}; style=null

```tsx
<button
              type="button"
              disabled={!required || (candidates.length > 0 && !confirmed) || status === 'saving'}
              onClick={save}
            >
              {status === 'saving' ? '登録中…' : '商品マスタに登録'}
            </button>
```

- frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:L346; class=absent; handlers={"onClick":{"raw":"{search}","inline":false,"name":"search"}}; form=null; type="button"; disabled={!query.trim() || searching}; style=null

```tsx
<button type="button" disabled={!query.trim() || searching} onClick={search}>
          {searching ? '検索中…' : 'マスタを検索'}
        </button>
```

- frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:L358; class=absent; handlers={"onClick":{"raw":"{() => setSelected(c === selected ? undefined : c)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button type="button" onClick={() => setSelected(c === selected ? undefined : c)}>
            <strong>{c.product_id}</strong> {c.japanese_title}
          </button>
```

- frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:L372; class=absent; handlers={"onClick":{"raw":"{addKeyword}","inline":false,"name":"addKeyword"}}; form=null; type="button"; disabled={addStatus === 'saving'}; style=null

```tsx
<button type="button" disabled={addStatus === 'saving'} onClick={addKeyword}>
              {addStatus === 'saving' ? '追記中…' : 'キーワードを追記'}
            </button>
```

- frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:L479; class=absent; handlers={"onClick":{"raw":"{search}","inline":false,"name":"search"}}; form=null; type="button"; disabled={!query.trim() || searching}; style=null

```tsx
<button type="button" disabled={!query.trim() || searching} onClick={search}>
          {searching ? t('superAdmin.supplierQuality.productAssign.searching') : t('superAdmin.supplierQuality.productAssign.searchBtn')}
        </button>
```

- frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:L491; class=absent; handlers={"onClick":{"raw":"{() => setSelected(c === selected ? undefined : c)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button type="button" onClick={() => setSelected(c === selected ? undefined : c)}>
            <strong>{c.product_id}</strong>  {c.japanese_title}
          </button>
```

- frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:L499; class=absent; handlers={"onClick":{"raw":"{changeProduct}","inline":false,"name":"changeProduct"}}; form=null; type="button"; disabled={!selected || busy}; style=null

```tsx
<button type="button" disabled={!selected || busy} onClick={changeProduct}>
          {status === 'changing' ? t('superAdmin.supplierQuality.productAssign.changing') : t('superAdmin.supplierQuality.productAssign.changeBtn')}
        </button>
```

- frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:L502; class=absent; handlers={"onClick":{"raw":"{markConfirmed}","inline":false,"name":"markConfirmed"}}; form=null; type="button"; disabled={!item.system.product_uuid || busy}; style=null

```tsx
<button type="button" disabled={!item.system.product_uuid || busy} onClick={markConfirmed}>
          {status === 'confirming' ? t('superAdmin.supplierQuality.productAssign.confirming') : t('superAdmin.supplierQuality.productAssign.confirmBtn')}
        </button>
```

- frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:L529; class=absent; handlers={"onClick":{"raw":"{onClose}","inline":false,"name":"onClose"}}; form=null; type="button"; disabled=null; style=null

```tsx
<button type="button" onClick={onClose} aria-label="閉じる">×</button>
```

- frontend/src/features/tcg-analysis-review/SourceRawPane.tsx:L30; class=absent; handlers={}; form=null; type="submit"; disabled=null; style=null

```tsx
<button type="submit">移動</button>
```

- frontend/src/features/tcg-analysis-review/SourceRawPane.tsx:L30; class=absent; handlers={"onClick":{"raw":"{() => moveToMatch(activeMatch - 1)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button type="button" onClick={() => moveToMatch(activeMatch - 1)}>前へ</button>
```

- frontend/src/features/tcg-analysis-review/SourceRawPane.tsx:L30; class=absent; handlers={"onClick":{"raw":"{() => moveToMatch(activeMatch + 1)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button type="button" onClick={() => moveToMatch(activeMatch + 1)}>次へ</button>
```

- frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx:L92; class=static; handlers={"onClick":{"raw":"{onBack}","inline":false,"name":"onBack"}}; form=null; type="button"; disabled=null; style=null

```tsx
<button type="button" className="supplier-detail-back" onClick={onBack}>{t("superAdmin.supplierQuality.backToList")}</button>
```

- frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx:L119; class=static; handlers={"onClick":{"raw":"{() => setMasterDrawerItem(item)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button type="button" className="supplier-detail-correct-btn" onClick={() => setMasterDrawerItem(item)}>{t("superAdmin.supplierQuality.correctPhase3")}</button>
```

- frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx:L125; class=static; handlers={"onClick":{"raw":"{() => setDisplayCount((c) => c + PAGE_SIZE)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button type="button" className="supplier-detail-back" onClick={() => setDisplayCount((c) => c + PAGE_SIZE)}>
                    {t("superAdmin.supplierQuality.loadMore", { remaining })}
                  </button>
```

- frontend/src/features/tcg-analysis-review/components/DataList.tsx:L8; class=static; handlers={"onClick":{"raw":"{() => onRowSelect?.(row)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button className="data-list-row" role="listitem" type="button" key={getRowKey(row)} onClick={() => onRowSelect?.(row)}>{visibleColumns.map((column) => <span key={column.id} style={{ minWidth: column.minWidth }}>{renderCell(row, column)}</span>)}</button>
```

- frontend/src/features/tcg-distribution/DistributionPreview.tsx:L121; class=static; handlers={"onClick":{"raw":"{() => setShowConfirm(true)}","inline":true,"name":null}}; form=null; type="button"; disabled={running || preview.output_count === 0}; style=null

```tsx
<button
            type="button"
            className="dist-btn dist-btn--primary"
            onClick={() => setShowConfirm(true)}
            disabled={running || preview.output_count === 0}
            aria-label={t("distributionTarget.preview.runAllLabel")}
          >
            <INBOX_ACTION_ICONS.send size={16} aria-hidden="true" />
            {running ? t("distributionTarget.preview.running") : t("distributionTarget.preview.runAll")}
          </button>
```

- frontend/src/features/tcg-distribution/DistributionPreview.tsx:L174; class=static; handlers={"onClick":{"raw":"{() => setShowConfirm(false)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                type="button"
                className="dist-btn dist-btn--ghost"
                onClick={() => setShowConfirm(false)}
              >
                {t("common.cancel")}
              </button>
```

- frontend/src/features/tcg-distribution/DistributionPreview.tsx:L181; class=static; handlers={"onClick":{"raw":"{handleRunAll}","inline":false,"name":"handleRunAll"}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                type="button"
                className="dist-btn dist-btn--primary"
                onClick={handleRunAll}
              >
                {t("distributionTarget.preview.runAll")}
              </button>
```

- frontend/src/features/tcg-distribution/DistributionTargetForm.tsx:L135; class=static; handlers={"onClick":{"raw":"{onClose}","inline":false,"name":"onClose"}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
            type="button"
            className="dist-drawer-close"
            onClick={onClose}
            aria-label={t("common.close")}
          >
            <NAV_ICONS.close size={20} aria-hidden="true" />
          </button>
```

- frontend/src/features/tcg-distribution/DistributionTargetForm.tsx:L156; class=static; handlers={"onClick":{"raw":"{handleCopy}","inline":false,"name":"handleCopy"}}; form=null; type="button"; disabled=null; style={{ fontSize: "var(--font-xs)", padding: "2px var(--space-2)" }}

```tsx
<button
                type="button"
                className="dist-btn dist-btn--ghost"
                style={{ fontSize: "var(--font-xs)", padding: "2px var(--space-2)" }}
                onClick={handleCopy}
              >
                {copied ? t("distributionTarget.form.copied") : t("distributionTarget.form.copy")}
              </button>
```

- frontend/src/features/tcg-distribution/DistributionTargetForm.tsx:L248; class=static; handlers={"onClick":{"raw":"{onClose}","inline":false,"name":"onClose"}}; form=null; type="button"; disabled=null; style=null

```tsx
<button type="button" className="dist-btn dist-btn--ghost" onClick={onClose}>
            {t("common.cancel")}
          </button>
```

- frontend/src/features/tcg-distribution/DistributionTargetForm.tsx:L251; class=static; handlers={"onClick":{"raw":"{handleSave}","inline":false,"name":"handleSave"}}; form=null; type="button"; disabled={saving}; style=null

```tsx
<button
            type="button"
            className="dist-btn dist-btn--primary"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? t("common.saving") : t("common.save")}
          </button>
```

- frontend/src/features/tcg-distribution/DistributionTargetList.tsx:L157; class=static; handlers={"onClick":{"raw":"{() => setEditTarget(target)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                        type="button"
                        className="dist-btn dist-btn--ghost"
                        onClick={() => setEditTarget(target)}
                        title={t("common.edit")}
                        aria-label={`${t("common.edit")}: ${target.name}`}
                      >
                        <SCHEDULE_POPOVER_ICONS.edit size={14} aria-hidden="true" />
                        {t("common.edit")}
                      </button>
```

- frontend/src/features/tcg-distribution/DistributionTargetList.tsx:L170; class=static; handlers={"onClick":{"raw":"{() => setConfirm({ type: \"run\", target })}","inline":true,"name":null}}; form=null; type="button"; disabled={running === target.id}; style=null

```tsx
<button
                            type="button"
                            className="dist-btn dist-btn--primary"
                            onClick={() => setConfirm({ type: "run", target })}
                            disabled={running === target.id}
                            title={t("distributionTarget.list.runBtn")}
                            aria-label={`${t("distributionTarget.list.runBtn")}: ${target.name}`}
                          >
                            <INBOX_ACTION_ICONS.send size={14} aria-hidden="true" />
                            {running === target.id
                              ? t("distributionTarget.preview.running")
                              : t("distributionTarget.list.runBtn")}
                          </button>
```

- frontend/src/features/tcg-distribution/DistributionTargetList.tsx:L184; class=static; handlers={"onClick":{"raw":"{() => setConfirm({ type: \"disable\", target })}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                            type="button"
                            className="dist-btn dist-btn--danger"
                            onClick={() => setConfirm({ type: "disable", target })}
                            title={t("distributionTarget.list.disableBtn")}
                            aria-label={`${t("distributionTarget.list.disableBtn")}: ${target.name}`}
                          >
                            {t("distributionTarget.list.disableBtn")}
                          </button>
```

- frontend/src/features/tcg-distribution/DistributionTargetList.tsx:L222; class=static; handlers={"onClick":{"raw":"{() => setConfirm(null)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                    type="button"
                    className="dist-btn dist-btn--ghost"
                    onClick={() => setConfirm(null)}
                  >
                    {t("common.cancel")}
                  </button>
```

- frontend/src/features/tcg-distribution/DistributionTargetList.tsx:L229; class=static; handlers={"onClick":{"raw":"{() => handleRun(confirm.target)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                    type="button"
                    className="dist-btn dist-btn--primary"
                    onClick={() => handleRun(confirm.target)}
                  >
                    {t("distributionTarget.list.runBtn")}
                  </button>
```

- frontend/src/features/tcg-distribution/DistributionTargetList.tsx:L249; class=static; handlers={"onClick":{"raw":"{() => setConfirm(null)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                    type="button"
                    className="dist-btn dist-btn--ghost"
                    onClick={() => setConfirm(null)}
                  >
                    {t("common.cancel")}
                  </button>
```

- frontend/src/features/tcg-distribution/DistributionTargetList.tsx:L256; class=static; handlers={"onClick":{"raw":"{() => handleDisable(confirm.target)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                    type="button"
                    className="dist-btn dist-btn--danger"
                    onClick={() => handleDisable(confirm.target)}
                  >
                    {t("distributionTarget.list.disableBtn")}
                  </button>
```

- frontend/src/features/tcg-distribution/DistributionWorkspace.tsx:L53; class=static; handlers={"onClick":{"raw":"{() => setShowNewForm(true)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                type="button"
                className="dist-btn dist-btn--primary"
                onClick={() => setShowNewForm(true)}
                aria-label={t("distributionTarget.page.newBtn")}
              >
                <NAV_ICONS.add size={16} aria-hidden="true" />
                {t("distributionTarget.page.newBtn")}
              </button>
```

- frontend/src/pages/admin/ChannelMastersPage.tsx:L97; class=absent; handlers={"onClick":{"raw":"{() => handleDelete(ch.id)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                        type="button"
                        onClick={() => handleDelete(ch.id)}
                        aria-label={t("channelMasters.deleteAriaLabel", { name: ch.display_name })}
                      >
                        {t("channelMasters.delete")}
                      </button>
```

- frontend/src/pages/admin/ChannelMastersPage.tsx:L131; class=absent; handlers={"onClick":{"raw":"{handleAdd}","inline":false,"name":"handleAdd"}}; form=null; type="button"; disabled={saving || !newPlatform.trim() || !newDisplayName.trim()}; style=null

```tsx
<button
              type="button"
              onClick={handleAdd}
              disabled={saving || !newPlatform.trim() || !newDisplayName.trim()}
              aria-label={t("channelMasters.add")}
            >
              {saving ? t("channelMasters.saving") : t("channelMasters.add")}
            </button>
```

- frontend/src/pages/channels/ChannelsPage.tsx:L347; class=absent; handlers={"onClick":{"raw":"{() => setBanner(null)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style={{
              float: "right",
              background: "transparent",
              border: "none",
              cursor: "pointer",
              fontSize: "var(--font-md)",
              lineHeight: 1,
            }}

```tsx
<button
            type="button"
            onClick={() => setBanner(null)}
            style={{
              float: "right",
              background: "transparent",
              border: "none",
              cursor: "pointer",
              fontSize: "var(--font-md)",
              lineHeight: 1,
            }}
            aria-label={t("channels.close")}
          >
            ×
          </button>
```

- frontend/src/pages/companies/CompaniesPage.tsx:L439; class=dynamic; handlers={"onClick":{"raw":"{() => setActiveTab(\"basic\")}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className={`tab ${activeTab === "basic" ? "active" : ""}`} onClick={() => setActiveTab("basic")}>{t("companies.basicInfo")}</button>
```

- frontend/src/pages/companies/CompaniesPage.tsx:L440; class=dynamic; handlers={"onClick":{"raw":"{() => setActiveTab(\"billing\")}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className={`tab ${activeTab === "billing" ? "active" : ""}`} onClick={() => setActiveTab("billing")}>{t("companies.billing")}</button>
```

- frontend/src/pages/companies/CompaniesPage.tsx:L441; class=dynamic; handlers={"onClick":{"raw":"{() => setActiveTab(\"delivery\")}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button className={`tab ${activeTab === "delivery" ? "active" : ""}`} onClick={() => setActiveTab("delivery")}>{t("companies.delivery")}</button>
```

- frontend/src/pages/contacts/ContactEditPage.tsx:L202; class=absent; handlers={}; form=null; type="button"; disabled=true; style={{ opacity: "var(--opacity-disabled)", cursor: "not-allowed" }}

```tsx
<button type="button" disabled style={{ opacity: "var(--opacity-disabled)", cursor: "not-allowed" }}>
                  {t("contacts.mergeAsDuplicate")}
                </button>
```

- frontend/src/pages/dashboard/DashboardPage.tsx:L423; class=dynamic; handlers={"onClick":{"raw":"{() => setViewMode(\"management\")}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                  type="button"
                  className={`db-tab${viewMode === "management" ? " active" : ""}`}
                  onClick={() => setViewMode("management")}
                >
                  {t("funnel.viewManagement")}
                </button>
```

- frontend/src/pages/dashboard/DashboardPage.tsx:L430; class=dynamic; handlers={"onClick":{"raw":"{() => setViewMode(\"player\")}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                  type="button"
                  className={`db-tab${viewMode === "player" ? " active" : ""}`}
                  onClick={() => setViewMode("player")}
                >
                  {t("funnel.viewPlayer")}
                </button>
```

- frontend/src/pages/dashboard/DashboardPage.tsx:L543; class=static; handlers={"onClick":{"raw":"{() => navigate(\"/goals/settings\")}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button
              className="db-set-goals-btn"
              onClick={() => navigate("/goals/settings")}
            >
              {t("dashboard.setGoals")}
              <ArrowRightIcon aria-hidden="true" size={14} />
            </button>
```

- frontend/src/pages/dashboard/FollowUpsPage.tsx:L148; class=dynamic; handlers={"onClick":{"raw":"{() => { setFilter(f.key); setPage(1); }}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                key={f.key}
                type="button"
                className={`fu-filter-chip${filter === f.key ? " active" : ""} fu-chip--${f.key}`}
                onClick={() => { setFilter(f.key); setPage(1); }}
              >
                {f.label}
                <span className="fu-chip-count">{counts[f.key]}</span>
              </button>
```

- frontend/src/pages/dashboard/FunnelReasonsPage.tsx:L41; class=dynamic; handlers={"onClick":{"raw":"{() => setReasonType(\"won\")}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
          type="button"
          className={`frr-tab${reasonType === "won" ? " active" : ""}`}
          onClick={() => setReasonType("won")}
        >
          {t("funnel.won")}
        </button>
```

- frontend/src/pages/dashboard/FunnelReasonsPage.tsx:L48; class=dynamic; handlers={"onClick":{"raw":"{() => setReasonType(\"lost\")}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
          type="button"
          className={`frr-tab${reasonType === "lost" ? " active" : ""}`}
          onClick={() => setReasonType("lost")}
        >
          {t("funnel.lost")}
        </button>
```

- frontend/src/pages/dashboard/FunnelSection.tsx:L107; class=static; handlers={"onClick":{"raw":"{(e) => {\n              e.stopPropagation();\n              onClick();\n            }}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
            type="button"
            className="fn-link-btn"
            onClick={(e) => {
              e.stopPropagation();
              onClick();
            }}
          >
            {t(actionLabel)} →
          </button>
```

- frontend/src/pages/dashboard/FunnelSection.tsx:L256; class=static; handlers={"onClick":{"raw":"{(e) => {\n              e.stopPropagation();\n              onOpen();\n            }}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
            type="button"
            className="fn-link-btn"
            onClick={(e) => {
              e.stopPropagation();
              onOpen();
            }}
          >
            {t(VIEW_ALL_LABEL)} →
          </button>
```

- frontend/src/pages/dashboard/FunnelSection.tsx:L341; class=static; handlers={"onClick":{"raw":"{(e) => {\n                e.stopPropagation();\n                onOpen();\n              }}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
              type="button"
              className="fn-link-btn"
              onClick={(e) => {
                e.stopPropagation();
                onOpen();
              }}
            >
              {t(VIEW_ALL_LABEL)} →
            </button>
```

- frontend/src/pages/dashboard/FunnelSection.tsx:L370; class=static; handlers={"onClick":{"raw":"{(e) => {\n                e.stopPropagation();\n                onOpen();\n              }}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
              type="button"
              className="fn-link-btn"
              onClick={(e) => {
                e.stopPropagation();
                onOpen();
              }}
            >
              {t(VIEW_ALL_LABEL)} →
            </button>
```

- frontend/src/pages/dashboard/FunnelSection.tsx:L413; class=static; handlers={"onClick":{"raw":"{(e) => {\n              e.stopPropagation();\n              onOpen();\n            }}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
            type="button"
            className="fn-link-btn"
            onClick={(e) => {
              e.stopPropagation();
              onOpen();
            }}
          >
            {t(VIEW_ALL_LABEL)} →
          </button>
```

- frontend/src/pages/design-system/DesignSystemPage.tsx:L135; class=dynamic; handlers={"onClick":{"raw":"{() => setActiveTab(id)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button
                key={id}
                className={`tab-item${activeTab === id ? " active" : ""}`}
                onClick={() => setActiveTab(id)}
              >
                {id === "tab1" ? "すべて" : id === "tab2" ? "進行中" : "完了"}
              </button>
```

- frontend/src/pages/design-system/DesignSystemPage.tsx:L151; class=dynamic; handlers={"onClick":{"raw":"{() => setActivePill(p)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button
                key={p}
                className={`filter-pill${activePill === p ? " active" : ""}`}
                onClick={() => setActivePill(p)}
              >
                {p === "all" ? "すべて" : p === "active" ? "アクティブ" : p === "pending" ? "保留中" : "完了"}
              </button>
```

- frontend/src/pages/design-system/DesignSystemPage.tsx:L170; class=static; handlers={}; form=null; type=null; disabled=null; style=null

```tsx
<button className="icon-btn" aria-label="icon button">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.5" />
                <line x1="8" y1="5" x2="8" y2="8" stroke="currentColor" strokeWidth="1.5" />
                <circle cx="8" cy="11" r="0.75" fill="currentColor" />
              </svg>
            </button>
```

- frontend/src/pages/design-system/DesignSystemPage.tsx:L418; class=static; handlers={}; form=null; type="button"; disabled=null; style=null

```tsx
<button type="button" className="icon-btn" aria-label="settings">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
                <circle cx="10" cy="10" r="2.5" stroke="currentColor" strokeWidth="1.5" />
                <path d="M10 2v2M10 16v2M2 10h2M16 10h2M4.1 4.1l1.4 1.4M14.5 14.5l1.4 1.4M4.1 15.9l1.4-1.4M14.5 5.5l1.4-1.4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
            </button>
```

- frontend/src/pages/design-system/DesignSystemPage.tsx:L430; class=static; handlers={}; form=null; type="button"; disabled=null; style=null

```tsx
<button type="button" className="icon-btn" aria-label="settings">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
                <circle cx="10" cy="10" r="2.5" stroke="currentColor" strokeWidth="1.5" />
                <path d="M10 2v2M10 16v2M2 10h2M16 10h2M4.1 4.1l1.4 1.4M14.5 14.5l1.4 1.4M4.1 15.9l1.4-1.4M14.5 5.5l1.4-1.4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
            </button>
```

- frontend/src/pages/goal-setting/GoalSettingPage.tsx:L343; class=dynamic; handlers={"onClick":{"raw":"{() => setKgiType(\"revenue\")}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                  type="button"
                  data-testid="goal-advisor-type-revenue"
                  className={`gs-advisor__toggle-btn${kgiType === "revenue" ? " is-active" : ""}`}
                  onClick={() => setKgiType("revenue")}
                >
                  {t("goals.advisorTypeRevenue")}
                </button>
```

- frontend/src/pages/goal-setting/GoalSettingPage.tsx:L351; class=dynamic; handlers={"onClick":{"raw":"{() => setKgiType(\"wins\")}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                  type="button"
                  data-testid="goal-advisor-type-wins"
                  className={`gs-advisor__toggle-btn${kgiType === "wins" ? " is-active" : ""}`}
                  onClick={() => setKgiType("wins")}
                >
                  {t("goals.advisorTypeWins")}
                </button>
```

- frontend/src/pages/inbox/EmojiPickerWrapper.tsx:L48; class=static; handlers={"onClick":{"raw":"{() => onSelect({ name: emoji })}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
          key={emoji}
          type="button"
          className="emoji-preset-btn"
          aria-label={emoji}
          onClick={() => onSelect({ name: emoji })}
        >
          {emoji}
        </button>
```

- frontend/src/pages/inbox/EmojiPickerWrapper.tsx:L62; class=static; handlers={"onClick":{"raw":"{() => onSelect({ name: ce.names[0] ?? ce.id, id: ce.id })}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
              key={ce.id}
              type="button"
              className="emoji-preset-btn"
              aria-label={ce.names[0] ?? ce.id}
              title={ce.names[0] ?? ce.id}
              onClick={() => onSelect({ name: ce.names[0] ?? ce.id, id: ce.id })}
            >
              <img
                src={ce.imgUrl}
                alt={ce.names[0] ?? ce.id}
                width={20}
                height={20}
                style={{ verticalAlign: "middle" }}
              />
            </button>
```

- frontend/src/pages/inbox/InboxConversationList.tsx:L70; class=dynamic; handlers={"onClick":{"raw":"{toggleSelectMode}","inline":false,"name":"toggleSelectMode"}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
            type="button"
            className={`inbox-manage-btn${selectMode ? " active" : ""}`}
            onClick={toggleSelectMode}
            aria-pressed={selectMode}
          >
            <NAV_ICONS.filter size={13} weight="fill" />
            {t("inbox.manage")}
          </button>
```

- frontend/src/pages/inbox/InboxConversationList.tsx:L81; class=static; handlers={"onClick":{"raw":"{handleMarkAllRead}","inline":false,"name":"handleMarkAllRead"}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                type="button"
                className="dropdown-item"
                role="menuitem"
                onClick={handleMarkAllRead}
              >
                {t("inbox.markAllRead")}
              </button>
```

- frontend/src/pages/inbox/InboxConversationList.tsx:L107; class=static; handlers={"onClick":{"raw":"{handleBulkMarkRead}","inline":false,"name":"handleBulkMarkRead"}}; form=null; type="button"; disabled={selectedLeadIds.size === 0}; style=null

```tsx
<button type="button" className="inbox-bulk-action" onClick={handleBulkMarkRead}
            disabled={selectedLeadIds.size === 0} title={t("inbox.markAllRead")} aria-label={t("inbox.markAllRead")}>
            <INBOX_ACTION_ICONS.markRead size={14} weight="fill" aria-hidden="true" />
          </button>
```

- frontend/src/pages/inbox/InboxConversationList.tsx:L111; class=static; handlers={"onClick":{"raw":"{handleBulkMarkUnread}","inline":false,"name":"handleBulkMarkUnread"}}; form=null; type="button"; disabled={selectedLeadIds.size === 0}; style=null

```tsx
<button type="button" className="inbox-bulk-action" onClick={handleBulkMarkUnread}
            disabled={selectedLeadIds.size === 0} title={t("inbox.markUnread")} aria-label={t("inbox.markUnread")}>
            <INBOX_ACTION_ICONS.markUnread size={14} weight="fill" aria-hidden="true" />
          </button>
```

- frontend/src/pages/inbox/InboxConversationList.tsx:L115; class=static; handlers={"onClick":{"raw":"{handleBulkExclude}","inline":false,"name":"handleBulkExclude"}}; form=null; type="button"; disabled={selectedLeadIds.size === 0}; style=null

```tsx
<button type="button" className="inbox-bulk-action" onClick={handleBulkExclude}
            disabled={selectedLeadIds.size === 0} title={t("inbox.exclude")} aria-label={t("inbox.exclude")}>
            <INBOX_ACTION_ICONS.exclude size={14} weight="fill" aria-hidden="true" />
          </button>
```

- frontend/src/pages/inbox/InboxConversationList.tsx:L119; class=static; handlers={"onClick":{"raw":"{handleBulkDelete}","inline":false,"name":"handleBulkDelete"}}; form=null; type="button"; disabled={selectedLeadIds.size === 0}; style=null

```tsx
<button type="button" className="inbox-bulk-action inbox-bulk-delete" onClick={handleBulkDelete}
            disabled={selectedLeadIds.size === 0} title={t("inbox.deleteLead")} aria-label={t("inbox.deleteLead")}>
            <INBOX_ACTION_ICONS.delete size={14} weight="fill" aria-hidden="true" />
          </button>
```

- frontend/src/pages/inbox/InboxConversationList.tsx:L128; class=dynamic; handlers={"onClick":{"raw":"{() => setUnreadOnly((v) => !v)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
          type="button"
          className={`inbox-sub-filter-pill${unreadOnly ? " active" : ""}`}
          onClick={() => setUnreadOnly((v) => !v)}
        >
          {t("inbox.filterUnread")}
        </button>
```

- frontend/src/pages/inbox/InboxConversationList.tsx:L135; class=dynamic; handlers={"onClick":{"raw":"{() => setFollowUpOnly((v) => !v)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
          type="button"
          className={`inbox-sub-filter-pill${followUpOnly ? " active" : ""}`}
          onClick={() => setFollowUpOnly((v) => !v)}
        >
          {t("inbox.filterFollowUp")}
        </button>
```

- frontend/src/pages/inbox/InboxConversationList.tsx:L166; class=absent; handlers={"onClick":{"raw":"{() => loadConversations()}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style={{ marginLeft: "var(--space-2)", fontSize: "var(--font-xs)", cursor: "pointer" }}

```tsx
<button
              type="button"
              style={{ marginLeft: "var(--space-2)", fontSize: "var(--font-xs)", cursor: "pointer" }}
              onClick={() => loadConversations()}
            >
              {t("common.reload")}
            </button>
```

- frontend/src/pages/inbox/InboxConversationList.tsx:L194; class=dynamic; handlers={"onClick":{"raw":"{() => selectMode ? toggleSelectConv(conv.lead_id) : selectLead(conv.lead_id)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                key={conv.lead_id}
                type="button"
                role={selectMode ? "checkbox" : undefined}
                aria-checked={selectMode ? isBulkChecked : undefined}
                className={`conv-item conversation-item${isSelected ? " selected" : ""}${selectMode && isBulkChecked ? " bulk-selected" : ""}`}
                onClick={() => selectMode ? toggleSelectConv(conv.lead_id) : selectLead(conv.lead_id)}
              >
                {selectMode && (
                  <span aria-hidden="true" className={`conv-select-check${isBulkChecked ? " checked" : ""}`} />
                )}
                <div className="conv-avatar-wrap">
                  <div className="conv-avatar">
                    {conv.profile_picture_url && !avatarErrors.has(conv.lead_id) ? (
                      <img
                        src={conv.profile_picture_url}
                        alt={t("inbox.avatarAlt")}
                        style={{ width: "100%", height: "100%", borderRadius: "50%", objectFit: "cover" }}
                        onError={() => handleAvatarError(conv.lead_id)}
                      />
                    ) : (
                      getInitials(conv.customer_name)
                    )}
                  </div>
                  <span className={`conv-platform-dot${SQUIRCLE_ICONS.has(conv.platform ?? "") ? " conv-platform-dot--squircle" : ""}`}>
                    <PlatformIcon platform={conv.platform} size={ICON.base} />
                  </span>
                </div>
                <div className="conv-info">
                  <div className="conv-header">
                    <span className={`conv-name${(conv.unread_count ?? 0) > 0 ? " unread" : ""}`}>
                      {conv.customer_name ?? `Lead #${conv.lead_id}`}
                    </span>
                    {conv.lead_status && (
                      <span className="conv-status-badge">{t(`leads.statusCode.${conv.lead_status}`, { defaultValue: conv.lead_status })}</span>
                    )}
                    <span className="conv-time">{relativeTime(conv.last_message_at)}</span>
                  </div>
                  <div className="conv-preview">
                    <span className={`conv-preview-text${conv.unread_count > 0 ? " unread" : ""}`}>
                      {conv.last_message_direction === "outbound" && (
                        <span style={{ opacity: "var(--opacity-muted)" }}>You: </span>
                      )}
                      {conv.last_message_text ?? ""}
                    </span>
                    {conv.unread_count > 0 && (
                      <span className="badge conv-unread-badge">{conv.unread_count}</span>
                    )}
                  </div>
                </div>
              </button>
```

- frontend/src/pages/inbox/InboxKartePanel.tsx:L125; class=static; handlers={"onClick":{"raw":"{closeKartePanel}","inline":false,"name":"closeKartePanel"}}; form=null; type="button"; disabled=null; style=null

```tsx
<button type="button" className="karte-close-btn" onClick={closeKartePanel}
              aria-label={t("common.close")} data-tooltip={t("common.close")}>
              <NAV_ICONS.close size={ICON.md} weight="fill" aria-hidden="true" />
            </button>
```

- frontend/src/pages/inbox/InboxKartePanel.tsx:L166; class=static; handlers={"onClick":{"raw":"{() => setShowProfileModal(true)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button type="button" className="karte-open-link" onClick={() => setShowProfileModal(true)}>
                {t("inbox.openCustomerPage")} →
              </button>
```

- frontend/src/pages/inbox/InboxKartePanel.tsx:L182; class=dynamic; handlers={"onClick":{"raw":"{() => setKarteTab(tab)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button key={tab} type="button"
                className={`right-panel-tab${karteTab === tab ? " active" : ""}`}
                data-testid={`karte-tab-${tab}`}
                onClick={() => setKarteTab(tab)}>
                {t(`inbox.karte${tab.charAt(0).toUpperCase()}${tab.slice(1)}`)}
              </button>
```

- frontend/src/pages/inbox/InboxKartePanel.tsx:L270; class=static; handlers={"onClick":{"raw":"{primaryOnClick!}","inline":false,"name":"primaryOnClick!"}}; form=null; type="button"; disabled=null; style=null

```tsx
<button type="button" className="karte-action-primary" data-testid="karte-action-primary" onClick={primaryOnClick!}>
        {primaryLabel}
      </button>
```

- frontend/src/pages/inbox/InboxKartePanel.tsx:L273; class=static; handlers={"onClick":{"raw":"{() => setMenuOpen((prev) => !prev)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
        type="button"
        className="karte-action-overflow"
        data-testid="karte-action-overflow"
        aria-label={t("inbox.moreActions")}
        aria-expanded={menuOpen}
        onClick={() => setMenuOpen((prev) => !prev)}
      >
        ⋯
      </button>
```

- frontend/src/pages/inbox/InboxKartePanel.tsx:L286; class=static; handlers={"onClick":{"raw":"{() => generateLink(\"register\")}","inline":true,"name":null}}; form=null; type="button"; disabled={regLinkLoading}; style=null

```tsx
<button
            type="button"
            role="menuitem"
            className="karte-overflow-item"
            disabled={regLinkLoading}
            onClick={() => generateLink("register")}
          >
            {t("registration.generateLink")}
          </button>
```

- frontend/src/pages/inbox/InboxKartePanel.tsx:L295; class=static; handlers={"onClick":{"raw":"{() => generateLink(\"add_address\")}","inline":true,"name":null}}; form=null; type="button"; disabled={regLinkLoading}; style=null

```tsx
<button
            type="button"
            role="menuitem"
            className="karte-overflow-item"
            disabled={regLinkLoading}
            onClick={() => generateLink("add_address")}
          >
            {t("registration.generateAddressLink")}
          </button>
```

- frontend/src/pages/inbox/InboxKartePanel.tsx:L305; class=static; handlers={"onClick":{"raw":"{() => generateLink(\"change_billing\")}","inline":true,"name":null}}; form=null; type="button"; disabled={regLinkLoading}; style=null

```tsx
<button
              type="button"
              role="menuitem"
              className="karte-overflow-item"
              disabled={regLinkLoading}
              onClick={() => generateLink("change_billing")}
            >
              {t("registration.generateChangeBillingLink")}
            </button>
```

- frontend/src/pages/inbox/InboxMessageThread.tsx:L432; class=static; handlers={"onClick":{"raw":"{handleMarkUnread}","inline":false,"name":"handleMarkUnread"}}; form=null; type="button"; disabled=null; style=null

```tsx
<button type="button" className="inbox-thread-action-btn"
            onClick={handleMarkUnread}
            aria-label={t("inbox.markUnread")} data-tooltip={t("inbox.markUnread")}>
            <INBOX_ACTION_ICONS.markUnread size={ICON.base} weight="fill" aria-hidden="true" />
          </button>
```

- frontend/src/pages/inbox/InboxMessageThread.tsx:L439; class=static; handlers={"onClick":{"raw":"{() => showKartePanel ? closeKartePanel() : openKartePanel()}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button type="button" className="karte-toggle-btn"
            onClick={() => showKartePanel ? closeKartePanel() : openKartePanel()}
            aria-label={t("inbox.karteToggle")}>
            <PAGE_ICONS.kartePanel size={ICON.base} weight="fill" aria-hidden="true" />
            {t("inbox.karteToggle")}
          </button>
```

- frontend/src/pages/inbox/InboxMessageThread.tsx:L447; class=static; handlers={"onClick":{"raw":"{() => setMenuOpen(v => !v)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
            type="button"
            className="inbox-header-menu-btn"
            onClick={() => setMenuOpen(v => !v)}
            aria-label={t("inbox.moreActions")}
            aria-expanded={menuOpen}
            aria-haspopup="menu"
          >
            <NAV_ICONS.more size={ICON.base} weight="bold" aria-hidden="true" />
          </button>
```

- frontend/src/pages/inbox/InboxMessageThread.tsx:L459; class=static; handlers={"onClick":{"raw":"{() => { handleMarkUnread(); setMenuOpen(false); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button role="menuitem" className="inbox-header-menu-item"
                onClick={() => { handleMarkUnread(); setMenuOpen(false); }}>
                <INBOX_ACTION_ICONS.markUnread size={ICON.base} weight="fill" aria-hidden="true" />
                {t("inbox.markUnread")}
              </button>
```

- frontend/src/pages/inbox/InboxMessageThread.tsx:L464; class=static; handlers={"onClick":{"raw":"{() => { handleExclude(); setMenuOpen(false); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button role="menuitem" className="inbox-header-menu-item"
                onClick={() => { handleExclude(); setMenuOpen(false); }}>
                <INBOX_ACTION_ICONS.exclude size={ICON.base} weight="fill" aria-hidden="true" />
                {t("inbox.exclude")}
              </button>
```

- frontend/src/pages/inbox/InboxMessageThread.tsx:L469; class=static; handlers={"onClick":{"raw":"{() => { handleDeleteLead(); setMenuOpen(false); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button role="menuitem" className="inbox-header-menu-item danger"
                onClick={() => { handleDeleteLead(); setMenuOpen(false); }}>
                <INBOX_ACTION_ICONS.delete size={ICON.base} weight="fill" aria-hidden="true" />
                {t("inbox.deleteLead")}
              </button>
```

- frontend/src/pages/inbox/InboxMessageThread.tsx:L475; class=static; handlers={"onClick":{"raw":"{() => { showKartePanel ? closeKartePanel() : openKartePanel(); setMenuOpen(false); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button role="menuitem" className="inbox-header-menu-item"
                  onClick={() => { showKartePanel ? closeKartePanel() : openKartePanel(); setMenuOpen(false); }}>
                  <PAGE_ICONS.kartePanel size={ICON.base} weight="fill" aria-hidden="true" />
                  {t("inbox.karteToggle")}
                </button>
```

- frontend/src/pages/inbox/InboxMessageThread.tsx:L595; class=static; handlers={"onClick":{"raw":"{() =>\n                            handleReactionPillClick(\n                              msg.message_id!,\n                              reaction.emoji_name,\n                              reaction.emoji_id,\n                              reaction.is_mine,\n                            )\n                          }","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                          key={`${reaction.emoji_name}:${reaction.emoji_id ?? ""}`}
                          type="button"
                          className="msg-reaction-pill"
                          data-mine={reaction.is_mine ? "true" : undefined}
                          title={tooltipText}
                          aria-label={
                            reaction.is_mine
                              ? t("inbox.removeReaction")
                              : t("inbox.addReaction")
                          }
                          onClick={() =>
                            handleReactionPillClick(
                              msg.message_id!,
                              reaction.emoji_name,
                              reaction.emoji_id,
                              reaction.is_mine,
                            )
                          }
                        >
                          {reaction.emoji_id ? (
                            <img
                              src={`https://cdn.discordapp.com/emojis/${reaction.emoji_id}.${reaction.emoji_animated ? "gif" : "png"}?size=16`}
                              alt={reaction.emoji_name}
                              width={16}
                              height={16}
                              style={{ verticalAlign: "middle" }}
                            />
                          ) : (
                            <span aria-hidden="true">{reaction.emoji_name}</span>
                          )}
                          <span className="msg-reaction-count">{reaction.count}</span>
                        </button>
```

- frontend/src/pages/inbox/InboxMessageThread.tsx:L633; class=static; handlers={"onClick":{"raw":"{() =>\n                            setOpenPickerForMsgId((prev) =>\n                              prev === msg.message_id ? null : (msg.message_id ?? null)\n                            )\n                          }","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                          type="button"
                          className="msg-reaction-add-btn"
                          aria-label={t("inbox.addReaction")}
                          title={t("inbox.addReaction")}
                          onClick={() =>
                            setOpenPickerForMsgId((prev) =>
                              prev === msg.message_id ? null : (msg.message_id ?? null)
                            )
                          }
                        >
                          {/* emoji スマイルアイコン（INBOX_ACTION_ICONS にないため SVG 直書き） */}
                          {/* ui-allow: SmilePlus は icons.tsx 未登録・emoji-picker と同梱のため直書き */}
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                            <circle cx="12" cy="12" r="10" />
                            <path d="M8 13s1.5 2 4 2 4-2 4-2" />
                            <line x1="9" y1="9" x2="9.01" y2="9" />
                            <line x1="15" y1="9" x2="15.01" y2="9" />
                            <line x1="19" y1="5" x2="23" y2="5" />
                            <line x1="21" y1="3" x2="21" y2="7" />
                          </svg>
                        </button>
```

- frontend/src/pages/inbox/InboxMessageThread.tsx:L670; class=static; handlers={"onClick":{"raw":"{() =>\n                          setOpenPickerForMsgId((prev) =>\n                            prev === msg.message_id ? null : (msg.message_id ?? null)\n                          )\n                        }","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                        type="button"
                        className="msg-reaction-add-btn"
                        aria-label={t("inbox.addReaction")}
                        title={t("inbox.addReaction")}
                        onClick={() =>
                          setOpenPickerForMsgId((prev) =>
                            prev === msg.message_id ? null : (msg.message_id ?? null)
                          )
                        }
                      >
                        {/* ui-allow: SmilePlus は icons.tsx 未登録・emoji-picker と同梱のため直書き */}
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                          <circle cx="12" cy="12" r="10" />
                          <path d="M8 13s1.5 2 4 2 4-2 4-2" />
                          <line x1="9" y1="9" x2="9.01" y2="9" />
                          <line x1="15" y1="9" x2="15.01" y2="9" />
                          <line x1="19" y1="5" x2="23" y2="5" />
                          <line x1="21" y1="3" x2="21" y2="7" />
                        </svg>
                      </button>
```

- frontend/src/pages/inbox/InboxMessageThread.tsx:L706; class=static; handlers={"onClick":{"raw":"{() => handleTranslate(msg.message_id)}","inline":true,"name":null}}; form=null; type="button"; disabled={translationState?.loading}; style=null

```tsx
<button
                      type="button"
                      className="msg-translate-btn"
                      onClick={() => handleTranslate(msg.message_id)}
                      aria-label={translationState?.text ? t("inbox.showOriginal") : t("inbox.translate")}
                      title={translationState?.text ? t("inbox.showOriginal") : t("inbox.translate")}
                      disabled={translationState?.loading}
                    >
                      <INBOX_ACTION_ICONS.translate size={14} weight="fill" aria-hidden="true" />
                    </button>
```

- frontend/src/pages/inbox/InboxMessageThread.tsx:L748; class=static; handlers={"onClick":{"raw":"{() => {\n                  setShowSendGuardDialog(false);\n                  setShowOutboundPreview(true);\n                }}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                type="button"
                className="send-guard-btn send-guard-btn--translate"
                onClick={() => {
                  setShowSendGuardDialog(false);
                  setShowOutboundPreview(true);
                }}
              >
                {t("translation.sendGuard.translateAndSend")}
              </button>
```

- frontend/src/pages/inbox/InboxMessageThread.tsx:L758; class=static; handlers={"onClick":{"raw":"{() => {\n                  setShowSendGuardDialog(false);\n                  submitSend();\n                }}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                type="button"
                className="send-guard-btn send-guard-btn--asis"
                onClick={() => {
                  setShowSendGuardDialog(false);
                  submitSend();
                }}
              >
                {t("translation.sendGuard.sendAsIs")}
              </button>
```

- frontend/src/pages/inbox/InboxMessageThread.tsx:L768; class=static; handlers={"onClick":{"raw":"{() => setShowSendGuardDialog(false)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                type="button"
                className="send-guard-btn send-guard-btn--cancel"
                onClick={() => setShowSendGuardDialog(false)}
              >
                {t("translation.sendGuard.cancel")}
              </button>
```

- frontend/src/pages/inbox/InboxMessageThread.tsx:L801; class=static; handlers={"onClick":{"raw":"{handleClearAttachment}","inline":false,"name":"handleClearAttachment"}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                type="button"
                className="send-preview-remove"
                onClick={handleClearAttachment}
                aria-label={t("inbox.removeAttachment")}
              >
                <INBOX_ACTION_ICONS.delete size={ICON.sm} aria-hidden="true" />
              </button>
```

- frontend/src/pages/inbox/InboxMessageThread.tsx:L845; class=static; handlers={"onClick":{"raw":"{handleAttachClick}","inline":false,"name":"handleAttachClick"}}; form=null; type="button"; disabled={!canSend || sending}; style=null

```tsx
<button
                type="button"
                className="send-attach-btn"
                onClick={handleAttachClick}
                disabled={!canSend || sending}
                aria-label={t("inbox.attachImage")}
                title={t("inbox.attachImage")}
              >
                <INBOX_ACTION_ICONS.attach size={ICON.md} aria-hidden="true" />
              </button>
```

- frontend/src/pages/inbox/InboxMessageThread.tsx:L858; class=static; handlers={"onClick":{"raw":"{() => setShowOutboundPreview(true)}","inline":true,"name":null}}; form=null; type="button"; disabled={sending}; style=null

```tsx
<button
                type="button"
                className="inbox-translate-outbound-btn"
                onClick={() => setShowOutboundPreview(true)}
                disabled={sending}
                title={t("translation.outbound.buttonTitle")}
                aria-label={t("translation.outbound.buttonTitle")}
              >
                <INBOX_ACTION_ICONS.translate size={ICON.sm} aria-hidden="true" />
                <span className="inbox-translate-outbound-label">EN</span>
              </button>
```

- frontend/src/pages/inbox/InboxMessageThread.tsx:L870; class=static; handlers={"onClick":{"raw":"{checkAndSend}","inline":false,"name":"checkAndSend"}}; form=null; type="button"; disabled={sendDisabled && !attachedFile}; style=null

```tsx
<button
              type="button"
              className="inbox-send-btn"
              onClick={checkAndSend}
              disabled={sendDisabled && !attachedFile}
              title={
                discordChannelMissing
                  ? t("inbox.discordChannelMissing")
                  : !canSend
                    ? t("inbox.sendDisabled7d")
                    : trimmedDraft.length === 0 && !attachedFile
                      ? t("inbox.messagePlaceholder")
                      : t("inbox.send")
              }
            >
              <INBOX_ACTION_ICONS.send size={ICON.base} aria-hidden="true" />
              <span className="sr-only">{sending ? t("inbox.sending") : t("inbox.send")}</span>
            </button>
```

- frontend/src/pages/inbox/InboxPage.tsx:L64; class=static; handlers={"onClick":{"raw":"{() => setShowSettings(true)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
        type="button"
        className="icon-btn"
        onClick={() => setShowSettings(true)}
        aria-label={t("inbox.settings.title")}
        data-tooltip={t("inbox.settings.tooltip")}
      >
        <PAGE_ICONS.settingsSolid size={ICON.md} aria-hidden="true" />
      </button>
```

- frontend/src/pages/inbox/InboxPage.tsx:L85; class=dynamic; handlers={"onClick":{"raw":"{() => state.setStatusTab(tab.key)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button key={tab.key} type="button"
                  className={`inbox-full-tab${state.statusTab === tab.key ? " active" : ""}`}
                  onClick={() => state.setStatusTab(tab.key)}>
                  {t(tab.labelKey)}
                </button>
```

- frontend/src/pages/inbox/InboxProfileModal.tsx:L88; class=static; handlers={"onClick":{"raw":"{onClose}","inline":false,"name":"onClose"}}; form=null; type="button"; disabled=null; style=null

```tsx
<button type="button" className="inbox-profile-modal-close" onClick={onClose} aria-label={t("common.close")}>
            <NAV_ICONS.close size={ICON.md} aria-hidden="true" />
          </button>
```

- frontend/src/pages/inbox/InboxProfileModal.tsx:L101; class=dynamic; handlers={"onClick":{"raw":"{() => setProfileModalTab(tab)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button key={tab} type="button"
              className={`right-panel-tab${profileModalTab === tab ? " active" : ""}`}
              onClick={() => setProfileModalTab(tab)}>
              {t(`inbox.karte${tab.charAt(0).toUpperCase()}${tab.slice(1)}`)}
            </button>
```

- frontend/src/pages/inbox/ManualRecordSection.tsx:L179; class=static; handlers={"onClick":{"raw":"{() => handleSave(true)}","inline":true,"name":null}}; form=null; type="button"; disabled={saving}; style=null

```tsx
<button
            type="button"
            className="manual-record-dup-force-btn"
            onClick={() => handleSave(true)}
            disabled={saving}
          >
            {t("inbox.manualRecord.saveAnyway")}
          </button>
```

- frontend/src/pages/inbox/ManualRecordSection.tsx:L190; class=static; handlers={"onClick":{"raw":"{() => handleSave(false)}","inline":true,"name":null}}; form=null; type="button"; disabled={saving || !contentText.trim()}; style=null

```tsx
<button
        type="button"
        className="manual-record-save-btn"
        onClick={() => handleSave(false)}
        disabled={saving || !contentText.trim()}
        aria-label={t("inbox.manualRecord.save")}
      >
        {saving
          ? t("inbox.manualRecord.saving")
          : t("inbox.manualRecord.save")}
      </button>
```

- frontend/src/pages/inbox/OutboundTranslationPreview.tsx:L86; class=static; handlers={"onClick":{"raw":"{onClose}","inline":false,"name":"onClose"}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
            type="button"
            className="outbound-translation-close"
            onClick={onClose}
            aria-label={t("common.close")}
          >
            ×
          </button>
```

- frontend/src/pages/inbox/OutboundTranslationPreview.tsx:L164; class=static; handlers={"onClick":{"raw":"{onClose}","inline":false,"name":"onClose"}}; form=null; type="button"; disabled={confirming}; style=null

```tsx
<button
                type="button"
                className="outbound-translation-back-btn"
                onClick={onClose}
                disabled={confirming}
              >
                {t("translation.outbound.back")}
              </button>
```

- frontend/src/pages/inbox/OutboundTranslationPreview.tsx:L172; class=static; handlers={"onClick":{"raw":"{handleConfirmSend}","inline":false,"name":"handleConfirmSend"}}; form=null; type="button"; disabled={confirming || !editedText.trim()}; style=null

```tsx
<button
                type="button"
                className="outbound-translation-send-btn"
                onClick={handleConfirmSend}
                disabled={confirming || !editedText.trim()}
              >
                {confirming
                  ? t("translation.outbound.confirming")
                  : t("translation.outbound.confirmSend")}
              </button>
```

- frontend/src/pages/inbox/SalesFormMultiSelect.tsx:L102; class=static; handlers={"onClick":{"raw":"{() => {\n          if (open) onBlur();\n          setOpen((prev) => !prev);\n        }}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
        type="button"
        className="right-panel-field sales-form-trigger"
        onClick={() => {
          if (open) onBlur();
          setOpen((prev) => !prev);
        }}
        aria-haspopup="listbox"
        aria-expanded={open}
        data-testid="sales-form-trigger"
      >
        {selectedLabels || t("leads.salesFormPlaceholder")}
        <NAV_ICONS.chevronDown size={ICON.sm} aria-hidden="true" className="sales-form-caret" />
      </button>
```

- frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:L103; class=dynamic; handlers={"onClick":{"raw":"{(e) => {\n                const pane = (e.currentTarget as HTMLElement).closest(\n                  \".page-layout-content\",\n                ) as HTMLElement | null;\n                const scrollTop = pane?.scrollTop ?? 0;\n                setActiveIndex(i);\n                onLastReached?.(i === substeps.length - 1);\n                requestAnimationFrame(() => {\n                  if (pane) pane.scrollTop = scrollTop;\n                });\n              }}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
              type="button"
              role="tab"
              aria-selected={i === activeIndex}
              className={`etd-guide__substep-nav-item${i === activeIndex ? " etd-guide__substep-nav-item--active" : ""}`}
              onClick={(e) => {
                const pane = (e.currentTarget as HTMLElement).closest(
                  ".page-layout-content",
                ) as HTMLElement | null;
                const scrollTop = pane?.scrollTop ?? 0;
                setActiveIndex(i);
                onLastReached?.(i === substeps.length - 1);
                requestAnimationFrame(() => {
                  if (pane) pane.scrollTop = scrollTop;
                });
              }}
            >
              {sub.label}
            </button>
```

- frontend/src/pages/inventory/InventoryPage.tsx:L338; class=absent; handlers={"onClick":{"raw":"{() => onSort(field)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            font: "inherit",
            fontWeight: "var(--font-weight-semi)",
            color: "inherit",
            display: "inline-flex",
            alignItems: "center",
            gap: "var(--space-1)",
          }}

```tsx
<button
          type="button"
          onClick={() => onSort(field)}
          data-testid={`inventory-sort-${field}`}
          aria-label={t("inventory.sortBy", { col: t(`inventory.col.${colKey}`) })}
          title={t("inventory.sortBy", { col: t(`inventory.col.${colKey}`) })}
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            font: "inherit",
            fontWeight: "var(--font-weight-semi)",
            color: "inherit",
            display: "inline-flex",
            alignItems: "center",
            gap: "var(--space-1)",
          }}
        >
          {t(`inventory.col.${colKey}`)}
          <span
            aria-hidden="true"
            style={{
              fontSize: "var(--font-xs)",
              color: active ? "var(--accent)" : "var(--text-muted)",
            }}
          >
            {active ? sortArrow(field) : t("inventory.sortNone")}
          </span>
        </button>
```

- frontend/src/pages/inventory/InventoryPage.tsx:L468; class=dynamic; handlers={"onClick":{"raw":"{() => { setActiveTab(code); setPage(1); }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button
                key={code}
                className={activeTab === code ? "tab active" : "tab"}
                onClick={() => { setActiveTab(code); setPage(1); }}
              >{label}</button>
```

- frontend/src/pages/inventory/OwnInventoryPage.tsx:L209; class=absent; handlers={"onClick":{"raw":"{() => setPage((p) => p - 1)}","inline":true,"name":null}}; form=null; type="button"; disabled={page <= 1}; style=null

```tsx
<button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              aria-label={t("common.prevPage")}
            >
              {"<"}
            </button>
```

- frontend/src/pages/inventory/OwnInventoryPage.tsx:L218; class=absent; handlers={"onClick":{"raw":"{() => setPage((p) => p + 1)}","inline":true,"name":null}}; form=null; type="button"; disabled={items.length < PER_PAGE}; style=null

```tsx
<button
              type="button"
              disabled={items.length < PER_PAGE}
              onClick={() => setPage((p) => p + 1)}
              aria-label={t("common.nextPage")}
            >
              {">"}
            </button>
```

- frontend/src/pages/invoices/InvoicesPage.tsx:L126; class=absent; handlers={"onClick":{"raw":"{() => navigate(\"/quotes\")}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button onClick={() => navigate("/quotes")}>{t("nav.quoteHistory")}</button>
```

- frontend/src/pages/invoices/InvoicesPage.tsx:L127; class=static; handlers={}; form=null; type=null; disabled=null; style=null

```tsx
<button className="tab-active">{t("nav.invoices")}</button>
```

- frontend/src/pages/login/LoginPage.tsx:L111; class=static; handlers={"onClick":{"raw":"{switchToReset}","inline":false,"name":"switchToReset"}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                  type="button"
                  className="login-forgot-link"
                  onClick={switchToReset}
                >
                  {t("login.forgotPassword")}
                </button>
```

- frontend/src/pages/login/LoginPage.tsx:L149; class=static; handlers={"onClick":{"raw":"{switchToSignIn}","inline":false,"name":"switchToSignIn"}}; form=null; type="button"; disabled=null; style=null

```tsx
<button type="button" className="login-back-link" onClick={switchToSignIn}>
              {t("login.backToLogin")}
            </button>
```

- frontend/src/pages/orders/OrdersFilterBar.tsx:L51; class=static; handlers={"onClick":{"raw":"{toggleSortOrder}","inline":false,"name":"toggleSortOrder"}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
        type="button"
        className="field-h-md"
        onClick={toggleSortOrder}
        aria-label={sortOrder === "desc" ? "↓" : "↑"}
        data-testid="orders-sort-order"
      >
        {sortOrder === "desc" ? "↓" : "↑"}
      </button>
```

- frontend/src/pages/orders/OrdersPage.tsx:L67; class=dynamic; handlers={"onClick":{"raw":"{() => setStatusFilter(\"\")}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
            type="button"
            className={`hub-subnav-item${statusFilter === "" ? " active" : ""}`}
            onClick={() => setStatusFilter("")}
            aria-pressed={statusFilter === ""}
            data-testid="subnav-all"
          >
            {t("common.all")} ({groupCounts?.total ?? 0})
          </button>
```

- frontend/src/pages/orders/OrdersPage.tsx:L77; class=dynamic; handlers={"onClick":{"raw":"{() => setStatusFilter(statusFilter === s ? \"\" : s)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
              type="button"
              key={s}
              className={`hub-subnav-item${statusFilter === s ? " active" : ""}`}
              onClick={() => setStatusFilter(statusFilter === s ? "" : s)}
              aria-pressed={statusFilter === s}
              data-testid={`subnav-${s}`}
            >
              {STATUS_LABELS[s]} ({groupCounts?.counts[s] ?? 0})
            </button>
```

- frontend/src/pages/quotes/QuotesPage.tsx:L92; class=static; handlers={}; form=null; type=null; disabled=null; style=null

```tsx
<button className="tab-active">{t("nav.quoteHistory")}</button>
```

- frontend/src/pages/quotes/QuotesPage.tsx:L93; class=absent; handlers={"onClick":{"raw":"{() => navigate(\"/invoices\")}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button onClick={() => navigate("/invoices")}>{t("nav.invoices")}</button>
```

- frontend/src/pages/quotes/QuotesPage.tsx:L113; class=absent; handlers={"onClick":{"raw":"{() => setStatusFilter(active ? \"\" : s)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style={{
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    padding: 0,
                    // 単一ステータス選択中は非選択を淡く表示して選択を強調
                    opacity: statusFilter === "" || active ? 1 : 0.4,
                    outline: active ? "2px solid var(--accent)" : "none",
                    outlineOffset: "2px",
                    borderRadius: "var(--radius-pill)",
                  }}

```tsx
<button
                  key={s}
                  type="button"
                  data-testid={`quotes-filter-${s}`}
                  aria-pressed={active}
                  onClick={() => setStatusFilter(active ? "" : s)}
                  style={{
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    padding: 0,
                    // 単一ステータス選択中は非選択を淡く表示して選択を強調
                    opacity: statusFilter === "" || active ? 1 : 0.4,
                    outline: active ? "2px solid var(--accent)" : "none",
                    outlineOffset: "2px",
                    borderRadius: "var(--radius-pill)",
                  }}
                >
                  <span className={`badge badge-${getStatusPresentation("quote", s).badgeVariant}`}>{t(`quotes.status_${s}`)}</span>
                </button>
```

- frontend/src/pages/roles/RolesPage.tsx:L354; class=dynamic; handlers={"onClick":{"raw":"{() => selectRole(r.id)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style={{ borderLeft: `4px solid ${r.color || "var(--border-color)"}` }}

```tsx
<button
                    className={`role-item ${r.id === selectedRoleId ? "active" : ""}`}
                    style={{ borderLeft: `4px solid ${r.color || "var(--border-color)"}` }}
                    onClick={() => selectRole(r.id)}
                  >
                    <span className="role-item-name">{r.name}</span>
                  </button>
```

- frontend/src/pages/schedule/SchedulePageImpl.tsx:L220; class=static; handlers={"onClick":{"raw":"{onSave}","inline":false,"name":"onSave"}}; form=null; type=null; disabled=null; style=null

```tsx
<button
                className="modal-icon-btn"
                onClick={onSave}
                aria-label={t("schedule.editEvent")}
                title={t("schedule.editEvent")}
              >
                <EditIcon size={18} />
              </button>
```

- frontend/src/pages/schedule/SchedulePageImpl.tsx:L230; class=static; handlers={"onClick":{"raw":"{onDelete}","inline":false,"name":"onDelete"}}; form=null; type=null; disabled=null; style=null

```tsx
<button
                className="modal-icon-btn modal-icon-btn--danger"
                onClick={onDelete}
                aria-label={t("schedule.deleteEvent")}
                title={t("schedule.deleteEvent")}
              >
                <DeleteIcon size={18} />
              </button>
```

- frontend/src/pages/schedule/SchedulePageImpl.tsx:L239; class=static; handlers={"onClick":{"raw":"{onClose}","inline":false,"name":"onClose"}}; form=null; type=null; disabled=null; style=null

```tsx
<button className="modal-icon-btn" onClick={onClose} aria-label={t("common.close")}>
              <CloseIcon size={18} />
            </button>
```

- frontend/src/pages/schedule/SchedulePageImpl.tsx:L486; class=dynamic; handlers={"onClick":{"raw":"{() => onJumpToDate(date)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button
                  key={date.toISOString()}
                  className={[
                    "schedule-mini-calendar__day",
                    date.getMonth() === currentMonth.getMonth() ? "" : "schedule-mini-calendar__day--muted",
                    today ? "schedule-mini-calendar__day--today" : "",
                    active ? "schedule-mini-calendar__day--active" : "",
                  ].filter(Boolean).join(" ")}
                  onClick={() => onJumpToDate(date)}
                >
                  {date.getDate()}
                </button>
```

- frontend/src/pages/schedule/SchedulePageImpl.tsx:L609; class=dynamic; handlers={"onClick":{"raw":"{(event) => onSelectSlot(date, event.currentTarget.getBoundingClientRect())}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button
                key={date.toISOString()}
                className={`schedule-day-head${today ? " schedule-day-head--today" : ""}`}
                onClick={(event) => onSelectSlot(date, event.currentTarget.getBoundingClientRect())}
              >
                <span className="schedule-day-head__name">{new Intl.DateTimeFormat("ja-JP", { weekday: "short" }).format(date)}</span>
                <span className="schedule-day-head__num">{date.getDate()}</span>
              </button>
```

- frontend/src/pages/schedule/SchedulePageImpl.tsx:L633; class=static; handlers={"onClick":{"raw":"{(event) => onSelectEvent(item, event.currentTarget.getBoundingClientRect())}","inline":true,"name":null}}; form=null; type=null; disabled=null; style={{ background: ownerMeta.color, color: "var(--on-solid)" }}

```tsx
<button
                    key={item.id}
                    className="schedule-chip"
                    style={{ background: ownerMeta.color, color: "var(--on-solid)" }}
                    onClick={(event) => onSelectEvent(item, event.currentTarget.getBoundingClientRect())}
                  >
                    {item.title}
                    {meta && (
                      <span
                        className="schedule-category-chip"
                        style={{ background: cssVar(meta.tintVar), color: cssVar(meta.textVar), marginLeft: "var(--space-2)" }}
                      >
                        {t(meta.labelKey)}
                      </span>
                    )}
                  </button>
```

- frontend/src/pages/schedule/SchedulePageImpl.tsx:L679; class=static; handlers={"onClick":{"raw":"{(event) => {\n                      const base = new Date(day.date);\n                      base.setHours(hour, 0, 0, 0);\n                      onSelectSlot(base, event.currentTarget.getBoundingClientRect());\n                    }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style={{ top: `calc(${hour} * var(--schedule-row-height))` }}

```tsx
<button
                    key={hour}
                    className="schedule-slot"
                    style={{ top: `calc(${hour} * var(--schedule-row-height))` }}
                    onClick={(event) => {
                      const base = new Date(day.date);
                      base.setHours(hour, 0, 0, 0);
                      onSelectSlot(base, event.currentTarget.getBoundingClientRect());
                    }}
                  />
```

- frontend/src/pages/schedule/SchedulePageImpl.tsx:L694; class=dynamic; handlers={"onClick":{"raw":"{(event) => {\n                        event.stopPropagation();\n                        onSelectEvent(laneItem.item, event.currentTarget.getBoundingClientRect());\n                      }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style={{
                        top: `calc(${laneItem.top} * 1px)`,
                        left: `calc(${laneItem.left}% + var(--space-1))`,
                        width: `calc(${laneItem.width}% - var(--space-2))`,
                        height: `calc(${laneItem.height} * 1px)`,
                        background: ownerMeta.color,
                      }}

```tsx
<button
                      key={laneItem.item.id}
                      className={`schedule-event${laneItem.item.source === "shift" ? " schedule-event--shift" : ""}`}
                      style={{
                        top: `calc(${laneItem.top} * 1px)`,
                        left: `calc(${laneItem.left}% + var(--space-1))`,
                        width: `calc(${laneItem.width}% - var(--space-2))`,
                        height: `calc(${laneItem.height} * 1px)`,
                        background: ownerMeta.color,
                      }}
                      onClick={(event) => {
                        event.stopPropagation();
                        onSelectEvent(laneItem.item, event.currentTarget.getBoundingClientRect());
                      }}
                    >
                      <span className="schedule-event__title">{laneItem.item.title}</span>
                      {meta && (
                        <span
                          className="schedule-category-chip"
                          style={{ background: cssVar(meta.tintVar), color: cssVar(meta.textVar) }}
                        >
                          {t(meta.labelKey)}
                        </span>
                      )}
                      <span className="schedule-event__time">
                        {formatTimeRange(laneItem.item.start, laneItem.item.end, laneItem.item.allDay, "ja-JP", t("schedule.allDay"))}
                      </span>
                    </button>
```

- frontend/src/pages/schedule/SchedulePageImpl.tsx:L783; class=static; handlers={"onClick":{"raw":"{(event) => {\n                        event.stopPropagation();\n                        onSelectEvent(item, event.currentTarget.getBoundingClientRect());\n                      }}","inline":true,"name":null}}; form=null; type=null; disabled=null; style={{ background: ownerMeta.color, color: "var(--on-solid)" }}

```tsx
<button
                      key={item.id}
                      className="schedule-month__event"
                      style={{ background: ownerMeta.color, color: "var(--on-solid)" }}
                      onClick={(event) => {
                        event.stopPropagation();
                        onSelectEvent(item, event.currentTarget.getBoundingClientRect());
                      }}
                    >
                      <span>{item.title}</span>
                      {meta && (
                        <span
                          className="schedule-category-chip"
                          style={{ background: cssVar(meta.tintVar), color: cssVar(meta.textVar), marginLeft: "var(--space-1)" }}
                        >
                          {t(meta.labelKey)}
                        </span>
                      )}
                    </button>
```

- frontend/src/pages/schedule/SchedulePageImpl.tsx:L1142; class=dynamic; handlers={"onClick":{"raw":"{() => setView(nextView)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                  key={nextView}
                  type="button"
                  className={`schedule-view-switch__button${view === nextView ? " schedule-view-switch__button--active" : ""}`}
                  aria-pressed={view === nextView}
                  onClick={() => setView(nextView)}
                >
                  {t(`schedule.${nextView}View`)}
                </button>
```

- frontend/src/pages/schedule/SchedulePageImpl.tsx:L1173; class=static; handlers={"onClick":{"raw":"{() => setBanner(null)}","inline":true,"name":null}}; form=null; type=null; disabled=null; style=null

```tsx
<button
                  onClick={() => setBanner(null)}
                  className="schedule-banner__close"
                  aria-label={t("common.close")}
                >
                  ×
                </button>
```

- frontend/src/pages/schedule/ScheduleSettingsPage.tsx:L127; class=static; handlers={"onClick":{"raw":"{() => jumpToSection(\"schedule-settings-self\")}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                type="button"
                className="schedule-settings__nav-item"
                onClick={() => jumpToSection("schedule-settings-self")}
              >
                {t("schedule.myCalendars")}
              </button>
```

- frontend/src/pages/schedule/ScheduleSettingsPage.tsx:L135; class=static; handlers={"onClick":{"raw":"{() => jumpToSection(\"schedule-settings-others\")}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                  type="button"
                  className="schedule-settings__nav-item"
                  onClick={() => jumpToSection("schedule-settings-others")}
                >
                  {t("schedule.otherCalendars")}
                </button>
```

- frontend/src/pages/super-admin/TcgDistributionPage.tsx:L41; class=static; handlers={"onClick":{"raw":"{() => workspaceRef.current?.openNewTargetForm()}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
      type="button"
      className="dist-btn dist-btn--primary"
      onClick={() => workspaceRef.current?.openNewTargetForm()}
      aria-label={t("distributionTarget.page.newBtn")}
    >
      <NAV_ICONS.add size={16} aria-hidden="true" />
      {t("distributionTarget.page.newBtn")}
    </button>
```

- frontend/src/pages/super-admin/TcgLineImportPage.tsx:L547; class=absent; handlers={"onClick":{"raw":"{() =>\n                      setSelectedPendingId((prev) => (prev === job.id ? null : job.id))\n                    }","inline":true,"name":null}}; form=null; type=null; disabled=null; style={{
                      padding: "0.3rem 0.85rem",
                      border: "1px solid var(--color-warning-border)",
                      borderRadius: "4px",
                      background: selectedPendingId === job.id ? "var(--color-warning)" : "var(--bg-primary)",
                      color: selectedPendingId === job.id ? "var(--on-accent)" : "var(--text-primary)",
                      cursor: "pointer",
                      fontSize: "0.85rem",
                      fontWeight: 500,
                    }}

```tsx
<button
                    onClick={() =>
                      setSelectedPendingId((prev) => (prev === job.id ? null : job.id))
                    }
                    style={{
                      padding: "0.3rem 0.85rem",
                      border: "1px solid var(--color-warning-border)",
                      borderRadius: "4px",
                      background: selectedPendingId === job.id ? "var(--color-warning)" : "var(--bg-primary)",
                      color: selectedPendingId === job.id ? "var(--on-accent)" : "var(--text-primary)",
                      cursor: "pointer",
                      fontSize: "0.85rem",
                      fontWeight: 500,
                    }}
                  >
                    {t("tcgLineImport.openReview")}
                  </button>
```

- frontend/src/pages/super-admin/TcgParallelReportPage.tsx:L142; class=absent; handlers={"onClick":{"raw":"{fetchReport}","inline":false,"name":"fetchReport"}}; form=null; type=null; disabled={loading}; style={{ marginBottom: 16, padding: "6px 16px", cursor: "pointer" }}

```tsx
<button
          onClick={fetchReport}
          disabled={loading}
          style={{ marginBottom: 16, padding: "6px 16px", cursor: "pointer" }}
        >
          {loading ? t("tcgParallelReport.calculating") : t("tcgParallelReport.refreshReport")}
        </button>
```

- frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:L845; class=static; handlers={"onClick":{"raw":"{() => onNavigate(\"supplier-master\")}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
            type="button"
            className="analysis-dashboard-cta-btn"
            onClick={() => onNavigate("supplier-master")}
          >
            {t("analysisRules.dashboard.importOrphanCta")}
            <ArrowRightIcon size={14} />
          </button>
```

- frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:L893; class=static; handlers={"onClick":{"raw":"{() => onNavigate(\"supplier-master\")}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                  type="button"
                  className="analysis-dashboard-cta-btn"
                  onClick={() => onNavigate("supplier-master")}
                >
                  {t("analysisRules.dashboard.importCheckSupplierCta")}
                </button>
```

- frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:L919; class=static; handlers={"onClick":{"raw":"{() => onNavigate(\"needs-review\")}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                  type="button"
                  className="analysis-dashboard-cta-btn"
                  onClick={() => onNavigate("needs-review")}
                >
                  {t("analysisRules.dashboard.importReviewCta")}
                  <ArrowRightIcon size={14} />
                </button>
```

- frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:L1447; class=static; handlers={"onClick":{"raw":"{() => onNavigate(\"needs-review\")}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                type="button"
                className="analysis-dashboard-cta-btn"
                onClick={() => onNavigate("needs-review")}
              >
                {t("analysisRules.dashboard.ctaNeedsReview")}
                <ArrowRightIcon size={16} />
              </button>
```

- frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:L1455; class=static; handlers={"onClick":{"raw":"{() => onNavigate(\"product-master\")}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                type="button"
                className="analysis-dashboard-cta-btn"
                onClick={() => onNavigate("product-master")}
              >
                {t("analysisRules.dashboard.ctaProductMaster")}
                <ArrowRightIcon size={16} />
              </button>
```

- frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:L1463; class=static; handlers={"onClick":{"raw":"{() => onNavigate(\"unit-master\")}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
                type="button"
                className="analysis-dashboard-cta-btn"
                onClick={() => onNavigate("unit-master")}
              >
                {t("analysisRules.dashboard.ctaUnitMaster")}
                <ArrowRightIcon size={16} />
              </button>
```

- frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:L1497; class=static; handlers={"onClick":{"raw":"{() => onNavigate(bottleneck.ctaKey)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
              type="button"
              className="analysis-dashboard-cta-btn analysis-dashboard-cta-btn--primary"
              onClick={() => onNavigate(bottleneck.ctaKey)}
            >
              {t(bottleneck.ctaLabelKey)}
              <ArrowRightIcon size={16} />
            </button>
```

- frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:L1540; class=static; handlers={"onClick":{"raw":"{() => onNavigate(\"needs-review\")}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
          type="button"
          className="analysis-dashboard-cta-btn"
          onClick={() => onNavigate("needs-review")}
        >
          {t("analysisRules.dashboard.ctaNeedsReview")}
          <span className="analysis-dashboard-cta-count">
            {data.analysis.needs_review_count.toLocaleString()}
            {t("analysisRules.dashboard.items")}
          </span>
          <ArrowRightIcon size={16} />
        </button>
```

- frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:L1552; class=static; handlers={"onClick":{"raw":"{() => onNavigate(\"product-master\")}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
          type="button"
          className="analysis-dashboard-cta-btn"
          onClick={() => onNavigate("product-master")}
        >
          {t("analysisRules.dashboard.ctaProductMaster")}
          <ArrowRightIcon size={16} />
        </button>
```

- frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:L1560; class=static; handlers={"onClick":{"raw":"{() => onNavigate(\"unit-master\")}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
          type="button"
          className="analysis-dashboard-cta-btn"
          onClick={() => onNavigate("unit-master")}
        >
          {t("analysisRules.dashboard.ctaUnitMaster")}
          <ArrowRightIcon size={16} />
        </button>
```

- frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx:L49; class=dynamic; handlers={"onClick":{"raw":"{() => onChange(key)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
        key={key}
        type="button"
        className={`hub-subnav-item${isActive ? " active" : ""}`}
        onClick={() => onChange(key)}
        aria-pressed={isActive}
        data-testid={`analysis-subnav-${key}`}
      >
        {label}
        {badge !== undefined && badge > 0 && (
          <span
            style={{
              marginLeft: "var(--space-2)",
              fontSize: "var(--font-xs)",
              color: "var(--text-muted)",
            }}
          >
            {t("analysisRules.needsReview.count", { count: badge })}
          </span>
        )}
      </button>
```

- frontend/src/pages/super-admin/components/DbViewerPanel.tsx:L216; class=static; handlers={"onClick":{"raw":"{() => onNavigate(foreign_schema, foreign_table)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
            type="button"
            className="db-viewer__fk-link"
            onClick={() => onNavigate(foreign_schema, foreign_table)}
            title={label}
          >
            {label}
          </button>
```

- frontend/src/pages/super-admin/components/DbViewerPanel.tsx:L282; class=static; handlers={"onClick":{"raw":"{() => onNavigate(row.source_schema, row.source_table)}","inline":true,"name":null}}; form=null; type="button"; disabled=null; style=null

```tsx
<button
          type="button"
          className="db-viewer__fk-link"
          onClick={() => onNavigate(row.source_schema, row.source_table)}
        >
          {row.source_table}
        </button>
```
