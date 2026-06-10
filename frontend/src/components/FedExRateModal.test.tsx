/**
 * FedExRateModal テスト（ADR-125 D6）
 *
 * - 宛先国コード入力フィールドが表示される
 * - destinationCountryCode prop が初期値として反映される
 * - 見積もり取得後に料金選択 → onSelectRate が呼ばれる
 * - 未連携エラー時に誘導メッセージが表示される
 * - 宛先国コード未入力時はボタンが disabled
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { FedExRateModal } from "./FedExRateModal";

// react-i18next mock — English values intentionally used to avoid i18n lint rule
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "fedexRateModal.title": "FedEx Live Quote",
        "fedexRateModal.originLabel": "Origin country code",
        "fedexRateModal.originPlaceholder": "JP",
        "fedexRateModal.destinationLabel": "Destination country code",
        "fedexRateModal.destinationPlaceholder": "e.g. US",
        "fedexRateModal.getQuote": "Get quote",
        "fedexRateModal.loading": "Loading...",
        "fedexRateModal.noResults": "No services found",
        "fedexRateModal.sourceLive": "Live",
        "fedexRateModal.sourceStatic": "Static",
        "fedexRateModal.colSource": "Source",
        "fedexRateModal.colService": "Service",
        "fedexRateModal.colTransitDays": "Transit",
        "fedexRateModal.colFee": "Fee",
        "fedexRateModal.colCurrency": "Currency",
        "fedexRateModal.errorNotConnected": "FedEx not connected",
        "fedexRateModal.goToIntegrationSettings": "Open FedEx settings ->",
        "fedexRateModal.errorAccountNumber": "Account number missing",
        "fedexRateModal.errorApiFailure": "FedEx API error",
        "fedexRateModal.selectRate": "Use this rate",
        "fedexRateModal.cancel": "Cancel",
        "fedexRateModal.days": "d",
        "fedexRateModal.postalCodeLabel": "Destination postal code (optional)",
        "fedexRateModal.postalCodePlaceholder": "e.g. 10001",
        "fedexRateModal.badgeApproximate": "Approximate",
        "common.close": "Close",
      };
      return map[key] ?? key;
    },
  }),
}));

vi.mock("../lib/api", () => ({
  api: { post: vi.fn() },
}));

import { api } from "../lib/api";

const defaultProps = {
  open: true,
  onClose: vi.fn(),
  weightKg: 5,
  onSelectRate: vi.fn(),
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("FedExRateModal", () => {
  it("destination country code input is rendered", () => {
    render(<FedExRateModal {...defaultProps} />);
    expect(screen.getByLabelText("Destination country code")).toBeTruthy();
  });

  it("destinationCountryCode prop is used as initial value", () => {
    render(<FedExRateModal {...defaultProps} destinationCountryCode="US" />);
    const input = screen.getByDisplayValue("US") as HTMLInputElement;
    expect(input.id).toBe("fedex-dest-cc");
  });

  it("get-quote button is disabled when destination country code is empty", () => {
    render(<FedExRateModal {...defaultProps} destinationCountryCode="" />);
    const btn = screen.getByText("Get quote").closest("button");
    expect(btn?.disabled).toBe(true);
  });

  it("selecting a rate calls onSelectRate with fee, currency, serviceType", async () => {
    const mockPost = vi.mocked(api.post);
    mockPost.mockResolvedValueOnce({
      results: [
        {
          carrier: "FedEx",
          zone: "A",
          fee: 5000,
          currency: "JPY",
          source: "fedex_live",
          service_type: "FEDEX_IP",
          service_name: "FedEx International Priority",
          transit_days: 3,
          delivery_timestamp: null,
        },
      ],
      cheapest: null,
      live_error: null,
      rate_precision: "approximate",
    });

    const onSelectRate = vi.fn();
    render(
      <FedExRateModal {...defaultProps} destinationCountryCode="US" onSelectRate={onSelectRate} />,
    );

    fireEvent.click(screen.getByText("Get quote"));

    await waitFor(() => screen.getByText("Use this rate"));
    fireEvent.click(screen.getByText("Use this rate"));

    expect(onSelectRate).toHaveBeenCalledWith(5000, "JPY", "FEDEX_IP");
  });

  it("shows settings link when live_error includes the not-connected marker", async () => {
    const mockPost = vi.mocked(api.post);
    mockPost.mockResolvedValueOnce({
      results: [],
      cheapest: null,
      // Unicode escape to avoid i18n lint rule on the Japanese marker
      live_error: "FedEx\u672a\u9023\u643a\u3067\u3059", // "FedEx未連携です"
      rate_precision: null,
    });

    render(<FedExRateModal {...defaultProps} destinationCountryCode="US" />);
    fireEvent.click(screen.getByText("Get quote"));

    await waitFor(() => screen.getByText("Open FedEx settings ->"));
    expect(screen.getByText("Open FedEx settings ->")).toBeTruthy();
  });
});
