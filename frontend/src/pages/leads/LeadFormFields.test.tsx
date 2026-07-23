import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { LeadFormFields, buildLostReasonUpdatePayload } from "./LeadFormFields";

vi.mock("react-i18next", () => ({
  initReactI18next: { type: "3rdParty", init: vi.fn() },
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock("../../lib/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock("../../components/CountryCombobox", () => ({
  CountryCombobox: ({ id, value, onChange, placeholder }: {
    id: string;
    value: string;
    onChange: (value: string) => void;
    placeholder?: string;
  }) => <div data-testid={id} />,
}));

describe("LeadFormFields", () => {
  const baseForm = {
    customer_name: "Acme",
    email: "",
    phone: "",
    status: "lead",
    type: "",
    notes: "",
    country: "",
    close_reason_id: "",
    close_reason_memo: "",
  };

  it("hides lost reason fields when status is not lost", () => {
    render(
      <LeadFormFields
        form={baseForm}
        onChange={vi.fn()}
        closeReasonOptions={[]}
      />,
    );

    expect(screen.queryByLabelText("leads.lostReasonCode")).toBeNull();
    expect(screen.queryByLabelText("leads.lostReason")).toBeNull();
  });

  it("shows lost reason fields when status is lost and emits changes", () => {
    const onChange = vi.fn();
    render(
      <LeadFormFields
        form={{ ...baseForm, status: "lost" }}
        onChange={onChange}
        closeReasonOptions={[
          { id: 1, label: "Price" },
          { id: 2, label: "Competitor" },
        ]}
      />,
    );

    const select = screen.getByLabelText("leads.lostReasonCode");
    fireEvent.change(select, { target: { value: "2" } });
    expect(onChange).toHaveBeenCalledWith("close_reason_id", "2");

    const memo = screen.getByLabelText("leads.lostReason");
    fireEvent.change(memo, { target: { value: "important memo" } });
    expect(onChange).toHaveBeenCalledWith("close_reason_memo", "important memo");
  });

  it("builds lost-reason payload only when status is lost", () => {
    expect(buildLostReasonUpdatePayload("lead", "7", "memo")).toEqual({});
    expect(buildLostReasonUpdatePayload("lost", "7", "memo")).toEqual({
      close_reason_memo: "memo",
      close_reasons: [{ reason_id: 7, is_primary: true }],
    });
    expect(buildLostReasonUpdatePayload("lost", "", "")).toEqual({
      close_reason_memo: null,
      close_reasons: [],
    });
  });
});
