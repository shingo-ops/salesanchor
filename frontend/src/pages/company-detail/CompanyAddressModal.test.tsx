/* eslint-disable local/no-japanese-literal -- 試験の題名（画面の文字ではない） */
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CompanyAddressModal } from "./CompanyAddressModal";
import { emptyAddress, type AddressFormState, type Company } from "./company-detail.types";

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => key }) }));

afterEach(() => cleanup());

const company = { id: 1, addresses: [] } as unknown as Company;

function Harness({
  initial,
  submit,
}: {
  initial: AddressFormState;
  submit: (next: AddressFormState[]) => Promise<void>;
}) {
  const [form, setForm] = useState(initial);
  return (
    <CompanyAddressModal
      isOpen
      onClose={() => {}}
      addrForm={form}
      setAddrForm={setForm}
      submitAddresses={submit}
      company={company}
      canEdit
      handleAddressTypeChange={(type) => setForm({ ...form, address_type: type })}
    />
  );
}

function findLine1(): HTMLInputElement {
  const label = screen.getByText("shipping.address1");
  return label.parentElement!.querySelector("input") as HTMLInputElement;
}

describe("社内の住所の窓（K11・K12）", () => {
  it("送り先で住所1に36文字 → 保存で addressRule.maxLength・保存は呼ばれない", async () => {
    const submit = vi.fn().mockResolvedValue(undefined);
    render(<Harness initial={{ ...emptyAddress("delivery"), address_line_1: "x".repeat(36) }} submit={submit} />);
    expect(screen.queryByText("addressRule.maxLength")).toBeNull(); // 開いただけでは赤くならない
    fireEvent.click(screen.getByRole("button", { name: "common.save" }));
    expect(await screen.findByText("addressRule.maxLength")).toBeTruthy();
    expect(submit).not.toHaveBeenCalled();
  });

  it("送り先で住所1に日本語 → addressRule.ascii", async () => {
    const submit = vi.fn().mockResolvedValue(undefined);
    render(<Harness initial={{ ...emptyAddress("delivery"), address_line_1: "東京" }} submit={submit} />);
    fireEvent.click(screen.getByRole("button", { name: "common.save" }));
    expect(await screen.findByText("addressRule.ascii")).toBeTruthy();
    expect(submit).not.toHaveBeenCalled();
  });

  it("請求先なら36文字でも保存が呼ばれる", async () => {
    const submit = vi.fn().mockResolvedValue(undefined);
    render(<Harness initial={{ ...emptyAddress("billing"), address_line_1: "x".repeat(36) }} submit={submit} />);
    fireEvent.click(screen.getByRole("button", { name: "common.save" }));
    await waitFor(() => expect(submit).toHaveBeenCalledTimes(1));
    expect(screen.queryByText("addressRule.maxLength")).toBeNull();
  });

  it("赤くなった欄を打ち直すとその赤が消える", async () => {
    const submit = vi.fn().mockResolvedValue(undefined);
    render(<Harness initial={{ ...emptyAddress("delivery"), address_line_1: "x".repeat(36) }} submit={submit} />);
    fireEvent.click(screen.getByRole("button", { name: "common.save" }));
    await screen.findByText("addressRule.maxLength");
    fireEvent.change(findLine1(), { target: { value: "ok" } });
    expect(screen.queryByText("addressRule.maxLength")).toBeNull();
  });
});
