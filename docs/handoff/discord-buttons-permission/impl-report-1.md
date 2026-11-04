本報告はカード card-impl-1 の実行結果である

## 開始時 HEAD
8205ff97ff7266b3f50af462df03301f5e85fef4（8205ff97f で始まる＝一致）

## 実装メモ
- 試験は InboxKartePanel 全体ではなく、カード許可どおり KarteTabContent に export を 1 語足して直接描いた。
- 試験名・コメントは eslint(local/no-japanese-literal)警告のため英語にした。ボタン文言は ja.json を引く。
- 実装 commit: 7703fe196

## git diff origin/main...HEAD（該当 2 ファイル）
```diff
diff --git a/frontend/src/pages/inbox/InboxKartePanel.discordButtons.test.tsx b/frontend/src/pages/inbox/InboxKartePanel.discordButtons.test.tsx
new file mode 100644
index 000000000..f7729c5ab
--- /dev/null
+++ b/frontend/src/pages/inbox/InboxKartePanel.discordButtons.test.tsx
@@ -0,0 +1,89 @@
+import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
+import { cleanup, render, screen } from "@testing-library/react";
+import ja from "../../locales/ja.json";
+import type { LeadDetail } from "./inbox.types";
+
+let permissions: string[] = [];
+
+// t resolves existing ja.json keys (no hard-coded labels in this test)
+const lookup = (key: string): string => {
+  const v = key.split(".").reduce<unknown>(
+    (o, k) => (o && typeof o === "object" ? (o as Record<string, unknown>)[k] : undefined),
+    ja,
+  );
+  return typeof v === "string" ? v : key;
+};
+
+vi.mock("react-i18next", () => ({
+  useTranslation: () => ({ t: lookup, i18n: { language: "ja" } }),
+}));
+vi.mock("../../hooks/usePermissions", () => ({
+  usePermissions: () => ({ loading: false, hasPermission: (k: string) => permissions.includes(k) }),
+}));
+vi.mock("../../lib/api", () => ({
+  api: { get: vi.fn(() => Promise.resolve([])), post: vi.fn(() => Promise.resolve({})) },
+}));
+
+import { KarteTabContent } from "./InboxKartePanel";
+
+const leadDetail = {
+  id: 1,
+  discord_user_id: "111",
+  discord_guild_channel_id: "222",
+  estimated_scale: "Small",
+  discord_role_sync_status: "success",
+  discord_role_sync_at: null,
+} as unknown as LeadDetail;
+
+function renderContact() {
+  render(
+    <KarteTabContent
+      tab="contact"
+      leadDetail={leadDetail}
+      cardForm={{}}
+      handleCardFieldChange={vi.fn()}
+      handleCardFieldBlur={vi.fn()}
+      guildId={null}
+    />,
+  );
+}
+
+const INVITE = lookup("leads.channelInviteSend");
+const RESYNC = lookup("leads.discordRoleResync");
+const REMOVE = lookup("leads.discordRemoveFromChannel");
+const KICK = lookup("leads.discordKick");
+const BAN = lookup("leads.discordBan");
+const STATUS = lookup("leads.discordRoleSyncStatus");
+
+describe("Karte Discord buttons by permission", () => {
+  beforeEach(() => {
+    permissions = [];
+  });
+  afterEach(cleanup);
+
+  it("T1 no permission: no action buttons, status label shown", () => {
+    renderContact();
+    for (const label of [INVITE, RESYNC, REMOVE, KICK, BAN]) {
+      expect(screen.queryByText(label)).toBeNull();
+    }
+    expect(screen.getByText(STATUS)).toBeTruthy();
+  });
+
+  it("T2 leads.update only: invite and resync shown, remove/kick/ban hidden", () => {
+    permissions = ["leads.update"];
+    renderContact();
+    expect(screen.getByText(INVITE)).toBeTruthy();
+    expect(screen.getByText(RESYNC)).toBeTruthy();
+    for (const label of [REMOVE, KICK, BAN]) {
+      expect(screen.queryByText(label)).toBeNull();
+    }
+  });
+
+  it("T3 update and delete: all five shown", () => {
+    permissions = ["leads.update", "leads.delete"];
+    renderContact();
+    for (const label of [INVITE, RESYNC, REMOVE, KICK, BAN]) {
+      expect(screen.getByText(label)).toBeTruthy();
+    }
+  });
+});
diff --git a/frontend/src/pages/inbox/InboxKartePanel.tsx b/frontend/src/pages/inbox/InboxKartePanel.tsx
index 6e7122b5e..9dbf67794 100644
--- a/frontend/src/pages/inbox/InboxKartePanel.tsx
+++ b/frontend/src/pages/inbox/InboxKartePanel.tsx
@@ -461,7 +461,7 @@ function ActionBar({
 // Tab content — ADR-110 restructured sections
 // ---------------------------------------------------------------------------
 
-function KarteTabContent({
+export function KarteTabContent({
   tab, leadDetail, cardForm, handleCardFieldChange, handleCardFieldBlur, guildId,
 }: {
   tab: KarteTabKey;
@@ -472,6 +472,7 @@ function KarteTabContent({
   guildId: string | null;
 }) {
   const { t } = useTranslation();
+  const { hasPermission } = usePermissions();
 
   // === CONTACT TAB ===
   if (tab === "contact") {
@@ -529,12 +530,12 @@ function KarteTabContent({
           </div>
         )}
         {/* ADR-091 KPI5: Channel invite button */}
-        {leadDetail.discord_guild_channel_id &&
+        {hasPermission("leads.update") && leadDetail.discord_guild_channel_id &&
           (leadDetail.estimated_scale === "Small" || leadDetail.estimated_scale === "Large") && (
           <ChannelInviteButton leadId={leadDetail.id} />
         )}
         {/* ADR-091 KPI6: Discord remove buttons */}
-        {leadDetail.discord_user_id && (
+        {hasPermission("leads.delete") && leadDetail.discord_user_id && (
           <DiscordRemoveButtons leadId={leadDetail.id} hasChannel={!!leadDetail.discord_guild_channel_id} />
         )}
         {/* ADR-091 KPI7: Role sync status */}
@@ -543,6 +544,7 @@ function KarteTabContent({
             leadId={leadDetail.id}
             status={leadDetail.discord_role_sync_status}
             syncAt={leadDetail.discord_role_sync_at}
+            canResync={hasPermission("leads.update")}
           />
         )}
       </div>
@@ -873,8 +875,8 @@ function ChannelInviteButton({ leadId }: { leadId: number }) {
 
 /** ADR-091 KPI7: Role sync status + manual resync button */
 function RoleSyncStatusRow({
-  leadId, status, syncAt,
-}: { leadId: number; status: string | null; syncAt: string | null }) {
+  leadId, status, syncAt, canResync,
+}: { leadId: number; status: string | null; syncAt: string | null; canResync: boolean }) {
   const { t } = useTranslation();
   const [syncing, setSyncing] = useState(false);
   const [triggered, setTriggered] = useState(false);
@@ -915,13 +917,15 @@ function RoleSyncStatusRow({
             </span>
           )}
         </span>
-        <Button loading={syncing} variant="secondary" size="md"
-          onClick={handleResync}
-          disabled={syncing}
+        {canResync && (
+          <Button loading={syncing} variant="secondary" size="md"
+            onClick={handleResync}
+            disabled={syncing}
 
-        >
-          {t("leads.discordRoleResync")}
-        </Button>
+          >
+            {t("leads.discordRoleResync")}
+          </Button>
+        )}
         {triggered && <span className="text-xs text-green-600">{t("leads.discordRoleSyncTriggered")}</span>}
         {error && <span className="text-xs text-red-500">{error}</span>}
       </div>
```

## 点検の生出力（tail -80）
### 1 vitest
```
|
!  No story files found for the specified pattern: src/**/*.mdx

 RUN  v4.1.7 /root/worktrees/salesanchor/release-discord-buttons-permission/frontend


 Test Files  1 passed (1)
      Tests  3 passed (3)
   Start at  09:54:14
   Duration  2.61s (transform 864ms, setup 60ms, import 1.25s, tests 103ms, environment 1.01s)

exit 0
```
### 2 tsc --noEmit
```
src/features/tcg-sold-out/soldOutApi.ts(3,45): error TS2307: Cannot find module '../../api/generated/schema' or its corresponding type declarations.
src/pages/inventory/OwnInventoryPage.tsx(11,33): error TS2307: Cannot find module '../../api/generated/schema' or its corresponding type declarations.
src/pages/super-admin/components/SoldOutResultsPanel.tsx(34,27): error TS7006: Parameter 'line' implicitly has an 'any' type.
src/pages/super-admin/components/SoldOutResultsPanel.tsx(34,33): error TS7006: Parameter 'index' implicitly has an 'any' type.
exit 2
```
tsc は exit 2。出たエラー 4 件はすべて api/generated/schema 未生成（このクラウドに生成物が無い）に由来し、変更した 2 ファイルのエラーは 0 件。カード外の事象で、既存の状態と考えられる（main での再確認は未実施）。
### 3 eslint
```
exit 0
```
### 4 diff --name-only
```
docs/handoff/discord-buttons-permission/card-impl-1.md
docs/handoff/discord-buttons-permission/design.md
docs/handoff/discord-buttons-permission/recon.md
frontend/src/pages/inbox/InboxKartePanel.discordButtons.test.tsx
frontend/src/pages/inbox/InboxKartePanel.tsx
exit 0
```
docs/handoff/discord-buttons-permission/ と上の 2 ファイルだけ（impl-report-1.md は本報告で追加）。

## 最終 HEAD
実装の最終 commit は 7703fe196。本報告を追加する commit がその上に 1 つ載る（その sha は push 後の git rev-parse HEAD を参照）。

DONE
