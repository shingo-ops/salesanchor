/**
 * /admin/discord-config — Discord 連携設定 (ADR-091 KPI3/KPI7)
 *
 * 3 枚のカード（サーバー接続 / 自動セットアップ / チケットの案内文）と、
 * 折りたたみの「詳細設定」で構成する。
 *
 * 権限:
 *   tenant.profile.view → 閲覧
 *   tenant.profile.edit → 保存・実行
 */
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { usePermissions } from "../../hooks/usePermissions";
import { PageLayout } from "../../components/PageLayout";
import { Button } from "../../components/Button";
import { ButtonLink } from "../../components/ButtonLink";
import { Card } from "../../components/Card";
import { Badge } from "../../components/Badge";
import type { BadgeVariant } from "../../components/Badge";
import { TextField } from "../../components/TextField";
import { Textarea } from "../../components/Textarea";
import { NAV_ICONS } from "../../constants/icons";
import "./discord-config.css";

interface DiscordConfig {
  guild_id: string | null;
  role_member: string;
  role_partner: string;
}

interface DiscordTicketConfig {
  ticket_category_id: string | null;
  ticket_button_channel_id: string | null;
  staff_role_id: string | null;
  welcome_template: string;
  small_channel_id: string | null;
  large_channel_id: string | null;
  small_role_name: string;
  large_role_name: string;
}

type StepStatus = "created" | "skipped" | "updated" | "posted" | "failed";

interface DiscordAutoSetupStep {
  step: string;
  status: StepStatus;
  discord_id?: string | null;
  error?: string | null;
}

interface DiscordAutoSetupResponse {
  status: "completed" | "partial" | "failed";
  steps: DiscordAutoSetupStep[];
  role_order_guide_url: string;
  error_hint?: string | null;
}

const SNOWFLAKE_RE = /^\d{17,20}$/;
const WELCOME_MAX_LENGTH = 500;
const ROLE_NAME_MAX_LENGTH = 100;
const FEEDBACK_MS = 3000;

const STEP_STATUS_VARIANT: Record<StepStatus, BadgeVariant> = {
  created: "success",
  updated: "info",
  skipped: "neutral",
  posted: "success",
  failed: "danger",
};

const OVERALL_VARIANT: Record<DiscordAutoSetupResponse["status"], BadgeVariant> = {
  completed: "success",
  partial: "warning",
  failed: "danger",
};

const STEP_GROUPS: { key: string; steps: string[] }[] = [
  { key: "roles", steps: ["role_staff", "role_partner", "role_member"] },
  { key: "categories", steps: ["category", "category_stock_member", "category_stock_large"] },
  { key: "channels", steps: ["ch_ticket", "ch_member", "ch_partner"] },
  { key: "button", steps: ["button"] },
];

const KNOWN_STEPS = new Set(STEP_GROUPS.flatMap((g) => g.steps));

type SaveSource = "welcome" | "details";
type TicketMessage = { source: SaveSource; kind: "saved" | "error"; text: string } | null;

export default function DiscordConfigPage() {
  const { t } = useTranslation();
  const { hasPermission, loading: permsLoading } = usePermissions();
  const canEdit = hasPermission("tenant.profile.edit");

  const [config, setConfig] = useState<DiscordConfig | null>(null);
  const [ticketConfig, setTicketConfig] = useState<DiscordTicketConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");

  // サーバー接続
  const [guildId, setGuildId] = useState("");
  const [editingGuild, setEditingGuild] = useState(false);
  const [guildSaving, setGuildSaving] = useState(false);
  const [guildError, setGuildError] = useState("");
  const [guildSaved, setGuildSaved] = useState(false);

  // チケット設定
  const [ticketCategoryId, setTicketCategoryId] = useState("");
  const [ticketButtonChannelId, setTicketButtonChannelId] = useState("");
  const [staffRoleId, setStaffRoleId] = useState("");
  const [welcomeTemplate, setWelcomeTemplate] = useState(() =>
    t("discordTicketConfig.welcomeTemplateDefault"),
  );
  const [smallChannelId, setSmallChannelId] = useState("");
  const [largeChannelId, setLargeChannelId] = useState("");
  const [smallRoleName, setSmallRoleName] = useState("Member");
  const [largeRoleName, setLargeRoleName] = useState("Partner");
  const [ticketSavingSource, setTicketSavingSource] = useState<SaveSource | null>(null);
  const [ticketMessage, setTicketMessage] = useState<TicketMessage>(null);
  const [showDetails, setShowDetails] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [deployError, setDeployError] = useState("");
  const [deployDone, setDeployDone] = useState(false);

  // 自動セットアップ
  const [autoSetupRunning, setAutoSetupRunning] = useState(false);
  const [autoSetupError, setAutoSetupError] = useState("");
  const [autoSetupResult, setAutoSetupResult] = useState<DiscordAutoSetupResponse | null>(null);

  const applyTicketConfig = useCallback((data: DiscordTicketConfig) => {
    setTicketConfig(data);
    setTicketCategoryId(data.ticket_category_id ?? "");
    setTicketButtonChannelId(data.ticket_button_channel_id ?? "");
    setStaffRoleId(data.staff_role_id ?? "");
    setWelcomeTemplate(data.welcome_template);
    setSmallChannelId(data.small_channel_id ?? "");
    setLargeChannelId(data.large_channel_id ?? "");
    setSmallRoleName(data.small_role_name ?? "Member");
    setLargeRoleName(data.large_role_name ?? "Partner");
  }, []);

  /** サーバーの最新値を取り直して画面に反映する（初期表示・自動セットアップ後で共用） */
  const fetchAll = useCallback(async () => {
    const [data, ticketData] = await Promise.all([
      api.get<DiscordConfig>("/admin/discord-config"),
      api.get<DiscordTicketConfig>("/admin/discord-ticket-config"),
    ]);
    setConfig(data);
    setGuildId(data.guild_id ?? "");
    applyTicketConfig(ticketData);
  }, [applyTicketConfig]);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setLoadError("");
      try {
        await fetchAll();
      } catch {
        setLoadError(t("discordConfig.loadError"));
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [fetchAll, t]);

  const savedGuildId = config?.guild_id ?? "";
  const isConnected = savedGuildId !== "";
  const isGuildFormOpen = !isConnected || editingGuild;

  const handleGuildSave = async () => {
    if (!SNOWFLAKE_RE.test(guildId.trim())) {
      setGuildError(t("discordConfig.invalidGuildId"));
      return;
    }
    setGuildSaving(true);
    setGuildError("");
    setGuildSaved(false);
    try {
      const updated = await api.put<DiscordConfig>("/admin/discord-config", { guild_id: guildId.trim() });
      setConfig(updated);
      setGuildId(updated.guild_id ?? "");
      setEditingGuild(false);
      setGuildSaved(true);
      setTimeout(() => setGuildSaved(false), FEEDBACK_MS);
    } catch {
      setGuildError(t("discordConfig.saveError"));
    } finally {
      setGuildSaving(false);
    }
  };

  const handleGuildCancel = () => {
    setGuildId(savedGuildId);
    setGuildError("");
    setEditingGuild(false);
  };

  /** 入力値を検証し、問題があれば表示用の文言を返す */
  const validateTicket = (): string | null => {
    const category = ticketCategoryId.trim();
    const buttonChannel = ticketButtonChannelId.trim();
    if (category === "" || buttonChannel === "") return t("discordTicketConfig.needIds");
    if (!SNOWFLAKE_RE.test(category) || !SNOWFLAKE_RE.test(buttonChannel)) {
      return t("discordTicketConfig.invalidSnowflake");
    }
    const optionalIds = [staffRoleId, smallChannelId, largeChannelId].map((v) => v.trim());
    if (optionalIds.some((v) => v !== "" && !SNOWFLAKE_RE.test(v))) {
      return t("discordTicketConfig.invalidSnowflake");
    }
    if (smallRoleName.trim() === "" || largeRoleName.trim() === "") {
      return t("discordTicketConfig.invalidRoleName");
    }
    return null;
  };

  const handleTicketSave = async (source: SaveSource) => {
    setTicketMessage(null);
    const problem = validateTicket();
    if (problem) {
      setTicketMessage({ source, kind: "error", text: problem });
      return;
    }
    setTicketSavingSource(source);
    try {
      const updated = await api.put<DiscordTicketConfig>("/admin/discord-ticket-config", {
        ticket_category_id: ticketCategoryId.trim(),
        ticket_button_channel_id: ticketButtonChannelId.trim(),
        staff_role_id: staffRoleId.trim() || null,
        welcome_template: welcomeTemplate,
        small_channel_id: smallChannelId.trim() || null,
        large_channel_id: largeChannelId.trim() || null,
        small_role_name: smallRoleName.trim(),
        large_role_name: largeRoleName.trim(),
      });
      applyTicketConfig(updated);
      setTicketMessage({ source, kind: "saved", text: t("discordTicketConfig.saved") });
      setTimeout(() => setTicketMessage(null), FEEDBACK_MS);
    } catch {
      setTicketMessage({ source, kind: "error", text: t("discordTicketConfig.saveError") });
    } finally {
      setTicketSavingSource(null);
    }
  };

  const handleDeployButton = async () => {
    setDeploying(true);
    setDeployError("");
    setDeployDone(false);
    try {
      await api.post("/admin/discord-ticket-config/deploy-button", {});
      setDeployDone(true);
      setTimeout(() => setDeployDone(false), FEEDBACK_MS);
    } catch {
      setDeployError(t("discordTicketConfig.deployError"));
    } finally {
      setDeploying(false);
    }
  };

  const handleAutoSetup = async () => {
    setAutoSetupRunning(true);
    setAutoSetupError("");
    setAutoSetupResult(null);
    try {
      const result = await api.post<DiscordAutoSetupResponse>("/admin/discord/auto-setup", {});
      setAutoSetupResult(result);
      if (result.status !== "failed") {
        // 作成分だけでなく既存・更新分も含め、サーバーの最新値を取り直す
        await fetchAll();
      }
    } catch {
      setAutoSetupError(t("discordAutoSetup.requestFailed"));
    } finally {
      setAutoSetupRunning(false);
    }
  };

  const stepLabel = (step: string) =>
    KNOWN_STEPS.has(step) ? t(`discordAutoSetup.steps.${step}`) : step;

  const renderStepGroup = (groupKey: string, steps: DiscordAutoSetupStep[]) => (
    <div className="dc-group" key={groupKey}>
      <p className="dc-group-title">{t(`discordAutoSetup.groups.${groupKey}`)}</p>
      <ul className="dc-step-list">
        {steps.map((s) => (
          <li key={s.step}>
            <div className="dc-step">
              <span>{stepLabel(s.step)}</span>
              <Badge variant={STEP_STATUS_VARIANT[s.status] ?? "neutral"} size="sm">
                {t(`discordAutoSetup.statuses.${s.status}`)}
              </Badge>
            </div>
            {s.error && <p className="dc-step-error">{s.error}</p>}
          </li>
        ))}
      </ul>
    </div>
  );

  const renderAutoSetupResult = (result: DiscordAutoSetupResponse) => {
    const grouped = STEP_GROUPS.map((g) => ({
      key: g.key,
      steps: result.steps.filter((s) => g.steps.includes(s.step)),
    })).filter((g) => g.steps.length > 0);
    const others = result.steps.filter((s) => !KNOWN_STEPS.has(s.step));
    return (
      <div className="dc-result">
        <div className="dc-result-status" role="status">
          <Badge variant={OVERALL_VARIANT[result.status]}>{t(`discordAutoSetup.${result.status}`)}</Badge>
          {result.status !== "completed" && <span>{t("discordAutoSetup.retryHint")}</span>}
        </div>
        {result.error_hint && <p className="dc-step-error">{result.error_hint}</p>}
        {grouped.map((g) => renderStepGroup(g.key, g.steps))}
        {others.length > 0 && renderStepGroup("other", others)}
        {result.status !== "failed" && (
          <div className="dc-next">
            <Badge variant="warning" dot>{t("discordAutoSetup.nextStepBadge")}</Badge>
            <span className="dc-next-text">{t("discordAutoSetup.nextStep")}</span>
            <ButtonLink variant="ghost" size="sm" href={result.role_order_guide_url} target="_blank" rel="noreferrer">
              {t("discordAutoSetup.guideLink")}
            </ButtonLink>
          </div>
        )}
      </div>
    );
  };

  const renderTicketMessage = (source: SaveSource) => {
    if (ticketMessage?.source !== source) return null;
    return (
      <Badge variant={ticketMessage.kind === "saved" ? "success" : "danger"}>{ticketMessage.text}</Badge>
    );
  };

  if (permsLoading || loading) {
    return (
      <PageLayout navKey="nav.discordConfig">
        <p className="dc-desc">{t("common.loading")}</p>
      </PageLayout>
    );
  }

  return (
    <PageLayout navKey="nav.discordConfig">
      <div className="dc-page">
        {loadError && <Badge variant="danger">{loadError}</Badge>}

        {/* ① サーバー接続 */}
        <Card>
          <div className="dc-card-head">
            <h3 className="dc-card-title">{t("discordConfig.connectionTitle")}</h3>
            <Badge variant={isConnected ? "success" : "neutral"} dot>
              {isConnected ? t("discordConfig.connected") : t("discordConfig.notConnected")}
            </Badge>
          </div>
          {isGuildFormOpen ? (
            <>
              <TextField
                label={t("discordConfig.serverIdLabel")}
                value={guildId}
                onChange={(e) => setGuildId(e.target.value)}
                disabled={!canEdit}
                placeholder={t("discordConfig.serverIdPlaceholder")}
                helperText={t("discordConfig.serverIdHint")}
                error={guildError || undefined}
                fullWidth
              />
              {canEdit && (
                <div className="dc-actions">
                  <Button variant="primary" onClick={handleGuildSave} disabled={guildSaving}>
                    {guildSaving ? t("common.saving") : isConnected ? t("common.save") : t("discordConfig.connect")}
                  </Button>
                  {isConnected && (
                    <Button variant="ghost" onClick={handleGuildCancel} disabled={guildSaving}>
                      {t("common.cancel")}
                    </Button>
                  )}
                </div>
              )}
            </>
          ) : (
            <div className="dc-row">
              <span className="dc-server-id dc-grow">{savedGuildId}</span>
              {guildSaved && <Badge variant="success">{t("discordConfig.saved")}</Badge>}
              {canEdit && (
                <Button variant="secondary" size="sm" onClick={() => setEditingGuild(true)}>
                  {t("discordConfig.change")}
                </Button>
              )}
            </div>
          )}
        </Card>

        {/* ② 自動セットアップ */}
        {canEdit && (
          <Card>
            <div className="dc-card-head">
              <h3 className="dc-card-title">{t("discordAutoSetup.title")}</h3>
            </div>
            <p className="dc-desc">{t("discordAutoSetup.description")}</p>
            <div className="dc-row">
              <Button variant="secondary" onClick={handleAutoSetup} disabled={!isConnected || autoSetupRunning}>
                {autoSetupRunning ? t("discordAutoSetup.running") : t("discordAutoSetup.runButton")}
              </Button>
              {!isConnected && <span className="dc-hint">{t("discordAutoSetup.needConnect")}</span>}
            </div>
            {autoSetupError && <p className="dc-step-error">{autoSetupError}</p>}
            {autoSetupResult && renderAutoSetupResult(autoSetupResult)}
          </Card>
        )}

        {/* ③ チケットの案内文 */}
        <Card>
          <div className="dc-card-head">
            <h3 className="dc-card-title">{t("discordTicketConfig.welcomeTitle")}</h3>
          </div>
          <Textarea
            value={welcomeTemplate}
            onChange={(e) => setWelcomeTemplate(e.target.value)}
            disabled={!canEdit}
            placeholder={t("discordTicketConfig.welcomePlaceholder")}
            helperText={t("discordTicketConfig.welcomeHint", {
              count: welcomeTemplate.length,
              max: WELCOME_MAX_LENGTH,
            })}
            maxLength={WELCOME_MAX_LENGTH}
            rows={4}
            aria-label={t("discordTicketConfig.welcomeTitle")}
            fullWidth
          />
          {canEdit && (
            <div className="dc-actions">
              <Button
                variant="secondary"
                onClick={() => handleTicketSave("welcome")}
                disabled={ticketSavingSource !== null}
              >
                {ticketSavingSource === "welcome" ? t("common.saving") : t("common.save")}
              </Button>
              {ticketConfig?.ticket_button_channel_id && (
                <Button variant="secondary" onClick={handleDeployButton} disabled={deploying}>
                  {deploying ? t("discordTicketConfig.deploying") : t("discordTicketConfig.deployButton")}
                </Button>
              )}
              {renderTicketMessage("welcome")}
              {deployDone && <Badge variant="success">{t("discordTicketConfig.deployDone")}</Badge>}
              {deployError && <Badge variant="danger">{deployError}</Badge>}
            </div>
          )}
        </Card>

        {/* 詳細設定（通常は変更不要） */}
        <div className="dc-details">
          <Button variant="secondary" size="sm" onClick={() => setShowDetails((v) => !v)} aria-expanded={showDetails}>
            {t("discordTicketConfig.detailsToggle")}
            <NAV_ICONS.chevronDown
              size={16}
              aria-hidden="true"
              className={`dc-chevron${showDetails ? " dc-chevron--open" : ""}`}
            />
          </Button>
          {showDetails && (
            <Card density="compact">
              <div className="dc-details-fields">
                <TextField
                  label={t("discordTicketConfig.categoryIdLabel")}
                  value={ticketCategoryId}
                  onChange={(e) => setTicketCategoryId(e.target.value)}
                  disabled={!canEdit}
                  placeholder={t("discordTicketConfig.idPlaceholder")}
                  fullWidth
                />
                <TextField
                  label={t("discordTicketConfig.buttonChannelIdLabel")}
                  value={ticketButtonChannelId}
                  onChange={(e) => setTicketButtonChannelId(e.target.value)}
                  disabled={!canEdit}
                  placeholder={t("discordTicketConfig.idPlaceholder")}
                  fullWidth
                />
                <TextField
                  label={t("discordTicketConfig.staffRoleIdLabel")}
                  value={staffRoleId}
                  onChange={(e) => setStaffRoleId(e.target.value)}
                  disabled={!canEdit}
                  placeholder={t("discordTicketConfig.idPlaceholder")}
                  fullWidth
                />
                <TextField
                  label={t("discordTicketConfig.smallChannelIdLabel")}
                  value={smallChannelId}
                  onChange={(e) => setSmallChannelId(e.target.value)}
                  disabled={!canEdit}
                  placeholder={t("discordTicketConfig.idPlaceholder")}
                  fullWidth
                />
                <TextField
                  label={t("discordTicketConfig.largeChannelIdLabel")}
                  value={largeChannelId}
                  onChange={(e) => setLargeChannelId(e.target.value)}
                  disabled={!canEdit}
                  placeholder={t("discordTicketConfig.idPlaceholder")}
                  fullWidth
                />
                <TextField
                  label={t("discordTicketConfig.smallRoleNameLabel")}
                  value={smallRoleName}
                  onChange={(e) => setSmallRoleName(e.target.value)}
                  disabled={!canEdit}
                  maxLength={ROLE_NAME_MAX_LENGTH}
                  fullWidth
                />
                <TextField
                  label={t("discordTicketConfig.largeRoleNameLabel")}
                  value={largeRoleName}
                  onChange={(e) => setLargeRoleName(e.target.value)}
                  disabled={!canEdit}
                  maxLength={ROLE_NAME_MAX_LENGTH}
                  fullWidth
                />
              </div>
              {canEdit && (
                <div className="dc-actions">
                  <Button
                    variant="secondary"
                    onClick={() => handleTicketSave("details")}
                    disabled={ticketSavingSource !== null}
                  >
                    {ticketSavingSource === "details" ? t("common.saving") : t("common.save")}
                  </Button>
                  {renderTicketMessage("details")}
                </div>
              )}
            </Card>
          )}
        </div>
      </div>
    </PageLayout>
  );
}
