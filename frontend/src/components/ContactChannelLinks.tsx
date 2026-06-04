/**
 * SA-05: 担当者チャンネルリンクコンポーネント
 *
 * GET /api/v1/contacts/{contact_id}/channel-links から取得した
 * クリック可能なリンク一覧を表示する。
 *
 * is_verified=false のチャンネルは「未検証」バッジを添付して表示。
 * テンプレートが存在しない or URL 生成不可のチャンネルはラベルのみ表示。
 */

import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../lib/api";

interface ChannelLink {
  channel: string;
  url: string | null;
  is_verified: boolean;
  label: string;
  notes: string | null;
}

interface Props {
  contactId: number;
}

export default function ContactChannelLinks({ contactId }: Props) {
  const { t } = useTranslation();
  const [links, setLinks] = useState<ChannelLink[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .get<ChannelLink[]>(`/contacts/${contactId}/channel-links`)
      .then((data) => {
        if (!cancelled) setLinks(data);
      })
      .catch(() => {
        // サイレント失敗: チャンネルリンクは補助情報のため一覧表示を壊さない
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [contactId]);

  if (loading || links.length === 0) {
    return <span style={{ color: "var(--text-muted)" }}>-</span>;
  }

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-1)" }}>
      {links.map((link) => (
        <span key={link.channel} style={{ display: "inline-flex", alignItems: "center", gap: "2px" }}>
          {link.url ? (
            <a
              href={link.url}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={t("contacts.channels.open_link") + ": " + link.label}
              title={link.notes ?? link.label}
              style={{ fontSize: "var(--text-sm)" }}
            >
              {link.label}
            </a>
          ) : (
            <span style={{ fontSize: "var(--text-sm)", color: "var(--text-muted)" }} title={link.notes ?? undefined}>
              {link.label}
            </span>
          )}
          {!link.is_verified && (
            <span
              style={{
                fontSize: "var(--text-xs)",
                padding: "1px 4px",
                borderRadius: "var(--radius-sm)",
                background: "var(--warning-bg)",
                color: "var(--warning-text)",
              }}
              title={link.notes ?? undefined}
            >
              {t("contacts.channels.unverified_badge")}
            </span>
          )}
        </span>
      ))}
    </div>
  );
}
