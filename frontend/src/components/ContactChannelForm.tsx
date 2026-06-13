/**
 * 担当者チャンネル追加・編集フォーム（ADR-098 SA-04 J2/G1）。
 *
 * 役割:
 *   contact_contact_channels にチャンネルを追加または編集する。
 *   - ID 単位で保存（URL 入力欄なし・G1 SSOT 維持）
 *   - 保存前に重複チェック（同一 channel + purpose が別担当者に存在 → 警告 + 2択）
 *     ① 統合する    → MergeContactModal へ遷移
 *     ② 別人として保存（監査ログ記録） → 保存 + audit log エントリ追記
 *   - Discord のみ guild_id 入力欄を追加で表示
 */

import { useEffect, useState, FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../lib/api";
import { Modal } from "./Modal";
import { Button } from "./Button";
import { TextField } from "./TextField";
import { Select } from "./Select";

export interface ContactChannelEntry {
  id?: number;
  channel: string;
  purpose: string | null;
  guild_id?: string | null;
  is_primary: boolean;
}

interface DuplicateInfo {
  contact_id: number;
  contact_code: string;
  display_name: string | null;
}

interface Props {
  open: boolean;
  contactId: number;
  companyId: number;
  /** 既存行（編集モード）または null（新規） */
  initial: ContactChannelEntry | null;
  onSaved: () => void;
  onCancel: () => void;
  /** 重複検出時に統合モーダルを開くコールバック */
  onRequestMerge?: (duplicateContactId: number) => void;
}

const KNOWN_CHANNELS = [
  "whatsapp",
  "telegram",
  "discord",
  "instagram",
  "messenger",
  "phone",
  "email",
  "other",
] as const;

export default function ContactChannelForm({
  open, contactId, initial, onSaved, onCancel, onRequestMerge,
}: Props) {
  const { t } = useTranslation();
  const [channel, setChannel] = useState("whatsapp");
  const [purpose, setPurpose] = useState("");
  const [guildId, setGuildId] = useState("");
  const [isPrimary, setIsPrimary] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [duplicate, setDuplicate] = useState<DuplicateInfo | null>(null);
  /** true = ユーザーが「別人として保存」を選択した後 */
  const [forceWithAudit, setForceWithAudit] = useState(false);

  useEffect(() => {
    if (!open) return;
    if (initial) {
      setChannel(initial.channel);
      setPurpose(initial.purpose || "");
      setGuildId(initial.guild_id || "");
      setIsPrimary(initial.is_primary);
    } else {
      setChannel("whatsapp");
      setPurpose("");
      setGuildId("");
      setIsPrimary(false);
    }
    setError(null);
    setDuplicate(null);
    setForceWithAudit(false);
  }, [open, initial]);

  // purpose / channel 変更時に重複チェック（新規のみ）
  useEffect(() => {
    if (!open || initial || !purpose.trim() || !channel) {
      setDuplicate(null);
      setForceWithAudit(false);
      return;
    }
    let cancelled = false;
    const handle = window.setTimeout(async () => {
      try {
        const res = await api.get<DuplicateInfo | null>(
          `/contacts/channel-duplicate?channel=${encodeURIComponent(channel)}&purpose=${encodeURIComponent(purpose.trim())}&exclude_contact_id=${contactId}`
        );
        if (!cancelled) {
          setDuplicate(res);
          if (res) setForceWithAudit(false); // 新たな重複が見つかったらリセット
        }
      } catch {
        // 重複チェックは best-effort — エラーは無視
      }
    }, 400);
    return () => {
      cancelled = true;
      window.clearTimeout(handle);
    };
  }, [open, initial, channel, purpose, contactId]);

  const idPlaceholder = (() => {
    const key = `contactChannel.idPlaceholder.${channel}` as const;
    const specific = t(key, { defaultValue: "" });
    return specific || t("contactChannel.idPlaceholder.default");
  })();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    // 重複がある場合、「別人として保存」が選択されていない限りブロック
    if (duplicate && !forceWithAudit) {
      // フォームの submit は 2択ボタン経由で行われるため、ここには通常到達しない
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const payload: ContactChannelEntry = {
        channel,
        purpose: purpose.trim() || null,
        guild_id: channel === "discord" ? (guildId.trim() || null) : null,
        is_primary: isPrimary,
      };

      if (initial?.id != null) {
        // 編集: 呼び出し元が全リストを管理するため、ここでは onSaved を呼ぶだけ
        onSaved();
        return;
      }

      // 新規追加: GET で既存リストを取得 → 1行追加 → PATCH
      type ContactDetail = { contact_channels?: ContactChannelEntry[] };
      const contactDetail = await api.get<ContactDetail>(`/contacts/${contactId}`);
      const channels: ContactChannelEntry[] = contactDetail.contact_channels || [];

      await api.patch(`/contacts/${contactId}`, {
        contact_channels: [...channels, payload],
      });

      // 「別人として保存」の場合は監査ログエントリを追記
      if (forceWithAudit && duplicate) {
        try {
          await api.post(`/contacts/${contactId}/channel-acknowledge-duplicate`, {
            channel,
            purpose: purpose.trim() || null,
            duplicate_contact_id: duplicate.contact_id,
          });
        } catch {
          // 監査ログ書き込み失敗は非致命的 — 保存自体は成功済み
          logger.warn("[ContactChannelForm] audit log for duplicate acknowledge failed");
        }
      }

      onSaved();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "";
      // eslint-disable-next-line local/no-japanese-literal
      if (msg.includes("23505") || msg.includes("unique") || msg.includes("重複")) {
        setError(t("contactChannel.duplicateWarning"));
      } else {
        setError(msg || t("common.operationError"));
      }
    } finally {
      setSubmitting(false);
    }
  };

  const title = initial
    ? t("contactChannel.editTitle")
    : t("contactChannel.addTitle");

  return (
    <Modal open={open} onClose={onCancel} title={title} size="sm">
      <form onSubmit={handleSubmit}>
        <div className="form-grid">
          <Select
            label={t("contactChannel.channelLabel")}
            value={channel}
            onChange={(e) => setChannel(e.target.value)}
            disabled={!!initial}
            options={KNOWN_CHANNELS.map((ch) => ({
              value: ch,
              label: t(`contactChannel.channels.${ch}`, { defaultValue: ch }),
            }))}
          />

          <TextField
            label={t("contactChannel.idLabel")}
            type="text"
            value={purpose}
            onChange={(e) => setPurpose(e.target.value)}
            placeholder={idPlaceholder}
            maxLength={50}
          />

          {channel === "discord" && (
            <TextField
              label={t("contactChannel.guildIdLabel")}
              type="text"
              value={guildId}
              onChange={(e) => setGuildId(e.target.value)}
              placeholder={t("contactChannel.guildIdPlaceholder")}
              maxLength={50}
            />
          )}

          <div className="form-row">
            <label>
              {/* checkbox は TextField 対象外のため残置 */}
              <input
                type="checkbox"
                checked={isPrimary}
                onChange={(e) => setIsPrimary(e.target.checked)}
              />
              {" "}{t("contactChannel.isPrimaryLabel")}
            </label>
          </div>
        </div>

        {/* 重複警告（2択） */}
        {duplicate && !forceWithAudit && (
          <div
            style={{
              background: "var(--warning-bg)",
              border: "1px solid var(--warning-text)",
              padding: "var(--space-3)",
              borderRadius: "var(--radius-sm)",
              marginTop: "var(--space-3)",
              fontSize: "var(--font-sm)",
              color: "var(--warning-text)",
            }}
          >
            <p style={{ margin: 0, marginBottom: "var(--space-2)" }}>
              {t("contactChannel.duplicateWarning", {
                name: duplicate.display_name || duplicate.contact_code,
              })}
            </p>
            <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
              {onRequestMerge && (
                <Button
                  type="button"
                  size="sm"
                  variant="secondary"
                  onClick={() => onRequestMerge(duplicate.contact_id)}
                >
                  {t("contactChannel.mergeButton")}
                </Button>
              )}
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => setForceWithAudit(true)}
              >
                {t("contactChannel.saveAsDistinct")}
              </Button>
            </div>
          </div>
        )}

        {/* 「別人として保存」選択後の確認バナー */}
        {duplicate && forceWithAudit && (
          <div
            style={{
              background: "var(--bg-subtle)",
              border: "1px solid var(--border)",
              padding: "var(--space-2)",
              borderRadius: "var(--radius-sm)",
              marginTop: "var(--space-2)",
              fontSize: "var(--font-sm)",
            }}
          >
            {t("contactChannel.saveAsDistinctConfirmed")}
          </div>
        )}

        {error && <div className="error-banner" style={{ marginTop: "var(--space-2)" }}>{error}</div>}

        {/* 重複あり・選択前は保存ボタン非表示（2択ボタンでのみ進める） */}
        {(!duplicate || forceWithAudit) && (
          <div className="form-actions">
            <Button type="button" variant="secondary" onClick={onCancel}>
              {t("contactChannel.cancel")}
            </Button>
            <Button
              type="submit"
              variant="primary"
              disabled={submitting || !channel}
            >
              {submitting ? t("common.saving") : t("contactChannel.save")}
            </Button>
          </div>
        )}

        {/* 重複あり・選択前はキャンセルのみ */}
        {duplicate && !forceWithAudit && (
          <div className="form-actions">
            <Button type="button" variant="secondary" onClick={onCancel}>
              {t("contactChannel.cancel")}
            </Button>
          </div>
        )}
      </form>
    </Modal>
  );
}

const logger = { warn: (msg: string) => console.warn(msg) };
