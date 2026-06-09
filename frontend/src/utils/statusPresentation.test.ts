/* eslint-disable local/no-japanese-literal */
import { describe, expect, it, vi } from "vitest";
import {
  getStatusPresentation,
  STATUS_PRESENTATION_MAP,
  type BadgeBucket,
  type StatusDomain,
} from "./statusPresentation";

describe("getStatusPresentation — 正常系", () => {
  it("lead.negotiating → info / negotiating（不整合①解消確認）", () => {
    const p = getStatusPresentation("lead", "negotiating");
    expect(p.bucket).toBe("info");
    expect(p.badgeVariant).toBe("negotiating");
  });

  it("deal.negotiating → info / negotiating（DealsPage 統一確認）", () => {
    const p = getStatusPresentation("deal", "negotiating");
    expect(p.bucket).toBe("info");
    expect(p.badgeVariant).toBe("negotiating");
  });

  it("quote.sent → info / negotiating（Quote の negotiating バリアントを利用）", () => {
    const p = getStatusPresentation("quote", "sent");
    expect(p.bucket).toBe("info");
    expect(p.badgeVariant).toBe("negotiating");
  });

  it("invoice.sent と invoice.issued が同一バケット（重複ロジック統合確認）", () => {
    const sent   = getStatusPresentation("invoice", "sent");
    const issued = getStatusPresentation("invoice", "issued");
    expect(sent.bucket).toBe("info");
    expect(issued.bucket).toBe("info");
  });

  it("invoice.paid → success", () => {
    expect(getStatusPresentation("invoice", "paid").bucket).toBe("success");
  });

  it("staff.pending → danger（現状維持: 将来 warning に昇格可）", () => {
    expect(getStatusPresentation("staff", "pending").bucket).toBe("danger");
    expect(getStatusPresentation("staff", "pending").badgeVariant).toBe("lost");
  });

  it("bot.maintenance → danger（現状維持: 将来 warning に昇格可）", () => {
    expect(getStatusPresentation("bot", "maintenance").bucket).toBe("danger");
    expect(getStatusPresentation("bot", "maintenance").badgeVariant).toBe("lost");
  });

  it("deal.open → neutral", () => {
    expect(getStatusPresentation("deal", "open").bucket).toBe("neutral");
  });

  it("全ドメインに i18n labelKey が設定されている", () => {
    for (const [domain, statuses] of Object.entries(STATUS_PRESENTATION_MAP)) {
      for (const [status, p] of Object.entries(statuses)) {
        expect(p.labelKey, `${domain}.${status} に labelKey がない`).toBeTruthy();
      }
    }
  });
});

describe("getStatusPresentation — 未知ステータスのフォールバック", () => {
  it("未知の status は neutral を返す", () => {
    const p = getStatusPresentation("lead", "unknown_status_xyz");
    expect(p.bucket).toBe("neutral");
    expect(p.badgeVariant).toBe("neutral");
  });

  it("未知 status のとき開発環境で console.warn を出力する", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    getStatusPresentation("quote", "__nonexistent__");
    // Vite テスト環境では import.meta.env.DEV = true
    expect(warn).toHaveBeenCalledWith(
      expect.stringContaining("__nonexistent__"),
    );
    warn.mockRestore();
  });

  it("フォールバック後も呼び出し元がクラッシュしない", () => {
    expect(() => {
      const p = getStatusPresentation("invoice", "completely_unknown");
      // badgeVariant を使って文字列を組み立てても安全
      const cls = `badge badge-${p.badgeVariant}`;
      expect(cls).toBe("badge badge-neutral");
    }).not.toThrow();
  });
});

describe("STATUS_PRESENTATION_MAP — 網羅性", () => {
  const VALID_BUCKETS: Set<BadgeBucket> = new Set([
    "success", "danger", "warning", "info", "neutral",
  ]);

  it("全11ドメインが存在する", () => {
    const expected: StatusDomain[] = [
      "lead", "quote", "invoice", "deal", "order",
      "purchaseOrder", "parseStatus", "staff", "bot", "prospectRank", "erpJobStatus",
    ];
    for (const d of expected) {
      expect(STATUS_PRESENTATION_MAP[d], `domain "${d}" が存在しない`).toBeDefined();
    }
  });

  it("全エントリのバケットが有効な値である", () => {
    for (const [domain, statuses] of Object.entries(STATUS_PRESENTATION_MAP)) {
      for (const [status, p] of Object.entries(statuses)) {
        expect(
          VALID_BUCKETS.has(p.bucket),
          `${domain}.${status} のバケット "${p.bucket}" は不正`,
        ).toBe(true);
      }
    }
  });

  it("全エントリの badgeVariant が空でない", () => {
    for (const [domain, statuses] of Object.entries(STATUS_PRESENTATION_MAP)) {
      for (const [status, p] of Object.entries(statuses)) {
        expect(
          p.badgeVariant.length,
          `${domain}.${status} の badgeVariant が空`,
        ).toBeGreaterThan(0);
      }
    }
  });

  it("各ドメインに少なくとも1エントリある", () => {
    for (const [domain, statuses] of Object.entries(STATUS_PRESENTATION_MAP)) {
      expect(
        Object.keys(statuses).length,
        `domain "${domain}" にエントリがない`,
      ).toBeGreaterThan(0);
    }
  });
});
